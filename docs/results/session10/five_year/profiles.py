"""D64 size profiles (Regular / High risk) with the drawdown brake, 5 accounts, MAIN $250/$250, 5 years."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

dd = list(research_days()[1])
rows = [("lucid_pro_100k", 2, [None, (D("0.3"), 1), (D("0.5"), 1)]), ("lucid_pro_100k", 3, [None, (D("0.3"), 2), (D("0.5"), 2), (D("0.5"), 1)]),
        ("lucid_pro_150k", 3, [None, (D("0.3"), 2), (D("0.5"), 2)]), ("lucid_pro_150k", 4, [None, (D("0.3"), 2), (D("0.5"), 2), (D("0.5"), 3)])]
print("| plan | micros | brake | eval pass/bust (250 d) | per 2 wk | year avg / median | bust yr1 |")
print("|---|---|---|---|---|---|---|")
for plan, q, brakes in rows:
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    for b in brakes:
        er = [eval_path(dd[i:], ev, q, horizon=250, brake=b) for i in range(0, len(dd) - 260, 2)]
        p = project(fv, accounts=5, micros=q, cadence=10, days=dd, brake=b)
        lab = "none" if b is None else f"< {b[0]:.0%} → {b[1]}"
        print(f"| {plan[6:].replace('_', ' ').title()} | {q} | {lab} | {sum(r[0] == 'PASS' for r in er) / len(er):.0%} / "
              f"{sum(r[0] == 'BUST' for r in er) / len(er):.0%} | ${p.per_paycheck_mean:,.0f} | ${p.year_mean:,.0f} / ${p.year_median:,.0f} | {p.bust_pct}% |", flush=True)
