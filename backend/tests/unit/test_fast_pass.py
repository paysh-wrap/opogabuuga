"""D156 "150K fast pass": pure size decision (EVAL + plan size only; cushion brake at <= $1,500; OFF = None)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.config import FastPassCfg, StrategyCfg, load_rules
from app.risk.fast_pass import FastPassSize, fast_pass_size, plan_fast_pass
from tests.conftest import REPO_ROOT

CFG = FastPassCfg(
    account_size=D(150000), noise_contracts=5, noise_stop_usd=D(100), candace_contracts=4, brake_inclusive=False,
    noise_steps=[{"cushion_usd": 2250, "contracts": 2}, {"cushion_usd": 1500, "contracts": 1}],
    candace_steps=[{"cushion_usd": 2250, "contracts": 2}, {"cushion_usd": 900, "contracts": 1}],
)  # fmt: skip
CFG25 = FastPassCfg(
    account_size=D(25000), noise_contracts=1, noise_stop_usd=D(75), candace_contracts=2, brake_inclusive=False,
    candace_steps=[{"cushion_usd": 500, "contracts": 1}],
)  # fmt: skip
CFG100 = FastPassCfg(
    account_size=D(100000), noise_contracts=2, noise_stop_usd=D(250), candace_contracts=4, brake_inclusive=False,
    noise_steps=[{"cushion_usd": 750, "contracts": 1}], candace_steps=[{"cushion_usd": 1500, "contracts": 1}],
)  # fmt: skip
OLD = FastPassCfg(
    account_size=D(150000), noise_contracts=5, noise_stop_usd=D(100), candace_contracts=4,
    brake_cushion_usd=D(1500), noise_brake_contracts=2, candace_brake_contracts=2,
)  # fmt: skip
K150 = D(150000)


@pytest.mark.parametrize(
    ("strategy", "cushion", "want"),
    [
        ("NOISE", D(4500), FastPassSize(5, D(100), False)),
        ("NOISE", D(2250), FastPassSize(5, D(100), False)),  # strict <
        ("NOISE", D("2249.99"), FastPassSize(2, D(100), True)),
        ("NOISE", D(1500), FastPassSize(2, D(100), True)),
        ("NOISE", D("1499.99"), FastPassSize(1, D(100), True)),  # smallest applicable step
        ("NOISE", D(-5), FastPassSize(1, D(100), True)),
        ("CANDACE_ICT", D(3000), FastPassSize(4, None, False)),
        ("CANDACE_ICT", D(2250), FastPassSize(4, None, False)),
        ("CANDACE_ICT", D("2249.99"), FastPassSize(2, None, True)),
        ("CANDACE_ICT", D(900), FastPassSize(2, None, True)),
        ("CANDACE_ICT", D("899.99"), FastPassSize(1, None, True)),
    ],
)
def test_size_and_brake(strategy, cushion, want):
    assert fast_pass_size(True, CFG, "EVAL", K150, strategy, cushion) == want


@pytest.mark.parametrize(
    ("enabled", "cfg", "stage", "size", "strategy"),
    [
        (False, CFG, "EVAL", K150, "NOISE"),  # OFF = today's sizing
        (True, None, "EVAL", K150, "NOISE"),  # plan file without the section → inert
        (True, CFG, "FUNDED", K150, "NOISE"),  # never FUNDED / LIVE (non-negotiable 10)
        (True, CFG, "LIVE", K150, "CANDACE_ICT"),
        (True, CFG, "EVAL", D(100000), "NOISE"),  # other account sizes untouched
        (True, CFG, "EVAL", D(25000), "CANDACE_ICT"),
        (True, CFG, "EVAL", K150, "GALA_PA"),  # other strategies untouched
        (True, CFG, "EVAL", K150, ""),
    ],
)
def test_not_applied(enabled, cfg, stage, size, strategy):
    assert fast_pass_size(enabled, cfg, stage, size, strategy, D(4000)) is None


def test_old_single_step_fields_convert():
    assert OLD.noise_steps[0].contracts == 2 and OLD.candace_steps[0].cushion_usd == D(1500)
    assert fast_pass_size(True, OLD, "EVAL", K150, "NOISE", D(1500)) == FastPassSize(2, D(100), True)  # inclusive
    assert fast_pass_size(True, OLD, "EVAL", K150, "NOISE", D("1500.01")) == FastPassSize(5, D(100), False)


def test_cfg_validation():
    steps = [{"cushion_usd": 100, "contracts": 9}]
    with pytest.raises(ValueError, match="tighten-only"):
        FastPassCfg.model_validate({**CFG.model_dump(), "candace_steps": steps})
    with pytest.raises(ValueError, match="tighten-only"):
        FastPassCfg.model_validate({**CFG.model_dump(), "noise_steps": steps})
    with pytest.raises(ValueError, match="higher cushion"):
        FastPassCfg.model_validate(
            {
                **CFG.model_dump(),
                "noise_steps": [{"cushion_usd": 100, "contracts": 2}, {"cushion_usd": 200, "contracts": 1}],
            }
        )
    for bad in (
        {"noise_contracts": 0}, {"noise_stop_usd": 0}, {"brake_cushion_usd": -1}, {"account_size": 0},
    ):  # fmt: skip
        with pytest.raises(ValueError):
            FastPassCfg.model_validate({**CFG.model_dump(), **bad})
    assert StrategyCfg().fast_pass_150k is False and StrategyCfg().fast_pass_150k_cfg is None


@pytest.mark.parametrize(
    ("cfg", "strategy", "cushion", "want"),
    [
        (CFG25, "NOISE", D(100), FastPassSize(1, D(75), False)),  # no NOISE brake
        (CFG25, "CANDACE_ICT", D(500), FastPassSize(2, None, False)),  # strictly below
        (CFG25, "CANDACE_ICT", D("499.99"), FastPassSize(1, None, True)),
        (CFG100, "NOISE", D(750), FastPassSize(2, D(250), False)),
        (CFG100, "NOISE", D("749.99"), FastPassSize(1, D(250), True)),
        (CFG100, "CANDACE_ICT", D(1500), FastPassSize(4, None, False)),
        (CFG100, "CANDACE_ICT", D("1499.99"), FastPassSize(1, None, True)),
    ],
)
def test_small_plans(cfg, strategy, cushion, want):
    assert fast_pass_size(True, cfg, "EVAL", cfg.account_size, strategy, cushion) == want
    assert fast_pass_size(True, cfg, "FUNDED", cfg.account_size, strategy, cushion) is None


def test_plan_fast_pass_picks_by_size():
    st = StrategyCfg(
        fast_pass_25k=True, fast_pass_25k_cfg=CFG25, fast_pass_100k_cfg=CFG100, fast_pass_150k=True,
        fast_pass_150k_cfg=CFG,
    )  # fmt: skip
    assert plan_fast_pass(st, D(25000)) == (True, CFG25)
    assert plan_fast_pass(st, D(100000)) == (False, CFG100)  # own switch off
    assert plan_fast_pass(st, D(150000)) == (True, CFG)
    assert plan_fast_pass(st, D(50000)) == (False, None)  # 50K: nothing
    assert StrategyCfg().fast_pass_25k is False and StrategyCfg().fast_pass_100k_cfg is None


def test_plan_files():
    """Only Pro 25K / 100K / 150K carry numbers (default OFF); every other plan omits them → inert."""
    want = {"lucid_pro_25k.yaml": CFG25, "lucid_pro_100k.yaml": CFG100, "lucid_pro_150k.yaml": CFG}
    for f in sorted((REPO_ROOT / "config" / "rules").glob("*.yaml")):
        st = load_rules(f).rules.strategy
        assert not (st.fast_pass_25k or st.fast_pass_100k or st.fast_pass_150k), f.name
        got = (st.fast_pass_25k_cfg, st.fast_pass_100k_cfg, st.fast_pass_150k_cfg)
        if f.name in want:
            assert [c for c in got if c is not None] == [want[f.name]], f.name
        else:
            assert got == (None, None, None), f.name


def test_ar_side_by_side_cap_is_half_of_noise_and_tighten_only():
    """D160: AR beside NOISE never above half the NOISE fast-pass size (min 1); no NOISE fast pass = unchanged."""
    from app.risk.fast_pass import ar_side_by_side, ar_side_cap

    assert ar_side_cap(3, None) == 3
    assert ar_side_cap(3, FastPassSize(4, D(100), False)) == 2
    assert ar_side_cap(1, FastPassSize(4, D(100), False)) == 1  # never raises
    assert ar_side_cap(2, FastPassSize(1, D(75), False)) == 1  # half of 1 → floor, at least 1
    st = load_rules(REPO_ROOT / "config" / "rules" / "lucid_pro_25k.yaml").rules.strategy
    on = st.model_copy(
        update={"order_flow": True, "order_flow_cfg": st.order_flow_cfg.model_copy(update={"ar_side_by_side": True})}
    )
    assert ar_side_by_side(on, None) and ar_side_by_side(on, {}) and not ar_side_by_side(on, {"zone": {}})
    assert not ar_side_by_side(st, None)  # default OFF
