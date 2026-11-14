"""Feed freshness (§5.4): missing heartbeat for N× bar interval during CME session hours → STALE → block."""

from __future__ import annotations

from datetime import datetime, time
from typing import Literal

from app.clock import to_et

FeedStatus = Literal["FRESH", "STALE", "CLOSED", "NO_DATA"]


def cme_globex_open(dt: datetime) -> bool:
    """CME equity/metals Globex: Sun 18:00 → Fri 17:00 ET, daily halt 17:00–18:00 ET. Holidays not modelled."""
    et = to_et(dt)
    wd, t = et.weekday(), et.time()  # Mon=0 … Sun=6
    if wd == 5:  # Saturday
        return False
    if wd == 6:
        return t >= time(18, 0)
    if wd == 4 and t >= time(17, 0):
        return False
    return not (time(17, 0) <= t < time(18, 0))


def feed_status(last_close_ms: int | None, tf_min: int, now: datetime, multiple: int) -> FeedStatus:
    if not cme_globex_open(now):
        return "CLOSED"
    if last_close_ms is None:
        return "NO_DATA"
    age_ms = int(now.timestamp() * 1000) - last_close_ms
    return "STALE" if age_ms > multiple * tf_min * 60_000 else "FRESH"


DataFeed = Literal["realtime", "delayed", "unknown"]


def bar_lag_s(bar_close_ms: int, now: datetime) -> float:
    """Seconds between a bar's CLOSE and now (injected clock). Negative skew is clamped to 0."""
    return max(0.0, (now.timestamp() * 1000 - bar_close_ms) / 1000)


def data_feed_status(declared: str | None, lag_s: float | None, max_lag_s: int, tf_min: int = 1) -> DataFeed:
    """D112: CME real-time check. A declared 'delayed' (Pine timenow vs time_close) or a lag above the limit
    (scaled by bar size above 1m is NOT applied: lag is measured from the bar close) = delayed."""
    if declared == "delayed" or (lag_s is not None and lag_s > max_lag_s):
        return "delayed"
    if declared == "realtime" and lag_s is not None:
        return "realtime"
    return "unknown"


class FeedDelayTracker:
    """Delayed-data state per CHART (symbol, profile) — session 22 item 8. Before, one state per symbol was set by a
    delayed chart and cleared by the next normal bar of ANY chart, so a 1m and a 5m MNQ chart that disagreed flipped it
    on every heartbeat (notification spam, entries switching on and off). Now:
      * a symbol counts as delayed while ANY of its charts is delayed (tighter, never looser);
      * a chart clears only after `clear_after` non-delayed bars IN A ROW (a single good bar no longer clears it).
    `update` returns "DELAYED" / "CLEARED" only when the SYMBOL's state changes (one notification per change)."""

    def __init__(self, clear_after: int = 3) -> None:
        self.clear_after = clear_after
        self._lag: dict[tuple[str, str], float] = {}  # delayed charts → last lag (s)
        self._ok: dict[tuple[str, str], int] = {}  # delayed charts → non-delayed bars in a row since

    def symbol_lag(self, symbol: str) -> float | None:
        lags = [v for (s, _), v in self._lag.items() if s == symbol]
        return max(lags) if lags else None

    def update(self, symbol: str, profile: str, status: DataFeed, lag_s: float) -> Literal["DELAYED", "CLEARED"] | None:
        key = (symbol, profile)
        before = self.symbol_lag(symbol) is not None
        if status == "delayed":
            self._lag[key], self._ok[key] = lag_s, 0
        elif key in self._lag:
            self._ok[key] += 1
            if self._ok[key] >= self.clear_after:
                del self._lag[key], self._ok[key]
        after = self.symbol_lag(symbol) is not None
        return "DELAYED" if after and not before else "CLEARED" if before and not after else None
