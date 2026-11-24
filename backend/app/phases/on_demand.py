"""Lucid On-Demand payouts (pure). CONFIRMED (Lucid help center, user screenshots 2026-11-24): with the Daily Loss Limit ON a
funded LucidPro account can request a payout DURING the trading session (6:00 PM to 3:45 PM ET) from the profit made that
session; min request, per-plan cap, payout consistency, buffer (initial MLL + $100) all apply; after an intraday request
trading on that account is paused until the end of the trading day; an account with a Hedging Violation is not eligible;
with the DLL OFF payouts follow the regular end-of-day schedule. Lucid has no API: the app only PLANS, the user requests
in Lucid's dashboard. All numbers are arguments (rules file); nothing is hard-coded except the session window below."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from decimal import ROUND_DOWN, Decimal

CENT = Decimal("0.01")
SESSION_END = time(15, 45)  # ET; the session runs 18:00 -> 15:45 (CONFIRMED, same screenshot)
SESSION_START = time(18, 0)

PAUSE_RULE = (
    "After you request an on-demand payout, trading on that account is paused until the end of the trading day. "
    "The app blocks new entries on it until the next session opens (18:00 ET)."
)
REASONS = {
    "OK": "On-demand payout available now.",
    "NOT_FUNDED": "On-demand payouts are for funded accounts only.",
    "NOT_LUCIDPRO": "On-demand payouts apply to LucidPro accounts (this plan is not LucidPro).",
    "DLL_OFF": "The Daily Loss Limit is OFF: this account follows the regular end-of-day payout schedule.",
    "HEDGING_VIOLATION": "This account has a Hedging Violation: it is not eligible for intraday payouts.",
    "OUTSIDE_SESSION": "Outside the on-demand window (6:00 PM to 3:45 PM ET).",
    "PAYOUT_OPEN": "A payout request is already open on this account.",
    "PAUSED_UNTIL_EOD": "A payout was already requested this session: trading is paused until the end of the trading day.",
    "MAX_PAYOUTS_REACHED": "The maximum number of payouts for this plan is reached.",
    "NO_SESSION_PROFIT": "No profit made this session yet: an on-demand payout is paid from this session's profit.",
    "NO_CYCLE_PROFIT": "The cycle profit is below the plan's minimum profit goal.",
    "NOT_ENOUGH_PROFITABLE_DAYS": "Not enough profitable days in this payout cycle (VERIFY: not on Lucid's official page).",
    "CONSISTENCY": "The largest day would exceed the consistency limit of the cycle profit.",
    "BELOW_BUFFER": "The balance above the buffer is below the minimum payout.",
    "BELOW_MINIMUM": "The payable amount is below the minimum payout.",
}


@dataclass(frozen=True)
class OnDemand:
    available: bool
    amount: Decimal  # gross, what to request in Lucid's dashboard
    net: Decimal  # after the Lucid split
    reason: str  # key of REASONS
    message: str
    limited_by: str  # which limit set the amount: session_profit | cap | buffer | ""


def in_session(t: time) -> bool:
    """True inside the on-demand window: everything except 15:45 <= t < 18:00 ET."""
    return not (SESSION_END <= t < SESSION_START)


def _no(reason: str) -> OnDemand:
    return OnDemand(False, Decimal(0), Decimal(0), reason, REASONS[reason], "")


def on_demand_offer(
    *,
    stage: str,
    plan: str,
    dll_enabled: bool,
    hedging_violation: bool,
    now_et: time,
    open_payout: bool,
    requested_this_session: bool,
    payouts_done: int,
    max_payouts: int | None,
    balance: Decimal,
    session_profit: Decimal,
    prior_day_profits: list[Decimal],
    buffer: Decimal,
    min_request: Decimal,
    min_cycle_profit: Decimal,
    min_profitable_days: int,
    cap_first: Decimal,
    cap_next: Decimal,
    consistency_pct: Decimal | None,
    split: Decimal,
) -> OnDemand:
    if stage != "FUNDED":
        return _no("NOT_FUNDED")
    if not plan.startswith("lucid_pro_"):
        return _no("NOT_LUCIDPRO")
    if not dll_enabled:
        return _no("DLL_OFF")
    if hedging_violation:
        return _no("HEDGING_VIOLATION")
    if not in_session(now_et):
        return _no("OUTSIDE_SESSION")
    if open_payout:
        return _no("PAYOUT_OPEN")
    if requested_this_session:
        return _no("PAUSED_UNTIL_EOD")
    if max_payouts is not None and payouts_done >= max_payouts:
        return _no("MAX_PAYOUTS_REACHED")
    if session_profit <= 0:
        return _no("NO_SESSION_PROFIT")
    days = [*prior_day_profits, session_profit]
    cycle = sum(days, Decimal(0))
    if cycle < min_cycle_profit:
        return _no("NO_CYCLE_PROFIT")
    if sum(1 for d in days if d > 0) < min_profitable_days:
        return _no("NOT_ENOUGH_PROFITABLE_DAYS")
    if consistency_pct is not None and max(days) > consistency_pct / 100 * cycle:
        return _no("CONSISTENCY")
    room = balance - buffer
    if room < min_request:
        return _no("BELOW_BUFFER")
    cap = cap_first if payouts_done == 0 else cap_next
    amount, by = min((session_profit, "session_profit"), (cap, "cap"), (room, "buffer"), key=lambda x: x[0])
    amount = amount.quantize(CENT, rounding=ROUND_DOWN)
    if amount < min_request:
        return _no("BELOW_MINIMUM")
    return OnDemand(True, amount, (amount * split).quantize(CENT, rounding=ROUND_DOWN), "OK", REASONS["OK"], by)
