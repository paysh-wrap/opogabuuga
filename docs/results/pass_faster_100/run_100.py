"""3 contracts $100 each (2 NOISE + 1 CANDACE) on 25K/50K; double size (4 NOISE + 2 CANDACE) on 100K/150K. Research only.
NOISE stream regenerated with a $100 stop per micro (streams_noise_stop100.csv); CANDACE $100 per-micro cap (stop $ + fee + slippage), signal skipped if over.
Reuses ../pass_faster_fixed/run_fixed.py (account loop, stuck rule, rolling protocol) unchanged; only plans 100K/150K are added.
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_faster_100/run_100.py [check]  -> results.json
"""
import sys, os, json, time, pathlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../pass_faster_fixed")
import pandas as pd, multiprocessing as mp
import run_fixed as RF
F = RF.F
from app.config import load_rules

CAPC = 100.0
P = RF.P
S21P = F.S21.load_plans()
for k in (100, 150):
    nm = f"lucid_pro_{k}k"; p = dict(S21P[nm]); b = F.B.plan(k)
    r = load_rules(pathlib.Path(F.WT + f"/config/rules/{nm}.yaml")).rules
    c = r.strategy.candace_ict_cfg
    p.update(k=k, tick=float(b["tick"]), tv=float(b["tv"]), fee=float(b["fee"]), slip=int(b["slip"]), cap_trade=float(b["cap_trade"]),
             maxmicros=int(b["maxmicros"]), cost=float(F.B.cost1(b)), day_stop=float(b["day_stop"]),
             fitC=(float(c.risk_pct_of_drawdown), float(c.dll_use_pct), int(c.max_losses_per_day)),
             fitV=tuple(float(x) for x in b["fit"]["VWAP"]), row=p["tabs"]["regular"])
    P[k] = p
SIZES = {25: (2, 1), 50: (2, 1), 100: (4, 2), 150: (4, 2)}     # (NOISE micros, CANDACE micros)

t100 = pd.read_csv(HERE + "/streams_noise_stop100.csv")
p0 = P[25]
t100["entry"] = [float(RF.op[d][int(k)]) for d, k in zip(t100.d, t100.ek)]


def per_micro(stop_pts): return stop_pts / p0["tick"] * p0["tv"] + p0["fee"] + 2 * p0["slip"] * p0["tv"]


cst = RF.cst
cst_cap = cst[[per_micro(x) <= CAPC + 1e-9 for x in cst.stop_pts]]
T_N = RF.build(t100, None); T_NC = RF.build(t100, cst_cap)
BASE_T = RF.BASE_T
ROWS = ["BASE", "N100", "A", "B"]


def job(a):
    name, k, meth, win = a; p = P[k]
    if name == "BASE":
        if meth == "roll": return a, F.run_roll(BASE_T, win, p, RF.GMIN, RF.dates)
        return a, F.static_stats(BASE_T, win, p, RF.dates, None)
    nn, nc = SIZES[k]
    cfg = {"nn": nn, "nc": 0 if name == "N100" else nc, "both": name == "B"}
    by = T_N if name == "N100" else T_NC
    if meth == "roll": return a, RF.roll(by, win, p, cfg)
    return a, RF.static(by, win, p, cfg)


if __name__ == "__main__":
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        old = json.load(open(HERE + "/../pass_faster_fixed/results.json"))
        for k in (25, 50):
            for w in ("ALL", "JUDGE"):
                _, r = job(("BASE", k, "roll", w)); o = old[f"BASE|{k}|roll|{w}"]
                print("BASE", k, w, "MATCH" if abs(r["pass_"] - o["pass_"]) < 1e-9 and abs(r["stuck"] - o["stuck"]) < 1e-9 else "DIFF", r["pass_"], r["stuck"], o["pass_"], o["stuck"])
        for k in (100, 150):
            _, r = job(("BASE", k, "roll", "ALL")); print("BASE", k, "ALL pass", round(r["pass_"], 1), "bust", round(r["bust"], 1), "stuck", round(r["stuck"], 1), "run", round(r["run"], 1))
        sys.exit()
    print("CANDACE signals", len(cst), "kept under $100/micro", len(cst_cap), flush=True)
    wins = ("ALL", "PICK", "JUDGE")
    jobs = [(n, k, m, w) for k in (25, 50, 100, 150) for n in ROWS for m in ("roll", "static") for w in wins]
    with mp.Pool(4) as pool: res = pool.map(job, jobs, chunksize=1)
    out = {"|".join(map(str, a)): r for a, r in res}
    out["_meta"] = dict(gmin=RF.GMIN, cand_total=len(cst), cand_kept=len(cst_cap))
    json.dump(out, open(HERE + "/results.json", "w"), indent=1, default=float)
    print("done", time.time() - t0)
