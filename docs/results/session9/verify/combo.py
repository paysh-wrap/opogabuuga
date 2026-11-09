"""MNQ + MES noise-area in ONE account: max 1 open position (non-negotiable #7), MNQ has priority when flat.
Same rules as tools/noise_area.py (hourly checks, 1% emergency stop, flat 16:00, max 3 entries/day TOTAL)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/tools")
import noise_area as NA, sim25k as SM
S = "/tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad"
SPEC = {"MNQ": (2.0, 0.25, 1.0), "MES": (5.0, 0.25, 1.0)}   # point value, tick, fee RT
def prep(sym):
    days = NA.load_days(f"{S}/data/{sym.lower()}_1m.csv")
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    idx = {d: i for i, (d, _) in enumerate(days)}
    return days, moves, idx
def bands(days, moves, i, look=14):
    d, a = days[i]; pc = days[i - 1][1]["close"][389]
    if i < look or np.isnan(pc) or abs(a["open"][0] / pc - 1) > 0.015: return None
    sig = np.nanmean(moves[i - look:i], axis=0)
    return max(a["open"][0], pc) * (1 + sig), min(a["open"][0], pc) * (1 - sig)
def run(syms, step=60, hard=0.01, maxtr=3):
    P = {s: prep(s) for s in syms}; checks = set(range(29, 360, step)); out = []
    common = sorted(set.intersection(*[set(P[s][2]) for s in syms]))
    for d in common:
        B = {}
        for s in syms:
            days, moves, idx = P[s]; b = bands(days, moves, idx[d])
            if b: B[s] = (days[idx[d]][1], b)
        if not B: continue
        pos = ntr = 0; sym = None; pending = None; entry = hs = None
        def close(px):
            nonlocal pos
            pv, tick, fee = SPEC[sym]; out.append((d, sym, pos, (px - entry) * pos * pv - fee)); pos = 0
        for k in range(390):
            if pending and pos == 0:
                sym, side = pending; a = B[sym][0]; pending = None
                if np.isnan(a["open"][k]): continue
                entry = a["open"][k] + side * SPEC[sym][1]; pos = side; hs = entry - pos * hard * entry
            if pos:
                a = B[sym][0]; tick = SPEC[sym][1]
                if not np.isnan(a["close"][k]):
                    if (pos > 0 and a["low"][k] <= hs) or (pos < 0 and a["high"][k] >= hs):
                        close((min(hs, a["open"][k]) if pos > 0 else max(hs, a["open"][k])) - pos * tick)
                    elif k == 389: close(a["close"][k] - pos * tick)
            if k in checks:
                if pos:
                    a, (ub, lb) = B[sym]; c = a["close"][k]; vw = a["vwap"][k]
                    trail = max(ub[k], vw) if pos > 0 else min(lb[k], vw)
                    if (pos > 0 and c < trail) or (pos < 0 and c > trail):
                        nk = k + 1; px = a["open"][nk] if nk < 390 and not np.isnan(a["open"][nk]) else c
                        close(px - pos * SPEC[sym][1])
                if pos == 0 and ntr < maxtr:
                    for s in syms:                      # priority order
                        if s not in B: continue
                        a, (ub, lb) = B[s]; c = a["close"][k]
                        if np.isnan(c): continue
                        side = 1 if c > ub[k] else (-1 if c < lb[k] else 0)
                        if side: pending = (s, side); ntr += 1; break
    return pd.DataFrame(out, columns=["d", "sym", "side", "pnl"])
if __name__ == "__main__":
    for syms in (["MNQ"], ["MES"], ["MNQ", "MES"]):
        t = run(syms); name = "+".join(syms); p = f"{S}/verify/combo_{name}.csv"; t.to_csv(p, index=False)
        dt = pd.to_datetime(t.d); h = t[dt >= "2024"]; i = t[dt < "2024"]; nd = len(pd.bdate_range("2024-01-01", "2026-11-06"))
        f = lambda g: f"n={len(g)} win={(g.pnl>0).mean():.1%} $/tr={g.pnl.mean():.2f} PF={g.pnl[g.pnl>0].sum()/-g.pnl[g.pnl<=0].sum():.2f} tot=${g.pnl.sum():.0f}"
        r = SM.run("Pro", p, dll_funded=600); n = len(r)
        full = [x for x in r if x[0] == "pass" and not x[4]]
        ev = np.mean([x[2] for x in full]) if full else 0
        print(f"{name:8s} IN {f(i)}\n{'':8s} HELD {f(h)} | {5*len(h)/nd:.1f} trades/week | Pro25K pass "
              f"{sum(x[0]=='pass' for x in r)/n:.0%} bust {sum(x[0]=='bust' for x in r)/n:.0%} value/eval ≈ ${ev*sum(x[0]=='pass' for x in r)/n:.0f}", flush=True)
