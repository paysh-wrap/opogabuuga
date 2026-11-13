from decimal import Decimal as D

from app.risk.lucid_scale import effective_dll


def test_base_when_no_scale_not_locked_or_no_base():
    assert effective_dll(D(600), None, True, D(26500), D(25000)) == D(600)
    assert effective_dll(D(600), D(60), False, D(26500), D(25000)) == D(600)
    assert effective_dll(None, D(60), True, D(26500), D(25000)) is None


def test_scaled_after_lock():
    assert effective_dll(D(600), D(60), True, D(26500), D(25000)) == D("900.00")
    assert effective_dll(D(600), D(60), True, D(24000), D(25000)) == D("0.00")  # never negative
