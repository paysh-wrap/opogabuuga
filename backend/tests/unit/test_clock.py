from datetime import UTC, date, datetime, timedelta

import pytest

from app.clock import FixedClock, in_window, parse_hhmm, session_date, to_et


def utc(*a):
    return datetime(*a, tzinfo=UTC)


def test_et_dst_transitions():
    assert to_et(utc(2026, 3, 6, 14, 30)).hour == 9  # EST (UTC-5)
    assert to_et(utc(2026, 3, 9, 13, 30)).hour == 9  # EDT (UTC-4) after Mar 8
    assert to_et(utc(2026, 11, 2, 14, 30)).hour == 9  # EST after Nov 1


def test_session_date_rolls_at_1800_et():
    assert session_date(utc(2026, 11, 5, 22, 59)) == date(2026, 11, 5)  # 17:59 ET
    assert session_date(utc(2026, 11, 5, 23, 0)) == date(2026, 11, 6)  # 18:00 ET → next session


def test_windows_d2():
    w = [(parse_hhmm("06:45"), parse_hhmm("11:30")), (parse_hhmm("13:30"), parse_hhmm("15:30"))]
    assert not in_window(utc(2026, 11, 5, 11, 44), w)  # 06:44 ET
    assert in_window(utc(2026, 11, 5, 11, 45), w)  # 06:45 ET
    assert not in_window(utc(2026, 11, 5, 16, 30), w)  # 11:30 ET (end exclusive)
    assert in_window(utc(2026, 7, 6, 10, 45), w)  # 06:45 EDT


def test_fixed_clock_requires_aware():
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 1, 1))
    c = FixedClock(utc(2026, 1, 1))
    c.advance(timedelta(minutes=5))
    assert c.now() == utc(2026, 1, 1, 0, 5)
