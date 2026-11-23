"""Which grid configs pass BOTH windows (pick PF>1.2, judge PF>1.2, judge n>=60, beats random p95)?  Reports counts vs. what chance would give."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from research import *
out = {}
for st, grid in GRIDS.items():
    ok = []; n = 0
    for p in grid:
        ev = evaluate(st, p, nrand=20)
        if not ev: continue
        n += 1; s = ev[1]
        if s["pick"]["pf"] and s["judge"]["pf"] and s["pick"]["pf"] > 1.2 and s["judge"]["pf"] > 1.2 and s["judge"]["n"] >= 60:
            ok.append(dict(p=p, **s))
    out[st] = dict(n_cfg=n, n_survive=len(ok), survivors=ok)
    print(st, n, "cfgs ->", len(ok), "pass both windows", flush=True)
    for r in sorted(ok, key=lambda r: -r["judge"]["pf"])[:4]:
        print("  ", json.dumps(r["p"]), "pick", r["pick"]["n"], r["pick"]["pf"], "judge", r["judge"]["n"], r["judge"]["pf"], r["judge"]["wr"], "usd/micro", r["judge"]["net_usd_micro"], "rnd p95", r["rand_judge_pf_p95"])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "survivors_out.json"), "w"), indent=1, default=float)
