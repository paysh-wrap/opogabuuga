"""Whole pipeline: Python indicators → bridge-format payloads → real webhook → DB → parity check (D105: LunqFX
alerts are acknowledged and dropped, everything else is stored and replays cleanly)."""

import json
from datetime import UTC, datetime
from decimal import Decimal as D

from app.backtest.parity import compare, replay_payloads
from app.models import Event
from app.webhook.schemas import FRACTAL_EVENTS
from tests.conftest import WEBHOOK_SECRET
from tests.unit.test_indicators import c1_bars, long_model_c2, mk


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
    )
    kept = [p for p in payloads if p["event"] not in FRACTAL_EVENTS and not p["event"].startswith("MSO_")]
    assert len(kept) < len(payloads)  # the replay does produce LunqFX alerts ...
    for p in payloads:
        clock.set(datetime.fromtimestamp(p["bar_time_ms"] / 1000 + 1, tz=UTC))  # arrives 1 s after bar close
        r = client.post(
            "/api/webhook/tradingview",
            content=json.dumps({**p, "secret": WEBHOOK_SECRET}),
            headers={"content-type": "text/plain"},
        )
        assert r.status_code == 200, (p["event"], r.text)
        if p["event"] in FRACTAL_EVENTS:  # ... which D105 acknowledges and drops
            assert r.json()["code"] == "LUNQFX_REMOVED", r.text
        elif p["event"].startswith("MSO_"):  # D120: MSO alerts are acknowledged and dropped too
            assert r.json()["code"] == "MSO_REMOVED", r.text
        else:
            assert r.json()["duplicate"] is False, (p["event"], r.text)
    with client.app.state.sessionmaker() as s:
        rows = s.query(Event).all()
        assert len(rows) == len(kept) and not any(e.event in FRACTAL_EVENTS for e in rows)
        recorded = [{**e.payload, "symbol": "MNQ1!"} for e in rows]
    rep = compare(kept, recorded)
    assert rep.clean and rep.matched == sum(1 for p in kept if p["event"] != "HEARTBEAT")
    st = client.app.state.market.get("MNQ", "TIGHT")
    assert st.last_heartbeat_ms == bars[-1].close_ms
