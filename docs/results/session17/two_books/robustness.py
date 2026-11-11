"""Robustness of the only candidate (momentum guard on NOISE): IS eval sim, neighbours, per-year, placebo on the lock stream. writes out/robust.json"""
import os, json
import numpy as np, pandas as pd
import core as C, feats as F
HERE = os.path.dirname(os.path.abspath(__file__))
data = C.load(); D = data["days"]; f = F.daily(data); r2 = F.shift(f["rsi2"]); r2[0] = 50
guard = lambda th: (lambda i, s, k: not ((s < 0 and r2[i] > th) or (s > 0 and r2[i] < 100 - th)))
out = {"rows": {}}
S = {}
for lk, ln in ((None, "NOISE"), ((100, 10), "NOISE+lock")):
    S[ln] = C.noise(D, lock=lk)
    for th in (80, 85, 90, 95):
        S[f"{ln} + momentum guard {th}/{100-th}"] = C.noise(D, allow=guard(th), lock=lk)
for nm, t in S.items():
    e_is = C.eval_sim(t, start="2019-06-03", end="2023-12-29"); e_is_s = C.eval_sim(t, strict=True, start="2019-06-03", end="2023-12-29")
    e = C.eval_sim(t); es = C.eval_sim(t, strict=True)
    yr = {y: round(float(g.pnl.sum())) for y, g in t.groupby(t.d.str[:4])}
    out["rows"][nm] = dict(IS=C.stats(t, "IS"), HO=C.stats(t, "HO"), ev_is=e_is, evs_is=e_is_s, ev=e, evs=es, years=yr)
    print(f"{nm:38s} IS n{C.stats(t,'IS')['n']} pf{C.stats(t,'IS')['pf']:.2f} eval {e_is['pass_']:.1f}/{e_is['bust']:.1f} | HO n{C.stats(t)['n']} pf{C.stats(t)['pf']:.2f} net{C.stats(t)['net']:.0f} eval {e['pass_']:.1f}/{e['bust']:.1f} strict {es['pass_']:.1f}/{es['bust']:.1f} | {yr}")
# what did the guard remove on HO?
b = S["NOISE+lock"]; g = S["NOISE+lock + momentum guard 90/10"]
idx = {d: i for i, (d, _) in enumerate(D)}
blk = b[[not guard(90)(idx[d], s, 0) for d, s in zip(b.d, b.side)]]
out["blocked"] = {era: C.stats(blk, era) for era in ("IS", "HO")}; print("blocked trades (in the unfiltered lock stream):", out["blocked"])
rng = np.random.default_rng(17); kept = len(g) / len(b); pl = []
for _ in range(300):
    t = b[rng.random(len(b)) < kept]; e = C.eval_sim(t); pl.append((e["pass_"], e["bust"]))
pl = np.array(pl)
out["placebo_lock"] = dict(keep=kept, pass_mean=float(pl[:, 0].mean()), pass_p5=float(np.percentile(pl[:, 0], 5)), pass_p95=float(np.percentile(pl[:, 0], 95)),
                           bust_mean=float(pl[:, 1].mean()), bust_p5=float(np.percentile(pl[:, 1], 5)), bust_p95=float(np.percentile(pl[:, 1], 95)),
                           share_pass_ge=float(np.mean(pl[:, 0] >= C.eval_sim(g)["pass_"])), share_bust_le=float(np.mean(pl[:, 1] <= C.eval_sim(g)["bust"])))
print(out["placebo_lock"])
json.dump(out, open(HERE + "/out/robust.json", "w"), indent=1)
