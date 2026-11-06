"""§24.2 Trade Replay: everything needed to redraw one trade — recorded candles, the fractal model (C1 box, sweep,
CISD, targets), plan prices (entry/stop/TP/partial/BE), the exit, MSO events at their CONFIRMATION time, gate
results and the score breakdown. Read-only; works for live and paper trades (backtests replay through the same
tables)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.models import Bar, Event, Signal, SignalGate, Trade, TradePlanRow

router = APIRouter(prefix="/api")

BEFORE = timedelta(minutes=90)
AFTER = timedelta(minutes=30)
FRACTAL_KEYS = (
    "c1_high",
    "c1_low",
    "c1_time_ms",
    "t1",
    "t2",
    "invalid",
    "sweep_extreme",
    "sweep_time_ms",
    "cisd_level",
    "c3_close_time_ms",
)


def _s(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _utc(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _ms(d: datetime) -> int:
    return int(_utc(d).timestamp() * 1000)


def fractal_from_events(payloads: list[dict[str, Any]], c1_time_ms: int | None) -> dict[str, Any] | None:
    """PURE: latest fractal snapshot for this model (later events refine the earlier ones)."""
    out: dict[str, Any] = {}
    for p in payloads:
        f = p.get("fractal") or {}
        if c1_time_ms is not None and f.get("c1_time_ms") != c1_time_ms:
            continue
        out |= {k: f[k] for k in FRACTAL_KEYS if f.get(k) is not None}
    return out or None


@router.get("/trades/{tid}/replay")
def replay(tid: int, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    t = db.get(Trade, tid)
    if t is None:
        raise HTTPException(404, "no such trade")
    start = _utc(t.opened_at) - BEFORE
    end = _utc(t.closed_at or t.opened_at) + AFTER
    sig = db.get(Signal, t.signal_id) if t.signal_id else None
    tf = "1"
    bars = list(
        db.execute(
            select(Bar)
            .where(Bar.symbol == t.symbol, Bar.tf == tf, Bar.close_time >= start, Bar.close_time <= end)
            .order_by(Bar.close_time)
        ).scalars()
    )
    plan = None
    gates: list[dict[str, Any]] = []
    fractal = None
    mso: list[dict[str, Any]] = []
    if sig is not None:
        rows = list(db.execute(select(TradePlanRow).where(TradePlanRow.signal_id == sig.id)).scalars())
        p = next(
            (r for r in rows if r.mode == ("ONE_TO_ONE" if t.risk_profile_kind == "one_to_one" else "STANDARD")), None
        )
        p = p or (rows[0] if rows else None)
        if p is not None:
            plan = {
                "mode": p.mode,
                "entry": _s(p.entry),
                "stop": _s(p.stop),
                "take_profit": _s(p.take_profit),
                "partial": _s(p.partial_price),
                "breakeven": _s(p.breakeven_price),
                "rr": _s(p.rr),
            }
        gates = [
            {"gate": g.gate, "passed": g.passed, "code": g.detail.get("code"), "detail": g.detail.get("detail")}
            for g in db.execute(
                select(SignalGate).where(SignalGate.signal_id == sig.id).order_by(SignalGate.id)
            ).scalars()
        ]
        try:
            c1_ms: int | None = int(sig.model_key.rsplit("-", 1)[-1])
        except ValueError:
            c1_ms = None
        evs = list(
            db.execute(
                select(Event)
                .where(
                    Event.symbol == sig.symbol,
                    Event.profile == sig.profile,
                    Event.bar_time >= start - BEFORE,
                    Event.bar_time <= end,
                )
                .order_by(Event.bar_time)
            ).scalars()
        )
        fractal = fractal_from_events([e.payload for e in evs], c1_ms)
        mso = [
            {
                "event": e.event,
                "direction": e.direction,
                "time_ms": (e.payload.get("mso") or {}).get("confirm_time_ms") or _ms(e.bar_time),
            }
            for e in evs
            if e.event.startswith("MSO_")
        ]
    return {
        "trade": {
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "qty": t.qty,
            "entry": _s(t.entry),
            "exit": _s(t.exit),
            "opened_ms": _ms(t.opened_at),
            "closed_ms": _ms(t.closed_at) if t.closed_at else None,
            "pnl": _s(t.pnl_usd),
            "net_r": _s(t.net_r),
            "resolution": t.resolution,
            "exit_reason": t.exit_reason,
            "guard_on": t.guard_on,
        },
        "bars": [
            {"time_ms": _ms(b.close_time) - 60_000, "o": str(b.o), "h": str(b.h), "l": str(b.l), "c": str(b.c)}
            for b in bars
        ],
        "plan": plan,
        "fractal": fractal,
        "mso_events": mso,
        "gates": gates,
        "score": {
            "total": _s(sig.score) if sig else None,
            "items": (sig.features or {}).get("score_items", {}) if sig else {},
        },
        "signal": {"id": sig.id, "profile": sig.profile, "model_key": sig.model_key} if sig else None,
    }
