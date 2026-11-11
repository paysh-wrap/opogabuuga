"""C1 - Connors & Alvarez: (i) day-direction bias trade, (ii) NOISE filter, (iii) intraday-only version (5/15-minute bars).
writes out/c1.json + streams."""
import os, json, itertools
import numpy as np, pandas as pd
import core as C, feats as F
HERE = os.path.dirname(os.path.abspath(__file__)); ST = HERE + "/out/streams"; os.makedirs(ST, exist_ok=True)
data = C.load(); D = data["days"]; f = F.daily(data); B = F.connors(f)
HP = C.stop_pts(250.0)


def day_trade(bias, long_only=False):
    out = []
    for i, (d, a) in enumerate(D):
        s = int(bias[i])
        if s == 0 or f["rollskip"][i] or (long_only and s < 0) or np.isnan(a["open"][1]): continue
        p, xk, mae = C.walk(a, s, 1, HP, None, 390)
        out.append((d, s, 1, xk, p, mae))
    return pd.DataFrame(out, columns=["d", "side", "ek", "xk", "pnl", "mae"])


def hit(bias):
    """accuracy of the bias vs the day's RTH open->close direction"""
    r = {}
    for era, m in (("IS", f["d"] <= C.SPLIT), ("HO", f["d"] > C.SPLIT)):
        k = m & (bias != 0) & ~f["rollskip"]
        r[era] = dict(days=int(k.sum()), of=int(m.sum()), hit=float(100 * np.mean(np.sign(f["oc"][k]) == bias[k])) if k.any() else float("nan"))
    return r


def pick(rows, min_n=100):
    el = [r for r in rows if r["IS"]["n"] >= min_n and r["IS"]["net"] > 0]
    return max(el, key=lambda r: r["IS"]["pf"])["name"] if el else None


if __name__ == "__main__":
    res = {}
    base = pd.read_csv(ST + "/NOISE_250.csv", dtype={"d": str}); rb = C.row("NOISE_250 baseline", base)
    # ---------------- (i) day-direction bias
    rows = []; hits = {}; streams = {}
    for nm, b in B.items():
        hits[nm] = hit(b)
        for lo in (False, True):
            n2 = nm + (" - long only" if lo else " - both sides")
            t = day_trade(b, lo); streams[n2] = t; rows.append(C.row(n2, t))
    pk = pick(rows); res["bias"] = dict(rows=rows, hits=hits, pick=pk)
    if pk: streams[pk].to_csv(ST + "/C1_BIAS_PICK.csv", index=False)
    json.dump({k: v.tolist() for k, v in B.items()}, open(HERE + "/out/connors_bias.json", "w"))
    # ---------------- (ii) NOISE filter
    rows = []; fs = {}
    r2 = F.shift(f["rsi2"]); r2[0] = 50
    filt = {}
    for nm, b in B.items():
        filt[f"only WITH {nm}"] = (lambda b: lambda i, s, k: b[i] == s)(b)
        filt[f"not AGAINST {nm}"] = (lambda b: lambda i, s, k: b[i] != -s)(b)
    for thr in (90, 95):
        filt[f"no long after RSI2 > {thr} / no short after RSI2 < {100-thr} (overbought guard)"] = (lambda th: lambda i, s, k: not ((s > 0 and r2[i] > th) or (s < 0 and r2[i] < 100 - th)))(thr)
        filt[f"no short after RSI2 > {thr} / no long after RSI2 < {100-thr} (momentum guard)"] = (lambda th: lambda i, s, k: not ((s < 0 and r2[i] > th) or (s > 0 and r2[i] < 100 - th)))(thr)
    for nm, fn in filt.items():
        t = C.noise(D, allow=fn); fs[nm] = t; rows.append(C.row("NOISE " + nm, t))
    el = [r for r in rows if r["IS"]["pf"] >= rb["IS"]["pf"] and r["IS"]["net"] >= 0.9 * rb["IS"]["net"]]
    pk = max(el, key=lambda r: r["IS"]["pf"])["name"] if el else None
    res["filter"] = dict(rows=rows, pick=pk, eligible=[r["name"] for r in el])
    if pk: fs[pk[6:]].to_csv(ST + "/C1_FILTER_PICK.csv", index=False)
    # ---------------- (iii) intraday-only version
    rows = []; streams = {}
    for tf in (5, 15):
        bars = F.tfbars(D, tf); nbar = 390 // tf
        cc = np.concatenate([b["c"] for b in bars])
        m200, m5, r = F.sma(cc, 200), F.sma(cc, 5), F.rsi(cc, 2)
        s = pd.Series(cc); lo7 = (s <= s.rolling(7).min() + 1e-9).values; hi7 = (s >= s.rolling(7).max() - 1e-9).values
        cum = r + np.concatenate([[50], r[:-1]]); up = cc > m200; dn = cc < m200
        systems = {"RSI2<5, exit close > 5-bar avg": (up & (r < 5), cc > m5, dn & (r > 95), cc < m5),
                   "RSI2<10, exit close > 5-bar avg": (up & (r < 10), cc > m5, dn & (r > 90), cc < m5),
                   "CumRSI<35, exit RSI2 > 65": (up & (cum < 35), r > 65, dn & (cum > 165), r < 35),
                   "Double 7's (7-bar low -> 7-bar high)": (up & lo7, hi7, dn & hi7, lo7)}
        for (snm, (le, lx, se, sx)), stop_usd, lo in itertools.product(systems.items(), (250.0, 100.0), (False, True)):
            sp = C.stop_pts(stop_usd); out = []
            for i, (d, a) in enumerate(D):
                if f["rollskip"][i]: continue
                g = i * nbar; busy = -1; ntr = 0
                for j in range(nbar):
                    ek = tf * (j + 1)
                    if ek < 5 or ek > 360 or ek <= busy or ntr >= 3: continue
                    sd = 1 if le[g + j] else (-1 if (se[g + j] and not lo) else 0)
                    if not sd or np.isnan(a["open"][ek]): continue
                    xc = lx if sd > 0 else sx
                    p, xk, mae = C.walk(a, sd, ek, sp, None, 385, exit_fn=lambda k, xc=xc, g=g: (k + 1) % tf == 0 and xc[g + (k + 1) // tf - 1])
                    out.append((d, sd, ek, xk, p, mae)); busy = xk; ntr += 1
            t = pd.DataFrame(out, columns=["d", "side", "ek", "xk", "pnl", "mae"])
            nm = f"{tf}m {snm}, stop ${stop_usd:.0f}, {'long only' if lo else 'both sides'}"; streams[nm] = t; rows.append(C.row(nm, t))
    pk = pick(rows); res["intraday"] = dict(rows=rows, pick=pk)
    best_is = max(rows, key=lambda r: r["IS"]["pf"] if r["IS"]["n"] >= 100 else -1)["name"]
    streams[pk or best_is].to_csv(ST + "/C1_INTRADAY_PICK.csv", index=False); res["intraday"]["least_bad_is"] = best_is
    res["base"] = rb
    json.dump(res, open(HERE + "/out/c1.json", "w"), indent=1)
    for k in ("bias", "filter", "intraday"):
        print("==", k, "pick:", res[k]["pick"])
        for r in res[k]["rows"]: print(C.fmt(r))
    print(json.dumps(hits, indent=0))
