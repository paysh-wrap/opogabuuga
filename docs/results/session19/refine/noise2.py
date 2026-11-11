"""NOISE generator = session-17 nz.gen (preset C: $250 stop + lock 100->+10, hourly checks, max 3/day, roll guard) + hook efilt(d,k,side,a,F) for entry refinements.
efilt sees only data up to the check bar k (close of bar k), so no lookahead.  Costs: $1 RT + 1 tick on every entry/exit/stop fill, 1 micro."""
import numpy as np, pandas as pd
import lib
from lib import PV, TICK, FEE, NB

_cache = {}
def data(sym="MNQ"):
    if sym not in _cache:
        D = lib.build_days(sym); F = lib.day_feats(D)
        moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in D])
        _cache[sym] = (D, F, moves)
    return _cache[sym]

def gen(stop_usd=250.0, look=14, step=60, maxtr=3, first_check=29, lock=(100.0, 10.0), hours=None, efilt=None, dayskip=None, extra_checks=(),
        rnd=None, start=lib.S0, end=lib.J1, sym="MNQ", pv=PV, tick=TICK, fee=FEE, roll=0.015):
    D, F, moves = data(sym); nb = NB
    hard = (stop_usd - fee - 2 * tick * pv) / pv
    rng = np.random.default_rng(rnd) if rnd is not None else None
    checks = set(range(first_check, 360, step)) | set(extra_checks); out = []
    for i in range(look, len(D)):
        d, a = D[i]
        if d < start or d > end or d not in F: continue
        f = F[d]
        if dayskip is not None and dayskip(d, f): continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = D[i - 1][1]["close"][nb - 1]
        if pc != pc or abs(o[0] / pc - 1) > roll: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=0., ek=0, mae=0., hs=0., locked=False, hard=0.)
        ntr = pending = 0
        def close_trade(px, xk, stopout=False):
            nonlocal ntr
            if lock and st["locked"] and xk > st["ek"] and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)): ntr = maxtr
            p = (px - st["entry"]) * st["pos"] * pv - fee
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, mae=st["mae"] + tick * pv, risk=st["hard"] * pv + fee + 2 * tick * pv, side=st["pos"]))
            st["pos"] = 0
        for k in range(nb):
            if c[k] != c[k]: continue
            if pending and st["pos"] == 0:
                st.update(entry=o[k] + pending * tick, pos=pending, ek=k, mae=0., locked=False, hard=hard); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hard
            pos = st["pos"]
            if pos:
                e = st["entry"]
                st["mae"] = max(st["mae"], ((e - l[k]) if pos > 0 else (h[k] - e)) * pv)
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * tick, k, True)
                if st["pos"] and lock and not st["locked"] and ((pos > 0 and h[k] >= e + lock[0]) or (pos < 0 and l[k] <= e - lock[0])):
                    st["locked"] = True; st["hs"] = max(st["hs"], e + lock[1]) if pos > 0 else min(st["hs"], e - lock[1])
            if st["pos"] and k == nb - 1: close_trade(c[k] - st["pos"] * tick, k)
            if k in checks:
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < nb and o[nk] == o[nk] else c[k]) - pos * tick, min(nk, nb - 1))
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        ok = (hours is None or k in hours)
                        if ok and efilt is not None and not efilt(d, k, side, a, f, sig[k]): ok = False
                        if ok:
                            if rng is not None: side = 1 if rng.random() < 0.5 else -1
                            pending, ntr = side, ntr + 1
    return pd.DataFrame(out)
