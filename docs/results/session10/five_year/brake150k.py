"""Pro 150K (and 50K/100K) with the D63 drawdown brake: cut to `to` micros when cushion < x·MLL. 5 accounts."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

names, dd = research_days()
dd = list(dd)
h2 = names.index("2024-01-01") if "2024-01-01" in names else next(i for i, n in enumerate(names) if n >= "2024")
print("| plan | size | brake | eval pass/bust | eval bust H1/H2 | per 2 wk | year avg / median | bust yr1 | bust H1 / H2 | income H1 / H2 |")
print("|---|---|---|---|---|---|---|---|---|---|")
for plan, q, hz, brakes in (("lucid_pro_50k", 2, 120, [None, (D("0.5"), 1)]),
                            ("lucid_pro_100k", 2, 120, [None, (D("0.3"), 1), (D("0.5"), 1)]),
                            ("lucid_pro_150k", 3, 250, [None, (D("0.3"), 2), (D("0.5"), 2), (D("0.5"), 1), (D("0.3"), 1)])):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    for b in brakes:
        er = [(i, eval_path(dd[i:], ev, q, horizon=hz, brake=b)) for i in range(0, len(dd) - hz - 10, 2)]
        bh = [sum(r[0] == "BUST" for i, r in er if (i < h2) == half) / max(1, sum(1 for i, _ in er if (i < h2) == half)) for half in (True, False)]
        p = project(fv, accounts=5, micros=q, cadence=10, days=dd, brake=b)
        p1 = project(fv, accounts=5, micros=q, cadence=10, days=dd[:h2 + 260], brake=b)
        p2 = project(fv, accounts=5, micros=q, cadence=10, days=dd[h2:], brake=b)
        lab = "none" if b is None else f"cushion < {b[0]:.0%} MLL → {b[1]} micro{'s' if b[1] > 1 else ''}"
        print(f"| {plan[6:].replace('_', ' ').title()} | {q} | {lab} | {sum(r[0] == 'PASS' for _, r in er) / len(er):.0%} / "
              f"{sum(r[0] == 'BUST' for _, r in er) / len(er):.0%} | {bh[0]:.0%} / {bh[1]:.0%} | ${p.per_paycheck_mean:,.0f} | "
              f"${p.year_mean:,.0f} / ${p.year_median:,.0f} | {p.bust_pct}% | {p1.bust_pct}% / {p2.bust_pct}% | ${p1.year_mean:,.0f} / ${p2.year_mean:,.0f} |", flush=True)
