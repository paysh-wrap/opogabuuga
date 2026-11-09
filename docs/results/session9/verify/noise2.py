"""Noise-area MNQ with prop-account protection, chosen a priori (not optimized):
 hard = intrabar catastrophic stop at entry -/+ pct*entry (checked every 1m bar on high/low, stop-first, +1 tick slip)
 daycap = stop trading for the day after realized day P&L <= -daycap $ (per micro)
Same entry/trailing logic as noise.py (30-min checks, band/VWAP trail, flat 16:00, max 3/day)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); from load import load
PV, TICK, FEE, LOOK = 2.0, 0.25, 1.0, 14
df = load("mnq"); rth = df.between_time("09:30", "15:59")
days = []
for d, g in rth.groupby(rth.index.date):
    m = ((g.index.hour - 9) * 60 + g.index.minute - 30).values
    if len(g) < 380 or m[0] != 0: continue
    arr = {}
    for col in ("open", "high", "low", "close"):
        a = np.full(390, np.nan); a[m[m < 390]] = g[col].values[m < 390]; arr[col] = a
    tp = (g.high + g.low + g.close).values / 3; v = g.volume.values
    vw = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1); a = np.full(390, np.nan); a[m[m < 390]] = vw[m < 390]
    arr["vwap"] = a; days.append((d, arr))
moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
checks = set(range(29, 360, 30))
def run(hard=None, daycap=None, maxtr=3):
    out = []
    for i in range(LOOK, len(days)):
        d, a = days[i]; o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - LOOK:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        pos = ntr = 0; dayp = 0.0; entry = hs = r0 = None; pending = 0
        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and pos == 0:  # fill pending entry at this bar's open
                entry = o[k] + pending * TICK; pos = pending; pending = 0
                hs = entry - pos * hard * entry if hard else None
                st = max(ub[k - 1], vw[k - 1]) if pos > 0 else min(lb[k - 1], vw[k - 1]); r0 = max(abs(entry - st), entry * 0.001)
            exitp = None
            if pos and hs is not None and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                exitp = (min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos * TICK   # gap through stop -> open
            elif pos and pending_exit:
                pass
            if exitp is None and pos and k == 389:
                exitp = c[k] - pos * TICK
            if exitp is not None:
                pnl = (exitp - entry) * pos * PV - FEE; dayp += pnl
                out.append((d, pos, pnl, (exitp - entry) * pos / r0)); pos = 0
            if k in checks or k == 389:
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        exitp = (o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK
                        pnl = (exitp - entry) * pos * PV - FEE; dayp += pnl
                        out.append((d, pos, pnl, (exitp - entry) * pos / r0)); pos = 0
                if pos == 0 and k < 389 and ntr < maxtr and not (daycap and dayp <= -daycap):
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side: pending = side; ntr += 1
        # loop end
    return pd.DataFrame(out, columns=["d", "side", "pnl", "r"])
pending_exit = False
def stats(t, label):
    w = t.pnl > 0; eq = t.pnl.cumsum(); dd = (eq - eq.cummax()).min(); daily = t.groupby("d").pnl.sum()
    return (f"{label:30s} n={len(t):4d} win={w.mean():.1%} avg$={t.pnl.mean():6.2f} PF={t.pnl[w].sum()/-t.pnl[~w].sum():.2f} "
            f"DD$={dd:6.0f} worstTrade={t.pnl.min():5.0f} worstDay={daily.min():5.0f}")
if __name__ == "__main__":
    res = {}
    for name, kw in [("paper", {}), ("hard0.3%", {"hard": .003}), ("hard0.5%", {"hard": .005}),
                     ("hard0.3%+daycap300", {"hard": .003, "daycap": 300}), ("hard0.5%+daycap300", {"hard": .005, "daycap": 300})]:
        t = run(**kw); t["dt"] = pd.to_datetime(t.d); res[name] = t
        print(stats(t[t.dt < "2024"], name + " IN"), "|", stats(t[t.dt >= "2024"], "HELD")[31:])
        t.to_csv(f"{HERE}/noise_{name}.csv", index=False)
