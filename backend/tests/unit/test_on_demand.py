from datetime import time
from decimal import Decimal as D

import pytest

from app.phases import on_demand as od

BASE = dict(
    stage="FUNDED", plan="lucid_pro_50k", dll_enabled=True, hedging_violation=False, now_et=time(11, 0), open_payout=False,
    requested_this_session=False, payouts_done=0, max_payouts=5, balance=D(54000), session_profit=D(900),
    prior_day_profits=[D(800), D(700)], buffer=D(52100), min_request=D(500), min_cycle_profit=D(500),
    min_profitable_days=3, cap_first=D(2000), cap_next=D(2500), consistency_pct=D(40), split=D("0.9"),
)


def offer(**kw):
    return od.on_demand_offer(**{**BASE, **kw})


def test_window():
    assert od.in_session(time(18, 0)) and od.in_session(time(3, 0)) and od.in_session(time(15, 44))
    assert not od.in_session(time(15, 45)) and not od.in_session(time(17, 59))


def test_available_amount_is_limited_by_session_profit_cap_and_buffer():
    o = offer()
    assert o.available and o.amount == D(900) and o.net == D(810) and o.limited_by == "session_profit" and o.reason == "OK"
    o = offer(session_profit=D(900), prior_day_profits=[D(3000), D(3000)], consistency_pct=None, cap_first=D(600), balance=D(60000))
    assert o.amount == D(600) and o.limited_by == "cap"
    o = offer(balance=D(52800), prior_day_profits=[D(800), D(700)])
    assert o.amount == D(700) and o.limited_by == "buffer"
    assert offer(payouts_done=1, session_profit=D(2400), prior_day_profits=[D(2000), D(2000)], balance=D(70000)).amount == D(2400)
    assert offer(payouts_done=1, session_profit=D(3000), prior_day_profits=[D(2000), D(3000)], balance=D(70000)).limited_by == "cap"


@pytest.mark.parametrize(
    ("kw", "why"),
    [
        ({"stage": "LIVE"}, "NOT_FUNDED"),
        ({"stage": "EVAL"}, "NOT_FUNDED"),
        ({"plan": "lucid_flex_50k"}, "NOT_LUCIDPRO"),
        ({"dll_enabled": False}, "DLL_OFF"),
        ({"hedging_violation": True}, "HEDGING_VIOLATION"),
        ({"now_et": time(16, 30)}, "OUTSIDE_SESSION"),
        ({"open_payout": True}, "PAYOUT_OPEN"),
        ({"requested_this_session": True}, "PAUSED_UNTIL_EOD"),
        ({"payouts_done": 5}, "MAX_PAYOUTS_REACHED"),
        ({"session_profit": D(0)}, "NO_SESSION_PROFIT"),
        ({"session_profit": D(-50)}, "NO_SESSION_PROFIT"),
        ({"session_profit": D(100), "prior_day_profits": [D(50), D(50)]}, "NO_CYCLE_PROFIT"),
        ({"prior_day_profits": [D(800)]}, "NOT_ENOUGH_PROFITABLE_DAYS"),
        ({"session_profit": D(2000), "prior_day_profits": [D(200), D(200)]}, "CONSISTENCY"),
        ({"balance": D(52400)}, "BELOW_BUFFER"),
        ({"session_profit": D(400), "prior_day_profits": [D(500), D(450)]}, "BELOW_MINIMUM"),
    ],
)
def test_each_blocker(kw, why):
    o = offer(**kw)
    assert not o.available and o.reason == why and o.message == od.REASONS[why] and o.amount == 0 and o.limited_by == ""


def test_max_payouts_none_and_no_consistency_rule():
    assert offer(max_payouts=None, payouts_done=9, cap_next=D(2500)).available
    assert offer(consistency_pct=None, session_profit=D(2000), prior_day_profits=[D(200), D(200)]).available


def test_pause_rule_text_names_end_of_trading_day():
    assert "until the end of the trading day" in od.PAUSE_RULE
