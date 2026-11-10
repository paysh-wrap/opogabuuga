"""Round 2: refinements of the round-1 near-misses + NOISE confirmation + two new pre-10:00 setups (flat before NOISE can enter).
PASS = (win% up on BOTH halves OR $ up on BOTH halves) AND maxDD not worse AND worst day not worse, on BOTH halves."""
import pickle, sys, json
import numpy as np, pandas as pd
import winrate_study as W
from winrate_study import PV, TICK, FEE, PTS, START, END, hm
_c = W.HERE + "/days.pkl"
days = pickle.load(open(_c, "rb")) if __import__("os").path.exists(_c) else W.NG.load_days(W.MNQ)[0]

def verdict(a, b, A, B):
    up = lambda k: a[k] > A[k] + 1e-9 and b[k] > B[k] + 1e-9
    safe = all(x["dd"] <= X["dd"] + 0.01 and x["wd"] >= X["wd"] - 0.01 for x, X in ((a, A), (b, B)))
    return ("PASS" if (up("win") or up("usd")) and safe else "fail"), up("win"), up("usd"), safe

def gap_fade(g1, g2, frac, stop=PTS):
    """|gap| in [g1,g2): after the first closed 1-min bar, fade toward prior close; target = entry side of pc by frac of the gap; flat 9:58 close."""
    out = []
    for i in range(1, len(days)):
        d, a = days[i]
        if d < START or d > END: continue
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]; pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or np.isnan(o[0]) or np.isnan(o[1]): continue
        g = o[0] / pc - 1
        if not (g1 <= abs(g) < g2): continue
        s = -1 if g > 0 else 1; e = o[1] + s * TICK; tgt = o[0] + (pc - o[0]) * frac
        if (tgt - e) * s < 4 * TICK: continue
        p, _ = W.walk(s, e, e - s * stop, tgt, h, l, o, c, 1, 29)
        out.append((d, p, "GAPFADE", hm(1)))
    return out

def displacement(mult, body=0.7, stop=25.0, tgt=38.0, last_sig=20, flat=29):
    """5-min candle (closed) in the first minutes: range >= mult x mean range of the 12 previous 5-min candles of the PRIOR session's last hour,
    body >= `body` of range -> enter with it at next 1-min open, stop 25 pt / target 38 pt, flat at bar `flat`. One per day."""
    out = []
    for i in range(1, len(days)):
        d, a = days[i]
        if d < START or d > END: continue
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]; p = days[i - 1][1]
        ref = np.nanmean([np.nanmax(p["high"][j:j + 5]) - np.nanmin(p["low"][j:j + 5]) for j in range(330, 390, 5)])
        for k in range(0, last_sig, 5):
            if np.isnan(c[k:k + 6]).any(): continue
            hi, lo = h[k:k + 5].max(), l[k:k + 5].min(); rng = hi - lo; bd = c[k + 4] - o[k]
            if rng < mult * ref or abs(bd) < body * rng: continue
            s = 1 if bd > 0 else -1; e = o[k + 5] + s * TICK
            pnl, _ = W.walk(s, e, e - s * stop, e + s * tgt, h, l, o, c, k + 5, flat)
            out.append((d, pnl, "DISP", hm(k + 5))); break
    return out

def df(rows): return pd.DataFrame(rows, columns=["date", "pnl", "strategy", "entry_time"])
def comb(*ts): return pd.concat(ts).sort_values(["date", "entry_time"]).reset_index(drop=True)

if __name__ == "__main__":
    base = W.build(days); A, B = W.halves(base); res = {}; T = {}
    def add(name, t, standalone=None):
        a, b = W.halves(t); v = verdict(a, b, A, B); res[name] = (a, b, v); T[name] = t
        f = lambda s: f"{s['n']:4d} {s['win']:5.1f}% PF{s['pf']:.2f} ${s['usd']:7.0f} DD{s['dd']:5.0f} wd{s['wd']:5.0f}"
        print(f"{name:26s} | {f(a)} | {f(b)} | {v[0]}" + (f" | alone {standalone}" if standalone else ""), flush=True)
    add("BASE", base)
    for be in (50, 60, 70, 80, 100):
        for lock in (5, 10, 20):
            add(f"N_LOCK{be}+{lock}", W.build(days, {"be": be, "lock": lock}))
            add(f"N_LOCK{be}+{lock}_nore", W.build(days, {"be": be, "lock": lock, "norefire": True}))
    for cf in (3, 5, 10): add(f"N_CONF{cf}", W.build(days, {"confirm": cf}))
    add("N_STEP30", W.build(days, {"step": 30}))
    for k0 in (150, 165, 180, 195): add(f"F_START{hm(k0)}", W.build(days, {}, {"k0": k0}))
    add("F_AFTER_IFWIN", W.build(days, {}, {"after_noise": True}, after_if="win"))
    add("F_AFTER_IFWIN+12:30", W.build(days, {}, {"after_noise": True, "k0": 180}, after_if="win"))
    add("F_HALF+AFTER_IFWIN", W.build(days, {}, {"after_noise": True, "half": True}, after_if="win"))
    for g1, g2 in ((0.002, 0.015), (0.003, 0.015), (0.005, 0.015), (0.002, 0.005)):
        for fr in (0.5, 1.0):
            g = df(gap_fade(g1, g2, fr)); sa = W.halves(g)
            add(f"GAP{g1*100:.1f}-{g2*100:.1f}%_t{fr}", comb(base, g), f"{sa[0]['n']} {sa[0]['win']:.0f}% ${sa[0]['usd']:.0f} / {sa[1]['n']} {sa[1]['win']:.0f}% ${sa[1]['usd']:.0f}")
    for m in (1.0, 1.5, 2.0, 3.0):
        g = df(displacement(m)); sa = W.halves(g)
        add(f"DISP_x{m}", comb(base, g), f"{sa[0]['n']} {sa[0]['win']:.0f}% ${sa[0]['usd']:.0f} / {sa[1]['n']} {sa[1]['win']:.0f}% ${sa[1]['usd']:.0f}")
    g = df(displacement(1.5, last_sig=85, flat=120)); sa = W.halves(g)
    print("DISP 90-min standalone (overlaps NOISE, info only):", {k: round(v, 1) for k, v in sa[0].items()}, {k: round(v, 1) for k, v in sa[1].items()})
    pickle.dump((res, T), open(W.HERE + "/round2.pkl", "wb"))
