from datetime import UTC, datetime
from decimal import Decimal

from app.engine.market_state import MarketStateStore
from app.monitor.feed import bar_lag_s, data_feed_status
from app.webhook.schemas import WebhookPayload

NOW = datetime(2026, 11, 11, 15, 0, 30, tzinfo=UTC)
CLOSE = int(datetime(2026, 11, 11, 15, 0, 0, tzinfo=UTC).timestamp() * 1000)


def test_lag_math() -> None:
    assert bar_lag_s(CLOSE, NOW) == 30
    assert bar_lag_s(CLOSE + 99_000, NOW) == 0  # future skew clamped


def test_status() -> None:
    assert data_feed_status("realtime", 30, 90) == "realtime"
    assert data_feed_status("realtime", 200, 90) == "delayed"
    assert data_feed_status("delayed", 1, 90) == "delayed"
    assert data_feed_status(None, 30, 90) == "unknown"
    assert data_feed_status(None, 200, 90) == "delayed"
    assert data_feed_status("realtime", None, 90) == "unknown"


def _p(**price: str) -> WebhookPayload:
    return WebhookPayload.model_validate(
        {
            "v": 1,
            "secret": "x",
            "id": "a",
            "symbol": "MNQ",
            "profile": "TIGHT",
            "tf": "1",
            "bar_time_ms": CLOSE,
            "event": "HEARTBEAT",
            "direction": "NONE",
            "data_feed": "realtime",
            "price": {"o": "1", "h": "2", "l": "1", "c": "2", "v": "10", **price},
        }
    )


def test_ingest_tolerant_and_real_delta() -> None:
    store = MarketStateStore()
    st = store.apply("MNQ", _p())
    assert st.real_delta is None
    st = store.apply("MNQ", _p(up_volume="7", down_volume="3", delta="4"))
    assert st.real_delta == {"up_volume": Decimal(7), "down_volume": Decimal(3), "delta": Decimal(4)}


def test_tracker_symbol_delayed_while_any_chart_is_and_clears_after_three_good_bars():
    from app.monitor.feed import FeedDelayTracker

    t = FeedDelayTracker()
    assert t.update("MNQ", "TIGHT", "delayed", 120, 0) == "DELAYED"
    assert t.update("MNQ", "STD", "realtime", 1, 60) is None  # the other chart being fine does not clear it (was: flip)
    assert t.update("MNQ", "TIGHT", "realtime", 1, 60) is None
    assert t.update("MNQ", "TIGHT", "delayed", 95, 120) is None  # streak reset, still one change only
    assert t.symbol_lag("MNQ") == 95
    assert [t.update("MNQ", "TIGHT", "unknown", 2, 180 + i) for i in range(2)] == [None, None]
    assert t.update("MNQ", "TIGHT", "realtime", 1, 240) == "CLEARED"  # 3 non-delayed bars in a row
    assert t.symbol_lag("MNQ") is None
    assert t.update("MES", "TIGHT", "realtime", 1, 240) is None  # never delayed: nothing to clear
    t.update("MNQ", "TIGHT", "delayed", 100, 300)
    assert t.update("MNQ", "STD", "delayed", 300, 300) is None and t.symbol_lag("MNQ") == 300  # worst chart's lag


def test_silent_delayed_chart_is_forgotten_only_while_another_chart_keeps_reporting():
    """A delayed chart whose alert was deleted must not block NOISE / Order Flow on that symbol until a restart."""
    from app.monitor.feed import FeedDelayTracker

    t = FeedDelayTracker(stale_s=900)
    t.update("MNQ", "STD", "delayed", 200, 0)  # the 5m chart is delayed, then goes silent
    assert t.update("MNQ", "TIGHT", "realtime", 1, 600) is None and t.symbol_lag("MNQ") == 200  # 10 min: still blocked
    assert t.update("MNQ", "TIGHT", "realtime", 1, 901) == "CLEARED"  # silent > 15 min while TIGHT reports
    t.update("MGC", "TIGHT", "delayed", 200, 0)
    assert t.symbol_lag("MGC") == 200  # no other MGC chart reports: the block stays (safe)
