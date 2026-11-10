"""D84 TradingAgents MGC research setup (part of the AI Duo button on MGC, PAPER only). PURE: Decimal, no I/O.

TradingAgents (in its own venv, bias/ta_runner.py `research`) returns a structured gold setup:
  {"side": "LONG|SHORT|NONE", "confidence": 0-100, "entry_low": p, "entry_high": p, "invalidation": p, "target": p,
   "valid_until": "HH:MM" (ET) or ISO time, "reasons": ["…"]}.
This module validates it and turns it into a TradePlan with the same §7 builder every strategy uses (stop beyond the
invalidation price, tick-rounded away from entry, rr floor 1.5R and cap from config, preferred 2R). A setup is
taken only when Vibe-Trading agrees on the side (the SAME shared agreement function as AI Duo: ai_duo.agree).
Every refusal is a reason code. No safety check is weakened: the normal G1–G8 / risk / hedge-lock / news /
flatten path follows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from app.clock import ET
from app.engine.ai_duo import agree
from app.engine.trade_plan import Direction, Skip, TradePlan, build_trade_plan


@dataclass(frozen=True)
class Setup:
    direction: Direction
    confidence: int
    entry_low: Decimal
    entry_high: Decimal
    invalidation: Decimal
    target: Decimal
    valid_until: str
    reasons: tuple[str, ...]
    lock_price: Decimal | None = (
        None  # the AI's own profit-lock level (optional); the manager uses it instead of config
    )


def _dec(x: Any) -> Decimal | None:
    if isinstance(x, bool) or x is None:
        return None
    try:
        d = Decimal(str(x))
    except InvalidOperation:
        return None
    return d if d.is_finite() and d > 0 else None


def parse_setup(raw: Any, min_confidence: int) -> Setup | str:
    """Raw research JSON → Setup, or a reason code: SETUP_MALFORMED, RESEARCH_NO_TRADE (side NONE), SETUP_CONF_LOW,
    SETUP_ZONE_INVALID, SETUP_LEVELS_INVALID (invalidation / target on the wrong side of the zone)."""
    if not isinstance(raw, dict):
        return "SETUP_MALFORMED"
    side = str(raw.get("side", "")).strip().upper()
    if side == "NONE":
        return "RESEARCH_NO_TRADE"
    if side not in ("LONG", "SHORT"):
        return "SETUP_MALFORMED"
    lo, hi, inv, tgt = (_dec(raw.get(k)) for k in ("entry_low", "entry_high", "invalidation", "target"))
    conf = raw.get("confidence")
    if lo is None or hi is None or inv is None or tgt is None or isinstance(conf, bool) or not isinstance(conf, int):
        return "SETUP_MALFORMED"
    if lo > hi:
        return "SETUP_ZONE_INVALID"
    d = Direction.LONG if side == "LONG" else Direction.SHORT
    # invalidation beyond the zone against the trade, target beyond it in the trade's favour
    levels_ok = (inv < lo and tgt > hi) if d is Direction.LONG else (inv > hi and tgt < lo)
    if not levels_ok:
        return "SETUP_LEVELS_INVALID"
    if conf < min_confidence:
        return "SETUP_CONF_LOW"
    reasons = raw.get("reasons")
    why = tuple(str(r)[:200] for r in reasons[:8]) if isinstance(reasons, list) else ()
    lock = _dec(raw.get("lock_price"))
    if lock is not None and not ((hi < lock < tgt) if d is Direction.LONG else (tgt < lock < lo)):
        lock = None  # a lock level outside zone → target is ignored (the config level applies), never an error
    return Setup(d, conf, lo, hi, inv, tgt, str(raw.get("valid_until", "")), why, lock)


def valid_until_at(value: str, day: str) -> datetime | None:
    """'HH:MM' (ET, on `day`) or an ISO timestamp → aware datetime; None when unreadable."""
    try:
        if len(value) <= 5:
            h, m = (int(x) for x in value.split(":"))
            return datetime.combine(datetime.fromisoformat(day).date(), time(h, m), tzinfo=ET)
        t = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=ET)


def in_zone(setup: Setup, close: Decimal) -> bool:
    return setup.entry_low <= close <= setup.entry_high


def past_levels(setup: Setup, close: Decimal) -> str | None:
    """Price already through the invalidation (SETUP_INVALIDATED) or the target (TARGET_REACHED): the day is over."""
    s = setup.direction.sign
    if (close - setup.invalidation) * s <= 0:
        return "SETUP_INVALIDATED"
    if (close - setup.target) * s >= 0:
        return "TARGET_REACHED"
    return None


@dataclass(frozen=True)
class SetupPlan:
    plan: TradePlan
    below_preferred: bool  # rr is between the floor (1.5R) and the preferred 2R: allowed, tagged


def build_plan(
    setup: Setup,
    entry: Decimal,
    *,
    tick: Decimal,
    buffer_ticks: int,
    min_stop_ticks: int,
    cap_pts: Decimal,
    rr_min: Decimal,
    rr_max: Decimal,
    rr_preferred: Decimal,
) -> SetupPlan | str:
    """The §7 builder (stop beyond the invalidation, rr floor/cap), the NOISE dollar stop as a hard cap on the risk
    (STOP_TOO_WIDE), and the preferred-2R tag."""
    p = build_trade_plan(
        setup.direction, entry, setup.invalidation, setup.target, tick, buffer_ticks, min_stop_ticks, rr_min, rr_max
    )
    if isinstance(p, Skip):
        return p.reason
    if p.risk_pts > cap_pts:
        return "STOP_TOO_WIDE"
    return SetupPlan(p, p.rr < rr_preferred)


def vibe_agrees(setup: Setup, vt_dir: str | None, vt_conf: int | None, vt_min_conf: int) -> str:
    """'AI_AGREE' or the skip code - the SAME rule AI Duo uses (ai_duo.agree) with TradingAgents' setup side."""
    code: str = agree(setup.direction.sign, True, vt_dir, vt_conf, vt_min_conf)[1]
    return code
