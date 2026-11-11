"""Same signal → full paper trade on EVAL, FUNDED and LIVE stage accounts (standard + Evaluation Mode; D43)."""

from decimal import Decimal as D

import pytest

import app.signals.service as svc
from app.models import BiasDecision, Signal
from tests.integration.test_signals_flow import AT, MIN, MS, choch, confirm, hb


@pytest.fixture
def proven(monkeypatch):
    """Pretend the 1:1 filters' history is proven (E2 T1 rate 70% over 50 models, E-ATR mid-range)."""
    monkeypatch.setattr(svc, "t1_rate", lambda h, c1: (D("0.70"), 50))
    monkeypatch.setattr(svc, "atr_percentile", lambda h, v: (D(50), 300))


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
    _, res = run(authed, clock, stage)
    if stage == "FUNDED":  # intraday → drawdown guard needs 2 contracts; $1,000 risk base can't fit this stop
        assert res[0]["reason"] == "STOP_TOO_WIDE", res
        return
    assert res[0]["ok"] and res[0]["contracts"] >= 1, (stage, res)
    hb(authed, clock, MS - MIN, close="20071")
    t = authed.get("/api/trades").json()["trades"][0]
    assert t["exit_reason"] == "TP" and float(t["pnl"]) > 0, (stage, t)


@pytest.mark.parametrize("key", ["one_to_one_mode.enabled", "scalp_mode.enabled", "eval_mode.one_to_one"])
def test_scalp_and_1to1_retired(authed, key):
    """D43: Scalp and 1:1 can no longer be switched on from the settings API."""
    r = authed.put("/api/risk/settings", json={"changes": {key: True}})
    assert r.status_code >= 400 and "not editable" in r.text, r.text


def test_retired_modes_forced_off_even_if_stored(authed):
    """D43: an older stored setting (or a plan file) with Scalp/1:1 ON is ignored — the holder forces them OFF."""
    from app.risk.low_risk import retire_short_modes

    h = authed.app.state.rules
    on = h.rules.model_copy(
        update={
            "one_to_one_mode": h.rules.one_to_one_mode.model_copy(update={"enabled": True}),
            "scalp_mode": h.rules.scalp_mode.model_copy(update={"enabled": True}),
            "eval_mode": h.rules.eval_mode.model_copy(update={"one_to_one": True}),
        }
    )
    off = retire_short_modes(on)
    assert not off.one_to_one_mode.enabled and not off.scalp_mode.enabled and not off.eval_mode.one_to_one
    assert not h.rules.one_to_one_mode.enabled and not h.rules.scalp_mode.enabled


def test_drawdown_toggle(authed):
    e = authed.post("/api/accounts", json={"label": "E", "stage": "EVAL"}).json()["id"]
    f = authed.post("/api/accounts", json={"label": "F", "stage": "FUNDED"}).json()["id"]
    dd = {a["id"]: a["drawdown_type"] for a in authed.get("/api/accounts").json()["accounts"]}
    assert dd == {e: "eod", f: "intraday"}  # stage defaults (funded = intraday, D20)
    assert authed.patch(f"/api/accounts/{e}", json={"drawdown_type": "intraday"}).status_code == 200
    assert authed.patch(f"/api/accounts/{f}", json={"drawdown_type": "eod"}).status_code == 200  # user's choice
    acc = {a["id"]: a for a in authed.get("/api/accounts").json()["accounts"]}
    assert acc[e]["drawdown_type"] == "intraday" and acc[f]["drawdown_type"] == "eod"
    assert "normally use EOD" in acc[e]["drawdown_check"] and "normally use INTRADAY" in acc[f]["drawdown_check"]
    authed.patch(f"/api/accounts/{e}", json={"drawdown_type": "eod"})
    assert authed.get("/api/accounts").json()["accounts"][0]["drawdown_check"] is None


def test_real_account_never_trades_without_live(authed):
    r = authed.post("/api/accounts", json={"label": "L1", "stage": "EVAL", "tradovate_account": "lt25k1"}).json()
    assert r == {"id": r["id"], "broker_account_id": "LT25K1", "paper": False}
    assert authed.post("/api/accounts", json={"label": "L2", "tradovate_account": "LT25K1"}).status_code == 409
    ad = authed.app.state.controller.adapter
    assert "LT25K1" not in ad.sim.accounts and ad.live is None  # no live broker attached → unreachable
    assert not authed.app.state.controller.adapter.live_ok()


def test_payout_countdown_on_funded_and_live(authed, clock):
    clock.set(AT)
    for st in ("EVAL", "FUNDED", "LIVE"):
        authed.post("/api/accounts", json={"label": st, "stage": st})
    p = {x["label"]: x["payout"] for x in authed.get("/api/positions").json()["accounts"]}
    assert p["EVAL"] is None
    f = p["FUNDED"]
    assert f["seconds_left"] > 0 and f["needed"] == "1600" and f["live_trigger_left"] == "6000" and not f["pending"]
    assert p["LIVE"]["needed"] is None and p["LIVE"]["live_trigger_left"] is None


def test_dashboard_and_today(authed, clock):
    run(authed, clock, "EVAL")
    d = authed.get("/api/dashboard").json()
    a = d["accounts"][0]
    assert d["bias"]["MNQ"] == "LONG_ONLY" and a["trades_today"] == 1
    assert a["dll_left"] == "600.00" or float(a["dll_left"]) <= 600
    assert a["consistency_cap"] == "500.00" and a["target_left"] == "1250"
    assert a["max_loss"] == "1000" and a["dll_limit"] == "600"
    assert a["guard_on"] is False and a["eval_mode_on"] is False  # EVAL is EOD → guard OFF (§8)
    assert a["day_lockin"] is (float(a["day_net_r"]) >= float(a["day_lockin_r"]))
    t = authed.get("/api/today").json()
    assert t["signals"][0]["status"] == "PASS" and len(t["trades"]) == 1


def test_strategy_overview(authed, clock):
    run(authed, clock, "EVAL")
    r = authed.get("/api/strategy").json()
    mnq = next(i for i in r["instruments"] if i["symbol"] == "MNQ")
    assert mnq["bias"] == "LONG_ONLY" and mnq["proxy"] == "QQQ" and mnq["feeds"][0]["profile"] == "TIGHT"
    assert "gates" not in r and "last_signal" not in r  # D105: the LunqFX gate panel is gone


@pytest.mark.parametrize(
    ("stage", "offset_min", "flat"),
    [("EVAL", -2, True), ("LIVE", 1, True), ("EVAL", 1, True), ("EVAL", 3, False), ("EVAL", -5, False)],
)
def test_news_flatten(authed, clock, stage, offset_min, flat):
    """Flat 2 min before high-impact news (offset −2 = event 2 min ahead). Hard-breach stages stay flat until 1 min
    after (LIVE here; FUNDED behaves the same but its guard needs 2 contracts on this small paper account)."""
    import asyncio
    from datetime import timedelta

    from app.engine.filters import NewsEvent

    _, res = run(authed, clock, stage)
    assert res[0]["ok"], res
    ev = NewsEvent(at=clock.now() - timedelta(minutes=offset_min), title="CPI")
    got = asyncio.run(authed.app.state.controller.news_check([ev]))
    assert (got == "NEWS") is flat
    assert (authed.get("/api/positions").json()["accounts"][0]["positions"] == []) is flat


def test_eod_update_trails_mll_on_eod_accounts_only(authed, clock):
    import asyncio

    e = authed.post("/api/accounts", json={"label": "E", "stage": "EVAL", "balance": "25400"}).json()["id"]
    i = authed.post("/api/accounts", json={"label": "I", "stage": "EVAL", "drawdown_type": "intraday"}).json()["id"]
    with authed.app.state.sessionmaker() as s:
        from app.models import Account

        for a in s.query(Account):  # both created with start-balance MLL; pretend they started at 25,000
            a.mll, a.mll_peak = D(24000), D(25000)
        s.commit()
    assert asyncio.run(authed.app.state.controller.eod_all()) == 1
    acc = {a["id"]: a for a in authed.get("/api/dashboard").json()["accounts"]}
    assert acc[e]["mll"] == "24400" and acc[i]["mll"] == "24000"


def test_lucid_account_limits(authed):
    for i in range(5):
        r = authed.post("/api/accounts", json={"label": f"F{i}", "stage": "FUNDED", "tradovate_account": f"LT{i}"})
        assert r.status_code == 200, r.text
    r = authed.post("/api/accounts", json={"label": "F6", "stage": "FUNDED", "tradovate_account": "LT6"})
    assert r.status_code == 409 and "5 funded" in r.text
    for i in range(5):
        authed.post("/api/accounts", json={"label": f"E{i}", "stage": "EVAL", "tradovate_account": f"LE{i}"})
    r = authed.post("/api/accounts", json={"label": "E9", "stage": "EVAL", "tradovate_account": "LE9"})
    assert r.status_code == 409 and "at most 10" in r.text
    assert authed.post("/api/accounts", json={"label": "paper", "stage": "EVAL"}).status_code == 200  # paper unlimited
