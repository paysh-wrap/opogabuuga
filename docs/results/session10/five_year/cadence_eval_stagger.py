"""(A) payout request every 3 sessions vs 10 · (3) eval size vs funded size (value per eval bought) · (4) staggered starts.
MAIN strategy, Lucid Pro plans, automatic size + brake (D64 Regular / High). Uses the app's income_projection."""
import sys
from decimal import Decimal as D
from pathlib import Path
from statistics import mean, median

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, funded_path, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402
from app.risk.strategy_sizing import SizeTier, tier_for  # noqa: E402

names, dd = research_days()
dd = list(dd)
PLANS = ("lucid_pro_25k", "lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k")


def prof(rc, high):
    tab = rc.strategy.size_table_high if high else rc.strategy.size_table
    t = tier_for(rc.account_size, [SizeTier(x.account_size, x.mll, x.contracts, x.brake_below, x.brake_contracts) for x in tab])
    return t.contracts, ((t.brake_below, t.brake_contracts) if t.brake_below is not None else None)


print("## A. Payout every 3 sessions vs every 10 (5 funded accounts, first 12 months)")
print("| plan | profile | micros | cadence | per payout check | per 2 weeks (equiv.) | year avg / median | payouts in yr (avg) | bust yr1 |")
print("|---|---|---|---|---|---|---|---|---|")
for plan in PLANS:
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv = rules_view(rc)
    for high in (False, True):
        q, b = prof(rc, high)
        if high and plan in ("lucid_pro_25k", "lucid_pro_50k"):
            continue
        for cad in (10, 3):
            p = project(fv, accounts=5, micros=q, cadence=cad, days=dd, brake=b)
            paths = [funded_path(dd[i:i + 260], fv, q, cad, brake=b) for i in range(0, len(dd) - 260, 2)]
            npay = mean(len(x.payouts) for x in paths)
            print(f"| {plan[6:].replace('_', ' ').title()} | {'High' if high else 'Regular'} | {q} | every {cad} | ${p.per_paycheck_mean:,.0f} | "
                  f"${float(p.week_mean) * 2:,.0f} | ${p.year_mean:,.0f} / ${p.year_median:,.0f} | {npay:.1f} | {p.bust_pct}% |", flush=True)

print("\n## 3. Eval size vs funded size — value per eval bought (1 account; funded = profile size + brake, payout every 10)")
print("| plan | eval micros | eval pass / bust | median days to pass | funded avg paid yr1 | value per eval bought = pass × paid | evals per funded account |")
print("|---|---|---|---|---|---|---|")
for plan, hz in (("lucid_pro_25k", 120), ("lucid_pro_50k", 120), ("lucid_pro_100k", 250), ("lucid_pro_150k", 250)):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    q, b = prof(rc, False)
    paid = float(project(fv, accounts=1, micros=q, cadence=10, days=dd, brake=b).year_mean)
    for eq in sorted({1, 2, 3, 4, 5, 6} & set(range(1, max(q + 3, 3) + 1))):
        er = [eval_path(dd[i:], ev, eq, horizon=hz) for i in range(0, len(dd) - hz - 10, 2)]
        ps = sorted(r[1] for r in er if r[0] == "PASS")
        pp = len(ps) / len(er)
        print(f"| {plan[6:].replace('_', ' ').title()} | {eq} | {pp:.0%} / {sum(r[0] == 'BUST' for r in er) / len(er):.0%} | "
              f"{ps[len(ps) // 2] if ps else '-'} | ${paid:,.0f} | ${pp * paid:,.0f} | {1 / pp if pp else float('inf'):.1f} |", flush=True)

print("\n## 4. Staggered starts — 5 funded accounts, each followed 12 months from its own start")
print("| plan | starts | 5-acct yr avg | median | 25th pct | P(total = $0) | P(all 5 bust) |")
print("|---|---|---|---|---|---|---|")
for plan in ("lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k"):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv = rules_view(rc)
    q, b = prof(rc, False)
    for gap in (0, 21, 42):
        offs = [k * gap for k in range(5)]
        tot, allb = [], 0
        for i in range(0, len(dd) - 260 - offs[-1], 2):
            ps = [funded_path(dd[i + o:i + o + 260], fv, q, 10, brake=b) for o in offs]
            tot.append(sum(float(p.paid) for p in ps))
            allb += all(p.status == "BUST" for p in ps)
        s = sorted(tot)
        lab = "same day" if gap == 0 else f"every {gap} sessions (~{gap // 21} month{'s' if gap > 21 else ''})"
        print(f"| {plan[6:].replace('_', ' ').title()} | {lab} | ${mean(tot):,.0f} | ${median(tot):,.0f} | ${s[len(s) // 4]:,.0f} | "
              f"{sum(1 for x in tot if x == 0) / len(tot):.0%} | {allb / len(tot):.0%} |", flush=True)
