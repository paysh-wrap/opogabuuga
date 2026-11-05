from decimal import Decimal as D

from app.phases.payout_plan import plan_payout

KW = {
    "sweep_above": D(28100),
    "skim_mode": "half",
    "buffer": D(26100),
    "min_request": D(500),
    "min_cycle_profit": D(1),
    "split": D("0.90"),
}


def p(balance, week, locked=True, cycle=D(100), **kw):
    return plan_payout(balance=D(str(balance)), week_profit=D(week), cycle_profit=cycle, locked=locked, **{**KW, **kw})


def test_sweep():
    r = p("28650.55", 900)
    assert (r.kind, r.amount, r.net) == ("sweep", D("550.55"), D("495.49"))


def test_sweep_needs_min_request():
    assert p(28599, 2000).kind == "skim"  # 499 over → no sweep; falls through to skim (1000 ≥ 500, leaves 27599)


def test_skim_rules():
    assert p(27000, 1200).amount == D(600)
    assert p(27000, 900).reason == "SKIM_BELOW_MIN_REQUEST"
    assert p(26500, 1200).reason == "WOULD_BREAK_BUFFER"
    assert p(27000, 1200, locked=False).reason == "NOT_LOCKED"
    assert p(27000, 1200, skim_mode="off").reason == "SKIM_OFF"


def test_no_profit_since_last_payout():
    assert p(30000, 0, cycle=D("0.50")).reason == "NO_PROFIT_SINCE_LAST_PAYOUT"


def test_never_below_buffer_property():
    for bal in range(25000, 31000, 37):
        for wk in range(-500, 4000, 113):
            r = p(bal, wk)
            if r.kind:
                assert D(bal) - r.amount >= D(26100) and r.amount >= D(500)


def test_pro_caps_by_payout_number():
    r = p(30000, 3000, max_first=D(1000), max_next=D(1500))
    assert (r.kind, r.amount) == ("sweep", D(1000))
    assert p(30000, 3000, payout_no=2, max_first=D(1000), max_next=D(1500)).amount == D(1500)


def test_flex_half_of_profit_and_profitable_days():
    kw = {"max_pct_of_profit": D("0.5"), "min_profitable_days": 5, "max_first": D(1000)}
    assert p(30000, 3000, cycle=D(1500), profitable_days=4, **kw).reason == "NOT_ENOUGH_PROFITABLE_DAYS"
    assert p(30000, 3000, cycle=D(1500), profitable_days=5, **kw).amount == D(750)
    assert p(30000, 3000, cycle=D(900), profitable_days=5, **kw).reason == "CAPPED_BELOW_MIN_REQUEST"
