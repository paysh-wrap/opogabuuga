"""D63 automatic per-account size (pure, 100% coverage)."""

from decimal import Decimal as D

import pytest

from app.risk.strategy_sizing import SizeTier, auto_contracts, tier_for

T = [
    SizeTier(D(25000), D(1000), 1),
    SizeTier(D(50000), D(2000), 2, D("0.5"), 1),
    SizeTier(D(100000), D(3000), 2, D("0.3"), 1),
    SizeTier(D(150000), D(4500), 4, D("0.5"), 2),
]


def test_tier_by_account_size():
    assert tier_for(D(25000), T).contracts == 1
    assert tier_for(D(10000), T).account_size == D(25000)  # below the smallest row → smallest
    assert tier_for(D(75000), T).account_size == D(50000)
    assert tier_for(D(150000), list(reversed(T))).contracts == 4  # order in the file does not matter
    assert tier_for(D(300000), T).account_size == D(150000)
    with pytest.raises(ValueError):
        tier_for(D(25000), [])


def test_auto_contracts_with_drawdown_brake():
    assert auto_contracts(D(150000), D(4500), T).contracts == 4
    b = auto_contracts(D(150000), D(2249), T)  # cushion < 50% of $4,500
    assert b.contracts == 2 and b.braked and b.tier == D(150000)
    assert auto_contracts(D(150000), D(2250), T).contracts == 4  # exactly at the line → no brake
    assert auto_contracts(D(100000), D(899), T).contracts == 1 and auto_contracts(D(100000), D(900), T).contracts == 2
    assert auto_contracts(D(50000), D(999), T).contracts == 1
    assert auto_contracts(D(25000), D(100), T) == auto_contracts(D(25000), D(1000), T)  # no brake row → 1 always


def test_eval_growth_rows():  # D66
    g = [SizeTier(D(100000), D(3000), 2, D("0.3"), 1, D(1200), 4)]
    assert auto_contracts(D(100000), D(2399), g).contracts == 2  # < 2 × $1,200
    assert auto_contracts(D(100000), D(2400), g).contracts == 3
    assert auto_contracts(D(100000), D(3600), g).contracts == 4
    assert auto_contracts(D(100000), D(9000), g).contracts == 4  # max_contracts
    b = auto_contracts(D(100000), D(899), g)
    assert b.contracts == 1 and b.braked  # brake still applies on top


def test_eval_taper_sprint_then_protect():  # D69
    t = [SizeTier(D(25000), D(1000), 4, None, None, None, None, D("0.5"), 1)]
    assert auto_contracts(D(25000), D(1000), t, D(1)).contracts == 4  # nothing earned yet
    assert auto_contracts(D(25000), D(1000), t, D("0.5")).contracts == 4  # exactly half left → still big
    assert auto_contracts(D(25000), D(1600), t, D("0.49")).contracts == 1  # < 50% left → 1 micro
    assert auto_contracts(D(25000), D(1000), t, None).contracts == 4  # no target info (funded) → no taper
    both = [SizeTier(D(25000), D(1000), 4, D("0.5"), 2, None, None, D("0.5"), 1)]
    assert auto_contracts(D(25000), D(400), both, D("0.8")).contracts == 2  # brake still applies on top


def test_bias_size_d74() -> None:
    from app.risk.strategy_sizing import bias_size

    assert bias_size(2, 2, 1, 1) == 3  # agree: +1 (base 2 + 1 cap)
    assert bias_size(3, 2, 1, 1) == 3  # never above base + 1
    assert bias_size(1, 2, 1, 1) == 2  # braked size restored one step
    assert bias_size(2, 2, 1, -1) == 1  # disagree: -1
    assert bias_size(1, 2, -1, 1) == 1  # never below 1
    assert bias_size(2, 2, 1, 0) == 2  # no proven call: unchanged
    assert bias_size(2, 2, 0, 1) == 2


def test_plan_contracts_and_risk_cap_d115():
    from decimal import Decimal as Dd

    from app.risk.strategy_sizing import plan_contracts, risk_cap

    assert plan_contracts(5, Dd(150000), Dd(150000)) == 5  # the plan's own size
    assert plan_contracts(5, Dd(150000), Dd(200000)) == 5  # never more for a bigger account
    assert plan_contracts(5, Dd(150000), Dd(50000)) == 1  # 5 x 1/3 = 1 (rounded down)
    assert plan_contracts(5, Dd(150000), Dd(100000)) == 3
    assert plan_contracts(1, Dd(25000), Dd(10000)) == 1  # min 1
    assert plan_contracts(3, Dd(0), Dd(1)) == 3  # no plan size → unchanged
    assert risk_cap(None, None) is None
    assert risk_cap(Dd(600), None, Dd(500)) == Dd(500)
