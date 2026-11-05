"""Risk API (§11, §19): settings save/validate/version/rollback, Impact Preview, Evaluation Mode, Firm Rules."""

from decimal import Decimal as D

from app.models import Account, AuditLog


def add_account(c, stage="EVAL", ext="LUCID1", eval_mode="inherit"):
    with c.app.state.sessionmaker() as s:
        a = Account(broker_account_id=ext, stage=stage, drawdown_type="eod", eval_mode=eval_mode)
        s.add(a)
        s.commit()
        return a.id


def test_get_settings_shows_validation_and_dll_tests(authed):
    b = authed.get("/api/risk/settings").json()
    assert b["version"] == 0 and b["validation"]["ok"]
    assert b["validation"]["dll_tests"]["funded"]["total"] == "596.90"
    assert b["settings"]["internal.risk_pct_ceiling"] == "0.11" and "eval.daily_loss_limit" not in b["settings"]


def test_save_versions_audit_and_engine_uses_new_value(authed):
    r = authed.put("/api/risk/settings", json={"changes": {"internal.max_trades_per_day": 4}, "note": "aggressive"})
    assert r.status_code == 200 and r.json()["version"] == 1
    assert authed.app.state.rules.rules.internal.max_trades_per_day == 4  # applies to the next NEW trade
    r = authed.put("/api/risk/settings", json={"changes": {"internal.risk_pct_floor": "0.06"}, "note": "safer"})
    assert r.json()["version"] == 2 and r.json()["settings"]["internal.max_trades_per_day"] == 4  # kept
    vs = authed.get("/api/risk/versions").json()["versions"]
    assert [(v["version"], v["active"]) for v in vs if v["kind"] == "standard"] == [(2, True), (1, False)]
    assert vs[0]["diff"] == {"internal.risk_pct_floor": {"from": "0.07", "to": "0.06"}}
    with authed.app.state.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="risk.settings_saved").count() == 2


def test_rollback(authed):
    authed.put("/api/risk/settings", json={"changes": {"internal.max_trades_per_day": 4}, "note": "a"})
    authed.put("/api/risk/settings", json={"changes": {"internal.max_trades_per_day": 2}, "note": "b"})
    r = authed.post("/api/risk/rollback/1")
    assert r.status_code == 200 and r.json()["version"] == 3
    assert authed.app.state.rules.rules.internal.max_trades_per_day == 4
    assert authed.post("/api/risk/rollback/99").status_code == 422


def test_invalid_changes_rejected_with_reasons(authed):
    r = authed.put(
        "/api/risk/settings",
        json={
            "changes": {
                "internal.risk_pct_ceiling": "0.13",
                "internal.risk_pct_by_score": {"60": "0.07", "75": "0.09", "90": "0.13"},
            },
            "confirm_over_11": True,
        },
    )
    assert r.status_code == 422 and any("DLL test funded" in e for e in r.json()["detail"]["errors"])
    r = authed.put("/api/risk/settings", json={"changes": {"eval.daily_loss_limit": 900}})
    assert r.status_code == 422 and "not editable" in r.json()["detail"]["errors"][0]
    r = authed.put("/api/risk/settings", json={"changes": {"internal.day_lockin_r": "0.5"}})
    assert r.status_code == 422
    assert authed.app.state.rules.standard_version == 0  # nothing saved


def test_over_11_percent_needs_second_confirmation(authed):
    ch = {
        "internal.risk_pct_ceiling": "0.115",
        "internal.risk_pct_by_score": {"60": "0.07", "75": "0.09", "90": "0.115"},
        "internal.dll_safety_margin": 30,
    }
    r = authed.put("/api/risk/settings", json={"changes": ch})
    assert r.status_code == 422 and "second confirmation" in r.json()["detail"]["errors"][0]
    r = authed.put("/api/risk/settings", json={"changes": ch, "confirm_over_11": True})
    assert r.status_code == 200, r.json()


def test_impact_preview_standard_and_eval_mode_spec(authed):
    p = authed.post("/api/risk/preview", json={"changes": {}}).json()["preview"]
    assert p["risk_by_tier"]["1000"] == {"60": "70.00", "75": "90.00", "90": "110.00"}
    assert p["risk_by_tier"]["3000"] == {"60": "210.00", "75": "270.00", "90": "330.00"}
    e = authed.post("/api/risk/eval-mode/preview").json()
    on = e["on"]
    assert on["risk_by_tier"]["1000"] == {"60": "100.00", "75": "120.00", "90": "140.00"}
    assert on["worst_day_at_1000"] == "226.00" and on["losses_to_pause_from_1000"] == 7
    assert on["monte_carlo"] is None and "Phase 8" in on["monte_carlo_note"]  # no made-up probabilities
    bad = authed.post("/api/risk/preview", json={"changes": {"internal.risk_pct_floor": "0.5"}}).json()
    assert bad["valid"] is False


def test_eval_mode_toggle_rules(authed):
    r = authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"})
    assert r.status_code == 422 and "no EVAL accounts" in r.json()["detail"]["errors"][0]
    add_account(authed)
    assert authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "yes"}).status_code == 422
    r = authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"})
    assert r.status_code == 200 and r.json()["enabled"] and r.json()["accounts"][0]["effective"]
    assert authed.app.state.rules.eval_mode_on
    r = authed.put("/api/risk/eval-mode", json={"enabled": False})  # disabling: one click, no phrase
    assert r.status_code == 200 and not r.json()["enabled"]


def test_account_override_eval_only(authed):
    eid, fid = add_account(authed), add_account(authed, stage="FUNDED", ext="LUCID2")
    assert authed.patch(f"/api/accounts/{eid}/eval-mode", json={"override": "on"}).json()["effective"] is True
    assert authed.patch(f"/api/accounts/{fid}/eval-mode", json={"override": "on"}).status_code == 422
    assert authed.patch(f"/api/accounts/{eid}/eval-mode", json={"override": "maybe"}).status_code == 422
    assert authed.patch("/api/accounts/999/eval-mode", json={"override": "off"}).status_code == 404
    accts = authed.get("/api/accounts").json()["accounts"]
    assert [(a["stage"], a["eval_mode_effective"]) for a in accts] == [("EVAL", True), ("FUNDED", False)]


def test_firm_rules_typed_phrase_note_and_verify_badges(authed):
    before = authed.get("/api/rules").json()
    assert "eval.daily_loss_limit" in before["verify_paths"]
    r = authed.put("/api/rules", json={"verify": ["eval.daily_loss_limit"], "confirm": "update", "note": "x"})
    assert r.status_code == 422
    r = authed.put("/api/rules", json={"verify": ["eval.daily_loss_limit"], "confirm": "UPDATE FIRM RULES", "note": ""})
    assert r.status_code == 422
    r = authed.put(
        "/api/rules",
        json={
            "changes": {"instruments.MNQ.fee_rt": "1.04"},
            "verify": ["eval.daily_loss_limit", "instruments.MNQ"],
            "confirm": "UPDATE FIRM RULES",
            "note": "checked dashboard",
        },
    )
    assert r.status_code == 200 and r.json()["firm_version"] == 1
    after = authed.get("/api/rules").json()
    assert "eval.daily_loss_limit" not in after["verify_paths"] and "eval.daily_loss_limit" in after["verified_paths"]
    assert authed.app.state.rules.rules.instruments["MNQ"].fee_rt == D("1.04")
    r = authed.put(
        "/api/rules",
        json={"changes": {"internal.risk_pct_floor": "0.01"}, "confirm": "UPDATE FIRM RULES", "note": "sneaky"},
    )
    assert r.status_code == 422  # My Settings can't be changed through Firm Rules


def test_settings_survive_restart(settings, clock, mock_http):
    from fastapi.testclient import TestClient

    from app.auth import create_user
    from app.main import create_app
    from tests.conftest import PASSWORD

    app1 = create_app(settings, clock)
    with TestClient(app1) as c:
        with app1.state.sessionmaker() as s:
            create_user(s, "PayDay", PASSWORD)
            s.commit()
        csrf = c.post("/api/auth/login", json={"username": "PayDay", "password": PASSWORD}).json()["csrf"]
        c.headers["x-csrf-token"] = csrf
        assert c.put("/api/risk/settings", json={"changes": {"internal.max_trades_per_day": 2}}).status_code == 200
    app2 = create_app(settings, clock)
    with TestClient(app2):
        assert app2.state.rules.rules.internal.max_trades_per_day == 2 and app2.state.rules.standard_version == 1


def test_structural_errors_and_list_values(authed):
    r = authed.put("/api/risk/settings", json={"changes": {"internal.max_trades_per_day": "lots"}})
    assert r.status_code == 422 and "max_trades_per_day" in r.json()["detail"]["errors"][0]
    r = authed.put(
        "/api/risk/settings", json={"changes": {"internal.windows": [["06:45", "09:30"], ["13:30", "15:30"]]}}
    )
    assert r.status_code == 200 and authed.app.state.rules.rules.internal.windows == [
        ("06:45", "09:30"),
        ("13:30", "15:30"),
    ]


def test_invalid_stored_settings_block_and_report(authed):
    """If a stored version stops validating (e.g. YAML changed), the holder reports an error instead of trading."""
    from app.models import RiskProfile

    with authed.app.state.sessionmaker() as s:
        s.add(
            RiskProfile(
                kind="standard",
                version=1,
                settings={"internal.day_lockin_r": "0.2"},
                author="x",
                note="",
                diff={},
                active=True,
            )
        )
        s.commit()
        authed.app.state.rules.refresh(s)
    h = authed.app.state.rules
    assert h.error and "day lock-in" in h.error and authed.get("/api/rules").json()["error"] == h.error
    assert h.source_text.startswith("# Paytience rule profile")


def test_market_buttons_toggle_instruments(authed):
    m = {x["symbol"]: x["enabled"] for x in authed.get("/api/markets").json()["markets"]}
    assert m == {"MGC": False, "MNQ": True}
    r = authed.put("/api/markets", json={"symbol": "MGC", "enabled": True}).json()
    assert {x["symbol"]: x["enabled"] for x in r["markets"]}["MGC"] is True
    assert authed.app.state.rules.rules.instruments["MGC"].enabled
    authed.put("/api/risk/settings", json={"changes": {"one_to_one_mode.enabled": True}})  # survives other saves
    assert authed.app.state.rules.rules.instruments["MGC"].enabled
    assert authed.put("/api/markets", json={"symbol": "XYZ", "enabled": True}).status_code == 404


def test_plan_switch(authed):
    from app.risk.holder import RULES_DIR

    r = authed.get("/api/plans").json()
    assert r["current"] == "lucid_daily_25k" and any(p["id"] == "lucid_daily_25k" for p in r["plans"])
    assert authed.put("/api/plans", json={"plan": "nope"}).status_code == 404
    alt = RULES_DIR / "zz_test_plan.yaml"
    alt.write_text((RULES_DIR / "lucid_daily_25k.yaml").read_text())
    try:
        assert authed.put("/api/plans", json={"plan": "zz_test_plan"}).json()["current"] == "zz_test_plan"
        alt.unlink()
        h = authed.app.state.rules
        with authed.app.state.sessionmaker() as s:
            from app.automation.state import set_setting

            set_setting(s, "rules.plan", "zz_missing", authed.app.state.clock.now())
            s.commit()
            h.refresh(s)
        assert h.error and "not found" in h.error
    finally:
        alt.unlink(missing_ok=True)
