"""B2 (session 20): confirm the SHIPPED config reproduces the session-19 numbers.
Variants: NOISE preset C + Mondays off (R6) alone; + PM_FADE trading Monday afternoons (fade sees only 'NOISE did not trade');
+ PM_FADE also skipping Mondays (fade respects noise_cfg.skip_weekdays); and the pre-fix default (no lock + Mondays off + fade on Mondays).
Same lib / noise2 / fade2 generators as the session-19 refine study.  Writes shipped_results.json."""
import json, numpy as np, pandas as pd
import lib, noise2, fade2
from lib import stats, eval_boot
lib.RANGES["ALL"] = (lib.S0, lib.J1)
D, F, moves = noise2.data()
mon = lambda d, f: f["dow"] == 0
def combo(n, fz):
    if fz is None: return n
    return pd.concat([n[["d", "pnl", "mae"]], fz[["d", "pnl", "mae"]]]).sort_values("d", kind="stable").reset_index(drop=True)
nC = noise2.gen(dayskip=mon)                     # preset C + Mondays off
nL = noise2.gen(dayskip=mon, lock=None)          # no lock + Mondays off (pre-fix plan default)
fade_mon = fade2.gen(set(nC.d))                  # fade on every day NOISE did not trade (incl. Mondays)
mondays = {d for d, f in F.items() if f["dow"] == 0}
fade_nomon = fade_mon[~fade_mon.d.isin(mondays)].reset_index(drop=True)
fade_mon_L = fade2.gen(set(nL.d))
V = {"S0 NOISE C + Mon off, fade OFF": combo(nC, None),
     "S1 NOISE C + Mon off, fade ON (fade trades Mondays)": combo(nC, fade_mon),
     "S2 NOISE C + Mon off, fade ON (fade skips Mondays)": combo(nC, fade_nomon),
     "S3 pre-fix default: NOISE no lock + Mon off, fade ON (Mondays)": combo(nL, fade_mon_L),
     "S4 NOISE no lock + Mon off, fade OFF": combo(nL, None)}
rows = []
for name, t in V.items():
    r = dict(name=name)
    for e in ("IS", "J", "ALL"):
        r[e] = stats(t, e)
        for sz, n in ((25, 1), (50, 2)): r[f"boot{sz}_{e}"] = eval_boot(t, e, sz, n=n)
    rows.append(r); print(name, {e: (r[e]["n"], round(r[e]["win"], 1), round(r[e]["pf"], 2), round(r[e]["net"])) for e in ("IS", "J", "ALL")},
                          {k: (round(v["pass_"]), round(v["bust"])) for k, v in r.items() if k.startswith("boot")}, flush=True)
json.dump(dict(rows=rows), open(lib.OUT + "/shipped_results.json", "w"), indent=1, default=float)
# section-4 protocol (400 paths, cap 500) on ALL 7.5 yr, so the preset cards can be checked like for like
sec4 = []
for name, t in V.items():
    r = dict(name=name)
    for size, n in ((25, 1), (50, 1), (50, 2), (100, 2), (150, 3), (150, 4)):
        for e in ("ALL", "IS", "J"): r[f"{size}x{n}_{e}"] = eval_boot(t, e, size, n_paths=400, cap=500, n=n)
    sec4.append(r); print("sec4", name, {k: (round(v["pass_"]), round(v["bust"])) for k, v in r.items() if k.endswith("_ALL")}, flush=True)
json.dump(dict(rows=rows, sec4=sec4), open(lib.OUT + "/shipped_results.json", "w"), indent=1, default=float)
