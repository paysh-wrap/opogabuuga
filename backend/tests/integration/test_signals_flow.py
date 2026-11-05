"""Webhook → market state → confluence → stored signal, end to end (§4, §6, §21)."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.engine.filters import NewsEvent
from app.models import AuditLog, BiasDecision, Signal, TradePlanRow
from tests.conftest import WEBHOOK_SECRET

AT = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)  # 10:00 ET Thursday
MS = int(AT.timestamp() * 1000)
MIN = 60_000
C1T = MS - 30 * MIN
FR = {
    "c1_high": "20070",
    "c1_low": "19990",
    "c1_time_ms": C1T,
    "htf_atr14": "100",
    "t1": "20030",
    "t2": "20070",
    "invalid": "19981",
    "sweep_extreme": "19981",
    "sweep_time_ms": MS - 10 * MIN,
    "cisd_level": "19995",
    "cisd_before_c2_close": True,
    "t1_preticked": False,
    "c3_close_time_ms": MS + 13 * MIN,
}
MSO = {"trend": "BULL", "osc": "72", "div": None, "htf_trend": "BULL"}


def send(c, clock, event, t_ms, direction="LONG", profile="TIGHT", **extra):
    clock.set(datetime.fromtimestamp(t_ms / 1000 + 1, tz=UTC))
    p = {
        "v": 1,
        "secret": WEBHOOK_SECRET,
        "id": f"MNQ1!-{profile}-{t_ms}-{event}-{direction}",
        "symbol": "MNQ1!",
        "profile": profile,
        "tf": "1" if profile == "TIGHT" else "5",
        "bar_time_ms": t_ms,
        "event": event,
        "direction": direction,
        **extra,
    }
    r = c.post("/api/webhook/tradingview", content=json.dumps(p), headers={"content-type": "text/plain"})
    assert r.status_code == 200, r.text
    return r


def hb(c, clock, t_ms, close="20000", profile="TIGHT", mso=None):
    return send(
        c,
        clock,
        "HEARTBEAT",
        t_ms,
        "NONE",
        profile=profile,
        price={"o": close, "h": close, "l": close, "c": close, "v": "1"},
        mso={**(mso or MSO), "confirm_time_ms": t_ms},
    )


def confirm(c, clock, t_ms=MS - 2 * MIN, fr=None):
    send(c, clock, "MODEL_CONFIRMED", t_ms, fractal=fr or FR)


def choch(c, clock, t_ms=MS - 5 * MIN, direction="LONG"):
    send(c, clock, "MSO_CHOCH", t_ms, direction, mso={**MSO, "confirm_time_ms": t_ms})


@pytest.fixture
def ready(client, clock):
    """Bias LONG_ONLY for the session + an empty (but present) calendar."""
    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="0.7.1"))
        s.commit()
    client.app.state.calendar = lambda d: []
    return client


def signal(c):
    with c.app.state.sessionmaker() as s:
        return s.query(Signal).one()


def test_full_pass_stores_plan_gates_and_audit(ready, clock):
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN, close="20010")
    confirm(ready, clock)  # same bar as the heartbeat → evaluated now; close 20010 → RR vs T2 = 2.07R
    sig = signal(ready)
    assert sig.status == "PASS" and sig.passed and sig.skip_reason is None
    with ready.app.state.sessionmaker() as s:
        plans = s.query(TradePlanRow).all()
        assert [(p.mode, p.entry, p.stop, p.take_profit, p.rr) for p in plans] == [
            ("STANDARD", D(20010), D(19980), D(20070), D(2))
        ]  # risk 30 pts, T2 exactly 2R away
        assert s.query(AuditLog).filter_by(action="signal.pass").count() == 1
    body = ready.get("/api/signals/" + str(sig.id))
    assert body.status_code == 401  # login required


def test_api_lists_signal_with_gates(ready, clock, authed):
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN, close="20010")
    confirm(ready, clock)
    sigs = authed.get("/api/signals").json()["signals"]
    assert len(sigs) == 1 and sigs[0]["status"] == "PASS"
    assert [g["gate"] for g in sigs[0]["gates"]] == ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "SCORE"]
    assert all(g["passed"] for g in sigs[0]["gates"]) and D(sigs[0]["plans"][0]["rr"]) == 2


def test_no_calendar_waits_then_expires(client, clock):
    with client.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    choch(client, clock)
    hb(client, clock, MS - 2 * MIN)
    confirm(client, clock)
    assert (signal(client).status, signal(client).skip_reason) == ("WAIT", "CALENDAR_MISSING")
    for i in range(1, 7):  # max_wait_bars = 6 on a 1-minute chart
        hb(client, clock, MS - 2 * MIN + i * MIN)
    assert (signal(client).status, signal(client).skip_reason) == ("EXPIRED", "CALENDAR_MISSING")


def test_missing_bias_skips(client, clock):
    client.app.state.calendar = lambda d: []
    choch(client, clock)
    hb(client, clock, MS - 2 * MIN)
    confirm(client, clock)
    assert (signal(client).status, signal(client).skip_reason) == ("SKIP", "BIAS_NO_TRADE")


def test_news_blackout_waits(ready, clock):
    ready.app.state.calendar = lambda d: [NewsEvent(AT, "CPI")]
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN)
    confirm(ready, clock)
    assert signal(ready).skip_reason == "NEWS_BLACKOUT"


def test_event_before_its_heartbeat_waits_for_the_close_price(ready, clock):
    choch(ready, clock)
    hb(ready, clock, MS - 3 * MIN)
    confirm(ready, clock)  # bar MS-2min: heartbeat not here yet
    with ready.app.state.sessionmaker() as s:
        assert s.query(Signal).count() == 0
    hb(ready, clock, MS - 2 * MIN, close="20010")
    assert signal(ready).status == "PASS"


def test_one_entry_per_model_even_if_it_reconfirms(ready, clock):
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN, close="20010")
    confirm(ready, clock)
    assert signal(ready).status == "PASS"
    confirm(ready, clock, t_ms=MS + MIN)  # same c1_time_ms re-confirms
    hb(ready, clock, MS + MIN, close="20010")
    with ready.app.state.sessionmaker() as s:
        assert s.query(Signal).count() == 1 and s.query(TradePlanRow).count() == 1


def test_cooldown_after_three_failures_profile_scoped(ready, clock, authed):
    for i in range(3):
        fr = {**FR, "c1_time_ms": C1T - (i + 1) * 15 * MIN}
        send(ready, clock, "MODEL_FAILED", MS - (10 - i) * MIN, fractal=fr)
    cds = {(c["symbol"], c["profile"]): c for c in authed.get("/api/cooldowns").json()["cooldowns"]}
    assert cds[("MNQ", "TIGHT")]["active"] and cds[("MNQ", "TIGHT")]["until_session"] == "2026-11-12"
    assert ("MNQ", "STD") not in cds
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN, close="20010")
    confirm(ready, clock)
    assert (signal(ready).status, signal(ready).skip_reason) == ("SKIP", "COOLDOWN")
    assert authed.post("/api/cooldowns/TIGHT/clear", json={"confirm": "yes"}).status_code == 422
    assert authed.post("/api/cooldowns/TIGHT/clear", json={"confirm": "CLEAR COOLDOWN"}).json() == {"cleared": 1}
    assert not authed.get("/api/cooldowns").json()["cooldowns"][0]["active"]


def test_skip_report(ready, clock, authed):
    ready.app.state.calendar = lambda d: []
    with ready.app.state.sessionmaker() as s:
        s.query(BiasDecision).delete()
        s.commit()
    choch(ready, clock)
    hb(ready, clock, MS - 2 * MIN)
    confirm(ready, clock)
    rep = authed.get("/api/signals/skips?date=2026-11-05").json()
    assert rep["counts"] == {"BIAS_NO_TRADE": 1} and rep["sessions_in_avg"] == 0


def test_market_state_rebuilt_after_restart(settings, clock, mock_http):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app1 = create_app(settings, clock)
    with TestClient(app1) as c1:
        choch(c1, clock)
        hb(c1, clock, MS - 2 * MIN)
        confirm(c1, clock)
    app2 = create_app(settings, clock)
    with TestClient(app2):
        st = app2.state.market.get("MNQ", "TIGHT")
        assert st is not None and f"MNQ-TIGHT-{C1T}" in st.models and st.last_heartbeat_ms == MS - 2 * MIN
        assert st.mso_events and st.mso_events[0][0] == "MSO_CHOCH"


def test_processing_error_is_loud_not_silent(ready, clock, monkeypatch):
    import app.api.webhook as wh

    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(wh, "process", boom)
    hb(ready, clock, MS - 2 * MIN)  # still answers 200 (accepted & stored); error is broadcast + logged
    with ready.app.state.sessionmaker() as s:
        assert s.query(Signal).count() == 0


def test_timedelta_sanity():
    assert int((AT - timedelta(minutes=2)).timestamp() * 1000) == MS - 2 * MIN
