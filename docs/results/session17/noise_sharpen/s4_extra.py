"""EXPLORATORY (post-hoc, written after the held-out tables were visible - NOT part of the IS-only selection, label it so):
preset C + skip-Monday + min-sigma floor (the 2nd and 3rd IS-ranked families of the pre-registered ranking, instead of the pre-registered top-2 hours+Monday).
writes extra.json, streams/EXTRA_*.csv, RESULTS_extra.md"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd
import nz, sim, run_study as RS, s3_paired as P

S = json.load(open(HERE + "/study.json"))["variants"]
b = nz.gen(lock=(100, 10)); sg = float(b[b.d <= nz.SPLIT].sigk.quantile(0.2))
V = {"EXPLORATORY preset C + skip Monday + min sigma p20 [lock]": dict(lock=(100, 10), dayskip=RS._mon, min_sig=sg),
     "EXPLORATORY preset C + min sigma p20 + no flip after any exit [lock]": dict(lock=(100, 10), min_sig=sg, norev="any")}
out = {}; rows = []
base = pd.read_csv(f"{HERE}/streams/{S['BASE [lock]']['file']}.csv", dtype={"d": str})
for n, kw in V.items():
    t = nz.gen(**kw); fn = "EXTRA_" + str(len(out)); t.to_csv(f"{HERE}/streams/{fn}.csv", index=False)
    o = dict(file=fn)
    for e in ("IS", "HO"):
        o[e] = nz.stats(t, e); o[e]["roll"] = sim.eval_roll(t, e); o[e]["boot"] = sim.eval_boot(t, e)
    o["HO"]["roll_strict"] = sim.eval_roll(t, "HO", strict=True); o["dnet"] = sim.delta_ci(t, base, "HO")
    _, pr = P.job((n, fn, S["BASE [lock]"]["file"])); o["paired"] = pr
    out[n] = o; h, i = o["HO"], o["IS"]
    rows.append(f"| {n} | {h['n']} | {h['win']:.1f} | {h['avg']:.1f} | {h['net']:,.0f} | {h['dd']:,.0f} | {h['pf']:.2f} | {h['roll']['pass_']:.1f} / {h['roll']['bust']:.1f} / {h['roll']['open_']:.1f} | {h['roll']['med']:.0f} | "
                f"{h['boot']['pass_']:.1f} / {h['boot']['bust']:.1f} ({h['boot']['med']:.0f}) | {h['roll_strict']['pass_']:.1f} / {h['roll_strict']['bust']:.1f} | {o['dnet'][0]:+,.0f} [{o['dnet'][1]:+,.0f}, {o['dnet'][2]:+,.0f}] | {i['pf']:.2f} ({i['net']:,.0f}) | dPASS {pr['dpass']:+.1f} [{pr['dpass_lo']:+.1f},{pr['dpass_hi']:+.1f}], dBUST {pr['dbust']:+.1f} [{pr['dbust_lo']:+.1f},{pr['dbust_hi']:+.1f}] |\n")
json.dump(out, open(HERE + "/extra.json", "w"), indent=1, default=float)
hd = "| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs preset C [95% CI] | IS PF (net) | paired eval diff vs preset C |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
open(HERE + "/RESULTS_extra.md", "w").write("### T14 exploratory combination (post-hoc, not IS-selected)\n" + hd + "".join(rows)); print(hd + "".join(rows))
