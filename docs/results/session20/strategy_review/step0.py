import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, lib, noise3
b = noise3.gen(); print(len(b), lib.S0)
b.to_csv(lib.OUT + "/streams_BASE.csv", index=False)
r = pd.read_csv(lib.OUT + "/../../session19/refine/streams_noise_R6.csv")
r = r[(r.d >= lib.S0) & (r.d <= lib.J1)]
m = b.merge(r, on=["d", "ek", "xk", "side"], suffixes=("", "_r"))
print("mine", len(b), round(b.pnl.sum()), "ref", len(r), round(r.pnl.sum()), "match", len(m), len(m)/len(b), len(m)/len(r))
print("matched pnl mine/ref", m.pnl.sum(), m.pnl_r.sum())
