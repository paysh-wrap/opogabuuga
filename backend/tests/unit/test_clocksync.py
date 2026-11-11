"""D99: server clock drift is MEASURED from HTTP Date headers; unmeasurable = unknown (never blocks)."""

import asyncio
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx

from app.clock import FixedClock
from app.monitor import clocksync as cs

NOW = datetime(2026, 11, 11, 15, 0, 0, tzinfo=UTC)


def _date(dt: datetime) -> str:
    return format_datetime(dt, usegmt=True)


def test_sample_math_local_ahead_and_behind():
    s = cs.sample_from(NOW, NOW, _date(NOW))  # Date is truncated to the second: true time in [Date, Date+1)
    assert s is not None and abs(s.drift_s + 0.5) < 1e-9 and s.uncertainty_s == 0.5
    ahead = cs.sample_from(NOW + timedelta(seconds=10), NOW + timedelta(seconds=10), _date(NOW))
    assert ahead is not None and ahead.drift_s > 9
    slow = cs.sample_from(NOW, NOW + timedelta(seconds=2), _date(NOW + timedelta(seconds=1)))
    assert slow is not None and slow.uncertainty_s == 1.5  # half the round trip is added to the uncertainty


def test_bad_header_is_no_sample():
    assert cs.sample_from(NOW, NOW, "not a date") is None
    assert cs.sample_from(NOW, NOW, "Tue, 11 Nov 2026 15:00:00") is None  # no zone


def test_known_exceeds_only_when_certain():
    assert cs.exceeds_limit(None, None) is False  # unknown never blocks
    assert cs.exceeds_limit(2.4, 0.6) is False  # could still be within 2 s
    assert cs.exceeds_limit(3.0, 0.5) is True
    assert cs.exceeds_limit(-30.0, 0.5) is True  # behind is just as bad
    assert cs.combine([]).drift_s is None and "unknown" in cs.combine([]).detail


def _http(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_measure_median_of_sources_and_failures_are_unknown():
    clk = FixedClock(NOW)

    def ok(req):
        return httpx.Response(200, headers={"date": _date(NOW - timedelta(seconds=30))})

    rd = asyncio.run(cs.measure(_http(ok), clk))
    assert rd.samples == 2 and rd.drift_s is not None and 29 < rd.drift_s < 31 and rd.known_exceeds

    def boom(req):
        raise AssertionError("offline")  # not even an httpx error: still just "unknown"

    rd = asyncio.run(cs.measure(_http(boom), clk))
    assert rd.drift_s is None and rd.samples == 0 and not rd.known_exceeds

    def no_header(req):
        return httpx.Response(200)

    assert asyncio.run(cs.measure(_http(no_header), clk)).drift_s is None


def test_cached_measure_hits_the_network_once_a_minute():
    calls = []

    def ok(req):
        calls.append(1)
        return httpx.Response(200, headers={"date": _date(NOW)})

    class S:
        clock = FixedClock(NOW)
        http = _http(ok)

    asyncio.run(cs.cached_measure(S))
    n = len(calls)
    asyncio.run(cs.cached_measure(S))
    assert len(calls) == n
    S.clock.advance(timedelta(seconds=61))
    asyncio.run(cs.cached_measure(S))
    assert len(calls) == 2 * n
