import json, numpy as np
from study import *
out = {}
base = summ(gen(nd=BASE_ND)); out["A"] = base
for acc in (0.55, 0.60, 0.65, 0.70, 1.0):
    for cov in (0.1, 0.25, 0.5, 1.0):
        rs = []
        for seed in range(4):
            g = bias_gate(acc, cov, seed)
            rs.append(summ(gen(nd=BASE_ND, bn=g, bf=g)))
        avg = {h: {k: float(np.mean([r[h][k] for r in rs])) for k in rs[0][h]} for h in ("IS", "HO")}
        for h in ("IS", "HO"): avg[h]["block"] = 100 * (1 - avg[h]["n"] / base[h]["n"])
        out[f"D acc{int(acc*100)} cov{int(cov*100)}"] = avg
        a, b = avg["IS"], avg["HO"]
        print(f"acc{int(acc*100):3d} cov{int(cov*100):3d} | IS block{a['block']:5.1f}% win{a['win']:5.1f} ${a['usd']:6.0f} bust{a['bust']:5.1f} | HO block{b['block']:5.1f}% n/d{b['tpd']:.2f} win{b['win']:5.1f} PF{b['pf']:.2f} ${b['usd']:6.0f} bust{b['bust']:5.1f}", flush=True)
json.dump(out, open(HERE + "/grid_D.json", "w"), default=float)
