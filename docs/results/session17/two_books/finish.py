"""Session 17 two-books study - final checks added after reviewing the stopped helper's outputs. writes out/finish.json
(1) always-long / always-short day-trade benchmarks (is the Markov 'bias' just the up-drift?)  (2) momentum guard split by side
(3) permutation test: are the trades the guard blocks worse than random NOISE(+lock) trades?  (4) K6 per-year HO eval and day-level bootstrap."""
import os, json
import numpy as np, pandas as pd
import core as C, feats as F
HERE = os.path.dirname(os.path.abspath(__file__))
data = C.load(); D = data["days"]; f = F.daily(data); r2 = F.shift(f["rsi2"]); r2[0] = 50; HP = C.stop_pts(250.0)
res = {}
# (1) benchmarks
for nm, s in (("always long 09:31 -> 16:00", 1), ("always short 09:31 -> 16:00", -1)):
    out = []
    for i, (d, a) in enumerate(D):
        if i == 0 or f["rollskip"][i] or np.isnan(a["open"][1]): continue
        p, xk, mae = C.walk(a, s, 1, HP, None, 390); out.append((d, s, 1, xk, p, mae))
    t = pd.DataFrame(out, columns=["d", "side", "ek", "xk", "pnl", "mae"]); r = C.row(nm, t); res[nm] = r; print(C.fmt(r))
# (2) guard by side, with lock
g_short = lambda i, s, k: not (s < 0 and r2[i] > 90)
g_long = lambda i, s, k: not (s > 0 and r2[i] < 10)
for nm, fn in (("NOISE+lock, only 'no short after RSI2 > 90'", g_short), ("NOISE+lock, only 'no long after RSI2 < 10'", g_long)):
    r = C.row(nm, C.noise(D, allow=fn, lock=(100, 10))); res[nm] = r; print(C.fmt(r))
# (3) permutation test of the blocked trades (stream with lock)
b = C.noise(D, lock=(100, 10)); idx = {d: i for i, (d, _) in enumerate(D)}
blk = np.array([(s < 0 and r2[idx[d]] > 90) or (s > 0 and r2[idx[d]] < 10) for d, s in zip(b.d, b.side)])
rng = np.random.default_rng(17); perm = {}
for era in ("IS", "HO"):
    m = (b.d <= C.SPLIT).values if era == "IS" else (b.d > C.SPLIT).values
    x = b.pnl.values[m]; k = blk[m]; obs = x[k].mean()
    sims = np.array([x[rng.permutation(len(x))[:k.sum()]].mean() for _ in range(5000)])
    perm[era] = dict(blocked=int(k.sum()), of=int(len(x)), blocked_mean=float(obs), all_mean=float(x.mean()), p_value=float(np.mean(sims <= obs)))
res["perm_blocked"] = perm; print(perm)
# (4) K6 vs NOISE+lock: per HO year eval + bootstrap over HO trading days of the net difference
g = C.noise(D, lock=(100, 10), allow=lambda i, s, k: g_short(i, s, k) and g_long(i, s, k))
yr = {}
for y in ("2024", "2025", "2026"):
    st, en = f"{y}-01-01", (f"{y}-12-31" if y != "2026" else C.HO_END)
    yr[y] = dict(lock=C.eval_sim(b, start=st, end=en, horizon=120), k6=C.eval_sim(g, start=st, end=en, horizon=120))
res["k6_years"] = yr; print(json.dumps(yr))
hd = sorted(set(d for d, _ in D if d > C.SPLIT)); pb = b[b.d > C.SPLIT].groupby("d").pnl.sum(); pg = g[g.d > C.SPLIT].groupby("d").pnl.sum()
diff = np.array([pg.get(d, 0.0) - pb.get(d, 0.0) for d in hd]); bs = [diff[rng.integers(0, len(diff), len(diff))].sum() for _ in range(5000)]
res["k6_boot"] = dict(net_diff=float(diff.sum()), p5=float(np.percentile(bs, 5)), p95=float(np.percentile(bs, 95)), share_le0=float(np.mean(np.array(bs) <= 0)))
print(res["k6_boot"])
json.dump(res, open(HERE + "/out/finish.json", "w"), indent=1)
