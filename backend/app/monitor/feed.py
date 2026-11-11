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
