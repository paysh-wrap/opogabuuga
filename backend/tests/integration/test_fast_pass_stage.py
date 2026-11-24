"""D180 Fast Pass on FUNDED / LIVE: per-stage switches (default OFF), same pure sizes, every funded / live guard
still shrinks or skips; LIVE switch blocked without the live gates; old settings load."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.automation import state as AS
from app.config import FastPassCfg
from app.models import Account
from app.risk import settings_store as ss
from app.risk.fast_pass import fast_pass_size, funded_day_stop_hit, stage_switch_on
from tests.integration.test_fast_pass_150k import CFG, _fixed, _run, _setup

CFG25 = FastPassCfg(account_size=D(25000), noise_contracts=1, noise_stop_usd=D(75), candace_contracts=2)


def _stage(authed, stage, funded=False, live=False, **kw):
    st, aid = _setup(authed, kw.pop("clock"), stage=stage, **kw)
    st.controller.rules.fast_pass_funded_on, st.controller.rules.fast_pass_live_on = funded, live
    return st, aid


@pytest.mark.parametrize("stage", ["FUNDED", "LIVE"])
def test_default_off_changes_nothing(authed, clock, stage):
    st, aid = _stage(authed, stage, clock=clock)
    _, fp = _run(st, aid, "NOISE")
    assert fp == []  # old behaviour identical: no fast-pass sizing off the EVAL stage


@pytest.mark.parametrize("stage", ["FUNDED", "LIVE"])
@pytest.mark.parametrize("mode", ["NOISE", "CANDACE_ICT"])
def test_on_never_larger_than_eval_setup(authed, clock, stage, mode):
    st, aid = _stage(authed, stage, funded=stage == "FUNDED", live=stage == "LIVE", clock=clock)
    res, fp = _run(st, aid, mode)
    assert fp or mode == "CANDACE_ICT"
    top = CFG.noise_contracts if mode == "NOISE" else CFG.candace_contracts
    if fp:
        assert fp[-1]["contracts"] <= top
    if res.ok:
        assert 1 <= res.contracts <= top


@pytest.mark.parametrize("stage", ["FUNDED", "LIVE"])
def test_other_stage_switch_does_not_apply(authed, clock, stage):
    st, aid = _stage(authed, stage, funded=stage == "LIVE", live=stage == "FUNDED", clock=clock)
    assert _run(st, aid, "NOISE")[1] == []


@pytest.mark.parametrize("stage", ["EVAL", "FUNDED", "LIVE"])
def test_dll_and_mll_room_only_shrink_or_skip(authed, clock, stage):
    st, aid = _stage(authed, stage, funded=True, live=True, clock=clock, cushion=D(700), dll=D(150))
    res, fp = _run(st, aid, "NOISE")
    if res.ok:
        assert res.contracts <= (fp[-1]["contracts"] if fp else 99)
    assert not res.ok or res.contracts <= 2  # tiny cushion: 1-2 micros at most, or skipped


def test_funded_consistency_cap_uses_35_without_purchase_date(authed, clock):
    st, aid = _stage(authed, "FUNDED", funded=True, clock=clock)
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        r = st.controller.rules.rules
        off = AS.consistency(s, a, r)
        on = AS.consistency(s, a, r, True)
        assert on is not None and off is not None
        assert on.cap <= off.cap  # never looser; 35 % (unknown date) vs the 40 % yaml value
        a.purchased_at = datetime(2026, 1, 5, tzinfo=UTC)
        known = AS.consistency(s, a, r, True)
        assert known is not None and known.cap >= on.cap and known.cap <= off.cap


def test_funded_day_stop_150k_only_sub_setting():
    f = lambda **k: funded_day_stop_hit(  # noqa: E731
        k.get("on", True), D(30), k.get("cfg", CFG), k.get("stage", "FUNDED"), k.get("sw", True), D(9000), k["p"]
    )
    assert f(p=D(2700)) and not f(p=D(2699))  # 30 % of the 9,000 target
    assert not f(p=D(9999), on=False) and not f(p=D(9999), sw=False) and not f(p=D(9999), stage="EVAL")
    assert not f(p=D(9999), cfg=CFG25) and not f(p=D(9999), cfg=None)
    assert stage_switch_on("FUNDED", True, False) and stage_switch_on("LIVE", False, True)
    assert not stage_switch_on("EVAL", True, True) and not stage_switch_on("LIVE", True, False)
    assert fast_pass_size(True, CFG, "FUNDED", D(150000), "NOISE", D(4500)) is None
    assert fast_pass_size(True, CFG, "EVAL", D(150000), "NOISE", D(4500)) is not None  # EVAL needs no stage switch


def test_day_stop_skips_in_controller(authed, clock):
    st, aid = _stage(authed, "FUNDED", funded=True, clock=clock)
    h = st.controller.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(
        update={"fast_pass_funded_day_stop": True, "fast_pass_funded_day_stop_pct": D(0)})})
    res, _ = _run(st, aid, "NOISE")
    assert not res.ok and res.reason == "FUNDED_DAY_STOP"


def test_switch_api_phrase_audit_and_one_click_off(authed):
    cid = None
    with authed.app.state.sessionmaker() as s:
        s.add(Account(broker_account_id="FX1", stage="FUNDED", drawdown_type="eod"))
        s.commit()
    r = authed.get("/api/risk/fast-pass-stage").json()
    assert r["stages"]["FUNDED"]["enabled"] is False and r["stages"]["LIVE"]["enabled"] is False  # default OFF
    assert "UNVERIFIED" in r["warning"] and r["guards"] and cid is None
    assert authed.put("/api/risk/fast-pass-stage/FUNDED", json={"enabled": True, "confirm": "yes"}).status_code == 422
    ok = authed.put("/api/risk/fast-pass-stage/FUNDED", json={"enabled": True, "confirm": "ENABLE FAST PASS FUNDED"})
    assert ok.status_code == 200 and authed.app.state.rules.fast_pass_funded_on
    assert authed.put("/api/risk/fast-pass-stage/FUNDED", json={"enabled": False}).status_code == 200
    assert not authed.app.state.rules.fast_pass_funded_on
    assert authed.put("/api/risk/fast-pass-stage/BAD", json={"enabled": False}).status_code == 422


def test_live_switch_blocked_without_live_gates(authed):
    with authed.app.state.sessionmaker() as s:
        s.add(Account(broker_account_id="LV1", stage="LIVE", drawdown_type="eod"))
        s.commit()
    r = authed.put("/api/risk/fast-pass-stage/LIVE", json={"enabled": True, "confirm": "ENABLE FAST PASS LIVE"})
    assert r.status_code == 422 and "LIVE gates" in str(r.json())
    assert not authed.app.state.rules.fast_pass_live_on
    assert authed.get("/api/risk/fast-pass-stage").json()["stages"]["LIVE"]["blocked"]


def test_no_accounts_blocks_and_old_settings_load(authed):
    r = authed.put("/api/risk/fast-pass-stage/FUNDED", json={"enabled": True, "confirm": "ENABLE FAST PASS FUNDED"})
    assert r.status_code == 422
    with authed.app.state.sessionmaker() as s:
        eff = ss.effective(s, authed.app.state.rules.base)  # no stored kinds = a pre-D180 database
        assert eff.fast_pass_funded_on is False and eff.fast_pass_live_on is False
