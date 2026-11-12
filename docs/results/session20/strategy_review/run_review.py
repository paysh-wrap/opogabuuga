import sys, os, json, time; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from multiprocessing import Pool
import lib, noise3
from noise3 import gen
OUT = lib.OUT
SZ = [25, 50, 100, 150]
V = {}   # id -> (family, label, kwargs)
V["BASE"] = ("BASE", "baseline", {})
V["F1"] = ("F1", "MES close beyond MES band", dict(efilt=noise3.f1_strict))
V["F1b"] = ("F1", "MES close on side of MES VWAP", dict(efilt=noise3.f1_loose))
for p in (0.30, 0.35, 0.40, 0.45, 0.50):
    V[f"F2_{p:.2f}"] = ("F2", f"lock trigger {p}% of price", dict(lock_fn=(lambda e, s, p=p: e * p / 100)))
for m in (0.5, 0.75, 1.0, 1.25, 1.5):
    V[f"F3_{m}"] = ("F3", f"lock trigger {m} x sigma_k x price", dict(lock_fn=(lambda e, s, m=m: m * s * e)))
for x in (150, 200, 250, 300):
    V[f"F4_{x}"] = ("F4", f"ratchet +{x} -> +{x/2:g}", dict(ratchet=float(x)))
V["F5a"] = ("F5", "trail checked every 30 min", dict(exit_extra=range(29, 330, 30)))
V["F5b"] = ("F5", "trail checked every 15 min", dict(exit_extra=range(29, 330, 15)))
V["F6a"] = ("F6", "trail = VWAP only", dict(trail="vwap"))
V["F6b"] = ("F6", "trail = band only", dict(trail="band"))

def year_pf(t):
    r = {}
    for y in range(2022, 2027):
        x = t[t.d.str.startswith(str(y))]
        if not len(x): continue
        g = x.pnl[x.pnl > 0].sum(); l = -x.pnl[x.pnl <= 0].sum()
        r[str(y)] = dict(n=len(x), pf=float(g / l) if l > 0 else None, net=float(x.pnl.sum()))
    return r

def metrics(t, base=None):
    M = {}
    for e in ("IS", "J", "ALL"):
        s = lib.stats(t, e); s = {k: (None if (isinstance(v, float) and not np.isfinite(v)) else float(v)) for k, v in s.items()}
        s["boot"] = {str(z): lib.eval_boot(t, e, z) for z in SZ}
        M[e] = s
    if base is not None:
        M["dJ"] = lib.delta_ci(t, base, "J"); M["dIS"] = lib.delta_ci(t, base, "IS")
    M["years"] = year_pf(t)
    return M

def work(vid):
    base = pd.read_csv(OUT + "/streams_BASE.csv")
    t = base if vid == "BASE" else gen(**V[vid][2])
    return vid, t, metrics(t, None if vid == "BASE" else base)

def rnd_work(seed):
    t = gen(rnd=seed)
    return seed, lib.stats(t, "J"), lib.eval_boot(t, "J", 25), lib.stats(t, "IS"), lib.eval_boot(t, "IS", 25)

if __name__ == "__main__":
    t0 = time.time()
    base = gen(); base.to_csv(OUT + "/streams_BASE.csv", index=False)
    R = {}; streams = {}
    with Pool(4) as P:
        for vid, t, M in P.imap_unordered(work, list(V)):
            R[vid] = dict(family=V[vid][0], label=V[vid][1], **M); streams[vid] = t; print(vid, round(time.time() - t0), flush=True)
        rn = P.map(rnd_work, range(30))
    b = R["BASE"]
    def ok_is(v):
        i = R[v]["IS"]; bi = b["IS"]
        return i["pf"] >= bi["pf"] and i["net"] >= 0.9 * bi["net"] and i["n"] >= 100
    picks = {}
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        el = [v for v in V if V[v][0] == fam and ok_is(v)]
        for v in V:
            if V[v][0] == fam: R[v]["eligible"] = v in el
        if el: picks[fam] = max(el, key=lambda v: (R[v]["IS"]["boot"]["25"]["pass_"], R[v]["IS"]["pf"]))
        else: picks[fam] = None
    def verdict(v, ref=None):
        ref = ref or b; j, i, bj, bi = R[v]["J"], R[v]["IS"], ref["J"], ref["IS"]
        jc = dict(pf=j["pf"] > bj["pf"], avg=j["avg"] >= bj["avg"], pass_=j["boot"]["25"]["pass_"] >= bj["boot"]["25"]["pass_"], bust=j["boot"]["25"]["bust"] <= bj["boot"]["25"]["bust"], net=j["net"] >= 0.97 * bj["net"])
        ic = dict(pf=i["pf"] >= bi["pf"] - 0.03, avg=i["avg"] >= bi["avg"] - 0.5, net=i["net"] >= 0.85 * bi["net"],
                  pass_=i["boot"]["25"]["pass_"] >= bi["boot"]["25"]["pass_"] - 1, bust=i["boot"]["25"]["bust"] <= bi["boot"]["25"]["bust"] + 1)
        return dict(J=jc, IS=ic, adopt=all(jc.values()) and all(ic.values()))
    ver = {f: (verdict(p) if p else None) for f, p in picks.items()}
    adopted = [f for f, v in ver.items() if v and v["adopt"]]
    combo = None
    if len(adopted) >= 2:
        kw = {}
        for f in adopted: kw.update(V[picks[f]][2])
        V["COMBO"] = ("COMBO", "combo of " + "+".join(picks[f] for f in adopted), kw)
        _, t, M = work("COMBO"); R["COMBO"] = dict(family="COMBO", label=V["COMBO"][1], **M); streams["COMBO"] = t
        combo = dict(members=[picks[f] for f in adopted], verdict=verdict("COMBO"))
    for v in set([p for p in picks.values() if p] + (["COMBO"] if combo else [])): streams[v].to_csv(f"{OUT}/streams_{v}.csv", index=False)
    json.dump(dict(results=R, picks=picks, verdicts=ver, adopted=adopted, combo=combo,
                   random=[dict(seed=s, J=j, Jboot=jb, IS=i, ISboot=ib) for s, j, jb, i, ib in rn]), open(OUT + "/review_results.json", "w"), indent=1, default=float)
    print("picks", picks, "adopted", adopted, "combo", combo, round(time.time() - t0))
