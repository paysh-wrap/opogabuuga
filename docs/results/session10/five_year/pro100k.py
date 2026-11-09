"""5y: MAIN strategy ($250/$250) on Pro 100K (and 50K for comparison): eval pass/bust (120 sessions) + 5 funded accounts
paid every 2 weeks, sizes 1–5 micros and account growth. Uses the app's income_projection (same code as the Dashboard)."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

dd = list(research_days()[1])
print("| plan | size | eval pass / bust (120 days) | 5 funded per 2 wk | year avg / median | middle half | ≥1 payout | bust yr 1 | max possible |")
print("|---|---|---|---|---|---|---|---|---|")
for plan, grow_step in (("lucid_pro_50k", D(1000)), ("lucid_pro_100k", D(1500))):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    sizes = [(q, None) for q in (1, 2, 3, 4, 5)] + [(1, grow_step), (2, grow_step), (2, grow_step * 2)]
    for q, g in sizes:
        er = [eval_path(dd[i:], ev, q, g, max_micros=8) for i in range(0, len(dd) - 130, 2)]
        ps = sum(r[0] == "PASS" for r in er) / len(er); bs = sum(r[0] == "BUST" for r in er) / len(er)
        p = project(fv, accounts=5, micros=q, cadence=10, days=dd, grow_per=g, max_micros=8)
        lab = f"{q} micro{'s' if q > 1 else ''}" + (f" + grow/${g:,.0f}" if g else "")
        print(f"| {plan[6:].replace('_', ' ').title()} | {lab} | {ps:.0%} / {bs:.0%} | ${p.per_paycheck_mean:,.0f} | ${p.year_mean:,.0f} / "
              f"${p.year_median:,.0f} | ${p.year_p25:,.0f}–${p.year_p75:,.0f} | {p.any_payout_pct}% | {p.bust_pct}% | ${p.max_possible_year:,.0f} |")
