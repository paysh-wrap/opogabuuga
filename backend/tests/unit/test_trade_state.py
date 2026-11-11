"""OpenTrade snapshot round trip (restart recovery) and simulator bracket restore."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

from app.clock import FixedClock
from app.engine.trade_plan import Direction, TradePlan
from app.execution import trade_state
from app.execution.adapters.base import BracketRequest
from app.execution.adapters.sim import SimAdapter, SimInstrument
from app.execution.order_manager import Leg, OpenTrade

NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


def make() -> OpenTrade:
    plan = TradePlan(Direction.LONG, D(100), D(98), D(104), D(2), D(2), D(102), D(100), D("101"), "STANDARD")
    legs = [Leg("A", 1, D(102), "B1", "O2", D(98), D(100), None, D(0), False), Leg("B", 1, D(104), "B2", "O5", D(99))]
    t = OpenTrade("P-1-2", "ACC", "MNQ", plan, True, D("0.25"), D("0.5"), NOW, legs, (D(98), D(104), D(2), D(3), 2, 8))
    t.best, t.partial_done, t.closing, t.closing_since, t.pending_until = D(101), True, "X", NOW, NOW
    t.signal_id, t.strategy, t.profile, t.runner_trail = 7, "NOISE", "TIGHT", D(1)
    return t


def test_round_trip_is_lossless():
    t = make()
    back = trade_state.load(trade_state.dump(t))
    assert back == t
    assert trade_state.dump(back) == trade_state.dump(t)


def test_restore_bracket_keeps_ids_and_new_ids_never_collide():
    sim = SimAdapter(FixedClock(NOW), {"MNQ": SimInstrument(D("0.25"), D("0.5"), D("1"))}, 1)
    sim.add_account("ACC", D(25000))
    req = BracketRequest("P-1-2-A", "MNQ", "BUY", 1, D(98), D(102))
    sim.restore_bracket("ACC", "B7", "O9", req, D(100), D(99))
    pos = asyncio.run(sim.get_positions("ACC"))
    assert pos[0].qty == 1 and pos[0].avg_price == D(100)
    sim.last["MNQ"] = D(100)
    ack = asyncio.run(sim.place_bracket("ACC", BracketRequest("c", "MNQ", "BUY", 1, D(90), D(120))))
    assert ack.bracket_id not in ("B7",) and int(ack.bracket_id[1:]) > 9
    lim = BracketRequest("P-1-2-B", "MNQ", "BUY", 1, D(98), D(102), "LIMIT", D(99))
    sim.restore_bracket("ACC", "B30", "O31", lim, None, D(98))  # a working (unfilled) limit entry
    assert any(o.bracket_id == "B30" and o.status == "WORKING" for o in asyncio.run(sim.get_orders("ACC")))


def test_round_trip_keeps_the_dynamic_trail():
    from app.management.dynamic_trail import TrailParams

    t = make()
    steps = ((D(2), D(2)), (None, D(1)))
    t.dyn_trail = TrailParams(D(1), 8, 5, 14, 5, steps, D("0.25"), D("0.75"), 50, D("0.5"), 2, D("0.25"), (5, D(1)))
    back = trade_state.load(trade_state.dump(t))
    assert back == t and back.dyn_trail == t.dyn_trail
    t.dyn_trail = TrailParams(D(1), 8, 5, 14, 5, steps, D("0.25"), D("0.75"), 50, D("0.5"), 2)
    assert trade_state.load(trade_state.dump(t)).dyn_trail == t.dyn_trail
