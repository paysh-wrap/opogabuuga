"""Mean-reversion / high-win-rate study (agent meanrev).
Usage: nice -n 10 /home/user/opogabuuga/.venv/bin/python mr.py
All variants are fixed a priori (38 total). Selection uses 2019-05..2023-12 only."""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data")
SPEC = {"MNQ": dict(tick=0.25, pv=2.0, fee=1.00), "MGC": dict(tick=0.10, pv=10.0, fee=1.60)}
IS_END = pd.Timestamp("2024-01-01")


def load(sym):
    pq = os.path.join(HERE, f"{sym.lower()}.parquet")
    if os.path.exists(pq):
        return pd.read_parquet(pq)
    df = pd.read_csv(os.path.join(DATA, f"{sym.lower()}_1m.csv"))
    ts = pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
    df["date"] = ts.dt.tz_localize(None).dt.normalize()
    df["mod"] = ts.dt.hour * 60 + ts.dt.minute
    df = df[(df["mod"] >= 180) & (df["mod"] <= 1000)].drop(columns="timestamp").reset_index(drop=True)
    df.to_parquet(pq)
    return df


class Day:
    pass


def build_days(df, sym):
    days = []
    prev = None
    for d, g in df.groupby("date", sort=True):
        x = Day(); x.date = d
        for c in ("open", "high", "low", "close", "volume", "mod"):
            setattr(x, c, g[c].to_numpy(dtype=float))
        rth = (x.mod >= 570) & (x.mod < 960)
        x.has_rth = rth.sum() > 300
        if x.has_rth:
            x.rth_open = x.open[rth][0]; x.rth_close = x.close[rth][-1]
            x.rth_hi = x.high[rth].max(); x.rth_lo = x.low[rth].min()
        x.prev = None
        if prev is not None and prev.has_rth and x.has_rth and (d - prev.date).days <= 4:
            gap = abs(x.open[0] / prev.close[-1] - 1)
            if gap <= 0.015 and abs(x.rth_open / prev.rth_close - 1) <= 0.015:
                x.prev = prev  # prior-day features known (not a roll jump)
        days.append(x)
        if x.has_rth:
            prev = x
    # 14-day avg RTH range (only from valid chains)
    rng = []
    for x in days:
        x.avg_rng = np.mean(rng[-14:]) if len(rng) >= 10 and x.prev is not None else None
        if x.has_rth:
            rng.append(x.rth_hi - x.rth_lo)
    return days


def simulate(x, sp, sig, last_exit_bar):
    """sig: dict(i=signal bar (entry at i+1 open) or limit fields, dir, stop, target, tstop_mod,
    exit_flags=optional bool array (exit at next open), limit=price or None, expire_mod)."""
    t, n = sp["tick"], len(x.open)
    d = sig["dir"]; i0 = sig["i"]
    if sig.get("limit") is None:
        j = i0 + 1
        if j >= n or j <= last_exit_bar: return None
        entry = x.open[j] + d * t
    else:  # resting limit from bar i0+1 until expire, fills when traded through by 1 tick
        L = sig["limit"]; j = None
        for k in range(max(i0 + 1, last_exit_bar + 1), n):
            if x.mod[k] > sig["expire_mod"]: return None
            if (d == 1 and x.low[k] <= L - t) or (d == -1 and x.high[k] >= L + t):
                j = k; break
        if j is None: return None
        entry = L
    stop, tgt = sig["stop"], sig["target"]
    risk = (entry - stop) * d
    if risk < 4 * t or (tgt - entry) * d <= 0: return None
    ef = sig.get("exit_flags")
    k = j; ex = None; kind = None
    # on a limit fill bar, conservatively check stop on the fill bar only
    while k < n:
        if (d == 1 and x.low[k] <= stop) or (d == -1 and x.high[k] >= stop):
            ex = min(stop, x.open[k]) if d == 1 else max(stop, x.open[k])
            ex -= d * t; kind = "stop"; break
        if k > j or sig.get("limit") is None:
            if (d == 1 and x.high[k] >= tgt + t) or (d == -1 and x.low[k] <= tgt - t):
                ex = tgt; kind = "tp"; break
        if x.mod[k] >= sig["tstop_mod"] or x.mod[k] >= 1000 or k == n - 1:
            ex = x.close[k] - d * t; kind = "time"; break
        if ef is not None and ef[k] and k + 1 < n:
            k += 1; ex = x.open[k] - d * t; kind = "exit"; break
        k += 1
    pts = (ex - entry) * d
    net = pts * sp["pv"] - sp["fee"]
    return dict(date=x.date, dir=d, R=net / (risk * sp["pv"]), usd=net, kind=kind, exit_bar=k, risk_usd=risk * sp["pv"])


def run(days, sym, gen, cap=3):
    sp = SPEC[sym]; out = []
    for x in days:
        sigs = gen(x, sp)
        last = -1; cnt = 0
        for s in sorted(sigs, key=lambda s: s["i"]):
            if cap and cnt >= cap: break
            if s["i"] <= last: continue
            r = simulate(x, sp, s, last)
            if r is None: continue
            out.append(r); last = r["exit_bar"]; cnt += 1
    return pd.DataFrame(out)


# ---------------- strategies ----------------
def vwap_stats(x, start_mod):
    m = x.mod >= start_mod
    tp = (x.high + x.low + x.close) / 3
    v = np.where(m, np.maximum(x.volume, 1e-9), 0.0)
    cv = np.cumsum(v); cpv = np.cumsum(v * tp); cp2 = np.cumsum(v * tp * tp)
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = cpv / cv; sd = np.sqrt(np.maximum(cp2 / cv - vw * vw, 0))
    return vw, sd


def g_vwap(k, tgt, stop):
    def gen(x, sp):
        if not x.has_rth: return []
        vw, sd = vwap_stats(x, 570)
        tr = np.maximum(x.high - x.low, 0); atr = pd.Series(tr).rolling(30).mean().to_numpy()
        out = []
        for i in range(1, len(x.close)):
            if not (600 <= x.mod[i] <= 930) or sd[i] <= 0: continue
            for d in (1, -1):
                band = vw[i] - d * k * sd[i]; pband = vw[i - 1] - d * k * sd[i - 1]
                if (x.close[i] - band) * d < 0 and (x.close[i - 1] - pband) * d >= 0:
                    st = vw[i] - d * (k + 1) * sd[i] if stop == "sig" else x.close[i] - d * 2 * atr[i] * 1.5
                    tg = vw[i] if tgt == "vwap" else vw[i] - d * sd[i]
                    if np.isnan(st): continue
                    out.append(dict(i=i, dir=d, stop=st, target=tg, tstop_mod=960))
        return out
    return gen


def g_rsi2(exit_lvl, stop_atr):
    state = {}
    def gen(x, sp):
        if not x.has_rth: return []
        # 5m bars on this day; EMA200 / RSI2 continue across days via state (reset on roll day)
        if x.prev is None: state.clear()
        b = (x.mod // 5).astype(int); idx = np.flatnonzero(np.r_[b[1:] != b[:-1], True])
        c5 = x.close[idx]; h5 = np.maximum.reduceat(x.high, np.r_[0, idx[:-1] + 1]); l5 = np.minimum.reduceat(x.low, np.r_[0, idx[:-1] + 1])
        hist = state.get("c", np.array([])); c_all = np.r_[hist, c5]
        hh = state.get("tr", np.array([])); trs = np.r_[hh, h5 - l5]
        ema = pd.Series(c_all).ewm(span=200, adjust=False).mean().to_numpy()
        dlt = np.diff(c_all, prepend=c_all[0]); up = pd.Series(np.maximum(dlt, 0)).ewm(alpha=0.5, adjust=False).mean()
        dn = pd.Series(np.maximum(-dlt, 0)).ewm(alpha=0.5, adjust=False).mean()
        rsi = (100 * up / (up + dn).replace(0, np.nan)).fillna(50).to_numpy()
        atr = pd.Series(trs).rolling(14).mean().to_numpy()
        off = len(hist); state["c"] = c_all[-400:]; state["tr"] = trs[-400:]
        if len(c_all) < 260: return []
        ef_long = np.zeros(len(x.close), bool); ef_short = np.zeros(len(x.close), bool)
        out = []
        for q in range(len(c5)):
            p = off + q; i = idx[q]
            if rsi[p] > exit_lvl: ef_long[i] = True
            if rsi[p] < 100 - exit_lvl: ef_short[i] = True
        for q in range(len(c5)):
            p = off + q; i = idx[q]
            if not (575 <= x.mod[i] <= 930): continue
            if rsi[p] < 5 and c5[q] > ema[p]:
                out.append(dict(i=i, dir=1, stop=c5[q] - stop_atr * atr[p], target=c5[q] + 50 * atr[p], tstop_mod=x.mod[i] + 60, exit_flags=ef_long))
            elif rsi[p] > 95 and c5[q] < ema[p]:
                out.append(dict(i=i, dir=-1, stop=c5[q] + stop_atr * atr[p], target=c5[q] - 50 * atr[p], tstop_mod=x.mod[i] + 60, exit_flags=ef_short))
        return out
    return gen


def g_gap(min_gap, fill_frac):
    def gen(x, sp):
        if x.prev is None or not x.has_rth: return []
        pc = x.prev.rth_close; i = np.flatnonzero(x.mod >= 570)[0]
        o = x.open[i]; gap = o / pc - 1
        if not (min_gap <= abs(gap) <= 0.015): return []
        d = -1 if gap > 0 else 1; g = abs(o - pc)
        # defined ON the 09:30 open: signal bar = bar before 09:30 so entry = 09:30 open
        return [dict(i=i - 1, dir=d, stop=o - d * g, target=o + d * g * fill_frac, tstop_mod=690)]
    return gen


def g_pdsweep(N, tgt):
    def gen(x, sp):
        if x.prev is None or not x.has_rth: return []
        H, L = x.prev.rth_hi, x.prev.rth_lo; mid = (H + L) / 2
        out = []
        for lvl, d in ((H, -1), (L, 1)):
            brk = None; ext = None
            for i in range(len(x.close)):
                if x.mod[i] < 570: continue
                if brk is None:
                    if (d == -1 and x.high[i] > lvl) or (d == 1 and x.low[i] < lvl): brk = i; ext = x.high[i] if d == -1 else x.low[i]
                    else: continue
                ext = max(ext, x.high[i]) if d == -1 else min(ext, x.low[i])
                if i - brk > N: break
                if (x.close[i] - lvl) * d > 0:
                    if 575 <= x.mod[i] <= 930:
                        st = ext - d * sp["tick"]; e = x.close[i]
                        tg = mid if tgt == "mid" else e + d * abs(e - st)
                        out.append(dict(i=i, dir=d, stop=st, target=tg, tstop_mod=960))
                    break
        return out
    return gen


def g_drive(drive_mult, tgt_frac):
    def gen(x, sp):
        if x.avg_rng is None or not x.has_rth: return []
        o = x.rth_open; i10 = np.flatnonzero(x.mod >= 600)[0]
        hi = x.high[(x.mod >= 570) & (x.mod < 600)].max(); lo = x.low[(x.mod >= 570) & (x.mod < 600)].min()
        c = x.close[i10 - 1]; mv = c - o
        if abs(mv) < drive_mult * x.avg_rng: return []
        d = 1 if mv > 0 else -1; ext = hi if d == 1 else lo; leg = abs(ext - o)
        L = ext - d * 0.382 * leg; st = ext - d * 0.786 * leg; tg = L + d * tgt_frac * (ext - L) * d
        return [dict(i=i10 - 1, dir=d, limit=L, expire_mod=750, stop=st, target=tg, tstop_mod=780)]
    return gen


def variants():
    V = []
    for sym in ("MNQ", "MGC"):
        for k in (2, 2.5, 3):
            for t in ("vwap", "1sd"):
                V.append((sym, f"VWAPfade k={k} tgt={t} stop=(k+1)sd", g_vwap(k, t, "sig")))
        for t in ("vwap", "1sd"):
            V.append((sym, f"VWAPfade k=2.5 tgt={t} stop=3xATR30", g_vwap(2.5, t, "atr")))
        for e in (50, 70):
            for s in (1.5, 3.0):
                V.append((sym, f"RSI2 EMA200 exit>{e} stop={s}ATR", g_rsi2(e, s)))
        for N in (3, 5):
            for t in ("mid", "1R"):
                V.append((sym, f"PDsweep N={N} tgt={t}", g_pdsweep(N, t)))
        for f in (1.0, 0.5):
            V.append((sym, f"OpenDrive pullback tgt={f}x", g_drive(0.35, f)))
    for mg in (0.003, 0.005):
        for f in (1.0, 0.5):
            V.append(("MNQ", f"GapFill gap>={mg*100:.1f}% tgt={f}fill", g_gap(mg, f)))
    return V


def stats(t):
    if len(t) == 0: return dict(trades=0)
    R = t.R.to_numpy(); w = R > 0
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    s = mx = 0
    for v in R:
        s = s + 1 if v <= 0 else 0; mx = max(mx, s)
    gp = R[w].sum(); gl = -R[~w].sum()
    nd = t.date.nunique()
    return dict(trades=len(R), tpd=round(len(R) / max(nd, 1), 2), win=round(100 * w.mean(), 1),
                avgW=round(R[w].mean(), 2) if w.any() else 0, avgL=round(R[~w].mean(), 2) if (~w).any() else 0,
                expR=round(R.mean(), 3), usd=round(t.usd.mean(), 2), pf=round(gp / gl, 2) if gl > 0 else 99,
                ddR=round(dd, 1), streak=mx, beWin=None)


def main():
    res = []; trades = {}
    D = {s: build_days(load(s), s) for s in ("MNQ", "MGC")}
    for sym, name, gen in variants():
        for cap in (3, 0):
            t = run(D[sym], sym, gen, cap=cap)
            if cap == 3: trades[(sym, name)] = t
            for per, sub in (("IS", t[t.date < IS_END] if len(t) else t), ("OOS", t[t.date >= IS_END] if len(t) else t)):
                st = stats(sub); st.update(sym=sym, var=name, cap=cap, period=per); res.append(st)
        print(sym, name, "done", flush=True)
    R = pd.DataFrame(res); R.to_csv(os.path.join(HERE, "summary.csv"), index=False)
    pd.to_pickle(trades, os.path.join(HERE, "trades.pkl"))
    print(R[R.cap == 3].to_string())


if __name__ == "__main__":
    main()
