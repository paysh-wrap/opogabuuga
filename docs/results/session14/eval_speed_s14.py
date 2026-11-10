"""Session 14: D75 P2 (reset frozen evals at once) and P3 (25K High-risk recover mode) re-run on the chosen fade rule.
usage: FADE_RULE=causal|hindsight STUDY_OUT=<dir> python3 eval_speed_s14.py"""
import os, sys, json
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D + "/../session11/final_push")
sys.path.insert(0, D + "/../session11")
sys.path.insert(0, D + "/../../../backend")
from multiprocessing import Pool
import eval_speed_run as R

R_ = dict(recover=True)
GRID = {
    "25K": {"BASE (live)": {}, "reset<15%": dict(abandon=.15)},
    "25K-HR": {"BASE (live)": {}, "recover mode": R_, "recover + reset<15%": {**R_, "abandon": .15}, "reset<15%": dict(abandon=.15)},
    "50K": {"BASE (live)": {}, "reset<5%": dict(abandon=.05)},
    "100K": {"BASE (live)": {}, "reset<10%": dict(abandon=.1)},
    "150K": {"BASE (live)": {}, "reset<5%": dict(abandon=.05)},
}
if __name__ == "__main__":
    jobs = [(p, nm, o) for p, v in GRID.items() for nm, o in v.items()]
    with Pool(4, initializer=R.init) as pool:
        res = pool.map(R.work, jobs, chunksize=1)
    out = {}
    for p, nm, r in res:
        out.setdefault(p, {})[nm] = r
    T = os.environ.get("STUDY_OUT", D + "/out")
    json.dump(out, open(T + "/eval_speed_s14.json", "w"), indent=1)
    for p, v in out.items():
        print(f"\n{p}  pass/bust/frozen/open med spp  (IS | OOS)")
        for nm, r in v.items():
            f = lambda x: f"{x['pas']:5.1f}/{x['bust']:4.1f}/{x['frozen']:5.1f}/{x['open']:4.1f} {x['med']:5.1f} {x['spp']:6.1f}"
            print(f"  {nm:24s} {f(r['IS'])} | {f(r['OOS'])}")
