"""Read-only journal / audit-log search (§18 Journal & Logs, §19 GET /api/logs)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.models import AuditLog

router = APIRouter(prefix="/api")


@router.get("/logs")
def logs(
    q: str | None = Query(None, max_length=100),
    action: str | None = Query(None, max_length=64),
    since: date | None = None,
    until: date | None = None,
    limit: int = Query(200, ge=1, le=1000),
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Newest first. `q` matches actor / action / entity / payload text (audit payloads never hold secrets)."""
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                AuditLog.actor.ilike(like),
                AuditLog.action.ilike(like),
                AuditLog.entity.ilike(like),
                cast(AuditLog.payload, String).ilike(like),
            )
        )
    if since:
        stmt = stmt.where(AuditLog.at >= datetime.combine(since, time.min, tzinfo=UTC))
    if until:
        stmt = stmt.where(AuditLog.at < datetime.combine(until + timedelta(days=1), time.min, tzinfo=UTC))
    rows = db.execute(stmt.order_by(AuditLog.id.desc()).limit(limit)).scalars().all()
    actions = db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action)).scalars().all()
    ok, bad = audit.verify_chain(db)
    return {
        "logs": [
            {"id": r.id, "at": r.at.isoformat(), "actor": r.actor, "action": r.action, "entity": r.entity, "payload": r.payload}
            for r in rows
        ],
        "actions": list(actions),
        "chain_ok": ok,
        "chain_first_bad_id": bad,
    }
