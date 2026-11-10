"""D82 / D75-P1 profit lock: pure helpers + order-manager wiring + snapshot round trip."""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.trade_plan import Direction, TradePlan
from app.execution import trade_state
from app.execution.adapters.sim import SimAdapter, SimInstrument
from app.execution.order_manager import OrderManager
from app.management.profit_lock import PROFIT_LOCK_REASON, lock_stop, lock_triggered

AT = datetime(2026, 11, 5, 15, tzinfo=UTC)
T, TV = D("0.25"), D("0.50")
WIN = (D(19000), D(21000), D(1), D(100), 4, 20)


def test_lock_triggered_long_and_short():
    assert lock_triggered(Direction.LONG, D(20000), D(20100), D(100))
    assert not lock_triggered(Direction.LONG, D(20000), D("20099.75"), D(100))
    assert lock_triggered(Direction.SHORT, D(20000), D(19900), D(100))
    assert not lock_triggered(Direction.SHORT, D(20000), D("19900.25"), D(100))


def test_lock_stop_levels_and_none_before_trigger():
    assert lock_stop(Direction.LONG, D(20000), D(20120), D(100), D(10), T) == D(20010)
    assert lock_stop(Direction.SHORT, D(20000), D(19880), D(100), D(10), T) == D(19990)
    assert lock_stop(Direction.LONG, D(20000), D(20050), D(100), D(10), T) is None
    assert lock_stop(Direction.SHORT, D(20000), D(19990), D(100), D(10), T) is None
    # rounds toward entry (never claims more than configured)
    assert lock_stop(Direction.LONG, D(20000), D(20200), D(100), D("10.1"), T) == D("20010.00")
    assert lock_stop(Direction.SHORT, D(20000), D(19800), D(100), D("10.1"), T) == D("19990.00")


@pytest.fixture
def env():
    sim = SimAdapter(FixedClock(AT), {"MNQ": SimInstrument(T, TV, D("1.00"))}, slippage_ticks=0)
    sim.add_account("A", D(150000))
    sim.last["MNQ"] = D(20000)
    return sim, OrderManager(sim)


async def pump(sim, om, o, h, lo, c):
    events = []
    for f in sim.on_bar("MNQ", D(o), D(h), D(lo), D(c), AT):
        events += await om.on_fill(f)
    events += await om.on_bar("MNQ", D(h), D(lo))
    return events


async def open_noise(sim, om, direction=Direction.LONG, lock=(D(100), D(10))):
    s = direction.sign
    stop, tp = D(20000) - s * D(124), D(20000) + s * D(2000)
    plan = TradePlan(direction, D(20000), stop, tp, D(124), D("16.13"), mode="NOISE")
    t = await om.open_trade("A", "MNQ", plan, 3, False, T, TV, AT, WIN)
    t.strategy, t.profit_lock = "NOISE", lock
    for f in sim.drain_fills():
        await om.on_fill(f)
    return t


async def test_stop_moves_after_trigger_and_locked_exit_is_reported(env):
    sim, om = env
    t = await open_noise(sim, om)
    ev = await pump(sim, om, 20000, 20060, 19990, 20050)  # +60: no lock yet
    assert [e.kind for e in ev] == [] and not t.profit_locked and t.legs[0].stop == D(19876)
    ev = await pump(sim, om, 20050, 20105, 20040, 20100)  # +105 → stop to entry + 10
    assert [(e.kind, e.detail) for e in ev] == [("STOP_MOVED", "PROFIT_LOCK 20010.00")]
    assert t.profit_locked and t.legs[0].stop == D(20010)
    assert await pump(sim, om, 20100, 20150, 20090, 20140) == []  # ratchet: nothing looser, nothing new
    ev = await pump(sim, om, 20140, 20141, 20000, 20005)  # falls through the locked stop
    closed = [e for e in ev if e.kind == "CLOSED"]
    assert closed and closed[0].detail == PROFIT_LOCK_REASON and closed[0].trade.pnl() > 0


async def test_short_side_lock(env):
    sim, om = env
    t = await open_noise(sim, om, Direction.SHORT)
    ev = await pump(sim, om, 20000, 20010, 19890, 19900)
    assert [(e.kind, e.detail) for e in ev] == [("STOP_MOVED", "PROFIT_LOCK 19990.00")]
    assert t.legs[0].stop == D(19990)


async def test_plain_stop_is_not_reported_as_lock_and_no_lock_without_config(env):
    sim, om = env
    await open_noise(sim, om, lock=None)
    ev = await pump(sim, om, 20000, 20150, 19990, 20100)  # +150 but no lock configured
    assert ev == []
    ev = await pump(sim, om, 20100, 20100, 19870, 19880)  # original stop 19876 hit
    assert [e.detail for e in ev if e.kind == "CLOSED"] == ["STOP"]


async def test_stop_modify_failure_flattens_and_pauses(env):
    sim, om = env
    await open_noise(sim, om)
    sim.fail_next.add("modify_stop")
    ev = await pump(sim, om, 20000, 20105, 19990, 20100)
    assert ("PAUSE", "STOP_MODIFY_FAILED") in [(e.kind, e.detail) for e in ev]


async def test_snapshot_round_trip_keeps_the_lock(env):
    sim, om = env
    t = await open_noise(sim, om)
    await pump(sim, om, 20000, 20105, 19990, 20100)
    back = trade_state.load(trade_state.dump(t))
    assert back.profit_lock == (D(100), D(10)) and back.profit_locked and back == t
    old = trade_state.dump(t)
    del old["profit_lock"], old["profit_locked"]  # snapshot written before D82
    legacy = trade_state.load(old)
    assert legacy.profit_lock is None and legacy.profit_locked is False
