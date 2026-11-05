"""TradePlan (§7) — reward:risk 2–3R [Pillar], plus the user-approved 1:1 mode (D7). Pure, Decimal only."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import StrEnum


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self is Direction.LONG else -1


@dataclass(frozen=True)
class Skip:
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class TradePlan:
    direction: Direction
    entry: Decimal
    stop: Decimal
    take_profit: Decimal
    risk_pts: Decimal
    rr: Decimal
    partial_price: Decimal | None = None
    breakeven_price: Decimal | None = None
    lock_price: Decimal | None = None  # D7: 1-contract stop lock (+0.30R) once price reaches partial_price
    mode: str = "STANDARD"  # STANDARD (2–3R) | ONE_TO_ONE (D7)


def round_to_tick(
    x: Decimal, tick: Decimal, *, away_from: Decimal | None = None, toward: Decimal | None = None
) -> Decimal:
    """Snap to the tick grid. `away_from=ref` moves x further from ref; `toward=ref` moves it closer.
    With neither, rounds to nearest (half up). Values already on the grid are returned unchanged."""
    q = x / tick
    if q == q.to_integral_value():
        return x
    if away_from is not None:
        mode = ROUND_FLOOR if x < away_from else ROUND_CEILING
    elif toward is not None:
        mode = ROUND_CEILING if x < toward else ROUND_FLOOR
    else:
        return (q + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR) * tick
    return q.to_integral_value(rounding=mode) * tick


def fee_cover_ticks(fee_rt: Decimal, tick_value: Decimal) -> int:
    """§8: ceil(round_trip_fee_per_contract / tick_value)."""
    return int((fee_rt / tick_value).to_integral_value(rounding=ROUND_CEILING))


def build_trade_plan(
    d: Direction,
    entry: Decimal,
    invalid: Decimal,
    t2: Decimal,
    tick: Decimal,
    buffer_ticks: int,
    min_stop_ticks: int,
    rr_min: Decimal = Decimal(2),
    rr_max: Decimal = Decimal(3),
) -> TradePlan | Skip:
    """§7 reference implementation (binding contract)."""
    s = d.sign
    stop = round_to_tick(invalid - s * buffer_ticks * tick, tick, away_from=entry)
    risk = (entry - stop) * s
    if risk <= 0:
        return Skip("STOP_INVALID")
    if risk / tick < min_stop_ticks:
        return Skip("STOP_TOO_TIGHT", f"{risk / tick} ticks < {min_stop_ticks}")
    rr_t2 = (t2 - entry) * s / risk
    if rr_t2 < rr_min:
        return Skip("RR_BELOW_MIN", f"T2 is {rr_t2:.2f}R")
    tp = round_to_tick(entry + s * min(rr_t2, rr_max) * risk, tick, toward=entry)
    rr = (tp - entry) * s / risk
    if rr < rr_min:
        return Skip("RR_BELOW_MIN_AFTER_ROUNDING", f"{rr:.3f}R")
    return TradePlan(d, entry, stop, tp, risk, rr)


def build_one_to_one_plan(
    d: Direction,
    entry: Decimal,
    invalid: Decimal,
    t2: Decimal,
    tick: Decimal,
    buffer_ticks: int,
    min_stop_ticks: int,
    partial_fraction: Decimal,
    lock_r: Decimal,
    fee_ticks: int,
    rr: Decimal = Decimal(1),
) -> TradePlan | Skip:
    """D7: TP exactly 1R (only if the model's T2 is at least 1R away). Partial at 75% of the way to TP, then
    breakeven (entry + fees); a single contract instead locks +lock_r R once the partial price is reached."""
    s = d.sign
    stop = round_to_tick(invalid - s * buffer_ticks * tick, tick, away_from=entry)
    risk = (entry - stop) * s
    if risk <= 0:
        return Skip("STOP_INVALID")
    if risk / tick < min_stop_ticks:
        return Skip("STOP_TOO_TIGHT", f"{risk / tick} ticks < {min_stop_ticks}")
    if (t2 - entry) * s < rr * risk:
        return Skip("RR_BELOW_MIN", "T2 closer than 1R")
    tp = entry + s * rr * risk  # entry and stop are on the grid, so 1R is exact
    partial = round_to_tick(entry + partial_fraction * (tp - entry), tick, toward=entry)  # (tp - entry) is signed
    be = entry + s * fee_ticks * tick
    lock = round_to_tick(entry + s * lock_r * risk, tick, toward=entry)
    if (lock - be) * s < 0:
        lock = be  # never lock below breakeven-with-fees
    return TradePlan(
        d, entry, stop, tp, risk, rr, partial_price=partial, breakeven_price=be, lock_price=lock, mode="ONE_TO_ONE"
    )


def rebuild_after_fill(
    plan: TradePlan,
    fill: Decimal,
    invalid: Decimal,
    t2: Decimal,
    tick: Decimal,
    buffer_ticks: int,
    min_stop_ticks: int,
    rr_min: Decimal,
    rr_max: Decimal,
) -> TradePlan | Skip:
    """§7: after a market fill, rebuild with the fill price; outside the window → Skip (caller flattens)."""
    p = build_trade_plan(plan.direction, fill, invalid, t2, tick, buffer_ticks, min_stop_ticks, rr_min, rr_max)
    if isinstance(p, Skip):
        return Skip("RR_INVALID_AFTER_FILL", p.reason)
    return replace(p, mode=plan.mode)
