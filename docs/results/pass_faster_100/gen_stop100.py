"""Regenerate the NOISE stream with a $100 stop per micro (stop $ + fee + slippage = $100 -> 49 pt hard stop) using the SAME session-20 generator
(noise3.gen, shipped config: preset C lock +100 -> entry+10, Mondays off, hourly checks, band/VWAP exits). Also re-runs $250 to prove the generator is unchanged.
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_faster_100/gen_stop100.py"""
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
import noise3, pandas as pd
ref = pd.read_csv(WT + "/docs/results/pass_faster/streams_noise_base.csv")
b250 = noise3.gen()
same = len(ref) == len(b250) and abs(ref.pnl.values - b250.pnl.values).max() < 1e-9
print("$250 regenerated identical to pass_faster stream:", same, len(b250))
b100 = noise3.gen(stop_usd=100.0)
print("$100:", len(b100), "trades, risk/micro", sorted(set(b100.risk.round(2))), "net/micro", round(b100.pnl.sum(), 1), "($250:", round(b250.pnl.sum(), 1), ")")
b100.to_csv(HERE + "/streams_noise_stop100.csv", index=False)
