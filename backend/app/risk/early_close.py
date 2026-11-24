"""D179: CME early-close days (pure, no I/O). The table comes from config/early_closes.yaml (third-party, UNVERIFIED,
editable) via app/early_close.py; nothing here knows a date. Only ever tightens: no new entries from
(close - no_entry_before_min) and a flatten at (close - flatten_before_min). A missing date changes nothing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class EarlyClose:
    days: Mapping[str, str]  # ISO date -> "HH:MM" ET close, or "closed"
    no_entry_before_min: int
    flatten_before_min: int


def _minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def close_minute(ec: EarlyClose | None, day: date) -> int | None:
    """ET minute of the day of the early close; 0 for a closed day; None = a normal day."""
    if ec is None:
        return None
    v = ec.days.get(day.isoformat())
    if v is None:
        return None
    return 0 if v == "closed" else _minutes(v)


def entries_blocked(ec: EarlyClose | None, day: date, now: time) -> bool:
    """True from (close - no_entry_before_min) on an early-close day (whole day when closed)."""
    c = close_minute(ec, day)
    if c is None or ec is None:
        return False
    return c == 0 or now.hour * 60 + now.minute >= c - ec.no_entry_before_min


def flatten_due(ec: EarlyClose | None, day: date, now: time) -> bool:
    """True from (close - flatten_before_min) on an early-close day: flatten every open position."""
    c = close_minute(ec, day)
    if c is None or ec is None:
        return False
    return c == 0 or now.hour * 60 + now.minute >= c - ec.flatten_before_min
