"""Whole pipeline: Python indicators → bridge-format payloads → real webhook → DB → parity check."""

import json
from datetime import UTC, datetime
from decimal import Decimal as D

from app.backtest.parity import compare, replay_payloads
from app.models import Event
from tests.conftest import WEBHOOK_SECRET
from tests.unit.test_indicators import T0, c1_bars, long_model_c2, mk


def test_replayed_session_flows_through_webhook_and_parity_is_clean(client, clock):
    bars = (
        c1_bars()
        + long_model_c2()
        + [mk(30, 107, 108, 106.5, 107.5), mk(31, 107.5, 110.25, 107, 110)]
        + [mk(i, 110, 110.5, 109.5, 110) for i in range(32, 45)]
    )
    payloads = replay_payloads(
        bars,
        symbol="MNQ1!",
        profile="TIGHT",
        tf="1",
        htf_min=15,
        tick=D("0.25"),
        atr_period=14,
        pivot_left=5,
        pivot_right=3,
        osc_length=14,
    )
    sent = 0
    for p in payloads:
        clock.set(datetime.fromtimestamp(p["bar_time_ms"] / 1000 + 1, tz=UTC))  # arrives 1 s after bar close
        r = client.post(
            "/api/webhook/tradingview",
            content=json.dumps({**p, "secret": WEBHOOK_SECRET}),
            headers={"content-type": "text/plain"},
        )
        assert r.status_code == 200 and r.json()["duplicate"] is False, (p["event"], r.text)
        sent += 1
    with client.app.state.sessionmaker() as s:
        rows = s.query(Event).all()
        assert len(rows) == sent
        recorded = [{**e.payload, "symbol": "MNQ1!"} for e in rows]
    rep = compare(payloads, recorded)
    assert rep.clean and rep.matched == sum(1 for p in payloads if p["event"] != "HEARTBEAT")
    events = [(e.event, e.direction) for e in rows if e.event != "HEARTBEAT"]
    assert ("MODEL_CONFIRMED", "LONG") in events and ("T2_HIT", "LONG") in events
    st = client.app.state.market.get("MNQ", "TIGHT")
    model = st.models[f"MNQ-TIGHT-{T0}"]
    assert model.events[-1] == "C3_CLOSED" and "MODEL_CONFIRMED" in model.events
    assert st.last_heartbeat_ms == bars[-1].close_ms
