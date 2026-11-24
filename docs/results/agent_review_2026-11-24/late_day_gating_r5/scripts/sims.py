import sys, os, json, glob; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pandas as pd, harness5 as H
PLAN = {50: (2, 667), 150: (4, 2250)}      # built sizes (late_leg_sizes picks): 2 micros brake to 1 below $667 cushion; 4 micros brake to 1 below $2,250
out = {}
files = {os.path.basename(f).split("_")[0]: f for f in sorted(glob.glob(HERE + "/legsets/*_app.csv"))}
for k in (50, 150):
    ng, br = PLAN[k]
    for name in ["base"] + list(files):
        H.LEG[0] = pd.read_csv(files[name]) if name != "base" else pd.read_csv(files["G0"]); S = H.sim(k)
        c = H.cfg(k, **H.BUILT[k]); c["ng"] = ng if name != "base" else 0; c["gbands"] = ((br / H.MLL[k], 1),)
        m = H.metrics(S, c)
        out[f"{k}|{name}"] = {w: dict(pass_=round(float(m[w]["pass_"]), 1), med=float(m[w]["med"]), stuck=round(float(m[w]["stuck_bust"]), 1)) for w in ("ALL", "PICK", "JUDGE")} | dict(profit=round(float(m["profit"])), dd=round(float(m["dd"])), hy_min=float(m["hy_min"]), n_leg=0 if name == "base" else len(H.LEG[0]))
        print(k, name, out[f"{k}|{name}"], flush=True)
json.dump(out, open(HERE + "/../sim_results.json", "w"), indent=1)
