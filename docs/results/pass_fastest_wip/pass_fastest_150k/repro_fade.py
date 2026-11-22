"""Step 0c: regenerate the afternoon fade (all days, exit bar kept) and check it against session19 streams_fade_F0.csv once the strict F0 day rule
(no NOISE entry at all that day, Mondays off) is applied.  Prints how the causal rule ('no NOISE entry EARLIER than the fade signal') differs."""
import sys, os, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_lib as G
import pandas as pd, numpy as np

f = G.fade_stream(250.0)
f.to_csv(G.SCR + "/fade_all_250.csv", index=False)
n250 = G.noise_stream(250)
ref = pd.read_csv(G.WT + "/docs/results/session19/refine/streams_fade_F0.csv")
ref = ref[(ref.d >= "2021-10-21") & (ref.d <= "2026-10-30") & (pd.to_datetime(ref.d).dt.dayofweek != 0)]
ndays = set(n250.d)
g = f[(f.d >= "2021-10-21") & (f.d <= "2026-10-30") & (pd.to_datetime(f.d).dt.dayofweek != 0) & (~f.d.isin(ndays))]
ref2 = ref[~ref.d.isin(ndays)]   # sim2.load_fade applies the same day filter on top of F0
print("regenerated fade (strict F0 rule):", len(g), "F0 file after the sim2 day filter:", len(ref2), "F0 raw 5y non-Monday:", len(ref))
m = g.merge(ref2, on="d", suffixes=("", "_r"))
print("days in both:", len(m), "ek equal:", (m.ek == m.ek_r).all(), "side equal:", (m.side == m.side_r).all(),
      "max |pnl diff|:", float(np.abs(m.pnl - m.pnl_r).max()), "max |mae diff|:", float(np.abs(m.mae - m.mae_r).max()))
print("only regenerated:", sorted(set(g.d) - set(ref2.d))[:10], "only F0:", sorted(set(ref2.d) - set(g.d))[:10])
print("net $ per micro: regenerated", round(g.pnl.sum(), 1), "F0", round(ref2.pnl.sum(), 1))
# causal rule: fade allowed unless NOISE entered earlier than the fade signal bar
first_n = n250.groupby("d").ek.min()
fc = f[(f.d >= "2021-10-21") & (f.d <= "2026-10-30") & (pd.to_datetime(f.d).dt.dayofweek != 0)].copy()
fc["noise_first"] = fc.d.map(first_n)
causal = fc[fc.noise_first.isna() | (fc.noise_first > fc.sk + 1)]
print("causal rule fade trades:", len(causal), "net", round(causal.pnl.sum(), 1), "(strict:", len(g), round(g.pnl.sum(), 1), ")")
print("extra (NOISE entered only later that day):", len(causal) - len(g))
