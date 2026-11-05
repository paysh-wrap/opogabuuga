from datetime import UTC, datetime, timedelta

from app.signals.stats import History, StatsCache


def test_cache_ages_in_app_time():
    c = StatsCache(ttl_s=300)
    h = History([], [])
    t0 = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)
    c.put(("MGC", "TIGHT"), h, t0)
    assert c.get(("MGC", "TIGHT"), t0 + timedelta(seconds=299)) is h
    assert c.get(("MGC", "TIGHT"), t0 + timedelta(minutes=6)) is None  # replay: market time, not wall time
    assert c.get(("MGC", "TIGHT"), t0 - timedelta(days=1)) is None  # clock moved back → refresh
    c.put(("MNQ", "STD"), h)  # no clock → monotonic (unchanged behaviour)
    assert c.get(("MNQ", "STD")) is h
