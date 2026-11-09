"""D55 OPEN_DRIVE (paper-only button): pure setup rules."""

from decimal import Decimal as D

from app.engine.open_drive import avg_range, setup
from app.engine.trade_plan import Direction

KW = {
    "frac": D("0.35"),
    "entry_retrace": D("0.382"),
    "stop_retrace": D("0.786"),
    "target_frac": D(1),
    "tick": D("0.25"),
}


def test_avg_range_needs_history():
    assert avg_range([D(100)] * 9, 14, 10) is None
    assert avg_range([D(50)] * 10 + [D(100)] * 14, 14, 10) == D(100)


def test_long_drive_setup():
    s = setup(rth_open=D(20000), drive_high=D(20100), drive_low=D(19990), close_0959=D(20090), avg_rng=D(200), **KW)
    assert s is not None and s.direction is Direction.LONG
    assert s.entry == D("20061.75")  # 20100 − 0.382·100 = 20061.8 → rounded toward the open
    assert s.stop == D("20021.25")  # 20100 − 78.6 = 20021.4 → rounded away from the entry
    assert s.take_profit == D(20100) and s.rr < D(1)  # back to the drive high, R:R ≈ 0.95


def test_short_drive_and_filters():
    s = setup(rth_open=D(20000), drive_high=D(20010), drive_low=D(19900), close_0959=D(19920), avg_rng=D(200), **KW)
    assert s is not None and s.direction is Direction.SHORT and s.stop > s.entry > s.take_profit
    assert (
        setup(rth_open=D(20000), drive_high=D(20050), drive_low=D(19990), close_0959=D(20040), avg_rng=D(200), **KW)
        is None
    )
    assert (
        setup(rth_open=D(20000), drive_high=D(20100), drive_low=D(19990), close_0959=D(20090), avg_rng=None, **KW)
        is None
    )
    assert (
        setup(rth_open=D(20000), drive_high=D(20000), drive_low=D(20000), close_0959=D(20000), avg_rng=D(0), **KW)
        is None
    )
    # tiny drive leg → risk below 4 ticks → no trade
    assert (
        setup(rth_open=D(20000), drive_high=D(20001), drive_low=D(19999), close_0959=D(20001), avg_rng=D(2), **KW)
        is None
    )
