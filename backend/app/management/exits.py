"""Exit rules (§8 early exits, D8 minimum hold). Pure."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.engine.trade_plan import TradePlan

PROTECTIVE = {"STOP", "TAKE_PROFIT", "KILL_SWITCH", "MLL_BREACH", "DLL_BREACH", "NEWS_FLATTEN", "FLAT_TIME"}


def early_exit_allowed(plan: TradePlan, best_price: Decimal, partial_filled: bool, until_r: Decimal) -> bool:
    """C3-close / CHoCH-against exits only BEFORE +1R or the partial (§8)."""
    if partial_filled:
        return False
    best_r = (best_price - plan.entry) * plan.direction.sign / plan.risk_pts
    return best_r < until_r


def exit_allowed_now(kind: str, opened_at: datetime, now: datetime, min_hold_s: int) -> bool:
    """D8: app-initiated exits wait until the trade is ≥ min_hold_s old; protective exits never wait."""
    if kind in PROTECTIVE:
        return True
    return (now - opened_at).total_seconds() >= min_hold_s


def rapid_profit_share(trades: list[tuple[Decimal, float]], hold_limit_s: int) -> Decimal:
    """% of net profit from trades held ≤ hold_limit_s (Lucid microscalp metric). trades = (pnl, held seconds)."""
    profit = sum((p for p, _ in trades if p > 0), Decimal(0))
    if profit <= 0:
        return Decimal(0)
    fast = sum((p for p, h in trades if p > 0 and h <= hold_limit_s), Decimal(0))
    return (fast * 100 / profit).quantize(Decimal("0.01"))
