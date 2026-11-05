"""Futures contract resolver (PURE): which real contract to send orders to on a given ET date.

TradingView charts the continuous symbol (MGC1!, MNQ1!) for signals; Lucid/Tradovate orders must name the actual
contract (MGCZ6, MNQZ6). Roll rules come from config (instrument.contract):
- roll "fnd" (COMEX metals): first notice day = last business day of the month BEFORE the contract month;
  switch to the next contract `roll_bdays` business days before FND.
- roll "expiry" (CME equity index): expiry = 3rd Friday of the contract month; switch `roll_days` calendar days
  before expiry (CME's standard roll date is 8 days before = the 2nd Thursday).
Exchange holidays are not modelled (business day = Mon–Fri) → `override` in config pins a contract when needed.
"""

from __future__ import annotations

from datetime import date, timedelta

MONTH_CODES = "FGHJKMNQUVXZ"  # Jan..Dec


def _last_bday(y: int, m: int) -> date:
    d = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _minus_bdays(d: date, n: int) -> date:
    while n > 0:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def third_friday(y: int, m: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(4 - d.weekday()) % 7)
    return d + timedelta(days=14)


def roll_date(y: int, m: int, roll: str, n: int) -> date:
    """First ET date on which contract (y, m) is no longer the one to trade."""
    if roll == "fnd":
        py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
        return _minus_bdays(_last_bday(py, pm), n)
    if roll == "expiry":
        return third_friday(y, m) - timedelta(days=n)
    raise ValueError(f"unknown roll rule {roll!r}")


def front_contract(root: str, months: str, roll: str, n: int, today: date) -> str:
    """'MGC', 'GJMQVZ', 'fnd', 2, 2026-11-05 → 'MGCZ6'."""
    if not months or any(c not in MONTH_CODES for c in months):
        raise ValueError(f"bad contract months {months!r}")
    nums = sorted(MONTH_CODES.index(c) + 1 for c in months)
    for y in (today.year, today.year + 1):
        for m in nums:
            if today < roll_date(y, m, roll, n):
                return f"{root}{MONTH_CODES[m - 1]}{y % 10}"
    raise AssertionError("unreachable")  # pragma: no cover


def is_roll_day(months: str, roll: str, n: int, today: date) -> bool:
    """True on the first day of a new front contract (liquidity moves; avoid new entries)."""
    nums = sorted(MONTH_CODES.index(c) + 1 for c in months)
    return any(roll_date(y, m, roll, n) == today for y in (today.year, today.year + 1) for m in nums)


def order_contract(root: str, cfg: object | None, today: date) -> str | None:
    """Contract to send orders to for instrument `root` (cfg = config ContractCfg). None = no contract config."""
    if cfg is None:
        return None
    override = getattr(cfg, "override", None)
    if override:
        return str(override)
    return front_contract(root, cfg.months, cfg.roll, cfg.roll_days, today)  # type: ignore[attr-defined]
