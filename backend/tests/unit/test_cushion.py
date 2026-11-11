"""D122 cushion level controls (pure) + config validators — every branch, tighten-only."""

from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from app.config import CushionCfg, DynamicTrailCfg, TrailStepCfg
from app.risk.cushion import (
    CushionLevels,
    cushion_block,
    cushion_contracts,
    cushion_k_minus,
    cushion_level,
    cushion_share,
)

LV = CushionLevels(D("0.75"), D("0.50"), D("0.25"), 1, D("0.25"), D("0.5"), 1)


def test_share_and_levels():
    assert cushion_share(D(24800), D(24000), D(1000)) == D("0.8")
    assert cushion_share(D(24800), D(24000), D(0)) == 0  # unknown distance → strictest
    assert [cushion_level(D(x), LV) for x in ("0.8", "0.75", "0.6", "0.5", "0.3", "0.25", "0.2", "-1")] == [
        "NORMAL", "NORMAL", "REDUCE", "REDUCE", "MINIMAL", "MINIMAL", "STOP", "STOP",
    ]  # fmt: skip


@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_contracts_never_increase(n):
    got = {lv: cushion_contracts(lv, n, LV) for lv in ("NORMAL", "REDUCE", "MINIMAL", "STOP")}  # type: ignore[misc]
    assert got == {"NORMAL": n, "REDUCE": max(1, n - 1), "MINIMAL": 1, "STOP": 0}
    assert all(v <= n for v in got.values())


def test_k_minus_per_level():
    assert [cushion_k_minus(x, LV) for x in ("NORMAL", "REDUCE", "MINIMAL", "STOP")] == [  # type: ignore[arg-type]
        D(0), D("0.25"), D("0.5"), D("0.5"),
    ]  # fmt: skip


def test_block_rules():
    assert cushion_block("STOP", 0, False, LV) == "CUSHION_STOP"
    assert cushion_block("NORMAL", 0, True, LV) == "CUSHION_STOP"  # STOP earlier this session: until next session
    assert cushion_block("MINIMAL", 1, False, LV) == "CUSHION_MAX_TRADES"
    assert cushion_block("MINIMAL", 0, False, LV) is None
    assert cushion_block("REDUCE", 5, False, LV) is None


def test_cushion_cfg_defaults_off_and_validators():
    c = CushionCfg()
    assert not any(getattr(c, k) for k in ("noise", "pm_fade", "ai_bias", "ai_duo", "order_flow"))
    with pytest.raises(ValidationError, match="minimal_min < reduce_min < normal_min"):
        CushionCfg(reduce_min=D("0.8"))
    with pytest.raises(ValidationError, match="minimal_k_minus"):
        CushionCfg(minimal_k_minus=D("0.1"))
    with pytest.raises(ValidationError):
        CushionCfg(normal_min=D("0.99"))


def test_dynamic_trail_cfg_validators():
    d = DynamicTrailCfg()
    assert not d.noise and d.activate_r == D(1) and [s.k for s in d.steps] == [D(2), D("1.5"), D(1)]
    s = TrailStepCfg
    bad = [
        [s(until_r=D(2), k=D(2))],  # no open-ended last step
        [s(until_r=None, k=D(2)), s(until_r=None, k=D(1))],  # open-ended twice
        [s(until_r=D(3), k=D(2)), s(until_r=D(2), k=D("1.5")), s(k=D(1))],  # not increasing
        [s(until_r=D("0.5"), k=D(2)), s(k=D(1))],  # below activate_r
        [s(until_r=D(2), k=D(1)), s(k=D(2))],  # k grows with profit (loosens)
        [s(until_r=D(2), k=D(5)), s(k=D(1))],  # k out of range
    ]
    for steps in bad:
        with pytest.raises(ValidationError, match=r"dynamic_trail\.steps"):
            DynamicTrailCfg(steps=steps)
    with pytest.raises(ValidationError, match="k_floor"):
        DynamicTrailCfg(k_floor=D("1.5"))
    with pytest.raises(ValidationError):
        DynamicTrailCfg(min_distance_ticks=1)
