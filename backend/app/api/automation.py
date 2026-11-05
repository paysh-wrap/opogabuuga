"""Automation API (§13, §19): mode, pre-flight, attestation, approvals, accounts, flatten, kill switch."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.automation.preflight import PreflightInput
from app.automation.preflight import run as run_preflight
from app.clock import session_date
from app.execution.adapters.base import conservative_mode
from app.models import Account, Attestation, Trade

router = APIRouter(prefix="/api")
KILL_PHRASE = "KILL"
FLATTEN_PHRASE = "FLATTEN ALL"


def _ctl(request: Request) -> Any:
    return request.app.state.controller


def _status(request: Request, db: Session) -> dict[str, Any]:
    c = _ctl(request)
    now = request.app.state.clock.now()
    return {
        "mode": c.mode,
        "conservative_mode": conservative_mode(c.adapter),
        "broker": c.adapter.name,
        "attested_today": stt.attested_today(db, now),
        "entries_blocked_by_time": c.entries_blocked_by_time(),
        "approvals": [{"signal_id": a.signal_id, "expires": a.expires.isoformat()} for a in c.approvals.values()],
        "notices": c.notices[-20:],
        "rules_error": request.app.state.rules.error,
    }


@router.get("/automation")
def get_automation(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return _status(request, db)


class ModeIn(BaseModel):
    mode: str


@router.put("/automation")
async def put_automation(
    body: ModeIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    c = _ctl(request)
    if body.mode != "OFF":
        pf = await _preflight(request, db)
        if not pf["ok"]:
            raise HTTPException(409, {"errors": [f"pre-flight failed: {', '.join(pf['failures'])}"], "preflight": pf})
    try:
        got = c.set_mode(db, body.mode, p.user.username)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    db.commit()
    await request.app.state.hub.broadcast("automation.changed", {"mode": got})
    out = _status(request, db)
    out["granted"] = got
    return out


async def _preflight(request: Request, db: Session) -> dict[str, Any]:
    st = request.app.state
    c = st.controller
    now = st.clock.now()
    from app.monitor.feed import feed_status
    from app.signals.service import today_bias

    feeds_ok = True
    for (sym, prof), ss in st.market.states.items():
        if st.rules.rules.instruments.get(sym) and st.rules.rules.instruments[sym].enabled:
            tf = 1 if prof == "TIGHT" else 5
            feeds_ok &= feed_status(ss.last_heartbeat_ms, tf, now, 2) in ("FRESH", "CLOSED")
    if not st.market.states:
        feeds_ok = False
    reconciled = not await c.reconcile(db)
    sess = session_date(now)
    proxy = st.rules.rules.instrument("MNQ").bias_proxy
    res = run_preflight(
        PreflightInput(
            broker_ok=True,
            token_hours_left=None,
            feeds_fresh=feeds_ok,
            calendar_loaded=st.calendar(sess) is not None,
            bias_loaded=today_bias(db, sess, proxy) != "NO_TRADE",
            live=any(a.stage == "LIVE" and not a.is_sim for a in db.execute(select(Account)).scalars()),
            unconfirmed_verify=len(st.rules.verify_paths),
            reconciled=reconciled,
            orphan_orders=0,
            attested_today=stt.attested_today(db, now),
            clock_drift_s=0.0,
            rules_error=st.rules.error,
            conservative_mode=conservative_mode(c.adapter),
        )
    )
    return {"ok": res.ok, "checks": res.checks, "failures": res.failures}


@router.post("/automation/preflight")
async def preflight(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return await _preflight(request, db)


class AttestIn(BaseModel):
    confirm: bool = Field(description="I hold no positions at other firms/platforms that could hedge these")


@router.post("/attestation")
def attest(
    body: AttestIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    if not body.confirm:
        raise HTTPException(422, "attestation must be confirmed")
    now = request.app.state.clock.now()
    db.add(
        Attestation(
            session_date=session_date(now),
            user_id=p.user.id,
            text="No open positions at other firms/platforms that could hedge or correlate (§1.12).",
        )
    )
    audit.record(db, request.app.state.clock, p.user.username, "attestation", session_date(now).isoformat())
    return {"attested_today": True}


# ---------- accounts ----------
class NewAccount(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    stage: str = "EVAL"
    drawdown_type: str = "eod"
    balance: Decimal = Decimal(25000)


@router.post("/accounts")
def create_account(
    body: NewAccount, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    if body.stage not in ("EVAL", "FUNDED", "LIVE") or body.drawdown_type not in ("eod", "intraday"):
        raise HTTPException(422, "stage EVAL/FUNDED/LIVE and drawdown eod/intraday")
    a = _ctl(request).create_paper_account(
        db, body.label, body.stage, body.drawdown_type, body.balance, p.user.username
    )
    return {"id": a.id, "broker_account_id": a.broker_account_id, "paper": True}


class AccountPatch(BaseModel):
    armed: bool | None = None
    selected: bool | None = None
    priority: int | None = None
    label: str | None = None
    clear_pause: str | None = None  # typed "RESUME" to clear a pause that never auto-resumes


@router.patch("/accounts/{acct_id}")
async def patch_account(
    acct_id: int,
    body: AccountPatch,
    request: Request,
    p: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    a = db.get(Account, acct_id)
    if a is None:
        raise HTTPException(404, "no such account")
    if body.clear_pause is not None:
        if body.clear_pause != "RESUME":
            raise HTTPException(422, 'type "RESUME" to clear the pause')
        a.paused_reason = None
    if body.armed:
        if a.paused_reason:
            raise HTTPException(409, f"account is paused: {a.paused_reason}")
        if a.closed_by_firm:
            raise HTTPException(409, "account was closed by the firm — never re-enter")
    for k in ("armed", "selected", "priority", "label"):
        v = getattr(body, k)
        if v is not None:
            setattr(a, k, v)
    audit.record(
        db,
        request.app.state.clock,
        p.user.username,
        "account.updated",
        a.broker_account_id,
        body.model_dump(exclude_none=True),
    )
    db.commit()
    await request.app.state.hub.broadcast("account.updated", {"id": a.id})
    return {"id": a.id, "armed": a.armed, "selected": a.selected, "priority": a.priority, "paused": a.paused_reason}


class SelectionIn(BaseModel):
    count: int = Field(ge=1, le=5)
    order: list[int] = Field(default_factory=list)


@router.put("/accounts/selection")
def selection(
    body: SelectionIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    for i, aid in enumerate(body.order):
        a = db.get(Account, aid)
        if a is not None:
            a.priority = i
    from app.risk import settings_store as ss

    try:
        ss.save_my_settings(
            db,
            request.app.state.rules.base,
            request.app.state.clock,
            p.user.username,
            {"automation.accounts_to_trade": body.count},
            "account selector",
        ) if "automation.accounts_to_trade" in ss.MY_SETTINGS_KEYS else None
    except ss.SettingsError as e:
        raise HTTPException(422, e.errors) from e
    db.commit()
    request.app.state.rules.refresh(db)
    return {"count": body.count, "order": body.order}


# ---------- approvals / execution ----------
class ExecIn(BaseModel):
    accounts: list[int] | None = None


@router.post("/signals/{sid}/execute")
async def execute(sid: int, body: ExecIn, request: Request, p: Principal = Depends(current_user)) -> dict[str, Any]:
    c = _ctl(request)
    if c.entries_blocked_by_time():
        raise HTTPException(409, "entries are blocked after the flatten time")
    res = await c.execute(sid, p.user.username, body.accounts)
    await request.app.state.hub.broadcast("order.updated", {"signal": sid})
    return {"results": [r.__dict__ for r in res]}


@router.post("/signals/{sid}/skip")
async def skip(
    sid: int, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    _ctl(request).approvals.pop(sid, None)
    audit.record(db, request.app.state.clock, p.user.username, "approval.skipped", str(sid))
    await request.app.state.hub.broadcast("approval.expired", {"signal": sid})
    return {"skipped": sid}


# ---------- flatten / kill ----------
@router.post("/accounts/{acct_id}/flatten")
async def flatten(acct_id: int, request: Request, p: Principal = Depends(current_user)) -> dict[str, Any]:
    try:
        await _ctl(request).flatten(acct_id, p.user.username)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    await request.app.state.hub.broadcast("position.updated", {"account": acct_id})
    return {"flattened": acct_id}


class ConfirmIn(BaseModel):
    confirm: str


@router.post("/flatten-all")
async def flatten_all(body: ConfirmIn, request: Request, p: Principal = Depends(current_user)) -> dict[str, Any]:
    if body.confirm != FLATTEN_PHRASE:
        raise HTTPException(422, f'type "{FLATTEN_PHRASE}" to confirm')
    await _ctl(request).flatten_all(p.user.username)
    await request.app.state.hub.broadcast("position.updated", {"all": True})
    return {"flattened": "all"}


@router.post("/kill-switch")
async def kill(body: ConfirmIn, request: Request, p: Principal = Depends(current_user)) -> dict[str, Any]:
    if body.confirm != KILL_PHRASE:
        raise HTTPException(422, f'type "{KILL_PHRASE}" to confirm')
    await _ctl(request).kill_switch(p.user.username)
    await request.app.state.hub.broadcast("automation.changed", {"mode": "OFF", "kill_switch": True})
    return {"killed": True}


@router.get("/positions")
async def positions(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    c = _ctl(request)
    out = []
    for a in db.execute(select(Account)).scalars():
        if a.broker_account_id not in c.adapter.accounts:
            continue
        bal = await c.adapter.get_balance(a.broker_account_id)
        pos = await c.adapter.get_positions(a.broker_account_id)
        out.append(
            {
                "account_id": a.id,
                "label": a.label,
                "balance": str(bal),
                "open_pnl": str(c.adapter.open_pnl(a.broker_account_id)),
                "mll": str(a.mll),
                "positions": [{"symbol": x.symbol, "qty": x.qty, "avg": str(x.avg_price)} for x in pos],
            }
        )
    return {"accounts": out}


@router.get("/trades")
def trades(_: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.execute(select(Trade).order_by(Trade.id.desc()).limit(200)).scalars()
    return {
        "trades": [
            {
                "id": t.id,
                "account_id": t.account_id,
                "symbol": t.symbol,
                "direction": t.direction,
                "qty": t.qty,
                "entry": str(t.entry),
                "exit": str(t.exit) if t.exit else None,
                "pnl": str(t.pnl_usd) if t.pnl_usd is not None else None,
                "net_r": str(t.net_r) if t.net_r is not None else None,
                "guard_on": t.guard_on,
                "risk_profile": t.risk_profile_kind,
                "exit_reason": t.exit_reason,
                "opened_at": t.opened_at.isoformat(),
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in rows
        ]
    }
