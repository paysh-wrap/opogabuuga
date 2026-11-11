"""D95 Order Flow button: ORDER_FLOW webhook alert → paper-only strategy signal (UNVERIFIED)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal as D

from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import Account, AuditLog, Signal, TradePlanRow
from app.signals import strategy_service as SS
from app.webhook.schemas import WebhookPayload
from tests.conftest import WEBHOOK_SECRET

AT = datetime(2026, 10, 12, 14, 0, tzinfo=UTC)  # Monday 10:00 ET
MS = int(AT.timestamp() * 1000)


def _rules(loaded_rules, **strategy):
    r = loaded_rules.rules
    mnq = r.instruments["MNQ"].model_copy(update={"enabled": True, "windows": [("09:30", "16:00")]})
    st = r.strategy.model_copy(update={"lunqfx": False, "order_flow": True, **strategy})
    return r.model_copy(update={"strategy": st, "instruments": {**r.instruments, "MNQ": mnq}})


def _p(ms=MS, direction="LONG", entry="20010", defended="20000", stop="19999.75", kind="ABSORPTION"):
    return {
        "v": 1, "secret": WEBHOOK_SECRET, "id": f"MNQ1!-TIGHT-{ms}-ORDER_FLOW-{direction}", "symbol": "MNQ1!",
        "profile": "TIGHT", "tf": "1", "bar_time_ms": ms, "event": "ORDER_FLOW", "direction": direction,
        "order_flow": {"kind": kind, "entry": entry, "defended": defended, "stop": stop, "target": "20030.5", **AR, "confirm_time": ms - 60000},
    }  # fmt: skip


# D101: an alert whose four AR-Model layers agree (LONG: discount below value, inside Asia, confirmed 1 bar earlier)
AR = {
    "env": "ROTATION", "location_zone": "F0788", "fib": "0.79", "value_side": "BELOW_VAL", "path_zone": "INSIDE",
    "path_side": "INSIDE", "delta_source": "real",
}  # fmt: skip


def _run(s, rules, p, cal=lambda _d: []):
    return SS.run_order_flow(
        s, rules=rules, clock=FixedClock(AT), calendar=cal, symbol="MNQ", payload=WebhookPayload.model_validate(p)
    )


def test_signal_plan_gates_and_skips(client, loaded_rules):
    rules = _rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        assert _run(s, _rules(loaded_rules, order_flow=False), _p()).updates == []  # button off (default)
        out = _run(s, rules, _p())
        assert len(out.updates) == 1 and out.updates[0].status == "PASS"
        sig = s.get(Signal, out.updates[0].signal_id)
        assert sig.features["strategy"] == "ORDER_FLOW" and sig.features["paper_only"] is True
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        assert (plan.mode, plan.stop, plan.take_profit, plan.rr) == ("ORDER_FLOW", D("19999.75"), D("20030.5"), 2)
        assert _run(s, rules, _p()).updates == []  # same alert twice
        nxt = _run(s, rules, _p(ms=MS + 60000)).updates[0]
        assert (nxt.status, nxt.reason) == ("SKIP", "OF_POSITION_OPEN")
        # engine skip: no signal row, reason audited
        assert _run(s, rules, _p(ms=MS + 120000, defended="20020", stop=None)).updates == []
        assert s.query(AuditLog).filter_by(action="order_flow.skip").count() >= 1


def test_hedge_lock_daily_cap_and_window(client, loaded_rules):
    rules = _rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        plan = ("NOISE", D(20000), D(20050), D(19900), D(50), D(2))
        SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key="MNQ-NOISE-2026-10-12", direction=Direction.SHORT, at=AT,
            gate=(True, "OK", ""), features={}, plan=plan,
        )  # fmt: skip
        s.commit()
        u = _run(s, rules, _p()).updates[0]
        assert (u.status, u.reason) == ("SKIP", "HEDGE_LOCK")
    with client.app.state.sessionmaker() as s:
        s.query(Signal).filter(Signal.model_key.like("MNQ-NOISE%")).one().features = {"state": "CLOSED"}
        s.commit()
        cap = _rules(loaded_rules)
        cap = cap.model_copy(
            update={
                "strategy": cap.strategy.model_copy(
                    update={"order_flow_cfg": cap.strategy.order_flow_cfg.model_copy(update={"max_per_day": 1})}
                )
            }
        )
        assert _run(s, cap, _p(ms=MS + 180000)).updates[0].status == "PASS"
        for x in s.query(Signal).filter(Signal.model_key.like("MNQ-OF%")):
            x.features = {**x.features, "state": "CLOSED"}
        s.commit()
        u = _run(s, cap, _p(ms=MS + 240000)).updates[0]
        assert (u.status, u.reason) == ("SKIP", "OF_DAILY_CAP")
        late = int(datetime(2026, 10, 12, 21, 0, tzinfo=UTC).timestamp() * 1000)  # 17:00 ET
        u = _run(s, rules, _p(ms=late)).updates[0]
        assert (u.status, u.reason) == ("SKIP", "OUTSIDE_WINDOW")


def test_webhook_accepts_order_flow_and_rejects_incomplete(client, clock):
    clock.set(AT)
    r = client.post("/api/webhook/tradingview", content=json.dumps(_p()))
    assert r.status_code == 200, r.text
    bad = {**_p(ms=MS + 60000), "order_flow": None}
    r = client.post("/api/webhook/tradingview", content=json.dumps(bad))
    assert r.status_code == 422 and r.json()["code"] == "BAD_PAYLOAD"


def test_order_flow_never_executes_on_a_non_paper_account(authed, clock):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "P", "stage": "EVAL", "balance": "25000"}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    with st.sessionmaker() as s:
        s.get(Account, aid).is_sim = False
        plan = ("ORDER_FLOW", D(20010), D("19999.75"), D("20030.5"), D("10.25"), D(2))
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key="MNQ-OF-2026-10-12-1-LONG", direction=Direction.LONG, at=AT,
            gate=(True, "OK", ""), features={}, plan=plan,
        )  # fmt: skip
        s.commit()
        sid = sig.id
    res = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    assert res[0].ok is False and res[0].reason == "PAPER_ONLY_STRATEGY", res


# ---------- D96: MGC on for Order Flow ONLY (plan file strategy.order_flow_cfg.instruments) ----------


def _mgc_rules(loaded_rules, instruments=("MNQ", "MGC"), **strategy):
    r = _rules(loaded_rules, **strategy)
    cfg = r.strategy.order_flow_cfg.model_copy(update={"instruments": list(instruments)})
    return r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow_cfg": cfg})})


def _pm(ms=MS, direction="LONG", entry="2650.0", defended="2648.0", stop="2647.9"):
    p = _p(ms=ms, direction=direction, entry=entry, defended=defended, stop=stop)
    p["order_flow"]["target"] = "2654.2"
    return {**p, "id": f"MGC1!-TIGHT-{ms}-ORDER_FLOW-{direction}", "symbol": "MGC1!"}


def _run_mgc(s, rules, p, at=AT):
    return SS.run_order_flow(
        s, rules=rules, clock=FixedClock(at), calendar=lambda _d: [], symbol="MGC",
        payload=WebhookPayload.model_validate(p),
    )  # fmt: skip


def test_mgc_trades_for_order_flow_only_with_config_ticks(client, loaded_rules):
    rules = _mgc_rules(loaded_rules)
    assert rules.instruments["MGC"].enabled is False  # the global gold switch stays OFF
    with client.app.state.sessionmaker() as s:
        assert _run_mgc(s, _mgc_rules(loaded_rules, instruments=("MNQ",)), _pm()).updates == []  # not in the list
        assert _run_mgc(s, _mgc_rules(loaded_rules, order_flow=False), _pm()).updates == []  # button off
        u = _run_mgc(s, rules, _pm()).updates[0]
        assert u.status == "PASS", u
        sig = s.get(Signal, u.signal_id)
        assert sig.symbol == "MGC" and sig.model_key.startswith("MGC-OF-2026-10-12-")
        plan = s.query(TradePlanRow).filter_by(signal_id=sig.id).one()
        # MGC tick 0.10 from the instrument config: stop 1 tick beyond 2648.0, 2R target
        assert (plan.stop, plan.take_profit, plan.rr) == (D("2647.9"), D("2654.2"), 2)
        # the market's own min_stop_ticks (MGC 16) tightens the order-flow floor (8): 11 ticks → skipped
        assert _run_mgc(s, rules, _pm(ms=MS + 60000, defended="2649.0", stop=None)).updates == []
        row = s.query(AuditLog).filter_by(action="order_flow.skip").order_by(AuditLog.id.desc()).first()
        assert row.payload["code"] == "STOP_TOO_TIGHT"
    # every other strategy keeps MGC off: the shared G1 gate without the Order Flow override refuses it
    assert SS._gate(rules, "MGC", AT, lambda _d: [])[1] == "INSTRUMENT_DISABLED"
    assert SS._gate(rules, "MGC", AT, lambda _d: [], enabled=True)[0] is True
    assert rules.super_group_of("MGC") == "METALS"


def test_mgc_hedge_lock_and_news(client, loaded_rules):
    rules = _mgc_rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        plan = ("AI_DUO", D(2650), D(2655), D(2640), D(5), D(2))
        SS._new_signal(
            s, FixedClock(AT), symbol="MGC", key="MGC-DUO-2026-10-12", direction=Direction.SHORT, at=AT,
            gate=(True, "OK", ""), features={}, plan=plan,
        )  # fmt: skip
        s.commit()
        u = _run_mgc(s, rules, _pm()).updates[0]
        assert (u.status, u.reason) == ("SKIP", "HEDGE_LOCK")
        assert _run_mgc(s, rules, _pm(ms=MS + 60000)).updates[0].reason == "HEDGE_LOCK"
        none = SS.run_order_flow(
            s, rules=rules, clock=FixedClock(AT), calendar=lambda _d: None, symbol="MGC",
            payload=WebhookPayload.model_validate(_pm(ms=MS + 120000, direction="SHORT", entry="2650.0",
                                                      defended="2652.0", stop="2652.1")),
        )  # fmt: skip
        assert none.updates[0].reason == "CALENDAR_MISSING"


def test_order_flow_flat_at_1600(client, loaded_rules):
    rules = _mgc_rules(loaded_rules)
    with client.app.state.sessionmaker() as s:
        plan = ("ORDER_FLOW", D(2650), D("2647.9"), D("2654.2"), D("2.1"), D(2))
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MGC", key="MGC-OF-2026-10-12-1-LONG", direction=Direction.LONG, at=AT,
            gate=(True, "OK", ""), features={}, plan=plan,
        )  # fmt: skip
        s.commit()
        before = datetime(2026, 10, 12, 19, 59, tzinfo=UTC)  # 15:59 ET
        flat = datetime(2026, 10, 12, 20, 0, tzinfo=UTC)  # 16:00 ET
        assert SS.order_flow_exits(s, rules, FixedClock(before), "MGC", before).exits == []
        assert (
            SS.order_flow_exits(s, _mgc_rules(loaded_rules, instruments=("MNQ",)), FixedClock(flat), "MGC", flat).exits
            == []
        )
        off = _mgc_rules(loaded_rules, order_flow=False)  # protective: still flattens with the button off
        out = SS.run(s, rules=off, clock=FixedClock(flat), calendar=lambda _d: [], symbol="MGC", tf="1", at=flat)
        assert out.exits == [(sig.id, "OF_FLAT_1600")]
        s.refresh(sig)
        assert sig.features["state"] == "CLOSED" and sig.features["exit_reason"] == "OF_FLAT_1600"
        assert SS.order_flow_exits(s, rules, FixedClock(flat), "MGC", flat).exits == []  # once per signal


def test_webhook_maps_mgc1_and_plan_files(client, clock):
    clock.set(AT)
    r = client.post("/api/webhook/tradingview", content=json.dumps(_pm()))
    assert r.status_code == 200, r.text
    from pathlib import Path

    from app.config import load_rules

    for p in sorted((Path(__file__).resolve().parents[3] / "config" / "rules").glob("lucid_*.yaml")):
        lr = load_rules(p).rules
        assert lr.instruments["MGC"].enabled is False, p.name  # MGC stays off for every other strategy (D55)
        assert lr.strategy.order_flow is False and lr.strategy.order_flow_cfg.paper_only, p.name  # default OFF
        want = ["MNQ"] if "daily" in p.name else ["MNQ", "MGC"]
        assert lr.strategy.order_flow_cfg.instruments == want, p.name


def test_strategies_card_lists_order_flow_markets(authed):
    d = authed.get("/api/strategies").json()
    of = next(x for x in d["strategies"] if x["key"] == "order_flow")
    assert of["instruments"] == ["MNQ"] and of["paper_only"] is True and of["flat_at"] == "16:00"
    assert "MNQ + MGC" in of["name"]
    assert "instruments" not in next(x for x in d["strategies"] if x["key"] == "noise")
