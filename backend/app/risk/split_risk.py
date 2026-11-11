"""D92: "NOISE + AI Duo - split risk" button. Pure (no I/O).

When the button is on (and both strategies are on), each side gets half the size (rounded down, never below 1 micro)
and half the daily loss budget. This only ever TIGHTENS: it is applied on top of every other size / DLL / MLL check.
The share (0.5) comes from the rules file (`strategy.noise_ai_split_share`), never from code."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.risk.risk_base import money

SPLIT_STRATEGIES = ("NOISE", "AI_DUO")


def split_active(split_on: bool, noise_on: bool, ai_duo_on: bool) -> bool:
    """The split only exists while BOTH sides are switched on (otherwise a lone strategy keeps its normal size)."""
    return split_on and noise_on and ai_duo_on


def split_contracts(n: int, share: Decimal) -> int:
    """Half size, rounded DOWN, minimum 1 micro (0 stays 0: nothing to trade)."""
    if n <= 0:
        return 0
    return max(int((Decimal(n) * share).to_integral_value(rounding=ROUND_DOWN)), 1)


def split_budget(dll: Decimal | None, share: Decimal) -> Decimal | None:
    """This side's share of the daily loss limit; None when the account has no DLL (nothing to split)."""
    return None if dll is None else money(dll * share)


def side_budget_left(budget: Decimal, realised_pnl_today: Decimal, open_risk: Decimal) -> Decimal:
    """Budget still free for a NEW trade of this side: losses already taken today by this side and the risk still open
    on its positions are used up; profits never add room (same rule as `dll_remaining`)."""
    used = max(-realised_pnl_today, Decimal(0)) + open_risk
    return money(budget - used)
