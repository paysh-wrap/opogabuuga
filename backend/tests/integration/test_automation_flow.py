"""Phase 5 end to end on paper: signal → SEMI approval → execute → fills → close; kill switch; flat time."""

from datetime import UTC, datetime

from app.models import Account, BiasDecision, Order, Signal, Trade
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
    res = authed.get("/api/signals").json()["signals"][0]["results"]  # §18 per-account result on the signal
    assert len(res) == 1 and res[0]["account"] == "E1" and res[0]["exit_reason"] == "TP" and not res[0]["open"]
    assert float(res[0]["gross_r"]) >= float(res[0]["net_r"]) > 1.5 and res[0]["risk_profile"] and "guard_on" in res[0]
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


def test_slippage_below_min_rr_is_flattened_immediately(authed, clock):
    setup(authed, clock)
    authed.app.state.controller.mode = "FULL"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20012.5")  # 1.77R; 1 tick slippage → 1.748R < 1.75 (D35)
    confirm(authed, clock)
    assert authed.get("/api/trades").json()["trades"][0]["exit_reason"] == "RR_INVALID_AFTER_FILL"


def test_full_auto_requires_preflight(authed, clock):
    setup(authed, clock)
    r = authed.put("/api/automation", json={"mode": "FULL"})
    assert r.status_code == 409 and "pre-flight failed" in r.json()["detail"]["errors"][0]


def test_arming_a_new_stage_account_downgrades_full_to_semi(authed, clock):
    """§13: first N sessions of each stage run OFF/SEMI only — also when the account is armed AFTER FULL was set."""
    clock.set(AT)
    ctl = authed.app.state.controller
    ctl.mode = "FULL"  # e.g. set while no account was armed (allowed_mode had nothing to check)
    aid = authed.post("/api/accounts", json={"label": "E9", "stage": "EVAL"}).json()["id"]
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True}).status_code == 200
    assert ctl.mode == "SEMI" and authed.get("/api/automation").json()["mode"] == "SEMI"
    with authed.app.state.sessionmaker() as s:
        from app.models import AuditLog

        assert s.query(AuditLog).filter(AuditLog.action == "automation.mode", AuditLog.entity == "SEMI").count() == 1


def test_flat_time_blocks_entries(authed, clock):
    setup(authed, clock)
    clock.set(datetime(2026, 11, 5, 21, 41, tzinfo=UTC))  # 16:41 ET
    assert authed.app.state.controller.entries_blocked_by_time()
    assert authed.post("/api/signals/1/execute", json={}).status_code == 409


def test_mode_override_semi_needs_approval_even_in_full(authed, clock):
    """§13 per-account override (only more restrictive): SEMI → never auto-executed, waits for approval."""
    aid = setup(authed, clock)
    assert authed.patch(f"/api/accounts/{aid}", json={"mode_override": "SEMI"}).json()["mode_override"] == "SEMI"
    assert authed.get("/api/accounts").json()["accounts"][0]["mode_override"] == "SEMI"
    ctl = authed.app.state.controller
    ctl.mode = "FULL"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []  # not auto-executed
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
    assert sig.id in ctl.approvals
    r = authed.post(f"/api/signals/{sig.id}/execute", json={}).json()["results"]
    assert r[0]["ok"], r
    assert authed.get("/api/positions").json()["accounts"][0]["positions"]
    again = authed.post(f"/api/signals/{sig.id}/execute", json={}).json()["results"]  # double click
    assert again == [
        {"account_id": 0, "ok": False, "reason": "APPROVAL_EXPIRED", "contracts": 0, "trade_ref": None, "checks": []}
    ]


def test_full_mode_approval_never_retrades_auto_executed_accounts(authed, clock):
    """Review fix: FULL auto-executes 'inherit' accounts and queues an approval for SEMI-override ones; approving it
    later — even after the global mode changed to SEMI — trades ONLY the SEMI account, never the first one again."""
    a1 = setup(authed, clock)
    a2 = authed.post("/api/accounts", json={"label": "E2", "stage": "EVAL"}).json()["id"]
    r2 = authed.patch(f"/api/accounts/{a2}", json={"armed": True, "selected": True, "mode_override": "SEMI"})
    assert r2.status_code == 200, r2.text
    ctl = authed.app.state.controller
    ctl.mode = "FULL"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        assert {o.account_id for o in s.query(Order)} == {a1}  # only the 'inherit' account was auto-executed
    assert ctl.approvals[sig.id].mode == "FULL"
    ctl.mode = "SEMI"  # user switches the global mode before approving
    r = authed.post(f"/api/signals/{sig.id}/execute", json={}).json()["results"]
    assert [x["account_id"] for x in r if x["ok"]] == [a2], r
    with authed.app.state.sessionmaker() as s:
        assert sorted(o.account_id for o in s.query(Order)) == [a1, a2]  # one entry each, no re-entry for a1


def test_expired_approval_and_already_traded_are_refused(authed, clock):
    from app.automation.controller import Approval

    setup(authed, clock)
    ctl = authed.app.state.controller
    ctl.mode = "SEMI"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sid = s.query(Signal).one().id
    ap = ctl.approvals[sid]
    clock.set(ap.expires)  # too late
    assert authed.post(f"/api/signals/{sid}/execute", json={}).json()["results"][0]["reason"] == "APPROVAL_EXPIRED"
    clock.set(ap.created)
    ctl.approvals[sid] = ap
    assert authed.post(f"/api/signals/{sid}/execute", json={}).json()["results"][0]["ok"]
    ctl.approvals[sid] = Approval(sid, ap.created, ap.expires)  # even with a fresh approval: one entry per model
    assert authed.post(f"/api/signals/{sid}/execute", json={}).json()["results"][0]["reason"] == "ALREADY_TRADED"


def test_mode_override_off_never_trades_but_inherit_restores(authed, clock):
    aid = setup(authed, clock)
    assert authed.patch(f"/api/accounts/{aid}", json={"mode_override": "OFF"}).status_code == 200
    assert authed.patch(f"/api/accounts/{aid}", json={"mode_override": "FULL"}).status_code == 422  # never looser
    ctl = authed.app.state.controller
    ctl.mode = "SEMI"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sid = s.query(Signal).one().id
    ap = ctl.approvals[sid]
    assert authed.post(f"/api/signals/{sid}/execute", json={}).json()["results"] == []  # OFF account excluded
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []
    authed.patch(f"/api/accounts/{aid}", json={"mode_override": "inherit"})
    with authed.app.state.sessionmaker() as s:
        assert s.get(Account, aid).mode_override is None
    assert authed.post(f"/api/signals/{sid}/execute", json={}).json()["results"][0]["reason"] == "APPROVAL_EXPIRED"
    ctl.approvals[sid] = ap  # the next approval for this account trades again
    assert authed.post(f"/api/signals/{sid}/execute", json={}).json()["results"][0]["ok"]
