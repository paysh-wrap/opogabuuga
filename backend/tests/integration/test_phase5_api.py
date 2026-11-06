"""WS event bus, notifications, jobs, manual ticket, eval pace, payout settings, plan, journal, backtest delete."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest
from starlette.websockets import WebSocketDisconnect

from app.events import EVENTS, EventBus, UnknownEvent
from app.models import Account, BacktestRun, BacktestTrade, DailyAccountStats, Notification, Order, Payout, Trade
from tests.integration.test_automation_flow import setup


def _wait_notifications(c, n=1, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        r = c.get("/api/notifications").json()
        if len(r["notifications"]) >= n:
            return r
        time.sleep(0.05)
    raise AssertionError("notifications not stored")


# ---------- WebSocket ----------
def test_ws_requires_session(client):
    with pytest.raises(WebSocketDisconnect) as e, client.websocket_connect("/api/ws") as ws:
        ws.receive_text()
    assert e.value.code == 4401


def test_ws_broadcasts_kill_switch_events_and_notification(authed, clock):
    setup(authed, clock)
    with authed.websocket_connect("/api/ws") as ws:
        assert authed.post("/api/kill-switch", json={"confirm": "KILL"}).status_code == 200
        seen = {}
        for _ in range(20):
            m = ws.receive_json()
            seen[m["event"]] = m["data"]
            if {"risk.alert", "automation.changed", "notification"} <= seen.keys():
                break
    assert seen["risk.alert"]["kill_switch"] is True
    assert seen["automation.changed"]["mode"] == "OFF"
    assert seen["notification"]["title"] == "KILL SWITCH" and seen["notification"]["read"] is False
    r = _wait_notifications(authed)
    assert r["unread"] >= 1 and any(n["kind"] == "kill_switch" for n in r["notifications"])


def test_notifications_mark_read(authed, clock):
    with authed.app.state.sessionmaker() as s:
        s.add_all([Notification(level="warn", title=f"n{i}", body="", channels=["in_app"]) for i in range(3)])
        s.commit()
    r = authed.get("/api/notifications?unread=true").json()
    assert r["unread"] == 3
    first = r["notifications"][0]["id"]
    assert authed.post("/api/notifications/read", json={"ids": []}).status_code == 422
    assert authed.post("/api/notifications/read", json={"ids": [first]}).json()["marked"] == 1
    assert authed.get("/api/notifications").json()["unread"] == 2
    assert authed.post("/api/notifications/read", json={}).json()["marked"] == 2
    assert authed.get("/api/notifications?unread=true").json()["notifications"] == []
    assert authed.post("/api/notifications/read", json={}, headers={"x-csrf-token": "bad"}).status_code == 403


def test_bus_rejects_unknown_events_and_survives_failures(authed):
    bus = authed.app.state.bus
    assert {"signal.updated", "job.progress", "notification", "risk.day_lockin"} <= EVENTS
    with pytest.raises(UnknownEvent):
        bus.publish("nope", {})
    with pytest.raises(UnknownEvent):
        asyncio.run(bus.emit("nope", {}))

    class Boom:
        async def broadcast(self, *_):
            raise RuntimeError("x")

    b2 = EventBus(Boom(), authed.app.state.sessionmaker, authed.app.state.clock.now)
    asyncio.run(b2.emit("notification", {}))  # logged, not raised
    b2.publish("notification", {})  # no loop bound → dropped with a warning
    b2.notify("bogus-level", "t")  # no loop → dropped

    class BadMaker:
        def __call__(self):
            raise RuntimeError("db down")

    b3 = EventBus(Boom(), BadMaker(), authed.app.state.clock.now)  # type: ignore[arg-type]
    assert b3._store("info", "t", "", "general") is None


def test_bus_notify_from_worker_thread_and_drain(authed):
    bus = authed.app.state.bus
    bus.notify("bogus", "From thread", "detail", "test")  # TestClient: no running loop here → bound loop
    r = _wait_notifications(authed)
    n = r["notifications"][0]
    assert n["title"] == "From thread" and n["level"] == "error" and n["kind"] == "test"
    authed.portal.call(bus.drain)


def test_jobs_indicator_lists_bus_jobs_and_running_backtests(authed):
    bus = authed.app.state.bus
    bus.job("lab-cycle", "lab", "Strategy Lab", "running", 150)
    with authed.app.state.sessionmaker() as s:
        s.add(BacktestRun(kind="NIGHTLY", status="running", cache_key="k", progress=10))
        s.commit()
    jobs = authed.get("/api/jobs").json()["jobs"]
    assert {j["kind"] for j in jobs} == {"lab", "backtest"}
    assert next(j for j in jobs if j["kind"] == "lab")["progress"] == 100
    bus.job("lab-cycle", "lab", "Strategy Lab", "done", 100)
    assert [j["kind"] for j in authed.get("/api/jobs").json()["jobs"]] == ["backtest"]


# ---------- backtest delete ----------
def test_backtest_delete(authed):
    with authed.app.state.sessionmaker() as s:
        done = BacktestRun(kind="ON_DEMAND", status="done", cache_key="a")
        run = BacktestRun(kind="ON_DEMAND", status="running", cache_key="b")
        s.add_all([done, run])
        s.flush()
        s.add(BacktestTrade(run_id=done.id, data={"x": 1}))
        s.commit()
        did, rid = done.id, run.id
    assert authed.delete("/api/backtest/999").status_code == 404
    assert authed.delete(f"/api/backtest/{rid}").status_code == 409
    assert authed.delete(f"/api/backtest/{did}").json() == {"deleted": did}
    with authed.app.state.sessionmaker() as s:
        assert s.get(BacktestRun, did) is None and s.query(BacktestTrade).count() == 0
    assert any(x["action"] == "backtest.delete" for x in authed.get("/api/logs").json()["logs"])


# ---------- manual ticket ----------
def _price(authed, px="20000"):
    authed.app.state.controller.adapter.sim.last["MNQ"] = D(px)


def test_manual_order_goes_through_full_risk_path(authed, clock):
    aid = setup(authed, clock)
    body = {"account_id": aid, "symbol": "MNQ", "direction": "LONG", "stop": "19980", "take_profit": "20040"}
    assert authed.post("/api/orders/manual", json=body).status_code == 409  # no price yet
    _price(authed)
    r = authed.post("/api/orders/manual", json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["result"]["ok"] and j["result"]["contracts"] >= 1, j
    assert any(c["check"] == "hedge_lock" for c in j["result"]["checks"])  # same pretrade checks as automation
    with authed.app.state.sessionmaker() as s:
        assert {o.source for o in s.query(Order).all()} == {"MANUAL"}
    again = authed.post("/api/orders/manual", json=body).json()["result"]
    assert again["ok"] is False and again["reason"] == "POSITION_OPEN"  # max 1 position, no bypass
    logs = [x["action"] for x in authed.get("/api/logs").json()["logs"]]
    assert "order.manual" in logs and "trade.pretrade" in logs


def test_manual_order_refusals(authed, clock):
    aid = setup(authed, clock)
    _price(authed)
    base = {"account_id": aid, "symbol": "MNQ", "direction": "LONG", "stop": "19980", "take_profit": "20040"}
    r = authed.post("/api/orders/manual", json={**base, "take_profit": "20010"})
    assert r.status_code == 422 and r.json()["detail"].startswith("RR_BELOW_MIN")
    assert authed.post("/api/orders/manual", json={**base, "stop": "20010"}).status_code == 422  # STOP_INVALID
    assert authed.post("/api/orders/manual", json={**base, "symbol": "XYZ"}).status_code == 422
    assert authed.post("/api/orders/manual", json={**base, "account_id": 999}).status_code == 404
    assert authed.post("/api/orders/manual", json={**base, "stop": "-1"}).status_code == 422
    with authed.app.state.sessionmaker() as s:
        s.get(Account, aid).armed = False
        s.commit()
    res = authed.post("/api/orders/manual", json=base).json()["result"]
    assert res["ok"] is False and res["reason"] == "ACCOUNT_NOT_READY"
    authed.app.state.calendar = lambda d: None
    assert authed.post("/api/orders/manual", json=base).json()["detail"].startswith("NO_CALENDAR")

    class Ev:
        at = clock.now() + timedelta(minutes=1)
        title = "CPI"

    authed.app.state.calendar = lambda d: [Ev()]
    assert authed.post("/api/orders/manual", json=base).json()["detail"].startswith("NEWS_BLACKOUT")
    authed.app.state.rules.error = "bad"
    assert authed.post("/api/orders/manual", json=base).status_code == 409
    authed.app.state.rules.error = None
    authed.app.state.calendar = lambda d: []
    authed.app.state.controller.entries_blocked_by_time = lambda: True
    assert authed.post("/api/orders/manual", json=base).json()["detail"].startswith("FLATTEN_TIME")


# ---------- eval pace ----------
def test_eval_pace(authed, clock):
    aid = authed.post("/api/accounts", json={"label": "E1", "stage": "EVAL"}).json()["id"]
    fid = authed.post("/api/accounts", json={"label": "F1", "stage": "FUNDED"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        a = s.get(Account, aid)
        s.add(DailyAccountStats(account_id=aid, session_date=clock.now().date(), day_profit=D(300)))
        s.add(Trade(account_id=aid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(2), pnl_usd=D(300),
                    risk_usd=D(70), opened_at=clock.now(), closed_at=clock.now(), trade_ref="P1"))  # fmt: skip
        a.stage_started_at = clock.now() - timedelta(days=1)
        s.commit()
    p = authed.get(f"/api/accounts/{aid}/eval-pace").json()
    assert D(p["profit"]) == 300 and D(p["target_left"]) == 950 and p["profitable_days"] == 1
    assert D(p["largest_day"]) == 300 and D(p["consistency_cap"]) == 500 and D(p["consistency_headroom"]) == 200
    assert authed.get(f"/api/accounts/{fid}/eval-pace").status_code == 409
    assert authed.get("/api/accounts/999/eval-pace").status_code == 404


# ---------- payout settings + plan ----------
def test_payout_settings_validated_audited_applied(authed):
    g = authed.get("/api/payouts/settings").json()
    assert g["skim_mode"] == "half" and g["frequency"] == "weekly"
    assert authed.put("/api/payouts/settings", json={"skim_mode": "all", "frequency": "weekly"}).status_code == 422
    r = authed.put("/api/payouts/settings", json={"skim_mode": "off", "frequency": "on_demand"})
    assert r.status_code == 200 and r.json()["skim_mode"] == "off"
    assert authed.app.state.rules.rules.payouts.frequency == "on_demand"
    assert any(x["action"] == "payouts.settings" for x in authed.get("/api/logs").json()["logs"])
    assert authed.get("/api/plan").json()["next_payout"]["check_at"] is None


def test_holder_rejects_invalid_stored_payout_settings(authed):
    from app.automation.state import set_setting

    st = authed.app.state
    with st.sessionmaker() as s:
        set_setting(s, "payouts.settings", {"skim_mode": "everything"}, st.clock.now())
        s.commit()
        st.rules.refresh(s)
    assert st.rules.error and "payout settings" in st.rules.error


def test_plan_tracker_projection_next_payout(authed, clock):
    from app.api.plan import next_check

    fid = authed.post("/api/accounts", json={"label": "F1", "stage": "FUNDED", "balance": "28700"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        s.add(Account(broker_account_id="GONE", label="X", stage="FUNDED", drawdown_type="eod"))
        s.add(Payout(account_id=fid, week="2026-W40", kind="sweep", amount=D(900), balance_before=D(29000),
                     status="processed", processed_at=clock.now() - timedelta(days=30)))  # fmt: skip
        s.add(Trade(account_id=fid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(2), pnl_usd=D(600),
                    risk_usd=D(70), opened_at=clock.now(), closed_at=clock.now(), trade_ref="P2"))  # fmt: skip
        s.commit()
    j = authed.get("/api/plan").json()
    t = j["tracker"]
    assert D(t["ytd_gross"]) == 900 and t["payouts_processed"] == 1 and D(t["ytd_net"]) > 0
    pr = j["projection"]
    assert len(pr["months"]) == 12 and D(pr["months"][11]["cumulative"]) == D(pr["monthly_net"]) * 12
    accts = {a["label"]: a for a in j["next_payout"]["accounts"]}
    assert accts["X"]["error"] == "broker not connected" and "kind" in accts["F1"]
    assert j["next_payout"]["check_at"] is not None
    thu = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
    assert next_check(thu, "Fri 17:05").date().isoformat() == "2026-11-06"
    fri_late = datetime(2026, 11, 6, 23, 0, tzinfo=UTC)
    assert next_check(fri_late, "Fri 17:05").date().isoformat() == "2026-11-13"


def test_payout_ready_publishes_event(authed, clock):
    from tests.conftest import PASSWORD
    from tests.integration.test_payouts import FRI

    clock.set(FRI)
    r = authed.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    authed.headers["x-csrf-token"] = r.json()["csrf"]
    fid = authed.post("/api/accounts", json={"label": "F1", "stage": "FUNDED", "balance": "28700"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        s.add(Trade(account_id=fid, symbol="MNQ", direction="LONG", qty=1, entry=D(1), exit=D(2), pnl_usd=D(600),
                    risk_usd=D(70), opened_at=FRI, closed_at=FRI, trade_ref="P3"))  # fmt: skip
        s.commit()
    with authed.websocket_connect("/api/ws") as ws:
        assert authed.post("/api/payouts/check").json()["created"]
        events = set()
        for _ in range(10):
            events.add(ws.receive_json()["event"])
            if {"payout.ready", "notification"} <= events:
                break
    assert {"payout.ready", "notification"} <= events


# ---------- journal ----------
def test_journal_filters_and_csv(authed, clock):
    aid = authed.post("/api/accounts", json={"label": "E1", "stage": "EVAL"}).json()["id"]
    now = clock.now()
    with authed.app.state.sessionmaker() as s:
        for i, (sym, d, pnl) in enumerate([("MNQ", "LONG", 50), ("MGC", "SHORT", -30), ("MNQ", "SHORT", None)]):
            s.add(Trade(account_id=aid, symbol=sym, direction=d, qty=1, entry=D(1), risk_usd=D(70),
                        pnl_usd=D(pnl) if pnl is not None else None, opened_at=now,
                        closed_at=now if pnl is not None else None, trade_ref=f"J{i}",
                        exit_reason="TP" if pnl and pnl > 0 else None))  # fmt: skip
        s.commit()
    j = authed.get("/api/journal").json()
    assert j["summary"] == {"count": 3, "closed": 2, "wins": 1, "net_pnl": "20"} and j["symbols"] == ["MGC", "MNQ"]
    assert len(authed.get("/api/journal?symbol=MNQ").json()["trades"]) == 2
    assert len(authed.get("/api/journal?direction=SHORT").json()["trades"]) == 2
    assert len(authed.get("/api/journal?result=win").json()["trades"]) == 1
    assert len(authed.get("/api/journal?result=loss").json()["trades"]) == 1
    assert len(authed.get("/api/journal?result=open").json()["trades"]) == 1
    assert len(authed.get(f"/api/journal?q=TP&account_id={aid}").json()["trades"]) == 1
    d = now.date()
    assert len(authed.get(f"/api/journal?since={d}&until={d}").json()["trades"]) == 3
    assert authed.get(f"/api/journal?until={d - timedelta(days=1)}").json()["trades"] == []
    csv = authed.get("/api/journal?format=csv")
    assert csv.headers["content-type"].startswith("text/csv")
    lines = csv.text.strip().splitlines()
    assert lines[0].startswith("id,account,stage,symbol") and len(lines) == 4
    assert authed.get("/api/journal?result=bogus").status_code == 422


# ---------- inactivity + day lock-in ----------
def test_inactivity_job_notifies_once_per_session(authed, clock):
    from app.main import _inactivity

    aid = authed.post("/api/accounts", json={"label": "Idle", "stage": "EVAL"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        s.get(Account, aid).last_trade_at = clock.now() - timedelta(days=40)
        s.commit()
    ctl = authed.app.state.controller

    async def run():
        with authed.app.state.sessionmaker() as s:
            await _inactivity(authed.app, s, clock.now())
            await _inactivity(authed.app, s, clock.now())

    authed.portal.call(run)
    assert [n["title"] for n in ctl.notices].count("Inactivity alert") == 1
    r = _wait_notifications(authed)
    assert r["notifications"][0]["kind"] == "inactivity"
