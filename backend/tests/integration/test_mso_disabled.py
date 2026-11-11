"""D91: BigBeluga MSO off - heartbeats need no mso snapshot, the MSO defence does nothing (D105: LunqFX removed)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.models import BiasDecision
from tests.conftest import WEBHOOK_SECRET
from tests.integration.test_signals_flow import AT, FR, MIN, MS, choch, confirm, hb, send  # noqa: F401


def _set_mso(app, enabled: bool) -> None:
    h = app.state.rules
    ind = h.rules.indicators
    h.rules = h.rules.model_copy(
        update={"indicators": ind.model_copy(update={"mso": ind.mso.model_copy(update={"enabled": enabled})})}
    )


@pytest.fixture
def ready(client, clock):
    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    client.app.state.calendar = lambda d: []
    return client


def _heartbeat_without_mso(c, clock, t_ms, close="20010"):
    return send(c, clock, "HEARTBEAT", t_ms, "NONE", price={"o": close, "h": close, "l": close, "c": close, "v": "1"})


def test_strategy_api_reports_mso_state_and_lists_no_lunqfx(authed):
    """D91 + D105: the MSO switch is reported, its divergence row hides when off; LunqFX is gone from the catalog."""
    _set_mso(authed.app, False)
    s = authed.get("/api/strategy").json()
    assert s["mso_enabled"] is False and "gates" not in s and "indicators" not in s
    body = authed.get("/api/strategies").json()
    assert "lunqfx" not in {x["key"] for x in body["strategies"]}
    assert "gate_chain" not in body  # D106: per-strategy gates endpoint instead
    _set_mso(authed.app, True)
    assert authed.get("/api/strategy").json()["mso_enabled"] is True


def test_half_off_defence_does_nothing_without_mso(authed, clock):
    _set_mso(authed.app, False)
    ctl = authed.app.state.controller
    ctl.om.trades["t"] = SimpleNamespace(symbol="MNQ", strategy="", boom=True)  # would raise if it were inspected
    asyncio.run(ctl.defence_check("MNQ", 1, 1, {"trend": "BEAR"}, [("MSO_CHOCH", "SHORT", 1)]))
    ctl.om.trades.clear()


def test_a_heartbeat_with_no_mso_is_a_valid_payload(client, clock):
    clock.set(AT)
    p = {
        "v": 1,
        "secret": WEBHOOK_SECRET,
        "id": "MNQ1!-TIGHT-1-HEARTBEAT-NONE",
        "symbol": "MNQ1!",
        "profile": "TIGHT",
        "tf": "1",
        "bar_time_ms": MS,
        "event": "HEARTBEAT",
        "direction": "NONE",
        "price": {"o": "1", "h": "1", "l": "1", "c": "1", "v": "1"},
    }
    r = client.post("/api/webhook/tradingview", content=json.dumps(p), headers={"content-type": "text/plain"})
    assert r.status_code == 200, r.text
