"""Order-flow families on ESTIMATED bars (signed volume = CLV x volume), 2019-05..2026-11, RTH 1m cached bars, MNQ + MGC.  No real delta/footprint/DOM/gamma.
 AMT+  : prior-RTH value area context (acceptance in first 30 min), location = prior VAH/VAL/POC/H/L touch, 5m trigger = estimated absorption (heavy opposing delta, close in
         the favourable half) or delta flip; stop 1 tick beyond trigger bar; 2R; max 2/day, day ends after the first win (teacher: green, stop).  Refinement = context LOCK.
 ATRZ  : volume-event zone (5m bar vol >= m x avg20), Wilder ATR(14) of 5m bars; reversion entry when a close is k ATR beyond the zone edge, target = zone edge,
         stop (a) k+1 ATR (rules file) or (b) 2R floor (stop = k/2 ATR so reward >= 2R).  Refinement = dead-zone 11:15-13:30 only if rel-vol>=1.5, no entries after 15:50.
Costs: $fee RT + 1 tick on entry, stop and flat exits (TP fills at the limit).  1 micro.  Pick = IS 2019-05..2025-11-05, judge = last 12 months."""
import sys, json, numpy as np, pandas as pd
import lib
from lib import era, stats, eval_boot
MK = dict(MNQ=dict(PV=2.0, TICK=.25, FEE=1.0, MAXPT=124., MINPT=4.), MGC=dict(PV=10., TICK=.1, FEE=1.6, MAXPT=25., MINPT=1.6))

def prep(sym):
    D = lib.build_days(sym); F = lib.day_feats(D); P = MK[sym]; days = {}
    allc5 = []
    for d, a in D:
        o, h, l, c, v = (np.nan_to_num(a[k], nan=np.nan) for k in ("open", "high", "low", "close", "volume"))
        o, h, l, c = (pd.Series(x).ffill().bfill().values for x in (o, h, l, c)); v = np.nan_to_num(v)
        rg = h - l; clv = np.where(rg > 0, ((c - l) - (h - c)) / np.where(rg > 0, rg, 1), 0.0); sv = clv * v
        n5 = 78; r = lambda x: x[:n5 * 5].reshape(n5, 5)
        b = dict(o=r(o)[:, 0], h=r(h).max(1), l=r(l).min(1), c=r(c)[:, -1], v=r(v).sum(1), sv=r(sv).sum(1))
        days[d] = dict(a=dict(open=o, high=h, low=l, close=c), b=b)
    # Wilder ATR(14) over the concatenated 5m sequence (known at bar close)
    ds = sorted(days); H = np.concatenate([days[d]["b"]["h"] for d in ds]); L = np.concatenate([days[d]["b"]["l"] for d in ds]); C = np.concatenate([days[d]["b"]["c"] for d in ds])
    tr = np.maximum(H - L, np.maximum(abs(H - np.r_[C[0], C[:-1]]), abs(L - np.r_[C[0], C[:-1]]))); atr = np.zeros_like(tr); atr[:14] = tr[:14].mean()
    for i in range(14, len(tr)): atr[i] = (atr[i - 1] * 13 + tr[i]) / 14
    for n, d in enumerate(ds): days[d]["b"]["atr"] = atr[n * 78:(n + 1) * 78]
    return D, F, days, P, ds

def run_trade(a, i0, s, stop, tp, P):
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]; e = o[i0] + s * P["TICK"]; risk = s * (e - stop)
    if risk < P["MINPT"] or risk > P["MAXPT"]: return None
    if tp is not None and (tp - e) * s <= 0: return None
    mae = 0.; px = None
    for i in range(i0, 390):
        mae = max(mae, s * (e - (l[i] if s > 0 else h[i])))
        if (s > 0 and l[i] <= stop) or (s < 0 and h[i] >= stop): px = (min(stop, o[i]) if s > 0 else max(stop, o[i])) - s * P["TICK"]; break
        if tp is not None and ((s > 0 and h[i] >= tp) or (s < 0 and l[i] <= tp)): px = tp; break
    if px is None: i = 389; px = c[389] - s * P["TICK"]
    return dict(pnl=(px - e) * s * P["PV"] - P["FEE"], mae=mae * P["PV"] + P["FEE"], xi=i, risk=risk * P["PV"])

def amt(S, k=1.5, lock=True, dead=False, rvmin=None, R=2.0, rnd=None, start=lib.S0):
    D, F, days, P, ds = S; out = []; rng = np.random.default_rng(rnd) if rnd is not None else None
    for d in ds:
        if d < start or d not in F or "atr" not in F[d]: continue
        f = F[d]; b = days[d]["b"]; a = days[d]["a"]
        ctx = np.median(b["c"][:6]); cx = 1 if ctx > f["vah"] else (-1 if ctx < f["val"] else 0)
        ad = pd.Series(np.abs(b["sv"])).rolling(20, min_periods=6).mean().shift(1).values; cvol = np.cumsum(b["v"])
        busy = -1; cnt = 0
        for j in range(6, 76):
            if cnt >= 2 or j * 5 + 5 <= busy: continue
            tmin = 570 + j * 5 + 5
            if dead and 675 <= tmin < 810 and (rvmin is None or cvol[j] / f["rv_base"][j * 5 + 4] < rvmin): continue
            if rvmin is not None and not dead and cvol[j] / f["rv_base"][j * 5 + 4] < rvmin: continue
            tol = 0.02 * f["atr"]
            r = dict(o=b["o"][j], h=b["h"][j], l=b["l"][j], c=b["c"][j], sv=b["sv"][j]); mid = (r["h"] + r["l"]) / 2
            heavy = abs(r["sv"]) > k * ad[j] if ad[j] == ad[j] else False
            prev_sv = b["sv"][j - 1]
            for s in (1, -1):
                lv = [f["val"], f["poc"], f["pL"]] if s > 0 else [f["vah"], f["poc"], f["pH"]]
                touch = any((r["l"] <= x + tol and r["c"] > x) if s > 0 else (r["h"] >= x - tol and r["c"] < x) for x in lv)
                if not touch: continue
                if lock:
                    if cx != 0 and cx != s: continue
                    if cx == 0:   # balance: only edges
                        edge = f["val"] if s > 0 else f["vah"]
                        if not ((r["l"] <= edge + tol and r["c"] > edge) if s > 0 else (r["h"] >= edge - tol and r["c"] < edge)): continue
                conf = (heavy and s * r["sv"] < 0 and s * (r["c"] - mid) > 0) or (s * prev_sv < 0 and ad[j] == ad[j] and s * r["sv"] > k * ad[j] and s * (r["c"] - (b["h"][j - 1] if s > 0 else b["l"][j - 1])) > 0)
                if not conf: continue
                stop = (r["l"] - P["TICK"]) if s > 0 else (r["h"] + P["TICK"]); ss = s
                if rng is not None:
                    ref = r["c"]; dist = abs(ref - stop); ss = 1 if rng.random() < .5 else -1; stop = ref - ss * dist
                i0 = (j + 1) * 5; e = a["open"][i0] + ss * P["TICK"]
                t = run_trade(a, i0, ss, stop, e + ss * R * ss * (e - stop) if True else None, P)
                if t is None: continue
                out.append(dict(d=d, **t)); busy = t["xi"]; cnt += 1
                if t["pnl"] > 0: cnt = 99
                break
    return pd.DataFrame(out, columns=["d", "pnl", "mae", "xi", "risk"])

def atrz(S, m=2.5, kk=1, stopmode="a", dead=False, rv_dead=1.5, last=15 * 60 + 50, rnd=None, start=lib.S0):
    D, F, days, P, ds = S; out = []; rng = np.random.default_rng(rnd) if rnd is not None else None
    for d in ds:
        if d < start or d not in F or "atr" not in F[d]: continue
        f = F[d]; b = days[d]["b"]; a = days[d]["a"]; av = pd.Series(b["v"]).rolling(20, min_periods=6).mean().shift(1).values; cvol = np.cumsum(b["v"])
        events = []; cnt = 0; busy = -1
        for j in range(3, 76):
            tmin = 570 + j * 5 + 5
            if av[j] == av[j] and b["v"][j] >= m * av[j]: events.append((j, b["l"][j], b["h"][j]))
            if cnt >= 2 or j * 5 + 5 <= busy or tmin > last: continue
            if dead and 675 <= tmin < 810 and cvol[j] / f["rv_base"][j * 5 + 4] < rv_dead: continue
            atr = b["atr"][j]
            for ev in events[::-1]:
                if j - ev[0] > 36 or j <= ev[0]: continue
                s = 0
                if b["c"][j] > ev[2] + kk * atr: s = -1; edge = ev[2]
                elif b["c"][j] < ev[1] - kk * atr: s = 1; edge = ev[1]
                if not s: continue
                i0 = (j + 1) * 5; e = a["open"][i0] + s * P["TICK"]
                stop = e - s * ((kk + 1) * atr if stopmode == "a" else (kk * atr) / 2)
                ss = s; tp = edge
                if rng is not None: ss = 1 if rng.random() < .5 else -1; stop = e - ss * abs(e - stop); tp = e + ss * abs(e - edge)
                t = run_trade(a, i0, ss, stop, tp, P)
                events = [x for x in events if x is not ev]
                if t is None: break
                if stopmode == "b" and (abs(tp - e) < 2 * abs(e - stop) - 1e-9): break
                out.append(dict(d=d, **t)); busy = t["xi"]; cnt += 1; break
    return pd.DataFrame(out, columns=["d", "pnl", "mae", "xi", "risk"])

def row(t):
    r = {e: stats(t, e) for e in ("IS", "J")}
    if len(era(t, "J")) >= 5: r["boot_J"] = eval_boot(t, "J", 25, n_paths=300)
    if len(era(t, "IS")) >= 5: r["boot_IS"] = eval_boot(t, "IS", 25, n_paths=300)
    return r

if __name__ == "__main__":
    sym = sys.argv[1]; S = prep(sym); res = []
    V = []
    for k in (1.0, 1.5):
        for lock in (False, True): V.append(("AMT+", dict(k=k, lock=lock), lambda kw=dict(k=k, lock=lock): amt(S, **kw), lambda sd, kw=dict(k=k, lock=lock): amt(S, rnd=sd, **kw)))
    for kw in (dict(k=1.5, lock=True, dead=True, rvmin=1.0), dict(k=1.5, lock=True, rvmin=1.0), dict(k=1.5, lock=False, rvmin=1.0)):
        V.append(("AMT+", kw, lambda kw=kw: amt(S, **kw), lambda sd, kw=kw: amt(S, rnd=sd, **kw)))
    for m in (2.0, 3.0):
        for kk in (1, 2):
            for sm in ("a", "b"):
                kw = dict(m=m, kk=kk, stopmode=sm); V.append(("ATRZ", kw, lambda kw=kw: atrz(S, **kw), lambda sd, kw=kw: atrz(S, rnd=sd, **kw)))
    for kw in (dict(m=2.0, kk=1, stopmode="b", dead=True), dict(m=2.0, kk=1, stopmode="a", dead=True)):
        V.append(("ATRZ", kw, lambda kw=kw: atrz(S, **kw), lambda sd, kw=kw: atrz(S, rnd=sd, **kw)))
    for fam, kw, f, fr in V:
        t = f(); r = dict(sym=sym, fam=fam, kw=kw, **row(t))
        rb = [fr(sd) for sd in range(6)]
        r["rand"] = {e: dict(avg=float(np.mean([stats(x, e)["avg"] for x in rb])), pf=float(np.nanmedian([stats(x, e)["pf"] for x in rb]))) for e in ("IS", "J")}
        res.append(r); t.to_csv(lib.OUT + f"/streams_of_{sym}_{len(res)}.csv", index=False)
        print(sym, fam, kw, "IS", r["IS"]["n"], round(r["IS"]["pf"], 2), "J", r["J"]["n"], round(r["J"]["pf"], 2), flush=True)
        json.dump(res, open(lib.OUT + f"/of_long_{sym}.json", "w"), indent=1, default=float)
