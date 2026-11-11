"""Session 18 'New ICT strategy' study on MNQ 1-minute bars (self-contained, no app imports).
Sequence: (1) liquidity sweep (prior-day H/L, session H/L, 5-bar swing) -> (2) market-structure shift (close beyond last opposing 3-bar swing,
with displacement) -> (3) limit entry on retrace into the FVG (3-candle gap, 1m or 5m) -> stop beyond sweep extreme -> targets 1.5R / 2R / opposing liquidity.
Costs: $1.00 RT fee, 1 tick slippage on stop / time exits; limit entries and TP need 1 tick of penetration to fill (conservative); stop first in a bar;
no TP check on the fill bar.  1 micro: $2/pt, tick 0.25.  No order-flow / delta / footprint confirmation (no tick data: Databento locked)."""
import os
import numpy as np, pandas as pd

CSV = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/mnq_2019_2026.csv"
SPLIT = "2023-12-31"
PV, TICK, FEE = 2.0, 0.25, 1.0
WINS = dict(AM=(10 * 60, 11 * 60), PM=(14 * 60, 15 * 60), LON=(3 * 60, 4 * 60))
_D = {}


def load():
    if "o" in _D: return _D
    df = pd.read_csv(CSV)
    ts = pd.to_datetime(df.timestamp, utc=True)
    et = ts.dt.tz_convert("America/New_York").dt.tz_localize(None)
    D = dict(o=df.open.values.astype(float), h=df.high.values.astype(float), l=df.low.values.astype(float), c=df.close.values.astype(float))
    D["t"] = et.values.astype("datetime64[m]").astype("int64")  # minutes since epoch, ET wall clock
    D["mod"] = (D["t"] % 1440).astype(int)
    D["day"] = (D["t"] // 1440).astype(int)
    h, l, c, o = D["h"], D["l"], D["c"], D["o"]
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    D["atr"] = pd.Series(tr).rolling(14, min_periods=5).mean().values
    n = len(c)
    # pivots (n bars each side); value index p, confirmed at p+n
    def piv(n_):
        H = pd.Series(h); L = pd.Series(l)
        w = 2 * n_ + 1
        ph = (H.rolling(w, center=True).max() == H) & (H.shift(1).rolling(n_).max() < H) & (H[::-1].shift(1).rolling(n_).max()[::-1] < H)
        pl = (L.rolling(w, center=True).min() == L) & (L.shift(1).rolling(n_).min() > L) & (L[::-1].shift(1).rolling(n_).min()[::-1] > L)
        return np.flatnonzero(ph.values), np.flatnonzero(pl.values)
    D["p3h"], D["p3l"] = piv(3); D["p5h"], D["p5l"] = piv(5)
    # 5m bars (clock aligned), completed index e5
    g = D["t"] // 5
    chg = np.r_[True, g[1:] != g[:-1]]
    s5 = np.flatnonzero(chg); e5 = np.r_[s5[1:] - 1, n - 1]
    D["s5"], D["e5"] = s5, e5
    D["o5"] = o[s5]; D["c5"] = c[e5]
    D["h5"] = np.maximum.reduceat(h, s5); D["l5"] = np.minimum.reduceat(l, s5)
    # HTF trend biases: sign(close - EMA20) of last COMPLETED 15m / 1h bar
    s = pd.Series(c, index=pd.to_datetime(D["t"], unit="m"))
    for nm, rule in (("b15", "15min"), ("b1h", "1h")):
        r = s.resample(rule).last().dropna(); ema = r.ewm(span=20, adjust=False).mean()
        sg = np.sign(r - ema).values
        comp = (r.index + pd.Timedelta(rule)).values.astype("datetime64[m]").astype("int64")  # completion minute
        pos = np.searchsorted(comp, D["t"] + 1, side="right") - 1  # completed by the close of this 1m bar
        D[nm] = np.where(pos >= 0, sg[np.clip(pos, 0, None)], 0.0)
    # per-day structures
    days = np.unique(D["day"]); first = np.searchsorted(D["day"], days)
    D["days"] = days; D["dfirst"] = dict(zip(days.tolist(), first.tolist()))
    rth = (D["mod"] >= 570) & (D["mod"] < 960)
    pdi = {}
    for dd in days:
        a = D["dfirst"][int(dd)]
        b = np.searchsorted(D["day"], dd, side="right")
        m = rth[a:b]
        if m.sum() > 300:
            ii = a + np.flatnonzero(m)
            pdi[int(dd)] = (h[ii].max(), l[ii].min(), c[ii[-1]] - o[ii[0]])
    D["rthd"] = pdi
    _D.update(D)
    return _D


def _bar_idx(D, day, mod):
    return int(np.searchsorted(D["t"], day * 1440 + mod, side="left"))


def gen(win, tf=1, lev="all", disp=1.0, exp_sweep=25, start="2019-05-10", end="2026-11-05"):
    """candidate setups (one per sweep that completes sweep->MSS->FVG) in window `win` ('AM','PM','LON')."""
    D = load(); o, h, l, c, atr = D["o"], D["h"], D["l"], D["c"], D["atr"]
    m0, m1 = WINS[win]
    d0 = int(pd.Timestamp(start).value // 86400 // 10**9); d1 = int(pd.Timestamp(end).value // 86400 // 10**9)
    out = []
    p3h, p3l, p5h, p5l = D["p3h"], D["p3l"], D["p5h"], D["p5l"]
    rthd = D["rthd"]; dl = sorted(rthd)
    for dd in D["days"].tolist():
        if dd < d0 or dd > d1: continue
        if pd.Timestamp(dd * 86400, unit="s").dayofweek >= 5: continue
        prev = [x for x in (dd - 1, dd - 2, dd - 3, dd - 4) if x in rthd]
        if not prev: continue
        pH, pL, pdir = rthd[prev[0]]
        i0 = _bar_idx(D, dd, m0); i1 = _bar_idx(D, dd, m1)
        if i1 - i0 < 40 or i0 >= len(c): continue
        if D["mod"][i0] != m0 and D["mod"][i0] > m0 + 5: continue
        sidx = _bar_idx(D, dd - 1, 18 * 60)
        if i0 - sidx < 30: continue
        sH = h[sidx:i0].max(); sL = l[sidx:i0].min()
        used = set(); active = []
        stH = [("pd", pH), ("sess", sH)]; stL = [("pd", pL), ("sess", sL)]
        for k in range(i0, i1):
            # --- new sweeps ---
            hi_levels = list(stH); lo_levels = list(stL)
            if lev == "all":
                lo_ = max(0, k - 120); a = np.searchsorted(p5h, lo_); b = np.searchsorted(p5h, k - 5, side="right")
                for p in p5h[a:b]:
                    if h[p + 1:k].size == 0 or h[p + 1:k].max() < h[p]: hi_levels.append(("sw", h[p]))
                a = np.searchsorted(p5l, lo_); b = np.searchsorted(p5l, k - 5, side="right")
                for p in p5l[a:b]:
                    if l[p + 1:k].size == 0 or l[p + 1:k].min() > l[p]: lo_levels.append(("sw", l[p]))
            for nm, L in hi_levels:
                key = (nm, 1, round(L, 2))
                if key in used or h[k] <= L: continue
                used.add(key)
                if c[k] >= L: continue  # accepted above -> level consumed, not a sweep
                act = [x for x in active if x["dir"] == -1]
                if act: act[0]["ext"] = max(act[0]["ext"], h[k])
                else:
                    a = np.searchsorted(p3l, k - 90); b = np.searchsorted(p3l, k - 3, side="right")
                    if b > a: active.append(dict(dir=-1, ks=k, ext=h[k], ref=l[p3l[b - 1]]))
            for nm, L in lo_levels:
                key = (nm, -1, round(L, 2))
                if key in used or l[k] >= L: continue
                used.add(key)
                if c[k] <= L: continue
                act = [x for x in active if x["dir"] == 1]
                if act: act[0]["ext"] = min(act[0]["ext"], l[k])
                else:
                    a = np.searchsorted(p3h, k - 90); b = np.searchsorted(p3h, k - 3, side="right")
                    if b > a: active.append(dict(dir=1, ks=k, ext=l[k], ref=h[p3h[b - 1]]))
            # --- MSS + FVG ---
            keep = []
            for s in active:
                dr = s["dir"]
                if k - s["ks"] > exp_sweep: continue
                s["ext"] = max(s["ext"], h[k]) if dr == -1 else min(s["ext"], l[k])
                mss = (c[k] < s["ref"]) if dr == -1 else (c[k] > s["ref"])
                if k > s["ks"] and mss and np.nanmax(abs(c[k - 2:k + 1] - o[k - 2:k + 1])) >= disp * atr[k]:
                    fvg = None
                    if tf == 1:
                        for j in range(k, max(s["ks"] + 1, k - 12), -1):
                            if j - 2 < 0: break
                            if dr == -1 and h[j] < l[j - 2]: fvg = (l[j - 2], h[j]); break
                            if dr == 1 and l[j] > h[j - 2]: fvg = (l[j], h[j - 2]); break
                    else:
                        bi = np.searchsorted(D["e5"], k, side="right") - 1  # last 5m bar completed by k
                        for b in range(bi, bi - 4, -1):
                            if b < 2 or D["s5"][b - 1] < s["ks"] - 4: break
                            if dr == -1 and D["h5"][b] < D["l5"][b - 2]: fvg = (D["l5"][b - 2], D["h5"][b]); break
                            if dr == 1 and D["l5"][b] > D["h5"][b - 2]: fvg = (D["l5"][b], D["h5"][b - 2]); break
                    if fvg is not None:
                        top, bot = fvg
                        # opposing liquidity (targets): static + unexceeded 5-bar swings in last 240 bars
                        liq = []
                        lvls = (stL if dr == -1 else stH)
                        liq += [v for _, v in lvls]
                        pp = p5l if dr == -1 else p5h; a = np.searchsorted(pp, k - 240); b2 = np.searchsorted(pp, k - 5, side="right")
                        for p in pp[a:b2]:
                            seg = l[p + 1:k] if dr == -1 else h[p + 1:k]
                            if seg.size == 0 or (seg.min() > l[p] if dr == -1 else seg.max() < h[p]): liq.append(l[p] if dr == -1 else h[p])
                        out.append(dict(win=win, day=dd, k=k, dir=dr, ext=s["ext"], top=top, bot=bot, gap=top - bot, atr=atr[k], liq=liq,
                                        pd=pdir, b15=D["b15"][k], b1h=D["b1h"][k], ks=s["ks"], i1=i1))
                        continue
                keep.append(s)
            active = keep
    return out


def simulate(cands, entry="mid", tgt=2.0, hold=60, expire=30, maxrisk=250.0, minr=6.0, buf=1):
    """simulate every candidate independently -> DataFrame (taken-if-allowed outcome); overlap / max-trades-per-day applied later by select()."""
    D = load(); o, h, l, c = D["o"], D["h"], D["l"], D["c"]; n = len(c)
    rows = []
    for cd in cands:
        dr = cd["dir"]; k = cd["k"]
        top, bot = cd["top"], cd["bot"]
        if entry == "mid": E = (top + bot) / 2
        else: E = bot if dr == -1 else top  # near edge = first touch on the retrace
        E = round(E / TICK) * TICK
        stop = cd["ext"] + dr * -1 * TICK * buf if False else (cd["ext"] + TICK * buf if dr == -1 else cd["ext"] - TICK * buf)
        R = abs(E - stop)
        if R < minr or R * PV + FEE + 2 * TICK * PV > maxrisk: continue
        if tgt == "liq":
            c_ = [v for v in cd["liq"] if (dr == 1 and v >= E + 1.5 * R) or (dr == -1 and v <= E - 1.5 * R)]
            if not c_: continue
            tp = (min(c_) if dr == 1 else max(c_)); tp = min(tp, E + 4 * R) if dr == 1 else max(tp, E - 4 * R)
        else:
            tp = E + dr * tgt * R
        tp = round(tp / TICK) * TICK
        tend = np.searchsorted(D["t"], cd["day"] * 1440 + (WINS[cd["win"]][1] + hold), side="left")
        tend = min(tend, n - 1)
        # wait for fill
        f = -1
        for b in range(k + 1, min(k + 1 + expire, tend)):
            if (dr == -1 and h[b] >= stop) or (dr == 1 and l[b] <= stop): break  # stop level traded first -> setup dead
            if (dr == -1 and h[b] >= E + TICK) or (dr == 1 and l[b] <= E - TICK): f = b; break
        if f < 0: continue
        mae = 0.0; ex = None; xk = tend
        for b in range(f, tend + 1):
            mae = max(mae, ((h[b] - E) if dr == -1 else (E - l[b])) * PV)
            if (dr == -1 and h[b] >= stop) or (dr == 1 and l[b] <= stop):
                px = (max(stop, o[b]) + TICK) if (dr == -1 and b > f) else (min(stop, o[b]) - TICK) if (dr == 1 and b > f) else (stop + TICK if dr == -1 else stop - TICK)
                ex, xk = px, b; break
            if b > f and ((dr == -1 and l[b] <= tp - TICK) or (dr == 1 and h[b] >= tp + TICK)):
                ex, xk = tp, b; break
        if ex is None:
            ex = c[tend] - dr * TICK; xk = tend
        pnl = (ex - E) * dr * PV - FEE
        rows.append(dict(win=cd["win"], day=cd["day"], k=k, f=f, xk=xk, dir=dr, pnl=pnl, mae=mae + TICK * PV, risk=R * PV, rpts=R, gapatr=cd["gap"] / cd["atr"],
                         gap=cd["gap"], pd=cd["pd"], b15=cd["b15"], b1h=cd["b1h"]))
    df = pd.DataFrame(rows)
    if len(df):
        df["d"] = pd.to_datetime(df.day * 86400, unit="s").dt.strftime("%Y-%m-%d")
    return df


def select(df, maxday=1, wins=None, bias=None, gapmin=0.0, gapmax=None, era=None):
    """sequential selection: filters, one position at a time, at most maxday trades per day (in time order across windows)."""
    if wins is not None: df = df[df.win.isin(wins)]
    if bias:
        m = np.ones(len(df), bool)
        for b in bias.split("+"):
            if b == "pd": m &= (np.sign(df.pd.values) == df.dir.values)
            elif b == "15": m &= (df.b15.values == df.dir.values)
            elif b == "1h": m &= (df.b1h.values == df.dir.values)
        df = df[m]
    df = df[df.gapatr >= gapmin]
    if gapmax is not None: df = df[df.gapatr <= gapmax]
    df = df.sort_values(["day", "k"])
    keep = []; last_day = None; cnt = 0; busy = -1
    for r in df.itertuples():
        if r.day != last_day: last_day = r.day; cnt = 0; busy = -1
        if cnt >= maxday or r.f <= busy: continue
        keep.append(r.Index); cnt += 1; busy = r.xk
    t = df.loc[keep] if keep else df.iloc[:0]
    if era == "IS": t = t[t.d <= SPLIT]
    elif era == "HO": t = t[t.d > SPLIT]
    return t


def stats(t):
    if not len(t): return dict(n=0, win=float("nan"), avg=0.0, net=0.0, dd=0.0, pf=float("nan"))
    w = t.pnl > 0; gl = -t.pnl[~w].sum(); cum = np.concatenate([[0], t.pnl.cumsum().values])
    return dict(n=len(t), win=100 * w.mean(), avg=t.pnl.mean(), net=t.pnl.sum(), dd=float(np.max(np.maximum.accumulate(cum) - cum)),
                pf=float(t.pnl[w].sum() / gl) if gl > 0 else float("inf"))
