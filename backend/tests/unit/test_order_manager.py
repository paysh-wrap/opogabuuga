from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.engine.trade_plan import Direction, build_one_to_one_plan, build_trade_plan
from app.execution.adapters.base import BrokerError
from app.execution.adapters.sim import SimAdapter, SimInstrument
from app.execution.order_manager import OrderManager
from app.management.drawdown_guard import apply_guard

AT = datetime(2026, 11, 5, 15, tzinfo=UTC)
T, TV = D("0.25"), D("0.50")
WIN = (D(19981), D(20070), D(2), D(3), 4, 20)


@pytest.fixture
def env():
    clock = FixedClock(AT)
    sim = SimAdapter(clock, {"MNQ": SimInstrument(T, TV, D("1.00"))}, slippage_ticks=0)
    sim.add_account("A", D(25000))
    sim.last["MNQ"] = D(20000)
    return sim, OrderManager(sim), clock


async def pump(sim, om, o, h, lo, c):
    events = []
    for f in sim.on_bar("MNQ", D(o), D(h), D(lo), D(c), AT):
        events += await om.on_fill(f)
    events += await om.on_bar("MNQ", D(h), D(lo))
    return events


async def opened(sim, om, plan, n, guard):
    t = await om.open_trade("A", "MNQ", plan, n, guard, T, TV, AT, WIN)
    ev = []
    for f in sim.drain_fills():
        ev += await om.on_fill(f)
    return t, ev


async def test_guard_on_partial_breakeven_then_trailing_runner(env):
    sim, om, _ = env
    plan = apply_guard(build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20), T, 2)
    t, ev = await opened(sim, om, plan, 3, True)
    assert [(leg.name, leg.qty, leg.take_profit) for leg in t.legs] == [("A", 2, D(20030)), ("B", 1, D(20060))]
    assert [e.kind for e in ev] == ["OPENED"]
    ev = await pump(sim, om, 20010, 20031, 20005, 20028)  # leg A hits the partial
    assert ("STOP_MOVED", "BREAKEVEN 20000.50") in [(e.kind, e.detail) for e in ev]
    ev = await pump(sim, om, 20028, 20055, 20027, 20050)  # best 20055 → trail 2R (40 pts) → 20015
    assert ("STOP_MOVED", "TRAIL 20015.00") in [(e.kind, e.detail) for e in ev]
    ev = await pump(sim, om, 20050, 20051, 20010, 20012)  # runner stopped at 20015
    closed = [e for e in ev if e.kind == "CLOSED"]
    assert closed and closed[0].trade.pnl() == D(2) * 30 / T * TV + D(15) / T * TV - D(3)  # 2×30pts + 15pts − fees


async def test_one_to_one_single_contract_locks_profit(env):
    sim, om, _ = env
    plan = build_one_to_one_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20, D("0.75"), D("0.30"), 2)
    t, _ = await opened(sim, om, plan, 1, False)
    ev = await pump(sim, om, 20005, 20016, 20004, 20014)  # reaches the 75% point (20015)
    assert ("STOP_MOVED", "LOCK 20006.00") in [(e.kind, e.detail) for e in ev]
    ev = await pump(sim, om, 20014, 20015, 20005, 20006)
    assert [e.kind for e in ev if e.kind == "CLOSED"] and t.pnl() == D(6) / T * TV - D(1)


async def test_one_to_one_two_legs_breakeven_after_partial(env):
    sim, om, _ = env
    plan = build_one_to_one_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20, D("0.75"), D("0.30"), 2)
    t, _ = await opened(sim, om, plan, 2, False)
    assert [(leg.name, leg.take_profit) for leg in t.legs] == [("A", D(20015)), ("B", D(20020))]
    ev = await pump(sim, om, 20005, 20016, 20004, 20012)
    assert ("STOP_MOVED", "BREAKEVEN 20000.50") in [(e.kind, e.detail) for e in ev]


async def test_stop_modify_failure_flattens_and_pauses(env):
    sim, om, _ = env
    plan = apply_guard(build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20), T, 2)
    await opened(sim, om, plan, 2, True)
    sim.fail_next.add("modify_stop")
    ev = await pump(sim, om, 20010, 20031, 20005, 20028)
    assert ("PAUSE", "STOP_MODIFY_FAILED") in [(e.kind, e.detail) for e in ev]
    assert await sim.get_positions("A") == []


async def test_second_leg_failure_flattens_first_leg(env):
    sim, om, _ = env
    plan = apply_guard(build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20), T, 2)
    orig = sim.place_bracket
    calls = {"n": 0}

    async def flaky(acct, req):
        calls["n"] += 1
        if calls["n"] == 2:
            raise BrokerError("reject")
        return await orig(acct, req)

    sim.place_bracket = flaky
    with pytest.raises(BrokerError):
        await om.open_trade("A", "MNQ", plan, 2, True, T, TV, AT, WIN)
    assert await sim.get_positions("A") == []  # no half-protected position left


async def test_market_fill_outside_window_is_flattened(env):
    sim, om, _ = env
    sim.last["MNQ"] = D(20030)  # price ran away before the market order filled
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    _, ev = await opened(sim, om, plan, 1, False)
    assert ("FLATTENED", "RR_INVALID_AFTER_FILL") in [(e.kind, e.detail) for e in ev]
    assert await sim.get_positions("A") == []


async def test_early_exit_respects_hold_and_1r(env):
    sim, om, _clock = env
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    t, _ = await opened(sim, om, plan, 1, False)
    await pump(sim, om, 20000, 20005, 19995, 20002)
    assert await om.early_exit(t.trade_id, "C3_CLOSED", AT + timedelta(seconds=8)) == []  # < 9 s hold
    ev = await om.early_exit(t.trade_id, "C3_CLOSED", AT + timedelta(seconds=10))
    assert [e.detail for e in ev] == ["C3_CLOSED"] and await sim.get_positions("A") == []


async def test_no_early_exit_after_1r(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    t, _ = await opened(sim, om, plan, 1, False)
    await pump(sim, om, 20000, 20021, 19999, 20010)  # reached +1R (20 pts)
    assert await om.early_exit(t.trade_id, "CHOCH_AGAINST", AT + timedelta(minutes=5)) == []


async def test_adverse_half_closes_one_leg_near_the_stop(env):
    from datetime import timedelta

    from app.management.exits import adverse_half_due

    sim, om, _ = env
    om.split_for_defence = True
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)  # risk 20 pts (stop 19980)
    t, _ = await opened(sim, om, plan, 4, False)
    assert [(x.name, x.qty) for x in t.legs] == [("H1", 2), ("H2", 2)]
    later = AT + timedelta(seconds=30)
    assert await om.adverse_half(t.trade_id, D(19990), D("0.9"), True, later) == []  # only 50% of the way
    assert await om.adverse_half(t.trade_id, D(19982), D("0.9"), False, later) == []  # confirmations still OK
    assert await om.adverse_half(t.trade_id, D(19982), D("0.9"), True, AT) == []  # minimum hold not reached
    sim.last["MNQ"] = D(19982)
    ev = await om.adverse_half(t.trade_id, D(19982), D("0.9"), True, later)
    assert [e.detail for e in ev] == ["HALF_OFF 2"]
    for f in sim.drain_fills():
        await om.on_fill(f)
    assert [x.closed for x in t.legs] == [True, False] and t.trade_id in om.trades  # other half keeps its stop
    assert await om.adverse_half(t.trade_id, D(19981), D("0.9"), True, later) == []  # once per trade
    assert not adverse_half_due(plan, D(19982), D("0.9"), True, 1, False)  # 1 contract can't be halved
    assert await om.adverse_half("nope", D(1), D("0.9"), True, later) == []


async def test_adverse_half_broker_failure_is_reported(env):
    from datetime import timedelta

    sim, om, _ = env
    om.split_for_defence = True
    plan = build_trade_plan(Direction.SHORT, D(20000), D(20019), D(19930), T, 4, 20)
    t, _ = await opened(sim, om, plan, 2, False)
    sim.fail_next.add("close_leg")
    ev = await om.adverse_half(t.trade_id, D(20018), D("0.9"), True, AT + timedelta(seconds=30))
    assert ev[0].detail.startswith("HALF_OFF_FAILED")


async def test_scalp_half_banks_quick_target_half_runs_with_trailing_stop(env):
    sim, om, _ = env
    om.scalp_runner = (D(2), D("0.5"))
    # 0.5R scalp plan: entry 20000, stop 19980 (20 pts), TP 20010
    plan = build_one_to_one_plan(
        Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20, D("0.75"), D("0.3"), 2, D("0.5")
    )
    t, _ = await opened(sim, om, plan, 2, False)
    assert [(x.name, x.qty, x.take_profit) for x in t.legs] == [("A", 1, D(20010)), ("B", 1, D(20040))]
    assert t.runner_trail == D("0.5")
    ev = await pump(sim, om, 20001, 20011, 20000, 20010)  # quick target hit → half banked
    assert any(e.kind == "STOP_MOVED" and e.detail.startswith("BREAKEVEN") for e in ev)
    b = t.legs[1]
    assert b.stop >= t.plan.entry  # runner can no longer lose
    await pump(sim, om, 20010, 20030, 20012, 20028)  # best 20030 → trail 0.5R (10 pts) → 20020
    assert b.stop == D(20020)
    await pump(sim, om, 20028, 20029, 20025, 20026)  # pullback: the stop never loosens
    assert b.stop == D(20020)
