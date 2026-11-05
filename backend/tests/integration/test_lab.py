from decimal import Decimal as D

from app.api.lab import session_progress


def test_session_progress_cumulative():
    s = session_progress([("d1", D(100), D(1)), ("d1", D(-50), D(-1)), ("d2", D(80), None)])
    assert s[0] == {
        "session": "d1",
        "trades": 2,
        "win_rate": 0.5,
        "net": "50",
        "avg_r": "0.000",
        "cum_win_rate": 0.5,
        "cum_net": "50",
    }
    assert s[1]["cum_win_rate"] == round(2 / 3, 4) and s[1]["avg_r"] is None and s[1]["cum_net"] == "130"


def test_lab_api_and_proposals(authed):
    r = authed.get("/api/lab").json()
    assert r["sessions"] == [] and r["backtests"] == [] and r["proposals"] == []
    pid = authed.post("/api/lab/proposals", json={"text": "Skip hour 09 ET"}).json()["id"]
    assert authed.put(f"/api/lab/proposals/{pid}", json={"status": "approved"}).json()["status"] == "approved"
    assert authed.put(f"/api/lab/proposals/{pid}", json={"status": "rejected"}).status_code == 409
    assert authed.put("/api/lab/proposals/999", json={"status": "rejected"}).status_code == 404
    assert authed.get("/api/lab").json()["proposals"][0]["status"] == "approved"
