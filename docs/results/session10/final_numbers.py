"""Final per-plan numbers for the PDF (MAIN strategy, D63/D64 automatic size + brake), using the app's own code.
usage: final_numbers.py OUT.json"""
import json
import sys
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import eval_path, eval_view, funded_path, project, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402
from app.risk.strategy_sizing import SizeTier, tier_for  # noqa: E402

names, dd = research_days()
dd = list(dd)
out = {"period": f"{names[0]} → {names[-1]}", "sessions": len(dd), "rows": []}
for plan in ("lucid_pro_25k", "lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k",
             "lucid_flex_25k", "lucid_flex_50k", "lucid_flex_100k", "lucid_flex_150k"):
    rc = load_rules(REPO / "config" / "rules" / f"{plan}.yaml").rules
    fv, ev = rules_view(rc), eval_view(rc)
    for prof, table in (("Regular", rc.strategy.size_table), ("High risk", rc.strategy.size_table_high)):
        t = tier_for(rc.account_size, [SizeTier(x.account_size, x.mll, x.contracts, x.brake_below, x.brake_contracts) for x in table])
        brake = (t.brake_below, t.brake_contracts) if t.brake_below is not None else None
        ev_res = {}
        for h in (120, 250):
            er = [eval_path(dd[i:], ev, t.contracts, horizon=h, brake=brake) for i in range(0, len(dd) - h - 10, 2)]
            ps = sorted(r[1] for r in er if r[0] == "PASS")
            ev_res[h] = (sum(r[0] == "PASS" for r in er) / len(er), sum(r[0] == "BUST" for r in er) / len(er), ps[len(ps) // 2] if ps else None)
        p5 = project(fv, accounts=5, micros=t.contracts, cadence=10, days=dd, brake=brake)
        p1 = project(fv, accounts=1, micros=t.contracts, cadence=10, days=dd, brake=brake)
        paths = [funded_path(dd[i:i + 260], fv, t.contracts, 10, brake=brake) for i in range(0, len(dd) - 260, 2)]
        cnt = Counter(len(x.payouts) for x in paths)
        months = [0.0] * 12
        for x in paths:
            for day, amt in x.payouts:
                months[min(11, (day - 1) // 21)] += float(amt) * 5 / len(paths)
        out["rows"].append({
            "plan": plan, "label": plan[6:].replace("_", " ").title().replace("K", "K"), "profile": prof,
            "micros": t.contracts, "brake": None if brake is None else [float(brake[0]), brake[1]],
            "worst_trade": 250 * t.contracts, "mll": float(rc.funded.max_loss_limit), "target": float(rc.eval.profit_target),
            "eval120": ev_res[120], "eval250": ev_res[250],
            "p1_2wk": float(p1.per_paycheck_mean), "p1_year_mean": float(p1.year_mean), "p1_year_median": float(p1.year_median),
            "p5_2wk": float(p5.per_paycheck_mean), "p5_week": float(p5.week_mean), "p5_year_mean": float(p5.year_mean),
            "p5_year_median": float(p5.year_median), "p5_p25": float(p5.year_p25), "p5_p75": float(p5.year_p75),
            "payout_pct": float(p5.any_payout_pct), "bust_pct": float(p5.bust_pct), "first_payout": p5.median_sessions_to_first,
            "max_year5": float(p5.max_possible_year), "payout_dist": {k: cnt[k] / len(paths) for k in range(6)}, "months5": months,
        })
        print(plan, prof, t.contracts, round(p5.per_paycheck_mean), round(p5.year_median), p5.bust_pct, flush=True)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float))
