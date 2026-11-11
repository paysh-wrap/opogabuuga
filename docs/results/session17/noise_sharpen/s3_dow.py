"""Descriptive check (NOT a selection step): day-of-week and band-width effects of the preset-C NOISE trades in three non-overlapping periods.
The 2019-05..2021-10 period was never used in the session-10 / session-15 work (which started 2021-10/11), so a Monday effect that shows up there too
is an independent replication of the session-10 N11 finding. Writes RESULTS_dow.md"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd
S = json.load(open(HERE + "/study.json"))["variants"]
t = pd.read_csv(f"{HERE}/streams/{S['BASE [lock]']['file']}.csv", dtype={"d": str})
t["dow"] = pd.to_datetime(t.d).dt.day_name().str[:3]
P = {"2019-05..2021-10 (never used before)": ("2019-05-06", "2021-10-31"), "2021-11..2023-12 (session-15 pick)": ("2021-11-01", "2023-12-31"), "2024-01..2026-11 (held-out)": ("2024-01-01", "2026-11-06")}
sig_p20 = float(t[t.d <= "2023-12-31"].sigk.quantile(0.2))
o = ["### T11 preset-C trades by weekday and period ($/trade, [n trades], win %)\n| period | Mon | Tue | Wed | Thu | Fri | Tue-Fri avg |\n|---|---|---|---|---|---|---|\n"]
for lab, (a, b) in P.items():
    x = t[(t.d >= a) & (t.d <= b)]; cells = []
    for d in ("Mon", "Tue", "Wed", "Thu", "Fri"):
        y = x[x.dow == d]; cells.append(f"{y.pnl.mean():+.1f} [{len(y)}] {100*(y.pnl>0).mean():.0f}%")
    y = x[x.dow != "Mon"]; cells.append(f"{y.pnl.mean():+.1f} [{len(y)}]")
    o.append(f"| {lab} | " + " | ".join(cells) + " |\n")
o.append(f"\n### T12 preset-C trades by band width (sigma at the entry bar; IS 20th percentile = {100*sig_p20:.3f}% of price) ($/trade [n])\n| period | sigma < p20 | sigma >= p20 |\n|---|---|---|\n")
for lab, (a, b) in P.items():
    x = t[(t.d >= a) & (t.d <= b)]; lo, hi = x[x.sigk < sig_p20], x[x.sigk >= sig_p20]
    o.append(f"| {lab} | {lo.pnl.mean():+.1f} [{len(lo)}] | {hi.pnl.mean():+.1f} [{len(hi)}] |\n")
# Monday t-test (Welch) in each period
from math import sqrt
o.append("\nWelch t of Monday vs Tue-Fri $/trade: ")
for lab, (a, b) in P.items():
    x = t[(t.d >= a) & (t.d <= b)]; m, r = x[x.dow == "Mon"].pnl, x[x.dow != "Mon"].pnl
    o.append(f"{lab.split(' ')[0]} t={(m.mean()-r.mean())/sqrt(m.var()/len(m)+r.var()/len(r)):+.2f}; ")
o.append("\n")
open(HERE + "/RESULTS_dow.md", "w").write("".join(o)); print("".join(o))
