import pickle, numpy as np, pandas as pd
from gen import pf
L, E = pickle.load(open("/home/user/days.pkl","rb")); M = dict(L)
c = pd.read_csv("/home/user/paytience/docs/results/pass_faster_c125/streams_candace_base.csv")
print("rows", len(c), "outcomes", c.outcome.value_counts().to_dict(), "grades", c.grade.value_counts().to_dict())
print("p1==pts share", (c.p1 == c.pts).mean(), "stop_pts max", c.stop_pts.max(), "time range", c.time.min(), c.time.max())
c["usd"] = c.p1 * 2 - 2
def s(t, lab):
    p = t.usd.values; return f"{lab:12s} n={len(p):3d} win={100*(p>0).mean():5.1f}% PF={pf(p):4.2f} avg=${p.mean():6.2f} net=${p.sum():7.0f}"
print(s(c, "ALL")); print(s(c[c.day < "2024"], "2021-23")); print(s(c[c.day >= "2024"], "2024-26"))
for y, g in c.groupby(c.day.str[:4]): print(s(g, y))
for gname, g in c.groupby("grade"): print(s(g, "grade " + gname))
# cost sensitivity
for extra in (1, 2, 3):
    p = c.usd - extra; print(f"+${extra} RT: PF={pf(p):.2f} net=${p.sum():.0f}  21-23 PF={pf(p[c.day<'2024']):.2f}  24-26 PF={pf(p[c.day>='2024']):.2f}")
# bootstrap
rng = np.random.default_rng(5)
def bci(p, n=10000):
    p = np.asarray(p); return np.percentile([pf(rng.choice(p, len(p))) for _ in range(n)], [2.5, 50, 97.5]).round(2), np.mean([rng.choice(p, len(p)).sum() <= 0 for _ in range(n)])
for lab, t in (("ALL", c), ("21-23", c[c.day < "2024"]), ("24-26", c[c.day >= "2024"])):
    ci, ploss = bci(t.usd); print(lab, "PF CI", ci, "P(net<=0)", round(ploss, 3))
# TP touch-only fills
tp = c[c.outcome == "TP"]; touch = 0
for r in tp.itertuples():
    a = M[r.day]; j = int(r.exit_idx); hi, lo = a["high"][j], a["low"][j]
    if (r.dir == "LONG" and abs(hi - r.tp) < 1e-9) or (r.dir == "SHORT" and abs(lo - r.tp) < 1e-9): touch += 1
print("TP exits", len(tp), "touch-only (bar extreme == TP)", touch)
# stop exits where bar opened beyond stop (gap through)
st_ = c[c.outcome == "STOP"]; gap = 0; gapcost = 0.0
for r in st_.itertuples():
    a = M[r.day]; j = int(r.exit_idx); o = a["open"][j]
    if (r.dir == "LONG" and o < r.stop) or (r.dir == "SHORT" and o > r.stop): gap += 1; gapcost += abs(o - r.stop) * 2
print("STOP exits", len(st_), "opened through stop", gap, "extra $", round(gapcost, 1))
# entry at signal close vs next bar open
d_ = []
for r in c.itertuples():
    a = M[r.day]; k = int(r.idx); sgn = 1 if r.dir == "LONG" else -1
    d_.append((a["open"][k + 1] - r.entry) * sgn)
d_ = np.array(d_); print("next-open minus signal close, adverse pts: mean %.2f median %.2f (pos = worse fill)" % (d_.mean(), np.median(d_)))
c["adv_next"] = d_
p2 = c.usd - c.adv_next * 2; print("if filled at next bar open (+cost): PF=%.2f net=$%.0f" % (pf(p2), p2.sum()))
c.to_csv("cand_aug.csv", index=False)
