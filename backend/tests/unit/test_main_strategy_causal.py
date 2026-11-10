"""Session 14 (D77 follow-up): the shipped research stream is CAUSAL — a fade row exists only if no NOISE entry
had fired by then (live rule, strategy_service.run_pm_fade). The hindsight file keeps the old rule for comparison."""

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "app" / "backtest" / "data"


def _rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open() as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def test_causal_csv_columns_and_flag():
    rows = _rows("main_strategy_5y.csv")
    assert rows and set(rows[0]) == {"d", "pnl", "strategy", "entry_time", "causal"}
    assert {r["causal"] for r in rows} == {"1"}
    assert {r["strategy"] for r in rows} == {"NOISE", "FADE"}


def test_no_fade_row_has_an_earlier_noise_entry_that_day():
    rows = _rows("main_strategy_5y.csv")
    first_noise: dict[str, str] = {}
    for r in rows:
        if r["strategy"] == "NOISE":
            first_noise[r["d"]] = min(first_noise.get(r["d"], "99:99"), r["entry_time"])
    fades = [r for r in rows if r["strategy"] == "FADE"]
    assert fades
    for r in fades:
        assert "13:00" <= r["entry_time"] <= "15:30"  # fade window 13:00-15:29 signal, entry next bar
        # a NOISE entry (signal one bar earlier) at or before the fade entry would have blocked it
        assert first_noise.get(r["d"], "99:99") > r["entry_time"], r


def test_at_most_one_fade_per_day_and_hindsight_file_is_the_old_rule():
    rows = _rows("main_strategy_5y.csv")
    days = [r["d"] for r in rows if r["strategy"] == "FADE"]
    assert len(days) == len(set(days))
    old = _rows("main_strategy_5y_hindsight.csv")
    noise_days = {r["d"] for r in old if r["strategy"] == "NOISE"}
    # hindsight: the fade only trades on days NOISE never trades
    assert not any(r["d"] in noise_days for r in old if r["strategy"] == "FADE")
    assert {r["causal"] for r in old} == {"0"}
