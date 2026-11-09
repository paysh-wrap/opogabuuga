"""Weekly payout plan (§14). PURE. Lucid has no API: the app only PLANS; the user requests it in Lucid's dashboard.

Rules (numbers from the rules file):
- balance ≥ sweep_above + min_request → SWEEP down to sweep_above.
- else if MLL locked and skim_mode == half → SKIM 50% of this week's profit, if ≥ min_request and the balance stays
  ≥ buffer afterwards.
- else none. D65 mode "max_eligible" (Lucid Pro): balance − buffer (capped) once the cycle profit ≥ min_cycle_profit
  and the largest day ≤ consistency % of the cycle profit (optionally only once ≥ min_pct_of_cap × the cap).
Never plans a payout that leaves the balance below `buffer`, or with < min_cycle_profit since the last one.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

CENT = Decimal("0.01")


@dataclass(frozen=True)
class PayoutPlan:
    kind: str | None  # "sweep" | "skim" | None
    amount: Decimal
    net: Decimal  # after the firm's split
    reason: str


def plan_payout(
    *,
    balance: Decimal,
    week_profit: Decimal,
    cycle_profit: Decimal,
    locked: bool,
    sweep_above: Decimal,
    skim_mode: str,
    buffer: Decimal,
    min_request: Decimal,
    min_cycle_profit: Decimal,
    split: Decimal,
    payout_no: int = 1,
    max_first: Decimal | None = None,
    max_next: Decimal | None = None,
    max_pct_of_profit: Decimal | None = None,
    profitable_days: int = 0,
    min_profitable_days: int = 0,
    mode: str = "sweep_skim",
    largest_day: Decimal = Decimal(0),
    consistency_pct: Decimal | None = None,
    min_pct_of_cap: Decimal | None = None,
) -> PayoutPlan:
    def plan(kind: str, amt: Decimal, why: str) -> PayoutPlan:
        cap = max_first if payout_no <= 1 else max_next
        if cap is not None:
            amt = min(amt, cap)
        if max_pct_of_profit is not None:
            amt = min(amt, cycle_profit * max_pct_of_profit)
        amt = amt.quantize(CENT, rounding=ROUND_DOWN)
        if amt < min_request:
            return PayoutPlan(None, Decimal(0), Decimal(0), "CAPPED_BELOW_MIN_REQUEST")
        return PayoutPlan(kind, amt, (amt * split).quantize(CENT, rounding=ROUND_DOWN), why)

    if cycle_profit < min_cycle_profit:
        return PayoutPlan(None, Decimal(0), Decimal(0), "NO_PROFIT_SINCE_LAST_PAYOUT")
    if profitable_days < min_profitable_days:
        return PayoutPlan(None, Decimal(0), Decimal(0), "NOT_ENOUGH_PROFITABLE_DAYS")
    if mode == "max_eligible":  # D65 Lucid Pro: largest allowed payout, any day once eligible
        if consistency_pct is not None and largest_day > consistency_pct / 100 * cycle_profit:
            return PayoutPlan(None, Decimal(0), Decimal(0), "CONSISTENCY")
        if balance - buffer < min_request:
            return PayoutPlan(None, Decimal(0), Decimal(0), "BELOW_BUFFER")
        cap = max_first if payout_no <= 1 else max_next
        if min_pct_of_cap is not None and cap is not None and balance - buffer < min_pct_of_cap * cap:
            return PayoutPlan(None, Decimal(0), Decimal(0), "WAIT_FOR_LARGER")
        return plan("max", balance - buffer, f"largest payout above the {buffer} buffer")
    if balance >= sweep_above + min_request:
        return plan("sweep", balance - sweep_above, f"balance above {sweep_above}")
    if locked and skim_mode == "half":
        amt = (week_profit / 2).quantize(CENT, rounding=ROUND_DOWN)
        if amt < min_request:
            return PayoutPlan(None, Decimal(0), Decimal(0), "SKIM_BELOW_MIN_REQUEST")
        if balance - amt < buffer:
            return PayoutPlan(None, Decimal(0), Decimal(0), "WOULD_BREAK_BUFFER")
        return plan("skim", amt, "half of this week's profit")
    return PayoutPlan(None, Decimal(0), Decimal(0), "NOT_LOCKED" if not locked else "SKIM_OFF")
