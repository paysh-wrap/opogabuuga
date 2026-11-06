"""Trade journal (§18/§19 GET /api/journal): search, filters, signal snapshot, CSV export."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.models import Account, Signal, Trade

router = APIRouter(prefix="/api")
COLUMNS = [
    "id", "account", "stage", "symbol", "direction", "qty", "entry", "exit", "risk_usd", "pnl_usd", "gross_r",
    "net_r", "guard_on", "risk_profile", "mode", "profile", "exit_reason", "opened_at", "closed_at", "signal_id",
    "score",
]  # fmt: skip


def _s(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _row(t: Trade, a: Account | None, sig: Signal | None) -> dict[str, Any]:
    return {
        "id": t.id,
        "account_id": t.account_id,
        "account": a.label if a else str(t.account_id),
        "stage": a.stage if a else None,
        "symbol": t.symbol,
        "direction": t.direction,
        "qty": t.qty,
        "entry": str(t.entry),
        "exit": _s(t.exit),
        "risk_usd": str(t.risk_usd),
        "pnl_usd": _s(t.pnl_usd),
        "gross_r": _s(t.gross_r),
        "net_r": _s(t.net_r),
        "guard_on": t.guard_on,
        "risk_profile": t.risk_profile_kind,
        "mode": t.mode,
        "profile": t.profile,
        "exit_reason": t.exit_reason,
        "opened_at": t.opened_at.isoformat(),
        "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        "signal_id": t.signal_id,
        "score": _s(sig.score) if sig else None,
        "snapshot": sig.features if sig else None,
    }


@router.get("/journal")
def journal(
    q: str | None = Query(None, max_length=100),
    account_id: int | None = None,
    symbol: str | None = Query(None, max_length=16),
    direction: Literal["LONG", "SHORT"] | None = None,
    result: Literal["win", "loss", "open"] | None = None,
    since: date | None = None,
    until: date | None = None,
    limit: int = Query(500, ge=1, le=5000),
    fmt: Literal["json", "csv"] = Query("json", alias="format"),
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> Any:
    stmt = select(Trade)
    if account_id is not None:
        stmt = stmt.where(Trade.account_id == account_id)
    if symbol:
        stmt = stmt.where(Trade.symbol == symbol)
    if direction:
        stmt = stmt.where(Trade.direction == direction)
    if result == "open":
        stmt = stmt.where(Trade.closed_at.is_(None))
    elif result == "win":
        stmt = stmt.where(Trade.closed_at.is_not(None), Trade.pnl_usd > Decimal(0))
    elif result == "loss":
        stmt = stmt.where(Trade.closed_at.is_not(None), Trade.pnl_usd <= Decimal(0))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Trade.symbol.ilike(like),
                Trade.exit_reason.ilike(like),
                Trade.profile.ilike(like),
                Trade.trade_ref.ilike(like),
                Trade.resolution.ilike(like),
            )
        )
    if since:
        stmt = stmt.where(Trade.opened_at >= datetime.combine(since, time.min, tzinfo=UTC))
    if until:
        stmt = stmt.where(Trade.opened_at < datetime.combine(until + timedelta(days=1), time.min, tzinfo=UTC))
    trades = db.execute(stmt.order_by(Trade.id.desc()).limit(limit)).scalars().all()
    accts = {a.id: a for a in db.execute(select(Account)).scalars()}
    sids = {t.signal_id for t in trades if t.signal_id is not None}
    sigs = {x.id: x for x in db.execute(select(Signal).where(Signal.id.in_(sids))).scalars()} if sids else {}
    rows = [_row(t, accts.get(t.account_id), sigs.get(t.signal_id) if t.signal_id else None) for t in trades]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        return Response(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="paytience-journal.csv"'},
        )
    closed = [Decimal(r["pnl_usd"]) for r in rows if r["closed_at"] and r["pnl_usd"] is not None]
    return {
        "trades": rows,
        "summary": {
            "count": len(rows),
            "closed": len(closed),
            "wins": sum(1 for x in closed if x > 0),
            "net_pnl": str(sum(closed, Decimal(0))),
        },
        "symbols": sorted({t for t in db.execute(select(Trade.symbol).distinct()).scalars()}),
    }
