from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.execution.adapters.base import BracketRequest, BrokerError, conservative_mode
from app.execution.adapters.sim import SimAdapter, SimInstrument

AT = datetime(2026, 11, 5, 15, tzinfo=UTC)


@pytest.fixture
def sim():
    s = SimAdapter(FixedClock(AT), {"MNQ": SimInstrument(D("0.25"), D("0.50"), D("1.00"))}, slippage_ticks=1)
    s.add_account("A", D(25000))
    s.last["MNQ"] = D(20000)
    return s


def bar(s, o, h, lo, c):
    return s.on_bar("MNQ", D(o), D(h), D(lo), D(c), AT)


async def test_market_long_tp_pnl_and_fees(sim):
    ack = await sim.place_bracket("A", BracketRequest("c1", "MNQ", "BUY", 2, D(19980), D(20060)))
    pos = await sim.get_positions("A")
    assert pos[0].qty == 2 and pos[0].avg_price == D("20000.25")  # 1 tick adverse slippage
    assert {o.role for o in await sim.get_orders("A")} == {"STOP", "TP"}
    fills = bar(sim, 20010, 20061, 20005, 20055)
    assert [(f.role, f.price) for f in fills] == [("TP", D(20060))]
    # (20060 − 20000.25) = 59.75 pts = 239 ticks × $0.50 × 2 = $239 − fees $2
    assert await sim.get_balance("A") == D(25000) + D(239) - D(2)
    assert await sim.get_positions("A") == [] and await sim.get_orders("A") == []
    assert ack.bracket_id.startswith("B")


async def test_ambiguous_bar_takes_the_stop_first(sim):
    await sim.place_bracket("A", BracketRequest("c1", "MNQ", "BUY", 1, D(19980), D(20060)))
    fills = bar(sim, 20000, 20070, 19970, 20000)
    assert [(f.role, f.price) for f in fills] == [("STOP", D("19979.75"))]


async def test_gap_through_stop_fills_at_open(sim):
    await sim.place_bracket("A", BracketRequest("c1", "MNQ", "SELL", 1, D(20020), D(19940)))
    fills = bar(sim, 20030, 20035, 20025, 20030)
    assert [(f.role, f.price) for f in fills] == [("STOP", D("20030.25"))]


async def test_limit_entry_and_modify_stop(sim):
    await sim.place_bracket("A", BracketRequest("c1", "MNQ", "BUY", 1, D(19980), D(20060), "LIMIT", D(19995)))
    assert await sim.get_positions("A") == []
    fills = bar(sim, 20000, 20001, 19994, 19998)
    assert [(f.role, f.price) for f in fills] == [("ENTRY", D(19995))]
    stop_id = next(o.order_id for o in await sim.get_orders("A") if o.role == "STOP")
    assert await sim.modify_stop("A", stop_id, D(20000))
    fills = bar(sim, 20001, 20002, 19999, 20000)  # opens above the new stop → fills at the stop − 1 tick
    assert [(f.role, f.price) for f in fills] == [("STOP", D("19999.75"))]


async def test_failures_and_flatten(sim):
    sim.fail_next.add("place_bracket")
    with pytest.raises(BrokerError):
        await sim.place_bracket("A", BracketRequest("c1", "MNQ", "BUY", 1, D(19980), D(20060)))
    await sim.place_bracket("A", BracketRequest("c2", "MNQ", "BUY", 1, D(19980), D(20060)))
    stop_id = next(o.order_id for o in await sim.get_orders("A") if o.role == "STOP")
    sim.fail_next.add("modify_stop")
    assert await sim.modify_stop("A", stop_id, D(19990)) is False
    await sim.cancel_all("A")  # protective orders of an open position are NOT cancelled
    assert {o.role for o in await sim.get_orders("A")} == {"STOP", "TP"}
    await sim.flatten("A")
    assert await sim.get_positions("A") == [] and await sim.get_orders("A") == []
    with pytest.raises(BrokerError):
        await sim.get_balance("nope")
    assert not conservative_mode(sim)


def test_bracket_requires_stop_and_tp():
    with pytest.raises(ValueError):
        BracketRequest("c", "MNQ", "BUY", 0, D(1), D(2))
    with pytest.raises(ValueError):
        BracketRequest("c", "MNQ", "BUY", 1, None, D(2))  # type: ignore[arg-type]
