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


AR_KEYS = (
    "env", "location_zone", "fib", "value_side", "path_zone", "path_side", "delta_source", "confirm_time",
    "close_pos", "cvd_slope", "open_vs_value", "prior_va_width_atr",  # D108 Casper fields
    "context", "ctx_session", "key_level_type", "target_level",  # D110 AMT+ fields
)  # fmt: skip
SKIP_LABELS = {  # D101 skip reason codes of the Order Flow strategy (engine/order_flow.py), by AR layer
    "OF_COMPRESSION": "Environment: compression / low participation — no trade",
    "OF_ENVIRONMENT": "Environment not allowed by the plan",
    "OF_LOCATION": "Location: not in the 0.705–0.886 zone / wrong value-area side",
    "OF_PATH_UNKNOWN": "Path: Asia range zone unknown",
    "OF_PATH_EXHAUSTED": "Path: move already beyond the Asia + ATR zone limit",
    "OF_NO_CONFIRM": "Confirmation: no (recent) confirmation candle",
    "OF_DELTA_ESTIMATED": "Confirmation: estimated delta only (real delta required)",
    # D108 Casper 4h course refinements (TEACHER_RULES_4H.md), layer CASPER
    "OF_CASPER_PRICE_CONFIRMS": "Casper: entry candle did not close away from the trapped side",
    "OF_CASPER_STACKED": "Casper: stacked imbalance too short to count as aggression",
    "OF_CASPER_CVD": "Casper: CVD does not confirm (the other side gets no return)",
    "OF_CASPER_CONDITION": "Casper: against the open vs prior value-area lean",
    "OF_CASPER_BUNCHED": "Casper: levels bunched (narrow prior value area) — no trade",
    "OF_CASPER_ROUND_STOP": "Casper: stop moved off the round number no longer fits risk / R:R",
    # D110 AMT+ (CONTEXT → LOCATION before the order-flow layers)
    "OF_AMT_NO_CONTEXT": "AMT+: context unknown (indicator sent no acceptance read)",
    "OF_AMT_COUNTER_CONTEXT": "AMT+: against the accepted context (prior RTH value area)",
    "OF_AMT_BALANCE": "AMT+: balance context — stand aside / VA edges only",
    "OF_AMT_NO_LEVEL": "AMT+: not at a key level",
    # D111 ATR-zone type (iceberg PROXY)
    "OF_ZONE_NOT_ENTRY": "Zone: not an entry alert",
    "OF_ZONE_MODE_OFF": "Zone: this mode (POSITION / REVERSION) is off",
    "OF_ZONE_NO_EVENT": "Zone: event zone / ATR missing",
    "OF_ZONE_EVENT_SMALL": "Zone: event too small (iceberg proxy)",
    "OF_ZONE_LAST_MINUTES": "Zone: last minutes of RTH — no new trades",
    "OF_ZONE_DEAD_ZONE": "Zone: dead zone without enough relative volume",
    "OF_ZONE_NOT_PROVEN": "Zone: price not 115% ATR out of the zone",
    "OF_ZONE_REV_LEVEL": "Zone: not at a 1/2/3 ATR reversion level",
    "OF_ZONE_NO_PRICE_CHANGE": "Zone: no price-change (too far too fast) confirm",
    "OF_ZONE_PROGRAM_DAY": "Zone: TICK program day — no fade",
    "OF_ZONE_NOT_A_PLUS": "Zone: not in front of a prior event (A+ only)",
    "OF_ZONE_EXCLUSIVE": "Zone type exclusive: AR alert not traded",
}


def casper_rules(c: Any) -> list[dict[str, Any]]:
    """D108: the Casper 4h-course refinements as configured (strategy.order_flow_cfg.casper)."""
    steps = ", ".join(f"{k} {v}" for k, v in c.round_step.items())
    return [
        {"key": "PRICE_CONFIRMS", "on": c.price_confirms,
         "rule": f"entry candle closes away from the trapped side (≥ {c.close_pos_min} of its range)"},
        {"key": "STACKED", "on": c.stacked_definition,
         "rule": f"stacked imbalance needs ≥ {c.min_stacked} diagonal imbalances in a row"},
        {"key": "CVD", "on": c.cvd_confirm, "rule": "CVD over the last bars moves in the trade direction"},
        {"key": "CONDITION", "on": c.condition,
         "rule": "no trade against the RTH open vs prior value lean"
         f"{'' if c.inside_value_ok else '; open inside value = no trade'}"},
        {"key": "BUNCHED", "on": c.bunched,
         "rule": f"no trade when the prior value area < {c.min_va_width_atr} × daily ATR(20)"},
        {"key": "ROUND_STOP", "on": c.round_stop,
         "rule": f"stop {c.round_buffer_ticks} ticks beyond a nearby round number ({steps})"},
    ]  # fmt: skip


def amt_rules(m: Any) -> list[dict[str, Any]]:
    """D110: the AMT+ layers as configured (strategy.order_flow_cfg.amt); all OFF while the button is off."""
    return [
        {"key": "CONTEXT", "on": m.enabled,
         "rule": "acceptance vs the prior RTH value area at the session open: above = longs only, below = shorts "
         f"only; balance = {'VA-edge trades only' if m.balance_mode == 'edges' else 'no trade'}"},
        {"key": "LOCATION", "on": m.enabled and m.level_filter,
         "rule": f"signal at a key level ({', '.join(m.levels)})"},
        {"key": "TARGET", "on": m.enabled and m.target_to_level,
         "rule": f"TP = next key level beyond entry when it gives rr_min–{m.target_max_rr}R, else the normal target"},
    ]  # fmt: skip


def zone_rules(z: Any) -> list[dict[str, Any]]:
    """D111: the ATR-zone Order Flow type (iceberg PROXY, no MBO data), strategy.order_flow_cfg.zone_atr."""
    on = z.enabled
    return [
        {"key": "EVENT", "on": on,
         "rule": "iceberg PROXY (no MBO data): footprint absorption / large-volume zone, size ≥ "
         + ", ".join(f"{k} {v}" for k, v in z.min_event_size.items())},
        {"key": "POSITION", "on": on and "POSITION" in z.modes,
         "rule": f"entry {z.entry_atr_pct}×ATR(5m) outside the zone; stop back through it + {z.stop_atr_pct}×ATR; "
         "trail only to a new same-direction event, never breakeven"},
        {"key": "REVERSION", "on": on and "REVERSION" in z.modes,
         "rule": f"entry {'/'.join(map(str, z.reversion_levels))} ATR away, target the zone, stop at the next ATR"
         f"{'; A+ only (in front of a prior event)' if z.a_plus_only else ''}; exit on an opposing event"},
        {"key": "DEAD_ZONE", "on": on and z.dead_zone_filter,
         "rule": f"{z.dead_zone[0]}–{z.dead_zone[1]} ET only with relative volume ≥ {z.dead_zone_min_rvol}×"},
        {"key": "LAST_MINUTES", "on": on and z.last_minutes_filter,
         "rule": f"no new trades in the last {z.last_minutes} min before {z.rth_close} ET"},
        {"key": "PRICE_CHANGE", "on": on and z.price_change_confirm,
         "rule": f"reversion needs a 5-min range ≥ {z.price_change_pct}×ATR"},
        {"key": "PROGRAM_DAY", "on": on and z.tick_filter,
         "rule": f"no fade with |TICK| ≥ {z.tick_extreme} against it (off when the alert has no TICK)"},
    ]  # fmt: skip


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
        "casper": casper_rules(r.order_flow_cfg.casper),  # D108: refinement layer list (each a switch)
        "amt": amt_rules(r.order_flow_cfg.amt),  # D110: AMT+ layers (button)
        "amt_enabled": r.order_flow_cfg.amt.enabled,
        "zone": zone_rules(r.order_flow_cfg.zone_atr),  # D111: ATR-zone type
        "zone_enabled": r.order_flow_cfg.zone_atr.enabled,
        "zone_setting": "strategy.order_flow_cfg.zone_atr.enabled",
        "zone_modes": list(r.order_flow_cfg.zone_atr.modes),
    }


def ta_advisor_view(request: Request, db: Session, symbol: str) -> dict[str, Any]:
    """D109: the TradingAgents advisor toggle + today's stored advice for this market (advisory label)."""
    from app.bias import of_advisor as OFA
    from app.clock import session_date

    r = request.app.state.rules.rules
    cfg = r.strategy.order_flow_cfg
    today = session_date(request.app.state.clock.now())
    return {
        "enabled": cfg.ta_advisor,
        "setting": "strategy.order_flow_cfg.ta_advisor",
        "blocks": cfg.ta_advisor_blocks,
        "at": OFA.advisor_at(r),
        "advisory": True,
        "session": today.isoformat(),
        "advice": OFA.advice(db, symbol, today) if cfg.ta_advisor else None,
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
    base["ta_advisor"] = ta_advisor_view(request, db, symbol)
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
