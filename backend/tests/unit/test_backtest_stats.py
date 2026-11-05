from decimal import Decimal as D

from app.backtest.stats import monte_carlo, stats


def test_stats():
    s = stats([("d1", D(100), D(2)), ("d1", D(-50), D(-1)), ("d2", D(-60), D(-1)), ("d3", D(200), D(2))])
    assert (s.trades, s.wins, s.win_rate, s.net) == (4, 2, D("0.5"), D(190))
    assert s.profit_factor == D("2.7273") and s.max_drawdown == D(110) and s.avg_r == D("0.5")
    assert s.best_day == D(200) and s.best_day_share == D("1.0526") and s.days == 3
    e = stats([])
    assert e.win_rate is None and e.profit_factor is None and e.best_day_share is None


def test_monte_carlo():
    good = monte_carlo([D(300), D(200), D(-100)], D(1250), D(1000), runs=500)
    bad = monte_carlo([D(-300), D(100)], D(1250), D(1000), runs=500)
    assert good.pass_rate > D("0.95") and bad.fail_rate > D("0.95")
    assert good.median_trades_to_pass is not None and bad.median_trades_to_pass is None
    assert monte_carlo([], D(1), D(1)).pass_rate == 0
    assert monte_carlo([D(300)], D(1250), D(1000), runs=10) == monte_carlo([D(300)], D(1250), D(1000), runs=10)
