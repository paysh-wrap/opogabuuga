"""print the 150K plan dict used by the old sims + a few stream stats (helper, no outputs written)"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../pass_faster_100")
import run_100 as R
p = R.P[150]
print({k: v for k, v in p.items() if k not in ("tabs",)})
print("row", p["row"])
print("GMIN", R.RF.GMIN)
import pandas as pd
t = R.t100
print(t.head(), len(t))
print(R.RF.t.head())
print(R.cst.head(), len(R.cst), list(R.cst.columns))
