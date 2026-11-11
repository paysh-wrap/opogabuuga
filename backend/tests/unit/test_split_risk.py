"""D92: split-risk button - pure functions and the pre-trade budget check (tighten-only)."""

from decimal import Decimal as D

import pytest

from app.config import StrategyCfg
from app.risk.split_risk import side_budget_left, split_active, split_budget, split_contracts
from tests.unit.test_risk_phase4 import NOISE_PLAN, _fixed, run


@pytest.mark.parametrize(
    "n,expected", [(0, 0), (1, 1), (2, 1), (3, 1), (4, 2), (5, 2), (6, 3), (7, 3)]
)  # half, rounded DOWN, never below 1 micro
def test_split_contracts_half_rounded_down_min_one(n, expected):
    assert split_contracts(n, D("0.5")) == expected


def test_split_never_increases_the_size():
    for n in range(0, 12):
        assert split_contracts(n, D("0.5")) <= max(n, 0) or n == 0
        assert split_contracts(n, D("0.5")) <= max(n, 1)


def test_active_only_when_button_and_both_sides_are_on():
    assert split_active(True, True, True)
    assert not split_active(False, True, True)
    assert not split_active(True, False, True) and not split_active(True, True, False)


def test_budget_is_half_of_the_dll_and_none_without_a_dll():
    assert split_budget(D(600), D("0.5")) == D("300.00") and split_budget(None, D("0.5")) is None
    assert split_budget(D(1500), D("0.5")) == D("750.00")


def test_budget_left_losses_and_open_risk_use_it_profits_do_not_add_room():
    b = D(300)
    assert side_budget_left(b, D(0), D(0)) == D(300)
    assert side_budget_left(b, D(-120), D(0)) == D(180)
    assert side_budget_left(b, D(-120), D(50)) == D(130)
    assert side_budget_left(b, D(200), D(0)) == D(300)  # a profit never adds room
    assert side_budget_left(b, D(-400), D(0)) == D(-100)  # over budget stays negative


def test_share_comes_from_config_and_is_bounded():
    assert StrategyCfg().noise_ai_split is False  # default OFF
    assert StrategyCfg().noise_ai_split_share == D("0.5")
    assert StrategyCfg(noise_ai_split_share=D("0.25")).noise_ai_split_share == D("0.25")
    for bad in (D(0), D("0.51"), D(1)):
        with pytest.raises(ValueError):
            StrategyCfg(noise_ai_split_share=bad)


def test_pretrade_blocks_a_trade_that_does_not_fit_this_sides_budget_and_allows_one_that_does():
    # NOISE_PLAN, 1 micro: worst case $402 + $40 margin = $442 (existing fixed-size test)
    ok = run(plan=NOISE_PLAN, lim=_fixed(side_budget_left=D(442)), consistency=None, acct_dll=None)
    assert ok.ok and any(c["check"] == "split_budget" and c["ok"] for c in ok.checks)
    r = run(plan=NOISE_PLAN, lim=_fixed(side_budget_left=D(441)), consistency=None, acct_dll=None)
    assert not r.ok and r.reason == "SPLIT_BUDGET_EXCEEDED"
    r = run(plan=NOISE_PLAN, lim=_fixed(side_budget_left=D(-1)), consistency=None, acct_dll=None)
    assert not r.ok and r.reason == "SPLIT_BUDGET_EXCEEDED"
    # no split → no such check, behaviour unchanged
    base = run(plan=NOISE_PLAN, lim=_fixed(), consistency=None, acct_dll=None)
    assert base.ok and not any(c["check"] == "split_budget" for c in base.checks)
