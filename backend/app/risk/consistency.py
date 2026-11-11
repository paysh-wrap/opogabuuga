"""Consistency guard (§11C EVAL; D16 FUNDED as the user's own limit). Pure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, Decimal

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


def live_day_stop_hit(today_realised: Decimal, open_pnl: Decimal, lim: ConsistencyLimits) -> bool:
    """N6: live flatten condition for fixed-size strategy trades: realised + open profit has reached the day stop."""
    return today_realised + open_pnl >= lim.day_stop


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


# ---------- D89: Lucid's official PAYOUT-ELIGIBILITY consistency rule (LucidPro, stage FUNDED only) ----------
# Lucid support, "Consistency Percentage" (2026-08-26): Largest Single Day Profit / Account Profit = Consistency
# Percentage; it must be at or below the limit to be eligible to REQUEST a payout (not a breach), and the cycle resets
# after each payout. It does not apply on LIVE. All numbers (limit, legacy limit, cutoff) come from the rules file.


@dataclass(frozen=True)
class PayoutConsistency:
    cycle_profit: Decimal  # account profit this payout cycle (sum of day profits, losing days included)
    largest_day: Decimal  # largest single day profit this cycle (0 when no profitable day)
    pct: Decimal | None  # largest day / cycle profit × 100; None when the cycle profit is not positive
    limit: Decimal
    eligible: bool  # "exactly at the limit" counts as eligible (DECISIONS D89, VERIFY)
    needed_cycle_profit: Decimal  # cycle profit at which today's largest day sits exactly at the limit
    still_needed: Decimal  # extra cycle profit still to make (0 when eligible)


def payout_rule_applies(stage: str, enabled: bool) -> bool:
    """FUNDED only: the rule is gone on LIVE and never applies to EVAL."""
    return enabled and stage == "FUNDED"


def payout_limit(
    purchased_at: datetime | None, pct: Decimal, legacy_pct: Decimal, legacy_cutoff: datetime
) -> tuple[Decimal, bool]:
    """(limit %, date_known). Accounts purchased/reset ON OR BEFORE the cutoff keep the legacy (35%) limit; unknown date
    → the stricter of the two, so the UI can ask for the date (never assume the looser limit)."""
    if purchased_at is None:
        return min(pct, legacy_pct), False
    return (legacy_pct if purchased_at <= legacy_cutoff else pct), True


def consistency_percentage(day_profits: list[Decimal]) -> Decimal | None:
    """Largest single day profit / account profit × 100 (Lucid's formula); None while the account profit is ≤ 0."""
    total = sum(day_profits, Decimal(0))
    if total <= 0:
        return None
    return max(max(day_profits), Decimal(0)) / total * D100


def payout_consistency(day_profits: list[Decimal], limit: Decimal) -> PayoutConsistency:
    total = sum(day_profits, Decimal(0))
    largest = max(max(day_profits, default=Decimal(0)), Decimal(0))
    pct = consistency_percentage(day_profits)
    eligible = pct is not None and pct <= limit
    needed = money((largest * D100 / limit).to_integral_value(rounding=ROUND_CEILING)) if largest > 0 else Decimal(0)
    still = Decimal(0) if eligible or largest <= 0 else max(needed - total, Decimal(0))
    return PayoutConsistency(total, largest, pct, limit, eligible, needed, still)


def _usd(x: Decimal) -> str:
    return f"${x:,.2f}"


def payout_consistency_text(c: PayoutConsistency) -> str:
    """Plain sentence for the Payouts page and the Dashboard."""
    if c.eligible:
        return (
            f"Consistency met: your largest day is {c.pct:.1f}% of the cycle profit (limit {c.limit}%). "
            "Payout requests are allowed."
        )
    if c.largest_day <= 0:
        return "No profitable day yet in this payout cycle: nothing to request."
    return (
        f"Largest day {_usd(c.largest_day)} must be at most {c.limit}% of the cycle profit: "
        f"you need {_usd(c.needed_cycle_profit)} "
        f"cycle profit (now {_usd(c.cycle_profit)}, {_usd(c.still_needed)} more) before a payout can be requested."
    )
