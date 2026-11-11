import json, numpy as np, pandas as pd
import lib, noise2
from lib import stats, eval_boot, eval_roll, delta_ci
R = json.load(open(lib.OUT + "/noise_results.json")); TH = R["TH"]
D, F, moves = noise2.data(); base = noise2.gen()
rvf = lambda a, k, f: np.nansum(np.nan_to_num(a["volume"][:k + 1])) / f["rv_base"][k]
combo = noise2.gen(dayskip=lambda d, f: f["dow"] == 0, efilt=lambda d, k, s, a, f, g: rvf(a, k, f) >= TH["rv20"])
mon = noise2.gen(dayskip=lambda d, f: f["dow"] != 0)
rows = []
for name, t in (("C1 skip Monday + rel-vol >= IS p20", combo),):
    r = dict(name=name)
    for e in ("IS", "J", "HO24"): r[e] = stats(t, e)
    for e in ("IS", "J"):
        for sz in (25, 50): r[f"boot{sz}_{e}"] = eval_boot(t, e, sz); r[f"roll{sz}_{e}"] = eval_roll(t, e, sz)
    r["dJ"] = delta_ci(t, base, "J"); r["dHO"] = delta_ci(t, base, "HO24"); rows.append(r)
    print(name, {e: (r[e]["n"], round(r[e]["pf"], 2), round(r[e]["avg"], 1)) for e in ("IS", "J")}, r["boot25_J"], r["boot25_IS"])
# per-year: baseline vs skip-Monday vs Monday-only
mon_skip = noise2.gen(dayskip=lambda d, f: f["dow"] == 0)
yr = []
for y in range(2019, 2027):
    g = lambda t: t[t.d.str[:4] == str(y)]
    def pf(x): w = x.pnl > 0; return x.pnl[w].sum() / max(-x.pnl[~w].sum(), 1e-9) if len(x) else np.nan
    yr.append(dict(y=y, base_n=len(g(base)), base_pf=pf(g(base)), base_net=g(base).pnl.sum(), skip_n=len(g(mon_skip)), skip_pf=pf(g(mon_skip)), skip_net=g(mon_skip).pnl.sum(),
                   mon_n=len(g(mon)), mon_pf=pf(g(mon)), mon_net=g(mon).pnl.sum(), mon_avg=g(mon).pnl.mean()))
print(pd.DataFrame(yr).round(2).to_string())
json.dump(dict(combo=rows, years=yr), open(lib.OUT + "/noise_results2.json", "w"), indent=1, default=float)
