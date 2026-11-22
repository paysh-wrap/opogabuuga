"""Shared stream-generator helpers (research only): loads the session-20 NOISE generator on the shared MNQ 1-minute days.pkl and
re-implements the session-19 PM_FADE generator with the exit bar kept (needed for the one-position rule).
Nothing is written to the old result folders."""
import sys, os, types, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
SCR = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/pf150k"
sys.argv = [sys.argv[0], PKL]
S20 = WT + "/docs/results/session20/strategy_review"
sys.path.insert(0, S20)
_src = open(S20 + "/lib.py").read().replace('SP + "/data/days12.pkl"', repr(PKL))
nlib = types.ModuleType("lib"); nlib.__file__ = S20 + "/lib.py"; sys.modules["lib"] = nlib
exec(compile(_src, S20 + "/lib.py", "exec"), nlib.__dict__)
import noise3
import numpy as np, pandas as pd
from lib import PV, TICK, FEE, NB

STOPS = (75, 100, 125, 150, 175, 200, 225, 250, 300)
LOCKS = (80.0, 100.0, 120.0)


def noise_stream(stop, lock=100.0, maxtr=3, mondays=False):
    kw = dict(stop_usd=float(stop), maxtr=maxtr, lock=(float(lock), 10.0))
    if mondays: kw["dayskip"] = None
    return noise3.gen(**kw)


def fade_stream(stop=250.0, band=2.0, first=210, last=358, min_ticks=4, flat_k=385, skip_monday=False):
    """session-19 fade2.gen rules, but (a) generated on EVERY day (NOISE days are filtered per config later), (b) exit bar xk and entry price kept.
    close_k > VWAP + band*sd -> SHORT, < VWAP - band*sd -> LONG; sd = pop std of (close - VWAP) over today's RTH bars <= k; fill next bar open +/- 1 tick;
    target = VWAP at signal; stop = `stop` $ per micro; flat 15:55 (bar 385); one try per day (TARGET_TOO_CLOSE ends the day)."""
    D, F, moves = noise3.data(); out = []
    hard = (stop - FEE - 2 * TICK * PV) / PV
    for i in range(14, len(D)):
        d, a = D[i]
        if d not in F: continue
        if skip_monday and F[d]["dow"] == 0: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        dev = np.nan_to_num(c - vw); n = np.cumsum(~np.isnan(c - vw)); s1 = np.cumsum(dev); s2 = np.cumsum(dev * dev)
        for k in range(first, last + 1):
            if np.isnan(c[k]) or np.isnan(vw[k]) or n[k] < 5: continue
            m = s1[k] / n[k]; sd = np.sqrt(max(s2[k] / n[k] - m * m, 0))
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + band * sd else (1 if c[k] < vw[k] - band * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK; tgt = vw[k]
            if (tgt - e) * s < min_ticks * TICK: break
            stp = e - s * hard; px = None; mae = 0.; xk = flat_k
            for j in range(k + 1, flat_k + 1):
                mae = max(mae, s * (e - (l[j] if s > 0 else h[j])))
                if (s > 0 and l[j] <= stp) or (s < 0 and h[j] >= stp): px = (min(stp, o[j]) if s > 0 else max(stp, o[j])) - s * TICK; xk = j; break
                if (s > 0 and h[j] >= tgt) or (s < 0 and l[j] <= tgt): px = tgt; xk = j; break
                if j == flat_k: px = c[j] - s * TICK; xk = j
            out.append(dict(d=d, sk=k, ek=k + 1, xk=xk, pnl=(px - e) * s * PV - FEE, mae=mae * PV + FEE, risk=hard * PV + FEE + 2 * TICK * PV, side=s, entry=float(e)))
            break
    return pd.DataFrame(out)
