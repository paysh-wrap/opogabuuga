"""NOISE generator for the session-20 strategy review (adapted from session19 noise2.gen).
Shipped baseline = preset C ($250 hard stop, lock +100pt -> stop entry+10, hourly checks, max 3/day, roll guard) + dayskip Monday.
Added hooks (all default to baseline behaviour):
  efilt(d,k,side,a,F,sig_k)  entry filter (data up to close of bar k)
  lock_fn(entry, sig_k)      lock trigger distance in points (F2/F3); lock distance stays lock[1]
  ratchet=X                  F4: at +X pt move stop to entry+X/2
  exit_extra=range(...)      F5: additional minutes at which only the trail exit is checked
  trail='both'|'vwap'|'band' F6
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

_mes = {}
def mes_bands(look=14):
    """per date: MES upper/lower band arrays, close, vwap (MES own 14-day sigma, same recipe as MNQ)."""
    if not _mes:
        D, F, moves = data("MES")
        for i in range(look, len(D)):
            d, a = D[i]; pc = D[i - 1][1]["close"][NB - 1]; sig = np.nanmean(moves[i - look:i], axis=0)
            _mes[d] = dict(ub=max(a["open"][0], pc) * (1 + sig), lb=min(a["open"][0], pc) * (1 - sig), c=a["close"], vw=a["vwap"])
    return _mes

def f1_strict(d, k, side, a, f, sk):
    m = mes_bands()[d]
    return m["c"][k] > m["ub"][k] if side > 0 else m["c"][k] < m["lb"][k]
def f1_loose(d, k, side, a, f, sk):
    m = mes_bands()[d]
    return m["c"][k] > m["vw"][k] if side > 0 else m["c"][k] < m["vw"][k]

monday = lambda d, f: f["dow"] == 0

def gen(stop_usd=250.0, look=14, step=60, maxtr=3, first_check=29, lock=(100.0, 10.0), hours=None, efilt=None, dayskip=monday,
        lock_fn=None, ratchet=None, exit_extra=(), trail="both",
        rnd=None, start=None, end=None, sym="MNQ", pv=PV, tick=TICK, fee=FEE, roll=0.015):
    start = start or lib.S0; end = end or lib.J1
    D, F, moves = data(sym); nb = NB
    hard = (stop_usd - fee - 2 * tick * pv) / pv
    rng = np.random.default_rng(rnd) if rnd is not None else None
    ent_checks = set(range(first_check, 360, step)); exit_checks = ent_checks | set(exit_extra); out = []
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
        st = dict(pos=0, entry=0., ek=0, mae=0., hs=0., locked=False, hard=0., trig=0.)
        ntr = pending = 0; psig = 0.
        def close_trade(px, xk):
            nonlocal ntr
            if lock and st["locked"] and xk > st["ek"] and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)): ntr = maxtr
            p = (px - st["entry"]) * st["pos"] * pv - fee
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, mae=st["mae"] + tick * pv, risk=st["hard"] * pv + fee + 2 * tick * pv, side=st["pos"]))
            st["pos"] = 0
        for k in range(nb):
            if c[k] != c[k]: continue
            if pending and st["pos"] == 0:
                en = o[k] + pending * tick
                st.update(entry=en, pos=pending, ek=k, mae=0., locked=False, hard=hard, trig=(lock_fn(en, psig) if lock_fn else (lock[0] if lock else 0.))); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hard
            pos = st["pos"]
            if pos:
                e = st["entry"]
                st["mae"] = max(st["mae"], ((e - l[k]) if pos > 0 else (h[k] - e)) * pv)
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * tick, k)
                if st["pos"] and lock and not st["locked"] and ((pos > 0 and h[k] >= e + st["trig"]) or (pos < 0 and l[k] <= e - st["trig"])):
                    st["locked"] = True; st["hs"] = max(st["hs"], e + lock[1]) if pos > 0 else min(st["hs"], e - lock[1])
                if st["pos"] and ratchet and ((pos > 0 and h[k] >= e + ratchet) or (pos < 0 and l[k] <= e - ratchet)):
                    st["hs"] = max(st["hs"], e + ratchet / 2) if pos > 0 else min(st["hs"], e - ratchet / 2)
            if st["pos"] and k == nb - 1: close_trade(c[k] - st["pos"] * tick, k)
            if k in exit_checks:
                pos = st["pos"]
                if pos:
                    if trail == "both": tr = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    elif trail == "vwap": tr = vw[k]
                    else: tr = ub[k] if pos > 0 else lb[k]
                    if (pos > 0 and c[k] < tr) or (pos < 0 and c[k] > tr):
                        nk = k + 1
                        close_trade((o[nk] if nk < nb and o[nk] == o[nk] else c[k]) - pos * tick, min(nk, nb - 1))
            if k in ent_checks:
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        ok = (hours is None or k in hours)
                        if ok and efilt is not None and not efilt(d, k, side, a, f, sig[k]): ok = False
                        if ok:
                            if rng is not None: side = 1 if rng.random() < 0.5 else -1
                            pending, ntr, psig = side, ntr + 1, sig[k]
    return pd.DataFrame(out)
