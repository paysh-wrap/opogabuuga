from gen import *
import pickle
L, E = pickle.load(open("/home/user/days.pkl","rb"))
# 1. VWAP causality: cumulative VWAP must move toward typical price of the current bar and never overshoot it
bad = badb = tot = 0
first_bad = []
for d, a in L:
    tp = (a["high"] + a["low"] + a["close"]) / 3; vw = a["vwap"]
    if abs(vw[0] - tp[0]) > 1e-6: badb += 1
    for k in range(1, 390):
        if np.isnan(vw[k]) or np.isnan(vw[k-1]) or np.isnan(tp[k]): continue
        tot += 1
        dv = vw[k] - vw[k-1]; dt = tp[k] - vw[k-1]
        if (dv * dt < -1e-9) or abs(dv) > abs(dt) + 1e-6:
            bad += 1
            if len(first_bad) < 3: first_bad.append((d, k, vw[k-1], vw[k], tp[k]))
print("VWAP bar0 != typical price days:", badb, "of", len(L))
print("VWAP non-causal steps:", bad, "of", tot, first_bad)
# NaN counts
nn = sum(int(np.isnan(a["close"]).sum()) for _, a in L); print("missing minutes total", nn, "days", len(L))
# 2. gaps / roll days
rows = []
for i in range(1, len(L)):
    d, a = L[i]; pc = L[i-1][1]["close"][389]; g = a["open"][0] / pc - 1
    rows.append((d, L[i-1][0], g))
g = pd.DataFrame(rows, columns=["d", "prev", "gap"])
print("days |gap|>1.5%:", (g.gap.abs() > 0.015).sum())
print(g[g.gap.abs() > 0.015].to_string())
# roll windows: second Thursday-ish of Mar/Jun/Sep/Dec; show gaps in those weeks
g["m"] = g.d.str[5:7]; g["dd"] = g.d.str[8:10].astype(int)
r = g[g.m.isin(["03","06","09","12"]) & (g.dd >= 7) & (g.dd <= 20)]
print("largest |gap| per roll month:")
print(r.assign(a=r.gap.abs()).sort_values("a").groupby(r.d.str[:7]).tail(1).sort_values("d")[["d","prev","gap"]].to_string())
# calendar gaps (missing trading days)
dts = pd.to_datetime(g.d); pr = pd.to_datetime(g.prev); big = (dts - pr).dt.days > 4
print("prev-day jumps > 4 calendar days:", big.sum(), g[big][["d","prev"]].head(20).to_string())
