from gen import *
base = pd.read_csv("base.csv")
rng = np.random.default_rng(1)
def boot_pf(p, n=5000, days=None):
    p = np.asarray(p); out = []
    for _ in range(n):
        out.append(pf(rng.choice(p, len(p))))
    return np.percentile(out, [2.5, 50, 97.5])
def boot_day(t, n=5000):
    g = t.groupby("d").pnl.apply(list).tolist(); out = []
    for _ in range(n):
        idx = rng.integers(0, len(g), len(g)); p = np.concatenate([g[i] for i in idx]); out.append(pf(p))
    return np.percentile(out, [2.5, 50, 97.5])
for lab, t in (("all", base), ("21-23", base[base.d < "2024-01-01"]), ("24-26", base[base.d >= "2024-01-01"])):
    print(lab, "PF", round(pf(t.pnl), 2), "trade-boot CI", boot_pf(t.pnl).round(2), "day-boot CI", boot_day(t).round(2))
# random direction baseline: same entry times, coin-flip side
res = []
for s in range(200):
    t = noise3.gen(rnd=s); res.append((pf(t.pnl), t.pnl.sum(), pf(t[t.d >= "2024-01-01"].pnl)))
r = np.array(res)
print("random-side PF: median %.2f p95 %.2f max %.2f ; net median %.0f p95 %.0f; share >= real PF 1.52: %.3f" % (np.median(r[:,0]), np.percentile(r[:,0],95), r[:,0].max(), np.median(r[:,1]), np.percentile(r[:,1],95), (r[:,0] >= 1.52).mean()))
print("random-side 24-26 PF median %.2f p95 %.2f" % (np.median(r[:,2]), np.percentile(r[:,2],95)))
