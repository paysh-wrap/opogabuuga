"""D156 "150K fast pass" through the controller: NOISE 4 @ $100 stop, CANDACE 3, both 2 at a cushion <= $1,500;
OFF / FUNDED = today's sizing; the later Lucid / Paytience checks still shrink or skip."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.config import FastPassCfg
from app.engine.noise import stop_pts_for_usd
from app.engine.trade_plan import Direction
from app.models import Account, AuditLog
from app.signals import strategy_service as SS

AT = datetime(2026, 10, 13, 15, 0, tzinfo=UTC)  # Tue 11:00 ET
CFG = FastPassCfg(
    account_size=D(150000), noise_contracts=5, noise_stop_usd=D(100), candace_contracts=4,
    brake_cushion_usd=D(1500), noise_brake_contracts=2, candace_brake_contracts=2,
)  # fmt: skip
CFG25 = FastPassCfg(
    account_size=D(25000), noise_contracts=1, noise_stop_usd=D(75), candace_contracts=2,
    brake_cushion_usd=D(333), brake_inclusive=False, candace_brake_contracts=1,
)  # fmt: skip
CFG100 = FastPassCfg(
    account_size=D(100000), noise_contracts=2, noise_stop_usd=D(250), candace_contracts=3,
    brake_cushion_usd=D(1000), brake_inclusive=False, noise_brake_contracts=1, candace_brake_contracts=2,
)  # fmt: skip
SWITCH = {25000: ("fast_pass_25k", CFG25), 100000: ("fast_pass_100k", CFG100), 150000: ("fast_pass_150k", CFG)}
PLANS = {
    "NOISE": ("NOISE", D(20000), D(19800), D(20050), D(200), D("0.25")),  # 1 % stop ($400 a micro) → $100 is tighter
    "CANDACE_ICT": ("CANDACE_ICT", D(20000), D(19980), D(20040), D(20), D(2)),
}


def _setup(authed, clock, *, stage="EVAL", balance="150000", cushion=D(4500), on=True, internal=None, dll=None):
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
    upd = {"candace_ict": True}
    for sw, cfg in SWITCH.values():
        upd[sw] = on
        upd[sw + "_cfg"] = cfg
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


@pytest.mark.parametrize(("cushion", "want", "braked"), [(D(4000), 5, False), (D(1500), 2, True)])
def test_noise_size_and_stop(authed, clock, cushion, want, braked):
    st, aid = _setup(authed, clock, cushion=cushion)
    res, fp = _run(st, aid, "NOISE")
    assert fp and fp[-1]["contracts"] == want and fp[-1]["braked"] is braked and fp[-1]["stop_usd"] == "100"
    assert D(fp[-1]["stop_pts"]) == _stop_pts(st)
    if (
        res.reason == "DRAWDOWN_TOO_DEEP"
    ):  # a later Lucid / Paytience check (D57 drawdown scale) may still skip the trade
        assert not res.ok and want == 5
        return
    assert _fixed(res) == str(want) and res.ok and res.contracts == want, res
    [t] = st.controller.om.trades.values()
    # $100 a micro (tighter than the 1 % stop); the D57 drawdown shrink may still tighten it further, never widen
    assert t.qty == want and D(0) < t.plan.entry - t.plan.stop <= _stop_pts(st)


@pytest.mark.parametrize(("cushion", "want"), [(D(4000), 4), (D(1000), 2)])
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
    [{"on": False}, {"stage": "FUNDED"}, {"balance": "50000"}],
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
    assert fp[-1]["contracts"] == 5 and res.ok and res.contracts == 3, res


def test_dll_worst_case_still_shrinks(authed, clock):
    st, aid = _setup(authed, clock, dll=D(250))  # 5 micros × $100 does not fit a $250 daily loss limit
    res, fp = _run(st, aid, "NOISE")
    assert fp[-1]["contracts"] == 5
    assert (res.ok and 1 <= res.contracts < 5) or not res.ok, res
    assert res.contracts * 100 <= 250


def test_one_position_still_skips(authed, clock):
    st, aid = _setup(authed, clock)
    res, _ = _run(st, aid, "CANDACE_ICT", key="a")
    assert res.ok, res
    res2, fp = _run(st, aid, "NOISE", key="b")  # one position already open → max 1 position still skips
    assert fp[-1]["contracts"] == 5 and not res2.ok and res2.reason == "POSITION_OPEN"


def test_strategy_card_and_setting(authed):
    got = {t["key"] for t in authed.get("/api/strategies").json()["toggles"]}
    assert "fast_pass_150k" in got  # D167: all four cards always shown (cfg read from each plan file)
    h = authed.app.state.rules
    cfgs = {"fast_pass_150k_cfg": CFG, "fast_pass_25k_cfg": CFG25, "fast_pass_100k_cfg": CFG100}
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update=cfgs)})
    tg = {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}
    assert "docs/results/pass_fastest/" in tg["fast_pass_25k"]["note"] and "< $333" in tg["fast_pass_25k"]["on_label"]
    assert (
        "NOISE 2 @ $250" in tg["fast_pass_100k"]["on_label"]
        and "CANDACE 3 (cushion < $1,000: 2)" in tg["fast_pass_100k"]["on_label"]
    )
    for k in ("fast_pass_25k", "fast_pass_100k"):
        assert (
            authed.put("/api/risk/settings", json={"changes": {f"strategy.{k}": True}, "note": "t"}).status_code == 200
        )
    h.rules = h.rules.model_copy(update={"strategy": h.rules.strategy.model_copy(update=cfgs)})  # PUT reloaded
    t = {t["key"]: t for t in authed.get("/api/strategies").json()["toggles"]}["fast_pass_150k"]
    assert t["setting"] == "strategy.fast_pass_150k" and t["value"] is False and t["title"].startswith("150K")
    assert "NOISE 5 @ $100" in t["on_label"] and "CANDACE 4" in t["on_label"] and "≤ $1,500" in t["on_label"]
    assert "beat109/RESULTS.md" in t["note"] and "%" not in t["note"]  # cites the study, no hard-coded odds
    put = authed.put("/api/risk/settings", json={"changes": {"strategy.fast_pass_150k": True}, "note": "t"})
    assert put.status_code == 200
    assert authed.app.state.rules.rules.strategy.fast_pass_150k is True
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.fast_pass_150k": "maybe"}, "note": "t"})
    assert bad.status_code in (400, 422)


# ---- D157: 25K and 100K plans -------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("bal", "mode", "cushion", "want"),
    [
        ("25000", "NOISE", D(900), 1), ("25000", "NOISE", D(200), 1),
        ("25000", "CANDACE_ICT", D(900), 2), ("25000", "CANDACE_ICT", D(333), 2), ("25000", "CANDACE_ICT", D(300), 1),
        ("100000", "NOISE", D(3000), 2), ("100000", "NOISE", D(1000), 2), ("100000", "NOISE", D(900), 1),
        ("100000", "CANDACE_ICT", D(3000), 3), ("100000", "CANDACE_ICT", D(999), 2),
    ],
)  # fmt: skip
def test_small_plans_size(authed, clock, bal, mode, cushion, want):
    st, aid = _setup(authed, clock, balance=bal, cushion=cushion)
    _, fp = _run(st, aid, mode)
    assert fp and fp[-1]["contracts"] == want and fp[-1]["strategy"] == mode


@pytest.mark.parametrize("kw", [{"on": False}, {"stage": "FUNDED"}, {"balance": "50000"}])
def test_small_plans_off_funded_wrong_size(authed, clock, kw):
    st, aid = _setup(authed, clock, **{"balance": "25000", "cushion": D(900), **kw})
    _, fp = _run(st, aid, "NOISE")
    assert fp == []


def test_small_plan_dll_still_shrinks(authed, clock):
    st, aid = _setup(authed, clock, balance="100000", cushion=D(3000), dll=D(100))  # 2 micros × $250 > $100 DLL
    res, fp = _run(st, aid, "NOISE")
    assert fp[-1]["contracts"] == 2 and res.contracts * 250 <= 100


# ---- D162: day lock + NOISE lock trigger + 50K card ------------------------------------------------------------------
def test_d162_day_lock_skips_noise_only(authed, clock, monkeypatch):
    import app.automation.state as stt

    cfg = CFG.model_copy(update={"day_lock_pct": D("0.1"), "noise_lock_trigger_pts": D(80)})
    monkeypatch.setitem(SWITCH, 150000, ("fast_pass_150k", cfg))
    st, aid = _setup(authed, clock, cushion=D(4000))
    target = st.controller.rules.rules.eval.profit_target
    orig = stt.day_stats

    def big_day(s, a, now):
        d = orig(s, a, now)
        d.day_profit = target / 50  # 2 % of the target: below 10 % of the remaining target -> not locked
        return d

    monkeypatch.setattr(stt, "day_stats", big_day)
    res, _ = _run(st, aid, "NOISE", "a")
    assert res.reason != "EVAL_DAY_LOCK"  # below the lock: sized and traded as usual
    monkeypatch.setattr(
        stt, "day_stats", lambda s, a, now: _day(orig, s, a, now, target / 5)
    )  # 20 % of the target >= 10 % of the remaining
    res, _ = _run(st, aid, "NOISE", "b")
    assert not res.ok and res.reason == "EVAL_DAY_LOCK", res  # today's profit >= day_lock_pct x remaining target
    res, _ = _run(st, aid, "CANDACE_ICT", "c")  # CANDACE is not day-locked (study definition: NOISE only)
    assert res.reason != "EVAL_DAY_LOCK"
    ts = [t for t in st.controller.om.trades.values() if t.strategy == "NOISE"]
    assert all(t.profit_lock is not None and t.profit_lock[0] == D(80) for t in ts)  # own trigger, same distance


def _day(orig, s, a, now, profit):
    d = orig(s, a, now)
    d.day_profit = profit
    return d
