"""Same signal → full paper trade on EVAL, FUNDED and LIVE stage accounts (standard, 1:1, Evaluation Mode)."""

from decimal import Decimal as D

import pytest

import app.signals.service as svc


@pytest.fixture
def proven(monkeypatch):
    """Pretend the 1:1 filters' history is proven (E2 T1 rate 70% over 50 models, E-ATR mid-range)."""
    monkeypatch.setattr(svc, "t1_rate", lambda h, c1: (D("0.70"), 50))
    monkeypatch.setattr(svc, "atr_percentile", lambda h, v: (D(50), 300))


from app.models import BiasDecision, Signal
from tests.integration.test_signals_flow import AT, MIN, MS, choch, confirm, hb


def run(authed, clock, stage, changes=None, eval_on=False):
    authed.app.state.calendar = lambda d: []
    with authed.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    clock.set(AT)
    if changes:
        assert authed.put("/api/risk/settings", json={"changes": changes}).status_code == 200
    aid = authed.post("/api/accounts", json={"label": stage, "stage": stage}).json()["id"]
    if eval_on:
        r = authed.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"})
        assert r.status_code == 200, r.text
    assert authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True}).status_code == 200
    authed.post("/api/attestation", json={"confirm": True})
    authed.app.state.controller.mode = "SEMI"
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
    assert sig.status == "PASS", sig.skip_reason
    res = authed.post(f"/api/signals/{sig.id}/execute", json={}).json()["results"]
    return aid, res


@pytest.mark.parametrize("stage", ["EVAL", "FUNDED", "LIVE"])
def test_standard_trade_every_stage(authed, clock, stage):
    aid, res = run(authed, clock, stage)
    assert res[0]["ok"] and res[0]["contracts"] >= 1, (stage, res)
    hb(authed, clock, MS - MIN, close="20071")
    t = authed.get("/api/trades").json()["trades"][0]
    assert t["exit_reason"] == "TP" and float(t["pnl"]) > 0, (stage, t)


@pytest.mark.parametrize("stage", ["EVAL", "FUNDED", "LIVE"])
def test_one_to_one_every_stage(authed, clock, stage, proven):
    _, res = run(authed, clock, stage, {"one_to_one_mode.enabled": True})
    assert res[0]["ok"], (stage, res)
    hb(authed, clock, MS - MIN, close="20031")
    t = authed.get("/api/trades").json()["trades"][0]
    assert t["exit_reason"] == "TP" and 0 < float(t["net_r"]) <= 1.05, (stage, t)  # 1:1 caps at ~1R


def test_eval_mode_with_1to1_option_only_on_eval(authed, clock, proven):
    _, res = run(authed, clock, "EVAL", {"eval_mode.one_to_one": True}, eval_on=True)
    assert res[0]["ok"], res
    hb(authed, clock, MS - MIN, close="20031")
    t = authed.get("/api/trades").json()["trades"][0]
    assert float(t["net_r"]) <= 1.05, t


def test_eval_1to1_option_ignored_on_funded(authed, clock):
    _, res = run(authed, clock, "FUNDED", {"eval_mode.one_to_one": True})
    assert res[0]["ok"], res
    hb(authed, clock, MS - MIN, close="20071")
    t = authed.get("/api/trades").json()["trades"][0]
    assert float(t["net_r"]) > 1.5, t  # standard 2R plan


def test_one_to_one_refuses_unproven_history(authed, clock):
    """Safety: without 30 resolved models proving T1 ≥ 65%, 1:1 does not trade (E2)."""
    authed.app.state.calendar = lambda d: []
    clock.set(AT)
    authed.put("/api/risk/settings", json={"changes": {"one_to_one_mode.enabled": True}})
    with authed.app.state.sessionmaker() as s:
        s.add(BiasDecision(session_date=AT.date(), proxy="QQQ", raw_rating="Buy", mapped="LONG_ONLY", version="x"))
        s.commit()
    choch(authed, clock)
    hb(authed, clock, MS - 2 * MIN, close="20005")
    confirm(authed, clock)
    with authed.app.state.sessionmaker() as s:
        assert s.query(Signal).one().skip_reason == "1TO1_T1_RATE_UNPROVEN"
