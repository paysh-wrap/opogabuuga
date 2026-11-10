"""D83 AI Duo (user button, PAPER only, default OFF): trade only the day's side that BOTH TradingAgents and Vibe-Trading
pick, entered on the first 5-minute VWAP pullback close in that direction. PURE: Decimal, no I/O, no clock.

AI = WHICH SIDE, price = WHEN. Vibe-Trading only gives an opinion (LONG/SHORT/NEUTRAL + confidence); it never trades.
Design: docs/results/session16/ai_combined_strategy_design.md. The trigger, structure stop and 2.0R target are
proposals — UNTESTED (LLM calls cannot be back-tested), so the strategy trades paper accounts only.

  side:    TA rating BUY/SELL and VT same side with confidence ≥ vt_min_conf, else a reason code (AI_*), no trade
  trigger: 5-minute bar (closing 09:40, 09:45 … ≤ window_end) that touches VWAP and closes back on the AI side of it
           in the AI direction (LONG: low ≤ VWAP < close and close > open; SHORT mirrored)
  stop:    beyond the pullback swing (lowest low / highest high of the trigger bar and the bar before it) ∓ buffer
           ticks, tick-rounded away from entry, CAPPED at the NOISE dollar stop in points (cap_pts)
  target:  entry ± rr_target × risk rounded toward entry, ≥ rr_min (config refuses rr_min < 1.5) else RR_BELOW_MIN
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.bias.policy import TA_SIDE, TA_STRONG, VT_SIDE
from app.engine.trade_plan import Direction, round_to_tick

RR_FLOOR = Decimal("1.5")  # binding firm-rule floor (CLAUDE.md D49)


@dataclass(frozen=True)
class Bar5:
    o: Decimal
    h: Decimal
    low: Decimal
    c: Decimal


@dataclass(frozen=True)
class DuoPlan:
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal
    stop_capped: bool


def ai_side(ta: str, vt_dir: str | None, vt_conf: int | None, min_conf: int) -> tuple[Direction | None, str]:
    """(side, reason code). A side only when both tools agree strongly; every other case is a stored skip reason."""
    ta = ta.strip().upper()
    if not ta:
        return None, "AI_TA_MISSING"
    if vt_dir is None:
        return None, "AI_VT_MISSING"
    t, v = TA_SIDE.get(ta, 0), VT_SIDE.get(vt_dir.upper(), 0)
    if t == 0 or v == 0:
        return None, "AI_NEUTRAL"
    if t != v:
        return None, "AI_DISAGREE"
    if ta not in TA_STRONG or (vt_conf or 0) < min_conf:
        return None, "AI_NOT_STRONG"
    return (Direction.LONG if t > 0 else Direction.SHORT), "AI_AGREE"


def aggregate(bars: Sequence[tuple[Decimal, Decimal, Decimal, Decimal]]) -> Bar5:
    """One bar from consecutive 1-minute (o, h, l, c) bars."""
    return Bar5(bars[0][0], max(b[1] for b in bars), min(b[2] for b in bars), bars[-1][3])


def pullback_trigger(direction: Direction, bar: Bar5, vwap: Decimal | None) -> bool:
    """The 5-minute bar pulled back to VWAP and closed back on the AI side of it, in the AI direction."""
    if vwap is None:
        return False
    if direction is Direction.LONG:
        return bar.low <= vwap < bar.c and bar.c > bar.o
    return bar.h >= vwap > bar.c and bar.c < bar.o


def plan(
    direction: Direction,
    entry: Decimal,
    bar: Bar5,
    prev: Bar5 | None,
    *,
    tick: Decimal,
    buffer_ticks: int,
    min_stop_ticks: int,
    cap_pts: Decimal,
    rr_target: Decimal,
    rr_min: Decimal,
) -> DuoPlan | str:
    """Structure stop (capped), target rr_target × risk. A reason string = skip."""
    s = direction.sign
    bars = [bar] if prev is None else [bar, prev]
    swing = min(b.low for b in bars) if s > 0 else max(b.h for b in bars)
    raw = round_to_tick(swing - s * buffer_ticks * tick, tick, away_from=entry)
    risk = (entry - raw) * s
    if risk <= 0:
        return "STOP_INVALID"
    capped = risk > cap_pts
    if capped:
        risk = cap_pts
    if risk < min_stop_ticks * tick:
        return "STOP_TOO_TIGHT"
    stop = entry - s * risk
    tp = round_to_tick(entry + s * rr_target * risk, tick, toward=entry)
    rr = ((tp - entry) * s / risk).quantize(Decimal("0.01"))
    if rr < max(rr_min, RR_FLOOR):
        return "RR_BELOW_MIN"
    return DuoPlan(direction, entry, stop, tp, risk, rr, capped)
