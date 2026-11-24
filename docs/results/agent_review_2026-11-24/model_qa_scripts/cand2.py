import pickle, numpy as np, pandas as pd
L, E = pickle.load(open("/home/user/days.pkl","rb")); M = dict(L)
c = pd.read_csv("cand_aug.csv")
for off in (-1, 0, 1):
    hit = 0; n = 0
    for r in c[c.outcome == "STOP"].itertuples():
        a = M[r.day]; j = int(r.exit_idx) + off
        if j < 0 or j >= 390: continue
        n += 1; hit += (a["low"][j] <= r.stop) if r.dir == "LONG" else (a["high"][j] >= r.stop)
    print("offset", off, "stop touched on bar", hit, "/", n)
r = c.iloc[1]; a = M[r.day]; print(r.day, r.time, r.idx, r.exit_idx, r.dir, r.entry, r.stop)
for j in range(int(r.idx) - 1, int(r.exit_idx) + 2): print(j, a["open"][j], a["high"][j], a["low"][j], a["close"][j])
