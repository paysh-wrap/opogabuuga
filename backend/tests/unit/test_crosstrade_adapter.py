import json
from decimal import Decimal as D

import httpx
import pytest

from app.execution.adapters.base import BracketRequest, BrokerError
from app.execution.adapters.crosstrade import CrossTradeAdapter, UnconfirmedError

SNAP = {
    "success": True,
    "accounts": [
        {
            "name": "LUCID123",
            "netLiq": 25125,
            "openPnl": 125,
            "errorCode": None,
            "positions": [{"contract": "MNQZ6", "netPos": 2, "netPrice": 20000.25}],
            "workingOrders": [
                {
                    "orderId": 91,
                    "contract": "MNQZ6",
                    "action": "Sell",
                    "qty": 2,
                    "orderType": "Stop",
                    "price": None,
                    "stopPrice": 19980,
                }
            ],
        }
    ],
}


def make(handler):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return CrossTradeAdapter("tok", http, {"MNQ": "MNQ1!"}, verify_delay_s=0)


async def test_reads_from_snapshot():
    seen = {}

    def h(req):
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(200, json=SNAP)

    ct = make(h)
    assert await ct.get_balance("lucid123") == D(25000)
    assert [(p.symbol, p.qty, p.avg_price) for p in await ct.get_positions("LUCID123")] == [("MNQ", 2, D("20000.25"))]
    assert [(o.role, o.price) for o in await ct.get_orders("LUCID123")] == [("STOP", D(19980))]
    assert seen["auth"] == "Bearer tok"


async def test_place_bracket_maps_oso_ids():
    body = {}

    def h(req):
        body.update(json.loads(req.content))
        return httpx.Response(200, json={"success": True, "response": {"orderId": 1, "oso1Id": 2, "oso2Id": 3}})

    ack = await make(h).place_bracket("LUCID123", BracketRequest("T1-A", "MNQ", "BUY", 2, D(19980), D(20060)))
    assert (ack.entry_order_id, ack.tp_order_id, ack.stop_order_id) == ("1", "2", "3")
    assert body == {
        "instrument": "MNQ1!",
        "action": "buy",
        "qty": 2,
        "orderType": "market",
        "takeProfit": 20060.0,
        "stopLoss": 19980.0,
        "clOrdId": "T1-A",
    }


async def test_502_on_mutation_is_unconfirmed_never_retried():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(502, json={"success": False, "error": "tradovate_unavailable"})

    with pytest.raises(UnconfirmedError):
        await make(h).place_bracket("A", BracketRequest("c", "MNQ", "BUY", 1, D(1), D(3)))
    assert calls["n"] == 1


async def test_unreadable_reply_is_a_broker_error_never_a_crash():
    """Review fix: a non-JSON reply (proxy HTML page) raised ValueError past every BrokerError handler."""
    html = lambda status: lambda r: httpx.Response(status, text="<html>Bad gateway</html>")  # noqa: E731
    req = BracketRequest("c", "MNQ", "BUY", 1, D(1), D(3))
    with pytest.raises(UnconfirmedError):  # mutation, outcome unknown: never resent blind
        await make(html(502)).place_bracket("A", req)
    with pytest.raises(UnconfirmedError):  # 2xx but unreadable: accepted or not is unknown
        await make(html(200)).place_bracket("A", req)
    with pytest.raises(UnconfirmedError):
        await make(lambda r: httpx.Response(504, json={"success": False})).flatten("A")
    with pytest.raises(BrokerError):
        await make(html(200)).get_balance("A")
    with pytest.raises(BrokerError):
        await make(lambda r: httpx.Response(200, json=[1, 2])).get_positions("A")


async def test_modify_stop_verified_against_working_order():
    def ok(req):
        if req.method == "PUT":
            return httpx.Response(200, json={"success": True, "response": {"commandId": 5}})
        s = json.loads(json.dumps(SNAP))
        s["accounts"][0]["workingOrders"][0]["stopPrice"] = 20000.5
        return httpx.Response(200, json=s)

    assert await make(ok).modify_stop("LUCID123", "91", D("20000.5")) is True

    def ignored(req):  # accepted but not applied → must report failure (→ flatten + pause upstream)
        if req.method == "PUT":
            return httpx.Response(200, json={"success": True, "response": {"commandId": 5}})
        return httpx.Response(200, json=SNAP)

    assert await make(ignored).modify_stop("LUCID123", "91", D("20000.5")) is False


async def test_errors():
    ct = make(lambda r: httpx.Response(429, json={"success": False, "error": "rate_limited"}))
    with pytest.raises(BrokerError):
        await ct.get_balance("A")
    s = json.loads(json.dumps(SNAP))
    s["accounts"][0]["openPnl"] = None
    with pytest.raises(BrokerError):
        await make(lambda r: httpx.Response(200, json=s)).get_balance("LUCID123")  # no fresh pricing
    with pytest.raises(BrokerError):
        CrossTradeAdapter("", httpx.AsyncClient(), {})
    h = await make(lambda r: httpx.Response(401, json={"success": False, "error": "api_requires_pro"})).health()
    assert not h.ok and "api_requires_pro" in h.detail


def _fill(i, oid, action="Buy", px=20000.25):
    # exact shape from crosstrade.io docs: GET /accounts/{account}/fills
    return {
        "id": i,
        "orderId": oid,
        "contractId": 1234,
        "timestamp": "2026-10-27T12:00:00Z",
        "tradeDate": {"year": 2026, "month": 10, "day": 27},
        "action": action,
        "qty": 1,
        "price": px,
        "active": True,
        "finallyPaired": 0,
        "external": False,
        "instrument": "MNQZ6",
        "executionId": f"tv:demo:{i}",
        "fillId": i,
        "environment": "demo",
        "accountId": 1,
        "accountName": "LUCID123",
    }


async def test_fills_polled_mapped_and_deduped():
    fills = [_fill(10, 1)]

    def h(req):
        if req.url.path.endswith("/orders/place"):
            return httpx.Response(200, json={"success": True, "response": {"orderId": 1, "oso1Id": 2, "oso2Id": 3}})
        return httpx.Response(200, json={"success": True, "data": fills})

    ct = make(h)
    await ct.place_bracket("LUCID123", BracketRequest("c1", "MNQ", "BUY", 1, D(19990), D(20020)))
    [f] = await ct.poll_fills("LUCID123")
    assert (f.bracket_id, f.role, f.symbol, f.side, f.price, f.at.year) == (
        "1",
        "ENTRY",
        "MNQ",
        "BUY",
        D("20000.25"),
        2026,
    )
    fills.append(_fill(11, 3, "Sell", 19990))
    fills.append(_fill(12, 77, "Sell"))
    got = await ct.poll_fills("LUCID123")
    assert [(x.role, x.bracket_id) for x in got] == [("STOP", "1"), ("EXTERNAL", None)]
    assert await ct.poll_fills("LUCID123") == []


async def test_fill_errors_raise():
    ct = make(lambda r: httpx.Response(200, json={"success": False, "error": "unknown_account"}))
    with pytest.raises(BrokerError):
        await ct.poll_fills("X")


async def test_stream_fills_skips_history_then_yields_new(monkeypatch):
    calls = {"n": 0}

    def h(req):
        if req.url.path.endswith("/snapshot"):
            return httpx.Response(200, json=SNAP)
        calls["n"] += 1
        data = [_fill(1, 9)] + ([_fill(2, 9, "Sell")] if calls["n"] > 1 else [])
        return httpx.Response(200, json={"success": True, "data": data})

    ct = make(h)
    ct.poll_s = 0
    gen = ct.stream_fills()
    f = await gen.__anext__()
    assert f.order_id == "9" and f.side == "SELL"
    await gen.aclose()


async def test_registered_bracket_maps_fills_after_restart():
    """Review fix: after a restart the role map is rebuilt from the snapshot, so stop / TP fills are not EXTERNAL."""
    ct = make(lambda r: httpx.Response(200, json={"success": True, "data": [_fill(7, 55, "Sell")]}))
    ct.register_bracket("40", "55", "56")
    f = (await ct.poll_fills("LUCID123"))[0]
    assert (f.bracket_id, f.role) == ("40", "STOP")
    ct.register_bracket("", "1", "2")  # no bracket id: nothing to map
    assert "1" not in ct._roles


async def test_cancel_entry_is_refused_not_invented():
    with pytest.raises(BrokerError, match="not supported"):
        await make(lambda r: httpx.Response(200, json={})).cancel_entry("LUCID123", "91")
