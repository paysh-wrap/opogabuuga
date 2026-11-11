"""(lib copied from smc.py) Session 18 S.M.C study (MNQ, 1 micro, flat daily). Self-contained, no app imports; reuses the session-17 cached MNQ.v.0 1m csv
and the session-17 Lucid Pro 25K eval simulator (noise_sharpen/sim.py). Closed bars only; entries at the next 1m open after a signal bar closes.
Costs: $1 fee RT + 1 tick slippage on every fill (entry, stop, target, exit), stop-first inside a bar, gaps fill at the open."""
import sys, json, random, os
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session17/noise_sharpen")
import sim as S
SP = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/"
MKT = os.environ.get("MKT", "MNQ")
OUT = "/home/user/opogabuuga/docs/results/session18/rsi_dmi/out"
START, SPLIT, END = "2025-11-06", "2026-06-30", "2026-11-06"   # last ~12 months: pick 8 mo, judge 4 mo
S.RANGES = dict(IS=(START, SPLIT), HO=("2026-07-01", END))
if MKT == "MNQ":
    PV, TICK, FEE, MAXPT, MINPT, SESS_LO = 2.0, 0.25, 1.0, 124.0, 4.0, 570
    df = pd.read_csv(SP + "mnq_2019_2026.csv", parse_dates=["timestamp"]); df = df[df.timestamp >= "2025-09-01"].set_index("timestamp")
else:   # MGC: 1 micro gold, tick 0.10 = $1.00 (10 oz), fee 1.60 RT (plan yaml), $250 cap = 25 pt, min stop 16 ticks; session 03:00-16:00 ET
    PV, TICK, FEE, MAXPT, MINPT, SESS_LO = 10.0, 0.10, 1.60, 25.0, 1.6, 180
    df = pd.concat([pd.read_csv(SP + f"split_raw/MGC_{y}.csv", usecols=["ts_event", "open", "high", "low", "close"]) for y in (2025, 2026)])
    df["timestamp"] = pd.to_datetime(df.ts_event, utc=True); df = df[df.timestamp >= "2025-09-01"].drop(columns="ts_event").set_index("timestamp").sort_index()
df.index = df.index.tz_convert("America/New_York").tz_localize(None)
O, H, L, C = (df[c].values.astype(float) for c in ("open", "high", "low", "close"))
TS = df.index.values
MOD = (df.index.hour * 60 + df.index.minute).values
DATE = df.index.strftime("%Y-%m-%d").values
N = len(df)
rth_end = np.full(N, -1)
isrth = (MOD >= SESS_LO) & (MOD < 960)
last = {}
for i in np.nonzero(isrth)[0]: last[DATE[i]] = i
rth_end = np.array([last.get(d, -1) for d in DATE])
print("bars", N, flush=True)


def bars(tf):
    if tf == 1:
        b = df.copy()
    else:
        b = df.resample(f"{tf}min", label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last")).dropna()
    # first 1m index at or after bar close time
    close_t = (b.index + pd.Timedelta(minutes=tf)).values
    b["nxt"] = np.searchsorted(TS, close_t)
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
    """sigs: list of (i0, side, stop_dist, R or None, exit_i, limit) chronological. one position at a time."""
    out = []; busy = -1; rr = random.Random(rnd) if rnd is not None else None
    for i0, side, dist, R, exit_i, limit in sigs:
        if i0 <= busy: continue
        if rr is not None: side = rr.choice((1, -1))
        ref = limit if limit is not None else O[i0]
        stop = ref - side * dist; tgt = ref + side * R * dist if R else None
        t = run_trade(i0, side, stop, tgt, exit_i, limit)
        if t: out.append(t); busy = t["xi"]
    return pd.DataFrame(out, columns=["d", "ei", "xi", "side", "pnl", "mae", "risk"])


def stats(t, era):
    x = t[(t.d <= SPLIT)] if era == "IS" else t[t.d > SPLIT]
    if len(x) == 0: return dict(n=0)
    p = x.pnl.values; eq = np.cumsum(p); dd = float(np.max(np.maximum.accumulate(np.r_[0, eq])[1:] - eq)) if len(p) else 0
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    r = dict(n=len(p), win=round(100 * (p > 0).mean(), 1), pf=round(gp / gl, 2) if gl else 99, avg=round(p.mean(), 2), net=round(p.sum()), dd=round(dd))
    if era == "HO":
        e = S.eval_roll(x, "HO"); bt = S.eval_boot(x, "HO", n_paths=400)
        r.update(passp=round(e["pass_"], 1), bust=round(e["bust"], 1), med=e["med"], bpass=round(bt["pass_"], 1), bbust=round(bt["bust"], 1))
    return r


def randbench(sigs, era="HO", seeds=30):
    v = [stats(collect(sigs, rnd=s), era) for s in range(seeds)]
    return dict(avg=round(np.mean([a["avg"] for a in v]), 2), pf=round(np.mean([a["pf"] for a in v]), 2), win=round(np.mean([a["win"] for a in v]), 1),
                passp=round(np.mean([a["passp"] for a in v]), 1), bust=round(np.mean([a["bust"] for a in v]), 1))


