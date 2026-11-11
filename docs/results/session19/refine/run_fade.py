import json, numpy as np, pandas as pd
import lib, noise2, fade2
from lib import stats, eval_boot, eval_roll, delta_ci
D, F, moves = noise2.data()
base_n = noise2.gen(); nd = set(base_n.d)
rvf = lambda a, k, f: np.nansum(np.nan_to_num(a["volume"][:k + 1])) / f["rv_base"][k]
trend = lambda a, k, f: abs(a["close"][k] - a["open"][0]) / f["atr"]
# IS thresholds
rec = dict(rv=[], tr=[])
def r_(d, k, s, a, f, sd):
    if d <= lib.IS_END: rec["rv"].append(rvf(a, k, f)); rec["tr"].append(trend(a, k, f))
    return True
fade2.gen(nd, efilt=r_)
TH = dict(rv_med=float(np.median(rec["rv"])), tr75=float(np.quantile(rec["tr"], .75)), tr50=float(np.median(rec["tr"])))
print(TH)
V = {"F0 baseline (band 2.0, $250, 13:01-15:29)": {}}
V["F1 band 2.5"] = dict(band=2.5); V["F1b band 3.0"] = dict(band=3.0)
V["F2 rel-vol <= IS median (%.2f)" % TH["rv_med"]] = dict(efilt=lambda d, k, s, a, f, sd: rvf(a, k, f) <= TH["rv_med"])
V["F2b rel-vol >= IS median"] = dict(efilt=lambda d, k, s, a, f, sd: rvf(a, k, f) >= TH["rv_med"])
V["F3 skip trend days (|c-open|/ATR14 >= IS p75 %.2f)" % TH["tr75"]] = dict(efilt=lambda d, k, s, a, f, sd: trend(a, k, f) < TH["tr75"])
V["F3b skip trend days (>= IS p50 %.2f)" % TH["tr50"]] = dict(efilt=lambda d, k, s, a, f, sd: trend(a, k, f) < TH["tr50"])
V["F4 window starts 13:31 (after dead zone)"] = dict(first=240)
V["F5 min target 12 ticks (3 pt)"] = dict(min_ticks=12)
V["F6 VA context: no fade into acceptance outside prior VA"] = dict(efilt=lambda d, k, s, a, f, sd: not (s < 0 and a["close"][k] > f["vah"]) and not (s > 0 and a["close"][k] < f["val"]))
V["F7 stop $150"] = dict(stop_usd=150.)
V["F8 last signal 15:00 (no new trades last 30 min)"] = dict(last=329)
rows = []; streams = {}
for name, kw in V.items():
    fz = fade2.gen(nd, **kw); streams[name] = fz
    comb = pd.concat([base_n[["d", "pnl", "mae"]], fz[["d", "pnl", "mae"]]]).sort_values("d", kind="stable").reset_index(drop=True)
    r = dict(name=name)
    for e in ("IS", "J", "HO24"): r[e] = stats(fz, e); r["comb_" + e] = stats(comb, e)
    for e in ("IS", "J"):
        for sz in (25, 50): r[f"boot{sz}_{e}"] = eval_boot(comb, e, sz)
    r["dJ"] = delta_ci(comb, base_n, "J")
    rows.append(r); print(name, r["IS"]["n"], round(r["IS"]["pf"], 2), r["J"]["n"], round(r["J"]["pf"], 2), r["boot25_J"], flush=True)
for e in ("IS", "J"):
    for sz in (25, 50): rows[0][f"noiseonly_boot{sz}_{e}"] = eval_boot(base_n, e, sz)
rb = [fade2.gen(nd, rnd=s) for s in range(20)]
rand = {e: dict(avg=float(np.mean([stats(x, e)["avg"] for x in rb])), pf=float(np.median([stats(x, e)["pf"] for x in rb])), win=float(np.mean([stats(x, e)["win"] for x in rb])), n=float(np.mean([stats(x, e)["n"] for x in rb]))) for e in ("IS", "J")}
json.dump(dict(rows=rows, TH=TH, rand=rand), open(lib.OUT + "/fade_results.json", "w"), indent=1, default=float)
for n_, t in streams.items(): t.to_csv(lib.OUT + "/streams_fade_%s.csv" % n_.split()[0], index=False)
