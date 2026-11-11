"""PM_FADE (D58): afternoon VWAP-band fade on days NOISE has not traded.  Same rules as engine/pm_fade.py + stops_250.py; variants add refinements.
close_k > VWAP + band*sd -> SHORT, < VWAP - band*sd -> LONG; sd = pop std of (close - VWAP) over today's RTH bars <= k; fill next bar open +/- 1 tick;
target = VWAP at signal; stop = $250 (124 pt); flat 15:55; one try per day (TARGET_TOO_CLOSE ends the day).  Costs $1 RT + 1 tick on entry and on stop/flat exits."""
import numpy as np, pandas as pd
import lib, noise2
from lib import PV, TICK, FEE, NB

def gen(noise_days, band=2.0, stop_usd=250.0, first=210, last=358, min_ticks=4, efilt=None, rnd=None, flat_k=385, start=lib.S0, end=lib.J1, only_days=None):
    D, F, moves = noise2.data(); out = []; rng = np.random.default_rng(rnd) if rnd is not None else None
    hard = (stop_usd - FEE - 2 * TICK * PV) / PV
    for i in range(14, len(D)):
        d, a = D[i]
        if d < start or d > end or d in noise_days or d not in F: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        dev = np.nan_to_num(c - vw); n = np.cumsum(~np.isnan(c - vw)); s1 = np.cumsum(dev); s2 = np.cumsum(dev * dev)
        for k in range(first, last + 1):
            if np.isnan(c[k]) or np.isnan(vw[k]) or n[k] < 5: continue
            m = s1[k] / n[k]; sd = np.sqrt(max(s2[k] / n[k] - m * m, 0))
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + band * sd else (1 if c[k] < vw[k] - band * sd else 0)
            if not s: continue
            if efilt is not None and not efilt(d, k, s, a, F[d], sd): continue
            if rng is not None: s = 1 if rng.random() < .5 else -1
            e = o[k + 1] + s * TICK; tgt = vw[k]
            if rng is not None: tgt = e + s * abs(vw[k] - c[k])
            if (tgt - e) * s < min_ticks * TICK: break                      # TARGET_TOO_CLOSE ends the day
            stop = e - s * hard; px = None; mae = 0.
            for j in range(k + 1, flat_k + 1):
                mae = max(mae, s * (e - (l[j] if s > 0 else h[j])))
                if (s > 0 and l[j] <= stop) or (s < 0 and h[j] >= stop): px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK; break
                if (s > 0 and h[j] >= tgt) or (s < 0 and l[j] <= tgt): px = tgt; break
                if j == flat_k: px = c[j] - s * TICK
            out.append(dict(d=d, ek=k + 1, pnl=(px - e) * s * PV - FEE, mae=mae * PV + FEE, side=s)); break
    return pd.DataFrame(out)
