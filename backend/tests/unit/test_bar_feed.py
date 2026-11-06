from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.automation.controller import Controller


def test_finest_feed_only_d37():
    c = SimpleNamespace(_bar_feeds={})
    ok = lambda tf, t: Controller.bar_feed_ok(c, "MGC", tf, t)  # noqa: E731
    t0 = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)
    assert ok("5", t0)  # only feed so far → used
    assert ok("1", t0 + timedelta(minutes=1))
    assert ok("1", t0 + timedelta(minutes=4))
    assert not ok("5", t0 + timedelta(minutes=5))  # 1-minute bars alive → 5-minute bar ignored
    assert ok("1", t0 + timedelta(minutes=5))
    assert ok("5", t0 + timedelta(minutes=15))  # 1-minute feed silent > 3 bars → fall back to 5-minute
    assert ok("D", t0)  # non-numeric timeframe → always used
