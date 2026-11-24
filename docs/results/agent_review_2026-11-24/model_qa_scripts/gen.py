import sys, types
S20 = "/home/user/paytience/docs/results/session20/strategy_review"
PKL = "/home/user/days.pkl"
sys.path.insert(0, S20)
_src = open(S20 + "/lib.py").read().replace('SP + "/data/days12.pkl"', repr(PKL))
nlib = types.ModuleType("lib"); nlib.__file__ = S20 + "/lib.py"; sys.modules["lib"] = nlib
exec(compile(_src, S20 + "/lib.py", "exec"), nlib.__dict__)
import noise3
import numpy as np, pandas as pd
def pf(p):
    p = np.asarray(p); w = p[p > 0].sum(); l = -p[p <= 0].sum(); return w / l if l > 0 else np.inf
def st(t, lab=""):
    p = t.pnl.values
    return f"{lab:16s} n={len(p):4d} win={100*(p>0).mean():5.1f}% PF={pf(p):5.2f} avg=${p.mean():6.2f} net=${p.sum():8.0f}"
