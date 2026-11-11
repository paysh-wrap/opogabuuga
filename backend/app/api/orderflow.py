"""D98 Order Flow chart page: footprint (per-price bid/ask), bar delta, CVD, session volume profile, prior-session
value, round numbers, premium/discount and stored ORDER_FLOW alert markers — from the 1-minute bars the app already
holds (TradingView heartbeats / replay bars). No external data. Read-only, display only.

With bar data the per-price buy/sell split is ESTIMATED (engine/footprint.py) — every response says so (`source`,
`estimated`, `note`). Sessions are CME Globex days: 18:00 ET → 17:00 ET, keyed by the ET date they end on."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.clock import ET
from app.engine import footprint as FP
from app.models import AuditLog, Bar, Event

router = APIRouter(prefix="/api")

SYMBOLS = ("MNQ", "MGC")
# display-only chart settings (NOT trading rules): row height in ticks and the round-number step
ROW_TICKS = {"MNQ": 4, "MGC": 2}
ROUND_STEP = {"MNQ": Decimal(50), "MGC": Decimal(10)}
LOOKBACK = timedelta(days=10)
LABELS = {
    "ABSORPTION": "Absorption",
    "DELTA_DIVERGENCE": "Exhaustion (delta divergence)",
    "STACKED_IMBALANCE": "Aggression (stacked imbalance)",
    "SWEEP": "Sweep",
    "POC_MAGNET": "POC magnet",
}
NOTE = "ESTIMATED from bars — not true order flow"


def _utc(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def session_of(close_time: datetime) -> date:
    """CME day: a bar closing at/after 18:00 ET belongs to the NEXT ET date."""
    et = _utc(close_time).astimezone(ET)
    return (et + timedelta(hours=6)).date()


def _s(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _profile(p: FP.Profile) -> dict[str, Any]:
    return {
        "rows": [{"p": str(px), "v": str(v)} for px, v in p.rows],
        "poc": _s(p.poc),
        "vah": _s(p.vah),
        "val": _s(p.val),
        "hvn": [str(x) for x in p.hvn],
        "lvn": [str(x) for x in p.lvn],
    }


AR_KEYS = ("env", "location_zone", "fib", "value_side", "path_zone", "path_side", "delta_source", "confirm_time")
SKIP_LABELS = {  # D101 skip reason codes of the Order Flow strategy (engine/order_flow.py), by AR layer
    "OF_COMPRESSION": "Environment: compression / low participation — no trade",
    "OF_ENVIRONMENT": "Environment not allowed by the plan",
    "OF_LOCATION": "Location: not in the 0.705–0.886 zone / wrong value-area side",
    "OF_PATH_UNKNOWN": "Path: Asia range zone unknown",
    "OF_PATH_EXHAUSTED": "Path: move already beyond the Asia + ATR zone limit",
    "OF_NO_CONFIRM": "Confirmation: no (recent) confirmation candle",
    "OF_DELTA_ESTIMATED": "Confirmation: estimated delta only (real delta required)",
}


def ar_rules(rules: Any) -> dict[str, Any]:
    """D101: the AR-Model layer rules as configured in the plan file (strategy.order_flow_cfg.ar)."""
    r = rules.strategy
    a = r.order_flow_cfg.ar
    return {
        "enabled": r.order_flow,
        "paper_only": r.order_flow_cfg.paper_only,
        "verified": False,
        "layers": [
            {
                "key": "ENVIRONMENT",
                "on": True,
                "rule": f"trade only in {' / '.join(a.allowed_envs)}; COMPRESSION = no trade",
            },
            {
                "key": "LOCATION",
                "on": a.location_filter,
                "rule": f"fib {a.fib_min}–{a.fib_max} of the swing range, {a.value_side.replace('_', ' ').lower()}; "
                "a close beyond 0.886 invalidates",
            },
            {
                "key": "PATH",
                "on": a.path_filter,
                "rule": f"Asia range + daily ATR(20) zones; no trade with the move at/beyond {a.path_block_zone}",
            },
            {
                "key": "CONFIRMATION",
                "on": True,
                "rule": "absorption / delta flip / stacked imbalance candle, "
                f"entry pullback ≤ {a.confirm_max_age_min} min"
                f"{' (real delta only)' if a.require_real_delta else ''}; stop beyond the absorption zone",
            },
        ],
    }


def _skips(db: Session, symbol: str, day: date | None) -> list[dict[str, Any]]:
    """D101: Order Flow alerts the engine refused (audit `order_flow.skip`) for this ET day, newest first."""
    if day is None:
        return []
    rows = db.execute(
        select(AuditLog)
        .where(AuditLog.action == "order_flow.skip", AuditLog.entity == f"{symbol}-OF-{day.isoformat()}")
        .order_by(AuditLog.id.desc())
        .limit(50)
    ).scalars()
    out = []
    for a in rows:
        p = a.payload or {}
        code = str(p.get("code") or "")
        out.append(
            {
                "time_ms": p.get("bar_time_ms"),
                "direction": p.get("direction"),
                "code": code,
                "layer": p.get("layer") or "PLAN",
                "label": SKIP_LABELS.get(code, code),
                "detail": p.get("detail"),
                "ar": {k: p.get(k) for k in AR_KEYS},
            }
        )
    return out


def _bars_in(rows: list[Bar]) -> list[FP.BarIn]:
    return [FP.BarIn(int(_utc(b.close_time).timestamp() * 1000) - 60_000, b.o, b.h, b.l, b.c, b.v) for b in rows]


@router.get("/orderflow")
def orderflow(
    request: Request,
    symbol: str = Query("MNQ"),
    session: date | None = Query(None),
    _: Principal = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if symbol not in SYMBOLS:
        raise HTTPException(422, f"symbol must be one of {', '.join(SYMBOLS)}")
    tick = request.app.state.rules.rules.instrument(symbol).tick
    row = tick * ROW_TICKS[symbol]
    q = select(Bar).where(Bar.symbol == symbol, Bar.tf == "1")
    if session is not None:
        end = datetime(session.year, session.month, session.day, 17, 0, tzinfo=ET) + timedelta(minutes=1)
        q = q.where(Bar.close_time <= end, Bar.close_time >= end - LOOKBACK)
    else:
        latest = db.execute(
            select(Bar.close_time).where(Bar.symbol == symbol, Bar.tf == "1").order_by(Bar.close_time.desc()).limit(1)
        ).scalar()
        if latest is not None:
            q = q.where(Bar.close_time >= latest - LOOKBACK)
    by: dict[date, list[Bar]] = defaultdict(list)
    for b in db.execute(q.order_by(Bar.close_time)).scalars():
        by[session_of(b.close_time)].append(b)
    days = sorted(by)
    base: dict[str, Any] = {
        "symbol": symbol,
        "symbols": list(SYMBOLS),
        "source": "estimated",
        "estimated": True,
        "note": NOTE,
        "method": "volume spread evenly over the bar's price rows; buy share = close location in the bar's range "
        "(tick rule vs previous close when high = low)",
        "tick": str(tick),
        "row_size": str(row),
        "sessions": [d.isoformat() for d in days],
        "ar": ar_rules(request.app.state.rules.rules),
    }
    cur = session if session is not None else (days[-1] if days else None)
    base["skips"] = _skips(db, symbol, cur)
    if cur is None or cur not in by:
        return base | {
            "session": cur.isoformat() if cur else None,
            "bars": [],
            "profile": None,
            "prior": None,
            "round_levels": [],
            "signals": [],
        }
    prev_days = [d for d in days if d < cur]
    prior = None
    if prev_days:
        pfp = FP.footprint(_bars_in(by[prev_days[-1]]), row)
        prior = FP.volume_profile(pfp, row)
    rows = by[cur]
    fp = FP.footprint(_bars_in(rows), row)
    prof = FP.volume_profile(fp, row)
    lo, hi = min(b.l for b in rows), max(b.h for b in rows)
    evs = db.execute(
        select(Event)
        .where(
            Event.symbol == symbol,
            Event.event == "ORDER_FLOW",
            Event.bar_time >= rows[0].close_time - timedelta(minutes=1),
            Event.bar_time <= rows[-1].close_time,
        )
        .order_by(Event.bar_time)
    ).scalars()
    signals = []
    for e in evs:
        of = e.payload.get("order_flow") or {}
        kind = str(of.get("kind") or "")
        signals.append(
            {
                "time_ms": int(_utc(e.bar_time).timestamp() * 1000),
                "kind": kind,
                "label": LABELS.get(kind, kind),
                "direction": e.direction,
                "ar": {k: of.get(k) for k in AR_KEYS},  # D101 layers as the indicator sent them
            }
        )
    sources = {b.source for b in fp}
    return base | {
        "source": "tick" if sources == {"tick"} else "estimated",
        "estimated": sources != {"tick"},
        "session": cur.isoformat(),
        "bars": [
            {
                "time_ms": b.time_ms,
                "o": str(b.o),
                "h": str(b.h),
                "l": str(b.l),
                "c": str(b.c),
                "v": str(b.v),
                "delta": str(b.delta),
                "cvd": str(b.cvd),
                "zone": FP.zone(b.c, prior),
                "source": b.source,
                "levels": [{"p": str(x.price), "bid": str(x.bid), "ask": str(x.ask)} for x in b.levels],
            }
            for b in fp
        ],
        "profile": _profile(prof),
        "prior": None if prior is None else {"session": prev_days[-1].isoformat(), **_profile(prior), "rows": []},
        "round_levels": [str(x) for x in FP.round_levels(lo, hi, ROUND_STEP[symbol])],
        "signals": signals,
    }
