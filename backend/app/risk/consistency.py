"""Consistency guard (§11C EVAL; D16 FUNDED as the user's own limit). Pure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.risk.risk_base import money

D100 = Decimal(100)


@dataclass(frozen=True)
class ConsistencyLimits:
    cap: Decimal  # today's profit must never exceed this
    day_stop: Decimal  # stop trading for the day once today's profit reaches this


def eval_limits(profit_target: Decimal, consistency_pct: Decimal, buffer_pct: Decimal) -> ConsistencyLimits:
    """40% × $1,250 = $500 cap; (40 − 5)% × $1,250 = $437.50 day stop."""
    return ConsistencyLimits(
        money(consistency_pct / D100 * profit_target), money((consistency_pct - buffer_pct) / D100 * profit_target)
    )


def funded_limits(
    cycle_profit: Decimal, reference_min: Decimal, consistency_pct: Decimal, buffer_pct: Decimal
) -> ConsistencyLimits:
    """D16: reference = max($1,250, payout-cycle profit so far)."""
    ref = max(reference_min, cycle_profit)
    return eval_limits(ref, consistency_pct, buffer_pct)


def day_stopped(today_profit: Decimal, lim: ConsistencyLimits) -> bool:
    return today_profit >= lim.day_stop


def fit_contracts(
    n: int, today_profit: Decimal, reward_per_contract_net: Decimal, lim: ConsistencyLimits, min_qty: int
) -> int:
    """Reduce contracts so today's profit + planned net reward at TP stays ≤ cap. 0 → Skip("CONSISTENCY_CAP")."""
    if reward_per_contract_net <= 0:
        return n
    room = lim.cap - today_profit
    fit = min(n, int(room // reward_per_contract_net)) if room > 0 else 0
    return fit if fit >= min_qty else 0


def largest_day_ok(day_profits: list[Decimal], consistency_pct: Decimal) -> bool:
    total = sum((p for p in day_profits), Decimal(0))
    if total <= 0:
        return False
    return max(day_profits) <= consistency_pct / D100 * total


def profitable_days(day_profits: list[Decimal]) -> int:
    return sum(1 for p in day_profits if p > 0)
