"""Session 14: restart recovery (items 1, 2, 4), unique trade refs and exit confirmation."""

import asyncio
from datetime import timedelta
from decimal import Decimal as D

from fastapi.testclient import TestClient

from app.execution.adapters.base import BrokerError, Position
from app.execution.adapters.crosstrade import UnconfirmedError
from app.main import create_app, watchdog_once
from app.models import Account, Signal, Trade
from tests.integration.test_all_stages import run
from tests.integration.test_signals_flow import MIN, MS, hb


def restart(authed, clock):
    """A second process on the same database (what `make dev` does after a crash / redeploy)."""
    return create_app(authed.app.state.settings, clock)


def open_trade(authed, clock):
    aid, res = run(authed, clock, "EVAL")
    assert res[0]["ok"], res
    return aid, res[0]["trade_ref"]


def test_trade_ref_is_deterministic_and_stored_with_snapshot(authed, clock):
    aid, ref = open_trade(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        row = s.query(Trade).one()
        assert ref == f"P-{sig.id}-{aid}" == row.trade_ref
        assert row.om_state and row.om_state["trade_id"] == ref and row.om_state["legs"][0]["bracket_id"]


def test_paper_restart_mid_trade_rebuilds_and_books_pnl(authed, clock):
    _aid, ref = open_trade(authed, clock)
    app2 = restart(authed, clock)
    with TestClient(app2):
        ctl = app2.state.controller
        assert ref in ctl.om.trades and ctl.om.trades[ref].legs[0].entry is not None
        pos = _first_pos(ctl)
        assert pos and pos[0].qty != 0
        # the next bar reaches the target: the rebuilt trade closes and books its P&L on the same row
        asyncio.run(ctl.on_bar("MNQ", D(20071), D(20071), D(20071), D(20071), clock.now()))
        with app2.state.sessionmaker() as s:
            row = s.query(Trade).one()
            assert row.closed_at is not None and row.exit_reason == "TP" and row.pnl_usd > 0
        assert ref not in ctl.om.trades


def _first_pos(ctl):
    return asyncio.run(ctl.adapter.get_positions(next(iter(ctl.adapter.sim.accounts))))


def legacy(aid, sid, clock, closed):
    return Trade(
        account_id=aid, signal_id=sid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), risk_usd=D(1),
        opened_at=clock.now(), closed_at=clock.now() if closed else None, trade_ref="T1",
    )  # fmt: skip


def test_restart_then_two_more_trades_never_collide(authed, clock):
    """Refs restarted at T1 after every restart; lookups then raised MultipleResultsFound and P&L was lost."""
    aid, ref = open_trade(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        for i in range(2):  # legacy rows from earlier processes, same ref
            s.add(legacy(aid, sig.id, clock, closed=True))
        s.add(legacy(aid, sig.id, clock, closed=False))
        s.commit()
    ctl = authed.app.state.controller
    with authed.app.state.sessionmaker() as s:
        assert ctl._trade_row(s, "T1").closed_at is None  # newest OPEN one, never an exception
        assert ctl._trade_row(s, "nope") is None
    hb(authed, clock, MS - MIN, close="20071")  # TP hit: closes through _trade_row without raising
    with authed.app.state.sessionmaker() as s:
        assert s.query(Trade).filter(Trade.trade_ref == ref).one().exit_reason == "TP"


def test_legacy_open_row_without_snapshot_is_closed_sim_restart(authed, clock):
    _aid, _ref = open_trade(authed, clock)
    with authed.app.state.sessionmaker() as s:
        s.query(Trade).one().om_state = None
        s.commit()
    app2 = restart(authed, clock)
    with TestClient(app2):
        assert app2.state.controller.om.trades == {}
    with authed.app.state.sessionmaker() as s:
        assert s.query(Trade).one().exit_reason == "SIM_RESTART"


# ---------- live (CrossTrade-like) accounts ----------
class FakeLive:
    name = "fake"
    capabilities = frozenset()

    def __init__(self, positions=None, orders=None, fail=False):
        self.positions, self.orders, self.fail, self.flattened = positions or [], orders or [], fail, []

    async def get_positions(self, acct):
        if self.fail:
            raise BrokerError("down")
        return self.positions

    async def get_orders(self, acct):
        return self.orders

    async def flatten(self, acct):
        self.flattened.append(acct)
        self.positions = []


def make_live_row(authed, clock):
    """Turn the paper trade into a LIVE-account trade the way a real one is stored."""
    aid, ref = open_trade(authed, clock)
    with authed.app.state.sessionmaker() as s:
        a = s.get(Account, aid)
        a.is_sim, a.broker_account_id = False, "LIVE1"
        row = s.query(Trade).one()
        row.om_state = {**row.om_state, "account": "LIVE1"}
        qty = sum(x["qty"] for x in row.om_state["legs"])
        s.commit()
    return aid, ref, qty


def recover_with(authed, clock, fake):
    app2 = restart(authed, clock)
    cm = TestClient(app2)
    cm.__enter__()
    ctl = app2.state.controller
    ctl.adapter.set_live(fake, {"LIVE1"}, lambda: True)
    asyncio.run(ctl.recover_open_trades())
    return app2, ctl, cm


def test_live_restart_with_matching_position_is_rebuilt(authed, clock):
    _, ref, qty = make_live_row(authed, clock)
    _app2, ctl, cm = recover_with(authed, clock, FakeLive([Position("LIVE1", "MNQ", qty, D(20000))]))
    try:
        assert ref in ctl.om.trades and not ctl.om.trades[ref].closing
    finally:
        cm.__exit__(None, None, None)


def test_live_restart_re_registers_bracket_order_roles(authed, clock):
    """Review fix: a live adapter keeps its order-id -> role map in memory; recovery hands it back every open leg's
    bracket / stop / take-profit ids so the stop or target fill after a restart is booked on its trade."""
    _, ref, qty = make_live_row(authed, clock)
    fake = FakeLive([Position("LIVE1", "MNQ", qty, D(20000))])
    fake.registered = []
    fake.register_bracket = lambda b, st, tp: fake.registered.append((b, st, tp))
    _app2, ctl, cm = recover_with(authed, clock, fake)
    try:
        legs = [x for x in ctl.om.trades[ref].legs if not x.closed]
        assert fake.registered == [(x.bracket_id, x.stop_order_id, x.tp_order_id) for x in legs]
        assert all(b and st and tp for b, st, tp in fake.registered)  # the snapshot now carries the TP order id
    finally:
        cm.__exit__(None, None, None)


def test_live_restart_flat_at_broker_closes_as_unverified_after_grace(authed, clock):
    _, ref, _ = make_live_row(authed, clock)
    app2, ctl, cm = recover_with(authed, clock, FakeLive([]))
    try:
        assert ctl.om.trades[ref].closing == "RESTART_FLAT"
        clock.advance(timedelta(seconds=61))
        asyncio.run(ctl.retry_closing())
        assert any("P&L unverified" in n["title"] for n in ctl.notices)
        with app2.state.sessionmaker() as s:
            assert s.query(Trade).one().exit_reason == "RESTART_FLAT"
    finally:
        cm.__exit__(None, None, None)


def test_live_restart_with_unmanaged_position_flattens_pauses_and_banners(authed, clock):
    aid, _ref, qty = make_live_row(authed, clock)
    with authed.app.state.sessionmaker() as s:
        s.query(Trade).one().om_state = None  # nothing to match it with
        s.commit()
    fake = FakeLive([Position("LIVE1", "MNQ", qty, D(20000))])
    app2, ctl, cm = recover_with(authed, clock, fake)
    try:
        assert fake.flattened == ["LIVE1"]
        with app2.state.sessionmaker() as s:
            assert s.get(Account, aid).paused_reason == "RESTART_UNMANAGED"
        assert any(n["title"] == "Restart found an unmanaged position" for n in ctl.notices)
    finally:
        cm.__exit__(None, None, None)


def test_live_restart_unreadable_broker_blocks_and_retries(authed, clock):
    aid, ref, qty = make_live_row(authed, clock)
    fake = FakeLive([Position("LIVE1", "MNQ", qty, D(20000))], fail=True)
    app2, ctl, cm = recover_with(authed, clock, fake)
    try:
        with app2.state.sessionmaker() as s:
            assert s.get(Account, aid).paused_reason == "RESTART_UNVERIFIED"
        assert ref in ctl.om.trades  # still managed from the snapshot
        assert any("could not read the broker" in n["title"] for n in ctl.notices)
        fake.fail = False
        asyncio.run(ctl.retry_recovery())
        assert not ctl._recovery_pending
    finally:
        cm.__exit__(None, None, None)


# ---------- exit confirmation (item 2) and failed exits (bug B) ----------
def mark_exit(authed, reason="NOISE_TEST"):
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        sig.features = {**sig.features, "state": "OPEN", "exit_requested": {"reason": reason, "at": "x"}}
        s.commit()
        return sig.id


def sig_state(authed):
    with authed.app.state.sessionmaker() as s:
        return s.query(Signal).one().features.get("state")


def test_failed_strategy_exit_is_announced_retried_and_signal_closes_only_when_flat(authed, clock):
    _aid, ref = open_trade(authed, clock)
    sid = mark_exit(authed)
    ctl = authed.app.state.controller
    clock.advance(timedelta(seconds=30))  # past the 6 s hold
    ctl.adapter.sim.fail_next.add("flatten")
    assert asyncio.run(ctl.strategy_exit(sid, "NOISE_TEST")) == 0
    assert any(n["title"].startswith("Exit order failed") for n in ctl.notices)
    assert ref in ctl.om.trades and sig_state(authed) == "OPEN"
    assert ctl._pending_exits[ref] == "NOISE_TEST"
    asyncio.run(watchdog_once(authed.app))  # watchdog retries: now it goes through
    with authed.app.state.sessionmaker() as s:
        row = s.query(Trade).one()
        assert row.closed_at is not None and row.exit_reason == "NOISE_TEST"
    assert sig_state(authed) == "CLOSED"
    assert authed.app.state.controller.om.trades == {}


def test_exit_marker_survives_restart_and_is_reissued(authed, clock):
    _aid, ref = open_trade(authed, clock)
    mark_exit(authed)
    clock.advance(timedelta(seconds=30))
    app2 = restart(authed, clock)
    with TestClient(app2):
        ctl = app2.state.controller
        assert ref in ctl.om.trades
        asyncio.run(watchdog_once(app2))
        with app2.state.sessionmaker() as s:
            assert s.query(Trade).one().exit_reason == "NOISE_TEST"
            assert s.query(Signal).one().features["state"] == "CLOSED"


def test_exit_marker_without_open_trade_closes_signal(authed, clock):
    open_trade(authed, clock)
    sid = mark_exit(authed)
    asyncio.run(authed.app.state.controller.flatten_all("t"))  # trade is gone, signal still says OPEN
    with authed.app.state.sessionmaker() as s:
        sg = s.get(Signal, sid)
        sg.features = {**sg.features, "state": "OPEN"}
        s.commit()
    asyncio.run(authed.app.state.controller.exit_watchdog())
    assert sig_state(authed) == "CLOSED"


def test_exit_pending_shows_on_positions_and_safety(authed, clock):
    open_trade(authed, clock)
    mark_exit(authed)
    pos = authed.get("/api/positions").json()["accounts"][0]["positions"][0]
    assert pos["exit_pending"] == "NOISE_TEST"
    assert authed.get("/api/safety").json()["pending_exits"][0]["reason"] == "NOISE_TEST"


# ---------- duplicate order guard (item 4) ----------
def test_unconfirmed_place_pauses_account_and_never_places_twice(authed, clock):
    aid, _ref = open_trade(authed, clock)
    ctl = authed.app.state.controller
    asyncio.run(ctl.flatten_all("t"))
    calls = []
    sim = ctl.adapter.sim
    orig = sim.place_bracket

    async def boom(acct, req):
        calls.append(req.client_id)
        raise UnconfirmedError("500 outcome unknown")

    sim.place_bracket = boom
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        sig.status = "PASS"
        s.query(Trade).delete()
        from app.models import Order

        s.query(Order).delete()
        s.commit()
        sid = sig.id
    res = asyncio.run(ctl.execute(sid, "automation"))
    assert not res[0].ok and res[0].reason == "ORDER_FAILED" and calls == [f"P-{sid}-{aid}-ONLY"]
    with authed.app.state.sessionmaker() as s:
        assert s.get(Account, aid).paused_reason == "ORDER_REJECTS"
    res = asyncio.run(ctl.execute(sid, "automation"))  # next heartbeat: the paused account is not tried again
    assert len(calls) == 1
    sim.place_bracket = orig
