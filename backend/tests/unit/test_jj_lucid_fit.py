"""D143: JJ F.P.T STRAT sized to fit Lucid Pro 25K/50K/100K/150K (EOD drawdown), EVAL and FUNDED — real plan yamls."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal as D

import pytest

from app.config import load_rules
from app.engine.jj_fpt import contracts_for, trade_risk_usd
from app.engine.trade_plan import Direction, TradePlan
from app.phases.phase_engine import firm_max_micros, stage_rules
from app.risk.consistency import eval_limits, funded_limits
from app.settings import REPO_ROOT
from tests.unit.test_risk_phase4 import LIM, run


def _plan(k: int):
    return load_rules(REPO_ROOT / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules


def fit(r, stage: str) -> tuple[D, dict[D, int]]:
    """Fresh account (no P&L today, MLL at its start): per-trade $ and capped contracts per stop size."""
    jj, i = r.strategy.jj_fpt_cfg, r.internal
    sr = stage_rules(r, stage, None, True)
    if stage == "EVAL":
        cons = eval_limits(r.eval.profit_target, r.eval.consistency_max_day_pct, i.consistency_day_stop_buffer_pct)
    else:
        cons = funded_limits(
            D(0), i.funded_consistency_reference_min, i.funded_consistency_pct, i.consistency_day_stop_buffer_pct
        )
    risk = trade_risk_usd(
        sr.max_loss,
        jj.risk_pct_of_drawdown,
        jj.stop_after_losses,
        sr.dll,
        jj.dll_use_pct,
        sr.max_loss - i.kill_switch_mll_distance,
        r.strategy.max_trade_risk_usd,
        cons.day_stop,
    )
    m = r.instrument("MNQ")
    slip = m.slippage_ticks or r.trade_plan.slippage_ticks
    cap = min(firm_max_micros(r, stage, D(0)), i.internal_max_micros)
    out = {
        pts: min(contracts_for(risk, pts, m.tick, m.tick_value, m.fee_rt, slip), cap)
        for pts in (D(25), D("12.5"), D(50))
    }
    return risk, out


TABLE = {  # plan: per-trade $, contracts at 25 / 12.5 / 50 pt (MNQ $52 / $27 / $102 per micro incl. fee + slippage)
    25: (D("158.33"), 3, 5, 1),  # consistency day stop $475 / 3
    50: (D("360.00"), 6, 13, 3),  # DLL $1,200 x 0.9 / 3
    100: (D("540.00"), 10, 20, 5),  # DLL $1,800 x 0.9 / 3
    150: (D("810.00"), 15, 30, 7),  # DLL $2,700 x 0.9 / 3
}


@pytest.mark.parametrize("stage", ["EVAL", "FUNDED"])
@pytest.mark.parametrize("k", [25, 50, 100, 150])
def test_pro_plan_fit_table(k, stage):
    r = _plan(k)
    assert r.eval.drawdown_type == "eod" and r.funded.drawdown_type == "eod"
    assert r.strategy.jj_fpt is False  # default OFF
    risk, n = fit(r, stage)
    exp = TABLE[k]
    assert (risk, n[D(25)], n[D("12.5")], n[D(50)]) == exp
    sr = stage_rules(r, stage, None, True)
    worst = 3 * risk
    assert worst <= sr.dll * r.strategy.jj_fpt_cfg.dll_use_pct  # 3 losses in a row fit the DLL
    assert worst < sr.max_loss - r.internal.kill_switch_mll_distance  # ... and never reach the kill switch


def test_trade_risk_terms():
    base = dict(
        max_loss=D(1000),
        risk_pct=D("0.25"),
        losses_per_session=3,
        dll_left=None,
        dll_use_pct=D(1),
        mll_room=D(10000),
        plan_cap=None,
        day_stop=None,
    )
    assert trade_risk_usd(**base) == D("250.00")  # JJ #29 alone
    assert trade_risk_usd(**{**base, "dll_left": D(300)}) == D("100.00")  # DLL left today / 3
    assert trade_risk_usd(**{**base, "dll_left": D(-5)}) == D(0)
    assert trade_risk_usd(**{**base, "mll_room": D(150)}) == D("50.00")  # EOD-trailed MLL room / 3
    assert trade_risk_usd(**{**base, "mll_room": D(-1)}) == D(0)
    assert trade_risk_usd(**{**base, "plan_cap": D(99)}) == D("99.00")
    assert trade_risk_usd(**{**base, "day_stop": D(100)}) == D("33.33")
    assert trade_risk_usd(**{**base, "losses_per_session": 0}) == D("250.00")  # never divides by 0
    assert contracts_for(D("33.33"), D(25), D("0.25"), D("0.5"), D(1), 1) == 0  # → JJ_SIZE_BELOW_1


JJ_PLAN = TradePlan(Direction.SHORT, D(20040), D(20065), D(20002), D(25), D("1.52"), mode="JJ_FPT")


def test_firm_and_internal_max_cap_fixed_jj_size():
    r = run(plan=JJ_PLAN, lim=replace(LIM, fixed_contracts=15, firm_max=4), consistency=None, acct_dll=None)
    assert r.ok and r.contracts == 4  # firm max micros
    r = run(plan=JJ_PLAN, lim=replace(LIM, fixed_contracts=15, internal_max=2), consistency=None, acct_dll=None)
    assert r.ok and r.contracts == 2  # internal max micros
