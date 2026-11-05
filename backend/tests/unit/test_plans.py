from decimal import Decimal as D
from pathlib import Path

import pytest

from app.config import load_rules
from app.phases.phase_engine import firm_max_micros, funded_live_move_triggered, stage_rules
from app.risk.validation import max_base_for_stage, validate

RULES = Path(__file__).resolve().parents[3] / "config" / "rules"


def r(name):
    return load_rules(RULES / f"{name}.yaml").rules


@pytest.mark.parametrize("plan", [f"lucid_{p}_{k}k" for p in ("pro", "flex") for k in (25, 50, 100, 150)])
def test_every_plan_validates(plan):
    v = validate(r(plan))
    assert v.ok, v.errors


def test_flex_funded_scaling_by_profit():
    f = r("lucid_flex_50k")
    assert firm_max_micros(f, "FUNDED", D(0)) == 20
    assert firm_max_micros(f, "FUNDED", D(1500)) == 30
    assert firm_max_micros(f, "FUNDED", D(9999)) == 40
    assert firm_max_micros(f, "FUNDED", D(-300)) == 20  # below the first tier → smallest
    assert firm_max_micros(f, "EVAL", D(0)) == 40  # eval: full size
    assert firm_max_micros(r("lucid_pro_50k"), "FUNDED", D(0)) == 40  # Pro: no scaling


def test_pro_has_no_eval_consistency_and_25k_no_eval_dll():
    p = r("lucid_pro_25k")
    assert p.eval.consistency_max_day_pct is None and p.eval.daily_loss_limit is None
    assert max_base_for_stage(p, "EVAL") == D(2250)  # MLL + target
    assert not funded_live_move_triggered(D(99999), p)  # no $-per-day trigger on Pro/Flex
    assert stage_rules(p, "FUNDED").news_hard_breach is False  # news allowed on Pro/Flex


def test_flex_payout_rules():
    pr = r("lucid_flex_100k").funded.payout
    assert (pr.max_pct_of_profit, pr.min_profitable_days, pr.min_day_profit, pr.lock_mll_on_payout) == (
        D("0.5"),
        5,
        D(200),
        True,
    )
