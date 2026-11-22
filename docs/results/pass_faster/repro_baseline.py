"""Step 0: reproduce config/eval_odds.yaml Pro 25K / 50K 'regular' rows with the session-21 simulator (sim2.py, unchanged code,
only the data paths patched to this worktree / the shared days.pkl)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
S21 = WT + "/docs/results/session21/pro_rules"
sys.path.insert(0, S21)
import sim, sim2
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
sim.R = WT + "/"; sim2.R = WT + "/"; sim2.PKL = PKL
from sim2 import *
P = sim.load_plans(); t = sim2.load()
sim2.GMIN = smin(float(t[t.d >= '2025-11-06'].entry.mean())); print('gmin', sim2.GMIN)
out = {}
for e in ERAS:
    d = day_table(t, e); paths = make_paths(len(d))
    for p in ('lucid_pro_25k', 'lucid_pro_50k'):
        r = run_cfg(d, paths, P[p], P[p]['tabs']['regular'], False)
        out[f'{p}|{e}'] = r; print(p, e, r)
json.dump(out, open(HERE + '/repro_baseline.json', 'w'), indent=1)
