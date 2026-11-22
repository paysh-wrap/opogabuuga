"""D156 "150K fast pass" through the controller: NOISE 4 @ $100 stop, CANDACE 3, both 2 at a cushion <= $1,500;
OFF / FUNDED = today's sizing; the later Lucid / Paytience checks still shrink or skip."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.config import FastPass150kCfg
from app.engine.noise import stop_pts_for_usd
from app.engine.trade_plan import Direction
from app.models import Account, AuditLog
from app.signals import strategy_service as SS

AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)  # Tue 11:00 ET
CFG = FastPass150kCfg(
    account_size=D(150000), noise_contracts=4, noise_stop_usd=D(100), candace_contracts=3,
    brake_cushion_usd=D(1500), brake_contracts=2,
)  # fmt: skip
PLANS = {
    "NOISE": ("NOISE", D(20000), D(19800), D(20050), D(200), D("0.25")),  # 1 % stop ($400 a micro) → $100 is tighter
    "CANDACE_ICT": ("CANDACE_ICT", D(20000), D(19980), D(20040), D(20), D(2)),
}


def _setup(authed, clock, *, stage="EVAL", balance="150000", cushion=D(4000), on=True, internal=None, dll=None):
    st = authed.app.state
    clock.set(AT)
    aid = authed.post("/api/accounts", json={"label": "F", "stage": stage, "balance": balance}).json()["id"]
    authed.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
    authed.post("/api/attestation", json={"confirm": True})
    st.controller.mode = "FULL"
    st.controller.adapter.sim.last["MNQ"] = D(20000)
    with st.sessionmaker() as s:
        a = s.get(Account, aid)
        a.mll, a.mll_peak = D(balance) - cushion, D(balance)  # cushion = equity − current MLL
        s.commit()
    h = st.controller.rules
    upd = {"fast_pass_150k": on, "fast_pass_150k_cfg": CFG, "candace_ict": True}
    rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update=upd)})
    if internal:
        rules = rules.model_copy(update={"internal": rules.internal.model_copy(update=internal)})
    if dll is not None:
        rules = rules.model_copy(update={"eval": rules.eval.model_copy(update={"daily_loss_limit": dll})})
    h.rules = rules
    return st, aid


def _run(st, aid, mode, key="1"):
    with st.sessionmaker() as s:
        x = SS._new_signal(
            s, FixedClock(AT), symbol="MNQ", key=f"MNQ-{mode}-fp-{key}", direction=Direction.LONG, at=AT,
            gate=(True, "OK", ""), features={"size_mult": "0.25", "invalid": "19800", "t2": "20050"},
            plan=PLANS[mode],
        )  # fmt: skip
        s.commit()
        sid = x.id
    [res] = asyncio.run(st.controller.execute(sid, "automation", only=[aid]))
    with st.sessionmaker() as s:
        fp = [x.payload for x in s.query(AuditLog).filter_by(action="trade.fast_pass")]
    return res, fp


def _fixed(res):
    return next(c for c in res.checks if c["check"] == "fixed_size")["contracts"]


def _stop_pts(st):
    inst = st.controller.rules.rules.instruments["MNQ"]
    slip = inst.slippage_ticks or st.controller.rules.rules.trade_plan.slippage_ticks
    return stop_pts_for_usd(D(100), inst.tick, inst.tick_value, inst.fee_rt, slip)


@pytest.mark.parametrize(("cushion", "want", "braked"), [(D(4000), 4, False), (D(1500), 2, True)])
def test_noise_size_and_stop(authed, clock, cushion, want, braked):
    st, aid = _setup(authed, clock, cushion=cushion)
    res, fp = _run(st, aid, "NOISE")
    assert fp and fp[-1]["contracts"] == want and fp[-1]["braked"] is braked and fp[-1]["stop_usd"] == "100"
    assert D(fp[-1]["stop_pts"]) == _stop_pts(st)
    assert _fixed(res) == str(want) and res.ok and res.contracts == want, res
    [t] = st.controller.om.trades.values()
    # $100 a micro (tighter than the 1 % stop); the D57 drawdown shrink may still tighten it further, never widen
    assert t.qty == want and D(0) < t.plan.entry - t.plan.stop <= _stop_pts(st)


@pytest.mark.parametrize(("cushion", "want"), [(D(4000), 3), (D(1000), 2)])
def test_candace_fixed_size(authed, clock, cushion, want):
    st, aid = _setup(authed, clock, cushion=cushion)
    res, fp = _run(st, aid, "CANDACE_ICT")
    assert fp[-1]["contracts"] == want and fp[-1]["strategy"] == "CANDACE_ICT" and fp[-1]["stop_usd"] is None
    with st.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="trade.cand_size").one().payload["contracts"] == want
    assert res.ok, res
    assert sum(t.qty for t in st.controller.om.trades.values()) == want  # grade C (0.25) would have been 0-1


@pytest.mark.parametrize(
    ("kw"),
    [{"on": False}, {"stage": "FUNDED"}, {"balance": "100000"}],
)
def test_off_funded_other_size_unchanged(authed, clock, kw):
    st, aid = _setup(authed, clock, **kw)
    res, fp = _run(st, aid, "CANDACE_ICT")
    assert fp == [] and res.reason == "CAND_GRADE_SIZE_BELOW_1"  # today's grade size (C = 0.25 → 0 micros)


def test_noise_off_keeps_the_strategy_stop(authed, clock):
    st, aid = _setup(authed, clock, on=False)
    res, fp = _run(st, aid, "NOISE")
    assert fp == [] and res.ok, res
    [t] = st.controller.om.trades.values()
    assert t.plan.entry - t.plan.stop > _stop_pts(st) * 3  # the strategy's own (wider) stop


def test_internal_max_still_shrinks(authed, clock):
    st, aid = _setup(authed, clock, internal={"internal_max_micros": 3})
    res, fp = _run(st, aid, "NOISE")
    assert fp[-1]["contracts"] == 4 and res.ok and res.contracts == 3, res


def test_dll_worst_case_still_shrinks(authed, clock):
    st, aid = _setup(authed, clock, dll=D(250))  # 4 micros × $100 does not fit a $250 daily loss limit
    res, fp = _run(st, aid, "NOISE")
    assert fp[-1]["contracts"] == 4
    assert (res.ok and 1 <= res.contracts < 4) or not res.ok, res
    assert res.contracts * 100 <= 250


def test_one_position_still_skips(authed, clock):
    st, aid = _setup(authed, clock)
    res, _ = _run(st, aid, "CANDACE_ICT", key="a")
    assert res.ok, res
    res2, fp = _run(st, aid, "NOISE", key="b")  # one position already open → max 1 position still skips
    assert fp[-1]["contracts"] == 4 and not res2.ok and res2.reason == "POSITION_OPEN"


def test_strategy_card_and_setting(authed):
    got = {t["key"] for t in authed.get("/api/strategies").json()["toggles"]}
    assert "fast_pass_150k" not in got  # plan file without fast_pass_150k_cfg → no card (feature inert)
    h = authed.app.state.rules
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update={"fast_pass_150k_cfg": CFG})})
    t = {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}["fast_pass_150k"]
    assert t["setting"] == "strategy.fast_pass_150k" and t["value"] is False and t["title"].startswith("150K")
    assert "NOISE 4 @ $100" in t["on_label"] and "CANDACE 3" in t["on_label"] and "≤ $1,500" in t["on_label"]
    assert "brake150/RESULTS.md" in t["note"] and "%" not in t["note"]  # cites the study, no hard-coded odds
    put = authed.put("/api/risk/settings", json={"changes": {"strategy.fast_pass_150k": True}, "note": "t"})
    assert put.status_code == 200
    assert authed.app.state.rules.rules.strategy.fast_pass_150k is True
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.fast_pass_150k": "maybe"}, "note": "t"})
    assert bad.status_code in (400, 422)
