from decimal import Decimal as D

import pytest

from app.backtest.data import DataError, load_csv


def test_iso_and_dedupe_and_sort():
    csv = "ts_event,open,high,low,close,volume,symbol\n2026-01-05T14:31:00Z,2,3,1,2.5,7,MNQH6\n2026-01-05T14:30:00Z,1,2,1,2,5,MNQH6\n2026-01-05T14:30:00Z,1,2,1,2,5,MNQH6\n"
    b = load_csv(csv)
    assert [x.c for x in b] == [D(2), D("2.5")] and b[0].close_ms - b[0].open_ms == 60_000 and b[1].v == D(7)


def test_epoch_units_fixed_point_and_symbol_filter():
    ns = 1767623400000000000  # 2026-01-05T14:30:00Z
    csv = (
        "ts_event,open,high,low,close,symbol\n"
        f"{ns},20000000000000,20001000000000,19999000000000,20000500000000,MNQH6\n"
        f"{ns},1,1,1,1,ESH6\n"
    )
    [b] = load_csv(csv, symbol_contains="MNQ")
    assert b.open_ms == 1767623400000 and b.c == D("20000.5")
    for v in ("1767623400", "1767623400000", "1767623400000000"):
        assert load_csv(f"time,open,high,low,close\n{v},1,1,1,1\n")[0].open_ms == 1767623400000


def test_errors():
    with pytest.raises(DataError):
        load_csv("")
    with pytest.raises(DataError):
        load_csv("foo,open\n1,2\n")
    with pytest.raises(DataError):
        load_csv("time,open,high,low,close\n2026-01-05T14:30:00,1,1,1,1\n")  # no timezone
    with pytest.raises(DataError):
        load_csv("time,open,high,low,close\n1767623400,1,0.5,1,1\n")  # high < open
    with pytest.raises(DataError):
        load_csv("time,open,high,low,close\n")
