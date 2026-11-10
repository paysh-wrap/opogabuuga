import json, itertools, numpy as np
from study import *
out = {}
def run(name, **kw):
    t = gen(nd=BASE_ND, **kw); r = summ(t); out[name] = r; print(line(name, r), flush=True); return r
run("A")
def apply(mk, which, **kw):
    g = mk
    if which == "N": return dict(bn=g, **kw)
    if which == "F": return dict(bf=g, **kw)
    return dict(bn=g, bf=g, **kw)
for j in ("mso1", "mso5"):
    for m in ("agree", "noopp"):
        for w in "NFB": run(f"C MSO structure {j} {m} {w}", **apply(mso(j, m), w))
for j in ("mso1", "mso5"):
    for wd in (15, 30, 60, 120):
        for w in "NFB": run(f"C MSO divergence {j} nodiv{wd} {w}", **apply(mso(j, "nodiv", wd), w))
    for wd in (30, 120): run(f"C MSO divergence {j} needdiv{wd} F", **apply(mso(j, "needdiv", wd), "F"))
for j in ("fr15", "fr60"):
    for m in ("agree", "noopp"):
        for w in "NFB": run(f"C Fractal {j} {m} {w}", **apply(frac(j, m), w))
# D: AI bias, simulated accuracy (no real ledger rows exist: AI key not connected)
for acc in (0.55, 0.60, 0.65, 0.70, 1.0):
    for cov in (1.0, 0.5):
        rs = []
        for seed in range(6):
            g = bias_gate(acc, cov, seed); rs.append(summ(gen(nd=BASE_ND, **apply(g, "B"))))
        avg = {h: {k: float(np.mean([r[h][k] for r in rs])) for k in rs[0][h]} for h in ("IS", "HO")}
        out[f"D AI acc{int(acc*100)} cov{int(cov*100)}"] = avg; print(line(f"D AI acc{int(acc*100)} cov{int(cov*100)} (6 seeds)", avg), flush=True)
json.dump(out, open(HERE + "/grid_C_D.json", "w"), default=float)
