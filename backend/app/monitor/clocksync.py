"""D99: MEASURE the server clock drift (pre-flight §13: drift < 2 s) without NTP and without touching Lucid/TradingView.

Method: HEAD request to a reliable public host, read the HTTP `Date` header (RFC 7231, whole seconds, truncated).
The true server time lies in [Date, Date + 1 s), so the estimate is Date + 0.5 s and the uncertainty is
0.5 s + half the round trip. Drift = local clock - server clock (positive = our clock is ahead).

Safe behaviour (user-binding: only MANDATORY items may block):
- no sample at all (offline, proxy blocks, header missing)  -> drift UNKNOWN (None). Does NOT block; shown as "unknown".
- samples exist -> the median drift is "KNOWN > limit" only when |drift| - uncertainty > limit, i.e. even in the best
  case for us the clock is more than `limit` s off. Then pre-flight blocks (mandatory item). Smaller drifts pass.
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.clock import Clock

DEFAULT_HOSTS: tuple[str, ...] = ("https://www.cloudflare.com/", "https://www.google.com/")
LIMIT_S = 2.0
CACHE_S = 60.0


@dataclass(frozen=True)
class ClockSample:
    drift_s: float
    uncertainty_s: float


@dataclass(frozen=True)
class ClockReading:
    """drift_s None = unknown (could not be measured)."""

    drift_s: float | None
    uncertainty_s: float | None
    samples: int
    detail: str
    at: datetime | None = None

    @property
    def known_exceeds(self) -> bool:
        return exceeds_limit(self.drift_s, self.uncertainty_s)


def exceeds_limit(drift_s: float | None, uncertainty_s: float | None, limit: float = LIMIT_S) -> bool:
    if drift_s is None:
        return False
    return abs(drift_s) - (uncertainty_s or 0.0) > limit


def sample_from(local_before: datetime, local_after: datetime, date_header: str) -> ClockSample | None:
    try:
        server = parsedate_to_datetime(date_header)
    except (TypeError, ValueError):
        return None
    if server.tzinfo is None:
        return None
    rtt = max((local_after - local_before).total_seconds(), 0.0)
    mid = local_before + (local_after - local_before) / 2
    drift = (mid - server).total_seconds() - 0.5
    return ClockSample(drift, 0.5 + rtt / 2)


def combine(samples: list[ClockSample]) -> ClockReading:
    if not samples:
        return ClockReading(None, None, 0, "unknown — no reliable time source reachable")
    drift = statistics.median(s.drift_s for s in samples)
    unc = statistics.median(s.uncertainty_s for s in samples)
    return ClockReading(drift, unc, len(samples), f"{drift:+.2f} s (±{unc:.2f}, {len(samples)} source(s))")


async def _one(http: Any, clock: Clock, url: str) -> ClockSample | None:
    try:
        before = clock.now()
        r = await asyncio.wait_for(http.head(url, follow_redirects=False), timeout=4)
        after = clock.now()
        hdr = r.headers.get("date")
        return sample_from(before, after, hdr) if hdr else None
    except Exception:  # offline, proxy, mocked transport, timeout: never an error for pre-flight
        return None


async def measure(http: Any, clock: Clock, hosts: tuple[str, ...] = DEFAULT_HOSTS) -> ClockReading:
    got = await asyncio.gather(*[_one(http, clock, h) for h in hosts])
    rd = combine([g for g in got if g is not None])
    return ClockReading(rd.drift_s, rd.uncertainty_s, rd.samples, rd.detail, clock.now())


async def cached_measure(state: Any, hosts: tuple[str, ...] = DEFAULT_HOSTS) -> ClockReading:
    """Measure at most once per CACHE_S (the UI polls pre-flight every 30 s). `state` = app.state."""
    now = state.clock.now()
    prev: ClockReading | None = getattr(state, "clock_reading", None)
    if prev is not None and prev.at is not None and (now - prev.at).total_seconds() < CACHE_S:
        return prev
    rd = await measure(state.http, state.clock, hosts)
    state.clock_reading = rd
    return rd
