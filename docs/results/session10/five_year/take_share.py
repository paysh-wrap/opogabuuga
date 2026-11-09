"""5y: withdraw only part of each payout (D61) + account growth, 5 funded accounts, MAIN $250/$250, Pro 25K / 50K.
Uses the shipped MAIN trades (app/backtest/data/main_strategy_5y.csv) and the app's income_projection."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import project, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

print("| plan | size | take per payout | 5 funded per 2 wk | year avg / median | middle half | ≥1 payout | bust yr 1 |")
print("|---|---|---|---|---|---|---|---|")
for plan, sizes in (("lucid_pro_25k", [(1, None), (1, D(1000))]), ("lucid_pro_50k", [(1, None), (2, None), (1, D(1000)), (2, D(1000))])):
    fv = rules_view(load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules)
    for q, g in sizes:
        for take in (D(1), D("0.75"), D("0.5")):
            p = project(fv, accounts=5, micros=q, cadence=10, grow_per=g, take=take)
            lab = f"{q} micro{'s' if q > 1 else ''}" + (f" + grow/${g:,.0f}" if g else "")
            print(f"| {plan[6:].replace('_', ' ').title()} | {lab} | {take:.0%} | ${p.per_paycheck_mean:,.0f} | ${p.year_mean:,.0f} / ${p.year_median:,.0f} | "
                  f"${p.year_p25:,.0f}–${p.year_p75:,.0f} | {p.any_payout_pct}% | {p.bust_pct}% |")
