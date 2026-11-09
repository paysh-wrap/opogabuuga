"""5y: NOISE (1 micro) + PM fade with band width M (entry beyond VWAP ± M·sd, stop M·sd beyond entry) at 1 or 2 micros.
Uses run_b.py (agent B, verified trade-for-trade) helpers. usage: fade_settings.py MNQ_5Y.csv"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_b as B  # noqa: E402
sys.path.insert(0, __file__.rsplit("/docs/", 1)[0] + "/docs/results/tools")
import noise_area as NA, sim25k  # noqa: E402

def pm(days, noise_days, M):
    out = []
    for d, a in days:
        if d < B.START or d > B.END or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + M * sd else (1 if c[k] < vw[k] - M * sd else 0)
            if not s: continue
            e = o[k + 1] + s * B.TICK; tgt = vw[k]
            if (tgt - e) * s < 4 * B.TICK: break
            p, _ = B.walk2(s, e, e - s * M * sd, tgt, h, l, o, c, k + 1, 386)
            out.append((d, p)); break
    return pd.DataFrame(out, columns=["d", "pnl"])

days = NA.load_days(sys.argv[1])
nt = B.noise_t(days); nt = nt[(nt.d >= B.START) & (nt.d <= B.END)][["d", "pnl"]]
nd = set(nt.d); nsess = sum(1 for d, _ in days if B.START <= d <= B.END)
H = (("5y", B.START, B.END), ("21-23", "2021-11-01", "2023-12-31"), ("24-26", "2024-01-01", B.END))
print("set | fade trades | win | total 5y | PF | maxDD | worst day | " + " | ".join(f"{h} pass/bust value" for h, _, _ in H) + " | fade $ 21-23 / 24-26 / losing yrs")
for M in (1.5, 2.0, 2.5, 3.0):
    f1 = pm(days, nd, M)
    for q in (1, 2):
        fq = f1.assign(pnl=f1.pnl * q)
        t = pd.concat([nt, fq]).sort_values("d", kind="stable").reset_index(drop=True)
        w = t.pnl > 0; eq = t.pnl.cumsum()
        cells = []
        for lab, a, b in H:
            fn = f"/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/fs_{M}_{q}.csv"; t.to_csv(fn, index=False)
            s = B.simsum(sim25k.run("Pro", fn, dll_funded=600, start=a, end=b))
            cells.append(f"{s['pass_']:.0%}/{s['bust']:.0%} ${s['val']:.0f}")
        yr = fq.groupby(fq.d.str[:4]).pnl.sum()
        h1 = fq[fq.d < "2024"].pnl.sum(); h2 = fq[fq.d >= "2024"].pnl.sum()
        print(f"NOISE + fade {M}sd x{q} | {len(f1)} | {(f1.pnl>0).mean():.0%} | ${t.pnl.sum():.0f} | {t.pnl[w].sum()/-t.pnl[~w].sum():.2f} | "
              f"{(eq-eq.cummax()).min():.0f} | {t.groupby('d').pnl.sum().min():.0f} | " + " | ".join(cells) +
              f" | {h1:.0f} / {h2:.0f} / {','.join(yr[yr<0].index) or 'none'}")
