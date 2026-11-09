"""Intraday-momentum backtests (agent "momentum"). Usage: python mom.py [prep|run]
Variants are fixed a priori (26 per run, see VARIANTS). Simulation is float (research only, not app code)."""
import sys, os, numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(D, "../../data")
SPEC = {"MNQ": dict(tick=0.25, pv=2.0, fee=1.00), "MGC": dict(tick=0.10, pv=10.0, fee=1.60)}
NM = 430  # minutes 09:30..16:39


def prep(sym):
    p = os.path.join(D, f"{sym.lower()}_rth.npz")
    if os.path.exists(p) and "prep" not in sys.argv:
        z = np.load(p, allow_pickle=True); return {k: z[k] for k in z.files}
    df = pd.read_csv(os.path.join(DATA, f"{sym.lower()}_1m.csv"))
    ts = pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
    mins = ts.dt.hour * 60 + ts.dt.minute - 570
    df = df[(mins >= 0) & (mins < NM)].copy(); df["m"] = mins[df.index]; df["d"] = ts[df.index].dt.date
    days = sorted(df.d.unique()); di = {d: i for i, d in enumerate(days)}
    A = {c: np.full((len(days), NM), np.nan) for c in ["open", "high", "low", "close", "volume"]}
    r, c = df.d.map(di).values, df.m.values
    for k in A: A[k][r, c] = df[k].values
    good = ~np.isnan(A["open"][:, 0]) & (np.sum(~np.isnan(A["close"][:, :390]), 1) > 300)
    for k in A: A[k] = A[k][good]
    days = np.array(days, dtype=object)[good]
    cl = pd.DataFrame(A["close"].T).ffill().T.values
    for k in ["open", "high", "low"]:
        A[k] = np.where(np.isnan(A[k]), cl, A[k])
    A["close"] = cl; A["volume"] = np.nan_to_num(A["volume"])
    A["days"] = np.array([str(d) for d in days])
    np.savez(p, **A); return A


def feats(A):
    o, h, l, c, v = A["open"], A["high"], A["low"], A["close"], A["volume"]
    tp = (h + l + c) / 3; cv = np.cumsum(v, 1)
    A["vwap"] = np.where(cv > 0, np.cumsum(tp * v, 1) / np.maximum(cv, 1e-9), c)
    o0 = o[:, 0]; pc = np.r_[np.nan, c[:-1, 389]]
    gap = np.abs(o0 / pc - 1); ok = gap <= 0.015  # roll guard: prior-day features unknown
    A["pc"] = np.where(ok, pc, np.nan)
    mv = np.abs(c / o0[:, None] - 1)
    sig = pd.DataFrame(mv).rolling(14).mean().shift(1).values
    A["sigma"] = sig
    A["ub"] = np.fmax(o0, A["pc"])[:, None] * (1 + sig)
    A["lb"] = np.fmin(o0, A["pc"])[:, None] * (1 - sig)
    return A


def trade_rec(day, side, entry, exitp, risk, how, s):
    gross = side * (exitp - entry) * s["pv"]
    slip = s["tick"] * s["pv"] * (1 + (how != "TP"))
    net = gross - slip - s["fee"]
    return dict(day=day, side=side, entry=entry, exit=exitp, risk=risk, net=net,
                r=net / (max(risk, 0.001 * entry) * s["pv"]), how=how)  # R floored at 0.1% of price for reporting only


def sim_noise(A, s, check="30", rr=None, cap=3):
    """Zarattini-Aziz-Barbon noise area. Entries at 30-min marks from 10:00 (bar m=29 close)."""
    out = []; checks = set(range(29, 360, 30)); tk = s["tick"]
    for d in range(len(A["days"])):
        if np.isnan(A["sigma"][d, 0]): continue
        o, h, l, c, vw = (A[k][d] for k in ["open", "high", "low", "close", "vwap"])
        ub, lb = A["ub"][d], A["lb"][d]
        pos = 0; n = 0; m = 29
        while m < 389:
            if pos:
                if rr:  # resting stop + limit target on bar m
                    if (pos > 0 and l[m] <= stop) or (pos < 0 and h[m] >= stop):
                        out.append(trade_rec(d, pos, ent, stop, R, "STOP", s)); pos = 0
                    elif (pos > 0 and h[m] >= tgt + tk) or (pos < 0 and l[m] <= tgt - tk):
                        out.append(trade_rec(d, pos, ent, tgt, R, "TP", s)); pos = 0
                elif check == "1" or m in checks:
                    trail = max(ub[m], vw[m]) if pos > 0 else min(lb[m], vw[m])
                    if (pos > 0 and c[m] < trail) or (pos < 0 and c[m] > trail):
                        out.append(trade_rec(d, pos, ent, o[m + 1], R, "TRAIL", s)); pos = 0
                        if m not in checks: m += 1; continue
            if pos == 0 and m in checks and (cap is None or n < cap) and m < 359 + 1:
                sd = 1 if c[m] > ub[m] else -1 if c[m] < lb[m] else 0
                if sd:
                    ent = o[m + 1]
                    stop = max(ub[m], vw[m]) if sd > 0 else min(lb[m], vw[m])
                    stop = (np.floor(stop / tk) * tk - tk) if sd > 0 else (np.ceil(stop / tk) * tk + tk)
                    R = sd * (ent - stop)
                    if R > 0:
                        pos, n = sd, n + 1
                        if rr: tgt = ent + sd * rr * R
                        m += 1; continue
            m += 1
        if pos: out.append(trade_rec(d, pos, ent, c[389], R, "EOD", s))
    return out


def sim_lasthalf(A, s, kind):
    """Gao et al. market intraday momentum: trade 15:30 open -> 16:00 close."""
    out = []; o, c, pc = A["open"], A["close"], A["pc"]
    r_last = c[:, 389] / o[:, 360] - 1
    Rn = pd.Series(np.abs(r_last) * o[:, 360]).rolling(14).mean().shift(1).values  # 1R = avg |last-30m| move
    for d in range(len(c)):
        r1 = c[d, 29] / pc[d] - 1            # prev close -> 10:00
        rf = c[d, 29] / o[d, 0] - 1          # first 30 min
        r12 = c[d, 359] / c[d, 329] - 1      # 12th half-hour 15:00-15:30
        sig = {"prevclose_10": np.sign(r1), "first30": np.sign(rf), "h12": np.sign(r12),
               "both_agree": np.sign(r1) if np.sign(r1) == np.sign(r12) else 0}[kind]
        if not np.isfinite(sig) or sig == 0 or not np.isfinite(Rn[d]): continue
        out.append(trade_rec(d, int(sig), o[d, 360], c[d, 389], Rn[d], "EOD", s))
    return out


def sim_vwap(A, s, tf=1, rr=None, cap=3):
    """VWAP trend: long close>VWAP & VWAP rising (short mirror); exit close crosses VWAP; flat 16:39."""
    out = []; tk = s["tick"]
    for d in range(len(A["days"])):
        o, h, l, c, vw = (A[k][d] for k in ["open", "high", "low", "close", "vwap"])
        pos = 0; n = 0
        for m in range(5 + tf - 1, NM - 1):
            if pos and rr:
                if (pos > 0 and l[m] <= stop) or (pos < 0 and h[m] >= stop):
                    out.append(trade_rec(d, pos, ent, stop, R, "STOP", s)); pos = 0; continue
                if (pos > 0 and h[m] >= tgt + tk) or (pos < 0 and l[m] <= tgt - tk):
                    out.append(trade_rec(d, pos, ent, tgt, R, "TP", s)); pos = 0; continue
            if (m + 1) % tf: continue  # bar-close of tf-minute bar
            if pos and not rr and ((pos > 0 and c[m] < vw[m]) or (pos < 0 and c[m] > vw[m])):
                out.append(trade_rec(d, pos, ent, o[m + 1], R, "TRAIL", s)); pos = 0; continue
            if pos == 0 and m < 425 and (cap is None or n < cap):
                up = vw[m] > vw[m - tf]
                sd = 1 if (c[m] > vw[m] and up) else -1 if (c[m] < vw[m] and not up and vw[m] < vw[m - tf]) else 0
                if sd:
                    ent = o[m + 1]
                    dist = max(abs(ent - vw[m]), 0.001 * ent)  # min stop 0.1% of price (fixed a priori)
                    stop = ent - sd * (np.ceil(dist / tk) * tk + tk); R = abs(ent - stop)
                    if rr: tgt = ent + sd * rr * R
                    pos, n = sd, n + 1
        if pos: out.append(trade_rec(d, pos, ent, c[NM - 1], R, "EOD", s))
    return out


def stats(t):
    if len(t) == 0: return dict(trades=0)
    r = t.r.values; w = r > 0; eq = np.cumsum(r); dd = np.max(np.maximum.accumulate(eq) - eq)
    st = mx = 0
    for x in r:
        st = st + 1 if x <= 0 else 0; mx = max(mx, st)
    gp, gl = t.net[t.net > 0].sum(), -t.net[t.net <= 0].sum()
    return dict(trades=len(t), tpd=round(len(t) / max(t.day.nunique(), 1), 2), win=round(100 * w.mean(), 1),
                avgW=round(r[w].mean(), 2) if w.any() else 0, avgL=round(r[~w].mean(), 2),
                expR=round(r.mean(), 3), usd=round(t.net.mean(), 2), PF=round(gp / gl, 2) if gl else 99,
                ddR=round(dd, 1), streak=mx, totusd=round(t.net.sum()))


VARIANTS = [("noise_30m_trail_EOD", sim_noise, {}), ("noise_1m_trail_EOD", sim_noise, {"check": "1"}),
            ("noise_RR1.5", sim_noise, {"rr": 1.5}), ("noise_RR2.0", sim_noise, {"rr": 2.0}),
            ("noise_RR2.5", sim_noise, {"rr": 2.5}),
            ("lasthalf_prevclose_10", sim_lasthalf, {"kind": "prevclose_10"}),
            ("lasthalf_first30", sim_lasthalf, {"kind": "first30"}), ("lasthalf_h12", sim_lasthalf, {"kind": "h12"}),
            ("lasthalf_both_agree", sim_lasthalf, {"kind": "both_agree"}),
            ("vwap_1m_trail", sim_vwap, {"tf": 1}), ("vwap_5m_trail", sim_vwap, {"tf": 5}),
            ("vwap_1m_RR2.0", sim_vwap, {"tf": 1, "rr": 2.0}), ("vwap_5m_RR2.0", sim_vwap, {"tf": 5, "rr": 2.0})]

if __name__ == "__main__":
    rows, yr = [], []
    for sym in ["MNQ", "MGC"]:
        A = feats(prep(sym)); s = SPEC[sym]; yrs = np.array([x[:4] for x in A["days"]])
        for name, fn, kw in VARIANTS:
            for cap in ([3, None] if fn is not sim_lasthalf else [1]):
                k = dict(kw); k.update({} if fn is sim_lasthalf else {"cap": cap})
                t = pd.DataFrame(fn(A, s, **k))
                if len(t) == 0: continue
                t["yr"] = yrs[t.day.values]; t["ins"] = t.yr < "2024"
                for per, sub in [("IS", t[t.ins]), ("HO", t[~t.ins])]:
                    rows.append(dict(sym=sym, var=name, cap=cap, per=per, **stats(sub)))
                for y, sub in t.groupby("yr"):
                    yr.append(dict(sym=sym, var=name, cap=cap, per=y, **stats(sub)))
                print(sym, name, cap, rows[-2], rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(D, "summary.csv"), index=False)
    pd.DataFrame(yr).to_csv(os.path.join(D, "per_year.csv"), index=False)
