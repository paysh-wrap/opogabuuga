"""Append-only, hash-chained audit log (§19 audit_log)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import DDL, event, select
from sqlalchemy.orm import Session

from app.clock import Clock
from app.models import AuditLog

GENESIS = "0" * 64

# Triggers make the table append-only at the database level (SQLite + Postgres variants).
SQLITE_TRIGGERS = [
    "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log "
    "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
    "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log "
    "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END",
]
PG_TRIGGERS = [
    "CREATE OR REPLACE FUNCTION audit_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'audit_log is append-only'; END; $$ LANGUAGE plpgsql",
    "CREATE TRIGGER audit_no_mod BEFORE UPDATE OR DELETE ON audit_log "
    "FOR EACH ROW EXECUTE FUNCTION audit_append_only()",
]

for _stmt in SQLITE_TRIGGERS:
    event.listen(AuditLog.__table__, "after_create", DDL(_stmt).execute_if(dialect="sqlite"))  # type: ignore[no-untyped-call]
for _stmt in PG_TRIGGERS:
    event.listen(AuditLog.__table__, "after_create", DDL(_stmt).execute_if(dialect="postgresql"))  # type: ignore[no-untyped-call]


def _digest(prev: str, at_iso: str, actor: str, action: str, entity: str, payload: dict[str, Any]) -> str:
    body = json.dumps(
        {"prev": prev, "at": at_iso, "actor": actor, "action": action, "entity": entity, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(body.encode()).hexdigest()


def record(
    s: Session, clock: Clock, actor: str, action: str, entity: str = "", payload: dict[str, Any] | None = None
) -> AuditLog:
    """Append one entry. Caller commits. Payload must never contain secrets."""
    payload = json.loads(json.dumps(payload or {}, default=str))  # JSON-safe (Decimals → str)
    last = s.execute(select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev = last or GENESIS
    at = clock.now()
    row = AuditLog(
        at=at,
        actor=actor,
        action=action,
        entity=entity,
        payload=payload,
        prev_hash=prev,
        hash=_digest(prev, at.isoformat(), actor, action, entity, payload),
    )
    s.add(row)
    s.flush()
    return row


def verify_chain(s: Session) -> tuple[bool, int | None]:
    """Returns (ok, first_bad_id)."""
    prev = GENESIS
    for row in s.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        expect = _digest(prev, row.at.isoformat(), row.actor, row.action, row.entity, row.payload)
        if row.prev_hash != prev or row.hash != expect:
            return False, row.id
        prev = row.hash
    return True, None
