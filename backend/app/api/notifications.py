"""In-app notifications (alerts bell) + running jobs (header jobs indicator) — §18/§19."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.events import notification_row
from app.models import BacktestRun, Notification

router = APIRouter(prefix="/api")


@router.get("/notifications")
def list_notifications(
    unread: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    q = select(Notification).order_by(Notification.id.desc()).limit(limit)
    if unread:
        q = q.where(Notification.read_at.is_(None))
    count = db.execute(select(func.count(Notification.id)).where(Notification.read_at.is_(None))).scalar_one()
    return {"notifications": [notification_row(n) for n in db.execute(q).scalars()], "unread": count}


class ReadIn(BaseModel):
    ids: list[int] | None = Field(None, description="None = mark all read")


@router.post("/notifications/read")
def mark_read(
    body: ReadIn, request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    now = request.app.state.clock.now()
    q = update(Notification).where(Notification.read_at.is_(None))
    if body.ids is not None:
        if not body.ids:
            raise HTTPException(422, "ids must not be empty (omit it to mark all read)")
        q = q.where(Notification.id.in_(body.ids))
    n = db.execute(q.values(read_at=now)).rowcount  # type: ignore[attr-defined]
    db.commit()
    return {"marked": n}


@router.get("/jobs")
def jobs(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    bus = request.app.state.bus
    out = [j.as_dict() for j in bus.jobs.values()]
    seen = {j["id"] for j in out}
    for r in db.execute(select(BacktestRun).where(BacktestRun.status.in_(("running", "queued")))).scalars():
        jid = f"backtest-{r.id}"
        if jid not in seen:  # e.g. started before a restart
            out.append(
                {
                    "id": jid,
                    "kind": "backtest",
                    "label": f"Backtest #{r.id} ({r.kind})",
                    "status": r.status,
                    "progress": r.progress,
                    "at": r.created_at.isoformat(),
                }
            )
    return {"jobs": out}
