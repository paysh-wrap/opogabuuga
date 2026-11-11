"""C2 - 'The Candlestick Trading Bible' rules intraday on MNQ: pin bar / engulfing bar / inside bar, WITH the trend, AT a level.
Published rules used (generic, from the book's text): trade only in the direction of the trend (8/21 EMA), take the pattern at a level
(21 EMA pullback or support/resistance), enter on the break of the pattern bar (inside bar: break of the mother bar), stop on the other
side of the pattern, target a fixed reward:risk. Everything flat by 15:55 ET. writes out/c2.json + stream of the IS pick."""
import os, json, itertools
import numpy as np, pandas as pd
import core as C, feats as F
HERE = os.path.dirname(os.path.abspath(__file__)); ST = HERE + "/out/streams"; os.makedirs(ST, exist_ok=True)
data = C.load(); D = data["days"]; f = F.daily(data)
MIN_RISK, MAX_RISK = 10.0, C.stop_pts(250.0)     # points: below 10 pt costs are > 10% of the risk; above = more than the $250 NOISE stop
PATS = ("pin", "engulf", "inside", "all"); LEVELS = ("none", "ema21", "sr", "any"); RRS = (1.5, 2.0, 3.0)


def signals(tf):
    """per TF: list over days of [(j, side, pattern, hi, lo, at_ema, at_sr)]"""
    bars = F.tfbars(D, tf); nbar = 390 // tf
    o = np.concatenate([b["o"] for b in bars]); h = np.concatenate([b["h"] for b in bars]); l = np.concatenate([b["l"] for b in bars])
    c = np.concatenate([b["c"] for b in bars]); vw = np.concatenate([b["vw"] for b in bars])
    e8, e21 = F.ema(c, 8), F.ema(c, 21)
    pc = np.concatenate([[c[0]], c[:-1]]); tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().values
    rng = h - l; body_hi = np.maximum(o, c); body_lo = np.minimum(o, c)
    po, ph, pl, pcl = (np.concatenate([[x[0]], x[:-1]]) for x in (o, h, l, c))
    with np.errstate(divide="ignore", invalid="ignore"):
        pin_b = (rng > 0) & ((body_lo - l) >= 2 / 3 * rng); pin_s = (rng > 0) & ((h - body_hi) >= 2 / 3 * rng)
    eng_b = (pcl < po) & (c > o) & (c >= po) & (o <= pcl) & (rng >= (ph - pl)); eng_s = (pcl > po) & (c < o) & (c <= po) & (o >= pcl) & (rng >= (ph - pl))
    ins = (h <= ph) & (l >= pl) & (rng > 0)
    up = (e8 > e21) & (c > e21); dn = (e8 < e21) & (c < e21)
    out = []
    for i in range(len(D)):
        g = i * nbar; lst = []
        if i == 0 or f["rollskip"][i]: out.append(lst); continue
        lv = [f["h"][i - 1], f["l"][i - 1], f["c"][i - 1], f["o"][i]]          # prior-day high / low / close (adjusted), today's open
        for j in range(1, nbar):
            k = g + j
            if np.isnan(atr[k]): continue
            for side, trend, pin, eng in ((1, up[k], pin_b[k], eng_b[k]), (-1, dn[k], pin_s[k], eng_s[k])):
                if not trend: continue
                pats = []
                if pin: pats.append(("pin", h[k], l[k]))
                if eng: pats.append(("engulf", h[k], l[k]))
                if ins[k]: pats.append(("inside", ph[k], pl[k]))              # mother bar range
                for pn, hi, lo in pats:
                    tol = 0.1 * atr[k]
                    def at(level):   # the bar's tail reaches the level and the close is back on the trend side
                        return (lo <= level + tol and c[k] > level) if side > 0 else (hi >= level - tol and c[k] < level)
                    lst.append((j, side, pn, hi, lo, bool(at(e21[k])), bool(any(at(x) for x in lv + [vw[k]]))))
        out.append(lst)
    return out


def run(sig, tf, pat, level, rr, bias=None, maxtr=2):
    res = []
    for i, (d, a) in enumerate(D):
        busy = -1; ntr = 0
        o, h, l = a["open"], a["high"], a["low"]; off = a["off"]
        for j, side, pn, hi, lo, at_e, at_s in sig[i]:
            m = tf * (j + 1)
            if m < 15 or m > 330 or m <= busy or ntr >= maxtr: continue
            if pat != "all" and pn != pat: continue
            if (level == "ema21" and not at_e) or (level == "sr" and not at_s) or (level == "any" and not (at_e or at_s)): continue
            if bias is not None and bias[i] != side: continue
            trig = (hi + C.TICK if side > 0 else lo - C.TICK) - off; stp = (lo - C.TICK if side > 0 else hi + C.TICK) - off     # raw prices
            risk = abs(trig - stp)
            if risk < MIN_RISK or risk > MAX_RISK: continue
            ek = None
            for k in range(m, min(m + 2 * tf, 385)):                      # stop order valid for the next 2 bars
                if np.isnan(o[k]): continue
                if (side > 0 and l[k] <= stp and h[k] < trig) or (side < 0 and h[k] >= stp and l[k] > trig): break   # pattern failed first
                if (side > 0 and h[k] >= trig) or (side < 0 and l[k] <= trig): ek = k; break
            if ek is None: continue
            p, xk, mae = C.walk(a, side, ek, risk, rr * risk, 385, entry_px=trig)
            res.append((d, side, ek, xk, p, mae)); busy = xk; ntr += 1
    return pd.DataFrame(res, columns=["d", "side", "ek", "xk", "pnl", "mae"])


def name(tf, pat, level, rr):
    return f"{tf}m {pat} / level {level} / {rr:g}R"


if __name__ == "__main__":
    rows = []; streams = {}
    for tf in (5, 15):
        sg = signals(tf)
        for pat, level, rr in itertools.product(PATS, LEVELS, RRS):
            t = run(sg, tf, pat, level, rr); nm = name(tf, pat, level, rr); streams[nm] = t; rows.append(C.row(nm, t))
    el = [r for r in rows if r["IS"]["n"] >= 150 and r["IS"]["net"] > 0]
    pk = max(el, key=lambda r: r["IS"]["pf"])["name"] if el else None
    lb = max([r for r in rows if r["IS"]["n"] >= 150], key=lambda r: r["IS"]["pf"])["name"]
    streams[pk or lb].to_csv(ST + "/C2_CANDLE_PICK.csv", index=False)
    summ = dict(n=len(rows), is_pos=sum(r["IS"]["net"] > 0 for r in rows), ho_pos=sum(r["HO"]["net"] > 0 for r in rows),
                both_pos=sum(r["IS"]["net"] > 0 and r["HO"]["net"] > 0 for r in rows),
                is_pf115=sum(r["IS"]["pf"] >= 1.15 and r["IS"]["n"] >= 150 for r in rows), ho_pf115=sum(r["HO"]["pf"] >= 1.15 and r["HO"]["n"] >= 100 for r in rows))
    json.dump(dict(rows=rows, pick=pk, least_bad_is=lb, summary=summ), open(HERE + "/out/c2.json", "w"), indent=1)
    print("pick", pk, "| least bad IS", lb, summ)
    for r in sorted(rows, key=lambda r: -r["IS"]["pf"])[:25]: print(C.fmt(r))
