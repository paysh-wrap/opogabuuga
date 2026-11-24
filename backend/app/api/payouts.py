"""Payouts API (§14): list, run the weekly check now, mark submitted / processed / cancelled."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.automation import state as stt
from app.clock import session_date
from app.execution.adapters.base import BrokerError
from app.models import Account, Payout
from app.phases.on_demand import PAUSE_RULE
from app.payouts.service import (
    consistency_view,
    on_demand_for,
    payout_consistency_for,
    session_check,
    weekly_check,
)

router = APIRouter(prefix="/api")
NEXT = {"ready": {"submitted", "cancelled"}, "submitted": {"processed", "cancelled"}}


def _row(p: Payout, a: Account | None) -> dict[str, Any]:
    return {
        "id": p.id,
        "account_id": p.account_id,
        "label": a.label if a else "",
        "week": p.week,
        "kind": p.kind,
        "amount": str(p.amount),
        "balance_before": str(p.balance_before),
        "status": p.status,
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
        "processed_at": p.processed_at.isoformat() if p.processed_at else None,
    }


@router.get("/payouts")
def list_payouts(_: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.execute(select(Payout).order_by(Payout.id.desc()).limit(200)).scalars()
    return {"payouts": [_row(p, db.get(Account, p.account_id)) for p in rows]}


@router.get("/payouts/consistency")
def consistency(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """D89: Lucid payout-consistency status of every FUNDED account (largest day / cycle profit vs the limit)."""
    r = request.app.state.rules  # D168: holder → each account's own plan
    out = []
    for a in db.execute(
        select(Account).where(Account.stage == "FUNDED").order_by(Account.priority, Account.id)
    ).scalars():
        v = consistency_view(db, r, a)
        if v is not None:
            out.append({"account_id": a.id, "label": a.label or a.broker_account_id, **v})
    return {"accounts": out}


async def _on_demand_rows(request: Request, db: Session) -> list[dict[str, Any]]:
    st = request.app.state
    now = st.clock.now()
    out = []
    for a in db.execute(select(Account).where(Account.stage == "FUNDED").order_by(Account.priority, Account.id)).scalars():
        try:
            bal = await st.controller.adapter.get_balance(a.broker_account_id)
        except BrokerError:
            continue
        o = on_demand_for(db, st.rules, a, bal, now)
        out.append(
            {
                "account_id": a.id,
                "label": a.label or a.broker_account_id,
                "available": o.available,
                "amount": str(o.amount),
                "net": str(o.net),
                "limited_by": o.limited_by,
                "reason": o.reason,
                "message": o.message,
                "dll_enabled": a.dll_enabled,
                "hedging_violation": a.hedging_violation,
                "paused": stt.payout_pending(db, a, now),
            }
        )
    return out


@router.get("/payouts/on-demand")
async def on_demand(
    request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """D182: On-demand payouts (CONFIRMED, Lucid help center, user screenshots 2026-11-24): what each funded LucidPro account
    could request RIGHT NOW. The app never submits anything (Lucid has no API): plan it here, request it in Lucid's dashboard."""
    return {
        "status": "CONFIRMED (Lucid help center)",
        "pause_rule": PAUSE_RULE,
        "accounts": await _on_demand_rows(request, db),
    }


@router.post("/payouts/on-demand/{acct_id}/plan")
async def plan_on_demand(
    acct_id: int, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    """Creates a READY payout row for the amount payable now; the user then requests it in Lucid and marks it submitted
    (which pauses the account until the end of the trading day). Nothing is sent to Lucid."""
    st = request.app.state
    a = db.get(Account, acct_id)
    if a is None:
        raise HTTPException(404, "no such account")
    try:
        bal = await st.controller.adapter.get_balance(a.broker_account_id)
    except BrokerError as e:
        raise HTTPException(502, f"balance unavailable: {e}") from e
    now = st.clock.now()
    o = on_demand_for(db, st.rules, a, bal, now)
    if not o.available:
        raise HTTPException(409, o.message)
    row = Payout(
        account_id=a.id, week=session_date(now).isoformat(), kind="ondem", amount=o.amount, balance_before=bal, status="ready"
    )
    db.add(row)
    audit.record(db, st.clock, p.user.username, "payout.planned", a.broker_account_id, {"kind": "ondem", "amount": str(o.amount)})
    db.commit()
    await st.hub.broadcast("payout.changed", {"id": row.id, "status": "ready"})
    return _row(row, a)


@router.post("/payouts/check")
async def run_check(request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    st = request.app.state
    check = session_check if st.rules.rules.payouts.frequency == "every_n_sessions" else weekly_check  # D65
    made = await check(db, st.controller, st.rules, st.clock.now())
    db.commit()
    return {"created": [_row(x, db.get(Account, x.account_id)) for x in made]}


class StatusIn(BaseModel):
    status: Literal["submitted", "processed", "cancelled"]


@router.post("/payouts/{pid}/status")
async def set_status(
    pid: int, body: StatusIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> Any:
    st = request.app.state
    row = db.get(Payout, pid)
    if row is None:
        raise HTTPException(404, "no such payout")
    if body.status not in NEXT.get(row.status, set()):
        raise HTTPException(409, f"cannot go from {row.status} to {body.status}")
    a = db.get(Account, row.account_id)
    if body.status == "submitted" and a is not None:  # D89: never submit while Lucid's consistency rule is not met
        got = payout_consistency_for(db, st.rules, a)
        if got is not None and not got[0].eligible:
            from app.risk.consistency import payout_consistency_text

            raise HTTPException(409, "Payout consistency not met. " + payout_consistency_text(got[0]))
    now = st.clock.now()
    row.status = body.status
    if body.status == "submitted":
        row.submitted_at = now  # trading on this account blocks until processed (§14)
        r = st.rules.rules_for(a) if a is not None else st.rules.rules
        if a is not None and r.funded.payout.lock_mll_on_payout and not a.mll_locked:
            a.mll, a.mll_locked = r.funded.lock_level, True  # LucidFlex: MLL moves to the locked level
    if body.status == "processed":
        row.processed_at = now
        sim = st.controller.adapter.sim
        if a is not None and a.is_sim and a.broker_account_id in sim.accounts:
            sim.accounts[a.broker_account_id].balance -= row.amount  # paper: money leaves the account
    audit.record(db, st.clock, p.user.username, f"payout.{body.status}", a.broker_account_id if a else "", {"id": pid})
    db.commit()
    await st.hub.broadcast("payout.changed", {"id": pid, "status": body.status})
    return _row(row, a)
