"""D98 footprint / delta / CVD / volume profile (pure, Decimal)."""

from decimal import Decimal as D

import pytest

from app.engine import footprint as FP

R = D("1")


def bar(t, o, h, l, c, v, ticks=None):  # noqa: E741
    return FP.BarIn(t, D(o), D(h), D(l), D(c), D(v), ticks)


def test_row_of_floors_to_row():
    assert FP.row_of(D("100.75"), D(1)) == D(100)
    assert FP.row_of(D("-0.5"), D(1)) == D(-1)


def test_estimated_levels_close_location_and_even_spread():
    fp = FP.footprint([bar(0, 100, 103, 100, 103, 40)], R)
    b = fp[0]
    assert b.source == "estimated"
    assert [x.price for x in b.levels] == [D(100), D(101), D(102), D(103)]
    assert all(x.ask == D(10) and x.bid == D(0) for x in b.levels)  # closed on the high → all buying
    assert b.delta == D(40) and b.cvd == D(40)


def test_mid_close_splits_and_cvd_accumulates():
    fp = FP.footprint([bar(0, 100, 102, 100, 101, 30), bar(60_000, 101, 102, 100, 100, 30)], R)
    assert fp[0].levels[0].ask == D(5) and fp[0].levels[0].bid == D(5)
    assert fp[0].delta == D(0)
    assert fp[1].delta == D(-30) and fp[1].cvd == D(-30)


def test_doji_uses_tick_rule():
    fp = FP.footprint(
        [bar(0, 10, 10, 10, 10, 4), bar(1, 11, 11, 11, 11, 4), bar(2, 9, 9, 9, 9, 4), bar(3, 9, 9, 9, 9, 4)], R
    )
    assert fp[0].delta == D(0)  # no previous close → half/half
    assert fp[1].delta == D(4)  # up-tick
    assert fp[2].delta == D(-4)  # down-tick
    assert fp[3].delta == D(0)  # unchanged


def test_real_tick_levels_are_used_as_is():
    ticks = (
        FP.TickLevel(D("100.25"), D(3), D(1)),
        FP.TickLevel(D("100.75"), D(1), D(5)),
        FP.TickLevel(D(101), D(2), D(0)),
    )
    b = FP.footprint([bar(0, 100, 101, 100, 101, 12, ticks)], R)[0]
    assert b.source == "tick"
    assert b.levels == (FP.Level(D(100), D(4), D(6)), FP.Level(D(101), D(2), D(0)))
    assert b.delta == D(0)


def test_bad_row_refused():
    with pytest.raises(ValueError):
        FP.footprint([], D(0))


def test_volume_profile_poc_value_area_nodes():
    # rows 100..108 with a peak at 104, a trough at 102
    vols = [10, 10, 1, 30, 80, 30, 10, 5, 4]
    fp = [
        FP.FootprintBar(
            0,
            D(0),
            D(0),
            D(0),
            D(0),
            D(0),
            tuple(FP.Level(D(100 + i), D(0), D(v)) for i, v in enumerate(vols)),
            D(0),
            D(0),
            "estimated",
        )
    ]
    p = FP.volume_profile(fp, R)
    assert p.poc == D(104)
    total = sum(vols)
    inside = sum(v for i, v in enumerate(vols) if p.val <= D(100 + i) <= p.vah)
    assert inside >= total * 0.7
    assert (p.val, p.vah) == (D(103), D(105))
    assert p.hvn == (D(104),)
    assert p.lvn == (D(102),)
    assert len(p.rows) == 9


def test_value_area_expands_down_when_lower_is_bigger_and_fills_gaps():
    fp = [
        FP.FootprintBar(
            0,
            D(0),
            D(0),
            D(0),
            D(0),
            D(0),
            (FP.Level(D(100), D(0), D(50)), FP.Level(D(102), D(0), D(60)), FP.Level(D(103), D(0), D(1))),
            D(0),
            D(0),
            "estimated",
        )
    ]
    p = FP.volume_profile(fp, R)
    assert p.poc == D(102)
    assert dict(p.rows)[D(101)] == D(0)
    assert p.val == D(100)


def test_empty_profile():
    p = FP.volume_profile([], R)
    assert p.poc is None and p.rows == ()


def test_zone_vs_prior_value():
    prior = FP.Profile((), D(100), D(105), D(95))
    assert FP.zone(D(106), prior) == "premium"
    assert FP.zone(D(94), prior) == "discount"
    assert FP.zone(D(100), prior) == "value"
    assert FP.zone(D(100), None) == "unknown"
    assert FP.zone(D(100), FP.Profile((), None, None, None)) == "unknown"


def test_round_levels():
    assert FP.round_levels(D(20012), D(20160), D(50)) == (D(20050), D(20100), D(20150))
    assert FP.round_levels(D(20050), D(20050), D(50)) == (D(20050),)
    assert FP.round_levels(D(1), D(0), D(50)) == ()
    assert FP.round_levels(D(1), D(2), D(0)) == ()
