"""Session 17 NOISE sharpening study - generalised copy of docs/results/session15/lib.noise_stream (same bar loop, same costs) with switches.
Default options (lock=(100,10)) == session-15 N1 stream (checked by baseline_check.py).
Switches:  hours = set of check bar-indexes allowed for ENTRIES (29=10:00 .. 329=15:00; exits always on every check)
           norev = None | 'stop' (no entry on the check bar where an emergency/locked stop was hit) | 'any' (also no flip on a trail exit)
           min_sig = minimum daily sigma (fraction of price) for any entry (band width filter), minw_pts = minimum band width in points
           vwapf = None | 'side' (long only close>VWAP, short only close<VWAP) | 'slope' (side AND VWAP rising/falling over last 60 min)
           rnd = seed -> entry direction random (+-1) whenever the normal 'close outside the band' signal fires (same exits/costs)"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session15")
import lib
from lib import INST, days, START, END, SPLIT


def gen(sym="MNQ", stop_usd=250.0, look=14, step=60, maxtr=3, first_check=29, lock=(100, 10), hours=None, norev=None,
        min_sig=None, minw_pts=None, vwapf=None, rnd=None, fixed_sigs=None):
    I = INST[sym]; PV, TICK, FEE = I["pv"], I["tick"], I["fee"]
    Dd, nb = days(sym)
    hard = (stop_usd - FEE - 2 * TICK * PV) / PV
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in Dd])
    checks = set(range(first_check, 360, step)); out = []
    rng = np.random.default_rng(rnd) if rnd is not None else None
    for i in range(look, len(Dd)):
        d, a = Dd[i]
        if d < START or d > END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = Dd[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=0.0, ek=0, mae=0.0, got=0.0, rem=1.0, moved=False, hs=0.0, locked=False, so=-1, sk=0, w=0.0, sg=0.0)
        ntr = pending = 0
        def close_trade(px, xk, stopout=False):
            nonlocal ntr
            if st["locked"] and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)) and xk > st["ek"]: ntr = maxtr
            p = st["got"] + st["rem"] * (px - st["entry"]) * st["pos"] * PV - FEE
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, mae=st["mae"] + TICK * PV, risk=hard * PV + FEE + 2 * TICK * PV, side=st["pos"],
                            sk=st["sk"], width=st["w"], sigk=st["sg"]))
            st["pos"] = 0
            if stopout: st["so"] = xk
        for k in range(nb):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                st.update(entry=o[k] + pending * TICK, pos=pending, ek=k, mae=0.0, got=0.0, rem=1.0, moved=False, locked=False, sk=k - 1); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hard
            pos = st["pos"]
            if pos:
                e = st["entry"]
                st["mae"] = max(st["mae"], ((e - l[k]) if pos > 0 else (h[k] - e)) * PV)
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * TICK, k, stopout=True)
                if st["pos"] and lock and not st["locked"] and ((pos > 0 and h[k] >= e + lock[0]) or (pos < 0 and l[k] <= e - lock[0])):
                    st["locked"] = True; st["hs"] = max(st["hs"], e + lock[1]) if pos > 0 else min(st["hs"], e - lock[1])
            if st["pos"] and k == nb - 1: close_trade(c[k] - st["pos"] * TICK, k)
            if k in checks:
                pos = st["pos"]; trail_exit = False
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1; trail_exit = True
                        close_trade((o[nk] if nk < nb and not np.isnan(o[nk]) else c[k]) - pos * TICK, min(nk, nb - 1))
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        wk = float(ub[k] - lb[k]); sgk = float(sig[k]); ok = (hours is None or k in hours)
                        if min_sig is not None and sgk < min_sig: ok = False
                        if minw_pts is not None and wk < minw_pts: ok = False
                        if ok and norev and st["so"] == k: ok = False
                        if ok and norev == "any" and trail_exit: ok = False
                        if ok and vwapf:
                            if side * (c[k] - vw[k]) <= 0: ok = False
                            elif vwapf == "slope" and k >= 60 and side * (vw[k] - vw[k - 60]) <= 0: ok = False
                        if ok:
                            if rng is not None: side = 1 if rng.random() < 0.5 else -1
                            pending, ntr = side, ntr + 1; st["w"], st["sg"] = wk, sgk
    return pd.DataFrame(out)


def stats(t, era):
    if era == "IS": t = t[t.d <= SPLIT]
    elif era == "HO": t = t[t.d > SPLIT]
    elif era == "L12": t = t[t.d >= "2025-11-01"]
    if not len(t): return dict(n=0, win=float("nan"), pf=float("nan"), net=0.0, dd=0.0, avg=0.0)
    w = t.pnl > 0; gl = -t.pnl[~w].sum()
    cum = np.concatenate([[0], t.pnl.cumsum().values])
    return dict(n=int(len(t)), win=float(100 * w.mean()), pf=float(t.pnl[w].sum() / gl) if gl > 0 else float("inf"), net=float(t.pnl.sum()),
                dd=float(np.max(np.maximum.accumulate(cum) - cum)), avg=float(t.pnl.mean()))
