"""Automation API (§13, §19): mode, pre-flight, attestation, approvals, accounts, flatten, kill switch."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

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
from app.execution.adapters.base import BrokerError, conservative_mode
from app.models import Account, Attestation, Trade
from app.phases.payout_clock import payout_clock
from app.phases.phase_engine import stage_rules

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
    out = {"ok": res.ok, "checks": res.checks, "failures": res.failures}
    prev = getattr(st, "last_preflight", None)
    if not res.ok and (prev is None or prev.get("ok")):  # notify on the transition only (UI polls every 30 s)
        c.notify("error", "Pre-flight failed", ", ".join(res.failures)[:500], "preflight")
        c.publish("system.status", {"preflight_ok": False, "failures": res.failures})
    elif res.ok and prev is not None and not prev.get("ok"):
        c.publish("system.status", {"preflight_ok": True})
    st.last_preflight = {**out, "at": now.isoformat()}  # shown on the Today page
    return out


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
    drawdown_type: str | None = None  # None → the stage default from the rules file
    balance: Decimal = Decimal(25000)
    tradovate_account: str | None = Field(default=None, max_length=64)  # set → REAL account (not paper)


@router.post("/accounts")
def create_account(
    body: NewAccount, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    if body.stage not in ("EVAL", "FUNDED", "LIVE") or body.drawdown_type not in (None, "eod", "intraday"):
        raise HTTPException(422, "stage EVAL/FUNDED/LIVE and drawdown eod/intraday")
    beh = request.app.state.rules.rules.behavior
    real = [a for a in db.execute(select(Account).where(Account.is_sim.is_(False))).scalars()]
    if body.tradovate_account:  # Lucid household limits apply to real Lucid accounts (11404617)
        if len(real) >= beh.max_total_accounts:
            raise HTTPException(409, f"Lucid allows at most {beh.max_total_accounts} evaluation + funded accounts")
        if body.stage == "FUNDED" and sum(a.stage == "FUNDED" for a in real) >= beh.max_funded_per_household:
            raise HTTPException(409, f"Lucid allows at most {beh.max_funded_per_household} funded accounts")
        if body.stage == "LIVE" and sum(a.stage == "LIVE" for a in real) >= 5:
            raise HTTPException(409, "Lucid allows at most 5 live accounts")
    dd = body.drawdown_type or stage_rules(request.app.state.rules.rules, body.stage).drawdown_type
    c = _ctl(request)
    if body.tradovate_account:
        ext = body.tradovate_account.strip().upper()
        if db.execute(select(Account).where(Account.broker_account_id == ext)).scalar_one_or_none():
            raise HTTPException(409, "account already added")
        a = c.create_paper_account(db, body.label, body.stage, dd, body.balance, p.user.username, real_id=ext)
        db.commit()
        return {"id": a.id, "broker_account_id": ext, "paper": False}
    a = c.create_paper_account(db, body.label, body.stage, dd, body.balance, p.user.username)
    return {"id": a.id, "broker_account_id": a.broker_account_id, "paper": True}


class AccountPatch(BaseModel):
    armed: bool | None = None
    selected: bool | None = None
    priority: int | None = None
    label: str | None = None
    clear_pause: str | None = None  # typed "RESUME" to clear a pause that never auto-resumes
    drawdown_type: Literal["eod", "intraday"] | None = None  # must match the account at Lucid
    mode_override: Literal["inherit", "SEMI", "OFF"] | None = None  # §13: only more restrictive than global


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
    if body.drawdown_type is not None and body.drawdown_type != a.drawdown_type:
        if any(t.account == a.broker_account_id for t in _ctl(request).om.trades.values()):
            raise HTTPException(409, "close the open trade before changing drawdown type")
        a.drawdown_type = body.drawdown_type
    if body.mode_override is not None:
        a.mode_override = None if body.mode_override == "inherit" else body.mode_override
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
    c = _ctl(request)
    if body.armed and c.mode == "FULL":  # §13: an account in its first sessions of a stage may only run OFF/SEMI
        db.flush()
        if c.set_mode(db, "FULL", "automation") != "FULL":
            c.notify(
                "warn", "Automation now SEMI-AUTO", f"{a.label} is in its first sessions of {a.stage}", "automation"
            )
            c.publish("automation.changed", {"mode": c.mode})
    db.commit()
    await request.app.state.hub.broadcast("account.updated", {"id": a.id})
    return {
        "id": a.id,
        "armed": a.armed,
        "selected": a.selected,
        "priority": a.priority,
        "paused": a.paused_reason,
        "mode_override": a.mode_override or "inherit",
    }


class SelectionIn(BaseModel):
    count: int = Field(ge=1, le=5)
    order: list[int] = Field(default_factory=list)


@router.put("/accounts/selection")
async def selection(
    body: SelectionIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """ "Trading N of M": priority order (`order` first, then the rest as before); the first N are selected."""
    accts = {a.id: a for a in db.execute(select(Account)).scalars()}
    if any(i not in accts for i in body.order) or len(set(body.order)) != len(body.order):
        raise HTTPException(422, "order must list existing accounts once each")
    rest = sorted((a for i, a in accts.items() if i not in body.order), key=lambda a: (a.priority, a.id))
    ranked = [accts[i] for i in body.order] + rest
    for rank, a in enumerate(ranked):
        a.priority = rank
        a.selected = rank < body.count
    audit.record(
        db, request.app.state.clock, p.user.username, "account.selection", str(body.count), {"order": body.order}
    )
    db.commit()
    await request.app.state.hub.broadcast("account.updated", {"selection": body.count})
    return {"count": body.count, "order": [a.id for a in ranked], "selected": [a.id for a in ranked[: body.count]]}


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
    return {"killed": True}


def _payout(request: Request, db: Session, a: Account, bal: Decimal, opnl: Decimal) -> dict[str, Any] | None:
    """FUNDED: payout countdown + amount needed + go-live trigger left today. LIVE: next payout time only."""
    if a.stage not in ("FUNDED", "LIVE"):
        return None
    r = request.app.state.rules.rules
    now = request.app.state.clock.now()
    pr = r.funded.payout
    c = payout_clock(
        stage=a.stage,
        balance=bal,
        today_pnl=stt.day_stats(db, a, now).day_profit + opnl,
        now=now,
        frequency=r.payouts.frequency,
        check_time=r.payouts.check_time,
        buffer=pr.buffer,
        min_request=pr.min_request,
        live_trigger=r.funded.max_daily_profit_live_trigger,
        session_check_time=r.payouts.session_check_time,
    )
    funded = a.stage == "FUNDED"
    return {
        "next_check": c.next_check.isoformat() if c.next_check else None,
        "seconds_left": c.seconds_left,
        "eligible": str(c.eligible) if funded else None,
        "needed": str(c.needed) if funded else None,
        "live_trigger_left": str(c.live_trigger_left) if c.live_trigger_left is not None else None,
        "pending": stt.payout_pending(db, a),
        "payouts_done": (done := stt.payouts_processed(db, a)),
        "payouts_to_live": r.funded.payouts_to_live if funded else None,
        "payouts_live_review": r.funded.payouts_live_review if funded else None,
        "live_ready": funded and done >= max(1, r.funded.payouts_to_live or 1),
    }


@router.get("/positions")
async def positions(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    c = _ctl(request)
    out = []
    for a in db.execute(select(Account)).scalars():
        if a.broker_account_id not in c.adapter.accounts:
            continue
        try:
            bal = await c.adapter.get_balance(a.broker_account_id)
            pos = await c.adapter.get_positions(a.broker_account_id)
            opnl = c.adapter.open_pnl(a.broker_account_id)
        except BrokerError as e:
            out.append({"account_id": a.id, "label": a.label, "error": str(e), "positions": []})
            continue
        out.append(
            {
                "account_id": a.id,
                "label": a.label,
                "balance": str(bal),
                "open_pnl": str(opnl),
                "mll": str(a.mll),
                "positions": [{"symbol": x.symbol, "qty": x.qty, "avg": str(x.avg_price)} for x in pos],
                "payout": _payout(request, db, a, bal, opnl),
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
