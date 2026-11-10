"""D85 AI Duo trade management: break-even, profit lock (config or AI level), trailing stop; ratchet only, never
through the market; the rule that chose the level is returned for the log."""

from decimal import Decimal as D

import pytest

from app.engine.trade_plan import Direction
from app.management.trade_manage import ManageCfg, StopMove, managed_stop

T = D("0.25")
CFG = ManageCfg(
    D("1.0"), D(30), D(15), D("1.5"), D("1.0"), 2
)  # BE +1R, lock +15 at +30 pts, trail 1R behind from +1.5R
ENTRY, RISK, STOP = D(20000), D(20), D(19980)


def stop(best, cur=STOP, d=Direction.LONG, cfg=CFG, last=None, entry=ENTRY):
    return managed_stop(d, entry, RISK, D(best), cur, cfg, T, None if last is None else D(last))


def test_nothing_moves_before_one_r():
    assert stop(20019.75) is None


def test_break_even_plus_fee_cover_at_one_r():
    assert stop(20020) == StopMove(D("20000.5"), "BREAKEVEN")  # entry + 2 ticks


def test_config_lock_then_trail_each_ratchet_the_stop():
    assert stop(20030, D("20000.5")) == StopMove(D(20015), "LOCK_CONFIG")  # +30 pts → entry +15 (trail would be 20010)
    assert stop(20050, D(20015)) == StopMove(D(20030), "TRAIL")  # trail: best − 1R beats the lock
    assert stop(20050, D(20035)) is None  # never loosens


def test_the_ai_lock_level_replaces_the_config_level():
    ai = ManageCfg(D("1.0"), D(30), D(15), D("9"), D("1.0"), 2, D(20022))
    assert stop(20030, D("20000.5"), cfg=ai) == StopMove(D(20022), "LOCK_AI")
    wrong = ManageCfg(D("1.0"), D(30), D(15), D("9"), D("1.0"), 2, D(19990))  # not in the trade's favour → ignored
    assert stop(20030, D("20000.5"), cfg=wrong) == StopMove(D(20015), "LOCK_CONFIG")
    assert stop(20030, D(20025), cfg=ai) is None  # the AI level would loosen the stop: ratchet only


def test_a_stop_is_never_placed_through_the_market():
    # lock level 20015 but price already back at 20010 → nearest valid tick under the market, logged as capped
    assert stop(20030, D("20000.5"), last=20010) == StopMove(D("20009.75"), "LOCK_CONFIG+MARKET_CAP")
    assert stop(20030, D("20000.5"), last=20016) == StopMove(D(20015), "LOCK_CONFIG")  # market above the level: as is
    assert stop(20030, D(20015), last=20010) is None  # the capped level would not tighten the current stop


def test_short_side():
    d = Direction.SHORT
    assert stop(19980, D(20020), d) == StopMove(D("19999.5"), "BREAKEVEN")
    assert stop(19970, D("19999.5"), d) == StopMove(D(19985), "LOCK_CONFIG")
    assert stop(19950, D(19985), d) == StopMove(D(19970), "TRAIL")
    ai = ManageCfg(D("1.0"), D(30), D(15), D("9"), D("1.0"), 2, D(19978))
    assert stop(19970, D(19999), d, cfg=ai) == StopMove(D(19978), "LOCK_AI")
    assert stop(19970, D(19999), d, cfg=ai, last=19980) == StopMove(D("19980.25"), "LOCK_AI+MARKET_CAP")


@pytest.mark.parametrize("best", [20000, 20010, 20019])
def test_below_threshold_is_none(best):
    assert stop(best) is None


# ---------- on a real AI Duo trade (order manager + simulator) ----------
async def test_duo_trade_break_even_lock_and_trail_through_the_order_manager():
    from datetime import UTC, datetime

    from app.clock import FixedClock
    from app.engine.trade_plan import TradePlan
    from app.execution.adapters.sim import SimAdapter, SimInstrument
    from app.execution.order_manager import OrderManager

    at = datetime(2026, 11, 5, 15, tzinfo=UTC)
    sim = SimAdapter(FixedClock(at), {"MNQ": SimInstrument(T, D("0.50"), D("1.00"))}, slippage_ticks=0)
    sim.add_account("A", D(150000))
    sim.last["MNQ"] = ENTRY
    om = OrderManager(sim)
    plan = TradePlan(Direction.LONG, ENTRY, STOP, D(20100), RISK, D(5), mode="AI_DUO")
    t = await om.open_trade("A", "MNQ", plan, 2, False, T, D("0.50"), at, (D(19000), D(21000), D(1), D(100), 4, 20))
    t.manage = CFG
    for f in sim.drain_fills():
        await om.on_fill(f)

    async def bar(o, h, lo, c):
        ev = []
        for f in sim.on_bar("MNQ", D(o), D(h), D(lo), D(c), at):
            ev += await om.on_fill(f)
        return ev + await om.on_bar("MNQ", D(h), D(lo), D(c))

    assert await bar(20000, 20015, 19995, 20010) == []  # +0.75R: nothing yet
    ev = await bar(20010, 20020, 20005, 20018)  # +1R → break-even + 2 ticks
    assert [(e.kind, e.detail) for e in ev] == [("STOP_MOVED", "MANAGE:BREAKEVEN 20000.50")]
    ev = await bar(20018, 20040, 20015, 20035)  # +40 pts: lock (+15) and trail (1R behind = 20020) → the trail wins
    assert [(e.kind, e.detail) for e in ev] == [("STOP_MOVED", "MANAGE:TRAIL 20020.0")] and t.legs[0].stop == D(20020)
    assert await bar(20035, 20036, 20030, 20031) == []  # best unchanged: the stop never loosens
    ev = await bar(20031, 20031, 20019, 20020)  # price falls through the managed stop
    closed = [e for e in ev if e.kind == "CLOSED"]
    assert closed and closed[0].detail == "STOP" and closed[0].trade.pnl() > 0  # a protective exit, booked as a win


def test_manage_config_survives_a_restart_snapshot():
    from datetime import UTC, datetime

    from app.engine.trade_plan import TradePlan
    from app.execution import trade_state
    from app.execution.order_manager import Leg, OpenTrade

    plan = TradePlan(Direction.LONG, ENTRY, STOP, D(20100), RISK, D(5), mode="AI_DUO")
    t = OpenTrade("T", "A", "MNQ", plan, False, T, D("0.5"), datetime(2026, 11, 5, tzinfo=UTC),
                  [Leg("ONLY", 1, D(20100), "B", "O", STOP, ENTRY)], (D(1), D(2), D(1), D(3), 4, 20))  # fmt: skip
    t.manage = ManageCfg(D("1.0"), D(100), D(50), D("1.5"), D("1.0"), 2, D(20055))
    back = trade_state.load(trade_state.dump(t))
    assert back.manage == t.manage and back == t
    t.manage = ManageCfg(D("1.0"), D(100), D(50), D("1.5"), D("1.0"), 2)
    assert trade_state.load(trade_state.dump(t)).manage.ai_lock_price is None
