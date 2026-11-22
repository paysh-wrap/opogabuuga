"""Step 0a: the NOISE generator at $250 must equal the shipped stream and at $100 pass_faster_100's stream exactly (nothing is written to the old folders).
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_fastest_150k/repro_gen.py"""
import sys, os, types
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
sys.argv = [sys.argv[0], PKL]
S20 = WT + "/docs/results/session20/strategy_review"
sys.path.insert(0, S20)
_src = open(S20 + "/lib.py").read().replace('SP + "/data/days12.pkl"', repr(PKL))
nlib = types.ModuleType("lib"); nlib.__file__ = S20 + "/lib.py"; sys.modules["lib"] = nlib
exec(compile(_src, S20 + "/lib.py", "exec"), nlib.__dict__)
import noise3, pandas as pd, numpy as np


def same(a, b):
    return len(a) == len(b) and all((a[c].values == b[c].values).all() for c in ("d", "ek", "xk", "side")) and abs(a.pnl.values - b.pnl.values).max() < 1e-9 \
        and abs(a.mae.values - b.mae.values).max() < 1e-9 and abs(a.risk.values - b.risk.values).max() < 1e-9


ref250 = pd.read_csv(WT + "/docs/results/pass_faster/streams_noise_base.csv")
ref100 = pd.read_csv(WT + "/docs/results/pass_faster_100/streams_noise_stop100.csv")
g250 = noise3.gen(); g100 = noise3.gen(stop_usd=100.0)
print("$250 == shipped stream (pass_faster/streams_noise_base.csv):", same(ref250, g250), len(g250), round(g250.pnl.sum(), 1))
print("$100 == pass_faster_100/streams_noise_stop100.csv:", same(ref100, g100), len(g100), round(g100.pnl.sum(), 1))
