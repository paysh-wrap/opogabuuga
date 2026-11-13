"""D138: LucidPro plan card rules (eval consistency 40 %, day stop 38 %, eval DLL, LucidScale, 3 profitable days)."""

from decimal import Decimal as D
from pathlib import Path

import pytest

from app.automation import state as st
from app.config import load_rules
from app.models import Account
from app.phases.payout_plan import plan_payout

RULES = Path(__file__).resolve().parents[3] / "config" / "rules"
DAY_STOP = {25: D("475.00"), 50: D("1140.00"), 100: D("2280.00"), 150: D("3420.00")}
CAP = {25: D("500.00"), 50: D("1200.00"), 100: D("2400.00"), 150: D("3600.00")}


def rules(k):
    return load_rules(RULES / f"lucid_pro_{k}k.yaml").rules


@pytest.mark.parametrize("k", (25, 50, 100, 150))
def test_eval_consistency_cap_and_day_stop(k):
    # the same consistency/DLL path serves every strategy (NOISE, AI Duo, Order Flow, PM fade): no per-strategy rule
    lim = st.consistency(None, Account(stage="EVAL"), rules(k))  # type: ignore[arg-type]
    assert lim is not None and (lim.cap, lim.day_stop) == (CAP[k], DAY_STOP[k])


def test_pro_25k_eval_dll_600_and_scale_after_lock():
    r = rules(25)
    a = Account(
        stage="EVAL",
        drawdown_type="eod",
        dll_enabled=True,
        starting_balance=D(25000),
        mll_locked=False,
        mll_peak=D(26000),
    )
    assert st.dll_for(r, a) == D(600)
    a.mll_locked, a.mll_peak = True, D(26500)
    assert st.dll_for(r, a) == D("900.00")  # 60 % of 1,500 peak EOD profit
    a.stage = "FUNDED"
    assert st.dll_for(r, a) == D("900.00")
    a.dll_enabled = False
    assert st.dll_for(r, a) is None


def test_flex_dll_unscaled():
    f = load_rules(RULES / "lucid_flex_50k.yaml").rules
    a = Account(
        stage="FUNDED",
        drawdown_type="eod",
        dll_enabled=True,
        starting_balance=D(50000),
        mll_locked=True,
        mll_peak=D(53000),
    )
    assert st.dll_for(f, a) == f.funded.daily_loss_limit


def _plan(days):
    p = rules(25).funded.payout
    return plan_payout(
        balance=D(27500),
        week_profit=D(1000),
        cycle_profit=D(1000),
        locked=False,
        sweep_above=D(28100),
        skim_mode="off",
        buffer=p.buffer,
        min_request=p.min_request,
        min_cycle_profit=p.min_cycle_profit,
        split=p.split,
        profitable_days=days,
        min_profitable_days=p.min_profitable_days,
        mode="max_eligible",
    )


def test_pro_payout_needs_3_profitable_days():
    assert rules(25).funded.payout.min_profitable_days == 3
    assert _plan(2).reason == "NOT_ENOUGH_PROFITABLE_DAYS"
    assert _plan(3).kind == "max"
