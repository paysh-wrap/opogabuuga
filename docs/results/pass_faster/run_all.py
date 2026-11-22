"""Run all tests (BASE, LOCK80, NOISE+CANDACE, NOISE+VWAP) x Pro 25K / 50K x {rolling starts, session-21 bootstrap, static} x windows. -> results.json
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_faster/run_all.py"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import multiprocessing as mp
import pf_sim as F

dates, op = F.trading_days()
P = F.load_plans(); t, t80, c, v = F.load_streams()
GMIN = F.smin(float(t[t.d >= '2025-11-06'].entry.mean()))
cst = c[c.day >= "2021-10-21"]; vst = v[v.day >= "2021-10-21"]
REFC = float(np.percentile(cst.stop_pts, 10))
MIX = {
    "BASE": (F.build_table(t), None),
    "LOCK80": (F.build_table(t80), None),
    "N+CANDACE": (F.build_table(t, cst), {F.STRAT_C: REFC}),
    "N+VWAP": (F.build_table(t, None, vst), {F.STRAT_V: 25.0}),
}


def job(a):
    mix, k, meth, win = a
    by, ref = MIX[mix]; p = P[k]
    if meth == "roll": r = F.run_roll(by, win, p, GMIN, dates, ref)
    elif meth == "boot": r = F.run_boot(by, win, p, GMIN, ref)
    elif meth == "rollmix": r = F.run_roll(by, win, p, GMIN, dates, ref, stuck_mix=True)
    elif meth == "bootmix": r = F.run_boot(by, win, p, GMIN, ref, stuck_mix=True)
    else: r = F.static_stats(by, win, p, dates, mix)
    return a, r


if __name__ == "__main__":
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "probe":
        for a in (("BASE", 25, "roll", "JUDGE"), ("N+VWAP", 25, "roll", "JUDGE"), ("N+CANDACE", 50, "static", "ALL")):
            print(job(a), time.time() - t0)
        sys.exit()
    jobs = [(m, k, "roll", w) for m in MIX for k in (25, 50) for w in ("ALL", "PICK", "JUDGE")]
    jobs += [(m, k, "boot", w) for m in MIX for k in (25, 50) for w in ("ALL", "PICK", "JUDGE", "L12", "IS")]
    jobs += [(m, k, meth, w) for m in ("N+CANDACE", "N+VWAP") for k in (25, 50) for w in ("ALL", "PICK", "JUDGE") for meth in ("rollmix", "bootmix")]
    jobs += [(m, k, "static", w) for m in MIX for k in (25, 50) for w in ("ALL", "PICK", "JUDGE")]
    with mp.Pool(4) as pool: res = pool.map(job, jobs, chunksize=1)
    out = {"|".join(map(str, a)): r for a, r in res}
    out["_meta"] = dict(gmin=GMIN, ref_candace_stop=REFC, candace_signals=len(cst), vwap_signals=len(vst))
    json.dump(out, open(os.path.dirname(os.path.abspath(__file__)) + "/results.json", "w"), indent=1, default=float)
    print("done", time.time() - t0)
