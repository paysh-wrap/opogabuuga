"""§21 exact plan cases (MNQ tick 0.25, buffer 4 ticks, min_stop_ticks 20) + D7 1:1 mode."""

from decimal import Decimal as D

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.engine.trade_plan import (
    Direction,
    Skip,
    TradePlan,
    build_one_to_one_plan,
    build_trade_plan,
    fee_cover_ticks,
    rebuild_after_fill,
    round_to_tick,
)

T = D("0.25")
L, S = Direction.LONG, Direction.SHORT


def plan(entry, invalid, t2, d=L):
    return build_trade_plan(d, D(entry), D(invalid), D(t2), T, 4, 20)


def test_spec_3_5r_capped_at_3r():
    p = plan("20000", "19981", "20070")
    assert isinstance(p, TradePlan)
    assert (p.stop, p.risk_pts, p.take_profit, p.rr) == (D(19980), D(20), D(20060), D(3))


def test_spec_t2_at_2_5r_used_as_tp():
    p = plan("20000", "19981", "20050")
    assert (p.take_profit, p.rr) == (D(20050), D("2.5"))


def test_spec_1_75r_skips():
    assert plan("20000", "19981", "20035") == Skip("RR_BELOW_MIN", "T2 is 1.75R")


def test_spec_stop_too_tight():
    r = plan("20000", "19997", "20100")  # stop 19996 → 4 pts = 16 ticks
    assert isinstance(r, Skip) and r.reason == "STOP_TOO_TIGHT"


def test_stop_invalid_and_short_mirror():
    assert plan("20000", "20010", "20100").reason == "STOP_INVALID"  # invalid above a long entry
    p = plan("20000", "20019", "19930", d=S)
    assert (p.stop, p.risk_pts, p.take_profit, p.rr) == (D(20020), D(20), D(19940), D(3))


def test_rounding_directions():
    assert round_to_tick(D("19980.1"), T, away_from=D(20000)) == D("19980")  # stop moves away from entry
    assert round_to_tick(D("20060.1"), T, toward=D(20000)) == D("20060")  # TP moves toward entry
    assert round_to_tick(D("19939.9"), T, toward=D(20000)) == D("19940")
    assert round_to_tick(D("20019.9"), T, away_from=D(20000)) == D("20020")
    assert round_to_tick(D("20000.125"), T) == D("20000.25")
    assert round_to_tick(D("20000.50"), T, toward=D(1)) == D("20000.50")


def test_fee_cover_ticks():
    assert fee_cover_ticks(D("1.50"), D("0.50")) == 3  # spec placeholder → BE 20000.75
    assert fee_cover_ticks(D("1.00"), D("0.50")) == 2  # Lucid MNQ
    assert fee_cover_ticks(D("1.60"), D("1.00")) == 2  # Lucid MGC


def test_rebuild_after_fill():
    p = plan("20000", "19981", "20070")
    ok = rebuild_after_fill(p, D("20002"), D(19981), D(20070), T, 4, 20, D(2), D(3))
    assert isinstance(ok, TradePlan) and ok.entry == D(20002) and ok.risk_pts == D(22)
    bad = rebuild_after_fill(p, D("20030"), D(19981), D(20070), T, 4, 20, D(2), D(3))
    assert isinstance(bad, Skip) and bad.reason == "RR_INVALID_AFTER_FILL"


def test_one_to_one_plan():
    p = build_one_to_one_plan(L, D(20000), D(19981), D(20070), T, 4, 20, D("0.75"), D("0.30"), 2)
    assert (p.stop, p.take_profit, p.rr, p.mode) == (D(19980), D(20020), D(1), "ONE_TO_ONE")
    assert p.partial_price == D(20015)  # 75% of 20 pts
    assert p.breakeven_price == D("20000.50")  # 2 fee ticks
    assert p.lock_price == D(20006)  # +0.30R = 6 pts
    s = build_one_to_one_plan(S, D(20000), D(20019), D(19900), T, 4, 20, D("0.75"), D("0.30"), 2)
    assert (s.take_profit, s.partial_price, s.breakeven_price, s.lock_price) == (
        D(19980),
        D(19985),
        D("19999.50"),
        D(19994),
    )
    assert (
        build_one_to_one_plan(L, D(20000), D(19981), D(20010), T, 4, 20, D("0.75"), D("0.3"), 2).reason
        == "RR_BELOW_MIN"
    )


prices = st.integers(min_value=40000, max_value=120000).map(lambda n: D(n) * T)


@given(entry=prices, inv_off=st.integers(1, 400), t2_off=st.integers(1, 2000), long=st.booleans())
def test_property_plan_always_within_2_to_3r_on_tick_grid(entry, inv_off, t2_off, long):
    d = L if long else S
    invalid = entry - d.sign * inv_off * T
    t2 = entry + d.sign * t2_off * T
    p = build_trade_plan(d, entry, invalid, t2, T, 4, 20)
    if isinstance(p, TradePlan):
        assert D(2) <= p.rr <= D(3)
        for x in (p.stop, p.take_profit):
            assert x / T == (x / T).to_integral_value()
        assert (p.entry - p.stop) * d.sign >= 20 * T
        assert (p.take_profit - p.entry) * d.sign <= (t2 - entry) * d.sign  # never beyond the model target


@given(entry=prices, inv_off=st.integers(1, 400), t2_off=st.integers(1, 2000), long=st.booleans())
def test_property_one_to_one_exact_1r_and_lock_between_be_and_partial(entry, inv_off, t2_off, long):
    d = L if long else S
    p = build_one_to_one_plan(
        d, entry, entry - d.sign * inv_off * T, entry + d.sign * t2_off * T, T, 4, 20, D("0.75"), D("0.30"), 2
    )
    if isinstance(p, TradePlan):
        assert p.rr == 1 and (p.take_profit - p.entry) * d.sign == p.risk_pts
        s = d.sign
        assert (p.breakeven_price - p.entry) * s > 0
        assert (p.lock_price - p.breakeven_price) * s >= 0
        assert (p.partial_price - p.lock_price) * s >= 0


@pytest.mark.parametrize("fn", [build_trade_plan])
def test_no_float_inputs_accepted(fn):
    with pytest.raises(TypeError):
        fn(L, 20000.0, D(19981), D(20070), T, 4, 20)  # floats must never reach plan math
