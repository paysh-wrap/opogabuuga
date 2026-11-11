"""NOISE (MNQ) refinements vs preset-C baseline.  Pick thresholds on IS (2019-05..2025-11-05) only, judge on the last 12 months (J) - HO24 secondary."""
import json, numpy as np, pandas as pd
import lib, noise2
from lib import stats, eval_boot, eval_roll, delta_ci
D, F, moves = noise2.data()
base = noise2.gen()

# --- IS-only thresholds ---------------------------------------------------------------------------------------------------------------------
rec = dict(rv=[], rng=[], sig=[], bw=[])
def recorder(d, k, side, a, f, sg):
    if d <= lib.IS_END:
        rec["rv"].append(np.nansum(np.nan_to_num(a["volume"][:k + 1])) / f["rv_base"][k])
        rec["rng"].append((np.nanmax(a["high"][:k + 1]) - np.nanmin(a["low"][:k + 1])) / f["atr"])
        rec["sig"].append(sg)
    return True
noise2.gen(efilt=recorder)
q = lambda x, p: float(np.quantile(x, p))
TH = dict(rv20=q(rec["rv"], .2), rv35=q(rec["rv"], .35), rng20=q(rec["rng"], .2), rng35=q(rec["rng"], .35), sig20=q(rec["sig"], .2))
print("IS thresholds", TH)

def rv(a, k, f): return np.nansum(np.nan_to_num(a["volume"][:k + 1])) / f["rv_base"][k]
def rngr(a, k, f): return (np.nanmax(a["high"][:k + 1]) - np.nanmin(a["low"][:k + 1])) / f["atr"]
def va_ctx_open(a, f): o = a["open"][0]; return 1 if o > f["vah"] else (-1 if o < f["val"] else 0)
DEAD = {149, 209}                                    # 12:00 and 13:00 checks: entries 12:01 / 13:01 fall in 11:15-13:30
V = {}
V["A0 baseline (preset C)"] = {}
V["R1 dead-zone skip 11:15-13:30"] = dict(hours={29, 89, 269, 329})
V["R1b dead-zone only if rel-vol >= 1.5"] = dict(efilt=lambda d, k, s, a, f, g: k not in DEAD or rv(a, k, f) >= 1.5)
V["R2 rel-vol >= IS p20 (%.2f)" % TH["rv20"]] = dict(efilt=lambda d, k, s, a, f, g: rv(a, k, f) >= TH["rv20"])
V["R2b rel-vol >= IS p35 (%.2f)" % TH["rv35"]] = dict(efilt=lambda d, k, s, a, f, g: rv(a, k, f) >= TH["rv35"])
V["R2c rel-vol >= 1.0"] = dict(efilt=lambda d, k, s, a, f, g: rv(a, k, f) >= 1.0)
V["R3 VA lock: no long below prior VAL / no short above prior VAH"] = dict(efilt=lambda d, k, s, a, f, g: not (s > 0 and a["close"][k] < f["val"]) and not (s < 0 and a["close"][k] > f["vah"]))
V["R3b VA acceptance: long needs close > prior VAH, short < prior VAL"] = dict(efilt=lambda d, k, s, a, f, g: (s > 0 and a["close"][k] > f["vah"]) or (s < 0 and a["close"][k] < f["val"]))
V["R3c AMT+ open context lock (open above VAH: longs only; below VAL: shorts only)"] = dict(efilt=lambda d, k, s, a, f, g: va_ctx_open(a, f) in (0, s))
V["R3d skip entry inside prior value area"] = dict(efilt=lambda d, k, s, a, f, g: not (f["val"] <= a["close"][k] <= f["vah"]))
V["R4 compression skip: range-so-far/ATR14 >= IS p20 (%.2f)" % TH["rng20"]] = dict(efilt=lambda d, k, s, a, f, g: rngr(a, k, f) >= TH["rng20"])
V["R4b compression skip: >= IS p35 (%.2f)" % TH["rng35"]] = dict(efilt=lambda d, k, s, a, f, g: rngr(a, k, f) >= TH["rng35"])
V["R5 min sigma >= IS p20 (%.4f%%)" % (100 * TH["sig20"])] = dict(efilt=lambda d, k, s, a, f, g: g >= TH["sig20"])
V["R6 skip Mondays (session-17 carry-over)"] = dict(dayskip=lambda d, f: f["dow"] == 0)
V["R7 VWAP side (close beyond VWAP on the trade side)"] = dict(efilt=lambda d, k, s, a, f, g: s * (a["close"][k] - a["vwap"][k]) > 0)
V["R8 max 2 trades/day"] = dict(maxtr=2)
V["R9 max 1 trade/day"] = dict(maxtr=1)

rows = []; streams = {}
for name, kw in V.items():
    t = noise2.gen(**kw) if kw else base; streams[name] = t
    r = dict(name=name)
    for e in ("IS", "J", "HO24"): r[e] = stats(t, e)
    for e in ("IS", "J"):
        for sz in (25, 50):
            r[f"boot{sz}_{e}"] = eval_boot(t, e, sz); r[f"roll{sz}_{e}"] = eval_roll(t, e, sz)
    r["dJ"] = delta_ci(t, base, "J"); r["dHO"] = delta_ci(t, base, "HO24")
    rows.append(r); print(name, {e: (r[e]["n"], round(r[e]["pf"], 2)) for e in ("IS", "J")}, r["boot25_J"], flush=True)
# combos of IS-picked winners: decided after IS table -> done in combo step below (IS criterion only)
isb = rows[0]["IS"]
elig = [r for r in rows[1:] if r["IS"]["pf"] >= isb["pf"] and r["IS"]["net"] >= .85 * isb["net"] and r["IS"]["n"] >= 300 and r["IS"]["dd"] <= 1.05 * isb["dd"]]
elig.sort(key=lambda r: -(r["IS"]["avg"] / max(r["IS"]["dd"], 1)))
print("IS-eligible:", [r["name"] for r in elig])
# random benchmark, same timing/exits/lock
rb = [noise2.gen(rnd=s) for s in range(30)]
rbs = {e: dict(avg=float(np.mean([stats(x, e)["avg"] for x in rb])), pf=float(np.median([stats(x, e)["pf"] for x in rb])), win=float(np.mean([stats(x, e)["win"] for x in rb])),
               n=float(np.mean([stats(x, e)["n"] for x in rb])), net=float(np.mean([stats(x, e)["net"] for x in rb])), dd=float(np.mean([stats(x, e)["dd"] for x in rb]))) for e in ("IS", "J", "HO24")}
rbs["boot25_J"] = eval_boot(pd.concat(rb[:1]), "J", 25); rbs["boot25_J_med"] = [eval_boot(x, "J", 25, n_paths=200) for x in rb[:10]]
json.dump(dict(rows=rows, TH=TH, rand=rbs, elig=[r["name"] for r in elig]), open(lib.OUT + "/noise_results.json", "w"), indent=1, default=float)
for n_, t in streams.items(): t.to_csv(lib.OUT + "/streams_noise_%s.csv" % n_.split()[0], index=False)
