"""D85: AI Duo on 150K — several positions, $250 per-trade cap, aggregate DLL/MLL check; others stay at 1 position."""

from decimal import Decimal as D

from tests.unit.test_risk_phase4 import _fixed, run  # 20-pt MNQ stop = $42 per micro incl. fee and slippage

BASE = {"consistency": None}


def test_default_account_still_rejects_a_second_position():
    r = run(**BASE, acct_has_open_position=True)
    assert not r.ok and r.reason == "POSITION_OPEN"
    r = run(**BASE, acct_open_positions=1, acct_max_open_positions=1)  # counted by the new field too
    assert not r.ok and r.reason == "POSITION_OPEN"


def test_big_account_may_hold_up_to_max_open_positions_and_no_more():
    ok = run(**BASE, lim=_fixed(1), acct_has_open_position=True, acct_open_positions=3, acct_max_open_positions=4)
    assert ok.ok and ok.contracts == 1
    full = run(**BASE, lim=_fixed(1), acct_has_open_position=True, acct_open_positions=4, acct_max_open_positions=4)
    assert not full.ok and full.reason == "POSITION_OPEN"


def test_per_trade_risk_cap_reduces_qty_or_skips():
    r = run(**BASE, lim=_fixed(4, max_risk_usd=D(100)))  # $42 per micro → 2 fit under $100
    assert r.ok and r.contracts == 2 and r.worst_case_usd == D("84.00")
    assert any(c["check"] == "trade_risk_cap" and c["ok"] is True for c in r.checks)
    r = run(**BASE, lim=_fixed(4, max_risk_usd=D(250)))  # 5 would fit, the cap of 4 binds
    assert r.ok and r.contracts == 4
    r = run(**BASE, lim=_fixed(4, max_risk_usd=D(40)))  # not even one micro fits
    assert not r.ok and r.reason == "STOP_TOO_WIDE"


def test_aggregate_risk_of_open_positions_plus_new_trade_must_fit_dll_and_mll_room():
    # room = min(DLL left $600, equity − MLL − kill distance $900) = $600; margin $40
    a = run(**BASE, lim=_fixed(4), acct_open_risk_usd=D(100))  # (600 − 40 − 100) // 42 = 10 → 4 fit
    assert a.ok and a.contracts == 4
    b = run(**BASE, lim=_fixed(4), acct_open_risk_usd=D(450))  # (600 − 40 − 450) // 42 = 2 → qty reduced to 2
    assert b.ok and b.contracts == 2 and b.worst_case_usd == D("84.00")
    assert any(c["check"] == "aggregate_risk" and c["contracts"] == "2" for c in b.checks)
    c = run(**BASE, lim=_fixed(4), acct_open_risk_usd=D(540))  # (600 − 40 − 540) // 42 = 0 → skip
    assert not c.ok and c.reason == "AGGREGATE_RISK_EXCEEDS_LIMITS"
    d = run(**BASE, lim=_fixed(4), acct_open_risk_usd=D(580))  # margin alone leaves nothing
    assert not d.ok and d.reason == "AGGREGATE_RISK_EXCEEDS_LIMITS"
    e = run(**BASE, lim=_fixed(4), acct_open_risk_usd=D(100), acct_dll=None, acct_equity=D(24500))  # MLL room 400
    assert e.ok and e.contracts == 4  # (400 − 40 − 100) // 42 = 6 → the cap of 4 binds
    f = run(**BASE, lim=_fixed(4), acct_open_risk_usd=D(370), acct_dll=None, acct_equity=D(24500))
    assert not f.ok and f.reason == "AGGREGATE_RISK_EXCEEDS_LIMITS"  # 400 − 40 − 370 < 0


def test_plan_is_untouched_when_nothing_is_open():
    r = run(**BASE, lim=_fixed(4))
    assert r.ok and r.contracts == 4 and not any(c["check"] == "aggregate_risk" for c in r.checks)
