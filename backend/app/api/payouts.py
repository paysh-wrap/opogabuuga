"""Payouts API (§14): list, run the weekly check now, mark submitted / processed / cancelled."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.models import Account, Payout
from app.payouts.service import weekly_check

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


@router.post("/payouts/check")
async def run_check(request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    st = request.app.state
    made = await weekly_check(db, st.controller, st.rules.rules, st.clock.now())
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
    now = st.clock.now()
    row.status = body.status
    if body.status == "submitted":
        row.submitted_at = now  # trading on this account blocks until processed (§14)
    if body.status == "processed":
        row.processed_at = now
        sim = st.controller.adapter.sim
        if a is not None and a.is_sim and a.broker_account_id in sim.accounts:
            sim.accounts[a.broker_account_id].balance -= row.amount  # paper: money leaves the account
    audit.record(db, st.clock, p.user.username, f"payout.{body.status}", a.broker_account_id if a else "", {"id": pid})
    db.commit()
    await st.hub.broadcast("payout.changed", {"id": pid, "status": body.status})
    return _row(row, a)
