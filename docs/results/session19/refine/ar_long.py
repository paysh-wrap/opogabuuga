"""AR Model (Christopher Creamer) bar-only approximation, MNQ.v.0 + MGC 1m cached (no downloads). Rules: ../order_flow/AR_MODEL_RULES.md.
ESTIMATED order flow only (CLV x volume). 1 micro, flat 16:00 ET, $fee + 1 tick slip on entry and every exit, stop-first inside a 1m bar.
SESSION 19 LONG-HISTORY COPY: PICK(IS)=2019-05-06..2025-11-05, JUDGE=2025-11-06..2026-11-06. usage: ar_long.py MNQ|MGC -> ar_long_<M>.json"""
import sys, json, random, itertools
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session17/noise_sharpen")
import sim
SP = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/"
OUT = "/home/user/opogabuuga/docs/results/session19/refine/"
S0, PE, J0, E = "2019-05-06", "2025-11-05", "2025-11-06", "2026-11-06"
sim.RANGES.update(PICK=(S0, PE), JUDGE=(J0, E), YEAR=(S0, E))
MK = dict(MNQ=dict(PV=2.0, TICK=0.25, FEE=1.0, MAXPT=124.0, MINPT=4.0, BIN=2.0),
          MGC=dict(PV=10.0, TICK=0.10, FEE=1.6, MAXPT=25.0, MINPT=1.6, BIN=0.5))


def load(m):
    if m == "MNQ":
        df = pd.read_csv(SP + "mnq_2019_2026.csv"); df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    else:
        df = pd.concat([pd.read_csv(SP + f"split_raw/MGC_{y}.csv", usecols=["ts_event", "open", "high", "low", "close", "volume"]) for y in range(2019, 2027)])
        df["timestamp"] = pd.to_datetime(df.ts_event, utc=True); df = df.drop(columns="ts_event")
    df = df[(df.timestamp >= "2019-04-01") & (df.timestamp <= "2026-11-08")].drop_duplicates("timestamp").sort_values("timestamp")
    df["t"] = df.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None); df = df.set_index("t")[["open", "high", "low", "close", "volume"]]
    rng = (df.high - df.low).values
    clv = np.where(rng > 0, ((df.close - df.low) - (df.high - df.close)).values / np.where(rng > 0, rng, 1), np.sign(df.close.diff().fillna(0).values))
    df["sv"] = clv * df.volume.values
    df["td"] = (df.index + pd.Timedelta(hours=6)).strftime("%Y-%m-%d")  # trading day 18:00 -> 17:00
    return df


def pivots(b, k=2):
    """confirmed swing pivots: returns series of (last pivot high, its time, last pivot low, its time) known at each bar close"""
    h, l = b.high.values, b.low.values; n = len(b)
    ph = np.full(n, np.nan); pl = np.full(n, np.nan); phi = np.full(n, -1); pli = np.full(n, -1); ph2 = np.full(n, np.nan); pl2 = np.full(n, np.nan)
    ch = cl = np.nan; chi = cli = -1; c2h = c2l = np.nan
    for i in range(n):
        j = i - k
        if j >= k:
            if h[j] == h[j - k:j + k + 1].max(): c2h, ch, chi = ch, h[j], j
            if l[j] == l[j - k:j + k + 1].min(): c2l, cl, cli = cl, l[j], j
        ph[i], phi[i], pl[i], pli[i], ph2[i], pl2[i] = ch, chi, cl, cli, c2h, c2l
    tr = np.where((ph > ph2) & (pl > pl2), 1, np.where((ph < ph2) & (pl < pl2), -1, 0))
    return pd.DataFrame(dict(ph=ph, phi=phi, pl=pl, pli=pli, tr=tr), index=b.index + (b.index[1] - b.index[0]))  # index = bar CLOSE time


def rs(df, rule, off=None):
    return df.resample(rule, label="left", closed="left", offset=off).agg(dict(open="first", high="max", low="min", close="last", volume="sum", sv="sum")).dropna()


def value_area(g, binw):
    vp = g.groupby((g.close / binw).round() * binw).volume.sum().sort_index(); px = list(vp.index); poc = vp.idxmax()
    lo = hi = px.index(poc); acc = vp[poc]; tot = vp.sum()
    while acc < 0.7 * tot and (lo > 0 or hi < len(px) - 1):
        up = vp.iloc[hi + 1] if hi + 1 < len(px) else -1; dn = vp.iloc[lo - 1] if lo > 0 else -1
        if up >= dn: hi += 1; acc += up
        else: lo -= 1; acc += dn
    return poc, px[hi], px[lo]


def build(m):
    P = MK[m]; df = load(m); TICK = P["TICK"]
    # daily ATR(20) on 18:00-17:00 days, shifted (known before the day)
    dd = df.groupby("td").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    trd = np.maximum(dd.h - dd.l, np.maximum(abs(dd.h - dd.c.shift()), abs(dd.l - dd.c.shift())))
    atr20 = trd.rolling(20).mean().shift(1)
    b5 = rs(df, "5min"); b15 = rs(df, "15min"); b1h = rs(df, "1h"); b4h = rs(df, "4h", "2h")  # 4h anchored 18:00/22:00/02:00 ...
    pv15 = pivots(b15); tr1h = pivots(b1h).tr; tr4h = pivots(b4h).tr
    # 5m per-bar estimated POC: typical price of the 1m bar with the largest volume inside the 5m bar
    g1 = df.assign(k=df.index.floor("5min"), tp=(df.high + df.low + df.close) / 3)
    poc5 = g1.loc[g1.groupby("k").volume.idxmax().values].set_index("k").tp
    b5["poc"] = poc5.reindex(b5.index).values
    poc15 = g1.assign(k=df.index.floor("15min")); poc15 = poc15.loc[poc15.groupby("k").volume.idxmax().values].set_index("k").tp
    # environment features on 5m (rolling 12 bars incl. overnight)
    c = b5.close; pc = c.shift(); tr5 = np.maximum(b5.high - b5.low, np.maximum(abs(b5.high - pc), abs(b5.low - pc)))
    b5["er"] = (c - c.shift(12)).abs() / c.diff().abs().rolling(12).sum(); b5["dir"] = np.sign(c - c.shift(12))
    ovl = (np.minimum(b5.high, b5.high.shift()) - np.maximum(b5.low, b5.low.shift())).clip(lower=0) / (b5.high - b5.low).replace(0, np.nan)
    b5["ov"] = ovl.rolling(12).mean(); b5["atr5"] = tr5.rolling(12).mean()
    b5["ad"] = b5.sv.abs().rolling(20).mean().shift(1)
    b5["td"] = (b5.index + pd.Timedelta(hours=6)).strftime("%Y-%m-%d"); b5["atrD"] = atr20.reindex(b5.td).values; b5["atrr"] = b5.atr5 / b5.atrD
    ce = b5.index + pd.Timedelta(minutes=5)  # close time
    for nm, s in (("tr15", pv15.tr), ("tr1h", tr1h), ("tr4h", tr4h), ("ph", pv15.ph), ("pl", pv15.pl), ("phi", pv15.phi), ("pli", pv15.pli)):
        b5[nm] = s.reindex(ce, method="ffill").values
    # per-day context: Asia (18:00-03:00) range, prior-day RTH value area
    days = sorted(d for d in df.td.unique() if S0 <= d <= E)
    tds = sorted(df.td.unique()); ctx = {}
    for d in tds:
        x = df[df.td == d]; t0 = pd.Timestamp(d)
        a = x[x.index < t0 + pd.Timedelta(hours=3)]; r = x[(x.index >= t0 + pd.Timedelta(hours=9, minutes=30)) & (x.index < t0 + pd.Timedelta(hours=16))]
        if len(r) < 300 or len(a) < 60: continue
        poc, vah, val = value_area(r, P["BIN"])
        ctx[d] = dict(ah=a.high.max(), al=a.low.min(), poc=poc, vah=vah, val=val, rh=r.high.max(), rl=r.low.min(),
                      post_h=x[x.index >= t0 + pd.Timedelta(hours=3)].high.max(), post_l=x[x.index >= t0 + pd.Timedelta(hours=3)].low.min())
    return dict(P=P, df=df, b5=b5, ctx=ctx, days=[d for d in days if d in ctx], tds=[d for d in tds if d in ctx], atr20=atr20, poc15=poc15, t15=b15.index)


def calib(D):
    """in-sample (PICK) multipliers: extension beyond Asia high/low in ATR20 units (asymmetric), env thresholds"""
    up, dn = [], []
    for d in D["days"]:
        if d > PE: continue
        c = D["ctx"][d]; a = D["atr20"].get(d)
        if not a or np.isnan(a): continue
        if c["post_h"] > c["ah"]: up.append((c["post_h"] - c["ah"]) / a)
        if c["post_l"] < c["al"]: dn.append((c["al"] - c["post_l"]) / a)
    q = (0.2, 0.35, 0.5, 0.7, 0.9)
    z = dict(up=[round(float(np.quantile(up, x)), 3) for x in q], dn=[round(float(np.quantile(dn, x)), 3) for x in q])
    b = D["b5"]; ins = b[(b.td >= S0) & (b.td <= PE)]
    z["atrr_q30"] = float(ins.atrr.quantile(0.3)); z["atrr_q95"] = float(ins.atrr.quantile(0.95)); z["ov_med"] = float(ins.ov.median())
    return z


def features(D, Z, k, amend):
    """one row per RTH 5m decision bar with per-side layer booleans"""
    b = D["b5"]; P = D["P"]; rows = []; T15 = D["t15"]; BT = b.index.values; BC = b.close.values
    def _sl(pi, tc):
        a0 = np.searchsorted(BT, np.datetime64(T15[int(pi)] + pd.Timedelta(minutes=15))); a1 = np.searchsorted(BT, np.datetime64(tc - pd.Timedelta(minutes=5)))
        return BC[a0:a1 + 1]
    def mincl(pi, tc):
        v = _sl(pi, tc); return v.min() if len(v) else np.inf
    def maxcl(pi, tc):
        v = _sl(pi, tc); return v.max() if len(v) else -np.inf
    for d in D["days"]:
        n = D["tds"].index(d)
        if n == 0: continue
        c = D["ctx"][d]; pc_ = D["ctx"][D["tds"][n - 1]]; a = D["atr20"].get(d)
        t0 = pd.Timestamp(d); x = b[(b.index >= t0 + pd.Timedelta(hours=9, minutes=30)) & (b.index < t0 + pd.Timedelta(hours=16))]
        post = b[(b.index >= t0 + pd.Timedelta(hours=3)) & (b.index < t0 + pd.Timedelta(hours=16))]
        for j in range(len(x) - 1):
            r = x.iloc[j]; tclose = x.index[j] + pd.Timedelta(minutes=5); mod = tclose.hour * 60 + tclose.minute
            if mod < 575 or mod > amend: continue
            sofar = post[post.index < tclose]; lo_s, hi_s = sofar.low.min(), sofar.high.max()
            # ENVIRONMENT
            comp = (r.atrr < Z["atrr_q30"] and r.ov > Z["ov_med"]) or r.atrr > Z["atrr_q95"]
            expn = (not comp) and r.er >= 0.4
            # LOCATION: top-down bias, fib 0.705-0.886 on 15m swing, prior-day VA
            sc = r.tr4h + r.tr1h + r.tr15; bias = int(np.sign(sc)) if (sc != 0 and r.tr4h != -np.sign(sc)) else 0  # top-down: 4h must not oppose
            rngf = r.ph - r.pl; fib = {1: False, -1: False}
            if 0.2 * a <= rngf <= 2.5 * a:
                if r.pli < r.phi:  # impulse up -> discount long zone
                    zl, zh = r.pl + 0.114 * rngf, r.pl + 0.295 * rngf; t_h = x.index[j]
                    fib[1] = r.low <= zh and r.close >= zl and mincl(r.phi, tclose) >= zl  # close beyond 0.886 since the swing = invalid
                if r.phi < r.pli:
                    zl, zh = r.pl + 0.705 * rngf, r.pl + 0.886 * rngf
                    fib[-1] = r.high >= zl and r.close <= zh and maxcl(r.pli, tclose) <= zh
            va = {1: r.low <= pc_["val"] + 0.05 * a and r.close >= pc_["val"] - 0.1 * a and r.close < pc_["poc"],
                  -1: r.high >= pc_["vah"] - 0.05 * a and r.close <= pc_["vah"] + 0.1 * a and r.close > pc_["poc"]}
            # PATH: Asia + ATR20 zones
            U, Dn = Z["up"], Z["dn"]
            path = {1: (c["al"] - Dn[4] * a <= lo_s <= c["al"] - Dn[0] * a) or (r.close > c["ah"] and hi_s < c["ah"] + U[2] * a),
                    -1: (c["ah"] + U[0] * a <= hi_s <= c["ah"] + U[4] * a) or (r.close < c["al"] and lo_s > c["al"] - Dn[2] * a)}
            # CONFIRMATION: estimated absorption or delta flip
            mid = (r.high + r.low) / 2; heavy = abs(r.sv) > k * r.ad; prev = x.iloc[j - 1] if j else r
            conf = {s: (heavy and s * r.sv < 0 and s * (r.close - mid) > 0) or (s * prev.sv < 0 and s * r.sv > k * r.ad and s * (r.close - (prev.high if s > 0 else prev.low)) > 0)
                    for s in (1, -1)}
            for s in (1, -1):
                env = (not comp) and (not expn or s == r.dir)
                rows.append(dict(d=d, t=tclose, s=s, E=env, L=(bias == s) and (fib[s] or va[s]), P=path[s], C=conf[s],
                                 poc=r.poc, ext=(r.low if s > 0 else r.high)))
    F = pd.DataFrame(rows).sort_values(["d", "s", "t"]).reset_index(drop=True)
    # location is a ZONE: confirmation may print up to 2 bars after price was at the location
    F["L"] = F.groupby(["d", "s"]).L.transform(lambda v: v.astype(int).rolling(3, min_periods=1).max().astype(bool))
    return F.sort_values(["d", "t", "s"]).reset_index(drop=True)


def simtrade(D, t_sig, s, stop, mode, limit=None, exp_min=10):
    df = D["df"]; P = D["P"]; TK = P["TICK"]; day_end = pd.Timestamp(t_sig.strftime("%Y-%m-%d")) + pd.Timedelta(hours=16)
    ix = D.setdefault("ix", df.index.values); a0 = np.searchsorted(ix, np.datetime64(t_sig)); a1 = np.searchsorted(ix, np.datetime64(day_end)); w = df.iloc[a0:a1]
    if len(w) < 2: return None
    H, L, O, Cc = w.high.values, w.low.values, w.open.values, w.close.values; idx = w.index
    if limit is None: i0 = 0; ent = O[0] + s * TK
    else:
        i0 = None
        for i in range(min(exp_min, len(w))):
            if (s > 0 and L[i] <= limit) or (s < 0 and H[i] >= limit):
                i0 = i; ent = min(limit, O[i]) + s * TK if s > 0 else max(limit, O[i]) + s * TK; break
            if (s > 0 and L[i] <= stop) or (s < 0 and H[i] >= stop): return None
        if i0 is None: return None
    risk = s * (ent - stop)
    if risk < P["MINPT"] or risk > P["MAXPT"]: return None
    tp = ent + s * 2 * risk if mode == "2R" else None; st = stop; be = False; mae = 0.0
    p5 = D["b5"].poc; p15 = D["poc15"]
    for i in range(i0, len(w)):
        h, l = H[i], L[i]; mae = max(mae, s * (ent - (l if s > 0 else h)))
        hit = (s > 0 and l <= st) or (s < 0 and h >= st)
        if hit and not (i == i0 and limit is not None and s * (O[i] - st) < 0 and False):
            px = (min(st, O[i]) if s > 0 else max(st, O[i])) if i > i0 else st; break
        if tp is not None and ((s > 0 and h >= tp) or (s < 0 and l <= tp)): px = tp; break
        if mode != "2R":
            fav = s * ((h if s > 0 else l) - ent)
            if not be and fav >= risk: st = ent + s * TK * 2 if s > 0 else ent + s * TK * 2; be = True; st = ent + s * 2 * TK
            tm = idx[i] + pd.Timedelta(minutes=1)
            per = 5 if mode == "trail5" else 15
            if be and tm.minute % per == 0:  # a 5m/15m candle just closed: stop behind its estimated POC
                pk = tm - pd.Timedelta(minutes=per); pp = (p5 if per == 5 else p15).get(pk)
                if pp is not None and not np.isnan(pp):
                    ns = pp - s * TK
                    st = max(st, ns) if s > 0 else min(st, ns)
                    if s * (Cc[i] - st) <= 0: st = st  # will be hit on next bar
    else: px = Cc[-1]; i = len(w) - 1
    px -= s * TK
    return dict(d=t_sig.strftime("%Y-%m-%d"), pnl=s * (px - ent) * P["PV"] - P["FEE"], mae=max(mae, 0) * P["PV"] + P["FEE"], xt=idx[i], risk=risk * P["PV"])


def run(D, F, layers, mode, rand=None, maxd=2):
    TK = D["P"]["TICK"]; rows = []; rnd = random.Random(rand)
    m = np.ones(len(F), bool)
    for Lr in layers: m &= F[Lr].values
    G = F[m]
    for d, g in G.groupby("d", sort=True):
        busy = None; cnt = 0; losses = 0
        for r in g.itertuples():
            if cnt >= maxd or losses >= 2 or (busy is not None and r.t <= busy): continue
            s = r.s
            if "C" in layers:
                stop = r.ext - s * TK; lim = r.poc
                if s * (lim - stop) <= 0: continue
            else: stop = r.ext - s * TK; lim = None
            if rand is not None:
                ref = lim if lim is not None else D["df"].open.get(r.t, np.nan)
                if np.isnan(ref): continue
                dist = abs(ref - stop); s = rnd.choice((1, -1)); stop = ref - s * dist
            t = simtrade(D, r.t, s, stop, mode, lim)
            if t is None: continue
            rows.append(t); busy = t["xt"]; cnt += 1
            if t["pnl"] < 0: losses += 1
            else: break  # teacher: green on the day -> stop
    return pd.DataFrame(rows, columns=["d", "pnl", "mae", "xt", "risk"])


def stats(t, era):
    s, e = sim.RANGES[era]; x = t[(t.d >= s) & (t.d <= e)]
    if len(x) == 0: return dict(n=0)
    p = x.pnl; w = p[p > 0]; lo = p[p < 0]; eq = p.cumsum().values
    bo = sim.eval_boot(x, era, n_paths=400, cap=250)
    return dict(n=len(x), win=round(100 * (p > 0).mean(), 1), aw=round(w.mean(), 1) if len(w) else 0, al=round(lo.mean(), 1) if len(lo) else 0,
                pf=round(w.sum() / -lo.sum(), 2) if len(lo) else 99, avg=round(p.mean(), 2), net=round(p.sum()),
                dd=round(float((np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max())), pas=round(bo["pass_"]), bust=round(bo["bust"]), med=bo["med"])


if __name__ == "__main__":
    m = sys.argv[1]; out = {}; streams = {}
    D = build(m); Z = calib(D); out[m] = dict(calib=Z); print(m, Z, flush=True)
    FR = {k: features(D, Z, k, 930) for k in (1.0, 1.5)}
    def am(F): return F[F.t.dt.hour * 60 + F.t.dt.minute <= 660].reset_index(drop=True)
    FS = {(k, "RTH"): FR[k] for k in FR}; FS.update({(k, "AM"): am(FR[k]) for k in FR})
    grid = []
    for (k, sess), F in FS.items():
        for mode in ("2R", "trail5", "trail15"):
            t = run(D, F, "ELPC", mode); grid.append(dict(k=k, sess=sess, mode=mode, pick=stats(t, "PICK"), judge=stats(t, "JUDGE"), year=stats(t, "YEAR")))
            print(m, k, sess, mode, grid[-1]["pick"], grid[-1]["judge"], flush=True)
    out[m]["full_grid"] = grid
    for sess in ("AM", "RTH"):
        cand = [g for g in grid if g["sess"] == sess and g["pick"].get("n", 0) >= 30] or [g for g in grid if g["sess"] == sess]
        best = max(cand, key=lambda g: g["pick"].get("pf", 0)); F = FS[(best["k"], sess)]; abl = []
        for r_ in range(1, 5):
            for lay in itertools.combinations("ELPC", r_):
                lay = "".join(lay)
                if "L" not in lay and "C" not in lay: continue
                t = run(D, F, lay, best["mode"]); abl.append(dict(layers=lay, pick=stats(t, "PICK"), judge=stats(t, "JUDGE")))
                if lay == "ELPC": streams[(m, sess)] = t
        rnds = [stats(run(D, F, "ELPC", best["mode"], rand=sd), "JUDGE") for sd in range(8)]
        rp = [stats(run(D, F, "ELPC", best["mode"], rand=sd), "PICK") for sd in range(8)]
        out[m][sess] = dict(best=dict(k=best["k"], mode=best["mode"]), ablation=abl,
                            rand_judge=dict(avg=round(float(np.mean([x.get("avg", 0) for x in rnds])), 2), pf=round(float(np.median([x.get("pf", 0) for x in rnds])), 2)),
                            rand_pick=dict(avg=round(float(np.mean([x.get("avg", 0) for x in rp])), 2), pf=round(float(np.median([x.get("pf", 0) for x in rp])), 2)))
        print(m, sess, out[m][sess]["best"], out[m][sess]["rand_pick"], flush=True)
        json.dump(out, open(OUT + f"ar_long_{m}.json", "w"), indent=1, default=str)
    for k_, t in streams.items(): t.to_csv(OUT + f"stream_arlong_{k_[0]}_{k_[1]}.csv", index=False)
