"""Pro 100K at 4 micros and Pro 150K at 4/6 micros (MAIN $250/$250), with and without the drawdown brake. 5 accounts."""
import sys
from decimal import Decimal as D
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

dd = list(research_days()[1])
print("| plan | micros | brake | worst trade | eval pass/bust | median days to pass | per 2 wk | year avg / median | middle half | bust yr1 |")
print("|---|---|---|---|---|---|---|---|---|---|")
for plan, q, hz, brakes in (("lucid_pro_100k", 2, 250, [None]), ("lucid_pro_100k", 4, 250, [None, (D("0.5"), 2), (D("0.5"), 1)]),
                            ("lucid_pro_150k", 3, 250, [None]), ("lucid_pro_150k", 4, 250, [None, (D("0.5"), 2)]),
                            ("lucid_pro_150k", 6, 250, [None, (D("0.5"), 3), (D("0.5"), 2)])):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    for b in brakes:
        er = [eval_path(dd[i:], ev, q, max_micros=10, horizon=hz, brake=b) for i in range(0, len(dd) - hz - 10, 2)]
        ps = sorted(r[1] for r in er if r[0] == "PASS")
        p = project(fv, accounts=5, micros=q, cadence=10, days=dd, max_micros=10, brake=b)
        lab = "none" if b is None else f"< {b[0]:.0%} MLL → {b[1]}"
        print(f"| {plan[6:].replace('_', ' ').title()} | {q} | {lab} | −${250 * q:,} ({250 * q / float(rc.funded.max_loss_limit):.0%} of MLL) | "
              f"{len(ps) / len(er):.0%} / {sum(r[0] == 'BUST' for r in er) / len(er):.0%} | {ps[len(ps) // 2] if ps else '-'} | "
              f"${p.per_paycheck_mean:,.0f} | ${p.year_mean:,.0f} / ${p.year_median:,.0f} | ${p.year_p25:,.0f}–${p.year_p75:,.0f} | {p.bust_pct}% |", flush=True)
