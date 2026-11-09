"""D59 projected income endpoint + pure funded-payout replay."""

from decimal import Decimal as D

from app.backtest.income_projection import FundedRulesView, funded_path, payout_amount, project, research_days

PRO25 = FundedRulesView(
    D(25000),
    D(1000),
    D(26100),
    D(25100),
    D(600),
    D("0.9"),
    D(26100),
    D(500),
    D(250),
    D(1000),
    D(1500),
    None,
    0,
    D(0),
    5,
    D(40),
    False,
)


def test_payout_rules():
    assert payout_amount(PRO25, D(27000), [D(300), D(300), D(400)], 0) == D(900)  # balance − buffer
    assert payout_amount(PRO25, D(28000), [D(600), D(700), D(600)], 0) == D(1000)  # first cap
    assert payout_amount(PRO25, D(29000), [D(1000), D(1000), D(1000)], 1) == D(1500)  # next cap
    assert payout_amount(PRO25, D(27000), [D(900), D(100)], 0) == 0  # 90% in one day > 40% consistency
    assert payout_amount(PRO25, D(26400), [D(300)] * 3, 0) == 0  # < $500 above the buffer
    assert payout_amount(PRO25, D(27000), [D(100), D(100)], 0) == 0  # cycle profit < $250
    flex = FundedRulesView(
        D(25000),
        D(1000),
        D(26100),
        D(25100),
        None,
        D("0.9"),
        D(25100),
        D(500),
        D(0),
        D(1000),
        D(1000),
        D("0.5"),
        5,
        D(100),
        None,
        None,
        True,
    )
    assert payout_amount(flex, D(27000), [D(400)] * 5, 0) == D(1000)  # 50% of 2,000, capped 1,000
    assert payout_amount(flex, D(27000), [D(400)] * 4, 0) == 0  # only 4 profitable days


def test_funded_path_payouts_bust_dll_and_lock():
    good = [(D(400),)] * 20
    p = funded_path(good, PRO25, 1, 10)
    assert p.status == "OPEN" and [a for _, a in p.payouts] == [D(900), D("1350.00")]  # 90% of 1,000 / 1,500
    assert funded_path([(D(-600),), (D(-600),)], PRO25, 1, 10).status == "BUST"  # 2 DLL days through the MLL
    capped = funded_path([(D(-500), D(-500), D(-500))] + [(D(0),)] * 9, PRO25, 1, 10)
    assert capped.status == "OPEN"  # soft DLL stopped the day at −600
    five = funded_path([(D(2000),)] * 60, PRO25, 1, 5)
    assert five.status == "MAX_PAYOUTS" and len(five.payouts) == 5
    flex = FundedRulesView(
        D(25000),
        D(1000),
        D(26100),
        D(25100),
        None,
        D("0.9"),
        D(25100),
        D(500),
        D(0),
        D(1000),
        D(1000),
        D("0.5"),
        5,
        D(100),
        None,
        None,
        True,
    )
    assert funded_path([(D(400),)] * 5, flex, 1, 5).payouts[0][1] == D(900)


def test_projection_from_research_file():
    names, days = research_days()
    assert names[0] == "2021-11-01" and len(names) == len(days) > 1200
    p = project(PRO25, accounts=5, micros=1, cadence=10)
    assert p.year_mean == D("8232.03") and p.max_possible_year == D("31500.00")  # matches the session-10 study
    assert p.week_mean * 52 == p.year_mean.quantize(D("0.01")) or abs(p.week_mean * 52 - p.year_mean) < 1
    tiny = project(PRO25, accounts=1, micros=1, cadence=5, horizon=10, days=[(D(0),)] * 30)
    assert tiny.any_payout_pct == 0 and tiny.median_sessions_to_first is None
    import pytest

    with pytest.raises(ValueError):
        project(PRO25, accounts=0, micros=1)


def test_income_endpoint(authed):
    r = authed.get("/api/income/projection", params={"plan": "lucid_pro_25k", "accounts": 5, "micros": 1})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["year_mean"] == "8232.03" and "lucid_pro_50k" in b["plans"] and b["accounts"] == 5
    assert authed.get("/api/income/projection", params={"plan": "../../etc/passwd"}).status_code == 422
    assert authed.get("/api/income/projection", params={"accounts": 9}).status_code == 422
    assert authed.get("/api/income/projection").status_code == 200  # current plan
    a = authed.get("/api/income/projection", params={"plan": "lucid_pro_150k"}).json()  # D63/D64 auto, Regular
    assert a["micros"] == 3 and a["auto"] == {"contracts": 3, "brake_below": "0.5", "brake_contracts": 2}
    assert a["profile"] == "regular" and a["bust_pct"] == "23.5"
    h = authed.get("/api/income/projection", params={"plan": "lucid_pro_150k", "profile": "high"}).json()
    assert h["micros"] == 4 and h["profile"] == "high" and h["year_median"] == "23705.50"
    assert authed.get("/api/income/projection", params={"profile": "max"}).status_code == 422
    g = authed.get("/api/income/projection", params={"plan": "lucid_pro_25k", "grow": 1000}).json()
    assert (
        g["grow"] == 1000 and g["year_mean"] == "9049.28"
    )  # D60 growth (table: $9,049; shipped file is rounded to cents)


def test_account_growth_sizing_and_eval_path():
    from app.backtest.income_projection import EvalRulesView, eval_path, size_for

    assert size_for(1, D(900), None, 5) == 1
    assert size_for(1, D(999), D(1000), 5) == 1 and size_for(1, D(2000), D(1000), 5) == 2
    assert size_for(1, D(9000), D(1000), 5) == 5 and size_for(2, D(500), D(1000), 5) == 2  # cap / never below base
    grown = funded_path([(D(400),)] * 10, PRO25, 1, 10, grow_per=D(1000))
    fixed = funded_path([(D(400),)] * 10, PRO25, 1, 10)
    assert grown.paid >= fixed.paid
    ev = EvalRulesView(D(25000), D(1250), D(1000), D(26100), D(25100), None, None, 1)
    assert eval_path([(D(700),), (D(700),)], ev, 1) == ("PASS", 2)
    assert eval_path([(D(-1000),)], ev, 1) == ("BUST", 1)
    assert eval_path([(D(0),)] * 5, ev, 1) == ("OPEN", 5)
    cons = EvalRulesView(D(25000), D(1250), D(1000), D(26100), D(25100), D(600), D(40), 3)
    assert eval_path([(D(1300),)], cons, 1)[0] == "OPEN"  # one day = 100% of the profit > 40%
    assert eval_path([(D(-500), D(-500))], cons, 1) == ("OPEN", 1)  # soft DLL stops the day at −600


def test_partial_withdrawal_leaves_profit_to_compound():
    full = funded_path([(D(400),)] * 20, PRO25, 1, 10)
    half = funded_path([(D(400),)] * 20, PRO25, 1, 10, take=D("0.5"))
    assert half.payouts[0][1] == D("450.00")  # 50% of the $1,000 eligible = $500 request → 90% to you
    assert half.paid < full.paid
    tiny = funded_path([(D(400),)] * 10, PRO25, 1, 10, take=D("0.1"))  # 10% of $900 < $500 minimum → no payout
    assert tiny.payouts == ()
