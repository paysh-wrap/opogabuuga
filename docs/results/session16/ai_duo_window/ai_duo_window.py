"""AI Duo window study (session 16). Research only. usage: python3 ai_duo_window.py <mnq_1m.csv> [seeds=300]
Data: Databento GLBX.MDP3 MNQ.v.0 ohlcv-1m (volume roll), tz America/New_York.
Minute index m = wall-clock minutes since the previous calendar day 18:00 ET (Globex open). 09:30=930, 03:00=540, 11:00=1020, 11:30=1050, 16:00=1320.
AI side is SIMULATED (accuracy vs the day's real RTH open->close direction); NEUTRAL days skipped at random. Results are BOUNDS, not evidence."""
import sys, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
INST = {"MNQ": dict(pv=2.0, tick=0.25, fee=1.0, jump=0.01, ffill=False), "MGC": dict(pv=10.0, tick=0.1, fee=1.5, jump=0.02, ffill=True)}
CUR = {}   # active instrument params (pv, tick, fee, cap, minstop)
RR = 2.0
WINDOWS = {  # name: (first allowed entry minute, flat minute (exclusive end), vwap anchor minute)
    "A 09:36-11:30": (936, 1050, 930),      # RTH-anchored VWAP (as live)
    "L 03:00-11:30": (540, 1050, 0),        # MAIN (user 2026-11-10): London open -> 11:30, Globex 18:00 anchored VWAP
    "B 03:00-11:00": (540, 1020, 0),
    "C 03:00-09:30": (540, 930, 0),
}
ACCS = [0.50, 0.55, 0.60, 0.65, 0.70]
NEUTRAL = [0.27, 0.73]   # 27% = user's brief; 73% = "agree-strong" days only fire ~27% of days (design doc)
PER = {"2019-2023": ("2019-01-01", "2023-12-31"), "2024-2026": ("2024-01-01", "2026-12-31"), "last12m": ("2025-11-10", "2026-12-31")}

def load(path, K):
    df = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    df = df[~df.index.duplicated()]
    base = (df.index - pd.Timedelta(hours=18)).normalize()   # 18:00 previous day -> trading date = base + 1 day
    out = []; skipped = 0
    for b, g in df.groupby(base):
        d = b + pd.Timedelta(days=1)
        if d.weekday() >= 5: continue
        m = ((g.index - (b + pd.Timedelta(hours=18))) / pd.Timedelta(minutes=1)).astype(int).values
        ok = (m >= 0) & (m < 1320); m = m[ok]; g = g[ok]
        a = {}
        for c in ("open", "high", "low", "close", "volume"):
            x = np.full(1320, np.nan); x[m] = g[c].values; a[c] = x
        need = 195 if K["ffill"] else 380
        if np.isfinite(a["close"][930:1320]).sum() < need or not np.isfinite(a["close"][930:960]).any(): skipped += 1; continue
        if K["ffill"]:   # thin market: a minute with no trade = price unchanged (same convention as session 15 lib)
            c0 = pd.Series(a["close"]).ffill().bfill().values
            for col in ("open", "high", "low"): a[col] = np.where(np.isnan(a[col]), c0, a[col])
            a["close"] = c0; a["volume"] = np.nan_to_num(a["volume"])
        cl = a["close"][~np.isnan(a["close"])]
        if np.abs(np.diff(cl) / cl[:-1]).max() > K["jump"]: skipped += 1; continue   # roll / bad-print guard
        out.append((d.strftime("%Y-%m-%d"), a))
    return out, skipped

def vwap_from(a, anchor):
    tp = (a["high"] + a["low"] + a["close"]) / 3; v = np.nan_to_num(a["volume"])
    tp = np.nan_to_num(tp, nan=0.0)
    cv = np.cumsum(np.where(np.arange(1320) >= anchor, v, 0)); ctp = np.cumsum(np.where(np.arange(1320) >= anchor, tp * v, 0))
    base_v = cv[anchor - 1] if anchor > 0 else 0; base_t = ctp[anchor - 1] if anchor > 0 else 0
    return (ctp - base_t) / np.maximum(cv - base_v, 1)

def bars5(a):
    r = {}
    for k, f in (("open", None), ("high", np.nanmax), ("low", np.nanmin), ("close", None)):
        x = a[k].reshape(264, 5)
        if k == "open": r[k] = np.array([row[~np.isnan(row)][0] if (~np.isnan(row)).any() else np.nan for row in x])
        elif k == "close": r[k] = np.array([row[~np.isnan(row)][-1] if (~np.isnan(row)).any() else np.nan for row in x])
        else: r[k] = f(x, axis=1)
    return r

def trade(a, b5, vw, ws, we, s, K):
    """first 5m bar (start b, close at b+5) that pulls back to VWAP and closes back in direction s; entry at next 1m open + 1 tick."""
    for bi in range(ws // 5 - 1, we // 5 - 1):
        b = bi * 5
        if b + 5 < ws: continue
        if 930 <= b < 935: continue               # D10 exclusion
        if b + 5 > we - 5: break
        o, h, l, c = b5["open"][bi], b5["high"][bi], b5["low"][bi], b5["close"][bi]
        if np.isnan(c) or np.isnan(h): continue
        v = vw[b + 4]
        if s > 0: trig = l <= v < c and c > o
        else: trig = h >= v > c and c < o
        if not trig: continue
        pb = [bi, bi - 1] if bi > 0 else [bi]
        ext = np.nanmin(b5["low"][pb]) if s > 0 else np.nanmax(b5["high"][pb])
        me = b + 5
        if np.isnan(a["open"][me]): continue
        e = a["open"][me] + s * K['tick']
        stop = ext - s * K['tick']
        sp = abs(e - stop)
        if sp > K['cap']: continue                   # STOP_TOO_WIDE skip
        if sp < K['minstop']: sp = K['minstop']; stop = e - s * sp
        tgt = e + s * RR * sp
        pnl = None
        for j in range(me, we):
            if np.isnan(a["close"][j]): continue
            hj, lj, oj = a["high"][j], a["low"][j], a["open"][j]
            if (s > 0 and lj <= stop) or (s < 0 and hj >= stop):
                px = (min(stop, oj) if s > 0 else max(stop, oj)) - s * K['tick']
                pnl = (px - e) * s * K['pv'] - K['fee']; xj = j; break
            if (s > 0 and hj >= tgt + K['tick']) or (s < 0 and lj <= tgt - K['tick']):
                pnl = (tgt - e) * s * K['pv'] - K['fee']; xj = j; break
        if pnl is None:
            j = we - 1
            while j > me and np.isnan(a["close"][j]): j -= 1
            pnl = (a["close"][j] - s * K['tick'] - e) * s * K['pv'] - K['fee']; xj = j
        return pnl, me, xj, sp
    return None

def stats(p):
    p = np.asarray(p, float)
    if len(p) == 0: return dict(n=0, win=np.nan, pf=np.nan, net=0.0, dd=0.0, avg=np.nan)
    w = p[p > 0].sum(); l = -p[p <= 0].sum()
    eq = np.cumsum(p)
    return dict(n=len(p), win=(p > 0).mean() * 100, pf=min(w / l, 50) if l > 0 else 50.0, net=p.sum(), dd=(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), avg=p.mean())

def build(sym, path):
    I = INST[sym]; K = dict(I); K["cap"] = (250.0 - I["fee"] - 2 * I["tick"] * I["pv"]) / I["pv"]
    K["minstop"] = 10.0 / I["pv"]   # assumption: structure stop widened to >= $10 of price risk (MNQ 5 pts, MGC 1.0 pt)
    days, sk = load(path, K); print(sym, "days", len(days), "skipped", sk, days[0][0], days[-1][0], flush=True)
    N = len(days); date = [d for d, _ in days]; tr = np.zeros(N)
    P = {w: {s: np.full((N, 4), np.nan) for s in (1, -1)} for w in WINDOWS}   # pnl, entry m, exit m, stop pts
    for i, (d, a) in enumerate(days):
        c = a["close"][930:1320]; c = c[~np.isnan(c)]; tr[i] = np.sign(c[-1] - a["open"][930]) or 1
        b5 = bars5(a)
        for w, (ws, we, anc) in WINDOWS.items():
            vw = vwap_from(a, anc)
            for s in (1, -1):
                t = trade(a, b5, vw, ws, we, s, K)
                if t: P[w][s][i] = t
    return dict(K=K, N=N, date=date, tr=tr, P=P, days=days, skipped=sk)

def noise_trades(M):
    sys.path.insert(0, __file__.rsplit("docs/results", 1)[0] + "docs/results/session10/five_year")
    import noise_gen as NG
    nd = []
    for d, a in M["days"]:
        r = {k: a[k][930:1320].copy() for k in ("open", "high", "low", "close", "volume")}
        tp = (r["high"] + r["low"] + r["close"]) / 3; v = np.nan_to_num(r["volume"])
        r["vwap"] = np.cumsum(np.nan_to_num(tp) * v) / np.maximum(np.cumsum(v), 1); nd.append((d, r))
    nt = NG.run(nd, 390, 2.0, 0.25, 1.0, 250.0); out = {}
    for r in nt.itertuples(): out.setdefault(r.d, []).append((r.ek + 930, r.xk + 930))
    return out, len(nt)

def main(mnq, mgc, nseeds=200):
    M = {"MNQ": build("MNQ", mnq), "MGC": build("MGC", mgc)}
    noise, nn_tr = noise_trades(M["MNQ"])
    alld = sorted(set(M["MNQ"]["date"]) | set(M["MGC"]["date"])); ix = {d: i for i, d in enumerate(alld)}; D = np.array(alld)
    pmask = {p: (D >= lo) & (D <= hi) for p, (lo, hi) in PER.items()}
    res = {}; diag = {}; info = {}
    def pick(m, w, call, neutral):
        """-> arrays over the union date axis: pnl, entry, exit (nan = no trade)"""
        Pw = M[m]["P"][w]; sel = np.where((call > 0)[:, None], Pw[1], Pw[-1]); sel[neutral] = np.nan
        out = np.full((len(alld), 3), np.nan); idx = [ix[d] for d in M[m]["date"]]; out[idx] = sel[:, :3]; return out
    for w in WINDOWS:
        for m in M:
            ts = [M[m]["P"][w][s][~np.isnan(M[m]["P"][w][s][:, 0])] for s in (1, -1)]; t = np.vstack(ts)
            info[f"{m}|{w}"] = dict(candidates=len(t), of=2 * M[m]["N"], median_stop_pts=float(np.median(t[:, 3])), median_entry=f"{int(np.median(t[:, 1]) + 1080) % 1440 // 60:02d}:{int(np.median(t[:, 1]) + 1080) % 60:02d}")
    for w in WINDOWS:
        for nz in NEUTRAL:
            for acc in ACCS:
                agg = {(k, p): [] for k in ("MNQ", "MGC", "BOTH") for p in PER}; ov = {(m, p): [0, 0] for m in M for p in PER}
                for seed in range(nseeds):
                    outs = {}
                    for mi, m in enumerate(M):
                        rng = np.random.default_rng(seed * 7919 + mi * 104729 + int(acc * 100) * 31 + int(nz * 100))
                        tr = np.zeros(len(alld)); tr[[ix[d] for d in M[m]["date"]]] = M[m]["tr"]
                        n_ = len(alld); call = np.where(rng.random(n_) < acc, tr, -tr); neutral = rng.random(n_) < nz
                        # ensure alignment of call per market date axis
                        sub = np.array([ix[d] for d in M[m]["date"]])
                        outs[m] = pick(m, w, call[sub], neutral[sub])
                    for p, pm in pmask.items():
                        for m in M:
                            x = outs[m][pm, 0]; agg[(m, p)].append(stats(x[~np.isnan(x)]))
                            if seed == 0:
                                for i in np.flatnonzero(pm & ~np.isnan(outs[m][:, 0])):
                                    ov[(m, p)][0] += 1
                                    if any(not (outs[m][i, 1] > x1 or outs[m][i, 2] < x0) for x0, x1 in noise.get(alld[i], [])): ov[(m, p)][1] += 1
                        both = np.concatenate([outs["MNQ"][pm, 0], outs["MGC"][pm, 0]]); order = np.argsort(np.concatenate([np.flatnonzero(pm)] * 2), kind="stable")
                        both = both[order]; agg[("BOTH", p)].append(stats(both[~np.isnan(both)]))
                for (m, p), L in agg.items():
                    mm = {k: float(np.nanmean([a_[k] for a_ in L])) for k in ("n", "win", "pf", "net", "dd", "avg")}
                    nets = [a_["net"] for a_ in L]; mm["net_p10"], mm["net_p90"] = float(np.percentile(nets, 10)), float(np.percentile(nets, 90))
                    if m != "BOTH": mm["ov_time_pct"] = ov[(m, p)][1] / ov[(m, p)][0] * 100 if ov[(m, p)][0] else 0
                    res[f"{m}|{w}|{nz}|{acc}|{p}"] = mm
    # diagnostics (no AI noise): oracle (acc 100%), anti (0%), blind long/short, no neutral skips
    for w in WINDOWS:
        for m in M:
            tr = M[m]["tr"]; d_ = np.array(M[m]["date"])
            for lab, call in (("oracle100", tr), ("anti0", -tr), ("always_long", np.ones_like(tr)), ("always_short", -np.ones_like(tr))):
                Pw = M[m]["P"][w]; sel = np.where((call > 0)[:, None], Pw[1], Pw[-1])
                for p, (lo, hi) in PER.items():
                    mk = (d_ >= lo) & (d_ <= hi); x = sel[mk, 0]; diag[f"{m}|{w}|{lab}|{p}"] = stats(x[~np.isnan(x)])
    json.dump(dict(res=res, diag=diag, info=info, ndays={m: M[m]["N"] for m in M}, skipped={m: M[m]["skipped"] for m in M}, noise_trades=nn_tr, caps={m: M[m]["K"]["cap"] for m in M}), open(__file__.rsplit("/", 1)[0] + "/results.json", "w"), indent=1)
    print("done")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 200)
