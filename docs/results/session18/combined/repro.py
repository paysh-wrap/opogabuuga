"""Reproduce the existing separate numbers on the last-12-month window (1 micro, each strategy alone, own position only, no day rules)."""
import sys, json
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/combined")
import numpy as np, pandas as pd, port
from port import *
c = pd.concat([pd.read_pickle(HERE + f"/out/cands_{m}.pkl") for m in ("MNQ", "MGC")], ignore_index=True)   # NO end cut here (rsi_dmi window ran to the last cached MGC day, 2026-11-09)
R = {m: json.load(open(f"/home/user/opogabuuga/docs/results/session18/rsi_dmi/out/results_{m}.json")) for m in ("MNQ", "MGC")}
rank = {"ICT": 0, "SMC": 1, "DMI": 2, "RSI": 3}
rows = []
def ps(x):
    s = pstats(x); return s
def stats_win(t, lo=None, hi=None):
    x = t[(t.d > SPLIT)] ; return pstats(x)
for (strat, var, mkt), g in c.groupby(["strat", "var", "mkt"]):
    t = select(g, 25, rank, fixed_n=1)
    i = pstats(t[t.d <= SPLIT]); h = pstats(t[t.d > SPLIT])
    orig = None
    if strat == "RSI":
        ps_, tf, ex = var.split(); name = f"A TriRSI({'2, 7, 14' if ps_.endswith('2') else '3, 7, 14'}) {tf} exit={ex}"
    elif strat == "DMI":
        _, thr, tf, ex = var.split(); name = f"B DMI adx{thr[3:] if False else thr} {tf} exit={ex}"
    else: name = None
    if name and name in R[mkt]: orig = R[mkt][name]
    rows.append(dict(strat=strat, var=var, mkt=mkt, IS_n=i["n"], IS_pf=i["pf"], HO_n=h["n"], HO_win=h["win"], HO_pf=h["pf"], HO_avg=h["avg"], HO_net=h["net"],
                     o_IS_n=orig["IS"].get("n") if orig else None, o_IS_pf=orig["IS"].get("pf") if orig else None, o_HO_n=orig["HO"].get("n") if orig else None,
                     o_HO_pf=orig["HO"].get("pf") if orig else None, o_HO_net=orig["HO"].get("net") if orig else None))
r = pd.DataFrame(rows); r.to_csv(HERE + "/out/repro.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print(r[r.strat.isin(["RSI", "DMI"])].round(2).to_string())
print(r[~r.strat.isin(["RSI", "DMI"])].round(2).to_string())
