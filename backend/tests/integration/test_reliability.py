"""Session 14: lost-signal replay (item 3), missed check minute, feed-loss protection (item 5)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.main import watchdog_once
from app.models import Bar, Event, Signal, Trade
from app.signals import recovery
from app.webhook.schemas import WebhookPayload
from tests.integration.test_all_stages import run
from tests.integration.test_signals_flow import MIN, MS, WEBHOOK_SECRET, hb


def put(authed, **changes):
    r = authed.put("/api/risk/settings", json={"changes": changes})
    assert r.status_code == 200, r.text


def lost_heartbeat(authed, t_ms, close):
    """An event the server accepted (stored) but whose processing never ran."""
    p = WebhookPayload.model_validate(
        {
            "v": 1, "secret": WEBHOOK_SECRET, "id": f"MNQ1!-TIGHT-{t_ms}-HEARTBEAT-NONE", "symbol": "MNQ1!",
            "profile": "TIGHT", "tf": "1", "bar_time_ms": t_ms, "event": "HEARTBEAT", "direction": "NONE",
            "price": {"o": close, "h": close, "l": close, "c": close, "v": "1"},
        }
    )  # fmt: skip
    with authed.app.state.sessionmaker() as s:
        s.add(Event(event_id=p.id, symbol="MNQ", profile="TIGHT", event="HEARTBEAT", direction="NONE",
                    bar_time=datetime.fromtimestamp(t_ms / 1000, tz=UTC),
                    payload=p.model_dump(mode="json", exclude={"secret"})))  # fmt: skip
        s.commit()
    return p.id


def processed(authed, event_id):
    with authed.app.state.sessionmaker() as s:
        return s.query(Event).filter_by(event_id=event_id).one().processed_at


# ---------- processed_at / replay ----------
def test_webhook_marks_events_processed(authed, clock):
    hb(authed, clock, MS)
    with authed.app.state.sessionmaker() as s:
        assert s.query(Event).one().processed_at is not None


def test_unprocessed_heartbeat_is_replayed_once_and_still_runs_the_exit_checks(authed, clock):
    run(authed, clock, "EVAL")  # open paper trade; target 20070
    eid = lost_heartbeat(authed, MS - MIN, "20071")  # the bar that hit the target was accepted but never processed
    clock.set(datetime.fromtimestamp(MS / 1000, tz=UTC))  # 60 s later
    assert processed(authed, eid) is None
    assert asyncio.run(recovery.reprocess_unprocessed(authed.app)) == 1
    assert processed(authed, eid) is not None
    with authed.app.state.sessionmaker() as s:
        assert s.query(Trade).one().exit_reason == "TP"
    assert asyncio.run(recovery.reprocess_unprocessed(authed.app)) == 0  # idempotent


def test_replay_window_age_and_inflight_guards(authed, clock):
    hb(authed, clock, MS)  # something stored so the clock is sane
    old = lost_heartbeat(authed, MS - 10 * MIN, "20000")
    young = lost_heartbeat(authed, MS + 50 * 1000, "20000")
    clock.set(datetime.fromtimestamp(MS / 1000 + 60, tz=UTC))
    authed.app.state.inflight_events.add(young)
    assert asyncio.run(recovery.reprocess_unprocessed(authed.app)) == 0  # too old / still in its normal task
    assert processed(authed, old) is None and processed(authed, young) is None


def test_failing_replay_alerts_and_gives_up_after_three_tries(authed, clock, monkeypatch):
    from app.signals import strategy_service

    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(strategy_service, "run", boom)
    eid = lost_heartbeat(authed, MS - MIN, "20000")
    clock.set(datetime.fromtimestamp(MS / 1000, tz=UTC))
    for _ in range(3):
        asyncio.run(recovery.reprocess_unprocessed(authed.app))
    assert processed(authed, eid) is not None
    titles = [n["title"] for n in authed.app.state.controller.notices]
    assert "Signal processing failed" in titles and "A price bar could not be processed" in titles


def test_unreadable_payload_is_marked_and_alerted(authed, clock):
    eid = lost_heartbeat(authed, MS - MIN, "20000")
    with authed.app.state.sessionmaker() as s:
        s.query(Event).one().payload = {"nonsense": 1}
        s.commit()
    clock.set(datetime.fromtimestamp(MS / 1000, tz=UTC))
    asyncio.run(recovery.reprocess_unprocessed(authed.app))
    assert processed(authed, eid) is not None


def test_startup_replays_unprocessed_heartbeats(authed, clock):
    from fastapi.testclient import TestClient

    from app.main import create_app

    eid = lost_heartbeat(authed, MS - MIN, "20000")
    clock.set(datetime.fromtimestamp(MS / 1000, tz=UTC))
    with TestClient(create_app(authed.app.state.settings, clock)):
        assert processed(authed, eid) is not None


# ---------- missed check minute ----------
def noise_rules(authed):
    r = authed.app.state.rules.rules
    return r.model_copy(update={"strategy": r.strategy.model_copy(update={"noise": True})})


def add_bar(s, close):
    s.add(Bar(symbol="MNQ", tf="1", close_time=close, o=D(1), h=D(1), l=D(1), c=D(1), v=D(1), source="tradingview"))


def test_missed_check_minute_detected_once_and_cleared_by_a_late_bar(authed, clock):
    check = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)  # 10:00 ET: first NOISE check minute
    r = noise_rules(authed)
    with authed.app.state.sessionmaker() as s:
        assert recovery.missed_checks(s, r, check + timedelta(seconds=100)) == []  # no bar today: market closed
        add_bar(s, check - timedelta(minutes=1))
        s.commit()
        assert recovery.missed_checks(s, r, check + timedelta(seconds=60)) == []  # inside the 90 s grace
        miss = recovery.missed_checks(s, r, check + timedelta(seconds=100))
        assert [m["minute_et"] for m in miss] == ["10:00"]
        off = r.model_copy(update={"strategy": r.strategy.model_copy(update={"noise": False})})
        assert recovery.missed_checks(s, off, check + timedelta(seconds=100)) == []
        assert recovery.missed_checks(s, r, datetime(2026, 11, 7, 15, 2, tzinfo=UTC)) == []  # Saturday
        add_bar(s, check)
        s.commit()
        assert recovery.missed_checks(s, r, check + timedelta(seconds=100)) == []


def test_missed_check_alert_is_sent_once(authed, clock):
    put(authed, **{"strategy.noise": True})
    check = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
    with authed.app.state.sessionmaker() as s:
        add_bar(s, check - timedelta(minutes=1))
        s.commit()
    clock.set(check + timedelta(seconds=100))
    ctl = authed.app.state.controller
    for _ in range(2):
        recovery.alert_missed_checks(authed.app)
    assert [n["title"] for n in ctl.notices].count("Missed check minute") == 1
    assert authed.get("/api/safety").json()["missed_checks"][0]["minute_et"] == "10:00"


# ---------- feed guard ----------
def open_trade(authed, clock):
    run(authed, clock, "EVAL")
    ctl = authed.app.state.controller
    with authed.app.state.sessionmaker() as s:
        sid = s.query(Signal).one().id
    return ctl, sid


def test_feed_guard_warns_blocks_entries_then_flattens_feed_lost(authed, clock):
    ctl, sid = open_trade(authed, clock)
    t0 = clock.now()
    clock.set(t0 + timedelta(minutes=2))
    asyncio.run(watchdog_once(authed.app))
    assert ctl.feed_state == {}
    clock.set(t0 + timedelta(minutes=4))
    asyncio.run(watchdog_once(authed.app))
    assert ctl.feed_state == {"MNQ": "WARN"}
    assert [n["title"] for n in ctl.notices if n["level"] == "error"].count("Price feed lost while in a position") == 1
    assert authed.get("/api/safety").json()["feed"] == [{"symbol": "MNQ", "state": "WARN"}]
    res = asyncio.run(ctl.execute(sid, "automation"))
    assert res[0].reason == "FEED_LOST"  # no NEW entries while the feed is down
    assert authed.get("/api/positions").json()["accounts"][0]["positions"]  # still open: not yet 6 min
    clock.set(t0 + timedelta(minutes=7))
    asyncio.run(watchdog_once(authed.app))
    assert authed.get("/api/positions").json()["accounts"][0]["positions"] == []
    with authed.app.state.sessionmaker() as s:
        assert s.query(Trade).one().exit_reason == "FEED_LOST"
    asyncio.run(watchdog_once(authed.app))  # flat now: the state clears and the user is told it is over
    assert ctl.feed_state == {}
    assert any(n["title"] == "Price feed is back" for n in ctl.notices)


def test_feed_returning_clears_the_block(authed, clock):
    ctl, _ = open_trade(authed, clock)
    clock.set(clock.now() + timedelta(minutes=4))
    asyncio.run(watchdog_once(authed.app))
    assert ctl.feed_state == {"MNQ": "WARN"}
    now_ms = int(clock.now().timestamp() * 1000) - 1000
    hb(authed, clock, now_ms - now_ms % 60000, close="20010")
    asyncio.run(watchdog_once(authed.app))
    assert ctl.feed_state == {}
    assert any(n["title"] == "Price feed is back" for n in ctl.notices)


def test_feed_guard_thresholds_and_switch_come_from_settings(authed, clock):
    open_trade(authed, clock)
    put(authed, **{"reliability.feed_warn_min": 1, "reliability.feed_flatten_min": 2})
    clock.set(clock.now() + timedelta(minutes=3))
    asyncio.run(watchdog_once(authed.app))
    with authed.app.state.sessionmaker() as s:
        assert s.query(Trade).one().exit_reason == "FEED_LOST"


def test_feed_guard_can_be_switched_off(authed, clock):
    ctl, _ = open_trade(authed, clock)
    put(authed, **{"reliability.feed_guard_enabled": False})
    clock.set(clock.now() + timedelta(minutes=30))
    asyncio.run(ctl.feed_guard())
    assert ctl.feed_state == {}
    assert authed.get("/api/positions").json()["accounts"][0]["positions"]


def test_feed_thresholds_are_validated(authed):
    r = authed.put("/api/risk/settings", json={"changes": {"reliability.feed_warn_min": 6}})
    assert r.status_code == 422 and "feed_flatten_min" in r.text


def test_feed_guard_uses_the_slower_feed_when_no_1m_bars(authed, clock):
    ctl, _ = open_trade(authed, clock)
    with authed.app.state.sessionmaker() as s:
        s.query(Bar).delete()
        s.add(Bar(symbol="MNQ", tf="5", close_time=clock.now(), o=D(1), h=D(1), l=D(1), c=D(1), v=D(1), source="x"))
        s.commit()
    clock.set(clock.now() + timedelta(minutes=4))  # a 5-minute profile: a 4-minute gap is normal
    asyncio.run(ctl.feed_guard())
    assert ctl.feed_state == {}
    clock.set(clock.now() + timedelta(minutes=5))
    asyncio.run(ctl.feed_guard())
    assert ctl.feed_state == {"MNQ": "WARN"}
