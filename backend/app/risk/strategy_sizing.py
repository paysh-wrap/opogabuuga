"""D63 automatic size per account for the fixed-size strategies (NOISE, PM_FADE). PURE.

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


def auto_contracts(size: Decimal, cushion: Decimal, table: Sequence[SizeTier]) -> AutoSize:
    t = tier_for(size, table)
    if t.brake_below is not None and t.brake_contracts is not None and cushion < t.brake_below * t.mll:
        return AutoSize(min(t.contracts, t.brake_contracts), t.account_size, True)
    return AutoSize(t.contracts, t.account_size, False)
