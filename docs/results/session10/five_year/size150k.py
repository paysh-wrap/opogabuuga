"""Pro 150K sizing grid (MAIN $250/$250): eval size and funded size chosen separately; growth rules. 5 accounts.
Eval horizon 250 sessions (a $9,000 target needs time). Score = eval pass − bust, and funded median / bust."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

dd = list(research_days()[1])
rc = load_rules(REPO / "config" / "rules" / "lucid_pro_150k.yaml").rules
fv, ev = rules_view(rc), eval_view(rc)
print("EVAL (250 sessions): size | pass | bust | still open | median days to pass")
for q, g in [(2, None), (3, None), (4, None), (5, None), (6, None), (2, D(1500)), (3, D(1500)), (3, D(2250)), (4, D(2250))]:
    er = [eval_path(dd[i:], ev, q, g, max_micros=8, horizon=250) for i in range(0, len(dd) - 260, 2)]
    ps = [r[1] for r in er if r[0] == "PASS"]
    ps.sort()
    print(f"  {q} micros{' + grow/$' + format(g, ',.0f') if g else ''}: {len(ps) / len(er):.0%} | "
          f"{sum(r[0] == 'BUST' for r in er) / len(er):.0%} | {sum(r[0] == 'OPEN' for r in er) / len(er):.0%} | {ps[len(ps) // 2] if ps else '-'}")
print("\nFUNDED, 5 accounts, payout every 2 weeks: size | per 2 wk | year avg / median | p25–p75 | ≥1 payout | bust yr1")
for q, g in [(2, None), (3, None), (4, None), (5, None), (2, D(1500)), (2, D(2250)), (3, D(1500)), (3, D(2250)), (3, D(3000)), (4, D(3000))]:
    p = project(fv, accounts=5, micros=q, cadence=10, days=dd, grow_per=g, max_micros=8)
    print(f"  {q} micros{' + grow/$' + format(g, ',.0f') if g else ''}: ${p.per_paycheck_mean:,.0f} | ${p.year_mean:,.0f} / ${p.year_median:,.0f} | "
          f"${p.year_p25:,.0f}–${p.year_p75:,.0f} | {p.any_payout_pct}% | {p.bust_pct}%", flush=True)
