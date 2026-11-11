"""Reproduce the verified NOISE baselines and compare with the session-9 record.
  (a) session-9 original: tools/noise_area.py (independent implementation, 1% stop) vs nz.gen(stop_pct=0.01)  -> must be trade-identical
  (b) session-9 record: IS 727 tr / 44.3% / +15.28 / PF 1.32 ; HO 440 tr / 45.0% / +25.81 / PF 1.33 (per-trade, 1 micro)
  (c) app default ($250 stop = 124 pt, no lock) and preset C ($250 + lock 100->+10)
  (d) trade-for-trade vs the committed session-15 stream docs/results/session15/out/streams/N1_MNQ.csv (lock 100/10) on its window 2021-11..2026-10
writes baseline_check.json and streams/BASE_*.csv"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "/home/user/opogabuuga/docs/results/tools")
import numpy as np, pandas as pd
import nz, noise_area as NA

os.makedirs(HERE + "/streams", exist_ok=True)
out = {}
ref_days = NA.load_days(nz.CSV)
ref = NA.run(ref_days, hard=0.01)
ref = ref[(ref.d >= nz.START) & (ref.d <= nz.END)].reset_index(drop=True)
mine = nz.gen(stop_usd=None, stop_pct=0.01)
same = len(ref) == len(mine) and np.allclose(ref.pnl.values, mine.pnl.values, atol=0.005) and (ref.d.values == mine.d.values).all()
out["session9_1pct"] = dict(identical_to_tools_noise_area=bool(same), n_ref=len(ref), n_mine=len(mine), IS=nz.stats(mine, "IS"), HO=nz.stats(mine, "HO"),
                            ref_IS=nz.stats(ref, "IS"), ref_HO=nz.stats(ref, "HO"))
mine.to_csv(HERE + "/streams/BASE_s9_1pct.csv", index=False)
b1 = nz.gen(); b1.to_csv(HERE + "/streams/BASE_250.csv", index=False)
b2 = nz.gen(lock=(100, 10)); b2.to_csv(HERE + "/streams/BASE_250_lock100_10.csv", index=False)
out["app_default_250"] = dict(IS=nz.stats(b1, "IS"), HO=nz.stats(b1, "HO"))
out["preset_C_250_lock"] = dict(IS=nz.stats(b2, "IS"), HO=nz.stats(b2, "HO"))
n1 = pd.read_csv("/home/user/opogabuuga/docs/results/session15/out/streams/N1_MNQ.csv", dtype={"d": str})
a = b2[(b2.d >= n1.d.min()) & (b2.d <= n1.d.max())].reset_index(drop=True)
out["vs_session15_N1"] = dict(window=[n1.d.min(), n1.d.max()], n_s15=len(n1), n_mine=len(a),
                              identical=bool(len(a) == len(n1) and (a.d.values == n1.d.values).all() and np.allclose(a.pnl.values, n1.pnl.values, atol=0.005)),
                              net_s15=float(n1.pnl.sum()), net_mine=float(a.pnl.sum()))
json.dump(out, open(HERE + "/baseline_check.json", "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
