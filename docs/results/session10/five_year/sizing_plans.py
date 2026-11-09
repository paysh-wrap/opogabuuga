"""5y: MAIN strategy stop sets × Pro 25K / 50K × sizing (fixed micros or D60 account growth), eval + 5 funded accounts.
Uses the app's pure app/backtest/income_projection.py (same code as the Dashboard). usage: sizing_plans.py MNQ_5Y.csv"""
import os
import sys
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE.rsplit("/docs/", 1)[0]
sys.path[:0] = [HERE, REPO + "/docs/results/tools", REPO + "/backend"]
import noise_area as NA  # noqa: E402
import run_b as B  # noqa: E402
from app.backtest.income_projection import eval_path, eval_view, project, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402


class Pts:
    def __init__(s, p): s.p = p
    def __bool__(s): return True
    def __rmul__(s, pos): return _P(pos * s.p)
class _P:
    def __init__(s, v): s.v = v
    def __mul__(s, entry): return s.v


def fade(days, noise_days, pts):
    out = []
    for d, a in days:
        if d < B.START or d > B.END or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * B.TICK
            if (vw[k] - e) * s < 4 * B.TICK: break
            p, _ = B.walk2(s, e, e - s * pts, vw[k], h, l, o, c, k + 1, 386)
            out.append((d, p)); break
    return pd.DataFrame(out, columns=["d", "pnl"])


def as_days(t):
    by = {}
    for d, p in zip(t.d, t.pnl): by.setdefault(d, []).append(D(str(round(p, 2))))
    first, last = date.fromisoformat(B.START), date.fromisoformat(B.END)
    out, x = [], first
    while x <= last:
        if x.weekday() < 5: out.append(tuple(by.get(x.isoformat(), ())))
        x += timedelta(days=1)
    return out


days = NA.load_days(sys.argv[1])
sets = {}
for ns, fs in ((250, 250), (350, 100)):
    nt = B.noise_t(days, hard=Pts((ns - 2) / 2)); nt = nt[(nt.d >= B.START) & (nt.d <= B.END)][["d", "pnl"]]
    t = pd.concat([nt, fade(days, set(nt.d), (fs - 2) / 2)]).sort_values("d", kind="stable")
    sets[f"NOISE ${ns} / fade ${fs}"] = as_days(t)
    print(f"NOISE ${ns} / fade ${fs}: {len(t)} trades, ${t.pnl.sum():,.0f}, win {(t.pnl > 0).mean():.1%}")
print()
print("| set | plan | sizing | eval pass / bust | 5 funded: per 2 weeks | year avg / median | middle half | ≥1 payout | funded bust yr 1 |")
print("|---|---|---|---|---|---|---|---|---|")
for name, dd in sets.items():
    for plan in ("lucid_pro_25k", "lucid_pro_50k"):
        rc = load_rules(Path(REPO) / "config" / "rules" / f"{plan}.yaml").rules
        fv, ev = rules_view(rc), eval_view(rc)
        unit = rc.funded.max_loss_limit / 2  # growth step: +1 micro per half of the MLL in extra cushion
        sizes = [("1 micro", 1, None), ("2 micros", 2, None)] + [
            (f"grow +1 per ${g:,.0f} cushion (max 5)", 1, D(g)) for g in (unit, unit * 2, unit * 3)]
        for lab, q, g in sizes:
            ev_res = [eval_path(dd[i:], ev, q, g) for i in range(0, len(dd) - 130, 2)]
            ps = sum(r[0] == "PASS" for r in ev_res) / len(ev_res); bs = sum(r[0] == "BUST" for r in ev_res) / len(ev_res)
            p = project(fv, accounts=5, micros=q, cadence=10, days=dd, grow_per=g)
            print(f"| {name} | {plan[6:].replace('_', ' ').title()} | {lab} | {ps:.0%} / {bs:.0%} | ${p.per_paycheck_mean:,.0f} | "
                  f"${p.year_mean:,.0f} / ${p.year_median:,.0f} | ${p.year_p25:,.0f}–${p.year_p75:,.0f} | {p.any_payout_pct}% | {p.bust_pct}% |")
