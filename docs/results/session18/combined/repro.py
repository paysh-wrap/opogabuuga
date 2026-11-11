"""Reproduce the existing separate numbers on the last-12-month window (1 micro, each strategy alone, own position only, no day rules) -> out/repro.md"""
import sys, json
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/combined")
import numpy as np, pandas as pd, port
from port import *
c = pd.concat([pd.read_pickle(HERE + f"/out/cands_{m}.pkl") for m in ("MNQ", "MGC")], ignore_index=True)   # NO end cut here (rsi_dmi window ran to the last cached MGC day, 2026-11-09)
R = {m: json.load(open(f"/home/user/opogabuuga/docs/results/session18/rsi_dmi/out/results_{m}.json")) for m in ("MNQ", "MGC")}
rank = {"ICT": 0, "SMC": 1, "DMI": 2, "RSI": 3}
L = ["| strategy variant | market | mine IS n / PF | orig IS n / PF | mine HO n / win% / PF / net $ | orig HO n / win% / PF / net $ | match |", "|---|---|---|---|---|---|---|"]
nm = ok = 0
for (strat, var, mkt), g in c[c.strat.isin(["RSI", "DMI"])].groupby(["strat", "var", "mkt"]):
    t = select(g, 25, rank, fixed_n=1)
    i = pstats(t[t.d <= SPLIT]); h = pstats(t[t.d > SPLIT])
    if strat == "RSI": a, tf, ex = var.split(); name = f"A TriRSI({'2, 7, 14' if a.endswith('2') else '3, 7, 14'}) {tf} exit={ex}"
    else: _, thr, tf, ex = var.split(); name = f"B DMI {thr} {tf} exit={ex}"
    o = R[mkt][name]; oi, oh = o["IS"], o["HO"]
    same = (oi["n"] == i["n"] and abs(oi["pf"] - i["pf"]) < 0.011 and oh["n"] == h["n"] and abs(oh["net"] - h["net"]) < 1.5)
    nm += 1; ok += same
    L.append(f"| {name} | {mkt} | {i['n']} / {i['pf']:.2f} | {oi['n']} / {oi['pf']} | {h['n']} / {h['win']:.1f} / {h['pf']:.2f} / {h['net']:,.0f} | {oh['n']} / {oh['win']} / {oh['pf']} / {oh['net']:,} | {'yes' if same else 'NO'} |")
rsi_dmi_md = "\n".join(L)
# SMC vs streams (MNQ, window 2025-11-06..2026-11-05)
base = "/home/user/opogabuuga/docs/results/session18/smc/out/stream_"
pairs = {"1m+ST15 R1.5": "C_1m_pST15m_R1.5", "1m+ST15 R2.0": "C_1m_pST15m_R2.0", "1m+ST15+EMA200 R1.5": "C_1m_pST15mpEMA200_R1.5", "1m+ST15+EMA200 R2.0": "C_1m_pST15mpEMA200_R2.0",
         "5m+ST15 R1.5": "C_5m_pST15m_R1.5", "5m+ST15 R2.0": "C_5m_pST15m_R2.0", "5m+ST15+EMA200 R1.5": "C_5m_pST15mpEMA200_R1.5", "5m+ST15+EMA200 R2.0": "C_5m_pST15mpEMA200_R2.0"}
M = ["| SMC family C variant (MNQ) | mine n / net $ / PF | original stream n / net $ / PF |", "|---|---|---|"]; smc_ok = 0
for v, f in pairs.items():
    o = pd.read_csv(base + f + ".csv.gz"); o = o[(o.d >= START) & (o.d <= END)]
    g = c[(c.strat == "SMC") & (c["var"] == v) & (c.d <= END) & (c.mkt == "MNQ")]
    a = pstats(select(g, 25, rank, fixed_n=1)); b = pstats(o); smc_ok += (a["n"] == b["n"] and abs(a["net"] - b["net"]) < 1.5)
    M.append(f"| {v} | {a['n']} / {a['net']:,.0f} / {a['pf']:.2f} | {b['n']} / {b['net']:,.0f} / {b['pf']:.2f} |")
open(HERE + "/out/repro.md", "w").write(f"RSI/DMI: {ok}/{nm} rows identical to rsi_dmi/out/results_*.json (IS n, IS PF, HO n, HO net).\n\n" + rsi_dmi_md + f"\n\nSMC: {smc_ok}/{len(pairs)} identical.\n\n" + "\n".join(M) + "\n")
print(open(HERE + "/out/repro.md").read()[:1500]); print("RSI/DMI", ok, nm, "SMC", smc_ok)
