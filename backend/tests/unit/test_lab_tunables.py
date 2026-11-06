"""§17: Lab tunables registry + challenger selection (pure)."""

from decimal import Decimal as D

import pytest

from app.lab.challenger import Candidate, Perf, best_on_train, explain, passes_oos, perf
from app.lab.tunables import TUNABLE_PARAMS, current_values, neighbours, validate_diff

PILLAR_AND_USER_KEYS = [
    "trade_plan.rr_min",
    "trade_plan.rr_max",
    "internal.risk_pct_floor",
    "internal.risk_pct_by_score",
    "internal.day_lockin_r",
    "filters.model_fail_cooldown",
    "eval_mode.risk_pct_ceiling",
    "payouts.skim_mode",
    "internal.windows",
    "indicators.require_c2_close_inside_c1",
    "eval.daily_loss_limit",
]


@pytest.mark.parametrize("key", PILLAR_AND_USER_KEYS)
def test_lab_can_never_touch_pillars_or_user_settings(key):
    assert key not in TUNABLE_PARAMS
    assert validate_diff({key: 1}, {}, D(25))[0].startswith(key)


def test_bounds_whole_numbers_and_step_limit():
    cur = {"score.min_score": D(60), "filters.c1_min_range_atr": D("0.4")}
    assert validate_diff({"score.min_score": 63}, cur, D(25)) == []
    assert "outside" in validate_diff({"score.min_score": 75}, cur, D(100))[0]
    assert "whole number" in validate_diff({"score.min_score": D("62.5")}, cur, D(25))[0]
    assert "larger than" in validate_diff({"filters.c1_min_range_atr": D("0.6")}, cur, D(25))[0]  # 0.2 > 25% of 0.6


def test_neighbours_one_step_inside_bounds_and_skip_user_values(loaded_rules):
    cur = current_values(loaded_rules.rules)
    cur["score.neutral_min_score"] = D(60)  # a user plan value outside 70–85 → never touched
    n = neighbours(cur, D(25))
    assert n and all(len(d) == 1 for d in n)
    assert not any("score.neutral_min_score" in d for d in n)
    for d in n:
        assert validate_diff(d, cur, D(25)) == []


def _p(trades, wins, r):
    return Perf(trades, wins, D(str(r)))


def test_perf_counts_closed_trades_only():
    p = perf([{"pnl": "10", "net_r": "1.5"}, {"pnl": "-5", "net_r": "-1"}, {"pnl": None, "net_r": None}])
    assert (p.trades, p.wins, p.net_r, p.win_rate, p.e) == (2, 1, D("0.5"), D("0.5"), D("0.25"))
    assert Perf(0, 0, D(0)).win_rate == 0 and Perf(0, 0, D(0)).e == 0


def test_best_on_train_never_lowers_win_rate_or_trade_count():
    champ = _p(20, 12, 4)  # 60%, +0.2R
    lower_win = Candidate({"score.min_score": D(55)}, _p(20, 11, 8))  # better E but lower win rate → out
    fewer = Candidate({"score.min_score": D(65)}, _p(10, 7, 5))  # 70% but half the trades → out
    good = Candidate({"entry.max_wait_bars": D(5)}, _p(19, 12, 6))
    assert best_on_train(champ, [lower_win, fewer, good]) == good
    assert best_on_train(champ, [lower_win, fewer]) is None


def test_out_of_sample_guard_and_explanation():
    champ_te = _p(10, 6, 1)
    c = Candidate({"entry.max_wait_bars": D(5)}, _p(19, 12, 6), _p(10, 7, 2))
    ok, why = passes_oos(champ_te, c, D("0.03"), 5)
    assert ok and why == []
    ok, why = passes_oos(champ_te, c, D("0.03"), 100)
    assert not ok and "out-of-sample trades" in why[0]
    ok, why = passes_oos(champ_te, Candidate(c.diff, c.train, _p(10, 5, 3)), D("0.03"), 5)
    assert not ok and "win rate" in why[-1]
    ok, why = passes_oos(champ_te, Candidate(c.diff, c.train, _p(10, 6, 1)), D("0.03"), 5)
    assert not ok and "expectancy" in why[0]
    assert passes_oos(champ_te, Candidate(c.diff, c.train), D(0), 0) == (False, ["not tested out of sample"])
    text = explain(c.diff, _p(20, 12, 4), c, champ_te)
    assert "entry.max_wait_bars" in text and "unseen" in text
