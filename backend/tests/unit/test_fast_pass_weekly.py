"""D164: weekly profit targets on the fast-pass cards (figures from config/eval_odds.yaml, eval target from the plan yaml)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.api.dashboard import _fast_pass_weekly
from app.eval_odds import load_odds, weekly_row


def test_25k_figures() -> None:
    w = _fast_pass_weekly("lucid_pro_25k")
    assert w is not None
    assert w["target"] == "1250" and w["median_days"] == "56.5" and w["measured"] is True
    assert D(w["needed_week"]) == D("110.62")  # 1250 / (56.5 / 5)
    assert D(w["sim_week"]) == D("74.23")  # 19300 / 260
    assert "needed_week_10" not in w and "sim_week_10" not in w  # counts come from the UI calculator
    assert w["source"].endswith("final_search/RESULTS.md")


@pytest.mark.parametrize(
    ("stem", "target", "days", "measured"),
    [("lucid_pro_50k", "3000", "61", False), ("lucid_pro_100k", "6000", "87", True), ("lucid_pro_150k", "9000", "80", False)],
)
def test_other_plans(stem: str, target: str, days: str, measured: bool) -> None:
    w = _fast_pass_weekly(stem)
    assert w is not None and w["target"] == target and w["median_days"] == days and w["measured"] is measured
    assert D(w["needed_week"]) == (D(target) / (D(days) / 5)).quantize(D("0.01"))


def test_unknown_plan_and_missing_file() -> None:
    assert weekly_row("nope") is None
    assert _fast_pass_weekly("nope") is None
    load_odds.cache_clear()
    try:
        assert load_odds() is not None
    finally:
        load_odds.cache_clear()


def test_missing_odds_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    import app.eval_odds as eo

    load_odds.cache_clear()
    monkeypatch.setattr(eo, "load_odds", lambda: None)
    assert weekly_row("lucid_pro_25k") is None
