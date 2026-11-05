"""Risk management API (§11, §19): My Settings, Impact Preview, versions/rollback, Evaluation Mode, Firm Rules."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.models import Account, RiskProfile, RuleProfile
from app.phases.phase_engine import stage_rules
from app.risk import settings_store as ss
from app.risk.eval_mode import eval_mode_effective
from app.risk.validation import validate

router = APIRouter(prefix="/api")


def _err(e: ss.SettingsError) -> HTTPException:
    return HTTPException(422, {"errors": e.errors, "warnings": e.validation.warnings if e.validation else []})


def _settings_view(request: Request) -> dict[str, Any]:
    h = request.app.state.rules
    r = h.rules
    v = validate(r)
    current = {k: ss._norm(ss._get(r.model_dump(), k)) for k in sorted(ss.MY_SETTINGS_KEYS)}
    return {
        "version": h.standard_version,
        "settings": current,
        "editable_keys": sorted(ss.MY_SETTINGS_KEYS),
        "validation": {"ok": v.ok, "errors": v.errors, "warnings": v.warnings, "dll_tests": v.dll_tests},
        "eval_mode_on": h.eval_mode_on,
        "error": h.error,
    }


@router.get("/risk/settings")
def get_settings_(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    return _settings_view(request)


class SaveIn(BaseModel):
    changes: dict[str, Any]
    note: str = ""
    confirm_over_11: bool = False


@router.put("/risk/settings")
async def put_settings(
    body: SaveIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    try:
        row, _ = ss.save_my_settings(
            db, st.rules.base, st.clock, p.user.username, body.changes, body.note, body.confirm_over_11
        )
    except ss.SettingsError as e:
        raise _err(e) from e
    db.commit()
    st.rules.refresh(db)
    await st.hub.broadcast("risk.settings_changed", {"version": row.version})
    return _settings_view(request)


class PreviewIn(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    kind: str = "standard"


@router.post("/risk/preview")
def preview(
    body: PreviewIn, request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Instant Impact Preview of unsaved changes (nothing is stored)."""
    st = request.app.state
    bad = sorted(set(body.changes) - ss.MY_SETTINGS_KEYS)
    if bad:
        raise HTTPException(422, {"errors": [f"not editable: {', '.join(bad)}"], "warnings": []})
    cur = ss.latest(db, "standard")
    firm = ss.latest_firm(db)
    merged = {**(cur.settings if cur else {}), **{k: ss._norm(v) for k, v in body.changes.items()}}
    try:
        cfg, v = ss.build(ss.merged_raw(st.rules.base, firm.body_overrides() if firm else {}, merged))
    except ss.SettingsError as e:
        return {"valid": False, "errors": e.errors, "warnings": e.validation.warnings if e.validation else []}
    return {
        "valid": True,
        "errors": [],
        "warnings": v.warnings,
        "needs_second_confirmation": v.needs_second_confirmation,
        "preview": ss.impact_preview(cfg, "evaluation" if body.kind == "evaluation" else "standard"),
    }


@router.get("/risk/versions")
def versions(_: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.execute(select(RiskProfile).order_by(RiskProfile.kind, RiskProfile.version.desc())).scalars()
    return {
        "versions": [
            {
                "kind": r.kind,
                "version": r.version,
                "author": r.author,
                "note": r.note,
                "diff": r.diff,
                "active": r.active,
                "at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@router.post("/risk/rollback/{version}")
async def do_rollback(
    version: int, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    try:
        ss.rollback(db, st.rules.base, st.clock, p.user.username, version)
    except ss.SettingsError as e:
        raise _err(e) from e
    db.commit()
    st.rules.refresh(db)
    await st.hub.broadcast("risk.settings_changed", {"version": st.rules.standard_version})
    return _settings_view(request)


# ---------- Evaluation Mode (§11C) ----------
def _eval_accounts(db: Session) -> list[Account]:
    return list(db.execute(select(Account).where(Account.stage == "EVAL")).scalars())


@router.get("/risk/eval-mode")
def get_eval_mode(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    on = request.app.state.rules.eval_mode_on
    accts = _eval_accounts(db)
    return {
        "enabled": on,
        "has_eval_accounts": bool(accts),
        "confirm_phrase": ss.EVAL_MODE_PHRASE,
        "accounts": [
            {
                "id": a.id,
                "label": a.label or a.broker_account_id,
                "override": a.eval_mode,
                "effective": eval_mode_effective(a.stage, a.eval_mode, on),
            }
            for a in accts
        ],
    }


class EvalModeIn(BaseModel):
    enabled: bool
    confirm: str = ""


@router.put("/risk/eval-mode")
async def put_eval_mode(
    body: EvalModeIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    try:
        ss.set_eval_mode(db, st.clock, p.user.username, body.enabled, body.confirm, bool(_eval_accounts(db)))
    except ss.SettingsError as e:
        raise _err(e) from e
    db.commit()
    st.rules.refresh(db)
    await st.hub.broadcast("risk.eval_mode.changed", {"enabled": body.enabled, "by": p.user.username})
    return get_eval_mode(request, p, db)


@router.post("/risk/eval-mode/preview")
def eval_mode_preview(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    r = request.app.state.rules.rules
    return {"on": ss.impact_preview(r, "evaluation"), "off": ss.impact_preview(r, "standard")}


class AcctEvalIn(BaseModel):
    override: str


@router.patch("/accounts/{acct_id}/eval-mode")
async def patch_account_eval_mode(
    acct_id: int,
    body: AcctEvalIn,
    request: Request,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    st = request.app.state
    if body.override not in ("inherit", "on", "off"):
        raise HTTPException(422, "override must be inherit, on or off")
    a = db.get(Account, acct_id)
    if a is None:
        raise HTTPException(404, "no such account")
    if a.stage != "EVAL" and body.override == "on":
        raise HTTPException(422, "Evaluation Mode applies to EVAL accounts only")
    from app import audit

    audit.record(db, st.clock, p.user.username, "risk.eval_mode.account", str(a.id), {"override": body.override})
    a.eval_mode = body.override
    db.commit()
    await st.hub.broadcast("risk.eval_mode.changed", {"account": a.id, "override": body.override})
    return {
        "id": a.id,
        "override": a.eval_mode,
        "effective": eval_mode_effective(a.stage, a.eval_mode, st.rules.eval_mode_on),
    }


# ---------- Firm Rules (§11A) ----------
class FirmIn(BaseModel):
    changes: dict[str, Any] = Field(default_factory=dict)
    verify: list[str] = Field(default_factory=list)
    confirm: str
    note: str


@router.put("/rules")
async def put_rules(
    body: FirmIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    st = request.app.state
    try:
        row: RuleProfile = ss.save_firm_rules(
            db, st.rules.base, st.clock, p.user.username, body.changes, body.verify, body.confirm, body.note
        )
    except ss.SettingsError as e:
        raise _err(e) from e
    db.commit()
    st.rules.refresh(db)
    await st.hub.broadcast("risk.settings_changed", {"firm_version": row.version})
    h = st.rules
    return {"firm_version": h.firm_version, "verify_paths": h.verify_paths, "verified_paths": h.verified_paths}


@router.get("/accounts")
def list_accounts(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    on = request.app.state.rules.eval_mode_on
    rows = db.execute(select(Account).order_by(Account.priority, Account.id)).scalars()
    return {
        "accounts": [
            {
                "id": a.id,
                "broker_account_id": a.broker_account_id,
                "label": a.label,
                "stage": a.stage,
                "paper": a.is_sim,
                "drawdown_type": a.drawdown_type,
                "drawdown_expected": (exp := stage_rules(request.app.state.rules.rules, a.stage).drawdown_type),
                "drawdown_check": None
                if a.drawdown_type == exp
                else f"{a.stage} accounts at Lucid normally use {exp.upper()} — confirm this account is "
                f"{a.drawdown_type.upper()} in your Lucid dashboard",
                "dll_enabled": a.dll_enabled,
                "eval_mode": a.eval_mode,
                "eval_mode_effective": eval_mode_effective(a.stage, a.eval_mode, on),
                "armed": a.armed,
                "selected": a.selected,
                "priority": a.priority,
                "mll_locked": a.mll_locked,
                "paused_reason": a.paused_reason,
            }
            for a in rows
        ]
    }


@router.get("/plans")
def list_plans(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    """Lucid plans available as rule files (config/rules/*.yaml) and the one in use."""
    from app.risk.holder import RULES_DIR

    out = []
    for f in sorted(RULES_DIR.glob("*.yaml")):
        first = f.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        out.append({"id": f.stem, "title": first})
    return {"current": request.app.state.rules.plan, "plans": out}


class PlanIn(BaseModel):
    plan: str


@router.put("/plans")
async def set_plan(
    body: PlanIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    from app import audit
    from app.automation import state as stt
    from app.risk.holder import RULES_DIR

    st = request.app.state
    if not (RULES_DIR / f"{body.plan}.yaml").is_file() or "/" in body.plan:
        raise HTTPException(404, "no such plan")
    if st.controller.om.trades:
        raise HTTPException(409, "close open trades before switching plan")
    stt.set_setting(db, "rules.plan", body.plan, st.clock.now())
    audit.record(db, st.clock, p.user.username, "rules.plan", body.plan, {"from": st.rules.plan})
    db.commit()
    st.rules.refresh(db)
    if st.rules.error:
        raise HTTPException(422, st.rules.error)
    await st.hub.broadcast("risk.settings_changed", {"plan": body.plan})
    return list_plans(request, p)


MARKETS = {"MGC": "Gold", "MNQ": "Nasdaq"}  # focus: gold (main) + Nasdaq


@router.get("/markets")
def markets(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    r = request.app.state.rules.rules
    return {
        "markets": [
            {
                "symbol": k,
                "name": n,
                "enabled": r.instruments[k].enabled,
                "tick_value": str(r.instruments[k].tick_value),
            }
            for k, n in MARKETS.items()
            if k in r.instruments
        ]
    }


class MarketIn(BaseModel):
    symbol: str
    enabled: bool


@router.put("/markets")
async def set_market(
    body: MarketIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    from app import audit
    from app.automation import state as stt

    st = request.app.state
    if body.symbol not in MARKETS or body.symbol not in st.rules.rules.instruments:
        raise HTTPException(404, "unknown market")
    cur = stt.get_setting(db, "instruments.enabled")
    tog = dict(cur) if isinstance(cur, dict) else {}
    tog[body.symbol] = body.enabled
    stt.set_setting(db, "instruments.enabled", tog, st.clock.now())
    audit.record(db, st.clock, p.user.username, "market.toggle", body.symbol, {"enabled": body.enabled})
    db.commit()
    st.rules.refresh(db)
    await st.hub.broadcast("risk.settings_changed", {"market": body.symbol})
    return markets(request, p)
