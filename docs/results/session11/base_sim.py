"""base_sim.py - rebuilt (the session-10 agent scratchpad copy is gone) from docs/results/session10/five_year/eval25k_total_risk.py:
prep / calendar / first_hit / trade_stop_exit are copied UNCHANGED. Only the CSV path and OUT differ (CSV = merged MNQ.v.0 1-minute bars)."""
import sys
import numpy as np, pandas as pd
sys.path[:0] = ["/home/user/opogabuuga/docs/results/tools"]
import noise_area as NA
CSV = "/home/user/opogabuuga/backend/app/backtest/data/raw/mnq_5y.csv"
OUT = "/home/user/opogabuuga/docs/results/session11/out"
START, END = "2021-11-01", "2026-10-30"
PV, TICK, FEE, TV, SLIP = 2.0, 0.25, 1.0, 0.5, 1
MARGIN, MIN_PCT = 40.0, 0.002
CHECKS = list(range(29, 360, 60))
def per_contract(ticks): return ticks * TV + FEE + SLIP * TV
class Day: pass
def prep():
    days = NA.load_days(CSV)
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    out = {}
    for i, (d, a) in enumerate(days):
        if d < START or d > END: continue
        D = Day(); D.o, D.h, D.l, D.c, D.vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        D.noise_ok = False; D.side = {}; D.trail = {}
        o, c, vw = D.o, D.c, D.vw
        if i >= 14:
            pc = days[i - 1][1]["close"][389]
            if not (np.isnan(pc) or abs(o[0] / pc - 1) > 0.015):
                sig = np.nanmean(moves[i - 14:i], axis=0)
                ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
                D.noise_ok = True
                for k in CHECKS:
                    if np.isnan(c[k]): continue
                    D.side[k] = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    D.trail[k] = (c[k] < max(ub[k], vw[k]), c[k] > min(lb[k], vw[k]))   # long exit, short exit
        D.nv = None
        # fade signal (stop independent)
        D.fade = None
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK
            if (vw[k] - e) * s < 4 * TICK: break
            D.fade = (k, s, e, vw[k]); break
        out[d] = D
    return out

def first_hit(arr_cond):
    if arr_cond.size == 0: return None
    j = int(arr_cond.argmax()); return j if arr_cond[j] else None

def trade_stop_exit(D, s, entry, ek, stop):
    """first 1-min bar >= ek whose range touches the stop -> (pnl_per_micro, bar) else None"""
    seg = (D.l[ek:390] <= stop) if s > 0 else (D.h[ek:390] >= stop)
    j = first_hit(seg)
    if j is None: return None
    j += ek
    px = (min(stop, D.o[j]) if s > 0 else max(stop, D.o[j])) - s * TICK
    return (px - entry) * s * PV - FEE, j

def calendar(DAYS):
    from datetime import date, timedelta
    names, objs, x = [], [], date.fromisoformat(START)
    while x <= date.fromisoformat(END):
        if x.weekday() < 5: names.append(x.isoformat()); objs.append(DAYS.get(x.isoformat()))
        x += timedelta(days=1)
    return names, objs

