"""D55 strategy runtime: NOISE / OPEN_DRIVE signals and exits from stored 1-minute TradingView bars."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.models import Bar, Signal, SignalGate, TradePlanRow
from app.signals import strategy_service as SS

DAY0 = datetime(2026, 10, 12, 13, 30, tzinfo=UTC)  # Monday 09:30 ET (EDT, UTC−4)


def _rules(loaded_rules, **strategy):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True, "windows": [("09:30", "16:00")]})
    st = r.strategy.model_copy(update={"lunqfx": False, **strategy})
    return r.model_copy(update={"strategy": st, "instruments": {**r.instruments, "MNQ": mnq}})


def _sessions(n=12):
    out, d = [], DAY0
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _add_day(s, start, closes, base=D(20000), vol=D(100)):
    """closes: k → close (missing k = flat at the previous close). Highs/lows ±1 around open/close."""
    prev = base
    for k in range(390):
        c = closes.get(k, prev)
        o = prev
        s.add(
            Bar(
                symbol="MNQ",
                tf="1",
                close_time=start + timedelta(minutes=k + 1),
                o=o,
                h=max(o, c) + 1,
                l=min(o, c) - 1,
                c=c,
                v=vol,
                source="tradingview",
            )
        )
        prev = c


@pytest.fixture
def db(client):
    return client.app.state.sessionmaker


def _history(s, days):
    for start in days:  # quiet days: ±0.2% wiggle at k=29 / 89 → σ ≈ 0.2% at those minutes
        _add_day(s, start, {29: D(20040), 30: D(20000), 89: D(19960), 90: D(20000)})


def test_noise_warmup_entry_exit_and_flat(db, loaded_rules):
    rules = _rules(loaded_rules, noise=True)
    days = _sessions(12)
    hist, today = days[:-1], days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    with db() as s:
        _history(s, hist[:5])  # only 5 sessions stored → warm-up, no signal
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.commit()
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=30)
        )
        assert out.updates == [] and out.exits == []
    with db() as s:
        _history(s, hist[5:])
        s.commit()
        # 10:00 check: close 20087 (+0.44%) above the upper band (prior close 20000, σ 0.2%) → LONG PASS
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=30)
        )
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.direction == "LONG" and sig.features["strategy"] == "NOISE" and sig.features["state"] == "OPEN"
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "NOISE" and plan.stop < plan.entry < plan.take_profit
        assert plan.entry - plan.stop == D(124)  # D58: fixed $250 emergency stop (1 micro MNQ)
        # a non-check minute does nothing
        assert (
            SS.run(
                s,
                rules=rules,
                clock=clock,
                calendar=lambda _d: [],
                symbol="MNQ",
                tf="1",
                at=today + timedelta(minutes=45),
            ).updates
            == []
        )
        # 11:00 check: price fell back below VWAP/band → EXIT
        for b in (
            s.query(Bar)
            .filter(Bar.close_time > today + timedelta(minutes=30), Bar.close_time <= today + timedelta(minutes=90))
            .all()
        ):
            b.c = b.o = D(19990)
            b.h, b.l = D(19991), D(19989)
        s.commit()
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=90)
        )
        assert out.exits == [(sig.id, "NOISE_TRAIL")]
        s.refresh(sig)
        assert sig.features["state"] == "CLOSED" and sig.features["exit_reason"] == "NOISE_TRAIL"


def test_noise_news_blackout_records_skip_and_flat_at_1600(db, loaded_rules):
    from app.engine.filters import NewsEvent

    rules = _rules(loaded_rules, noise=True)
    days = _sessions(12)
    today = days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    news = [NewsEvent(today + timedelta(minutes=32), "CPI")]
    with db() as s:
        _history(s, days[:-1])
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.commit()
        out = SS.run(
            s,
            rules=rules,
            clock=clock,
            calendar=lambda _d: news,
            symbol="MNQ",
            tf="1",
            at=today + timedelta(minutes=30),
        )
        assert out.updates[0].status == "SKIP" and out.updates[0].reason == "NEWS_BLACKOUT"
        g = s.query(SignalGate).filter_by(signal_id=out.updates[0].signal_id).one()
        assert not g.passed and g.detail["code"] == "NEWS_BLACKOUT"
        # an OPEN signal is flattened on the 16:00 bar
        sig = s.query(Signal).filter(Signal.model_key.like("MNQ-NOISE-%")).first()
        sig.features = {**sig.features, "state": "OPEN"}
        s.commit()
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=390)
        )
        assert out.exits == [(sig.id, "NOISE_FLAT_1600")]


def test_strategy_off_or_wrong_feed_does_nothing(db, loaded_rules):
    rules = _rules(loaded_rules)  # noise off, open_drive off
    with db() as s:
        assert (
            SS.run(
                s,
                rules=rules,
                clock=FixedClock(DAY0),
                calendar=lambda _d: [],
                symbol="MNQ",
                tf="1",
                at=DAY0 + timedelta(minutes=30),
            ).updates
            == []
        )
        rules_on = _rules(loaded_rules, noise=True)
        assert (
            SS.run(
                s,
                rules=rules_on,
                clock=FixedClock(DAY0),
                calendar=lambda _d: [],
                symbol="MNQ",
                tf="5",
                at=DAY0 + timedelta(minutes=30),
            ).updates
            == []
        )
        assert (
            SS.run(
                s,
                rules=rules_on,
                clock=FixedClock(DAY0),
                calendar=lambda _d: [],
                symbol="MGC",
                tf="1",
                at=DAY0 + timedelta(minutes=30),
            ).updates
            == []
        )


def test_open_drive_signal_and_time_stop(db, loaded_rules):
    rules = _rules(loaded_rules, open_drive=True)
    days = _sessions(12)
    today = days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    with db() as s:
        for start in days[:-1]:  # 100-point daily ranges
            _add_day(s, start, {100: D(20050), 200: D(19950), 300: D(20000)})
        _add_day(s, today, {k: D(20000) + 2 * k for k in range(30)})  # +58 by 09:59 ≥ 0.35 × ~102
        s.commit()
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=30)
        )
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.features["strategy"] == "OPEN_DRIVE" and sig.features["paper_only"] is True
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert plan.mode == "OPEN_DRIVE" and plan.stop < plan.entry < plan.take_profit and plan.rr < 1
        assert datetime.fromisoformat(sig.features["entry_expires_at"]).astimezone(UTC).hour == 16  # 12:31 ET
        # only one per day
        assert (
            SS.run(
                s,
                rules=rules,
                clock=clock,
                calendar=lambda _d: [],
                symbol="MNQ",
                tf="1",
                at=today + timedelta(minutes=30),
            ).updates
            == []
        )
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=210)
        )  # 13:00 close
        assert out.exits == [(sig.id, "OD_TIME_STOP")]


def test_load_days_groups_rth_sessions(db):
    d0 = DAY0
    with db() as s:
        _add_day(s, d0, {})
        s.add(
            Bar(
                symbol="MNQ",
                tf="1",
                close_time=d0 - timedelta(hours=3),
                o=D(1),
                h=D(1),
                l=D(1),
                c=D(1),
                v=D(1),
                source="tradingview",
            )
        )  # pre-market bar ignored
        s.commit()
        days = SS.load_days(s, "MNQ", d0 + timedelta(hours=8))
        assert [x.day for x in days] == [date(2026, 10, 12).isoformat()] and len(days[0].bars) == 390


def test_ai_bias_trades_only_when_both_tools_agree(db, loaded_rules):
    from datetime import date

    from app.models import BiasDecision

    rules = _rules(loaded_rules, ai_bias=True)
    today = _sessions(2)[-1]
    sess = date(today.year, today.month, today.day)
    with db() as s:
        _add_day(s, today, {k: D(20000) for k in range(5)})  # bar k=0 closes at 09:30 + 1 min
        s.commit()
        at = today + timedelta(minutes=1)

        def go(label=None, when=at):
            if label:
                s.add(BiasDecision(session_date=sess, proxy="QQQ", raw_rating=label, mapped="NEUTRAL", version="t"))
                s.commit()
            return SS.run(s, rules=rules, clock=FixedClock(when), calendar=lambda _d: [], symbol="MNQ", tf="1", at=when)

        out = go()
        assert out.updates == []  # no AI call → no trade
        assert go("BUY·VT SHORT 85").updates == []  # tools disagree → no trade
        out = go("SELL·VT SHORT 85")  # both strongly SHORT
        assert len(out.updates) == 1
        sig = s.get(Signal, out.updates[0].signal_id)
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert sig.direction == "SHORT" and plan.mode == "AI_BIAS" and plan.stop > plan.entry


def test_pm_fade_fades_a_stretch_only_on_noise_free_days(db, loaded_rules):
    rules = _rules(loaded_rules, pm_fade=True)
    today = _sessions(2)[-1]
    k_sig = 211  # bar closing 13:02
    with db() as s:
        # flat at 20000 all morning, then a jump to 20100 at 13:01–13:02 → far above VWAP + 2 sd
        _add_day(s, today, {k: (D(20100) if k >= 210 else D(20000)) for k in range(212)})
        s.commit()
        at = today + timedelta(minutes=k_sig + 1)
        out = SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"
        sig = s.get(Signal, out.updates[0].signal_id)
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert sig.direction == "SHORT" and plan.mode == "PM_FADE" and plan.stop - plan.entry == D(124)
        assert plan.take_profit < plan.entry and sig.features["paper_only"] is True
        # one per day
        at2 = at + timedelta(minutes=1)
        assert (
            SS.run(s, rules=rules, clock=FixedClock(at2), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at2).updates
            == []
        )
        # flat at 15:55
        flat = today + timedelta(minutes=385)  # bar closing 15:55
        out = SS.run(s, rules=rules, clock=FixedClock(flat), calendar=lambda _d: [], symbol="MNQ", tf="1", at=flat)
        assert out.exits == [(sig.id, "FADE_FLAT_1555")]


def test_pm_fade_skips_when_noise_traded_or_target_too_close(db, loaded_rules):
    rules = _rules(loaded_rules, pm_fade=True)
    d1, d2 = _sessions(3)[-2:]
    with db() as s:
        _add_day(s, d1, {k: (D(20100) if k >= 210 else D(20000)) for k in range(212)})
        s.add(
            Signal(
                symbol="MNQ",
                profile="TIGHT",
                direction="LONG",
                model_key=f"MNQ-NOISE-{d1.date().isoformat()}-1",
                bar_time=d1,
                status="PASS",
                passed=True,
                features={"state": "CLOSED"},
                updated_at=d1,
            )
        )
        # tiny stretch: 0.5 pt above a VWAP of ~20000 with a tiny sd → target < 4 ticks away
        _add_day(s, d2, {k: (D("20000.75") if k >= 210 else D(20000)) for k in range(212)}, vol=D(100))
        s.commit()
        at = d1 + timedelta(minutes=212)
        assert (
            SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at).updates
            == []
        )
        at = d2 + timedelta(minutes=212)
        out = SS.run(s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        assert len(out.updates) == 1 and out.updates[0].status == "SKIP" and out.updates[0].reason == "TARGET_TOO_CLOSE"
        before = d2 + timedelta(minutes=100)  # outside 13:01–15:29 → nothing
        assert (
            SS.run(
                s, rules=rules, clock=FixedClock(before), calendar=lambda _d: [], symbol="MNQ", tf="1", at=before
            ).updates
            == []
        )
