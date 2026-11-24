import pickle, numpy as np, pandas as pd
from gen import pf
L, E = pickle.load(open("/home/user/days.pkl","rb")); M = dict(L)
c = pd.read_csv("cand_aug.csv")
# fill checks with correct offsets (idx/exit_idx = close-time minute index; bar k = idx-1)
tp = c[c.outcome == "TP"]; touch = 0
for r in tp.itertuples():
    a = M[r.day]; j = int(r.exit_idx) - 1
    if (r.dir == "LONG" and abs(a["high"][j] - r.tp) < 1e-9) or (r.dir == "SHORT" and abs(a["low"][j] - r.tp) < 1e-9): touch += 1
print("TP exits", len(tp), "touch-only", touch)
gap = 0; gc = 0.0
for r in c[c.outcome == "STOP"].itertuples():
    a = M[r.day]; j = int(r.exit_idx) - 1; o = a["open"][j]
    if (r.dir == "LONG" and o < r.stop) or (r.dir == "SHORT" and o > r.stop): gap += 1; gc += abs(o - r.stop) * 2
print("STOP exits opened through stop", gap, "extra $", round(gc, 1))
adv = np.array([(M[r.day]["open"][int(r.idx)] - r.entry) * (1 if r.dir == "LONG" else -1) for r in c.itertuples()])
print("next-open vs signal close (pos = worse): mean %.3f pts, median %.2f" % (adv.mean(), np.median(adv)))
p2 = c.usd - adv * 2; print("next-open fill: PF=%.2f net=$%.0f" % (pf(p2), p2.sum()))
# re-simulate own direction and random direction with mirrored distances (stop-first, 15-min TIME at close)
def sim(day, k0, entry, sgn, sd, td):
    a = M[day]; stop = entry - sgn * sd; tgt = entry + sgn * td
    for j in range(k0 + 1, min(k0 + 16, 390)):
        lo, hi = a["low"][j], a["high"][j]
        if (sgn > 0 and lo <= stop) or (sgn < 0 and hi >= stop): return -sd
        if (sgn > 0 and hi >= tgt) or (sgn < 0 and lo <= tgt): return td
        if j == k0 + 15: return (a["close"][j] - entry) * sgn
    return (a["close"][min(k0 + 15, 389)] - entry) * sgn
own = []
for r in c.itertuples():
    sgn = 1 if r.dir == "LONG" else -1
    own.append(sim(r.day, int(r.idx) - 1, r.entry, sgn, r.stop_pts, r.tp_pts))
own = np.array(own); print("re-sim own direction matches p1:", np.mean(np.abs(own - c.p1.values) < 1e-6), "PF", round(pf(own * 2 - 2), 2))
rng = np.random.default_rng(11); rp = []; rn = []
flip = []
for r in c.itertuples():
    sgn = -1 if r.dir == "LONG" else 1
    flip.append(sim(r.day, int(r.idx) - 1, r.entry, sgn, r.stop_pts, r.tp_pts))
flip = np.array(flip) * 2 - 2; print("opposite direction (same distances): PF=%.2f net=$%.0f" % (pf(flip), flip.sum()))
for i in range(1000):
    sg = rng.choice([-1, 1], len(c)); x = np.where(sg > 0, own * 2 - 2, flip); rp.append(pf(x)); rn.append(x.sum())
rp = np.array(rp); print("random direction: PF median %.2f p95 %.2f; real PF 1.22 percentile %.1f%%; net median %.0f p95 %.0f" % (np.median(rp), np.percentile(rp, 95), 100 * (rp < 1.22).mean(), np.median(rn), np.percentile(rn, 95)))
# random entry times baseline: same day, random bar 5..29 inside window, random side, same stop/tp distances
rt = []
for i in range(300):
    x = []
    for r in c.itertuples():
        k0 = int(rng.integers(5, 30)); a = M[r.day]; sgn = int(rng.choice([-1, 1]))
        x.append(sim(r.day, k0, a["close"][k0], sgn, r.stop_pts, r.tp_pts) * 2 - 2)
    rt.append(pf(np.array(x)))
rt = np.array(rt); print("random time+side, same stop/TP: PF median %.2f p95 %.2f; share >= 1.22: %.3f" % (np.median(rt), np.percentile(rt, 95), (rt >= 1.22).mean()))
