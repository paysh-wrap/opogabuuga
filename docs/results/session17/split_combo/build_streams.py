"""builds NOISE trade stream + Duo candidates from the day cache; usage: python3 build_streams.py <cache dir>  (writes noise_mnq.pkl, duo.pkl there; also small noise_mnq.csv here)"""
import sys, pickle, time
import numpy as np, pandas as pd
import sim
cd = sys.argv[1]; t0 = time.time()
mnq = pickle.load(open(f"{cd}/mnq_days.pkl", "rb"))
nt = sim.noise_gen(mnq, "MNQ"); nt.to_csv("noise_mnq_stream.csv", index=False)
pickle.dump(nt, open(f"{cd}/noise_mnq.pkl", "wb"))
print("noise trades", len(nt), nt.d.min(), nt.d.max(), round(time.time() - t0), "s")
duo = {"MNQ": sim.duo_candidates(mnq, "MNQ")}
import os
if os.path.exists(f"{cd}/mgc_days.pkl"):
    duo["MGC"] = sim.duo_candidates(pickle.load(open(f"{cd}/mgc_days.pkl", "rb")), "MGC")
pickle.dump(duo, open(f"{cd}/duo.pkl", "wb"))
print({m: (len(v["dates"]), int((~np.isnan(v["cand"][:, :, 0])).sum())) for m, v in duo.items()}, round(time.time() - t0), "s")
