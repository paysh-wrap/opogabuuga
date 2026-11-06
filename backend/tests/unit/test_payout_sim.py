"""§16.4 weekly payout simulation + §16.5 income Monte Carlo (P(≥$50k), P(≥$70k))."""

from decimal import Decimal as D

from app.backtest.payout_sim import FundedSim, income_monte_carlo, simulate_payouts

C = FundedSim(D(25000), D(1000), D(26100), D(25100), D(28100), "half", D(26100), D(500), D("0.9"))


def test_sweep_and_skim_follow_live_rule():
    r = simulate_payouts([D(300)] * 20, C)
    assert [(w.kind, w.amount) for w in r.weeks] == [
        (None, D(0)),  # 26,500 − 750 would break the 26,100 buffer
        ("skim", D("750.00")),
        ("sweep", D("650.00")),
        ("sweep", D("1500.00")),
    ]
    assert r.total_gross == D("2900.00") and r.total_net == D("2610.00") and not r.breached
    assert all(w.balance - w.amount >= C.buffer for w in r.weeks if w.kind)


def test_breach_ends_the_account():
    r = simulate_payouts([D(200), D(-1300), D(500)], C)
    assert r.breached and r.weeks == [] and r.total_gross == 0


def test_eod_trailing_then_lock():
    assert simulate_payouts([D(900), D(-1000)], C).breached  # peak 25,900 → MLL 24,900
    assert not simulate_payouts([D(1100), D(-900)], C).breached  # locked at 25,100


def test_caps_apply():
    c = FundedSim(
        D(25000), D(1000), D(26100), D(25100), D(28100), "half", D(26100), D(500), D("0.9"), D(1000), D(1000), D("0.5")
    )
    r = simulate_payouts([D(1200)] * 5, c)
    assert r.weeks[0].kind == "sweep" and r.weeks[0].amount == D("1000.00")


def test_income_mc_probabilities():
    days = [D(x) for x in (300, -200, 150, -100, 400, -250, 50)]
    m = income_monte_carlo(days, C, D(50000), D(70000), runs=300)
    assert set(m.by_accounts) == {1, 2, 3, 4, 5}
    p = [m.by_accounts[n]["p_floor"] for n in range(1, 6)]
    assert p == sorted(p) and all(D(0) <= x <= D(1) for x in p)
    assert m.by_accounts[5]["p_target"] <= m.by_accounts[5]["p_floor"]
    assert m == income_monte_carlo(days, C, D(50000), D(70000), runs=300)  # seeded, reproducible
    assert income_monte_carlo([], C, D(1), D(2)).by_accounts == {}
