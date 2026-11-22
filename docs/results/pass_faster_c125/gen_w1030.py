"""CANDACE stream with NY window extended to 10:30 (D154 defaults otherwise), same harness as pass_faster/gen_streams.py.
Run: cd <worktree>/backend && NS_CACHE=<scratch> PYTHONPATH=. python3 ../docs/results/pass_faster_c125/gen_w1030.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
sys.argv = [sys.argv[0], PKL]
sys.path.insert(0, WT + "/docs/results/new_strategies/candace_keep_sweeps")
sys.path.insert(0, WT + "/docs/results/new_strategies/candace_trade_more")
import multiprocessing as mp, pandas as pd
import ctm_lib as L
if __name__ == "__main__":
    days = L.B.load_days(); built, info = L.B.build(days); L.BUILT = built
    for name, win in (("base", "09:00-10:00"), ("w1030", "09:00-10:30")):
        cfg = L.CandaceIctCfg(ny_window=win); assert cfg.keep_all_sweeps
        pool = mp.Pool(4)
        res = L.run_all(cfg.model_dump(), mode="engine", pool=pool)
        pool.close()
        rows = [t for ds, ts, _ in res for t in ts]
        pd.DataFrame(rows).to_csv(HERE + f"/streams_candace_{name}.csv", index=False)
        print(name, len(rows))
