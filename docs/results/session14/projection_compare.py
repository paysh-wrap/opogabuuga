"""Dashboard income projection (5 accounts, bi-weekly payouts, auto size, Regular profile) on the hindsight vs causal stream.
run with the repo venv: PYTHONPATH=backend python docs/results/session14/projection_compare.py"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, ROOT + "/backend")
from pathlib import Path
import app.backtest.income_projection as ip
from app.api.income import _cached

DATA = Path(ROOT) / "backend/app/backtest/data"
PLANS = ["lucid_pro_25k", "lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k"]
rows = {}
for tag, f in (("old", "main_strategy_5y_hindsight.csv"), ("new", "main_strategy_5y.csv")):
    ip.DATA = DATA / f
    ip.research_days.cache_clear()
    _cached.cache_clear()
    for p in PLANS:
        path = ROOT + f"/config/rules/{p}.yaml"
        for prof, high in (("regular", False), ("high", True)):
            r = _cached(path, os.stat(path).st_mtime, 5, 0, 10, 0, high)
            rows[(p, prof, tag)] = r
print("| plan | profile | micros | year mean old -> new | year median old -> new | any payout % | bust % (yr 1) | median sessions to first payout |")
print("|---|---|---|---|---|---|---|---|")
for p in PLANS:
    for prof in ("regular", "high"):
        o, n = rows[(p, prof, "old")], rows[(p, prof, "new")]
        print(f"| {p} | {prof} | {n['micros']} | ${float(o['year_mean']):,.0f} -> ${float(n['year_mean']):,.0f} | ${float(o['year_median']):,.0f} -> ${float(n['year_median']):,.0f} | "
              f"{o['any_payout_pct']} -> {n['any_payout_pct']} | {o['bust_pct']} -> {n['bust_pct']} | {o['median_sessions_to_first']} -> {n['median_sessions_to_first']} |")
