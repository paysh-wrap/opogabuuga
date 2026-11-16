"""BRUNI risk overlays (F2 / F3 / F5): pure, tighten-only."""

from decimal import Decimal as D

from app.risk.bruni_overlays import autocorr_multiplier, autocorr_strength, shield_account

CUT = {"WEAK": D("0.75"), "SOLID": D("0.5"), "STRONG": D("0.25")}


def test_f2_strength_table():
    assert autocorr_strength(D(50), D(51)) == (0, "NONE")
    assert autocorr_strength(D(46), D(50)) == (1, "WEAK")
    assert autocorr_strength(D(55), D(50)) == (-1, "SOLID")
    assert autocorr_strength(D(42), D(50)) == (1, "STRONG")
    assert autocorr_strength(D(40), D(50)) == (1, "EXTREME")


def test_f3_tighten_only():
    assert autocorr_multiplier(D(44), D(50), False, CUT) == D("0.5")  # positive, after a loss → smaller
    assert autocorr_multiplier(D(44), D(50), True, CUT) == 1  # after a win: never raised
    assert autocorr_multiplier(D(54), D(50), True, CUT) == D("0.75")  # negative, after a win → smaller
    assert autocorr_multiplier(D(40), D(50), False, CUT) == 1  # extreme = suspect
    assert autocorr_multiplier(D(50), D(50), False, CUT) == 1
    assert autocorr_multiplier(None, D(50), False, CUT) == 1
    assert autocorr_multiplier(D(44), D(50), False, {"SOLID": D(3)}) == 1  # a cut above 1 is clamped


def test_f5_one_account_per_week():
    assert shield_account([3, 1, 2], 10, None) == 2  # rotate: sorted [1,2,3], week 10 % 3 = 1
    assert shield_account([1, 2], 10, 2) == 2
    assert shield_account([1, 2], 10, 5) is None  # this week's account is not available → no trade
    assert shield_account([], 1, None) is None
