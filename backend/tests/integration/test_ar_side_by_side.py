"""D160: AR Model beside NOISE (option default OFF), pre-session TradingAgents runs, NO_CALL, card data."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.bias import ar_pre_session as ARP
from app.bias.tradingagents_adapter import RunnerResult
from app.clock import FixedClock
from app.engine.trade_plan import Direction
from app.models import AuditLog, BiasDecision
from app.signals import strategy_service as SS
from tests.integration.test_bias_job import FakeTA, save_creds
from tests.integration.test_order_flow import AT, _rules


def _on(st, **cfg):
    st.rules.rules = _rules(st.rules)
    of = st.rules.rules.strategy.order_flow_cfg.model_copy(update=cfg)
    r = st.rules.rules
    st.rules.rules = r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow_cfg": of})})


def _accounts(authed, clock, n=2):
    clock.set(AT)
    ids = []
    for i in range(n):
        aid = authed.post("/api/accounts", json={"label": f"A{i}", "stage": "EVAL", "balance": "25000"}).json()["id"]
        authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
        ids.append(aid)
    authed.post("/api/attestation", json={"confirm": True})
    authed.app.state.controller.mode = "FULL"
    return ids


def _signal(st, n, direction="LONG", features=None):
    long_ = direction == "LONG"
    plan = ("ORDER_FLOW", D(20010), D("19999.75") if long_ else D("20020.25"), D("20030.5") if long_ else D("19989.5"),
            D("10.25"), D(2))  # fmt: skip
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-OF-2026-10-12-{n}-{direction}",
            direction=Direction.LONG if long_ else Direction.SHORT, at=AT, gate=(True, "OK", ""),
            features=features or {}, plan=plan,
        )  # fmt: skip
        s.commit()
        return sig.id


def _traded(res):
    return [r.account_id for r in res if r.ok]


def test_off_is_unchanged_every_selected_account_is_tried(authed, clock):
    st = authed.app.state
    ids = _accounts(authed, clock)
    _on(st)
    assert st.rules.rules.strategy.order_flow_cfg.ar_side_by_side is False
    res = asyncio.run(st.controller.execute(_signal(st, 1), "automation", only=ids))
    assert {r.account_id for r in res} == set(ids)


def test_on_second_signal_goes_to_free_account_never_the_busy_one(authed, clock):
    st = authed.app.state
    ids = _accounts(authed, clock)
    _on(st, ar_side_by_side=True)
    first = _traded(asyncio.run(st.controller.execute(_signal(st, 1), "automation", only=ids)))
    assert len(first) == 1  # one free account per trade, never copy trading
    second = asyncio.run(st.controller.execute(_signal(st, 2), "automation", only=ids))
    assert [r.account_id for r in second] == [i for i in ids if i != first[0]]  # only the free account is tried
    third = asyncio.run(st.controller.execute(_signal(st, 3), "automation", only=ids))
    assert third == [] or all(not r.ok for r in third)  # both busy: never a second position on one account


def test_on_opposite_direction_is_skipped_by_hedge_lock(authed, clock):
    st = authed.app.state
    ids = _accounts(authed, clock)
    _on(st, ar_side_by_side=True)
    assert len(_traded(asyncio.run(st.controller.execute(_signal(st, 1), "automation", only=ids)))) == 1
    res = asyncio.run(st.controller.execute(_signal(st, 2, "SHORT"), "automation", only=ids))
    assert not any(r.ok for r in res) and any("HEDGE" in (r.reason or "") for r in res), res


def test_zone_signals_keep_todays_routing(authed, clock):
    st = authed.app.state
    ids = _accounts(authed, clock)
    _on(st, ar_side_by_side=True)
    res = asyncio.run(st.controller.execute(_signal(st, 1, features={"zone": {}}), "automation", only=ids))
    assert {r.account_id for r in res} == set(ids)


# ---------- pre-session runs ----------

MON = datetime(2026, 10, 12, tzinfo=UTC)


def _et(h, m):  # Monday 2026-10-12 is EDT (UTC-4)
    return MON.replace(hour=h + 4, minute=m)


def test_run_times_and_due(loaded_rules):
    r = _rules(loaded_rules)
    assert not ARP.enabled(r)  # default OFF
    r = r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow_cfg": r.strategy.order_flow_cfg.model_copy(update={"ar_side_by_side": True})})})
    assert ARP.enabled(r)
    assert ARP.run_times(r) == [(240, "05:30"), (60, "08:30"), (30, "09:00")]  # session start 09:30 (test window)
    d = MON.date()
    assert ARP.due(_et(5, 30), r, 240, None, d) and not ARP.due(_et(5, 29), r, 240, None, d)
    assert not ARP.due(_et(5, 31), r, 240, d.isoformat(), d)  # once per session and run
    assert not ARP.due(_et(9, 31), r, 30, None, d)  # never after the session start
    assert not ARP.due(_et(9, 0), r, 45, None, d)  # unknown run
    off = r.model_copy(update={"strategy": r.strategy.model_copy(update={"advisor": r.strategy.advisor.model_copy(update={"mode": "OFF"})})})
    assert not ARP.enabled(off)


def test_plan_files_carry_the_runs(loaded_rules):
    assert loaded_rules.rules.strategy.advisor.pre_session_runs_min == [240, 60, 30]


def test_validator_rejects_bad_runs():
    from app.config import AdvisorCfg

    for bad in ([60, 60], [2], [700]):
        with pytest.raises(ValueError):
            AdvisorCfg(pre_session_runs_min=bad)


def test_scheduler_runs_three_times_stores_probabilities_and_card(authed, clock):
    from app.main import _ar_pre_session

    st = authed.app.state
    st.rules.rules = _rules(st.rules)
    ta = FakeTA({"QQQ": RunnerResult(True, {"rating": "Sell", "decision": "x", "version": "0.7.1"})})
    st.ta = ta
    save_creds(authed)
    for t in (_et(5, 30), _et(8, 30), _et(9, 0)):
        clock.set(t)
        with st.sessionmaker() as s:
            asyncio.run(_ar_pre_session(authed.app, s, clock.now()))  # option OFF → nothing
    assert ta.calls == []
    _on(st, ar_side_by_side=True)
    for t in (_et(5, 30), _et(8, 30), _et(9, 0), _et(9, 0)):
        clock.set(t)
        with st.sessionmaker() as s:
            asyncio.run(_ar_pre_session(authed.app, s, clock.now()))
    assert ta.calls == ["QQQ"] * 3  # re-runs even though the day already has a call
    with st.sessionmaker() as s:
        assert s.query(BiasDecision).count() == 3
        rows = s.query(AuditLog).filter_by(action=ARP.ACTION).all()
        assert len(rows) == 3 and all(x.payload["status"] == "OK" and x.payload["side"] == "SHORT" for x in rows)
        assert all(0 < x.payload["prob_down"] < 1 and x.payload["prob_up"] < 0.5 for x in rows)
    card = next(c for c in authed.get("/api/strategies").json()["strategies"] if c["key"] == "order_flow")["ar_side_by_side"]
    assert card["enabled"] is True and card["data_source"] == "ESTIMATED delta (online data)" and card["verified"] is False
    assert [r["minutes_before"] for r in card["runs"]] == [240, 60, 30]
    assert card["runs"][0]["results"][0]["status"] == "OK" and "session22" in card["evidence"]
    assert card["setting"] == "strategy.order_flow_cfg.ar_side_by_side"


def test_no_key_records_no_call(authed, clock):
    from app.main import _ar_pre_session

    st = authed.app.state
    _on(st, ar_side_by_side=True)
    clock.set(_et(8, 30))
    with st.sessionmaker() as s:
        asyncio.run(_ar_pre_session(authed.app, s, clock.now()))
        row = s.query(AuditLog).filter_by(action=ARP.ACTION).one()
        assert row.payload["status"] == "NO_CALL" and row.payload["reason"] == "AI key not connected"
    card = next(c for c in authed.get("/api/strategies").json()["strategies"] if c["key"] == "order_flow")["ar_side_by_side"]
    assert card["runs"][1]["results"][0]["reason"] == "AI key not connected" and card["runs"][0]["results"][0]["status"] == "PENDING"


def test_crash_is_no_call_and_notifies(authed, clock, monkeypatch):
    from app.bias import service as bias
    from app.main import _ar_pre_session

    st = authed.app.state
    _on(st, ar_side_by_side=True)

    async def boom(*_a, **_k):
        raise RuntimeError("x")

    monkeypatch.setattr(bias, "run_bias", boom)
    clock.set(_et(8, 30))
    with st.sessionmaker() as s:
        asyncio.run(_ar_pre_session(authed.app, s, clock.now()))
        p = s.query(AuditLog).filter_by(action=ARP.ACTION).one().payload
        assert p["status"] == "NO_CALL" and "run failed" in p["reason"]
    assert st.controller.notices[-1]["title"].startswith("AR pre-session")


def test_failed_rerun_keeps_the_days_good_call(authed, clock):
    from app.main import _ar_pre_session

    st = authed.app.state
    _on(st, ar_side_by_side=True)
    save_creds(authed)
    ta = FakeTA({"QQQ": RunnerResult(True, {"rating": "Buy", "decision": "x", "version": "0.7.1"})})
    st.ta = ta
    clock.set(_et(5, 30))
    with st.sessionmaker() as s:
        asyncio.run(_ar_pre_session(authed.app, s, clock.now()))
    ta.results = {"QQQ": RunnerResult(False, {"error": "boom"})}
    clock.set(_et(8, 30))
    with st.sessionmaker() as s:
        asyncio.run(_ar_pre_session(authed.app, s, clock.now()))
        assert s.query(BiasDecision).count() == 1  # the failed re-run stored nothing
