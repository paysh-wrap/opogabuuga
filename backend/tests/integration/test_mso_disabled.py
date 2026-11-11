"""D91: with BigBeluga MSO off, LunqFX can only run in SHADOW (button on or not); heartbeats need no mso snapshot."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.models import BiasDecision, Order, Signal, Trade
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


def test_control_with_mso_on_the_same_setup_passes(ready, clock):
    _set_mso(ready.app, True)
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN, close="20010")
    confirm(ready, clock)
    with ready.app.state.sessionmaker() as s:
        assert s.query(Signal).one().status == "PASS"


def test_mso_off_lunqfx_is_shadow_only_even_with_the_button_on(ready, clock, authed):
    _set_mso(ready.app, False)
    assert ready.app.state.rules.rules.strategy.lunqfx is True  # the LunqFX button is ON
    _heartbeat_without_mso(ready, clock, MS - 2 * MIN)  # heartbeat needs no mso snapshot: accepted (send asserts 200)
    confirm(ready, clock)
    with ready.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        assert sig.status in ("SHADOW", "SHADOWED") and not sig.passed and sig.skip_reason == "MSO_DISABLED"
        assert sig.features["shadow"]["outcome"] in ("PASS", "WAIT")  # it WOULD have traded; recorded only
        assert s.query(Order).count() == 0 and s.query(Trade).count() == 0
    # even an explicit execute of that signal is refused
    authed.app.state.controller.mode = "SEMI"
    res = authed.post(f"/api/signals/{sig.id}/execute", json={}).json()["results"]
    assert res[0]["ok"] is False and res[0]["reason"] == "SIGNAL_NOT_TRADEABLE"
    # stored gate chain has no G4-G6
    sigs = authed.get("/api/signals").json()["signals"]
    assert [g["gate"] for g in sigs[0]["gates"]] == ["G1", "G2", "G3", "G7", "SCORE"]


def test_mso_events_are_still_accepted_but_cannot_change_the_outcome(ready, clock):
    _set_mso(ready.app, False)
    choch(ready, clock)  # TradingView may still send them: accepted, ignored
    hb(ready, clock, MS - 2 * MIN)
    confirm(ready, clock)
    with ready.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        assert sig.status in ("SHADOW", "SHADOWED") and sig.skip_reason == "MSO_DISABLED"


def test_strategy_api_hides_mso_gates_and_labels_lunqfx_shadow_only(authed):
    _set_mso(authed.app, False)
    s = authed.get("/api/strategy").json()
    assert s["mso_enabled"] is False
    assert [g["id"] for g in s["gates"]] == ["G1", "G2", "G3", "G7", "G8"]
    assert s["indicators"] == ["ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]"]
    strategies = {x["key"]: x for x in authed.get("/api/strategies").json()["strategies"]}
    assert strategies["lunqfx"]["status"] == "SHADOW ONLY" and strategies["lunqfx"]["enabled"] is False
    assert "SHADOW" in strategies["lunqfx"]["note"]
    chain = {g["id"] for g in authed.get("/api/strategies").json()["gate_chain"]}
    assert not chain & {"G4", "G5", "G6"}
    _set_mso(authed.app, True)
    s = authed.get("/api/strategy").json()
    assert s["mso_enabled"] is True and [g["id"] for g in s["gates"]][3:6] == ["G4", "G5", "G6"]
    on = {x["key"]: x for x in authed.get("/api/strategies").json()["strategies"]}
    assert on["lunqfx"]["status"] != "SHADOW ONLY"
    assert {"G4", "G5", "G6"} <= {g["id"] for g in authed.get("/api/strategies").json()["gate_chain"]}


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
