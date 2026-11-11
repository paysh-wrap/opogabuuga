"""D63 automatic size per account for the fixed-size strategies (NOISE, PM_FADE); D115 per-plan size helpers. PURE.

Each account is sized by its OWN Lucid account size (Account.starting_balance; the plan's account_size when unknown),
using the plan's strategy.size_table (config/rules/*.yaml). Tier = the largest row with account_size ≤ the account's
size; below the smallest row → the smallest row. Drawdown brake: when the cushion (equity − current MLL) is below
brake_below × the tier's MLL, trade brake_contracts instead. 5-year research: docs/results/session10/README.md §21–22.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SizeTier:
    account_size: Decimal
    mll: Decimal
    contracts: int
    brake_below: Decimal | None = None  # fraction of the MLL
    brake_contracts: int | None = None
    grow_per: Decimal | None = None  # D66: +1 micro per grow_per $ of cushion beyond the first grow_per
    max_contracts: int | None = None  # D66: growth cap
    taper_below_remaining: Decimal | None = None  # D69: fraction of the eval target still to earn
    taper_contracts: int | None = None  # D69: micros once less than that fraction of the target remains


@dataclass(frozen=True)
class AutoSize:
    contracts: int
    tier: Decimal  # account size of the chosen row
    braked: bool


def tier_for(size: Decimal, table: Sequence[SizeTier]) -> SizeTier:
    if not table:
        raise ValueError("empty size table")
    rows = sorted(table, key=lambda t: t.account_size)
    fit = [t for t in rows if t.account_size <= size]
    return fit[-1] if fit else rows[0]


def auto_contracts(
    size: Decimal, cushion: Decimal, table: Sequence[SizeTier], remaining_frac: Decimal | None = None
) -> AutoSize:
    """remaining_frac (EVAL only): share of the profit target still to earn at the start of the session."""
    t = tier_for(size, table)
    n = t.contracts
    if t.grow_per is not None and t.grow_per > 0:
        extra = max(0, int(cushion // t.grow_per) - 1)
        n = min(t.max_contracts or t.contracts, t.contracts + extra)
    tapered = (
        t.taper_below_remaining is not None
        and t.taper_contracts is not None
        and remaining_frac is not None
        and remaining_frac < t.taper_below_remaining
    )
    if tapered:  # D69 sprint-then-protect: big size far from the target, small size near it
        n = min(n, t.taper_contracts or n)
    if t.brake_below is not None and t.brake_contracts is not None and cushion < t.brake_below * t.mll:
        return AutoSize(min(n, t.brake_contracts), t.account_size, True)
    return AutoSize(n, t.account_size, False)


def bias_size(contracts: int, base_contracts: int, side: int, call: int) -> int:
    """D74 AI-bias sizing ("version B"). side = trade direction (+1/−1), call = proven AI call (+1/−1/0).
    Agree: +1 micro but never above the tier's base size + 1; disagree: −1 (min 1); no call: unchanged."""
    if call == 0 or side == 0:
        return contracts
    if call == side:
        return min(contracts + 1, base_contracts + 1)
    return max(1, contracts - 1)


def plan_contracts(contracts: int, plan_size: Decimal, account_size: Decimal) -> int:
    """D115: a strategy's per-plan size (config/rules/*.yaml) is written for the plan's own account size. An account
    SMALLER than the plan (mixed household) gets proportionally fewer micros (rounded down, min 1); never more."""
    if plan_size <= 0 or account_size >= plan_size:
        return contracts
    return max(1, min(contracts, int(contracts * account_size / plan_size)))


def risk_cap(*caps: Decimal | None) -> Decimal | None:
    """D115: the tightest per-trade $ cap that applies (strategy budget, AI Duo cap, the plan's per-trade cap)."""
    vals = [c for c in caps if c is not None]
    return min(vals) if vals else None
