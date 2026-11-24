from gen import *
b = pd.read_csv("base.csv"); rng = np.random.default_rng(9)
def ci(p, n=10000):
    p = np.asarray(p); bs = [pf(rng.choice(p, len(p))) for _ in range(n)]
    return np.percentile(bs, [2.5, 50, 97.5]).round(2), round(float(np.mean([rng.choice(p, len(p)).sum() <= 0 for _ in range(3000)])), 3)
for lab, lo, hi in (("last 12m 2025-11-06..", "2025-11-06", "2099"), ("since mid-2024", "2024-07-01", "2099"), ("2025 only", "2025-01-01", "2025-12-31"), ("2021-10..2024-06", "2000", "2024-06-30")):
    x = b[(b.d >= lo) & (b.d <= hi)]; c, pl = ci(x.pnl)
    print(f"{lab:24s} n={len(x)} PF={pf(x.pnl):.2f} CI={c} P(net<=0)={pl}")
# rolling 12-month (252 trading-day) window PF distribution over the 5y
days = sorted(set(pd.read_pickle if False else []))
import pickle; L, _ = pickle.load(open("/home/user/days.pkl", "rb")); D = [d for d, _ in L if d >= "2021-10-21"]
pfs = []
for s in range(0, len(D) - 252, 5):
    x = b[(b.d >= D[s]) & (b.d < D[s + 252])]; pfs.append(pf(x.pnl))
pfs = np.array(pfs); print("rolling 12m PF: min %.2f p10 %.2f median %.2f p90 %.2f max %.2f; share >= 1.72: %.2f; share < 1.0: %.2f" % (pfs.min(), np.percentile(pfs, 10), np.median(pfs), np.percentile(pfs, 90), pfs.max(), (pfs >= 1.72).mean(), (pfs < 1).mean()))
# recent window at higher costs (+$1/+$2/+$4 RT)
x = b[b.d >= "2025-11-06"]; y = b[b.d >= "2024-07-01"]
for e in (0, 1, 2, 4): print(f"+${e} RT: last12m PF {pf(x.pnl - e):.2f} net {x.pnl.sum() - e*len(x):.0f} | since mid-2024 PF {pf(y.pnl - e):.2f} net {y.pnl.sum() - e*len(y):.0f}")
# simulated: if true PF were 1.0 (zero edge), chance a 12m window of n trades shows PF>=1.72 -> demean trades
for lab, xx in (("last12m", x),):
    p = xx.pnl.values - b.pnl.mean()  # zero-mean version using full-sample trade shape
    sims = [pf(rng.choice(b.pnl.values - b.pnl.mean(), len(p))) for _ in range(20000)]
    print("zero-edge null: P(PF>=%.2f with n=%d) = %.4f" % (pf(xx.pnl), len(p), np.mean(np.array(sims) >= pf(xx.pnl))))
    sims2 = [pf(rng.choice(b.pnl.values, len(p))) for _ in range(20000)]
    print("full-sample-edge (PF 1.52) world: P(12m PF>=%.2f) = %.3f ; P(12m PF<1.2) = %.3f" % (pf(xx.pnl), np.mean(np.array(sims2) >= pf(xx.pnl)), np.mean(np.array(sims2) < 1.2)))
