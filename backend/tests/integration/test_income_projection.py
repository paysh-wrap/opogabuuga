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
    assert names[0] == "2019-05-24" and len(names) == len(days) > 1900  # B7: session-19 shipped-config stream
    p = project(PRO25, accounts=5, micros=1, cadence=10)
    assert p.year_mean == D("7089.66") and p.max_possible_year == D("31500.00")
    # B7 / D135: session-19 shipped config (lock + Mondays off + fade); session 14 gave 4408.91, hindsight 8232.03
    assert p.week_mean * 52 == p.year_mean.quantize(D("0.01")) or abs(p.week_mean * 52 - p.year_mean) < 1
    tiny = project(PRO25, accounts=1, micros=1, cadence=5, horizon=10, days=[(D(0),)] * 30)
    assert tiny.any_payout_pct == 0 and tiny.median_sessions_to_first is None
    import pytest

    with pytest.raises(ValueError):
        project(PRO25, accounts=0, micros=1)


def test_income_endpoint(authed):
    """Dashboard calculator: every number comes from config/income_calc.json (micros 1..9, MAIN = fast-pass NOISE + CANDACE)."""
    import json

    from app.api.income import CALC_PATH

    data = json.loads(CALC_PATH.read_text())
    cell = data["plans"]["lucid_pro_25k"]["cells"]["m9|g0|c10"]
    r = authed.get("/api/income/projection", params={"plan": "lucid_pro_25k", "accounts": 5, "micros": 9})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["micros"] == 9 and b["accounts"] == 5 and "lucid_pro_50k" in b["plans"]
    assert D(b["year_mean"]) == D(str(cell["paid_year_mean"])) * 5  # same trades on every account -> N x one account
    assert b["bust_pct"] == str(cell["bust_pct"]) and b["median_sessions_to_first"] == cell["median_sessions_to_first"]
    assert "UNVERIFIED" in b["basis"] and "NOISE" in b["basis"] and "CANDACE" in b["basis"] and "$250" not in b["basis"]
    assert "20-43%" in b["caveat"] and "session-19" not in b["basis"]
    for m in range(1, 10):  # micros 1..9 all selectable, nine and above is refused
        assert authed.get("/api/income/projection", params={"micros": m}).status_code == 200
    assert authed.get("/api/income/projection", params={"micros": 10}).status_code == 422
    assert authed.get("/api/income/projection", params={"plan": "../../etc/passwd"}).status_code == 422
    assert authed.get("/api/income/projection", params={"accounts": 9}).status_code == 422
    assert authed.get("/api/income/projection", params={"cadence": 7}).status_code == 422
    assert authed.get("/api/income/projection", params={"grow": 123, "micros": 2}).status_code == 422
    assert authed.get("/api/income/projection").status_code == 200  # current plan, auto
    h = authed.get("/api/income/projection", params={"plan": "lucid_pro_150k", "profile": "high"}).json()
    hc = data["plans"]["lucid_pro_150k"]["cells"]["auto-high|c10"]
    assert h["profile"] == "high" and h["auto"]["contracts"] == 5 and h["year_median"] == str(D(str(hc["paid_year_median"])) * 5)
    od = authed.get("/api/income/projection", params={"cadence": 0, "micros": 3}).json()
    assert od["cadence_sessions"] == 0 and "VERIFY" in od["on_demand_note"] and "no fixed payout window" in od["on_demand_note"]
    assert authed.get("/api/income/projection", params={"profile": "max"}).status_code == 422


def test_income_data_file_is_complete():
    import json

    from app.api.income import CALC_PATH

    d = json.loads(CALC_PATH.read_text())
    assert d["meta"]["max_micros"] == 9 and "UNVERIFIED" in d["meta"]["status"]
    for p in d["plans"].values():
        for m in range(1, 10):
            for g in d["meta"]["grows"]:
                for c in d["meta"]["cadences"]:
                    assert f"m{m}|g{g}|c{c}" in p["cells"]
        for prof in ("high", "regular"):
            for c in d["meta"]["cadences"]:
                assert f"auto-{prof}|c{c}" in p["cells"]


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


def _cells():
    import json

    from app.api.income import CALC_PATH

    d = json.loads(CALC_PATH.read_text())
    for pn, p in d["plans"].items():
        for key, c in p["cells"].items():
            yield pn, p, key, c


def test_income_invariants_all_cells():
    """Units/consistency of every cell: per-payout <= cap, week x weeks = year, median vs share paid, ranges."""
    for pn, p, key, c in _cells():
        wk = 250 // 5
        assert 0 < p["cap_first_net"] <= p["cap_next_net"]
        assert c["per_paycheck_mean"] <= p["cap_next_net"] + 0.01 and c["per_payout_max"] <= p["cap_next_net"] + 0.01, (pn, key)
        assert abs(c["week_mean"] * wk - c["year_mean"]) <= 0.5 * wk and abs(c["paid_week_mean"] * wk - c["paid_year_mean"]) <= 0.5 * wk, (pn, key)
        assert p["max_possible_year"] == round(p["cap_first_net"] + (p["payout_events_max"] - 1) * p["cap_next_net"], 2)
        assert 0 <= c["any_payout_pct"] <= 100 and 0 <= c["bust_pct"] <= 100 and 0 <= c["max_payouts_pct"] <= 100
        if c["any_payout_pct"] < 49.9:
            assert c["year_median"] == 0, (pn, key)  # median 0 iff at most half are paid
        if c["any_payout_pct"] > 50.1:
            assert c["year_median"] > 0, (pn, key)
        for f in ("year_mean", "year_median", "year_p25", "year_p75", "paid_year_mean", "paid_year_median", "paid_year_p25", "paid_year_p75", "paid_week_mean", "week_mean"):
            assert c[f] >= 0
        assert c["year_p25"] <= c["year_median"] <= c["year_p75"] and c["paid_year_p25"] <= c["paid_year_median"] <= c["paid_year_p75"]
        assert c["paid_year_mean"] >= c["year_mean"] - 0.01  # profit scenario never below the all-accounts mean
        assert c["paid_year_mean"] <= p["max_possible_year"] + 0.01 and c["paid_year_p75"] <= p["max_possible_year"] + 0.01


def test_income_endpoint_units_and_note(authed):
    b = authed.get("/api/income/projection", params={"plan": "lucid_pro_150k", "accounts": 5, "micros": 9, "cadence": 10}).json()
    assert b["scenario"] == "paid" and b["net_of_split"] is True
    assert D(b["max_possible_year"]) == D(b["max_possible_account"]) * 5 == (D(b["cap_first_net"]) + 4 * D(b["cap_next_net"])) * 5
    assert "5 accounts" in b["max_possible_formula"]
    assert D(b["per_paycheck_mean"]) <= D(b["cap_next_net"]) * 5
    assert abs(D(b["week_mean"]) * b["weeks_in_horizon"] - D(b["year_mean"])) <= 5 * b["weeks_in_horizon"] / 2
    assert D(b["incl_unpaid_year_mean"]) <= D(b["year_mean"])
    assert 0 <= float(b["bust_pct"]) <= 100 and 0 <= float(b["any_payout_pct"]) <= 100


def test_income_150k_9_micros_matches_sim_distribution():
    import json

    from app.api.income import CALC_PATH

    c = json.loads(CALC_PATH.read_text())["plans"]["lucid_pro_150k"]["cells"]["m9|g0|c10"]
    assert c["starts"] > 500 and c["paid_year_mean"] >= c["year_mean"]
    assert abs(c["paid_year_mean"] * c["any_payout_pct"] / 100 - c["year_mean"]) <= 0.002 * c["paid_year_mean"] + 1  # (pct rounded to 0.1) mixture identity: mean = share paid x paid mean
