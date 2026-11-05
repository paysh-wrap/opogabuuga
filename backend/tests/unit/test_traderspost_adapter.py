import json
from decimal import Decimal as D

import httpx
import pytest

from app.execution.adapters.base import BracketRequest, BrokerError, NotSupported, conservative_mode
from app.execution.adapters.traderspost import TradersPostAdapter

URL = "https://webhooks.traderspost.io/trading/webhook/abc/pw"


def make(handler):
    return TradersPostAdapter({"A": URL}, httpx.AsyncClient(transport=httpx.MockTransport(handler)), {"MNQ": "MNQ1!"})


async def test_bracket_payload_and_conservative_mode():
    sent = {}

    def h(req):
        sent.update(json.loads(req.content))
        return httpx.Response(200, json={"success": True, "id": "sig1"})

    tp = make(h)
    ack = await tp.place_bracket("A", BracketRequest("T1", "MNQ", "SELL", 2, D(20020), D(19940)))
    assert ack.bracket_id == "sig1"
    assert (sent["ticker"], sent["action"], sent["quantity"], sent["orderType"]) == ("MNQ1!", "sell", 2, "market")
    assert sent["takeProfit"] == {"limitPrice": 19940.0} and sent["stopLoss"] == {"type": "stop", "stopPrice": 20020.0}
    assert sent["rejectAfter"] == 10 and conservative_mode(tp) and tp.stream_pnl() is None
    assert await tp.modify_stop("A", "x", D(1)) is False
    with pytest.raises(NotSupported):
        await tp.get_positions("A")


async def test_errors():
    tp = make(lambda r: httpx.Response(400, json={"success": False, "messageCode": "invalid-action", "message": "bad"}))
    with pytest.raises(BrokerError, match="invalid-action"):
        await tp.flatten("A")
    with pytest.raises(BrokerError):
        TradersPostAdapter({"A": "https://evil.example/x"}, httpx.AsyncClient(), {})
