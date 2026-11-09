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
