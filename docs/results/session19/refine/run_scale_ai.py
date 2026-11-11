import json, numpy as np, pandas as pd
import lib, noise2
from lib import stats, eval_boot, eval_roll
lib.RANGES["ALL"] = (lib.S0, lib.J1)
D, F, moves = noise2.data(); base = noise2.gen()
mon = noise2.gen(dayskip=lambda d, f: f["dow"] == 0)
out = dict(scale=[], ai=[])
for nm, t in (("NOISE preset C", base), ("NOISE preset C + skip Monday", mon)):
    for size in (25, 50, 100, 150):
        for n in (1, 2, 3, 4, 5):
            r = dict(strategy=nm, size=size, n=n)
            for e in ("IS", "J", "ALL"):
                b = eval_boot(t, e, size, n_paths=400, cap=500, n=n); r[e] = b
            # worst day / worst trade at this size vs DLL, MLL
            dd = t.groupby("d").pnl.sum() * n
            r["worst_day"] = float(dd.min()); r["worst_trade"] = float(t.pnl.min() * n)
            r["days_dll_hit"] = int((dd <= -(lib.ACC[size]["DLL"] or 1e9)).sum()); out["scale"].append(r)
        print(nm, size, flush=True)
# AI accuracy bands: bias per day = sign(close - open) with prob a (else wrong); hard filter on NOISE trades against bias
dayret = {d: np.sign(a["close"][NB-1] - a["open"][0]) if (NB:=390) and a["close"][389] == a["close"][389] else 0 for d, a in D}
def ai(acc, seed):
    rng = np.random.default_rng(seed); bias = {}
    for d in dayret: bias[d] = dayret[d] if rng.random() < acc else -dayret[d]
    return noise2.gen(efilt=lambda d, k, s, a, f, g: bias.get(d, 0) == s)
for acc in (0.5, 0.55, 0.6, 0.65, 0.7, 0.75):
    ts = [ai(acc, s) for s in range(20)]
    r = dict(acc=acc)
    for e in ("IS", "J"):
        ss = [stats(t, e) for t in ts]
        r[e] = {k: float(np.mean([x[k] for x in ss])) for k in ("n", "win", "avg", "net", "dd")}; r[e]["pf"] = float(np.median([x["pf"] for x in ss]))
        bb = [eval_boot(t, e, 25, n_paths=150) for t in ts[:8]]
        r[e]["pass"] = float(np.mean([b["pass_"] for b in bb])); r[e]["bust"] = float(np.mean([b["bust"] for b in bb]))
    out["ai"].append(r); print(acc, r["J"], flush=True)
json.dump(out, open(lib.OUT + "/scale_ai_results.json", "w"), indent=1, default=float)
