"""Stage 2: IS-only selection per family (rule fixed BEFORE looking at held-out: eligible = IS PF >= its base's IS PF, IS net >= 90% of base,
IS max drawdown <= 105% of base; pick = best IS edge ratio 2*mean/sd^2), then best-2-families combination on the 'lock' base.
Writes stage2.json, streams/COMBO_*.csv.  Needs study.json from run_study.py."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pandas as pd
import nz, sim
import run_study as RS

S = json.load(open(HERE + "/study.json"))["variants"]


def load(n): return pd.read_csv(f"{HERE}/streams/{S[n]['file']}.csv", dtype={"d": str})


def pick(base_name, names):
    b = S[base_name]["IS"]; sel = {}
    for n in names:
        r = S[n]; i = r["IS"]
        ok = i["pf"] >= b["pf"] and i["net"] >= 0.9 * b["net"] and i["dd"] <= 1.05 * b["dd"] and i["n"] >= 100
        sel.setdefault(r["fam"], []).append((n, i["ratio"], bool(ok)))
    chosen = {}
    for f, lst in sel.items():
        el = [x for x in lst if x[2]]
        if el: chosen[f] = max(el, key=lambda x: x[1])[0]
    return chosen, sel


out = {"selected": {}, "eligibility": {}}
for ln in ("nolock", "lock"):
    base = f"BASE [{ln}]"
    names = [n for n in S if n.endswith(f"[{ln}]") and S[n]["fam"] != "base"]
    if ln == "nolock":
        names += [n for n in S if S[n]["fam"] in ("lock", "tlock", "stop") and not n.startswith("session-9")]
    ch, el = pick(base, names)
    out["selected"][ln] = ch; out["eligibility"][ln] = {f: l for f, l in el.items()}
# combination on the lock base: top-2 distinct filter families by IS ratio (families that are not 'lock'/'tlock'/'stop'), applied together
ln = "lock"; ch = out["selected"][ln]
rk = sorted(((S[n]["IS"]["ratio"], f, n) for f, n in ch.items() if f in ("N10-12", "vwap", "hours", "norev", "width", "addon-1530") and S[n]["IS"]["ratio"] > S[f"BASE [{ln}]"]["IS"]["ratio"]), reverse=True)
out["ranked"] = [(f, n, r) for r, f, n in rk]
ALLV = {}
for l2 in RS.LOCKS: ALLV.update(RS.fam_variants(l2))
import numpy as np
b = nz.gen(lock=RS.LOCKS["lock"]); bi = b[b.d <= nz.SPLIT]
for q in (10, 20, 30, 40):
    w = float(bi.width.quantile(q / 100)); s_ = float(bi.sigk.quantile(q / 100))
    ALLV[f"min band width >= IS p{q} ({w:.0f} pt) [lock]"] = ("width", dict(lock=RS.LOCKS["lock"], minw_pts=w))
    ALLV[f"min sigma >= IS p{q} ({100*s_:.2f}%) [lock]"] = ("width", dict(lock=RS.LOCKS["lock"], min_sig=s_))
combos = {}
if len(rk) >= 2:
    kw = {}; names = []
    for _, f, n in rk[:2]:
        k = dict(ALLV[n][1]); names.append(n)
        for kk, vv in k.items():
            if kk == "dayskip" and "dayskip" in kw: kw[kk] = (lambda a, b_: (lambda f_: a(f_) or b_(f_)))(kw[kk], vv)
            else: kw[kk] = vv
    combos["COMBO(best-2 IS) = " + " + ".join(x.replace(" [lock]", "") for x in names)] = kw
if len(rk) >= 3:
    kw = {}; names = []
    for _, f, n in rk[:3]:
        k = dict(ALLV[n][1]); names.append(n)
        for kk, vv in k.items():
            if kk == "dayskip" and "dayskip" in kw: kw[kk] = (lambda a, b_: (lambda f_: a(f_) or b_(f_)))(kw[kk], vv)
            else: kw[kk] = vv
    combos["COMBO(best-3 IS) = " + " + ".join(x.replace(" [lock]", "") for x in names)] = kw
res = {}
for cn, kw in combos.items():
    t = nz.gen(**kw); fn = "COMBO_" + str(len(res)); t.to_csv(f"{HERE}/streams/{fn}.csv", index=False)
    o = dict(name=cn, fam="combo", file=fn)
    for e in ("IS", "HO"):
        o[e] = nz.stats(t, e); o[e]["roll"] = sim.eval_roll(t, e); o[e]["boot"] = sim.eval_boot(t, e)
        x = nz.era(t, e); o[e]["ratio"] = float(2 * x.pnl.mean() / x.pnl.std() ** 2 * 1000)
    o["HO"]["roll_strict"] = sim.eval_roll(t, "HO", strict=True)
    res[cn] = o
out["combos"] = res
json.dump(out, open(HERE + "/stage2.json", "w"), indent=1, default=float)
print(json.dumps({k: out[k] for k in ("selected", "ranked")}, indent=1)); print({k: (v["HO"]["roll"], v["HO"]["net"], v["IS"]["net"]) for k, v in res.items()})
