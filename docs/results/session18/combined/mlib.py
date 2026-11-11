"""Session 18 'combined' study - market loader + 1-micro trade simulator (copied from session18/rsi_dmi/lib.py, which itself is smc.py's loader).
MKT=MNQ|MGC selects the market.  Closed bars only; entries at the next 1m open after a signal bar closes (or a limit fill).
Costs: fee RT (MNQ $1.00, MGC $1.60 plan yaml) + 1 tick slippage on every fill, stop-first inside a bar, gaps fill at the open.
Only change vs rsi_dmi/lib.py: UTCM (UTC minute of each 1m bar) so two markets can share one timeline; no eval-sim import."""
import os
import numpy as np, pandas as pd, random
SP = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/"
MKT = os.environ.get("MKT", "MNQ")
HERE = "/home/user/opogabuuga/docs/results/session18/combined"
OUT = HERE + "/out"
START, SPLIT, END = "2025-11-06", "2026-06-30", "2026-11-05"   # last 12 months: pick on 2025-11-06..2026-06-30 (~8 mo), judge on 2026-07-01..2026-11-05 (~4 mo)
if MKT == "MNQ":
    PV, TICK, FEE, MAXPT, MINPT, SESS_LO = 2.0, 0.25, 1.0, 124.0, 4.0, 570
    df = pd.read_csv(SP + "mnq_2019_2026.csv", parse_dates=["timestamp"]); df = df[df.timestamp >= "2025-09-01"].set_index("timestamp")
else:   # MGC: 1 micro gold, tick 0.10 = $1.00 (10 oz => $10/pt), fee 1.60 RT (plan yaml), $250 cap = 25 pt, min stop 16 ticks = 1.6 pt, session 03:00-16:00 ET
    PV, TICK, FEE, MAXPT, MINPT, SESS_LO = 10.0, 0.10, 1.60, 25.0, 1.6, 180
    df = pd.concat([pd.read_csv(SP + f"split_raw/MGC_{y}.csv", usecols=["ts_event", "open", "high", "low", "close"]) for y in (2025, 2026)])
    df["timestamp"] = pd.to_datetime(df.ts_event, utc=True); df = df[df.timestamp >= "2025-09-01"].drop(columns="ts_event").set_index("timestamp").sort_index()
if df.index.tz is None: df.index = df.index.tz_localize("UTC")
UTCM = ((df.index - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(minutes=1)).values.astype("int64")
df.index = df.index.tz_convert("America/New_York").tz_localize(None)
O, H, L, C = (df[c].values.astype(float) for c in ("open", "high", "low", "close"))
TS = df.index.values
MOD = (df.index.hour * 60 + df.index.minute).values
DATE = df.index.strftime("%Y-%m-%d").values
N = len(df)
isrth = (MOD >= SESS_LO) & (MOD < 960)
last = {}
for i in np.nonzero(isrth)[0]: last[DATE[i]] = i
rth_end = np.array([last.get(d, -1) for d in DATE])


def bars(tf):
    if tf == 1:
        b = df.copy()
    else:
        b = df.resample(f"{tf}min", label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last")).dropna()
    close_t = (b.index + pd.Timedelta(minutes=tf)).values
    b["nxt"] = np.searchsorted(TS, close_t)          # first 1m index at or after bar close time
    b["mod_close"] = ((b.index.hour * 60 + b.index.minute) + tf).values
    return b


def supertrend(b, n=10, m=3.0):
    h, l, c = b.high.values, b.low.values, b.close.values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = np.empty_like(tr); atr[0] = tr[0]; a = 1.0 / n
    for i in range(1, len(tr)): atr[i] = atr[i - 1] + a * (tr[i] - atr[i - 1])
    hl2 = (h + l) / 2; ub = hl2 + m * atr; lb = hl2 - m * atr
    fu = ub.copy(); fl = lb.copy(); d = np.ones(len(c), int); line = np.empty_like(c)
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if d[i - 1] == 1: d[i] = -1 if c[i] < fl[i] else 1
        else: d[i] = 1 if c[i] > fu[i] else -1
        line[i] = fl[i] if d[i] == 1 else fu[i]
    line[0] = fl[0]
    return d, line, atr


def run_trade(i0, side, stop, tgt=None, exit_i=None, limit=None):
    """i0 = 1m index of entry (market at open, or limit fill bar). returns dict or None"""
    ie = rth_end[i0]
    if ie < 0 or i0 > ie: return None
    if exit_i is not None: ie2 = min(ie, exit_i - 1)
    else: ie2 = ie
    ent = (limit if limit is not None else O[i0]) + side * TICK
    rng = slice(i0, ie2 + 1)
    lo, hi, op = L[rng], H[rng], O[rng]
    if side == 1: sh = np.nonzero(lo <= stop)[0]; th = np.nonzero(hi >= tgt)[0] if tgt is not None else np.array([], int)
    else: sh = np.nonzero(hi >= stop)[0]; th = np.nonzero(lo <= tgt)[0] if tgt is not None else np.array([], int)
    if limit is not None: th = th[th > 0]
    k_s = sh[0] if len(sh) else 10**9; k_t = th[0] if len(th) else 10**9
    if k_s <= k_t and k_s < 10**9:
        k = k_s; px = (min(stop, op[k]) if side == 1 else max(stop, op[k])) if k > 0 or limit is None else stop
    elif k_t < 10**9:
        k = k_t; px = tgt
    else:
        k = ie2 - i0
        if exit_i is not None and exit_i <= ie: px = O[exit_i]
        else: px = C[ie]
    px -= side * TICK
    seg = slice(i0, i0 + k + 1)
    mae = (ent - L[seg].min()) * PV if side == 1 else (H[seg].max() - ent) * PV
    pnl = side * (px - ent) * PV - FEE
    return dict(d=DATE[i0], ei=i0, xi=i0 + k, side=side, pnl=pnl, mae=max(mae, 0.0) + FEE, risk=abs(ent - stop) * PV)


def collect(sigs, rnd=None):
    """(rsi_dmi/lib.py) sigs: list of (i0, side, stop_dist, R or None, exit_i, limit) chronological. one position at a time."""
    out = []; busy = -1; rr = random.Random(rnd) if rnd is not None else None
    for i0, side, dist, R, exit_i, limit in sigs:
        if i0 <= busy: continue
        if rr is not None: side = rr.choice((1, -1))
        ref = limit if limit is not None else O[i0]
        stop = ref - side * dist; tgt = ref + side * R * dist if R else None
        t = run_trade(i0, side, stop, tgt, exit_i, limit)
        if t: out.append(t); busy = t["xi"]
    return pd.DataFrame(out, columns=["d", "ei", "xi", "side", "pnl", "mae", "risk"])
