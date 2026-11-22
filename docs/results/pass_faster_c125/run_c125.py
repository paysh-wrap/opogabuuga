"""C125 study: NOISE + CANDACE with a $125 per-trade risk cap and min 1 micro (no grade shrink to 0). Builds on ../pass_faster/pf_sim.py unchanged,
only CANDACE sizing (fit_contracts for kind CANDACE) is swapped per variant.
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_faster_c125/run_c125.py [check]  -> results.json
"""
import sys, os, json, time, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../pass_faster")
import numpy as np, pandas as pd
import multiprocessing as mp
import pf_sim as F

CAP = 125.0
VARIANT = {"mode": "orig"}          # orig | c125 | c125_1
_orig_fit = F.fit_contracts


def fit_contracts(p, fit, stop_pts, gmult, left, room, day_cap=None):
    mode = VARIANT["mode"]
    if mode == "orig" or fit is not p["fitC"]:
        return _orig_fit(p, fit, stop_pts, gmult, left, room, day_cap)
    rp, up, n = fit
    parts = [rp * p["mll"], max(room, 0.0) / n, p["cap_trade"], p["day_stop"] / n]
    if left is not None:
        parts.append(max(left, 0.0) * up / n)
    risk = math.floor(min(parts) * 100 + 1e-7) / 100          # the Lucid fit risk (unchanged)
    eff = min(risk, CAP)                                       # never above the Lucid fit, never above $125
    per = stop_pts / p["tick"] * p["tv"] + p["fee"] + 2 * p["slip"] * p["tv"]
    c = min(int(eff // per), p["maxmicros"])
    if c < 1: return 0                                         # 1 micro does not fit in min(fit, $125): skipped (Lucid fit stays on)
    if mode == "c125_1": return 1
    if gmult is not None and gmult < 2.0:                      # grade rule tighten-only, floored at 1
        c = max(1, min(c, int(c * gmult / 2.0 + 1e-9)))
    return c


F.fit_contracts = fit_contracts

dates, op = F.trading_days()
P = F.load_plans(); t, t80, c, v = F.load_streams()
GMIN = F.smin(float(t[t.d >= '2025-11-06'].entry.mean()))
cst = c[c.day >= "2021-10-21"]
cw = pd.read_csv(HERE + "/streams_candace_w1030.csv"); cw = cw[cw.day >= "2021-10-21"]
REFC = float(np.percentile(cst.stop_pts, 10))
MIX = {   # name -> (table, ref_stops, sizing mode)
    "BASE": (F.build_table(t), None, "orig"),
    "N+CANDACE": (F.build_table(t, cst), {F.STRAT_C: REFC}, "orig"),
    "C125": (F.build_table(t, cst), {F.STRAT_C: REFC}, "c125"),
    "C125_1": (F.build_table(t, cst), {F.STRAT_C: REFC}, "c125_1"),
    "C125_W1030": (F.build_table(t, cw), {F.STRAT_C: REFC}, "c125"),
}


def job(a):
    mix, k, meth, win = a
    by, ref, mode = MIX[mix]; p = P[k]; VARIANT["mode"] = mode
    if meth == "roll": r = F.run_roll(by, win, p, GMIN, dates, ref)
    elif meth == "boot": r = F.run_boot(by, win, p, GMIN, ref)
    else: r = F.static_stats(by, win, p, dates, mix)
    return a, r


if __name__ == "__main__":
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        old = json.load(open(HERE + "/../pass_faster/results.json"))
        ok = True
        for mix in ("BASE", "N+CANDACE"):
            for k in (25, 50):
                for meth, w in (("roll", "ALL"), ("roll", "JUDGE"), ("static", "ALL")):
                    _, r = job((mix, k, meth, w)); o = old[f"{mix}|{k}|{meth}|{w}"]
                    keys = ("pass_", "bust_all", "run", "med", "p75") if meth == "roll" else ("t1", "tp", "ddp")
                    same = all(abs((r[x] or 0) - (o[x] or 0)) < 1e-9 for x in keys); ok &= same
                    print(mix, k, meth, w, "MATCH" if same else "DIFF", {x: r[x] for x in keys})
        print("ALL MATCH" if ok else "MISMATCH", time.time() - t0); sys.exit()
    wins = ("ALL", "PICK", "JUDGE")
    jobs = [(m, k, "roll", w) for m in MIX for k in (25, 50) for w in wins]
    jobs += [(m, k, "boot", w) for m in MIX for k in (25, 50) for w in wins + ("L12",)]
    jobs += [(m, k, "static", w) for m in MIX for k in (25, 50) for w in wins]
    with mp.Pool(4) as pool: res = pool.map(job, jobs, chunksize=1)
    out = {"|".join(map(str, a)): r for a, r in res}
    out["_meta"] = dict(gmin=GMIN, ref_candace_stop=REFC, cap=CAP, candace_signals=len(cst), candace_w1030_signals=len(cw))
    json.dump(out, open(HERE + "/results.json", "w"), indent=1, default=float)
    print("done", time.time() - t0)
