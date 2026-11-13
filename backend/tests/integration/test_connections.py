import json
import stat

import httpx
import pytest

from app.models import ApiCredential, AuditLog


def _get(c, pid):
    return next(x for x in c.get("/api/connections").json()["connections"] if x["id"] == pid)


def test_lists_every_service_with_links(authed, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(200, json=[{"name": "v0.7.1"}])
    body = authed.get("/api/connections").json()
    ids = {c["id"] for c in body["connections"]}
    assert {
        "tradingview",
        "tradingagents",
        "tradovate",
        "lucid",
        "databento",
        "fincept",
        "openbb",
        "forexfactory",
        "crosstrade",
        "discord",
        "tunnel",
        "alpha_vantage",
        "fred",
    } <= ids
    assert all(c["links"] and c["links"][0]["url"].startswith("https://") for c in body["connections"])
    ta = _get(authed, "tradingagents")
    assert any("github.com/TauricResearch/TradingAgents" in lk["url"] for lk in ta["links"])
    assert ta["pinned_version"] == "0.7.1" and ta["latest_tag"] == "v0.7.1"
    assert ta["status"] == "not_set"
    assert ta["llm_key_urls"]["anthropic"] == "https://console.anthropic.com/settings/keys"
    assert set(ta["llm_key_urls"]) == set(ta["fields"][0]["options"])
    assert _get(authed, "tradingview")["status"] == "waiting"
    lucid = _get(authed, "lucid")
    assert lucid["status"] == "link" and lucid["detail"] == "" and "never logs into Lucid" in lucid["note"]
    names = [i["name"] for i in body["indicators"]]
    assert names == []  # D105 LunqFX card + D113 BigBeluga card removed


def test_save_test_connected_then_failed_is_write_only(authed, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    key = "db-SECRETKEY-ABCDEFGH1234"
    seen = {}

    def databento(req):
        seen["auth"] = req.headers["authorization"]
        return httpx.Response(200, text='["GLBX.MDP3","XNAS.ITCH"]')

    mock_http["https://hist.databento.com/"] = databento
    r = authed.put("/api/connections/databento", json={"values": {"api_key": key}})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["status"] == "connected" and "GLBX.MDP3" in v["detail"]
    assert v["hints"] == {"api_key": "••••1234"}
    full = authed.get("/api/connections").text
    assert key not in full and "SECRETKEY" not in full  # never returned
    with authed.app.state.sessionmaker() as s:
        row = s.query(ApiCredential).filter_by(provider="databento").one()
        assert key not in row.ciphertext  # encrypted at rest
        assert key not in json.dumps([a.payload for a in s.query(AuditLog)])  # never audited
    # key revoked → re-test turns red
    mock_http["https://hist.databento.com/"] = lambda req: httpx.Response(401)
    v = authed.post("/api/connections/databento/test").json()
    assert v["status"] == "failed" and "rejected" in v["detail"]
    bad = '{"detail":{"case":"auth_invalid"}}'
    mock_http["https://hist.databento.com/"] = lambda req: httpx.Response(400, text=bad)
    v = authed.post("/api/connections/databento/test").json()
    assert v["status"] == "failed" and "db-" in v["detail"]
    # blank secret on re-save keeps the stored key
    mock_http["https://hist.databento.com/"] = databento
    v = authed.put("/api/connections/databento", json={"values": {"api_key": ""}}).json()
    assert v["status"] == "connected"
    assert authed.delete("/api/connections/databento").json()["status"] == "not_set"


def test_key_quoted_back_by_the_service_is_redacted(authed, mock_http):
    """Review fix (session 22 E2E): Alpha Vantage quotes the key in its error text; the app relayed it to the page."""
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    key = "AV-SECRET-KEY-998877"
    info = f"We have detected your API key as {key} and our standard API rate limit is 25 requests per day."
    mock_http["https://www.alphavantage.co/"] = lambda req: httpx.Response(200, json={"Information": info})
    v = authed.put("/api/connections/alpha_vantage", json={"values": {"api_key": key}}).json()
    assert v["status"] == "failed" and "detected your API key as •••" in v["detail"], v
    assert key not in authed.get("/api/connections").text
    assert key not in authed.post("/api/connections/alpha_vantage/test").text
    with authed.app.state.sessionmaker() as s:
        assert key not in json.dumps([a.payload for a in s.query(AuditLog)])


def test_validation_errors(authed, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    assert authed.put("/api/connections/discord", json={"values": {}}).status_code == 422
    assert authed.put("/api/connections/discord", json={"values": {"webhook_url": "x", "evil": "1"}}).status_code == 422
    assert authed.put("/api/connections/nope", json={"values": {}}).status_code == 404
    v = authed.put("/api/connections/discord", json={"values": {"webhook_url": "https://evil.example/x"}}).json()
    assert v["status"] == "failed"
    v = authed.put("/api/connections/tradingagents", json={"values": {"llm_provider": "notreal", "api_key": "k" * 20}})
    assert v.status_code == 422


def test_tunnel_reacts_when_reachable(authed, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    mock_http["https://pt.example.com/api/health"] = lambda r: httpx.Response(200, json={"app": "paytience"})
    v = authed.put("/api/connections/tunnel", json={"values": {"public_url": "https://pt.example.com"}}).json()
    assert v["status"] == "connected" and v["hints"]["public_url"] == "https://pt.example.com"
    v = authed.put("/api/connections/tunnel", json={"values": {"public_url": "http://pt.example.com"}}).json()
    assert v["status"] == "failed"


@pytest.fixture
def fake_ta(tmp_path, authed):
    script = tmp_path / "fake-ta-python"
    script.write_text('#!/bin/sh\ncat >/dev/null\necho \'{"ok": true, "version": "0.7.1"}\'\n')
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    authed.app.state.ta.python_bin = str(script)
    return authed


def test_tradingagents_connects_with_valid_llm_key(fake_ta, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(200, json=[{"name": "v0.7.1"}])
    mock_http["https://api.anthropic.com/v1/models"] = lambda r: httpx.Response(
        200 if r.headers.get("x-api-key") == "good-key-123456" else 401
    )
    v = fake_ta.put(
        "/api/connections/tradingagents", json={"values": {"llm_provider": "anthropic", "api_key": "bad-key-1234567"}}
    ).json()
    assert v["status"] == "failed"
    v = fake_ta.put(
        "/api/connections/tradingagents", json={"values": {"llm_provider": "anthropic", "api_key": "good-key-123456"}}
    ).json()
    assert v["status"] == "connected" and "0.7.1" in v["detail"]
    assert v["installed_version"] == "0.7.1"
    assert any(lk["url"] == "https://console.anthropic.com/settings/keys" for lk in v["links"])


def test_tradingagents_version_mismatch_fails(fake_ta, mock_http, tmp_path):
    script = tmp_path / "old-ta"
    script.write_text('#!/bin/sh\ncat >/dev/null\necho \'{"ok": true, "version": "0.6.0"}\'\n')
    script.chmod(0o755)
    fake_ta.app.state.ta.python_bin = str(script)
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    v = fake_ta.put(
        "/api/connections/tradingagents", json={"values": {"llm_provider": "openai", "api_key": "sk-1234567890ab"}}
    ).json()
    assert v["status"] == "failed" and "pinned 0.7.1" in v["detail"]


def test_indicator_cards_removed(authed, mock_http):
    src = "// This work is licensed under Attribution-NonCommercial-ShareAlike 4.0\n//@version=6\nindicator('x')"
    assert authed.put("/api/indicators/bigbeluga_mso", json={"source": src}).status_code == 404  # D113: removed
    assert authed.put("/api/indicators/lunqfx", json={"source": src}).status_code == 404  # D105: removed


def test_websocket_pushes_connection_updates(authed, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    mock_http["https://pt.example.com/"] = lambda r: httpx.Response(200, json={"app": "paytience"})
    with authed.websocket_connect("/ws") as ws:
        authed.put("/api/connections/tunnel", json={"values": {"public_url": "https://pt.example.com"}})
        msg = ws.receive_json()
        assert msg == {
            "event": "connection.updated",
            "data": {"id": "tunnel", "status": "connected", "detail": msg["data"]["detail"]},
        }


def test_websocket_rejects_anonymous(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws") as ws:
        ws.receive_text()


def test_master_key_missing_is_loud(authed, mock_http):
    from pydantic import SecretStr

    authed.app.state.settings.master_key = SecretStr("")
    r = authed.put("/api/connections/discord", json={"values": {"webhook_url": "https://discord.com/api/webhooks/1/x"}})
    assert r.status_code == 503 and "make keys" in r.json()["detail"]


def test_crosstrade_key_test(authed, mock_http):
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    mock_http["https://app.crosstrade.io/v1/api/tv/status"] = lambda r: (
        httpx.Response(200, json={"success": True})
        if r.headers["authorization"] == "Bearer good-key-12345"
        else httpx.Response(401, json={"success": False, "error": "api_requires_pro"})
    )
    v = authed.put("/api/connections/crosstrade", json={"values": {"token": "bad-key-1234567"}}).json()
    assert v["status"] == "failed" and "api_requires_pro" in v["detail"]
    v = authed.put("/api/connections/crosstrade", json={"values": {"token": "good-key-12345"}}).json()
    assert v["status"] == "connected"


def test_openbb_keys_are_optional_and_reach_the_openbb_process(authed, monkeypatch):
    r = authed.put("/api/connections/openbb", json={"values": {"pat": "pat-secret-123"}})  # FMP/Polygon left empty
    assert r.status_code == 200, r.text
    assert "pat-secret-123" not in r.text  # never echoed back
    seen = {}

    async def fake_exec(*args, **kw):
        seen.update(kw.get("env") or {})
        raise OSError("stop here")  # don't run uvx in tests

    import asyncio

    from app.market import openbb_feed

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    st = authed.app.state
    st.openbb = openbb_feed.OpenBBFeed(uvx="/usr/bin/true")
    authed.get("/api/market/openbb")  # loads the saved keys, starts a refresh
    authed.portal.call(st.openbb.refresh)
    assert seen.get("PB_OPENBB_PAT") == "pat-secret-123" and "PB_FMP_API_KEY" not in seen


def test_ngrok_card_validates_domain_and_never_returns_token(authed, mock_http, monkeypatch):
    from app import tunnel

    async def fake_verify(tools, token, domain, **kw):
        return (token == "good-token", "Token accepted" if token == "good-token" else "authtoken rejected")

    monkeypatch.setattr(tunnel, "verify_ngrok", fake_verify)
    mock_http["https://api.github.com/"] = lambda r: httpx.Response(404)
    bad = authed.put("/api/connections/ngrok", json={"values": {"authtoken": "x", "domain": "evil.com"}})
    assert bad.status_code == 422
    v = authed.put(
        "/api/connections/ngrok", json={"values": {"authtoken": "good-token", "domain": "https://Me.ngrok-free.app/"}}
    ).json()
    assert v["status"] == "connected" and v["hints"]["domain"] == "me.ngrok-free.app"
    assert "good-token" not in str(v) and v["tunnel"]["mode"] == "none"
    v = authed.put(
        "/api/connections/ngrok", json={"values": {"authtoken": "wrong", "domain": "me.ngrok-free.app"}}
    ).json()
    assert v["status"] == "failed" and "rejected" in v["detail"]
    assert authed.delete("/api/connections/ngrok").status_code == 200


def test_ngrok_tester_reuses_running_manager(tmp_path):
    import asyncio

    from app import tunnel
    from app.connections.testers import _ngrok

    class M:
        state = tunnel.TunnelState("ngrok", "me.ngrok-free.app")

    tunnel.ACTIVE = M()  # type: ignore[assignment]
    try:
        r = asyncio.run(_ngrok({"authtoken": "t", "domain": "me.ngrok-free.app"}, None))  # type: ignore[arg-type]
    finally:
        tunnel.ACTIVE = None
    assert r.ok and "permanent" in r.detail


def test_ngrok_tester_reports_run_failure(monkeypatch):
    import asyncio

    from app import tunnel
    from app.connections.testers import _ngrok

    async def boom(*a, **k):
        raise OSError("x")

    monkeypatch.setattr(tunnel, "verify_ngrok", boom)

    class M:
        state = tunnel.TunnelState()
        killed = poked = False

        def _kill(self):
            self.killed = True

        def poke(self):
            self.poked = True

    m = M()
    tunnel.ACTIVE = m  # type: ignore[assignment]
    try:
        r = asyncio.run(_ngrok({"authtoken": "t", "domain": "me.ngrok-free.app"}, None))  # type: ignore[arg-type]
    finally:
        tunnel.ACTIVE = None
    assert not r.ok and "OSError" in r.detail and m.killed and m.poked
