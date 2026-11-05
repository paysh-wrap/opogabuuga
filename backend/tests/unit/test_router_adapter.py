from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.execution.adapters.base import BracketAck, BracketRequest, BrokerAccount, BrokerError, Fill, PnlUpdate
from app.execution.adapters.router import LiveBlockedError, RoutingAdapter
from app.execution.adapters.sim import SimAdapter, SimInstrument

AT = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


class FakeLive:
    name = "crosstrade"
    capabilities = SimAdapter.capabilities

    def __init__(self):
        self.placed, self.flattened = [], []

    async def list_accounts(self):
        return [BrokerAccount("LUCID1", "LUCID1", D(25000)), BrokerAccount("OTHER", "OTHER", D(1))]

    async def get_positions(self, a):
        return []

    async def get_balance(self, a):
        return D(25000)

    async def place_bracket(self, a, req):
        self.placed.append(a)
        return BracketAck("1", "1", "3", "2")

    async def flatten(self, a):
        self.flattened.append(a)

    async def health(self):
        from app.execution.adapters.base import AdapterHealth

        return AdapterHealth(True, "ct")


def mk():
    sim = SimAdapter(FixedClock(AT), {"MNQ": SimInstrument(D("0.25"), D("0.50"), D(1))})
    sim.add_account("SIM-1", D(25000))
    r = RoutingAdapter(sim)
    live = FakeLive()
    ok = {"v": False}
    r.set_live(live, {"LUCID1"}, lambda: ok["v"])
    return r, live, ok


REQ = BracketRequest("c", "MNQ", "BUY", 1, D(19990), D(20020))


async def test_live_orders_blocked_until_checklist_green():
    r, live, ok = mk()
    with pytest.raises(LiveBlockedError):
        await r.place_bracket("LUCID1", REQ)
    assert live.placed == []
    ok["v"] = True
    await r.place_bracket("LUCID1", REQ)
    assert live.placed == ["LUCID1"]


async def test_protective_actions_never_blocked_and_unknown_rejected():
    r, live, _ = mk()
    await r.flatten("LUCID1")
    assert live.flattened == ["LUCID1"]
    with pytest.raises(BrokerError):
        await r.flatten("NOPE")


async def test_routing_pnl_fills_and_accounts():
    r, _, _ = mk()
    assert r.accounts == {"SIM-1", "LUCID1"} and r.name == "sim+crosstrade"
    assert {a.account_id for a in await r.list_accounts()} == {"SIM-1", "LUCID1"}
    with pytest.raises(BrokerError):
        r.open_pnl("LUCID1")  # no live P&L yet → never assume flat
    r.push_live_pnl(PnlUpdate("LUCID1", D(25010), D(-40), AT))
    assert r.open_pnl("LUCID1") == D(-40) and await r.get_balance("LUCID1") == D(25010)
    assert r.pnl_age("LUCID1", AT) == 0 and r.pnl_age("X", AT) is None
    f = Fill("LUCID1", "3", "1", "STOP", "MNQ", "SELL", 1, D(19990), AT)
    r.push_live_fill(f)
    assert r.drain_live() == [f] and r.drain_fills() == []
    assert (await r.health()).ok


async def test_no_live_is_plain_sim():
    sim = SimAdapter(FixedClock(AT), {})
    r = RoutingAdapter(sim)
    assert r.name == "sim" and r.capabilities == sim.capabilities and r.accounts == set()


async def test_pumps_survive_broker_errors():
    import asyncio

    r, live, _ = mk()
    calls = {"n": 0}

    async def bad_fills():
        calls["n"] += 1
        raise BrokerError("rate_limited")
        yield  # pragma: no cover

    async def pnl():
        yield PnlUpdate("LUCID1", D(25000), D(5), AT)
        raise BrokerError("down")

    live.stream_fills, live.stream_pnl = bad_fills, pnl
    r.retry_s = 0
    r.start()
    await asyncio.sleep(0.01)
    r.stop()
    assert calls["n"] > 1 and r.open_pnl("LUCID1") == D(5) and r.last_error


async def test_on_bar_fills_are_not_left_queued():
    sim = SimAdapter(FixedClock(AT), {"MNQ": SimInstrument(D("0.25"), D("0.50"), D(1))}, slippage_ticks=0)
    sim.add_account("S", D(25000))
    r = RoutingAdapter(sim)
    sim.on_bar("MNQ", D(20000), D(20000), D(20000), D(20000), AT)
    await r.place_bracket("S", REQ)
    entry = r.drain_fills()
    assert [f.role for f in entry] == ["ENTRY"]
    got = r.on_bar("MNQ", D(20000), D(20030), D(20000), D(20025), AT)
    assert [f.role for f in got] == ["TP"]
    assert r.drain_fills() == []  # each fill delivered exactly once
