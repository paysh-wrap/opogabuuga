"""Signals, skip reasons and cooldowns (§19)."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import Principal, current_user, get_db
from app.clock import session_date
from app.engine.filters import CooldownState
from app.models import Cooldown, Signal, SignalGate, TradePlanRow

router = APIRouter(prefix="/api")
CLEAR_PHRASE = "CLEAR COOLDOWN"


def _signal_json(s: Session, sig: Signal, full: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": sig.id,
        "symbol": sig.symbol,
        "profile": sig.profile,
        "direction": sig.direction,
        "model_key": sig.model_key,
        "status": sig.status,
        "skip_reason": sig.skip_reason,
        "score": str(sig.score) if sig.score is not None else None,
        "c1_range_atr": str(sig.c1_range_atr) if sig.c1_range_atr is not None else None,
        "confirmed_at": sig.bar_time.isoformat(),
        "updated_at": sig.updated_at.isoformat() if sig.updated_at else None,
        "entry_bar_time": sig.entry_bar_time.isoformat() if sig.entry_bar_time else None,
    }
    gates = s.execute(select(SignalGate).where(SignalGate.signal_id == sig.id).order_by(SignalGate.id)).scalars()
    out["gates"] = [{"gate": g.gate, "passed": g.passed, **g.detail} for g in gates]
    plans = s.execute(select(TradePlanRow).where(TradePlanRow.signal_id == sig.id)).scalars()
    out["plans"] = [
        {
            "mode": p.mode,
            "direction": p.direction,
            "entry": str(p.entry),
            "stop": str(p.stop),
            "take_profit": str(p.take_profit),
            "risk_pts": str(p.risk_pts),
            "rr": str(p.rr),
            "partial_price": str(p.partial_price) if p.partial_price is not None else None,
            "breakeven_price": str(p.breakeven_price) if p.breakeven_price is not None else None,
            "lock_price": str(p.lock_price) if p.lock_price is not None else None,
        }
        for p in plans
    ]
    if full:
        out["features"] = sig.features
    return out


@router.get("/signals")
def list_signals(
    limit: int = Query(50, ge=1, le=500), _: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    rows = db.execute(select(Signal).order_by(Signal.id.desc()).limit(limit)).scalars()
    return {"signals": [_signal_json(db, r) for r in rows]}


@router.get("/signals/skips")
def skips(
    request: Request,
    date_: date | None = Query(None, alias="date"),
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Skip reasons for one session vs the average of the previous 20 sessions (§6, §24.3)."""
    day = date_ or session_date(request.app.state.clock.now())
    rows = db.execute(
        select(Signal.bar_time, Signal.status, Signal.skip_reason).where(Signal.status.in_(("SKIP", "EXPIRED")))
    ).all()
    by_day: dict[date, Counter[str]] = {}
    for bt, _status, reason in rows:
        by_day.setdefault(session_date(bt), Counter())[reason or "UNKNOWN"] += 1
    today = by_day.get(day, Counter())
    prev = [d for d in by_day if d < day][-20:]
    avg = (
        {k: round(sum(by_day[d][k] for d in prev) / len(prev), 2) for k in {k for d in prev for k in by_day[d]}}
        if prev
        else {}
    )
    return {"date": day.isoformat(), "counts": dict(today), "avg_20": avg, "sessions_in_avg": len(prev)}


@router.get("/signals/{sid}")
def get_signal(sid: int, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    sig = db.get(Signal, sid)
    if sig is None:
        raise HTTPException(404, "no such signal")
    return _signal_json(db, sig, full=True)


@router.get("/cooldowns")
def cooldowns(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    sess = session_date(request.app.state.clock.now())
    rows = db.execute(select(Cooldown)).scalars()
    return {
        "cooldowns": [
            {
                "symbol": r.symbol,
                "profile": r.profile,
                "streak": r.streak,
                "until_session": r.until_session.isoformat() if r.until_session else None,
                "active": CooldownState(r.streak, r.until_session).active(sess),
            }
            for r in rows
        ]
    }


class ClearIn(BaseModel):
    confirm: str
    symbol: str | None = None


@router.post("/cooldowns/{profile}/clear")
def clear_cooldown(
    profile: str, body: ClearIn, request: Request, p: Principal = Depends(current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    if body.confirm != CLEAR_PHRASE:
        raise HTTPException(422, f'type "{CLEAR_PHRASE}" to confirm')
    q = select(Cooldown).where(Cooldown.profile == profile)
    if body.symbol:
        q = q.where(Cooldown.symbol == body.symbol)
    n = 0
    for r in db.execute(q).scalars():
        r.streak, r.until_session = 0, None
        n += 1
    audit.record(
        db, request.app.state.clock, p.user.username, "cooldown.cleared", profile, {"symbol": body.symbol, "rows": n}
    )
    return {"cleared": n}
