"""Session 18 S.M.C study (MNQ, 1 micro, flat daily). Self-contained, no app imports; reuses the session-17 cached MNQ.v.0 1m csv
and the session-17 Lucid Pro 25K eval simulator (noise_sharpen/sim.py). Closed bars only; entries at the next 1m open after a signal bar closes.
Costs: $1 fee RT + 1 tick slippage on every fill (entry, stop, target, exit), stop-first inside a bar, gaps fill at the open."""
import sys, json, random
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session17/noise_sharpen")
import sim as S
CSV = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/mnq_2019_2026.csv"
OUT = "/home/user/opogabuuga/docs/results/session18/smc/out"
PV, TICK, FEE, MAXPT, MINPT = 2.0, 0.25, 1.0, 124.0, 4.0
SPLIT = "2023-12-31"

df = pd.read_csv(CSV, parse_dates=["timestamp"]).set_index("timestamp")
df.index = df.index.tz_convert("America/New_York").tz_localize(None)
df = df[df.index >= "2019-05-01"]
O, H, L, C = (df[c].values.astype(float) for c in ("open", "high", "low", "close"))
TS = df.index.values
MOD = (df.index.hour * 60 + df.index.minute).values
DATE = df.index.strftime("%Y-%m-%d").values
N = len(df)
# last RTH bar (15:59) index of each bar's date
rth_end = np.full(N, -1)
isrth = (MOD >= 570) & (MOD < 960)
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


ENTRY_LO, ENTRY_HI = 575, 930   # signal bar close 09:35..15:30
BARS = {tf: bars(tf) for tf in (1, 5, 15)}
ST = {}
for tf, b in BARS.items():
    d, line, atr = supertrend(b); ST[tf] = (d, line, atr); print("ST", tf, flush=True)


# ---------------- (A) SuperTrend alone ----------------
def sigs_A(tf, exitm):
    b = BARS[tf]; d, line, _ = ST[tf]; nxt = b.nxt.values; mc = b.mod_close.values
    flips = np.nonzero(d[1:] != d[:-1])[0] + 1
    out = []
    for j, f in enumerate(flips):
        if not (ENTRY_LO <= mc[f] <= ENTRY_HI): continue
        i0 = nxt[f]
        if i0 >= N or DATE[i0] != b.index[f].strftime("%Y-%m-%d"): continue
        side = int(d[f]); dist = abs(O[i0] - line[f])
        if exitm == "flip":
            ex = nxt[flips[j + 1]] if j + 1 < len(flips) else None
            out.append((i0, side, MAXPT, None, ex, None))
        else:
            if dist < MINPT or dist > MAXPT: continue
            out.append((i0, side, dist, exitm, None, None))
    return out


# ---------------- (B) sweep + FVG ----------------
def sigs_B(tf, R, stf=None, extra=None, W=6):
    b = BARS[tf]; h, l, c = b.high.values, b.low.values, b.close.values; nxt = b.nxt.values; mc = b.mod_close.values
    bd = b.index.strftime("%Y-%m-%d").values; bmod = mc - tf
    std = None
    if stf is not None:  # ST direction of the last CLOSED stf bar at each tf bar close
        sb = BARS[stf]; sd = ST[stf][0]; sclose = (sb.index + pd.Timedelta(minutes=stf)).values
        bclose = (b.index + pd.Timedelta(minutes=tf)).values
        k = np.searchsorted(sclose, bclose, side="right") - 1; std = np.where(k >= 0, sd[np.maximum(k, 0)], 0)
    ema = None
    if extra == "ema200":
        ema = pd.Series(c).ewm(span=200, adjust=False).mean().values
    if extra == "rsi":
        dl = np.diff(c, prepend=c[0]); up = pd.Series(np.maximum(dl, 0)).ewm(alpha=1 / 14, adjust=False).mean(); dn = pd.Series(np.maximum(-dl, 0)).ewm(alpha=1 / 14, adjust=False).mean()
        rsi = (100 - 100 / (1 + up / dn.replace(0, 1e-9))).values
    # daily levels: prior RTH high/low, overnight (18:00 prev .. 09:29) high/low
    rthm = (bmod >= 570) & (bmod < 960)
    daily = pd.DataFrame(dict(d=bd[rthm], h=h[rthm], l=l[rthm])).groupby("d").agg(h=("h", "max"), l=("l", "min"))
    pdh = daily.h.shift(1).to_dict(); pdl = daily.l.shift(1).to_dict()
    out = []; cur = None; lv = {}; sweep = None
    sh_hi = None; sh_lo = None  # last confirmed swing (2 left / 2 right)
    on_h = -1e18; on_l = 1e18
    for i in range(4, len(b)):
        # swing confirmation at bar i (pivot i-2)
        p = i - 2
        if h[p] > max(h[p - 2:p].max(), h[p + 1:i + 1].max()): sh_hi = h[p]
        if l[p] < min(l[p - 2:p].min(), l[p + 1:i + 1].min()): sh_lo = l[p]
        if bd[i] != cur:
            cur = bd[i]; lv = {}; sweep = None
            if cur in pdh and not np.isnan(pdh[cur]): lv["pdh"] = pdh[cur]; lv["pdl"] = pdl[cur]
            on_h, on_l = -1e18, 1e18
        if bmod[i] < 570:
            on_h = max(on_h, h[i]); on_l = min(on_l, l[i]); continue
        if bmod[i] >= 960: continue
        if "onh" not in lv and on_h > -1e17: lv["onh"] = on_h; lv["onl"] = on_l
        if not (ENTRY_LO <= mc[i] <= ENTRY_HI): continue
        highs = [v for k2, v in lv.items() if k2 in ("pdh", "onh")] + ([sh_hi] if sh_hi else [])
        lows = [v for k2, v in lv.items() if k2 in ("pdl", "onl")] + ([sh_lo] if sh_lo else [])
        if any(h[i] > x and c[i] < x for x in highs): sweep = (-1, i, h[i])
        elif any(l[i] < x and c[i] > x for x in lows): sweep = (1, i, l[i])
        if sweep is None or i - sweep[1] > W: continue
        side, si, ext = sweep
        ext = max(ext, h[si:i + 1].max()) if side == -1 else min(ext, l[si:i + 1].min())
        fvg = (side == -1 and l[i - 2] > h[i] and i - 1 >= si) or (side == 1 and h[i - 2] < l[i] and i - 1 >= si)
        if not fvg: continue
        if std is not None and std[i] != side: continue
        if extra == "ema200" and (c[i] - ema[i]) * side < 0: continue
        if extra == "rsi" and (rsi[i] - 50) * side < 0: continue
        lim = (h[i] + l[i - 2]) / 2 if side == -1 else (l[i] + h[i - 2]) / 2
        lim = round(lim / TICK) * TICK
        stop = ext + TICK if side == -1 else ext - TICK
        dist = abs(lim - stop)
        sweep = None
        if dist < MINPT or dist > MAXPT: continue
        # limit fill within W tf bars, cancelled if stop touched first
        a0 = nxt[i]; a1 = min(rth_end[a0] if a0 < N else -1, a0 + W * tf)
        if a0 >= N or a1 < a0: continue
        seg = slice(a0, a1 + 1)
        hit = np.nonzero(H[seg] >= lim)[0] if side == -1 else np.nonzero(L[seg] <= lim)[0]
        if not len(hit): continue
        out.append((a0 + hit[0], side, dist, R, None, lim))
    return out


res = {}; streams = {}
def row(name, sigs, bench=True):
    t = collect(sigs); streams[name] = t
    r = dict(IS=stats(t, "IS"), HO=stats(t, "HO"))
    if bench: r["rand_HO"] = randbench(sigs)
    res[name] = r; print(name, json.dumps(r), flush=True)
    json.dump(res, open(OUT + "/results.json", "w"), indent=1)

base = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE__lock_.csv")
res["NOISE preset C"] = dict(IS=stats(base, "IS"), HO=stats(base, "HO"))
for tf in (1, 5, 15):
    for ex in ("flip", 1.5, 2.0):
        row(f"A ST{tf}m exit={ex}", sigs_A(tf, ex))
for tf in (1, 5):
    for R in (1.5, 2.0):
        row(f"B sweep+FVG {tf}m R={R}", sigs_B(tf, R))
for tf in (1, 5):
    for stf in (5, 15):
        if stf <= tf: continue
        for R in (1.5, 2.0):
            row(f"C {tf}m +ST{stf}m R={R}", sigs_B(tf, R, stf))
    for R in (1.5, 2.0):
        row(f"C {tf}m +ST15m+EMA200 R={R}", sigs_B(tf, R, 15, "ema200"))
        row(f"C {tf}m +ST15m+RSI50 R={R}", sigs_B(tf, R, 15, "rsi"))
for k, t in streams.items():
    t.to_csv(OUT + "/stream_" + k.replace(" ", "_").replace("=", "").replace("+", "p") + ".csv.gz", index=False)

# SuperTrend series export (10/3): 15m RTH bars + daily summary
for tf in (5, 15):
    b = BARS[tf]; d, line, _ = ST[tf]; m = (b.mod_close.values > 570) & (b.mod_close.values <= 960)
    pd.DataFrame(dict(bar_start_et=b.index[m].strftime("%Y-%m-%d %H:%M"), close=b.close.values[m], st_dir=d[m], st_line=np.round(line[m], 2))).to_csv(OUT + f"/supertrend_{tf}m_rth.csv.gz", index=False)
b = BARS[15]; d = ST[15][0]; bd = b.index.strftime("%Y-%m-%d").values; mc = b.mod_close.values
dd = pd.DataFrame(dict(d=bd, mc=mc, dir=d))
o = dd[dd.mc == 570].set_index("d").dir.rename("st15_at_0930"); cl = dd[dd.mc == 960].set_index("d").dir.rename("st15_at_1600")
r = dd[(dd.mc > 570) & (dd.mc <= 960)]; fl = r.groupby("d").dir.apply(lambda s: int((s.diff().fillna(0) != 0).sum())).rename("st15_flips_rth")
pd.concat([o, cl, fl], axis=1).dropna().astype(int).to_csv(OUT + "/supertrend_daily.csv")
print("done")
