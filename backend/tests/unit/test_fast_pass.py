"""D156 "150K fast pass": pure size decision (EVAL + plan size only; cushion brake at <= $1,500; OFF = None)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.config import FastPassCfg, StrategyCfg, load_rules
from app.risk.fast_pass import (
    FastPassSize,
    fast_pass_day_locked,
    fast_pass_lock,
    fast_pass_size,
    plan_fast_pass,
)
from tests.conftest import REPO_ROOT

CFG = FastPassCfg(
    account_size=D(150000), noise_contracts=5, noise_stop_usd=D(100), candace_contracts=4,
    brake_cushion_usd=D(1500), noise_brake_contracts=2, candace_brake_contracts=2,
)  # fmt: skip
CFG25 = FastPassCfg(
    account_size=D(25000), noise_contracts=1, noise_stop_usd=D(75), candace_contracts=2,
    brake_cushion_usd=D(333), brake_inclusive=False, candace_brake_contracts=1,
)  # fmt: skip
CFG100 = FastPassCfg(
    account_size=D(100000), noise_contracts=2, noise_stop_usd=D(250), candace_contracts=4, brake_inclusive=False,
    noise_steps=[{"cushion_usd": 750, "contracts": 1}], candace_steps=[{"cushion_usd": 1500, "contracts": 1}],
)  # fmt: skip
CFG100_NEW = FastPassCfg(  # D162 pass70 row N3@$100 [1000>2] C3 [600>2] dl0.5
    account_size=D(100000), noise_contracts=3, noise_stop_usd=D(100), candace_contracts=3, brake_inclusive=False,
    noise_steps=[{"cushion_usd": 1000, "contracts": 2}], candace_steps=[{"cushion_usd": 600, "contracts": 2}],
    day_lock_pct=D("0.5"),
)  # fmt: skip
CFG150_NEW = FastPassCfg(  # D162 pass70 row N5[2250>2,1500>1] C5[2700>4,1500>1] grow500 dl0.7
    account_size=D(150000), noise_contracts=5, noise_stop_usd=D(100), candace_contracts=5, brake_inclusive=False,
    noise_steps=[{"cushion_usd": 2250, "contracts": 2}, {"cushion_usd": 1500, "contracts": 1}],
    candace_steps=[{"cushion_usd": 2700, "contracts": 4}, {"cushion_usd": 1500, "contracts": 1}],
    noise_grow_per=D(500), noise_max_contracts=6, day_lock_pct=D("0.7"),
)  # fmt: skip
CFG50 = FastPassCfg(  # D162 pass70 62 %-floor row N2@$75 [667>1] C4 [1000>3] dl0.5 lock80
    account_size=D(50000), noise_contracts=2, noise_stop_usd=D(75), candace_contracts=4, brake_inclusive=False,
    noise_steps=[{"cushion_usd": 667, "contracts": 1}], candace_steps=[{"cushion_usd": 1000, "contracts": 3}],
    day_lock_pct=D("0.5"), noise_lock_trigger_pts=D(80),
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
        ("NOISE", D("1500.01"), FastPassSize(5, D(100), False)),
        ("NOISE", D(1500), FastPassSize(2, D(100), True)),  # at the brake -> braked (inclusive)
        ("NOISE", D(200), FastPassSize(2, D(100), True)),
        ("CANDACE_ICT", D(3000), FastPassSize(4, None, False)),
        ("CANDACE_ICT", D(1500), FastPassSize(2, None, True)),
        ("CANDACE_ICT", D(-5), FastPassSize(2, None, True)),
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
        (CFG25, "NOISE", D(100), FastPassSize(1, D(75), False)),  # no NOISE brake: stays 1
        (CFG25, "NOISE", D(900), FastPassSize(1, D(75), False)),
        (CFG25, "CANDACE_ICT", D(900), FastPassSize(2, None, False)),
        (CFG25, "CANDACE_ICT", D(333), FastPassSize(2, None, False)),  # strictly below
        (CFG25, "CANDACE_ICT", D("332.99"), FastPassSize(1, None, True)),
        (CFG100, "NOISE", D(750), FastPassSize(2, D(250), False)),  # D161: per-strategy steps
        (CFG100, "NOISE", D("749.99"), FastPassSize(1, D(250), True)),
        (CFG100, "NOISE", D(1000), FastPassSize(2, D(250), False)),  # NOISE step is 750, not CANDACE's 1500
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
    want = {
        "lucid_pro_25k.yaml": CFG25, "lucid_pro_50k.yaml": CFG50, "lucid_pro_100k.yaml": CFG100_NEW,
        "lucid_pro_150k.yaml": CFG150_NEW,
    }  # fmt: skip
    for f in sorted((REPO_ROOT / "config" / "rules").glob("*.yaml")):
        st = load_rules(f).rules.strategy
        assert not (st.fast_pass_25k or st.fast_pass_50k or st.fast_pass_100k or st.fast_pass_150k), f.name
        got = (st.fast_pass_25k_cfg, st.fast_pass_50k_cfg, st.fast_pass_100k_cfg, st.fast_pass_150k_cfg)
        if f.name in want:
            assert [c for c in got if c is not None] == [want[f.name]], f.name
        else:
            assert got == (None, None, None, None), f.name


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


@pytest.mark.parametrize(
    ("cfg", "strategy", "cushion", "want"),
    [
        # 150K: grow +1 per $500 beyond the first (cap 6), NOISE steps strictly below 2,250 / 1,500
        (CFG150_NEW, "NOISE", D(4500), FastPassSize(6, D(100), False)),  # grown to the cap
        (CFG150_NEW, "NOISE", D(2250), FastPassSize(6, D(100), False)),  # 2250 // 500 - 1 = 3 -> 5 + 3 -> cap 6
        (CFG150_NEW, "NOISE", D("2249.99"), FastPassSize(2, D(100), True)),
        (CFG150_NEW, "NOISE", D(1500), FastPassSize(2, D(100), True)),
        (CFG150_NEW, "NOISE", D("1499.99"), FastPassSize(1, D(100), True)),
        (CFG150_NEW, "CANDACE_ICT", D(2700), FastPassSize(5, None, False)),
        (CFG150_NEW, "CANDACE_ICT", D("2699.99"), FastPassSize(4, None, True)),
        (CFG150_NEW, "CANDACE_ICT", D(1500), FastPassSize(4, None, True)),
        (CFG150_NEW, "CANDACE_ICT", D("1499.99"), FastPassSize(1, None, True)),
        # 100K
        (CFG100_NEW, "NOISE", D(1000), FastPassSize(3, D(100), False)),
        (CFG100_NEW, "NOISE", D("999.99"), FastPassSize(2, D(100), True)),
        (CFG100_NEW, "CANDACE_ICT", D(600), FastPassSize(3, None, False)),
        (CFG100_NEW, "CANDACE_ICT", D("599.99"), FastPassSize(2, None, True)),
        # 50K
        (CFG50, "NOISE", D(667), FastPassSize(2, D(75), False)),
        (CFG50, "NOISE", D("666.99"), FastPassSize(1, D(75), True)),
        (CFG50, "CANDACE_ICT", D(1000), FastPassSize(4, None, False)),
        (CFG50, "CANDACE_ICT", D("999.99"), FastPassSize(3, None, True)),
    ],
)
def test_d162_rows(cfg, strategy, cushion, want):
    assert fast_pass_size(True, cfg, "EVAL", cfg.account_size, strategy, cushion) == want


def test_grow_and_day_lock_and_lock_trigger():
    cfg = CFG150_NEW.model_copy(update={"noise_steps": (), "noise_max_contracts": 8})  # no brake: pure grow
    got = [
        fast_pass_size(True, cfg, "EVAL", K150, "NOISE", D(c)).contracts
        for c in (400, 999, 1000, 1499, 1500, 2000, 9000)
    ]
    assert got == [5, 5, 6, 6, 7, 8, 8]  # extra = max(0, cushion // 500 - 1), capped at noise_max_contracts
    assert fast_pass_size(True, CFG100_NEW, "EVAL", D(100000), "NOISE", D(9000)).contracts == 3  # no grow configured
    # day lock: only ever skips, from the remaining target (0.7 x 1,000 = 700; 0.5 x 1,000 = 500)
    assert fast_pass_day_locked(CFG150_NEW, D(700), D(1000)) and not fast_pass_day_locked(CFG150_NEW, D(699), D(1000))
    assert fast_pass_day_locked(CFG50, D(500), D(1000)) and not fast_pass_day_locked(CFG50, D(499), D(1000))
    assert not fast_pass_day_locked(CFG50, D(0), D(1000)) and not fast_pass_day_locked(CFG50, D(10), D(0))
    assert not fast_pass_day_locked(CFG, D(900), D(1000)) and not fast_pass_day_locked(None, D(900), D(1000))
    # NOISE lock trigger only where configured; no lock configured at all -> none
    assert fast_pass_lock(CFG50, (D(100), D(10))) == (D(80), D(10))
    assert fast_pass_lock(CFG50, None) is None
    assert fast_pass_lock(CFG, (D(100), D(10))) == (D(100), D(10)) and fast_pass_lock(None, (D(100), D(10))) == (
        D(100),
        D(10),
    )


def test_d162_cfg_validation():
    for bad in (
        {"noise_grow_per": None},
        {"noise_max_contracts": None},
        {"noise_max_contracts": 4},
        {"day_lock_pct": 1.5},
    ):
        with pytest.raises(ValueError):
            FastPassCfg.model_validate({**CFG150_NEW.model_dump(), **bad})


def test_plan_fast_pass_50k():
    st = StrategyCfg(fast_pass_50k=True, fast_pass_50k_cfg=CFG50)
    assert plan_fast_pass(st, D(50000)) == (True, CFG50)


def test_d163_candace_grow():
    cfg = CFG150_NEW.model_copy(
        update={"candace_steps": (), "candace_grow_per": D(1500), "candace_max_contracts": 6}
    )
    got = [fast_pass_size(True, cfg, "EVAL", K150, "CANDACE_ICT", D(c)).contracts for c in (0, 2999, 3000, 9000)]
    assert got == [5, 5, 6, 6]  # extra = cushion // 1500 - 1 (first +1 at $3,000), capped at 6
    # steps still cap the grown size (tighten-only)
    capped = CFG150_NEW.model_copy(update={"candace_grow_per": D(1500), "candace_max_contracts": 6})
    assert fast_pass_size(True, capped, "EVAL", K150, "CANDACE_ICT", D(1400)).contracts == 1
    assert fast_pass_size(True, capped, "EVAL", K150, "CANDACE_ICT", D(2600)).contracts == 4
    # inert default
    assert fast_pass_size(True, CFG150_NEW, "EVAL", K150, "CANDACE_ICT", D(9000)).contracts == 5


def test_d163_candace_grow_validation():
    for bad in ({"candace_grow_per": D(1500)}, {"candace_max_contracts": 6}, {"candace_grow_per": D(1500), "candace_max_contracts": 4}):
        with pytest.raises(ValueError):
            FastPassCfg.model_validate({**CFG150_NEW.model_dump(), **bad})
