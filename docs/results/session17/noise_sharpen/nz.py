"""Session 17 NOISE sharpening (helper rewrite, self-contained: no app imports).  Same bar loop / costs as
docs/results/tools/noise_area.py (session 9) and docs/results/session15/lib.noise_stream (session 15), plus switches.
Data: Databento MNQ.v.0 1-minute (volume roll), 2019-05-06 .. 2026-11-06, cached by env NZ_CSV (default scratchpad file).
Costs per round trip, 1 micro: $1.00 fee + 1 tick slippage on entry, every exit and every stop fill. Point value $2, tick 0.25.
Switches of gen():
  stop_usd (default 250 -> 124 pt)  | stop_pct (1% of entry, session-9 original; overrides stop_usd)
  lock=(trigger_pts, lock_pts)      fixed profit lock (D75-P1 / D82); a stop exit on the locked stop ends NOISE for the day (session-15 convention)
  tlock=(trigger_pts, giveback_pts) trailing profit lock: after +trigger the stop trails (max favourable price - giveback), ratchet only
  hours   = set of check bar-indexes allowed for ENTRIES (29=10:00 .. 329=15:00); exits always on every check
  norev   = None|'stop'|'any'     vwapf = None|'side'|'slope'     min_sig / minw_pts = band-width filters
  dayskip = callable(feat)->True to skip the whole day (feat has dow, lowvol)
  rnd     = seed -> random +-1 direction whenever the normal 'close outside the band' signal fires (same exits)
  extra_checks = extra check bar-indexes (e.g. 359 = 15:30 close) added to the hourly checks
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session10/five_year")
import noise_gen as NG

CSV = os.environ.get("NZ_CSV", "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/mnq_2019_2026.csv")
START, END, SPLIT = "2019-05-06", "2026-11-06", "2023-12-31"
PV, TICK, FEE = 2.0, 0.25, 1.0
_c = {}


def days():
    if "d" not in _c:
        Dd, nb = NG.load_days(CSV)
        for _, a in Dd:
            for k in list(a): a[k + "_l"] = a[k].tolist()
        moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in Dd])
        # day features (past data only) exactly as session-10 filters_study (N10 low-vol tercile of the past 500 days, N11/N12 day of week)
        F = {}; sigs = []
        for i in range(14, len(Dd)):
            sig = float(np.nanmean(moves[i - 14:i]))
            past = np.array(sigs[-500:]) if len(sigs) >= 60 else None
            F[Dd[i][0]] = dict(dow=pd.Timestamp(Dd[i][0]).day_of_week, lowvol=bool(past is not None and sig <= np.quantile(past, 1 / 3)))
            sigs.append(sig)
        _c["d"] = (Dd, nb, moves, F)
    return _c["d"]


def gen(stop_usd=250.0, stop_pct=None, look=14, step=60, maxtr=3, first_check=29, lock=None, tlock=None, hours=None, norev=None,
        min_sig=None, minw_pts=None, vwapf=None, rnd=None, dayskip=None, extra_checks=(), start=START, end=END):
    Dd, nb, moves, F = days()
    hard_usd = None if stop_usd is None else (stop_usd - FEE - 2 * TICK * PV) / PV
    checks = set(range(first_check, 360, step)) | set(extra_checks); out = []
    rng = np.random.default_rng(rnd) if rnd is not None else None
    for i in range(look, len(Dd)):
        d, a = Dd[i]
        if d < start or d > end: continue
        if dayskip is not None and dayskip(F[d]): continue
        o, h, l, c, vw = a["open_l"], a["high_l"], a["low_l"], a["close_l"], a["vwap_l"]
        pc = Dd[i - 1][1]["close_l"][nb - 1]
        if pc != pc or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = (max(o[0], pc) * (1 + sig)).tolist(); lb = (min(o[0], pc) * (1 - sig)).tolist(); sigl = sig.tolist()
        st = dict(pos=0, entry=0.0, ek=0, mae=0.0, hs=0.0, locked=False, so=-1, sk=0, w=0.0, sg=0.0, hard=0.0, mfe=0.0)
        ntr = pending = 0
        def close_trade(px, xk, stopout=False):
            nonlocal ntr
            if st["locked"] and xk > st["ek"]:
                if tlock is not None and stopout: ntr = maxtr
                elif lock is not None and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)): ntr = maxtr
            p = (px - st["entry"]) * st["pos"] * PV - FEE
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, mae=st["mae"] + TICK * PV, risk=st["hard"] * PV + FEE + 2 * TICK * PV, side=st["pos"],
                            sk=st["sk"], width=st["w"], sigk=st["sg"]))
            st["pos"] = 0
            if stopout: st["so"] = xk
        for k in range(nb):
            if c[k] != c[k]: continue
            if pending and st["pos"] == 0:
                hp = (stop_pct * (o[k] + pending * TICK)) if stop_pct is not None else hard_usd
                st.update(entry=o[k] + pending * TICK, pos=pending, ek=k, mae=0.0, locked=False, sk=k - 1, hard=hp, mfe=o[k] + pending * TICK); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hp
            pos = st["pos"]
            if pos:
                e = st["entry"]
                st["mae"] = max(st["mae"], ((e - l[k]) if pos > 0 else (h[k] - e)) * PV)
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * TICK, k, stopout=True)
                if st["pos"]:
                    if lock and not st["locked"] and ((pos > 0 and h[k] >= e + lock[0]) or (pos < 0 and l[k] <= e - lock[0])):
                        st["locked"] = True; st["hs"] = max(st["hs"], e + lock[1]) if pos > 0 else min(st["hs"], e - lock[1])
                    if tlock:
                        st["mfe"] = max(st["mfe"], h[k]) if pos > 0 else min(st["mfe"], l[k])
                        if (pos > 0 and st["mfe"] >= e + tlock[0]) or (pos < 0 and st["mfe"] <= e - tlock[0]):
                            st["locked"] = True
                            ns = st["mfe"] - pos * tlock[1]
                            st["hs"] = max(st["hs"], ns) if pos > 0 else min(st["hs"], ns)
            if st["pos"] and k == nb - 1: close_trade(c[k] - st["pos"] * TICK, k)
            if k in checks:
                pos = st["pos"]; trail_exit = False
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1; trail_exit = True
                        close_trade((o[nk] if nk < nb and o[nk] == o[nk] else c[k]) - pos * TICK, min(nk, nb - 1))
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        wk = ub[k] - lb[k]; sgk = sigl[k]; ok = (hours is None or k in hours)
                        if min_sig is not None and sgk < min_sig: ok = False
                        if minw_pts is not None and wk < minw_pts: ok = False
                        if ok and norev and st["so"] == k: ok = False
                        if ok and norev == "any" and trail_exit: ok = False
                        if ok and vwapf:
                            if side * (c[k] - vw[k]) <= 0: ok = False
                            elif vwapf == "slope" and k >= 60 and side * (vw[k] - vw[k - 60]) <= 0: ok = False
                        if ok:
                            if rng is not None: side = 1 if rng.random() < 0.5 else -1
                            pending, ntr = side, ntr + 1; st["w"], st["sg"] = wk, sgk
    return pd.DataFrame(out)


def era(t, e):
    if e == "IS": return t[t.d <= SPLIT]
    if e == "HO": return t[t.d > SPLIT]
    if e == "ALL": return t
    raise ValueError(e)


def stats(t, e):
    t = era(t, e)
    if not len(t): return dict(n=0, win=float("nan"), pf=float("nan"), net=0.0, dd=0.0, avg=0.0)
    w = t.pnl > 0; gl = -t.pnl[~w].sum()
    cum = np.concatenate([[0], t.pnl.cumsum().values])
    return dict(n=int(len(t)), win=float(100 * w.mean()), pf=float(t.pnl[w].sum() / gl) if gl > 0 else float("inf"), net=float(t.pnl.sum()),
                dd=float(np.max(np.maximum.accumulate(cum) - cum)), avg=float(t.pnl.mean()))
