import sys, json, glob, os, math
sys.path[:0] = ["/home/user/opogabuuga/docs/results/session15", "/home/user/opogabuuga/docs/results/session21/orderblock_footprint"]
import numpy as np, pandas as pd, yaml
from types import SimpleNamespace as NS
import ob
import lib   # session15 account engine: _day / eval_run (works; plan_rules there only covers Pro, so plans are read here)
OUT = os.path.dirname(os.path.abspath(__file__))
IS_END, J_START = "2025-11-05", "2025-11-06"
D, E = ob.load()
mnq = ob.Market(D, 2.0)
Ed = [(d, E[d]) for d, _ in D if d in E]
mes = ob.Market(Ed, 5.0, vol_modes=("rec", "range", "one"))
VARS = ["V0", "V1", "V2", "V3"]; RS = [1.5, 2.0, 2.5]; TFS = [5, 1]
res = dict(imputed=dict(MNQ=mnq.imputed / mnq.total, MES=mes.imputed / mes.total), grid=[])
cache = {}
def grid(vm, mk=mnq, tag="MNQ"):
    rows = []
    for tf in TFS:
        for v in VARS:
            c = mk.candidates(tf, v, vm)
            for R in RS:
                r = mk.run(c, R); cache[(tag, vm, tf, v, R)] = r
                si, sj = ob.stats(r, None, IS_END), ob.stats(r, J_START, None)
                rows.append(dict(vm=vm, tf=tf, var=v, R=R, IS=si, J=sj))
    return rows
for vm in ("rec", "range", "one"): res["grid"] += grid(vm)
# pick on IS, main volume only
main = [g for g in res["grid"] if g["vm"] == "rec"]
for g in main:
    g["elig"] = bool(g["IS"]["pf"] > 1.05 and g["IS"]["n"] >= 150)
    g["score"] = g["IS"]["per"] * math.sqrt(g["IS"]["n"])
el = [g for g in main if g["elig"]]
fallback = not el
pool = el if el else main
pick = max(pool, key=lambda g: (g["score"], g["IS"]["pf"]))
res["pick"] = dict(tf=pick["tf"], var=pick["var"], R=pick["R"], vm="rec", eligible=not fallback, IS=pick["IS"], J=pick["J"])
rows = cache[("MNQ", "rec", pick["tf"], pick["var"], pick["R"])]
pd.DataFrame(rows).drop(columns=["di"]).to_csv(f"{OUT}/streams_pick_MNQ.csv", index=False)
# per-year PF
py = {}
for y in range(2021, 2027):
    py[y] = ob.stats(rows, f"{y}-01-01", f"{y}-12-31")
res["pick"]["per_year"] = py
# random benchmark on J
Jrows = [r for r in rows if r["d"] >= J_START]
rs = np.array([mnq.random_side(Jrows, pick["R"], s).mean() for s in range(30)])
pj = pick["J"]["per"]
res["random"] = dict(seeds_per_trade=rs.tolist(), mean=float(rs.mean()), beats=int((pj > rs).sum()), pick_J_per=pj)
Irows = [r for r in rows if r["d"] <= IS_END]
rsI = np.array([mnq.random_side(Irows, pick["R"], s).mean() for s in range(30)])
res["random"]["IS_mean"] = float(rsI.mean()); res["random"]["IS_beats"] = int((pick["IS"]["per"] > rsI).sum())
edge = pj > 0 and pick["J"]["pf"] >= 1.15 and pick["J"]["net"] > 0 and res["random"]["beats"] >= 27 and not fallback
res["edge"] = bool(edge)
# MES check for the pick
c = mes.candidates(pick["tf"], pick["var"], "rec"); mr = mes.run(c, pick["R"])
res["mes"] = dict(IS=ob.stats(mr, None, IS_END), J=ob.stats(mr, J_START, None))
pd.DataFrame(mr).drop(columns=["di"]).to_csv(f"{OUT}/streams_pick_MES.csv", index=False)

# ---------------- accounts
PL = ["pro_25k", "pro_50k", "pro_100k", "pro_150k", "flex_25k", "flex_50k", "flex_100k", "flex_150k", "daily_25k"]
def plan(n):
    y = yaml.safe_load(open(f"/home/user/opogabuuga/config/rules/lucid_{n}.yaml")); e = y["eval"]; s = y["account_size"]
    q = next((r["contracts"] for r in y.get("strategy", {}).get("size_table", []) if r["account_size"] == s), 1)
    fl = lambda x: None if x is None else float(x)
    return NS(start=float(s), e=NS(target=fl(e["profit_target"]), mll=fl(e["max_loss_limit"]), lt=fl(e["lock_trigger"]), ll=fl(e["lock_level"]),
              dll=fl(e["daily_loss_limit"]), cons=fl(e["consistency_max_day_pct"]), mpd=int(e["min_profitable_days"]))), q
noise = pd.read_csv("/home/user/opogabuuga/docs/results/session20/strategy_review/streams_BASE.csv")
dates = mnq.dates
def tab_from(rows_or_df, era):
    ds = [d for d in dates if (d <= IS_END if era == "IS" else d >= J_START)]
    by = {}
    it = rows_or_df.to_dict("records") if hasattr(rows_or_df, "to_dict") else rows_or_df
    for r in sorted(it, key=lambda r: (r["d"], r["ek"])): by.setdefault(r["d"], []).append((r["pnl"], r["mae"], r["risk"]))
    return [by.get(d, []) for d in ds]
def boot(tab, R, q, seed=7, paths=600, H=400):
    rng = np.random.default_rng(seed); n = len(tab); outs = []; days = []
    for _ in range(paths):
        seq = []
        while len(seq) < H:
            s0 = int(rng.integers(0, n - 10 + 1)); seq += tab[s0:s0 + 10]
        o, d = lib.eval_run(seq[:H], R, {"q": q}, H); outs.append(o)
        if o == "PASS": days.append(d)
    return dict(pass_=100 * outs.count("PASS") / paths, bust=100 * outs.count("BUST") / paths, open_=100 * outs.count("OPEN") / paths,
                med=float(np.median(days)) if days else None)
streams = {"OB": rows, "NOISE": noise}
comb = None
if edge:
    busy = {}
    for r in noise.itertuples(): busy.setdefault(r.d, []).append((r.ek, r.xk))
    comb = [r for r in rows if not any(a <= r["ek"] <= b for a, b in busy.get(r["d"], []))]
    streams["NOISE+OB"] = pd.concat([noise, pd.DataFrame(comb)[["d", "ek", "xk", "pnl", "mae", "risk", "side"]]]).to_dict("records")
res["accounts"] = {}
for n in PL:
    R, q = plan(n); res["accounts"][n] = dict(q=q)
    for nm, st in streams.items():
        for era in ("IS", "J"):
            res["accounts"][n][f"{nm}_{era}"] = boot(tab_from(st, era), R, q)
res["stream_stats"] = dict(NOISE_IS=ob.stats(noise.assign(d=noise.d).to_dict("records"), None, IS_END), NOISE_J=ob.stats(noise.to_dict("records"), J_START, None))
json.dump(res, open(f"{OUT}/results.json", "w"), indent=1, default=float)
print(json.dumps({k: res[k] for k in ("imputed", "pick", "random", "edge", "mes")}, indent=1, default=float)[:3500])
