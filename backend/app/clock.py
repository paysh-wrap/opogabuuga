"""Injected clock. All trading logic receives a Clock; never call datetime.now() directly."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = UTC
SESSION_REOPEN = time(18, 0)


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware UTC now."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Deterministic clock for tests, replay and backtest."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock needs an aware datetime")
        self._at = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._at

    def set(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("aware datetime required")
        self._at = at.astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._at += delta


def to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("aware datetime required")
    return dt.astimezone(ET)


def et_now(clock: Clock) -> datetime:
    return to_et(clock.now())


def session_date(dt: datetime, reopen: time = SESSION_REOPEN) -> date:
    """CME session date: a session reopening at 18:00 ET belongs to the NEXT calendar day."""
    local = to_et(dt)
    return local.date() + timedelta(days=1) if local.time() >= reopen else local.date()


def parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def in_window(dt: datetime, windows: list[tuple[time, time]]) -> bool:
    t = to_et(dt).time()
    return any(start <= t < end for start, end in windows)
