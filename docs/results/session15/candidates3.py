"""Step 3c: the last fixed candidates.  N4/N5 = the unchanged NOISE rules on MES and MGC (same $250 emergency stop, hourly checks);
O3 = classic 5-minute opening-range breakout (Zarattini/Aziz style: trade in the direction of the first 5-minute candle at 09:35, stop = other end of
that candle, no fixed target, flat 15:55; skip if the candle is < 0.04% or > 0.4% of price).  Same strict test as candidates.py."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import lib
from lib import INST, walk, days, START, END
from candidates import rec, OUT


def orb5(sym, k0=5):
    tk = INST[sym]["tick"]; D, nb = days(sym); out = []
    for d, a in D:
        if d < START or d > END: continue
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        if np.isnan(c[:k0]).any() or np.isnan(o[k0]): continue
        s = 1 if c[k0 - 1] > o[0] else (-1 if c[k0 - 1] < o[0] else 0)
        if not s: continue
        e = o[k0] + s * tk
        ext = np.nanmin(l[:k0]) if s > 0 else np.nanmax(h[:k0])
        sp = abs(e - ext) + tk
        if not (0.0004 * e <= sp <= 0.004 * e) or (e - ext) * s <= 0: continue
        p, xk, mae, risk = walk(a, s, k0, sp, None, 386, sym); rec(out, d, k0, xk, p, mae, risk, s)
    return pd.DataFrame(out)


if __name__ == "__main__":
    C = []
    for sym in ("MNQ", "MES", "MGC"):
        if not os.path.exists(f"{lib.RAW}/{INST[sym]['csv']}"): continue
        if sym != "MNQ":
            C.append((f"N{4 if sym == 'MES' else 5} NOISE rules unchanged on {sym} ($250 stop)", sym, None, lib.noise_stream(sym)))
        C.append((f"O3 5-minute opening-range breakout, stop = candle, flat 15:55 ({sym})", sym, None, orb5(sym)))
    rows = []
    for name, sym, rr, t in C:
        if len(t) == 0: print("EMPTY", name); continue
        key = name.split()[0] + "_" + sym
        t.to_csv(f"{OUT}/streams/{key}.csv", index=False)
        r = dict(name=name, sym=sym, rr=rr, note="", key=key)
        for e in ("IS", "HO", "ALL"): r[e] = lib.stream_stats(t, e)
        rows.append(r)
        print(f"{name:62s} IS n={r['IS']['n']:4d} win={r['IS']['win']:5.1f} PF={r['IS']['pf']:.2f} ${r['IS']['profit']:8.0f} | HO n={r['HO']['n']:4d} win={r['HO']['win']:5.1f} PF={r['HO']['pf']:.2f} ${r['HO']['profit']:8.0f}", flush=True)
    json.dump(rows, open(f"{OUT}/candidates3.json", "w"), indent=1, default=float)
