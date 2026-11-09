import sys, os, itertools, json
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
R = "/home/user/opogabuuga/docs/results"
sys.path.insert(0, R + "/session10/five_year"); sys.path.insert(0, R + "/tools")
import run_b as B, noise_area as NA, sim25k
DATA = "/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/data/mnq_5y.csv"
NS = [150,200,250,300,350,400,520]; FS = [100,150,200,250,300,350,400]
pts = lambda usd: (usd - 2) / 2
class Pts:
    def __init__(s, p): s.p = p
    def __bool__(s): return True
    def __rmul__(s, pos): return _P(pos * s.p)
class _P:
    def __init__(s, v): s.v = v
    def __mul__(s, entry): return s.v
def pm_all(days, dist):
    out = []
    for d, a in days:
        if d < B.START or d > B.END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * B.TICK; tgt = vw[k]
            if (tgt - e) * s < 4 * B.TICK: break
            p, _ = B.walk2(s, e, e - s * dist, tgt, h, l, o, c, k + 1, 386)
            out.append((d, p)); break
    return pd.DataFrame(out, columns=["d", "pnl"])
H = (("5y", B.START, B.END), ("H1", "2021-11-01", "2023-12-31"), ("H2", "2024-01-01", B.END))
def sim(job):
    ns, fs, t = job
    fn = f"tmp/t_{ns}_{fs}.csv"; t.to_csv(fn, index=False)
    r = {}
    for lab, a, b in H:
        s = B.simsum(sim25k.run("Pro", fn, dll_funded=600, start=a, end=b))
        r[lab] = (s["pass_"], s["bust"], s["val"])
    return ns, fs, r
if __name__ == "__main__":
    os.makedirs("tmp", exist_ok=True)
    days = NA.load_days(DATA)
    f = lambda t: t[(t.d >= B.START) & (t.d <= B.END)][["d", "pnl"]]
    noise = {n: f(B.noise_t(days, hard=Pts(pts(n)))) for n in NS}
    fade = {x: pm_all(days, pts(x)) for x in FS}
    jobs = []; stats = {}
    for n, x in itertools.product(NS, FS):
        nt = noise[n]; ft = fade[x]; ft = ft[~ft.d.isin(set(nt.d))]
        t = pd.concat([nt, ft]).sort_values("d", kind="stable").reset_index(drop=True)
        w = t.pnl > 0; eq = t.pnl.cumsum(); yr = t.groupby(t.d.str[:4]).pnl.sum()
        stats[(n, x)] = dict(trades=len(t), win=w.mean(), total=t.pnl.sum(), pf=t.pnl[w].sum() / -t.pnl[~w].sum(),
            dd=(eq - eq.cummax()).min(), wd=t.groupby("d").pnl.sum().min(), ly=",".join(yr[yr < 0].index) or "none")
        jobs.append((n, x, t))
    with ProcessPoolExecutor(8) as ex: res = list(ex.map(sim, jobs))
    rows = []
    for n, x, r in res: rows.append(dict(ns=n, fs=x, **stats[(n, x)], **{f"{k}_{m}": v for k, (p, b, v_) in r.items() for m, v in (("p", p), ("b", b), ("v", v_))}))
    pd.DataFrame(rows).to_csv("grid.csv", index=False)
