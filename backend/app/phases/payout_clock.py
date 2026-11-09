"""Payout + go-live countdown (Lucid funded/live). PURE: numbers come from the rules file, time from the caller.

- Next payout check = next `check_time` ("Fri 17:05" ET) after now (weekly) — on_demand → None.
- Eligible amount = balance − buffer, only when ≥ min_request; else "needed" = buffer + min_request − balance.
- Go-live trigger (FUNDED only): a day with profit ≥ max_daily_profit_live_trigger moves the account to LIVE.
  Shows how much more profit TODAY would trigger it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


@dataclass(frozen=True)
class PayoutClock:
    next_check: datetime | None
    seconds_left: int | None
    eligible: Decimal  # requestable now (0 if below min_request)
    needed: Decimal  # more balance needed to reach the first requestable amount (0 if eligible)
    live_trigger_left: Decimal | None  # FUNDED: today's profit still needed to trigger the move to LIVE


def next_check(now: datetime, check_time: str) -> datetime:
    day, hm = check_time.split()
    h, m = (int(x) for x in hm.split(":"))
    local = now.astimezone(ET)
    ahead = (DAYS[day] - local.weekday()) % 7
    cand = datetime.combine(local.date() + timedelta(days=ahead), time(h, m), ET)
    if cand <= local:
        cand += timedelta(days=7)
    return cand


def next_session_check(now: datetime, hm: str) -> datetime:
    """D65: next weekday at hm (ET) after now."""
    h, m = (int(x) for x in hm.split(":"))
    local = now.astimezone(ET)
    cand = datetime.combine(local.date(), time(h, m), ET)
    while cand <= local or cand.weekday() >= 5:
        cand = datetime.combine(cand.date() + timedelta(days=1), time(h, m), ET)
    return cand


def payout_clock(
    *,
    stage: str,
    balance: Decimal,
    today_pnl: Decimal,
    now: datetime,
    frequency: str,
    check_time: str,
    buffer: Decimal,
    min_request: Decimal,
    live_trigger: Decimal | None,
    session_check_time: str = "17:05",
) -> PayoutClock:
    nxt = (
        next_check(now, check_time)
        if frequency == "weekly"
        else next_session_check(now, session_check_time)
        if frequency == "every_n_sessions"
        else None
    )
    secs = int((nxt - now).total_seconds()) if nxt else None
    over = balance - buffer
    eligible = over if over >= min_request else Decimal(0)
    needed = Decimal(0) if eligible else buffer + min_request - balance
    left = max(live_trigger - today_pnl, Decimal(0)) if stage == "FUNDED" and live_trigger is not None else None
    return PayoutClock(nxt, secs, eligible, needed, left)
