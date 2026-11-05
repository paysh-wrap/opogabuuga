"""D16: history-based filter inputs, shadow evaluation of disabled instruments (A5), per-proxy bias."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.models import BiasDecision, Event, Signal, TradePlanRow
from app.signals.stats import History, atr_percentile, load_history, t1_rate
from tests.conftest import WEBHOOK_SECRET
from tests.integration.test_signals_flow import AT, FR, MIN, MS, MSO, choch, confirm, hb


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


def test_disabled_instrument_is_evaluated_in_shadow_never_traded(client, clock, authed):
    client.app.state.calendar = lambda d: []
    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="GLD", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    fr = {
        "c1_high": "2015.0",
        "c1_low": "2002.0",
        "c1_time_ms": MS - 30 * MIN,
        "htf_atr14": "10",
        "t1": "2008.5",
        "t2": "2015.0",
        "invalid": "1999.0",
        "sweep_extreme": "1999.0",
        "sweep_time_ms": MS - 10 * MIN,
        "cisd_level": "2003.0",
        "cisd_before_c2_close": True,
        "t1_preticked": False,
        "c3_close_time_ms": MS + 13 * MIN,
    }

    def send(event, t_ms, **extra):
        clock.set(datetime.fromtimestamp(t_ms / 1000 + 1, tz=UTC))
        p = {
            "v": 1,
            "secret": WEBHOOK_SECRET,
            "id": f"MGC1!-TIGHT-{t_ms}-{event}",
            "symbol": "MGC1!",
            "profile": "TIGHT",
            "tf": "1",
            "bar_time_ms": t_ms,
            "event": event,
            "direction": "NONE" if event == "HEARTBEAT" else "LONG",
            **extra,
        }
        assert client.post("/api/webhook/tradingview", content=json.dumps(p)).status_code == 200

    send("MSO_CHOCH", MS - 5 * MIN, mso={**MSO, "confirm_time_ms": MS - 5 * MIN})
    send(
        "HEARTBEAT",
        MS - 2 * MIN,
        price={"o": "2003.0", "h": "2003.0", "l": "2003.0", "c": "2003.0", "v": "1"},
        mso={**MSO, "confirm_time_ms": MS - 2 * MIN},
    )
    send("MODEL_CONFIRMED", MS - 2 * MIN, fractal=fr)
    with client.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        from app.models import SignalGate

        gates = {g.gate: g.detail["code"] for g in s.query(SignalGate).all()}
        assert sig.symbol == "MGC" and sig.status == "SHADOWED" and not sig.passed, (sig.status, gates)
        assert sig.skip_reason == "INSTRUMENT_DISABLED"
        assert sig.features["shadow"]["outcome"] == "PASS"
        assert D(sig.features["shadow"]["plan"]["stop"]) == D("1998.6")
        assert s.query(TradePlanRow).count() == 0  # no real plan for a shadow signal
    assert authed.get("/api/signals/skips?date=2026-11-05").json()["counts"] == {}


def test_bias_is_per_proxy(client, clock):
    """A GLD bias must not let an MNQ (QQQ) signal through."""
    client.app.state.calendar = lambda d: []
    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="GLD", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    choch(client, clock)
    hb(client, clock, MS - 2 * MIN, close="20010")
    confirm(client, clock)
    with client.app.state.sessionmaker() as s:
        assert s.query(Signal).one().skip_reason == "BIAS_NO_TRADE"
