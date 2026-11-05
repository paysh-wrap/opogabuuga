from decimal import Decimal as D

from app.backtest.runner import BacktestConfig, aggregate, run_backtest
from tests.unit.test_indicators import c1_bars, long_model_c2, mk


def test_aggregate_complete_buckets_only():
    bars = [mk(i, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(12)]
    five = aggregate(bars, 5)
    assert (
        len(five) == 2
        and five[0].o == D(100)
        and five[0].h == D(105)
        and five[0].l == D(99)
        and five[0].c == D("104.5")
    )


def test_replay_runs_the_live_pipeline():
    bars = (
        c1_bars()
        + long_model_c2()
        + [mk(30, 107, 108, 106.5, 107.5), mk(31, 107.5, 110.25, 107, 110)]
        + [mk(i, 110, 110.5, 109.5, 110) for i in range(32, 60)]
    )
    r = run_backtest(bars, BacktestConfig(bias="LONG_ONLY", profiles=("TIGHT",)))
    assert r.sessions == 1 and sum(r.signals.values()) >= 1, r
    assert any("bias fixed" in a for a in r.assumptions) and r.final_balance


def test_replay_is_not_rate_limited():
    bars = [mk(i, 100, 101, 99, 100) for i in range(400)]  # > 300 payloads in a few seconds of wall time
    r = run_backtest(bars, BacktestConfig(bias="NEUTRAL", profiles=("TIGHT",)))
    assert r.rejects == {}, r.rejects
