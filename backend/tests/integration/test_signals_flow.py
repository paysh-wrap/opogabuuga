"""D105: shared helpers for the integration tests + the webhook paths that remain after the LunqFX removal.

LunqFX fractal alerts no longer create signals (the webhook ignores them). The safety tests (automation, kill switch,
restart recovery, watchdog, reliability, every stage) still need a tradeable signal: `confirm` stores a PASS signal
with a STANDARD §7 TradePlan (built by the real engine/trade_plan.build_trade_plan from the last heartbeat close) and
hands it to the REAL webhook dispatch (app.api.webhook.dispatch_updates: SEMI approval / FULL auto-execute), so the
controller, risk, order manager and monitor paths run exactly as they do for every strategy signal.
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.engine.trade_plan import Direction, Skip, build_trade_plan
from app.models import BiasDecision, Signal, TradePlanRow
from app.signals.service import SignalUpdate
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
    """A PASS signal (+ STANDARD plan from the last heartbeat close) dispatched through the real automation path."""
    from app.api.webhook import dispatch_updates

    f = fr or FR
    st = c.app.state
    ms = st.market.get("MNQ", "TIGHT")
    assert ms is not None and ms.last_price is not None, "send a heartbeat first"
    r = st.rules.rules
    tp, inst = r.trade_plan, r.instrument("MNQ")
    entry = D(str(ms.last_price["c"]))
    plan = build_trade_plan(
        Direction.LONG,
        entry,
        D(str(f["invalid"])),
        D(str(f["t2"])),
        inst.tick,
        tp.stop_buffer_ticks,
        tp.min_stop_ticks,
        tp.rr_min,
        tp.rr_max,
    )
    assert not isinstance(plan, Skip), plan
    at = datetime.fromtimestamp(t_ms / 1000, tz=UTC)
    key = f"MNQ-TIGHT-{f['c1_time_ms']}"
    with st.sessionmaker() as s:
        sig = Signal(
            symbol="MNQ",
            profile="TIGHT",
            direction="LONG",
            model_key=key,
            bar_time=at,
            entry_bar_time=at,
            status="PASS",
            passed=True,
            score=D(80),
            features={"invalid": str(f["invalid"]), "t2": str(f["t2"]), "c1_high": str(f["c1_high"])},
        )
        s.add(sig)
        s.flush()
        s.add(
            TradePlanRow(
                signal_id=sig.id,
                direction=plan.direction.value,
                entry=plan.entry,
                stop=plan.stop,
                take_profit=plan.take_profit,
                risk_pts=plan.risk_pts,
                rr=plan.rr,
                partial_price=plan.partial_price,
                breakeven_price=plan.breakeven_price,
                lock_price=plan.lock_price,
                mode=plan.mode,
            )
        )
        s.commit()
        sid = sig.id
    clock.set(datetime.fromtimestamp(t_ms / 1000 + 1, tz=UTC))
    c.portal.call(dispatch_updates, st, [SignalUpdate(sid, key, "PASS", None, "80")])
    return sid


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


def test_lunqfx_alerts_are_ignored_and_never_create_a_signal(ready, clock):
    """D105: a fractal alert is acknowledged (200, LUNQFX_REMOVED) and nothing is stored or evaluated."""
    hb(ready, clock, MS - 2 * MIN, close="20010")
    r = send(ready, clock, "MODEL_CONFIRMED", MS - 2 * MIN, fractal=FR)
    assert r.json()["ignored"] is True and r.json()["code"] == "LUNQFX_REMOVED"
    send(ready, clock, "MODEL_FAILED", MS - MIN, fractal=FR)
    with ready.app.state.sessionmaker() as s:
        assert s.query(Signal).count() == 0 and s.query(TradePlanRow).count() == 0


def test_market_state_rebuilt_after_restart(settings, clock, mock_http):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app1 = create_app(settings, clock)
    with TestClient(app1) as c1:
        choch(c1, clock)
        hb(c1, clock, MS - 2 * MIN)
    app2 = create_app(settings, clock)
    with TestClient(app2):
        st = app2.state.market.get("MNQ", "TIGHT")
        assert st is not None and st.last_heartbeat_ms == MS - 2 * MIN
        assert st.mso_events and st.mso_events[0][0] == "MSO_CHOCH"


def test_processing_error_is_loud_not_silent(ready, clock, monkeypatch):
    """§1.8: a strategy crash on a heartbeat still answers 200 (stored), broadcasts + notifies, and opens nothing."""
    from app.signals import strategy_service

    def boom(*a, **k):
        raise RuntimeError("db down")

    notes: list[tuple] = []
    ctl = ready.app.state.controller
    monkeypatch.setattr(strategy_service, "run", boom)
    monkeypatch.setattr(ctl, "notify", lambda *a, **k: notes.append(a))
    hb(ready, clock, MS - 2 * MIN)
    with ready.app.state.sessionmaker() as s:
        assert s.query(Signal).count() == 0
    assert notes and notes[0][1] == "Signal processing failed"


def test_timedelta_sanity():
    assert int((AT - timedelta(minutes=2)).timestamp() * 1000) == MS - 2 * MIN
