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
from tests.integration.test_order_flow import _rules
from tests.integration.trade_helpers import AT, PLAN, _ext, _qty, _setup, _sig


def _on(st, **cfg):
    r = _rules(st.rules)
    of = r.strategy.order_flow_cfg.model_copy(update=cfg)
    st.rules.rules = r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow_cfg": of})})


def _traded(res):
    return [r.account_id for r in res if r.ok]


def _two(authed, clock, **cfg):
    st, ids = _setup(authed, clock, [("a", "25000"), ("b", "25000")], noise=True)
    _on(st, **cfg)
    r = st.rules.rules
    st.rules.rules = r.model_copy(update={"strategy": r.strategy.model_copy(update={"order_flow": True})})
    return st, ids


def test_off_is_unchanged_every_selected_account_is_tried(authed, clock):
    st, (a, b) = _two(authed, clock)
    assert st.rules.rules.strategy.order_flow_cfg.ar_side_by_side is False
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    res = asyncio.run(st.controller.execute(_sig(st, "ORDER_FLOW", "O1"), "automation", only=[a, b]))
    assert {r.account_id for r in res} == {a, b}  # today's routing; the busy account is stopped by the 1-position check
    assert next(r for r in res if r.account_id == a).ok is False


def test_on_ar_goes_to_a_free_account_never_the_noise_account(authed, clock):
    st, (a, b) = _two(authed, clock, ar_side_by_side=True)
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    res = asyncio.run(st.controller.execute(_sig(st, "ORDER_FLOW", "O1"), "automation", only=[a, b]))
    assert [r.account_id for r in res] == [b] and res[0].ok, res  # only the free account; never copy trading
    res = asyncio.run(st.controller.execute(_sig(st, "ORDER_FLOW", "O2"), "automation", only=[a, b]))
    assert not any(r.ok for r in res)  # both busy: never a second position on one account


def test_on_opposite_direction_is_skipped_by_hedge_lock(authed, clock):
    st, (a, b) = _two(authed, clock, ar_side_by_side=True)
    assert asyncio.run(st.controller.execute(_sig(st, "NOISE", "N1"), "automation", only=[a]))[0].ok
    short = (D(20000), D(20020), D(19900), D(20), D(5))
    res = asyncio.run(
        st.controller.execute(_sig(st, "ORDER_FLOW", "O1", Direction.SHORT, short), "automation", only=[a, b])
    )
    assert not any(r.ok for r in res) and any(r.reason == "HEDGE_LOCK" for r in res), res


def test_ar_size_is_capped_at_half_of_the_noise_fast_pass_size(authed, clock):
    from app.config import FastPassCfg

    st, (a, _b) = _two(authed, clock, ar_side_by_side=True, contracts=4)
    fp = FastPassCfg(
        account_size=D(25000), noise_contracts=2, noise_stop_usd=D(75), candace_contracts=2,
        brake_cushion_usd=D(333), brake_inclusive=False, candace_brake_contracts=1,
    )  # fmt: skip
    r = st.rules.rules
    st.rules.rules = r.model_copy(
        update={"strategy": r.strategy.model_copy(update={"fast_pass_25k": True, "fast_pass_25k_cfg": fp})}
    )
    res = asyncio.run(st.controller.execute(_sig(st, "ORDER_FLOW", "O1"), "automation", only=[a]))
    assert res[0].ok and _qty(st, _ext(st, a)) == 1  # half of NOISE's 2 micros


def test_zone_signals_keep_todays_routing(authed, clock):
    st, (a, b) = _two(authed, clock, ar_side_by_side=True)
    with st.sessionmaker() as s:
        sig = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key="Z1", direction=Direction.LONG, at=AT, gate=(True, "OK", ""),
            features={"zone": {}}, plan=("ORDER_FLOW", *PLAN),
        )  # fmt: skip
        s.commit()
        sid = sig.id
    res = asyncio.run(st.controller.execute(sid, "automation", only=[a, b]))
    assert {r.account_id for r in res} == {a, b}


# ---------- pre-session runs ----------

MON = datetime(2026, 10, 12, tzinfo=UTC)


def _et(h, m):  # Monday 2026-10-12 is EDT (UTC-4)
    return MON.replace(hour=h + 4, minute=m)


def test_run_times_and_due(loaded_rules):
    r = _rules(loaded_rules)
    assert not ARP.enabled(r)  # default OFF
    r = r.model_copy(
        update={
            "strategy": r.strategy.model_copy(
                update={"order_flow_cfg": r.strategy.order_flow_cfg.model_copy(update={"ar_side_by_side": True})}
            )
        }
    )
    assert ARP.enabled(r)
    assert ARP.run_times(r) == [(240, "05:30"), (60, "08:30"), (30, "09:00")]  # session start 09:30 (test window)
    d = MON.date()
    assert ARP.due(_et(5, 30), r, 240, None, d) and not ARP.due(_et(5, 29), r, 240, None, d)
    assert not ARP.due(_et(5, 31), r, 240, d.isoformat(), d)  # once per session and run
    assert not ARP.due(_et(9, 31), r, 30, None, d)  # never after the session start
    assert not ARP.due(_et(9, 0), r, 45, None, d)  # unknown run
    off = r.model_copy(
        update={
            "strategy": r.strategy.model_copy(update={"advisor": r.strategy.advisor.model_copy(update={"mode": "OFF"})})
        }
    )
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
    card = next(c for c in authed.get("/api/strategies").json()["strategies"] if c["key"] == "order_flow")[
        "ar_side_by_side"
    ]
    assert (
        card["enabled"] is True and card["data_source"] == "ESTIMATED delta (online data)" and card["verified"] is False
    )
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
    card = next(c for c in authed.get("/api/strategies").json()["strategies"] if c["key"] == "order_flow")[
        "ar_side_by_side"
    ]
    assert (
        card["runs"][1]["results"][0]["reason"] == "AI key not connected"
        and card["runs"][0]["results"][0]["status"] == "PENDING"
    )


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
