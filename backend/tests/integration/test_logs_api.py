"""GET /api/logs — read-only audit search."""

from fastapi.testclient import TestClient


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/logs").status_code == 401


def test_search_filter_and_chain(authed: TestClient) -> None:
    authed.post("/api/cooldowns/TIGHT/clear", json={"confirm": "CLEAR COOLDOWN"})
    r = authed.get("/api/logs").json()
    assert r["chain_ok"] is True and r["chain_first_bad_id"] is None
    assert "cooldown.cleared" in r["actions"]
    assert any(x["action"] == "cooldown.cleared" for x in r["logs"])
    assert authed.get("/api/logs", params={"action": "nope"}).json()["logs"] == []
    hit = authed.get("/api/logs", params={"q": "TIGHT", "since": "2000-01-01", "until": "2999-01-01", "limit": 5}).json()
    assert any(x["entity"] == "TIGHT" for x in hit["logs"])
    assert authed.get("/api/logs", params={"q": "zzzzqq"}).json()["logs"] == []
    assert authed.get("/api/logs", params={"since": "2999-01-01"}).json()["logs"] == []
