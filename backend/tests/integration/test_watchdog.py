"""Wall-clock safety watchdog, hard flat, deferred exit fills and orphaned positions (no webhook needed)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.automation import state as stt
from app.execution.adapters.base import BrokerError, Fill
from app.main import _watchdog, watchdog_once
from app.models import Account, Trade
from tests.integration.test_all_stages import run

FLAT = datetime(2026, 11, 5, 21, 41, tzinfo=UTC)  # 16:41 ET: after the 16:40 auto-flatten
HARD = datetime(2026, 11, 5, 21, 44, 30, tzinfo=UTC)  # 16:44:30 ET: after the 16:44 hard flat


def positions(authed):
    return authed.get("/api/positions").json()["accounts"][0]["positions"]


def trade_row(authed) -> Trade:
    with authed.app.state.sessionmaker() as s:
        return s.query(Trade).one()


def test_watchdog_flattens_without_any_webhook(authed, clock):
    _, res = run(authed, clock, "EVAL")
    assert res[0]["ok"] and positions(authed)
    clock.set(FLAT)  # the feed is dead: only wall-clock time passes
    asyncio.run(watchdog_once(authed.app))
    assert positions(authed) == []
    assert trade_row(authed).exit_reason == "FLAT_TIME"


def test_flat_time_flattens_untracked_broker_positions(authed, clock):
    run(authed, clock, "EVAL")
    ctl = authed.app.state.controller
    ctl.om.trades.clear()  # e.g. after a restart: the broker holds a position we do not track
    clock.set(FLAT)
    assert asyncio.run(ctl.flat_time_check()) == "FLAT_TIME"
    assert positions(authed) == []


def test_flat_time_is_quiet_when_flat_or_outside_window(authed, clock):
    ctl = authed.app.state.controller
    authed.post("/api/accounts", json={"label": "E", "stage": "EVAL"})
    clock.set(FLAT)
    assert asyncio.run(ctl.flat_time_check()) is None  # flat, nothing tracked
    clock.set(datetime(2026, 11, 5, 15, tzinfo=UTC))
    assert asyncio.run(ctl.flat_time_check()) is None  # 10:00 ET


def test_failed_auto_flatten_is_retried_next_tick(authed, clock):
    run(authed, clock, "EVAL")
    ctl = authed.app.state.controller
    ctl.adapter.sim.fail_next.add("flatten")
    clock.set(FLAT)
    asyncio.run(watchdog_once(authed.app))
    assert positions(authed)  # still open
    assert any(n["title"].startswith("FLATTEN FAILED") for n in ctl.notices)
    asyncio.run(watchdog_once(authed.app))
    assert positions(authed) == []
    assert trade_row(authed).exit_reason == "FLAT_TIME"


def test_hard_flat_failure_pauses_account_and_retries(authed, clock):
    aid, _ = run(authed, clock, "EVAL")
    ctl = authed.app.state.controller
    ctl.adapter.sim.fail_next.add("flatten")
    clock.set(HARD)
    assert asyncio.run(ctl.flat_time_check()) == "HARD_FLAT"
    assert positions(authed)
    with authed.app.state.sessionmaker() as s:
        assert s.get(Account, aid).paused_reason == "FLATTEN_FAILED"
    n = len([x for x in ctl.notices if x["level"] == "error"])
    asyncio.run(ctl.flat_time_check())  # retry succeeds, no second banner, pause stays (never auto-resumes)
    assert positions(authed) == []
    assert trade_row(authed).exit_reason == "HARD_FLAT"
    assert len([x for x in ctl.notices if x["level"] == "error"]) == n
    with authed.app.state.sessionmaker() as s:
        assert s.get(Account, aid).paused_reason == "FLATTEN_FAILED"


def test_watchdog_runs_news_and_monitor(authed, clock):
    from app.engine.filters import NewsEvent

    run(authed, clock, "EVAL")
    authed.app.state.calendar = lambda d: [NewsEvent(at=clock.now() + timedelta(minutes=1), title="CPI")]
    asyncio.run(watchdog_once(authed.app))
    assert positions(authed) == []
    assert trade_row(authed).exit_reason == "NEWS"


def test_watchdog_survives_calendar_and_step_errors(authed, clock):
    ctl = authed.app.state.controller

    def boom(d):
        raise RuntimeError("x")

    authed.app.state.calendar = boom
    asyncio.run(watchdog_once(authed.app))
    assert any("calendar" in n["title"] for n in ctl.notices)

    async def bad() -> None:
        raise RuntimeError("x")

    ctl.monitor_accounts = bad  # type: ignore[method-assign]
    asyncio.run(ctl.watchdog_tick(None))
    assert any(n["title"] == "Safety watchdog step failed" for n in ctl.notices)


def test_watchdog_loop_runs_and_reports_failures(authed, clock):
    app = authed.app
    app.state.settings.watchdog_interval_s = 0.01
    calls = {"n": 0}

    async def tick(events) -> None:
        calls["n"] += 1
        raise RuntimeError("boom")

    app.state.controller.watchdog_tick = tick
    app.state.calendar = lambda d: []

    async def go() -> None:
        t = asyncio.create_task(_watchdog(app))
        await asyncio.sleep(0.1)
        t.cancel()

    asyncio.run(go())
    assert calls["n"] >= 2 and any(n["title"] == "Safety watchdog failed" for n in app.state.controller.notices)


def _defer_flatten(ctl):
    """CrossTrade-like: flatten is accepted but the exit fill only arrives later."""
    sim = ctl.adapter.sim

    async def noop(acct):
        return None

    sim.flatten = noop
    return sim


def test_flatten_keeps_trade_closing_until_exit_fill_then_books_real_pnl(authed, clock):
    aid, _ = run(authed, clock, "EVAL")
    ctl = authed.app.state.controller
    _defer_flatten(ctl)
    asyncio.run(ctl.flatten(aid, "tester", "MANUAL_FLATTEN"))
    row = trade_row(authed)
    assert row.closed_at is None and row.pnl_usd is None  # not booked as 0
    (t,) = ctl.om.trades.values()
    assert t.closing == "MANUAL_FLATTEN"
    with authed.app.state.sessionmaker() as s:
        before = stt.day_stats(s, s.get(Account, aid), clock.now()).consecutive_losses
    entry = t.legs[0].entry
    fill = Fill("x", "o1", None, "EXTERNAL", "MNQ", "SELL", t.qty, entry - D(5), clock.now(), D(1))

    async def deliver() -> None:
        with authed.app.state.sessionmaker() as s:
            await ctl._handle_events(s, await ctl.om.on_fill(fill))
            s.commit()

    # fill for another account is ignored
    other = Fill("other", "o2", None, "EXTERNAL", "MNQ", "SELL", t.qty, entry, clock.now())
    assert asyncio.run(ctl.om.on_fill(other)) == []
    fill = Fill(t.account, "o1", None, "EXTERNAL", "MNQ", "SELL", t.qty, entry - D(5), clock.now(), D(1))
    asyncio.run(deliver())
    row = trade_row(authed)
    assert row.exit_reason == "MANUAL_FLATTEN" and row.pnl_usd < 0 and row.exit == entry - D(5)
    assert not ctl.om.trades
    with authed.app.state.sessionmaker() as s:
        ds = stt.day_stats(s, s.get(Account, aid), clock.now())
        assert ds.consecutive_losses == before + 1 and ds.day_profit == row.pnl_usd


def test_missing_exit_fill_is_closed_after_grace_with_error_alert(authed, clock):
    aid, _ = run(authed, clock, "EVAL")
    ctl = authed.app.state.controller
    sim = _defer_flatten(ctl)
    asyncio.run(ctl.flatten(aid, "tester"))
    asyncio.run(ctl.retry_closing())  # still in the market → flatten requested again, trade still tracked
    assert ctl.om.trades and trade_row(authed).closed_at is None

    async def flat(acct):
        return []

    sim.get_positions = flat  # broker is flat but no fill was ever seen
    asyncio.run(ctl.retry_closing())
    assert ctl.om.trades  # inside the grace period
    clock.set(clock.now() + timedelta(seconds=61))
    asyncio.run(ctl.retry_closing())
    assert not ctl.om.trades and trade_row(authed).closed_at is not None
    assert any(n["title"].startswith("Exit fill missing") for n in ctl.notices)

    async def broken(acct):
        raise BrokerError("down")

    sim.get_positions = broken
    asyncio.run(ctl.retry_closing())  # nothing closing; no crash


def test_failed_emergency_flatten_keeps_orphan_tracked_and_pauses(authed, clock):
    ctl = authed.app.state.controller
    sim = ctl.adapter.sim
    orig = sim.place_bracket

    async def lost_ack(acct, req):
        await orig(acct, req)
        raise BrokerError("timeout after submit")

    sim.place_bracket = lost_ack
    sim.fail_next.add("flatten")
    aid, res = run(authed, clock, "EVAL")
    assert res[0]["reason"] == "ORPHAN_POSITION"
    (t,) = ctl.om.trades.values()
    assert t.orphan and t.closing
    row = trade_row(authed)
    assert row.closed_at is None
    with authed.app.state.sessionmaker() as s:
        assert s.get(Account, aid).paused_reason == "ORPHAN_POSITION" and not s.get(Account, aid).armed
    assert any(n["level"] == "error" and "ORPHAN" in n["title"] for n in ctl.notices)
    sim.place_bracket = orig
    asyncio.run(watchdog_once(authed.app))  # watchdog keeps trying: flatten now succeeds
    asyncio.run(watchdog_once(authed.app))
    assert positions(authed) == []
    clock.set(clock.now() + timedelta(seconds=61))
    asyncio.run(watchdog_once(authed.app))
    assert not ctl.om.trades and trade_row(authed).closed_at is not None
