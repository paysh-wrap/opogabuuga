import pickle, numpy as np, pandas as pd
from gen import pf
L, E = pickle.load(open("/home/user/days.pkl","rb")); M = dict(L)
t = pd.read_csv("/home/user/paytience/docs/results/new_edge/scripts/trades_lastmom239.csv"); t["usd"] = t.pts * 2 - 2
a = pd.read_csv("/home/user/paytience/docs/results/new_edge/late_leg_sizes/trades_app.csv"); print("app cols", list(a.columns), len(a))
def s(x, lab): p = x.usd.values; return f"{lab:10s} n={len(p):3d} win={100*(p>0).mean():5.1f}% PF={pf(p):4.2f} avg=${p.mean():6.2f} net=${p.sum():6.0f}"
print(s(t, "ALL")); print(s(t[t.day < "2024"], "pick")); print(s(t[t.day >= "2024"], "judge"))
for y, g in t.groupby(t.day.str[:4]): print(s(g, y))
rng = np.random.default_rng(3)
for lab, x in (("pick", t[t.day < "2024"]), ("judge", t[t.day >= "2024"])):
    p = x.usd.values; b = [pf(rng.choice(p, len(p))) for _ in range(10000)]
    print(lab, "PF CI", np.percentile(b, [2.5, 50, 97.5]).round(2), "P(net<=0)", np.mean([rng.choice(p, len(p)).sum() <= 0 for _ in range(4000)]))
# opposite-direction re-sim (entry open of bar idx, stop 60 first, flat close of 389)
def sim(day, k0, sgn, sd=60.0):
    x = M[day]; e = x["open"][k0]; stop = e - sgn * sd
    for j in range(k0, 390):
        if (sgn > 0 and x["low"][j] <= stop) or (sgn < 0 and x["high"][j] >= stop): return (min(stop, x["open"][j]) - e) * sgn if sgn > 0 else (e - max(stop, x["open"][j]))
    return (x["close"][389] - e) * sgn
own = np.array([sim(r.day, int(r.idx), int(r.side)) for r in t.itertuples()])
print("re-sim own matches pts (approx, slippage aside):", np.mean(np.abs(own - t.pts.values) < 0.6))
flip = np.array([sim(r.day, int(r.idx), -int(r.side)) for r in t.itertuples()]) * 2 - 2
J = (t.day >= "2024").values
ownu = own * 2 - 2
rp = []
for i in range(2000):
    sg = rng.choice([True, False], len(t)); x = np.where(sg, ownu, flip)[J]; rp.append(pf(x))
print("judge random-direction PF median %.2f p95 %.2f, real judge PF %.2f" % (np.median(rp), np.percentile(rp, 95), pf(ownu[J])))
# residual: days NOISE is flat at 15:00 and does not enter at the 15:00 check
nb = pd.read_csv("base.csv")
busy = set()
for r in nb.itertuples():
    if r.ek <= 330 and r.xk > 330: busy.add(r.d)
t["noise_busy"] = t.day.isin(busy)
for lab, x in (("judge, NOISE flat", t[(t.day >= "2024") & ~t.noise_busy]), ("judge, NOISE busy", t[(t.day >= "2024") & t.noise_busy]), ("pick, NOISE flat", t[(t.day < "2024") & ~t.noise_busy])):
    print(s(x, lab))
