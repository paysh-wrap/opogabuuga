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
        assert float((plan.entry - plan.stop) / plan.entry) == pytest.approx(0.01, abs=1e-4)
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
