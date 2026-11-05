"""Phase 5 end to end on paper: signal → SEMI approval → execute → fills → close; kill switch; flat time."""

from datetime import UTC, datetime

from app.models import Account, BiasDecision, Signal, Trade
from tests.integration.test_signals_flow import AT, MIN, MS, choch, confirm, hb


def setup(authed, clock):
    authed.app.state.calendar = lambda d: []
    with authed.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "E1", "stage": "EVAL"}).json()["id"]
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
    assert authed.post("/api/attestation", json={"confirm": True}).json()["attested_today"]
    return aid


def test_semi_auto_full_paper_lifecycle(authed, clock):
    setup(authed, clock)
    ctl = authed.app.state.controller
    ctl.mode = "SEMI"  # pre-flight needs live feeds; mode set directly for this flow test
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
    assert sig.status == "PASS" and sig.id in ctl.approvals  # waits for the user
    r = authed.post(f"/api/signals/{sig.id}/execute", json={}).json()["results"]
    assert r[0]["ok"] and r[0]["contracts"] >= 1, r
    pos = authed.get("/api/positions").json()["accounts"][0]["positions"]
    assert pos and pos[0]["qty"] > 0
    hb(authed, clock, MS - MIN, close="20071")  # through the 2R target (20070)
    t = authed.get("/api/trades").json()["trades"][0]
    assert t["exit_reason"] == "TP" and float(t["pnl"]) > 0 and float(t["net_r"]) > 1.5
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []


def test_kill_switch_flattens_disarms_and_turns_off(authed, clock):
    aid = setup(authed, clock)
    ctl = authed.app.state.controller
    ctl.mode = "FULL"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)  # FULL → executes immediately
    assert authed.get("/api/positions").json()["accounts"][0]["positions"]
    assert authed.post("/api/kill-switch", json={"confirm": "nope"}).status_code == 422
    assert authed.post("/api/kill-switch", json={"confirm": "KILL"}).status_code == 200
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []
    assert ctl.mode == "OFF"
    with authed.app.state.sessionmaker() as s:
        a = s.get(Account, aid)
        assert not a.armed and a.paused_reason == "KILL_SWITCH"
        assert s.query(Trade).one().exit_reason == "KILL_SWITCH"
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True}).status_code == 409  # never auto-resumes


def test_slippage_past_2r_is_flattened_immediately(authed, clock):
    setup(authed, clock)
    authed.app.state.controller.mode = "FULL"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20010")  # exactly 2R; 1 tick slippage → 1.98R
    confirm(authed, clock)
    assert authed.get("/api/trades").json()["trades"][0]["exit_reason"] == "RR_INVALID_AFTER_FILL"


def test_full_auto_requires_preflight(authed, clock):
    setup(authed, clock)
    r = authed.put("/api/automation", json={"mode": "FULL"})
    assert r.status_code == 409 and "pre-flight failed" in r.json()["detail"]["errors"][0]


def test_flat_time_blocks_entries(authed, clock):
    setup(authed, clock)
    clock.set(datetime(2026, 11, 5, 21, 41, tzinfo=UTC))  # 16:41 ET
    assert authed.app.state.controller.entries_blocked_by_time()
    assert authed.post("/api/signals/1/execute", json={}).status_code == 409
