"""D55 strategy runtime: NOISE / fade / AI signals and exits from stored 1-minute bars (D107: no OPEN_DRIVE)."""

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
    st = r.strategy.model_copy(update=strategy)
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
    rules = _rules(loaded_rules)  # noise off
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
        assert plan.take_profit < plan.entry and sig.features["paper_only"] is False
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


def test_pm_fade_respects_the_noise_weekday_skip(db, loaded_rules):  # D132 (B2): Mondays off for the fade too
    monday = DAY0
    assert monday.weekday() == 0
    with db() as s:
        _add_day(s, monday, {k: (D(20100) if k >= 210 else D(20000)) for k in range(212)})
        s.commit()
        at = monday + timedelta(minutes=212)
        for skip, n in (([0], 0), ([], 1)):
            r = _rules(loaded_rules, pm_fade=True)
            nc = r.strategy.noise_cfg.model_copy(update={"skip_weekdays": skip})
            r = r.model_copy(update={"strategy": r.strategy.model_copy(update={"noise_cfg": nc})})
            out = SS.run(s, rules=r, clock=FixedClock(at), calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
            assert len(out.updates) == n, skip


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


def test_exit_keeps_signal_open_with_marker_while_a_trade_is_open(db, loaded_rules):
    """Session 14: a strategy exit is only REQUESTED; the signal turns CLOSED when the trade really closes."""
    from app.models import Account, Trade

    rules = _rules(loaded_rules, noise=True)
    days = _sessions(12)
    today = days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    with db() as s:
        _history(s, days[:-1])
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.commit()
        at = today + timedelta(minutes=30)
        out = SS.run(s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        sig = s.get(Signal, out.updates[0].signal_id)
        # replaying the same bar never decides a second entry; exits_only never enters at all
        again = SS.run(s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        assert again.updates == []
        a = Account(broker_account_id="A", label="A", stage="EVAL", drawdown_type="eod", starting_balance=D(25000))
        s.add(a)
        s.flush()
        s.add(Trade(account_id=a.id, signal_id=sig.id, symbol="MNQ", direction="LONG", qty=1, entry=D(1), risk_usd=D(1),
                    opened_at=at, trade_ref="P-1-1"))  # fmt: skip
        s.commit()
        SS._close(s, sig, "NOISE_TRAIL", at, clock)
        assert sig.features["state"] == "OPEN" and sig.features["exit_requested"]["reason"] == "NOISE_TRAIL"
        SS._close(s, sig, "OTHER", at, clock)  # a later request never overwrites the first marker
        assert sig.features["exit_requested"]["reason"] == "NOISE_TRAIL"


def test_exits_only_replay_never_opens_a_position(db, loaded_rules):
    rules = _rules(loaded_rules, noise=True)
    days = _sessions(12)
    today = days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    with db() as s:
        _history(s, days[:-1])
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.commit()
        out = SS.run(
            s,
            rules=rules,
            clock=clock,
            calendar=lambda _d: [],
            symbol="MNQ",
            tf="1",
            at=today + timedelta(minutes=30),
            exits_only=True,
        )
        assert out.updates == [] and s.query(Signal).count() == 0


def test_noise_skip_weekdays_blocks_new_entries(db, loaded_rules):
    """D123: no new NOISE entry on a configured New York weekday (default plans: Monday)."""
    days = _sessions(12)
    hist, today = days[:-1], days[-1]
    base = _rules(loaded_rules, noise=True)
    ncfg = base.strategy.noise_cfg.model_copy(update={"skip_weekdays": [today.weekday()]})
    rules = base.model_copy(update={"strategy": base.strategy.model_copy(update={"noise_cfg": ncfg})})
    clock = FixedClock(today + timedelta(minutes=30))
    with db() as s:
        _history(s, hist)
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.commit()
        out = SS.run(
            s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=today + timedelta(minutes=30)
        )
        assert out.updates == []
    with pytest.raises(ValueError, match="skip_weekdays"):
        type(ncfg)(skip_weekdays=[5])


def _noise_long_at_1000(db, loaded_rules, later_closes):
    rules = _rules(loaded_rules, noise=True)
    days = _sessions(12)
    today = days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    cal = lambda _d: []  # noqa: E731
    with db() as s:
        _history(s, days[:-1])
        _add_day(s, today, {**{k: D(20200) for k in range(30)}, **later_closes})
        s.commit()
        at = today + timedelta(minutes=30)
        out = SS.run(s, rules=rules, clock=clock, calendar=cal, symbol="MNQ", tf="1", at=at)
        sig = s.get(Signal, out.updates[0].signal_id)
    return rules, today, clock, cal, sig.id


def test_broker_exit_closes_the_noise_signal_so_the_next_check_can_re_enter(db, loaded_rules):
    """A (H2): a broker STOP/TP close (no exit_requested marker) must turn the signal CLOSED, else NOISE holds a phantom."""
    from types import SimpleNamespace

    from app.automation.controller import Controller
    from app.models import Account, Trade

    later = {k: D(20200) for k in range(30, 150)}
    rules, today, clock, cal, sid = _noise_long_at_1000(db, loaded_rules, later)
    with db() as s:
        a = Account(broker_account_id="A", label="A", stage="EVAL", drawdown_type="eod", starting_balance=D(25000))
        s.add(a)
        s.flush()
        s.add(Trade(account_id=a.id, signal_id=sid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), risk_usd=D(1),
                    opened_at=today, closed_at=today, trade_ref="P-9-1"))  # fmt: skip
        s.flush()
        Controller._mark_signal_closed(SimpleNamespace(clock=clock), s, sid, "STOP")
        sig = s.get(Signal, sid)
        assert sig.features["state"] == "CLOSED" and sig.features["exit_reason"] == "STOP"
        s.commit()
        out = SS.run(s, rules=rules, clock=clock, calendar=cal, symbol="MNQ", tf="1", at=today + timedelta(minutes=150))
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"  # re-entry after the broker exit


def test_same_direction_exit_and_reentry_is_a_hold_that_still_counts_the_entry(db, loaded_rules):
    """A: upper < close < VWAP gives EXIT then ENTER LONG; with the exit fill pending that re-entry would hit
    POSITION_OPEN. It is merged into HOLD (no exit, no second signal) but counts toward max entries."""
    later = {k: D(20060) for k in range(30, 150)}
    rules, today, clock, cal, sid = _noise_long_at_1000(db, loaded_rules, later)
    with db() as s:
        out = SS.run(s, rules=rules, clock=clock, calendar=cal, symbol="MNQ", tf="1", at=today + timedelta(minutes=90))
        assert out.exits == [] and out.updates == []
        sig = s.get(Signal, sid)
        assert sig.features["state"] == "OPEN" and "exit_requested" not in sig.features
        assert sig.features["merged_entries"] == 1
        sigs = SS._today_signals(s, "MNQ", "NOISE", today.astimezone(SS.ET).date().isoformat())
        assert SS.noise_entries_today(sigs) == 2


def test_one_runner_exception_keeps_the_other_strategies_exits(db, loaded_rules, monkeypatch):
    """D (M5): a crashing runner is isolated (savepoint), reported in out.errors, and never discards NOISE's exit."""
    rules = _rules(loaded_rules, noise=True, candace_ict=True)
    days = _sessions(12)
    today = days[-1]
    clock = FixedClock(today + timedelta(minutes=30))
    cal = lambda _d: []  # noqa: E731
    with db() as s:
        _history(s, days[:-1])
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.commit()
        out = SS.run(s, rules=rules, clock=clock, calendar=cal, symbol="MNQ", tf="1", at=today + timedelta(minutes=30))
        sig = s.get(Signal, out.updates[0].signal_id)
        for b in (
            s.query(Bar)
            .filter(Bar.close_time > today + timedelta(minutes=30), Bar.close_time <= today + timedelta(minutes=90))
            .all()
        ):
            b.c = b.o = D(19990)
            b.h, b.l = D(19991), D(19989)
        s.commit()

        def boom(*_a, **_k):
            raise RuntimeError("candace exploded")

        monkeypatch.setattr(SS, "run_candace_ict", boom)
        out = SS.run(s, rules=rules, clock=clock, calendar=cal, symbol="MNQ", tf="1", at=today + timedelta(minutes=90))
        assert out.exits == [(sig.id, "NOISE_TRAIL")]
        assert [(e[0], e[1]) for e in out.errors] == [("run_candace_ict", "RuntimeError")]
        s.refresh(sig)
        assert sig.features["state"] == "CLOSED"  # the NOISE exit marker was committed


def test_noise_flat_fires_on_the_first_bar_at_or_after_1600(db, loaded_rules):
    """E: the 16:00 bar is missing (heartbeat gap); the 16:01 bar still flattens the open NOISE position."""
    later = {k: D(20200) for k in range(30, 390)}
    rules, today, clock, cal, sid = _noise_long_at_1000(db, loaded_rules, later)
    with db() as s:
        s.query(Bar).filter(Bar.close_time == today + timedelta(minutes=390)).delete()  # the 16:00 bar never came
        s.add(Bar(symbol="MNQ", tf="1", close_time=today + timedelta(minutes=391), o=D(20200), h=D(20201),
                  l=D(20199), c=D(20200), v=D(100), source="tradingview"))  # fmt: skip
        s.commit()
        out = SS.run(s, rules=rules, clock=clock, calendar=cal, symbol="MNQ", tf="1", at=today + timedelta(minutes=391))
        assert out.exits == [(sid, "NOISE_FLAT_1600")]


def test_late_day_flat_fires_on_the_first_bar_at_or_after_1559(db, loaded_rules):
    """E: no 15:59 bar stored; the 16:00 bar flattens the late-day leg (and the exact bar still does)."""
    from app.engine import late_day as LD

    rules = _rules(loaded_rules, fast_pass_late_day=True)
    today = _sessions(12)[-1]
    clock = FixedClock(today + timedelta(minutes=390))
    with db() as s:
        sig = SS._new_signal(s, clock, symbol="MNQ", key=f"MNQ-LATE-{today.astimezone(SS.ET).date().isoformat()}-1500",
                             direction=SS.Direction.LONG, at=today, gate=(True, "OK", ""), features={},
                             plan=("LATE_DAY", D(20000), D(19940), D(20120), D(60), D(2)), rules=rules)  # fmt: skip
        s.commit()
        cfg = rules.strategy.late_day_cfg
        assert LD.is_flat_time(today + timedelta(minutes=389), cfg)  # 15:59
        assert LD.is_flat_time(today + timedelta(minutes=390), cfg)  # 16:00: first bar after a missing 15:59
        assert not LD.is_flat_time(today + timedelta(minutes=388), cfg)
        out = SS.run_late_day(s, rules, clock, lambda _d: [], today + timedelta(minutes=390))
        assert out.exits == [(sig.id, "LATE_FLAT_1559")]
