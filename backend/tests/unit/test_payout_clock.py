from datetime import UTC, datetime
from decimal import Decimal as D

from app.phases.payout_clock import ET, next_check, payout_clock

KW = {
    "frequency": "weekly",
    "check_time": "Fri 17:05",
    "buffer": D(26100),
    "min_request": D(500),
    "live_trigger": D(6000),
}


def test_next_check_same_week_and_rollover():
    wed = datetime(2026, 11, 4, 15, 0, tzinfo=UTC)  # Wed 10:00 ET
    assert next_check(wed, "Fri 17:05") == datetime(2026, 11, 6, 17, 5, tzinfo=ET)
    fri_after = datetime(2026, 11, 6, 17, 6, tzinfo=ET)
    assert next_check(fri_after, "Fri 17:05") == datetime(2026, 11, 13, 17, 5, tzinfo=ET)


def test_funded_needs_more_and_live_trigger():
    now = datetime(2026, 11, 6, 22, 0, tzinfo=UTC)  # Fri 17:00 ET → 5 minutes
    c = payout_clock(stage="FUNDED", balance=D(26300), today_pnl=D(400), now=now, **KW)
    assert c.seconds_left == 300 and c.eligible == 0 and c.needed == D(300) and c.live_trigger_left == D(5600)
    c = payout_clock(stage="FUNDED", balance=D(26700), today_pnl=D(7000), now=now, **KW)
    assert c.eligible == D(600) and c.needed == 0 and c.live_trigger_left == 0


def test_live_and_on_demand():
    now = datetime(2026, 11, 6, 22, 0, tzinfo=UTC)
    c = payout_clock(stage="LIVE", balance=D(26100), today_pnl=D(0), now=now, **{**KW, "frequency": "on_demand"})
    assert c.next_check is None and c.seconds_left is None and c.live_trigger_left is None and c.needed == D(500)


def test_every_n_sessions_next_check():  # D65
    from app.phases.payout_clock import next_session_check

    thu = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)  # Thu 10:00 ET → today 17:05
    assert next_session_check(thu, "17:05") == datetime(2026, 11, 5, 17, 5, tzinfo=ET)
    fri_late = datetime(2026, 11, 6, 17, 6, tzinfo=ET)  # after Friday's check → Monday
    assert next_session_check(fri_late, "17:05") == datetime(2026, 11, 9, 17, 5, tzinfo=ET)
    c = payout_clock(
        stage="FUNDED", balance=D(26700), today_pnl=D(0), now=thu, **{**KW, "frequency": "every_n_sessions"}
    )
    assert c.next_check == datetime(2026, 11, 5, 17, 5, tzinfo=ET) and c.eligible == D(600)
