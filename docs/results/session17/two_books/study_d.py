"""D - 'Markov property' (GENERIC method only - the video the user referred to was NOT seen): Markov chains over market states, transition
probabilities fitted on IS 2019-05..2023-12 only, applied unchanged on HO 2024-01..2026-11 as (i) day-direction bias, (ii) NOISE filter /
sizing, (iii) combined with the candlestick and Connors signals.  Also: 'new combinations' of the book signals with NOISE (K rows) and a
random-thinning placebo.  writes out/d.json"""
import os, json, itertools
import numpy as np, pandas as pd
import core as C, feats as F, study_c2 as C2
HERE = os.path.dirname(os.path.abspath(__file__)); ST = HERE + "/out/streams"
data = C.load(); D = data["days"]; f = F.daily(data); B = F.connors(f)
n = len(D); IS = f["d"] <= C.SPLIT; HP = C.stop_pts(250.0)
ld = lambda k: pd.read_csv(f"{ST}/{k}.csv", dtype={"d": str})


def terc(x, m):
    q1, q2 = np.nanpercentile(x[m], [100 / 3, 200 / 3])
    return np.where(np.isnan(x), 1, np.where(x < q1, 0, np.where(x > q2, 2, 1))), (float(q1), float(q2))


S, cutS = terc(f["ret"], IS); O, cutO = terc(f["oc"], IS); G, cutG = terc(f["gap"], IS)
vol = pd.Series(np.abs(np.nan_to_num(f["ret"]))).rolling(20).mean().values
V = (vol > np.nanmedian(vol[IS])).astype(int)
UP = f["oc"] > 0
prev = lambda x, k=1: np.concatenate([np.full(k, 1, int), x[:-k]])
CTX = {  # context known before the 09:31 entry of day i
    "M1 (yesterday's state)": [prev(S)],
    "M2 (last two days' states)": [prev(S, 2), prev(S)],
    "M1+vol (yesterday's state x volatility regime)": [prev(S), prev(V)],
    "M2+vol (two days x volatility regime)": [prev(S, 2), prev(S), prev(V)],
    "M1+gap (yesterday's open-to-close state x today's opening gap)": [prev(O), G],
}


def fit(ctx, margin, min_n=30):
    key = list(zip(*ctx)); tab = {}
    for i in range(25, n):
        if IS[i] and not f["rollskip"][i]:
            a = tab.setdefault(key[i], [0, 0]); a[0] += 1; a[1] += int(UP[i])
    b = np.zeros(n, int)
    for i in range(25, n):
        c = tab.get(key[i])
        if c and c[0] >= min_n:
            p = c[1] / c[0]; b[i] = 1 if p >= 0.5 + margin else (-1 if p <= 0.5 - margin else 0)
    return b, {"".join(("DFU" if ctx[j].max() == 2 else "LH")[x] for j, x in enumerate(k)): dict(n=c[0], p_up=round(100 * c[1] / c[0], 1)) for k, c in sorted(tab.items())}


def day_trade(bias):
    out = []
    for i, (d, a) in enumerate(D):
        s = int(bias[i])
        if s == 0 or f["rollskip"][i] or np.isnan(a["open"][1]): continue
        p, xk, mae = C.walk(a, s, 1, HP, None, 390); out.append((d, s, 1, xk, p, mae))
    return pd.DataFrame(out, columns=["d", "side", "ek", "xk", "pnl", "mae"])


def hit(bias):
    r = {}
    for era, m in (("IS", IS), ("HO", ~IS)):
        k = m & (bias != 0) & ~f["rollskip"]
        r[era] = dict(days=int(k.sum()), of=int(m.sum()), hit=float(100 * np.mean(np.sign(f["oc"][k]) == bias[k])) if k.any() else float("nan"))
    return r


def sized(t, bias_fn, q=2):
    """q micros when bias_fn(day index, side) is True, else 1"""
    idx = {d: i for i, (d, _) in enumerate(D)}; t = t.copy()
    m = np.array([q if bias_fn(idx[d], s) else 1 for d, s in zip(t.d, t.side)])
    t["pnl"] *= m; t["mae"] *= m; return t, int((m > 1).sum())


def intraday_markov():
    """30-minute bars (13 per RTH day). State = tercile of the bar's return (IS cut-offs). 1st / 2nd order / 1st order x time slot."""
    bars = F.tfbars(D, 30); R = np.array([b["c"] / b["o"] - 1 for b in bars])          # n x 13
    q1, q2 = np.percentile(R[IS], [100 / 3, 200 / 3]); st = np.where(R < q1, 0, np.where(R > q2, 2, 1)); up = R > 0
    rows = []; streams = {}
    for nm, keyf in (("30m, 1st order", lambda i, j: (st[i, j - 1],)), ("30m, 2nd order", lambda i, j: (st[i, j - 2], st[i, j - 1]) if j >= 2 else None),
                     ("30m, 1st order x time of day", lambda i, j: (j, st[i, j - 1]))):
        tab = {}
        for i in range(n):
            if not IS[i]: continue
            for j in range(1, 13):
                k = keyf(i, j)
                if k is None: continue
                a = tab.setdefault(k, [0, 0]); a[0] += 1; a[1] += int(up[i, j])
        for margin in (0.03, 0.05):
            out = []
            for i, (d, a) in enumerate(D):
                if f["rollskip"][i]: continue
                ntr = 0
                for j in range(1, 13):
                    k = keyf(i, j); c = tab.get(k) if k is not None else None
                    if not c or c[0] < 100 or ntr >= 3: continue
                    p = c[1] / c[0]; s = 1 if p >= 0.5 + margin else (-1 if p <= 0.5 - margin else 0)
                    if not s or np.isnan(a["open"][30 * j]): continue
                    pnl, xk, mae = C.walk(a, s, 30 * j, HP, None, min(30 * (j + 1), 385)); out.append((d, s, 30 * j, xk, pnl, mae)); ntr += 1
            t = pd.DataFrame(out, columns=["d", "side", "ek", "xk", "pnl", "mae"]); n2 = f"{nm}, trade when IS P >= {50+100*margin:.0f}%"
            streams[n2] = t; rows.append(C.row(n2, t, f"{sum(1 for c in tab.values() if c[0] >= 100 and abs(c[1]/c[0]-.5) >= margin)} of {len(tab)} states tradable"))
    return rows


if __name__ == "__main__":
    res = {}; base = ld("NOISE_250"); lockb = ld("NOISE_250_lock"); rb = C.row("NOISE_250 baseline", base); res["base"] = rb
    c1 = json.load(open(HERE + "/out/c1.json")); c2 = json.load(open(HERE + "/out/c2.json"))
    # ------------------------------------------------ Markov daily: transition tables, hit rates, (i) bias trade
    MB = {}; tabs = {}; hits = {}; rows = []; streams = {}
    for (nm, ctx), margin in itertools.product(CTX.items(), (0.03, 0.06)):
        b, tab = fit(ctx, margin); n2 = f"{nm}, edge >= {100*margin:.0f} pts"; MB[n2] = b; tabs[nm] = tab; hits[n2] = hit(b)
        t = day_trade(b); streams[n2] = t; rows.append(C.row(n2, t))
    el = [r for r in rows if r["IS"]["n"] >= 100 and r["IS"]["net"] > 0]
    pk_bias = max(el, key=lambda r: r["IS"]["pf"])["name"] if el else None
    res["markov_bias"] = dict(rows=rows, pick=pk_bias, hits=hits, tables=tabs, cuts=dict(ret=cutS, oc=cutO, gap=cutG))
    if pk_bias: streams[pk_bias].to_csv(ST + "/D_BIAS_PICK.csv", index=False)
    # ------------------------------------------------ (ii) NOISE filter / sizing
    rows = []; fs = {}
    for nm, b in MB.items():
        for mode, fn in (("only WITH", lambda i, s, k, b=b: b[i] == s), ("not AGAINST", lambda i, s, k, b=b: b[i] != -s)):
            t = C.noise(D, allow=fn); n2 = f"NOISE {mode} {nm}"; fs[n2] = (t, fn); rows.append(C.row(n2, t))
    el = [r for r in rows if r["IS"]["pf"] >= rb["IS"]["pf"] and r["IS"]["net"] >= 0.9 * rb["IS"]["net"]]
    pk_f = max(el, key=lambda r: r["IS"]["pf"])["name"] if el else None
    res["markov_filter"] = dict(rows=rows, pick=pk_f, eligible=[r["name"] for r in el])
    rows = []
    for nm, b in MB.items():
        t, k = sized(base, lambda i, s, b=b: b[i] == s); rows.append(C.row(f"NOISE 2 micros when WITH {nm}, else 1", t, f"{k} trades doubled"))
    # IS pick for sizing = best IS net / IS max DD
    pk_s = max(rows, key=lambda r: r["IS"]["net"] / max(r["IS"]["dd"], 1))["name"]
    t2 = base.copy(); t2["pnl"] *= 2; t2["mae"] *= 2; rows.append(C.row("reference: NOISE 2 micros always", t2))
    res["markov_sizing"] = dict(rows=rows, pick=pk_s)
    res["markov_intraday"] = dict(rows=intraday_markov())
    # ------------------------------------------------ (iii) + new combinations
    r2 = F.shift(f["rsi2"]); r2[0] = 50
    cf = {}
    for nm, b in B.items():
        cf[f"NOISE only WITH {nm}"] = lambda i, s, k, b=b: b[i] == s
        cf[f"NOISE not AGAINST {nm}"] = lambda i, s, k, b=b: b[i] != -s
    for thr in (90, 95):
        cf[f"NOISE no long after RSI2 > {thr} / no short after RSI2 < {100-thr} (overbought guard)"] = lambda i, s, k, th=thr: not ((s > 0 and r2[i] > th) or (s < 0 and r2[i] < 100 - th))
        cf[f"NOISE no short after RSI2 > {thr} / no long after RSI2 < {100-thr} (momentum guard)"] = lambda i, s, k, th=thr: not ((s < 0 and r2[i] > th) or (s > 0 and r2[i] < 100 - th))
    cpick = c1["filter"]["pick"]; cfn = cf[cpick]
    K = []
    K.append(C.row("K1 NOISE + Connors day-bias trade (IS pick), one position at a time", C.merge(base, ld("C1_BIAS_PICK")), c1["bias"]["pick"]))
    K.append(C.row("K2 NOISE + Connors intraday (IS pick), one position at a time", C.merge(base, ld("C1_INTRADAY_PICK")), c1["intraday"]["pick"] or c1["intraday"]["least_bad_is"]))
    K.append(C.row("K3 NOISE + candlestick (IS pick), one position at a time", C.merge(base, ld("C2_CANDLE_PICK")), c2["pick"] or c2["least_bad_is"]))
    if pk_bias: K.append(C.row("K4 NOISE + Markov day-bias trade (IS pick), one position at a time", C.merge(base, ld("D_BIAS_PICK")), pk_bias))
    K.append(C.row("K5 NOISE with Connors filter (IS pick)", C.noise(D, allow=cfn), cpick))
    K.append(C.row("K6 NOISE + profit lock with Connors filter (IS pick)", C.noise(D, allow=cfn, lock=(100, 10)), "compare with NOISE_250_lock"))
    if pk_f:
        mfn = fs[pk_f][1]
        K.append(C.row("K7 NOISE with Connors filter AND Markov filter (both IS picks)", C.noise(D, allow=lambda i, s, k: cfn(i, s, k) and mfn(i, s, k)), pk_f))
        K.append(C.row("K8 NOISE + profit lock with Markov filter (IS pick)", C.noise(D, allow=mfn, lock=(100, 10)), pk_f))
    # candlestick + trend/bias filters (iii)
    cname = c2["pick"] or c2["least_bad_is"]; a_, level, rr = cname.split(" / "); tf = int(a_.split("m ")[0]); pat = a_.split("m ")[1]
    level = level.replace("level ", ""); rr = float(rr[:-1]); sg = C2.signals(tf)
    t200 = B["T200 (close vs 200-day average)"]
    K.append(C.row("K9 candlestick (IS pick) only WITH the 200-day trend", C2.run(sg, tf, pat, level, rr, bias=t200), cname))
    mb_best = MB[pk_bias] if pk_bias else MB[list(MB)[0]]
    K.append(C.row("K10 candlestick (IS pick) only WITH the Markov day bias", C2.run(sg, tf, pat, level, rr, bias=mb_best), pk_bias or list(MB)[0]))
    cb = B[c1["bias"]["pick"].split(" - ")[0]] if c1["bias"]["pick"] else t200
    agree = np.where((cb == mb_best) & (cb != 0), cb, 0)
    K.append(C.row("K11 day trade only when Connors bias (IS pick) AND Markov bias agree", day_trade(agree), f"hit IS/HO {hit(agree)['IS']['hit']:.1f}/{hit(agree)['HO']['hit']:.1f}%"))
    t, k = sized(base, lambda i, s: cb[i] == s and mb_best[i] == s)
    K.append(C.row("K12 NOISE 2 micros when Connors AND Markov both agree with the trade, else 1", t, f"{k} trades doubled"))
    res["combos"] = dict(rows=K, connors_filter_pick=cpick, markov_filter_pick=pk_f, markov_bias_pick=pk_bias)
    # ------------------------------------------------ placebo: random thinning of NOISE to the trade count of the Connors filter pick (HO)
    kept = len(C.noise(D, allow=cfn)) / len(base); rng = np.random.default_rng(17); pl = []
    for _ in range(300):
        t = base[rng.random(len(base)) < kept]; e = C.eval_sim(t); pl.append((e["pass_"], e["bust"], C.stats(t)["net"]))
    pl = np.array(pl)
    res["placebo"] = dict(keep_frac=kept, n=300, pass_mean=float(pl[:, 0].mean()), pass_p5=float(np.percentile(pl[:, 0], 5)), pass_p95=float(np.percentile(pl[:, 0], 95)),
                          bust_mean=float(pl[:, 1].mean()), bust_p5=float(np.percentile(pl[:, 1], 5)), bust_p95=float(np.percentile(pl[:, 1], 95)),
                          net_mean=float(pl[:, 2].mean()))
    json.dump(res, open(HERE + "/out/d.json", "w"), indent=1)
    for k in ("markov_bias", "markov_filter", "markov_sizing", "markov_intraday", "combos"):
        print("==", k, res[k].get("pick"))
        for r in res[k]["rows"]: print(C.fmt(r))
    print(json.dumps(res["placebo"])); print(json.dumps(hits)); print(json.dumps(tabs["M1 (yesterday's state)"]), json.dumps(tabs["M2 (last two days' states)"]))
