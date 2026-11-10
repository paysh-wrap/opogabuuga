"""Step 3b (scope widened by the user): extra well-known ideas OUTSIDE the NOISE/fade family. Same strict test as candidates.py (causal, real costs, fixed parameters
chosen from the literature/structure before looking at results, IS 2021-11..2023-12 pick / HO 2024-01..2026-10 judge).
X1 prior-day high/low sweep-and-reclaim fade   X2 pre-market (04:00-09:29 ET) range sweep-and-reclaim fade   X3 gap-and-go continuation
X4 VWAP trend-day pullback continuation        X5 NR7 (narrow-range day) opening-range breakout           (each on MNQ, MES and MGC where data exist)
usage: S15_RAW=<raw folder> python3 candidates2.py"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import lib
from lib import INST, walk, days, START, END
from candidates import rec, OUT


def sweep_fade(sym, levels, rr=1.5, win_after=20, first=5, last=180, minrisk=0.0004, maxrisk=0.004):
    """levels(i, D) -> (hi, lo) or None. A bar closes beyond a level by >= 1 tick (sweep); if within win_after bars a later bar CLOSES back inside -> fade
    (next open). stop = sweep extreme + 1 tick, target rr x risk. Signals 09:30+first .. 09:30+last. One trade/day, flat 15:55."""
    tk = INST[sym]["tick"]; D, nb = days(sym); out = []
    for i in range(8, len(D)):
        d, a = D[i]
        if d < START or d > END: continue
        L = levels(i, D, d)
        if L is None: continue
        hi, lo = L
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        brk = None
        for k in range(first, last):
            if np.isnan(c[k]): continue
            if brk is None:
                if h[k] >= hi + tk and c[k] >= hi: brk, ext, k0 = 1, h[k], k      # closed beyond: a real break to be tested for failure
                elif l[k] <= lo - tk and c[k] <= lo: brk, ext, k0 = -1, l[k], k
                elif h[k] >= hi + tk and c[k] < hi:                                 # wick sweep and reject within the bar
                    brk, ext, k0 = 1, h[k], k
                    if k + 1 < nb and not np.isnan(o[k + 1]):
                        e = o[k + 1] - tk; sp = abs(ext - e) + tk
                        if minrisk * e <= sp <= maxrisk * e:
                            p, xk, mae, risk = walk(a, -1, k + 1, sp, rr * sp, 386, sym); rec(out, d, k + 1, xk, p, mae, risk, -1)
                        break
                elif l[k] <= lo - tk and c[k] > lo:
                    brk, ext, k0 = -1, l[k], k
                    if k + 1 < nb and not np.isnan(o[k + 1]):
                        e = o[k + 1] + tk; sp = abs(ext - e) + tk
                        if minrisk * e <= sp <= maxrisk * e:
                            p, xk, mae, risk = walk(a, 1, k + 1, sp, rr * sp, 386, sym); rec(out, d, k + 1, xk, p, mae, risk, 1)
                        break
                continue
            ext = max(ext, h[k]) if brk > 0 else min(ext, l[k])
            if k - k0 > win_after: break
            if (brk > 0 and c[k] < hi) or (brk < 0 and c[k] > lo):
                s = -brk
                if np.isnan(o[k + 1]): break
                e = o[k + 1] + s * tk; sp = abs(ext - e) + tk
                if minrisk * e <= sp <= maxrisk * e:
                    p, xk, mae, risk = walk(a, s, k + 1, sp, rr * sp, 386, sym); rec(out, d, k + 1, xk, p, mae, risk, s)
                break
    return pd.DataFrame(out)


def pdh_levels(sym):
    def f(i, D, d):
        p = D[i - 1][1]
        return float(np.nanmax(p["high"])), float(np.nanmin(p["low"]))
    return f


def premkt_levels(sym):
    I = INST[sym]
    df = pd.read_csv(f"{lib.RAW}/{I['csv']}", parse_dates=["timestamp"]).set_index("timestamp")
    df.index = df.index.tz_convert("America/New_York")
    pm = df.between_time("04:00", "09:29")
    g = pm.groupby(pm.index.date).agg(hi=("high", "max"), lo=("low", "min"), n=("high", "size"))
    tab = {str(k): (v.hi, v.lo) for k, v in g.iterrows() if v.n > 200}
    return lambda i, D, d: tab.get(d)


def gap_go(sym, rr=1.5, gmin=0.003, k0=15):
    tk = INST[sym]["tick"]; D, nb = days(sym); out = []
    for i in range(1, len(D)):
        d, a = D[i]
        if d < START or d > END: continue
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        pc = D[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or np.isnan(c[k0 - 1]) or np.isnan(o[k0]): continue
        g = o[0] / pc - 1
        if abs(g) < gmin: continue
        s = 1 if g > 0 else -1
        # continuation confirmed: after 15 min price still beyond the open in the gap direction and the gap has not been filled
        if (c[k0 - 1] - o[0]) * s <= 0: continue
        if (s > 0 and np.nanmin(l[:k0]) <= pc) or (s < 0 and np.nanmax(h[:k0]) >= pc): continue
        e = o[k0] + s * tk
        ext = np.nanmin(l[:k0]) if s > 0 else np.nanmax(h[:k0])
        sp = abs(e - ext) + tk
        if not (0.0004 * e <= sp <= 0.004 * e): continue
        p, xk, mae, risk = walk(a, s, k0, sp, rr * sp, 386, sym); rec(out, d, k0, xk, p, mae, risk, s)
    return pd.DataFrame(out)


def vwap_pull(sym, rr=1.5, stop_pct=0.0015, frac=0.8, win=(90, 300)):
    tk = INST[sym]["tick"]; D, nb = days(sym); out = []
    for i in range(1, len(D)):
        d, a = D[i]
        if d < START or d > END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = D[i - 1][1]["close"][nb - 1]
        if np.isnan(pc): continue
        for k in range(win[0], win[1]):
            if np.isnan(c[k]) or np.isnan(vw[k]) or np.isnan(o[k + 1]): continue
            seg = slice(30, k)   # from 10:00 (bars before k only -> causal)
            up = np.nanmean(c[seg] > vw[seg]); dn = np.nanmean(c[seg] < vw[seg])
            s = 0
            if up >= frac and c[k] > pc and l[k] <= vw[k] and c[k] > vw[k]: s = 1
            elif dn >= frac and c[k] < pc and h[k] >= vw[k] and c[k] < vw[k]: s = -1
            if not s: continue
            e = o[k + 1] + s * tk; sp = stop_pct * e
            p, xk, mae, risk = walk(a, s, k + 1, sp, rr * sp, 386, sym); rec(out, d, k + 1, xk, p, mae, risk, s); break
    return pd.DataFrame(out)


def nr7_orb(sym, rr=2.0, or_min=30):
    tk = INST[sym]["tick"]; D, nb = days(sym); out = []
    rng = [float(np.nanmax(a["high"]) - np.nanmin(a["low"])) for _, a in D]
    for i in range(8, len(D)):
        d, a = D[i]
        if d < START or d > END: continue
        if not rng[i - 1] <= min(rng[i - 7:i]): continue       # yesterday = narrowest of the last 7 days (known before today)
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        if np.isnan(c[:or_min]).any(): continue
        oh, ol = np.nanmax(h[:or_min]), np.nanmin(l[:or_min])
        for k in range(or_min, 300):
            if np.isnan(c[k]) or np.isnan(o[k + 1]): continue
            s = 1 if c[k] > oh else (-1 if c[k] < ol else 0)
            if not s: continue
            e = o[k + 1] + s * tk
            sp = abs(e - (ol if s > 0 else oh)) + tk
            if not (0.0005 * e <= sp <= 0.005 * e): break
            p, xk, mae, risk = walk(a, s, k + 1, sp, rr * sp, 386, sym); rec(out, d, k + 1, xk, p, mae, risk, s); break
    return pd.DataFrame(out)


def build():
    C = []
    for sym in os.environ.get("S15_SYMS", "MNQ,MES,MGC").split(","):
        if not os.path.exists(f"{lib.RAW}/{INST[sym]['csv']}"): continue
        C.append((f"X1 Prior-day high/low sweep-reclaim fade, 1.5R ({sym})", sym, 1.5, sweep_fade(sym, pdh_levels(sym))))
        if sym != "MGC": C.append((f"X2 Pre-market range sweep-reclaim fade, 1.5R ({sym})", sym, 1.5, sweep_fade(sym, premkt_levels(sym), first=3, last=150)))
        C.append((f"X3 Gap-and-go continuation, 1.5R ({sym})", sym, 1.5, gap_go(sym)))
        C.append((f"X4 VWAP trend-day pullback, 1.5R ({sym})", sym, 1.5, vwap_pull(sym)))
        C.append((f"X5 NR7 opening-range breakout, 2R ({sym})", sym, 2.0, nr7_orb(sym)))
    return C


if __name__ == "__main__":
    rows = []
    for name, sym, rr, t in build():
        if len(t) == 0: print("EMPTY", name); continue
        key = name.split()[0] + "_" + sym
        t.to_csv(f"{OUT}/streams/{key}.csv", index=False)
        r = dict(name=name, sym=sym, rr=rr, note="", key=key)
        for e in ("IS", "HO", "ALL"): r[e] = lib.stream_stats(t, e)
        rows.append(r)
        print(f"{name:62s} IS n={r['IS']['n']:4d} win={r['IS']['win']:5.1f} PF={r['IS']['pf']:.2f} ${r['IS']['profit']:8.0f} | HO n={r['HO']['n']:4d} win={r['HO']['win']:5.1f} PF={r['HO']['pf']:.2f} ${r['HO']['profit']:8.0f}", flush=True)
    json.dump(rows, open(f"{OUT}/candidates2_{os.environ.get('S15_TAG','all')}.json", "w"), indent=1, default=float)
