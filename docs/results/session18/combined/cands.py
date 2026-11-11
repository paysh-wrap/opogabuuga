"""Candidate-trade generator for the four strategies on ONE market (MKT=MNQ|MGC python3 -I cands.py).
Every signal a strategy would take is simulated at 1 micro as an independent trade (no own-busy filtering: the account-level selector in port.py
decides which candidates are taken).  Each candidate also stores the outcome of a 'random direction' twin (same entry bar / stop distance / R / exit rule,
opposite side) for the random-entry benchmark.
 ICT  = session18/new_ict (sweep -> MSS -> 1m FVG limit at midpoint, windows AM 10-11 / PM 14-15 ET, stop sweep extreme +-1 tick, 1.5R/2R, hold <= 60 min after the window, capped at 15:59)
 SMC  = session18/smc family C (sweep + FVG limit, only when SuperTrend(10,3) of the last closed 15m bar agrees; optional EMA200 side)
 RSI  = session18/rsi_dmi family A (Triple RSI (2|3,7,14) < 10/30/40 long, > 90/70/60 short; exit RSI2 cross 50 'mr' or 1.5R; stop 2xATR14)
 DMI  = session18/rsi_dmi family B (DMI14 + ADX>20/25 rising; exit DI flip or 1.5R / 2R; stop 2xATR14 or MAXPT)"""
import sys, pickle
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/combined")
from mlib import *

BARS = {tf: bars(tf) for tf in (1, 5, 15)}
NAN = float("nan")


def cand_rows(sigs, strat, var):
    rows = []
    for i0, side, dist, R, ex_i, lim in sigs:
        if DATE[i0] < START: continue
        ref = lim if lim is not None else O[i0]
        t = run_trade(i0, side, ref - side * dist, ref + side * R * dist if R else None, ex_i, lim)
        if not t: continue
        f = run_trade(i0, -side, ref + side * dist, ref - side * R * dist if R else None, ex_i, lim)
        rows.append(dict(strat=strat, var=var, mkt=MKT, d=t["d"], t0=UTCM[i0], t1=UTCM[t["xi"]], mod0=int(MOD[i0]), side=side, pnl=t["pnl"], mae=t["mae"], risk=t["risk"],
                         sideF=-side, pnlF=f["pnl"] if f else NAN, maeF=f["mae"] if f else NAN, t1F=UTCM[f["xi"]] if f else UTCM[t["xi"]]))
    return rows


# ------------------------------------------------------------------ RSI / DMI (copied from rsi_dmi.py)
ENTRY_LO, ENTRY_HI = SESS_LO + 5, 930


def wilder(x, n): return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().values


def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up = wilder(np.maximum(d, 0), n); dn = wilder(np.maximum(-d, 0), n)
    return 100 - 100 / (1 + up / np.where(dn == 0, 1e-9, dn))


def dmi(b, n=14):
    h, l, c = b.high.values, b.low.values, b.close.values
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = wilder(tr, n); pdi = 100 * wilder(pdm, n) / atr; mdi = 100 * wilder(mdm, n) / atr
    dx = 100 * abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-9)
    return pdi, mdi, wilder(dx, n), atr


class TF:
    def __init__(s, tf):
        b = BARS[tf]; s.b = b; s.tf = tf; s.c = b.close.values; s.nxt = b.nxt.values; s.mc = b.mod_close.values
        s.bd = b.index.strftime("%Y-%m-%d").values
        s.pdi, s.mdi, s.adx, s.atr = dmi(b)
        s.rsi = {n: rsi(s.c, n) for n in (2, 3, 7, 14)}


def rsi_state(T, ps, thr):
    a, bb, cc = (T.rsi[p] for p in ps)
    ob = (a > 100 - thr[0]) & (bb > 100 - thr[1]) & (cc > 100 - thr[2])
    os_ = (a < thr[0]) & (bb < thr[1]) & (cc < thr[2])
    return np.where(os_, 1, np.where(ob, -1, 0))


def dmi_state(T, thr):
    pdi, mdi, adx = T.pdi, T.mdi, T.adx
    rising = adx > np.r_[adx[0], adx[:-1]]
    return np.where((pdi > mdi) & (adx > thr) & rising, 1, np.where((mdi > pdi) & (adx > thr) & rising, -1, 0))


def to_sigs(T, state, exitm, mrp=2):
    out = []; n = len(state)
    ra = T.rsi[mrp]
    dd = np.where(T.pdi > T.mdi, 1, -1)
    for j in range(1, n):
        s = int(state[j])
        if s == 0 or s == state[j - 1]: continue
        if not (ENTRY_LO <= T.mc[j] <= ENTRY_HI) or T.bd[j] < START: continue
        i0 = T.nxt[j]
        if i0 >= N or DATE[i0] != T.bd[j]: continue
        dist = min(2 * T.atr[j], MAXPT)
        if exitm == "mr":
            if dist < MINPT: continue
            ex = None
            for k in range(j + 1, min(j + 400, n)):
                if T.bd[k] != T.bd[j]: break
                if (s == 1 and ra[k] > 50) or (s == -1 and ra[k] < 50) or T.mc[k] >= 955:
                    ex = T.nxt[k]; break
            if ex is not None and ex <= i0: continue
            out.append((i0, s, dist, None, ex, None))
        elif exitm == "flip":
            ex = None
            for k in range(j + 1, min(j + 400, n)):
                if T.bd[k] != T.bd[j]: break
                if dd[k] != s: ex = T.nxt[k]; break
            if ex is not None and ex <= i0: continue
            out.append((i0, s, MAXPT, None, ex, None))
        else:
            if dist < MINPT: continue
            out.append((i0, s, dist, exitm, None, None))
    return out


# ------------------------------------------------------------------ SMC family C (copied from smc.py sigs_B)
ST = {tf: supertrend(BARS[tf]) for tf in (1, 5, 15)}
SMC_LO, SMC_HI = 575, 930


def sigs_B(tf, stf=15, extra=None, W=6):
    b = BARS[tf]; h, l, c = b.high.values, b.low.values, b.close.values; nxt = b.nxt.values; mc = b.mod_close.values
    bd = b.index.strftime("%Y-%m-%d").values; bmod = mc - tf
    std = None
    if stf is not None:
        sb = BARS[stf]; sd = ST[stf][0]; sclose = (sb.index + pd.Timedelta(minutes=stf)).values
        bclose = (b.index + pd.Timedelta(minutes=tf)).values
        k = np.searchsorted(sclose, bclose, side="right") - 1; std = np.where(k >= 0, sd[np.maximum(k, 0)], 0)
    ema = None
    if extra == "ema200": ema = pd.Series(c).ewm(span=200, adjust=False).mean().values
    rthm = (bmod >= 570) & (bmod < 960)
    daily = pd.DataFrame(dict(d=bd[rthm], h=h[rthm], l=l[rthm])).groupby("d").agg(h=("h", "max"), l=("l", "min"))
    pdh = daily.h.shift(1).to_dict(); pdl = daily.l.shift(1).to_dict()
    out = []; cur = None; lv = {}; sweep = None
    sh_hi = None; sh_lo = None
    on_h = -1e18; on_l = 1e18
    for i in range(4, len(b)):
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
        if not (SMC_LO <= mc[i] <= SMC_HI): continue
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
        lim = (h[i] + l[i - 2]) / 2 if side == -1 else (l[i] + h[i - 2]) / 2
        lim = round(lim / TICK) * TICK
        stop = ext + TICK if side == -1 else ext - TICK
        dist = abs(lim - stop)
        sweep = None
        if dist < MINPT or dist > MAXPT: continue
        a0 = nxt[i]; a1 = min(rth_end[a0] if a0 < N else -1, a0 + W * tf)
        if a0 >= N or a1 < a0: continue
        seg = slice(a0, a1 + 1)
        hit = np.nonzero(H[seg] >= lim)[0] if side == -1 else np.nonzero(L[seg] <= lim)[0]
        if not len(hit): continue
        out.append((a0 + hit[0], side, dist, None, None, lim))
    return out


# ------------------------------------------------------------------ ICT Silver Bullet (ported from new_ict/lib.py; market parameters)
ET_T = df.index.values.astype("datetime64[m]").astype("int64")
DAYN = ET_T // 1440
WINS = dict(AM=(10 * 60, 11 * 60), PM=(14 * 60, 15 * 60))
FLATCAP = True   # False = original new_ict behaviour (time exit may run to the 16:00 bar close)
ICT_MINR = 6.0 if MKT == "MNQ" else 1.6
_h_ = pd.Series(H); _l_ = pd.Series(L)
_pc = np.r_[C[0], C[:-1]]
_tr = np.maximum(H - L, np.maximum(abs(H - _pc), abs(L - _pc)))
ATR = pd.Series(_tr).rolling(14, min_periods=5).mean().values


def piv(n_):
    w = 2 * n_ + 1
    ph = (_h_.rolling(w, center=True).max() == _h_) & (_h_.shift(1).rolling(n_).max() < _h_) & (_h_[::-1].shift(1).rolling(n_).max()[::-1] < _h_)
    pl = (_l_.rolling(w, center=True).min() == _l_) & (_l_.shift(1).rolling(n_).min() > _l_) & (_l_[::-1].shift(1).rolling(n_).min()[::-1] > _l_)
    return np.flatnonzero(ph.values), np.flatnonzero(pl.values)


P3H, P3L = piv(3); P5H, P5L = piv(5)
DAYS = np.unique(DAYN)
_rth = (MOD >= 570) & (MOD < 960)
RTHD = {}
for dd in DAYS:
    a = np.searchsorted(DAYN, dd); b_ = np.searchsorted(DAYN, dd, side="right"); m = _rth[a:b_]
    if m.sum() > 300:
        ii = a + np.flatnonzero(m); RTHD[int(dd)] = (H[ii].max(), L[ii].min(), C[ii[-1]] - O[ii[0]])


def bidx(day, mod): return int(np.searchsorted(ET_T, day * 1440 + mod, side="left"))


def ict_gen(win, disp=1.0, exp_sweep=25):
    o, h, l, c, atr = O, H, L, C, ATR
    m0, m1 = WINS[win]; d0 = int(np.datetime64(START, "D").astype(int)); d1 = int(np.datetime64(END, "D").astype(int)) + 4
    out = []
    for dd in DAYS.tolist():
        if dd < d0 or dd > d1 or (dd + 3) % 7 >= 5: continue
        prev = [x for x in (dd - 1, dd - 2, dd - 3, dd - 4) if x in RTHD]
        if not prev: continue
        pH, pL, _pd = RTHD[prev[0]]
        i0 = bidx(dd, m0); i1 = bidx(dd, m1)
        if i1 - i0 < 40 or i0 >= len(c): continue
        if MOD[i0] != m0 and MOD[i0] > m0 + 5: continue
        sidx = bidx(dd - 1, 18 * 60)
        if i0 - sidx < 30: continue
        sH = h[sidx:i0].max(); sL = l[sidx:i0].min()
        used = set(); active = []
        stH = [("pd", pH), ("sess", sH)]; stL = [("pd", pL), ("sess", sL)]
        for k in range(i0, i1):
            hi_levels = list(stH); lo_levels = list(stL)
            lo_ = max(0, k - 120); a = np.searchsorted(P5H, lo_); b = np.searchsorted(P5H, k - 5, side="right")
            for p in P5H[a:b]:
                if h[p + 1:k].size == 0 or h[p + 1:k].max() < h[p]: hi_levels.append(("sw", h[p]))
            a = np.searchsorted(P5L, lo_); b = np.searchsorted(P5L, k - 5, side="right")
            for p in P5L[a:b]:
                if l[p + 1:k].size == 0 or l[p + 1:k].min() > l[p]: lo_levels.append(("sw", l[p]))
            for nm, Lv in hi_levels:
                key = (nm, 1, round(Lv, 2))
                if key in used or h[k] <= Lv: continue
                used.add(key)
                if c[k] >= Lv: continue
                act = [x for x in active if x["dir"] == -1]
                if act: act[0]["ext"] = max(act[0]["ext"], h[k])
                else:
                    a = np.searchsorted(P3L, k - 90); b = np.searchsorted(P3L, k - 3, side="right")
                    if b > a: active.append(dict(dir=-1, ks=k, ext=h[k], ref=l[P3L[b - 1]]))
            for nm, Lv in lo_levels:
                key = (nm, -1, round(Lv, 2))
                if key in used or l[k] >= Lv: continue
                used.add(key)
                if c[k] <= Lv: continue
                act = [x for x in active if x["dir"] == 1]
                if act: act[0]["ext"] = min(act[0]["ext"], l[k])
                else:
                    a = np.searchsorted(P3H, k - 90); b = np.searchsorted(P3H, k - 3, side="right")
                    if b > a: active.append(dict(dir=1, ks=k, ext=l[k], ref=h[P3H[b - 1]]))
            keep = []
            for s in active:
                dr = s["dir"]
                if k - s["ks"] > exp_sweep: continue
                s["ext"] = max(s["ext"], h[k]) if dr == -1 else min(s["ext"], l[k])
                mss = (c[k] < s["ref"]) if dr == -1 else (c[k] > s["ref"])
                if k > s["ks"] and mss and np.nanmax(abs(c[k - 2:k + 1] - o[k - 2:k + 1])) >= disp * atr[k]:
                    fvg = None
                    for j in range(k, max(s["ks"] + 1, k - 12), -1):
                        if j - 2 < 0: break
                        if dr == -1 and h[j] < l[j - 2]: fvg = (l[j - 2], h[j]); break
                        if dr == 1 and l[j] > h[j - 2]: fvg = (l[j], h[j - 2]); break
                    if fvg is not None:
                        top, bot = fvg
                        out.append(dict(win=win, day=dd, k=k, dir=dr, ext=s["ext"], top=top, bot=bot))
                        continue
                keep.append(s)
            active = keep
    return out


def _run_bars(E, stop, tp, dr, f, tend):
    mae = 0.0; ex = None; xk = tend
    for b in range(f, tend + 1):
        mae = max(mae, ((H[b] - E) if dr == -1 else (E - L[b])) * PV)
        if (dr == -1 and H[b] >= stop) or (dr == 1 and L[b] <= stop):
            px = (max(stop, O[b]) + TICK) if (dr == -1 and b > f) else (min(stop, O[b]) - TICK) if (dr == 1 and b > f) else (stop + TICK if dr == -1 else stop - TICK)
            ex, xk = px, b; break
        if b > f and ((dr == -1 and L[b] <= tp - TICK) or (dr == 1 and H[b] >= tp + TICK)):
            ex, xk = tp, b; break
    if ex is None: ex = C[tend] - dr * TICK; xk = tend
    return ((ex - E) * dr * PV - FEE), mae + TICK * PV, xk


def ict_sim(cands, tgt, hold=60, expire=30, maxrisk=250.0, buf=1):
    rows = []
    for cd in cands:
        dr = cd["dir"]; k = cd["k"]; top, bot = cd["top"], cd["bot"]
        E = round(((top + bot) / 2) / TICK) * TICK
        stop = cd["ext"] + TICK * buf if dr == -1 else cd["ext"] - TICK * buf
        R = abs(E - stop)
        if R < ICT_MINR or R * PV + FEE + 2 * TICK * PV > maxrisk: continue
        tp = round((E + dr * tgt * R) / TICK) * TICK
        tend = min(int(np.searchsorted(ET_T, cd["day"] * 1440 + WINS[cd["win"]][1] + hold, side="left")), N - 1)
        if FLATCAP: tend = min(tend, int(np.searchsorted(ET_T, cd["day"] * 1440 + 960, side="left")) - 1)   # flat 15:59 (orig. ran to the 16:00 bar close)
        f = -1
        for b in range(k + 1, min(k + 1 + expire, tend)):
            if (dr == -1 and H[b] >= stop) or (dr == 1 and L[b] <= stop): break
            if (dr == -1 and H[b] >= E + TICK) or (dr == 1 and L[b] <= E - TICK): f = b; break
        if f < 0: continue
        pnl, mae, xk = _run_bars(E, stop, tp, dr, f, tend)
        s = -dr; stopF = round((E - s * R) / TICK) * TICK; tpF = round((E + s * tgt * R) / TICK) * TICK
        pnlF, maeF, xkF = _run_bars(E, stopF, tpF, s, f, tend)
        rows.append(dict(strat="ICT", var=None, mkt=MKT, d=DATE[f], t0=UTCM[f], t1=UTCM[xk], mod0=int(MOD[f]), side=dr, pnl=pnl, mae=mae, risk=R * PV,
                         sideF=s, pnlF=pnlF, maeF=maeF, t1F=UTCM[xkF], win=cd["win"], tgt=tgt, k=k))
    return rows


def main():
    rows = []
    # ICT: windows AM, PM; 1.5R / 2R; var names: 'PM 1.5R', 'AM+PM 1.5R', ...
    for win in ("AM", "PM"):
        cs = ict_gen(win); print("ICT", win, "setups", len(cs), flush=True)
        for tgt in (1.5, 2.0):
            rr = ict_sim(cs, tgt)
            for r in rr:
                if r["d"] < START: continue
                a = dict(r); a["var"] = f"{win} {tgt}R"; rows.append(a)
                if win == "PM":
                    a = dict(r); a["var"] = f"PM only {tgt}R"; rows.append(a)
    # make 'AM+PM x' = AM rows + PM rows
    out = []
    for r in rows:
        if r["var"].startswith("AM ") or r["var"].startswith("PM ") and "only" not in r["var"]:
            tgt = r["tgt"]; a = dict(r); a["var"] = f"AM+PM {tgt}R"; out.append(a)
        elif "only" in r["var"]:
            a = dict(r); a["var"] = f"PM {r['tgt']}R"; out.append(a)
    rows = out
    print("ICT cands", len(rows), flush=True)
    # SMC C
    for tf in (1, 5):
        for extra in (None, "ema200"):
            sg = sigs_B(tf, 15, extra)
            for R in (1.5, 2.0):
                name = f"{tf}m+ST15{'+EMA200' if extra else ''} R{R}"
                rr = cand_rows([(a, b_, c_, R, e, l_) for a, b_, c_, _, e, l_ in sg], "SMC", name); rows += rr
                print("SMC", name, len(rr), flush=True)
    # RSI / DMI
    TFS = {tf: TF(tf) for tf in (5, 15)}
    THR = (10, 30, 40)
    for tf in (5, 15):
        for ps in ((2, 7, 14), (3, 7, 14)):
            st = rsi_state(TFS[tf], ps, THR)
            for ex in ("mr", 1.5):
                rr = cand_rows(to_sigs(TFS[tf], st, ex), "RSI", f"TriRSI{ps[0]} {tf}m {ex}"); rows += rr; print("RSI", tf, ps, ex, len(rr), flush=True)
        for thr in (20, 25):
            st = dmi_state(TFS[tf], thr)
            for ex in ("flip", 1.5, 2.0):
                rr = cand_rows(to_sigs(TFS[tf], st, ex), "DMI", f"DMI adx>{thr} {tf}m {ex}"); rows += rr; print("DMI", tf, thr, ex, len(rr), flush=True)
    c = pd.DataFrame(rows)
    c.to_pickle(OUT + f"/cands_{MKT}.pkl")
    print(c.groupby(["strat", "var"]).size().to_string())


if __name__ == "__main__":
    main()
