"""D16: history-based filter inputs, shadow evaluation of disabled instruments (A5), per-proxy bias."""

from datetime import timedelta
from decimal import Decimal as D

from app.models import BiasDecision, Event
from app.signals.stats import History, atr_percentile, load_history, t1_rate
from tests.integration.test_signals_flow import AT, FR


def _ev(s, i, event, c1, atr=None):
    fr = {**FR, "c1_time_ms": c1, **({"htf_atr14": atr} if atr else {})}
    s.add(
        Event(
            event_id=f"e{i}",
            symbol="MNQ",
            profile="TIGHT",
            event=event,
            direction="LONG",
            bar_time=AT - timedelta(days=1),
            payload={"fractal": fr},
        )
    )


def test_history_t1_rate_and_atr_percentile(client):
    with client.app.state.sessionmaker() as s:
        n = 0
        for k in range(10):
            c1 = 1_000_000 + k
            _ev(s, n, "MODEL_CONFIRMED", c1, atr=str(10 + k))
            n += 1
            _ev(s, n, "T1_HIT" if k < 7 else "MODEL_FAILED", c1)
            n += 1
        _ev(s, n, "MODEL_CONFIRMED", 2_000_000, atr="50")  # unresolved → not a sample
        s.commit()
        h = load_history(s, "MNQ", "TIGHT", AT)
    assert t1_rate(h, None) == (D("0.7"), 10)
    assert t1_rate(h, 1_000_000)[1] == 9  # the current model is excluded
    assert atr_percentile(h, D("14.5")) == (D("45.5"), 11)  # 5 of 11 below
    assert atr_percentile(History([], []), D(1)) == (None, 0)


def test_bias_is_per_proxy(client):
    """A GLD bias must not let an MNQ (QQQ) strategy through: today_bias reads THIS instrument's proxy only."""
    from app.signals.service import today_bias

    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="GLD", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
        assert today_bias(s, AT.date(), "QQQ") == "NO_TRADE"
        assert today_bias(s, AT.date(), "GLD") == "LONG_ONLY"
