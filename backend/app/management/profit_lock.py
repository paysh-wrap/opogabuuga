"""D75-P1 profit lock for NOISE (D82 presets). PURE: no I/O, no clock.

Once a trade has been `trigger_pts` points in profit, its protective stop moves to entry + `lock_pts` points (a ratchet:
never loosened). It is a stop move, not a profit target. When that locked stop is the exit, NOISE trades no more that
day (strategy_service reads the PROFIT_LOCK exit reason). A protective stop exit never waits (D8). Research:
docs/results/session15/README.md (trigger +100 pt, lock +10 pt; neighbours +75/+150 and 0/25 pt tested).
"""

from __future__ import annotations

from decimal import Decimal

from app.engine.trade_plan import Direction, round_to_tick

PROFIT_LOCK_REASON = "PROFIT_LOCK"


def lock_triggered(direction: Direction, entry: Decimal, best: Decimal, trigger_pts: Decimal) -> bool:
    """True once the best price reached entry ± trigger_pts in the trade's favour."""
    return (best - entry) * direction.sign >= trigger_pts


def lock_stop(
    direction: Direction, entry: Decimal, best: Decimal, trigger_pts: Decimal, lock_pts: Decimal, tick: Decimal
) -> Decimal | None:
    """The locked stop (entry + sign·lock_pts, tick-rounded toward entry so it never over-claims), or None when the
    trigger has not been reached."""
    if not lock_triggered(direction, entry, best, trigger_pts):
        return None
    return round_to_tick(entry + direction.sign * lock_pts, tick, toward=entry)
