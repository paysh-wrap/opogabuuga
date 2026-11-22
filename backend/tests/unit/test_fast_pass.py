"""D156 "150K fast pass": pure size decision (EVAL + plan size only; cushion brake at <= $1,500; OFF = None)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.config import FastPass150kCfg, StrategyCfg, load_rules
from app.risk.fast_pass import FastPassSize, fast_pass_size
from tests.conftest import REPO_ROOT

CFG = FastPass150kCfg(
    account_size=D(150000), noise_contracts=4, noise_stop_usd=D(100), candace_contracts=3,
    brake_cushion_usd=D(1500), brake_contracts=2,
)  # fmt: skip
K150 = D(150000)


@pytest.mark.parametrize(
    ("strategy", "cushion", "want"),
    [
        ("NOISE", D(4500), FastPassSize(4, D(100), False)),
        ("NOISE", D("1500.01"), FastPassSize(4, D(100), False)),
        ("NOISE", D(1500), FastPassSize(2, D(100), True)),  # at the brake → braked
        ("NOISE", D(200), FastPassSize(2, D(100), True)),
        ("CANDACE_ICT", D(3000), FastPassSize(3, None, False)),
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


def test_cfg_validation():
    with pytest.raises(ValueError, match="tighten-only"):
        FastPass150kCfg.model_validate({**CFG.model_dump(), "brake_contracts": 4})
    for bad in ({"noise_contracts": 0}, {"noise_stop_usd": 0}, {"brake_cushion_usd": -1}, {"account_size": 0}):
        with pytest.raises(ValueError):
            FastPass150kCfg.model_validate({**CFG.model_dump(), **bad})
    assert StrategyCfg().fast_pass_150k is False and StrategyCfg().fast_pass_150k_cfg is None


def test_plan_files():
    """Only the Pro 150K plan carries the numbers (default OFF); every other plan omits them → inert."""
    for f in sorted((REPO_ROOT / "config" / "rules").glob("*.yaml")):
        st = load_rules(f).rules.strategy
        assert st.fast_pass_150k is False, f.name
        if f.name == "lucid_pro_150k.yaml":
            assert st.fast_pass_150k_cfg == CFG
        else:
            assert st.fast_pass_150k_cfg is None, f.name
