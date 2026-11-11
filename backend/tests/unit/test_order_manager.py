from dataclasses import replace
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
    assert await om.early_exit(t.trade_id, "C3_CLOSED", AT + timedelta(seconds=7)) == []  # < 7.5 s hold
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


async def test_leg_failure_with_failed_emergency_flatten_stays_tracked_as_orphan(env):
    from app.execution.order_manager import OrphanedPosition

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
    sim.fail_next.add("flatten")
    with pytest.raises(OrphanedPosition) as ei:
        await om.open_trade("A", "MNQ", plan, 2, True, T, TV, AT, WIN)
    t = ei.value.trade
    assert om.trades[t.trade_id] is t and t.orphan and t.closing == "ORPHAN_FLATTEN"


async def deferred(env):
    sim, om, _ = env

    async def noop(acct):
        return None

    sim.flatten = noop
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    t, _ = await opened(sim, om, plan, 2, False)
    await pump(sim, om, 20000, 20001, 20000, 20000)
    return sim, om, t


async def test_exit_fill_after_deferred_flatten_books_real_pnl_and_partials_accumulate(env):
    from app.execution.adapters.base import Fill

    _sim, om, t = await deferred(env)
    ev = await om.early_exit(t.trade_id, "C3_CLOSE", AT + timedelta(seconds=30))
    assert [e.kind for e in ev] == ["FLATTENED"] and t.trade_id in om.trades and t.closing == "C3_CLOSE"
    assert t.pnl() == 0 and not t.closed
    qty = sum(x.qty for x in t.legs)
    entry = t.legs[0].entry

    def fill(q, px, side="SELL", sym="MNQ"):
        return Fill("A", "o", None, "EXTERNAL", sym, side, q, px, AT, D("0.50"))

    assert await om.on_fill(fill(qty, entry, side="BUY")) == []  # wrong side
    assert await om.on_fill(fill(qty, entry, sym="MES")) == []  # other symbol
    assert await om.on_fill(fill(qty - 1, entry + 4)) == []  # partial
    ev = await om.on_fill(fill(1, entry + 8))
    assert [(e.kind, e.detail) for e in ev] == [("CLOSED", "FLATTEN")] and t.closed
    avg = (entry + 4) * (qty - 1) + (entry + 8)
    assert t.legs[0].exit == avg / qty and t.pnl() > 0 and t.trade_id not in om.trades


async def test_unmatched_fill_ignored_without_closing_trade_or_open_legs(env):
    from app.execution.adapters.base import Fill

    _sim, om, t = await deferred(env)
    f = Fill("A", "o", None, "EXTERNAL", "MNQ", "SELL", 2, D(20000), AT)
    assert await om.on_fill(f) == []  # trade not closing
    t.closing = "X"
    for leg in t.legs:
        leg.closed = True
    assert await om.on_fill(f) == []  # nothing left open


# ---------- limit_cisd entries ----------
DEADLINE = AT + timedelta(minutes=20)


async def open_limit(sim, om, plan, n, guard, deadline=DEADLINE):
    t = await om.open_trade("A", "MNQ", plan, n, guard, T, TV, AT, WIN, "limit_cisd", deadline)
    return t, sim.drain_fills()


async def test_limit_mode_places_limit_brackets_with_stop_and_tp(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, fills = await open_limit(sim, om, plan, 1, False)
    assert fills == []
    entry = next(o for o in sim.accounts["A"].orders.values() if o.role == "ENTRY")
    assert (entry.kind, entry.price, entry.status) == ("LIMIT", D(19990), "WORKING")
    assert {o.role for o in sim.accounts["A"].orders.values()} == {"ENTRY", "STOP", "TP"}
    assert await sim.get_positions("A") == [] and om.has_unfilled(t)


async def test_limit_fill_at_limit_passes_rr_recheck_and_hold_starts_at_fill(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, _ = await open_limit(sim, om, plan, 1, False)
    ev = await pump(sim, om, 19995, 19996, 19989, 19992)
    assert [e.kind for e in ev] == ["OPENED"] and t.closing is None and t.pending_until is None
    assert t.legs[0].entry == D(19990) and t.opened_at == AT  # same-instant fill: opened_at not moved back


async def test_limit_fill_later_moves_opened_at_to_fill_time(env):
    sim, om, clock = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, _ = await open_limit(sim, om, plan, 1, False)
    clock.set(AT + timedelta(minutes=5))
    await pump(sim, om, 19995, 19996, 19989, 19992)
    assert t.opened_at == AT + timedelta(minutes=5)


async def test_gap_through_limit_fills_better_and_trade_is_kept(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, _ = await open_limit(sim, om, plan, 1, False)
    ev = await pump(sim, om, 19985, 19988, 19984, 19986)  # opens below the limit → better price, R:R above 3R
    assert t.legs[0].entry == D(19985) and [e.kind for e in ev] == ["OPENED"] and t.closing is None


async def test_limit_fill_with_broken_window_still_flattens(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, _ = await open_limit(sim, om, plan, 1, False)
    t.rr_window = (D(19981), D(19995), D(2), D(3), 4, 20)  # T2 now too close → below 2R
    ev = await pump(sim, om, 19995, 19996, 19989, 19992)
    assert ("FLATTENED", "RR_INVALID_AFTER_FILL") in [(e.kind, e.detail) for e in ev]
    assert await sim.get_positions("A") == []


async def test_unfilled_limit_is_cancelled_at_timeout_and_not_booked(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    await open_limit(sim, om, plan, 1, False)
    assert await om.expire_unfilled(AT + timedelta(minutes=19)) == []  # not yet
    ev = await om.expire_unfilled(DEADLINE)
    assert [(e.kind, e.detail) for e in ev] == [("CANCELLED", "LIMIT_TIMEOUT")]
    assert om.trades == {} and await sim.get_orders("A") == []
    assert await pump(sim, om, 19995, 19996, 19980, 19992) == []  # the cancelled order can no longer fill
    assert await sim.get_positions("A") == []


async def test_failed_cancel_pauses_once_and_is_retried(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, _ = await open_limit(sim, om, plan, 1, False)
    sim.fail_next.add("cancel_all")
    ev = await om.expire_unfilled(DEADLINE)
    assert [e.kind for e in ev] == ["PAUSE"] and t.trade_id in om.trades
    sim.fail_next.add("cancel_all")
    assert await om.expire_unfilled(DEADLINE) == []  # still failing: tracked, retried, banner not repeated
    ev = await om.expire_unfilled(DEADLINE)
    assert [e.kind for e in ev] == ["CANCELLED"] and om.trades == {}


async def test_partial_fill_cancels_unfilled_leg_and_manages_filled_leg(env):
    sim, om, _ = env
    plan = apply_guard(build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20), T, 2)
    t, _ = await open_limit(sim, om, plan, 2, True)
    a, b = t.legs
    # fill only leg A: give B a limit the market never reaches
    br = sim.accounts["A"].brackets[b.bracket_id]
    br.req = replace(br.req, limit_price=D(19900))
    ev = await pump(sim, om, 19995, 19996, 19989, 19992)
    assert [e.kind for e in ev] == [] and a.entry == D(19990) and b.entry is None
    ev = await om.expire_unfilled(DEADLINE)
    assert [e.kind for e in ev] == ["ENTRY_TRIMMED", "OPENED"]
    assert [x.name for x in t.legs] == ["A"] and t.qty == 1
    assert [p.qty for p in await sim.get_positions("A")] == [1]  # A (and its stop) still protected
    assert any(o.role == "STOP" and o.status == "WORKING" for o in await sim.get_orders("A"))
    ev = await pump(sim, om, 19995, 20031, 19994, 20028)  # leg A's own TP, no leg B to move to breakeven
    assert [e.kind for e in ev] == ["CLOSED"]


async def test_partial_cancel_failure_keeps_everything_tracked(env):
    sim, om, _ = env
    plan = apply_guard(build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20), T, 2)
    t, _ = await open_limit(sim, om, plan, 2, True)
    t.legs[0].entry = D(19990)  # A filled
    sim.fail_next.add("cancel_entry")
    ev = await om.expire_unfilled(DEADLINE)
    assert [e.kind for e in ev] == ["PAUSE"] and len(t.legs) == 2


async def test_closing_or_filled_trades_are_not_expired(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(19990), D(19981), D(20070), T, 4, 20)
    t, _ = await open_limit(sim, om, plan, 1, False)
    t.closing = "FLAT_TIME"
    assert await om.expire_unfilled(DEADLINE) == []
    t.closing = None
    t.legs[0].entry = D(19990)
    assert await om.expire_unfilled(DEADLINE) == [] and await om.cancel_unfilled(t, "X") == []


async def test_market_mode_unchanged(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    t, ev = await opened(sim, om, plan, 1, False)
    assert t.pending_until is None and [e.kind for e in ev] == ["OPENED"]


async def test_lock_after_tp_filled_same_bar_is_not_a_failure(env):
    """D38: the TP fills on the same bar that reaches the 75% lock point → the stop is already gone; no pause."""
    sim, om, _ = env
    plan = build_one_to_one_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20, D("0.75"), D("0.30"), 2)
    await opened(sim, om, plan, 1, False)
    ev = await pump(sim, om, 20005, 20040, 20004, 20030)
    kinds = [(e.kind, e.detail) for e in ev]
    assert ("PAUSE", "STOP_MODIFY_FAILED") not in kinds
    assert any(k == "CLOSED" for k, _ in kinds)


async def test_stop_lookup_error_still_pauses(env):
    sim, om, _ = env
    plan = apply_guard(build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20), T, 2)
    await opened(sim, om, plan, 2, True)
    sim.fail_next.update({"modify_stop", "get_orders"})
    ev = await pump(sim, om, 20010, 20031, 20005, 20028)
    assert ("PAUSE", "STOP_MODIFY_FAILED") in [(e.kind, e.detail) for e in ev]


async def test_flatten_fill_is_shared_between_trades_of_one_account_by_quantity(env):
    """Review fix: two positions on one account (AI Duo 150K) closed by ONE flatten fill (no bracket id) — the fill
    is split by quantity, each trade books its own exit, neither takes the other's contracts."""
    from app.execution.adapters.base import Fill

    sim, om, _ = env
    sim.add_account("B", D(150000))
    ts = []
    for qty in (1, 2):
        plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
        ts.append(await om.open_trade("A", "MNQ", plan, qty, False, T, TV, AT, WIN))
        for f in sim.drain_fills():
            await om.on_fill(f)
    for t in ts:
        t.closing = "KILL_SWITCH"
    fill = Fill("A", "x", None, "EXIT", "MNQ", "SELL", 3, D(19990), AT, D(3))
    ev = await om.on_fill(fill)
    assert [e.kind for e in ev] == ["CLOSED", "CLOSED"] and not om.trades
    assert [t.exit_qty for t in ts] == [1, 2] and all(t.legs[0].exit == D(19990) for t in ts)
    assert sum(t.exit_fee for t in ts) == D(3)


def _trail(**kw):
    from app.management.dynamic_trail import TrailParams

    base = dict(
        activate_r=D(1), min_distance_ticks=8, atr_tf_min=1, atr_period=3, swing_tf_min=1,
        steps=((D(2), D(2)), (D(3), D("1.5")), (None, D(1))), low_vol_percentile=D("0.25"),
        low_vol_mult=D("0.75"), low_vol_lookback=50, k_floor=D("0.5"), fee_cover_ticks=2,
    )  # fmt: skip
    base.update(kw)
    return TrailParams(**base)


def _bar(i, h, lo):
    from app.indicators.bars import Bar

    return Bar(i * 60_000, (i + 1) * 60_000, D(lo), D(h), D(lo), D(h))


async def test_dynamic_trail_breakeven_then_atr_ratchet_tp_untouched(env):
    """D122: +1R → breakeven + fee cover, then k × ATR behind the best price; ratchet only, TP stays."""
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    t, _ = await opened(sim, om, plan, 1, False)
    t.dyn_trail = _trail()
    tp = t.legs[0].take_profit
    ev = await pump(sim, om, 20000, 20010, 19999, 20008)  # +10 pts < 1R (20 pts): nothing
    assert not [e for e in ev if e.kind == "STOP_MOVED"]
    ev = await pump(sim, om, 20008, 20021, 20007, 20020)  # +1R, no bars fed → breakeven only
    assert ("STOP_MOVED", "DYN_TRAIL:BREAKEVEN 20000.50") in [(e.kind, e.detail) for e in ev]
    for i in range(5):  # feed bars (range 4 → ATR 4)
        om.add_bar("MNQ", _bar(i, "20040", "20036"))
    for f in sim.on_bar("MNQ", D(20036), D(20040), D(20036), D(20040), AT):
        await om.on_fill(f)
    ev = await om.on_bar("MNQ", D(20040), D(20036), D(20040), _bar(5, "20040", "20036"))
    assert ("STOP_MOVED", "DYN_TRAIL:ATR 20034.00") in [(e.kind, e.detail) for e in ev]  # 2R → k 1.5 × 4
    assert t.legs[0].stop == D(20034) and t.legs[0].take_profit == tp
    ev = await om.on_bar("MNQ", D(20038), D(20035), D(20036))  # pull-back: never loosens
    assert not [e for e in ev if e.kind == "STOP_MOVED"] and t.legs[0].stop == D(20034)


async def test_dynamic_trail_stop_modify_failure_flattens_and_pauses(env):
    sim, om, _ = env
    plan = build_trade_plan(Direction.LONG, D(20000), D(19981), D(20070), T, 4, 20)
    t, _ = await opened(sim, om, plan, 2, False)
    t.dyn_trail = _trail()
    sim.fail_next.add("modify_stop")
    ev = await pump(sim, om, 20000, 20025, 19999, 20024)
    assert ("PAUSE", "STOP_MODIFY_FAILED") in [(e.kind, e.detail) for e in ev]
    assert t.closing == "STOP_MODIFY_FAILED"


def test_bar_buffer_dedupes_and_caps():
    om = OrderManager(None, max_bars=3)  # type: ignore[arg-type]
    for i in range(5):
        om.add_bar("MNQ", _bar(i, "10", "9"))
    om.add_bar("MNQ", _bar(4, "11", "9"))  # same bar again: replaces
    om.add_bar("MNQ", _bar(1, "12", "9"))  # older bar: ignored
    assert [(b.open_ms // 60_000, b.h) for b in om.bars["MNQ"]] == [(2, D(10)), (3, D(10)), (4, D(11))]
