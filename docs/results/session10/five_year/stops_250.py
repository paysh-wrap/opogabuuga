"""5y: NOISE and PM fade with $250 stops (1 micro each). NOISE: fixed 124-pt emergency stop ((250−2)/2).
Fade: CAP = stop min(2·sd, 124 pts) · FIXED = stop exactly 124 pts. usage: stops_250.py MNQ_5Y.csv"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_b as B  # noqa: E402
sys.path.insert(0, __file__.rsplit("/docs/", 1)[0] + "/docs/results/tools")
import noise_area as NA, sim25k  # noqa: E402
PTS = (250 - 2) / 2

class Pts:  # makes pos*hard*entry == pos*PTS inside the NOISE simulator
    def __init__(s, p): s.p = p
    def __bool__(s): return True
    def __rmul__(s, pos): return _P(pos * s.p)
class _P:
    def __init__(s, v): s.v = v
    def __mul__(s, entry): return s.v

def pm(days, noise_days, mode):
    out = []
    for d, a in days:
        if d < B.START or d > B.END or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * B.TICK; tgt = vw[k]
            if (tgt - e) * s < 4 * B.TICK: break
            dist = {"orig": 2 * sd, "cap": min(2 * sd, PTS), "fixed": PTS}[mode]
            p, _ = B.walk2(s, e, e - s * dist, tgt, h, l, o, c, k + 1, 386)
            out.append((d, p)); break
    return pd.DataFrame(out, columns=["d", "pnl"])

days = NA.load_days(sys.argv[1])
H = (("5y", B.START, B.END), ("21-23", "2021-11-01", "2023-12-31"), ("24-26", "2024-01-01", B.END))
f = lambda t: t[(t.d >= B.START) & (t.d <= B.END)][["d", "pnl"]]
n1, n250 = f(B.noise_t(days)), f(B.noise_t(days, hard=Pts(PTS)))
print("set | trades | win | total | PF | maxDD | worst trade | worst day | " + " | ".join(f"{h} pass/bust value" for h, _, _ in H) + " | losing yrs")
for name, nt, mode in (("NOISE 1% + fade orig", n1, "orig"), ("NOISE $250 + fade orig", n250, "orig"),
                       ("NOISE $250 + fade cap $250", n250, "cap"), ("NOISE $250 + fade fixed $250", n250, "fixed"),
                       ("NOISE 1% + fade cap $250", n1, "cap")):
    t = pd.concat([nt, pm(days, set(nt.d), mode)]).sort_values("d", kind="stable").reset_index(drop=True)
    t.to_csv("trades_" + "".join(ch if ch.isalnum() else "_" for ch in name) + ".csv", index=False)
    w = t.pnl > 0; eq = t.pnl.cumsum(); cells = []
    for lab, a, b in H:
        fn = "/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/s250.csv"; t.to_csv(fn, index=False)
        s = B.simsum(sim25k.run("Pro", fn, dll_funded=600, start=a, end=b))
        cells.append(f"{s['pass_']:.0%}/{s['bust']:.0%} ${s['val']:.0f}")
    yr = t.groupby(t.d.str[:4]).pnl.sum()
    print(f"{name} | {len(t)} | {w.mean():.1%} | ${t.pnl.sum():.0f} | {t.pnl[w].sum()/-t.pnl[~w].sum():.2f} | {(eq-eq.cummax()).min():.0f} | "
          f"{t.pnl.min():.0f} | {t.groupby('d').pnl.sum().min():.0f} | " + " | ".join(cells) + f" | {','.join(yr[yr<0].index) or 'none'}")
