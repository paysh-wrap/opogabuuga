def test_live_checklist_defaults_to_paper(authed):
    r = authed.get("/api/live").json()
    assert r["live"] is False and r["toggle_on"] is False
    checks = {c["check"]: c["ok"] for c in r["checklist"]}
    assert checks["server_allows_live"] is False and checks["broker_reads_back"] is True  # sim reads back
    assert checks["indicator_parity"] is False


def test_live_toggle_needs_phrase_and_off_is_one_click(authed):
    assert authed.put("/api/live", json={"enabled": True, "confirm": "yes"}).status_code == 422
    r = authed.put("/api/live", json={"enabled": True, "confirm": "I ACCEPT LIVE RISK"}).json()
    assert r["toggle_on"] is True and r["live"] is False  # still blocked by the rest of the checklist
    assert authed.put("/api/live", json={"enabled": False}).json()["toggle_on"] is False


def test_live_needs_login(client):
    assert client.get("/api/live").status_code == 401
