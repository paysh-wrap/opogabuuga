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
