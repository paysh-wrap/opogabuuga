"""5y: MAIN strategy ($250/$250) on Lucid's largest accounts (Pro 150K, Flex 150K; Pro 100K for reference): eval pass/bust
at 120 and 250 sessions + 5 funded accounts paid every 2 weeks, sizes 1–6 micros and growth (app income_projection)."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

dd = list(research_days()[1])
print("| plan | size | eval pass/bust 120 d | eval pass/bust 250 d | 5 funded per 2 wk | year avg / median | middle half | ≥1 payout | bust yr 1 |")
print("|---|---|---|---|---|---|---|---|---|")
for plan, sizes in (("lucid_pro_100k", [(2, None), (3, None)]),
                    ("lucid_pro_150k", [(q, None) for q in (2, 3, 4, 5, 6)] + [(2, D(1500)), (3, D(1500)), (3, D(2250))]),
                    ("lucid_flex_150k", [(q, None) for q in (2, 3, 4, 5, 6)] + [(3, D(1500))])):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    for q, g in sizes:
        cells = []
        for h in (120, 250):
            er = [eval_path(dd[i:], ev, q, g, max_micros=10, horizon=h) for i in range(0, len(dd) - h - 10, 2)]
            cells.append(f"{sum(r[0] == 'PASS' for r in er) / len(er):.0%} / {sum(r[0] == 'BUST' for r in er) / len(er):.0%}")
        p = project(fv, accounts=5, micros=q, cadence=10, days=dd, grow_per=g, max_micros=10)
        lab = f"{q} micros" + (f" + grow/${g:,.0f}" if g else "")
        print(f"| {plan[6:].replace('_', ' ').title()} | {lab} | {cells[0]} | {cells[1]} | ${p.per_paycheck_mean:,.0f} | ${p.year_mean:,.0f} / "
              f"${p.year_median:,.0f} | ${p.year_p25:,.0f}–${p.year_p75:,.0f} | {p.any_payout_pct}% | {p.bust_pct}% |", flush=True)
