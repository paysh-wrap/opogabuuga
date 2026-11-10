"""D87 Fast Evaluation: pure mechanisms, EVAL-only scope, no increase after a loss, default OFF."""

from decimal import Decimal as D

import pytest

from app.config import FastEvalCfg
from app.risk.consistency import ConsistencyLimits
from app.risk.fast_eval import (
    FastCtx,
    early_active,
    effective_fast_cfg,
    fast_contracts,
    fast_eval_effective,
    fast_risk_pct,
    harvest_limits,
    ladder_extra,
    quality_day_block,
)


def cfg(**kw) -> FastEvalCfg:
    base = {
        "ladder": {"enabled": True, "steps": [{"cushion_frac": "0.5", "extra": 1}, {"cushion_frac": "0.8", "extra": 2}],
                   "max_contracts": 3},
        "harvest": {"enabled": True, "day_stop_pct_of_target": "30"},
        "early": {"enabled": True, "first_trades": 10, "until_profit_frac": "0.5", "cushion_frac": "0.5",
                  "risk_pct": "0.14", "extra_contracts": 1},
        "quality_day": {"enabled": True, "mode": "prev_day", "trailing_days": 3},
    }  # fmt: skip
    base.update(kw)
    return FastEvalCfg.model_validate(base)


def ctx(**kw) -> FastCtx:
    d = dict(cushion=D(1000), mll=D(1000), last_closed_was_loss=False, losses_today=0, trades_in_stage=50,
             profit_frac=D("0.6"))  # fmt: skip
    d.update(kw)
    return FastCtx(**d)


def test_default_off_and_inert():
    c = FastEvalCfg()
    assert not (c.ladder.enabled or c.harvest.enabled or c.early.enabled or c.quality_day.enabled)
    assert fast_contracts(c, ctx(), 1) == 1 and ladder_extra(c, ctx()) == 0 and not early_active(c, ctx())
    assert fast_risk_pct(c, ctx(trades_in_stage=0), D("0.1")) == D("0.1")
    assert quality_day_block(c, [D(-5)]) is None
    lim = ConsistencyLimits(D(500), D("437.5"))
    assert harvest_limits(lim, c, D(1250)) is lim


def test_eval_only_scope():
    for stage in ("FUNDED", "LIVE", "", "eval"):
        assert fast_eval_effective(stage, True) is False
        assert effective_fast_cfg(stage, True, cfg()) is None
    assert fast_eval_effective("EVAL", True) and not fast_eval_effective("EVAL", False)
    c = cfg()
    assert effective_fast_cfg("EVAL", True, c) is c and effective_fast_cfg("EVAL", False, c) is None


def test_applies_to_stages_cannot_include_funded():
    with pytest.raises(ValueError):
        FastEvalCfg.model_validate({"applies_to_stages": ["EVAL", "FUNDED"]})
    with pytest.raises(ValueError):
        FastEvalCfg.model_validate({"pace_escalation": True})


def test_ladder_steps_with_cushion():
    c = cfg()
    assert ladder_extra(c, ctx(cushion=D(400))) == 0
    assert ladder_extra(c, ctx(cushion=D(500))) == 1
    assert ladder_extra(c, ctx(cushion=D(900))) == 2
    assert ladder_extra(c, ctx(mll=D(0))) == 0
    c2 = cfg(early={"enabled": False})
    assert fast_contracts(c2, ctx(cushion=D(900)), 1) == 3  # base 1 + 2, ceiling 3
    assert (
        fast_contracts(
            cfg(
                early={"enabled": False},
                ladder={"enabled": True, "steps": [{"cushion_frac": "0.1", "extra": 5}], "max_contracts": 3},
            ),
            ctx(),
            1,
        )
        == 3
    )  # capped by max_contracts
    assert (
        fast_contracts(
            cfg(
                early={"enabled": False},
                ladder={"enabled": True, "steps": [{"cushion_frac": "0.1", "extra": 1}], "max_contracts": 1},
            ),
            ctx(),
            4,
        )
        == 4
    )  # never below the base


def test_no_increase_after_loss_no_martingale():
    c = cfg()
    for kw in ({"last_closed_was_loss": True}, {"losses_today": 1}):
        assert ladder_extra(c, ctx(cushion=D(1000), **kw)) == 0
        assert fast_contracts(c, ctx(cushion=D(1000), trades_in_stage=0, **kw), 2) == 2  # exactly the base
        assert not early_active(c, ctx(trades_in_stage=0, profit_frac=D(0), **kw))
        assert fast_risk_pct(c, ctx(trades_in_stage=0, profit_frac=D(0), **kw), D("0.1")) == D("0.1")
    # after the loss is gone (a win), the ladder may step up again
    assert fast_contracts(c, ctx(cushion=D(1000)), 1) > 1


def test_early_tier_window_and_cushion():
    c = cfg()
    assert early_active(c, ctx(trades_in_stage=3, profit_frac=D("0.1")))
    assert not early_active(c, ctx(trades_in_stage=10, profit_frac=D("0.1")))  # past N trades
    assert not early_active(c, ctx(trades_in_stage=3, profit_frac=D("0.5")))  # past the profit share
    assert not early_active(c, ctx(trades_in_stage=3, profit_frac=D("0.1"), cushion=D(499)))  # below cushion
    assert not early_active(c, ctx(trades_in_stage=3, profit_frac=D("0.1"), mll=D(0)))
    assert fast_risk_pct(c, ctx(trades_in_stage=3, profit_frac=D(0)), D("0.10")) == D("0.14")
    assert fast_risk_pct(c, ctx(trades_in_stage=3, profit_frac=D(0)), D("0.14")) == D("0.14")  # never lowers
    assert fast_risk_pct(c, ctx(), D("0.10")) == D("0.10")  # outside the window
    only_n = cfg(early={"enabled": True, "first_trades": 5, "risk_pct": None, "extra_contracts": 2})
    assert early_active(only_n, ctx(trades_in_stage=4)) and not early_active(only_n, ctx(trades_in_stage=5))
    assert fast_risk_pct(only_n, ctx(trades_in_stage=1), D("0.1")) == D("0.1")  # no risk_pct configured
    assert (
        fast_contracts(cfg(ladder={"enabled": False}, early=only_n.early.model_dump()), ctx(trades_in_stage=1), 1) == 1
    )
    both = cfg(ladder={"enabled": True, "steps": [], "max_contracts": 4}, early=only_n.early.model_dump())
    assert fast_contracts(both, ctx(trades_in_stage=1), 1) == 3
    only_p = cfg(early={"enabled": True, "until_profit_frac": "0.3"})
    assert early_active(only_p, ctx(trades_in_stage=999, profit_frac=D("0.2")))


def test_harvest_only_tightens():
    lim = ConsistencyLimits(D(500), D("437.50"))
    t = harvest_limits(lim, cfg(), D(1250))
    assert t.day_stop == D("375.00") and t.cap == D(500)
    loose = cfg(harvest={"enabled": True, "day_stop_pct_of_target": "90"})
    assert harvest_limits(lim, loose, D(1250)).day_stop == D("437.50")  # can never loosen the existing stop
    assert harvest_limits(None, cfg(), D(1250)) is None
    assert harvest_limits(lim, cfg(harvest={"enabled": False}), D(1250)) is lim


def test_quality_day_filter():
    c = cfg()
    assert quality_day_block(c, []) is None
    assert quality_day_block(c, [D(5), D(-1)]) == "FAST_EVAL_QUALITY_DAY"
    assert quality_day_block(c, [D(-5), D(1)]) is None
    t = cfg(quality_day={"enabled": True, "mode": "trailing", "trailing_days": 2})
    assert quality_day_block(t, [D(100), D(-10), D(5)]) == "FAST_EVAL_QUALITY_DAY"  # last 2 sum -5
    assert quality_day_block(t, [D(-100), D(10), D(5)]) is None  # old loss outside the window
    assert quality_day_block(cfg(quality_day={"enabled": False}), [D(-1)]) is None


@pytest.mark.parametrize(
    "patch",
    [
        {"ladder": {"enabled": True, "steps": [{"cushion_frac": "0.5", "extra": 0}]}},
        {
            "ladder": {
                "enabled": True,
                "steps": [{"cushion_frac": "0.8", "extra": 1}, {"cushion_frac": "0.5", "extra": 2}],
            }
        },
        {
            "ladder": {
                "enabled": True,
                "steps": [{"cushion_frac": "0.5", "extra": 2}, {"cushion_frac": "0.8", "extra": 1}],
            }
        },
        {"ladder": {"max_contracts": 0}},
        {"harvest": {"day_stop_pct_of_target": "0"}},
        {"harvest": {"day_stop_pct_of_target": "101"}},
        {"early": {"first_trades": -1}},
        {"early": {"cushion_frac": "0"}},
        {"early": {"until_profit_frac": "1.5"}},
        {"early": {"enabled": True}},
        {"early": {"risk_pct": "0.2"}},
        {"quality_day": {"trailing_days": 0}},
    ],
)
def test_invalid_config_rejected(patch):
    with pytest.raises(ValueError):
        FastEvalCfg.model_validate(patch)
