"""(a) Late-day momentum on MNQ (docs/results/new_edge rules) + MES + MGC, and overnight + first-30-min -> last-30-min."""
import json, sys
import numpy as np
from lib import *

OUT = {}
def day_frames(df):
    """per ET date: positional index helpers"""
    d = {}
    for i, ts in enumerate(df.index):
        d.setdefault(ts.date(), []).append(i)
    return d

def run(sym, stop_pts, min_mult=0.1):
    df = load(sym); days = day_frames(df); keys = sorted(days)
    pu, cu = pt_usd(sym), cost_usd(sym)
    ranges, prev_close = [], None
    rows = []
    for d in keys:
        idx = days[d]; ts = df.index[idx]
        rth = [i for i in idx if time(9, 30) <= df.index[i].time() < time(16, 0)]
        if len(rth) < 180:
            prev_close = prev_close; continue
        o = df.o.values[rth[0]]
        i_ref = next((i for i in rth if df.index[i].time() == time(13, 28)), None)    # bar closing 13:30
        i_ent = next((i for i in rth if df.index[i].time() == time(15, 0)), None)      # enters at its OPEN (no lookahead)
        i_30 = next((i for i in rth if df.index[i].time() == time(15, 30)), None)
        i_f30 = next((i for i in rth if df.index[i].time() == time(9, 58)), None)     # bar closing 10:00
        i_end = rth[-1]                                                                # bar closing 16:00
        if None in (i_ref, i_ent, i_30, i_f30): continue
        glob_o = df.o.values[idx[0]] if df.index[idx[0]].time() < time(9, 30) else None
        ref = df.c.values[i_ref]
        rng = [r for r in ranges[-14:]]
        thr = (np.mean(rng) * min_mult) if len(rng) >= 5 else None
        r_on = (o / prev_close - 1) if prev_close else None
        r_f30 = df.c.values[i_f30] / o - 1
        # since Globex reopen 18:00 prior day: use first bar at/after 18:00 of the previous calendar date in df
        rows.append(dict(day=d, o=o, ref=ref, thr=thr, r_on=r_on, r_f30=r_f30, i_ent=i_ent, i_30=i_30, i_end=i_end,
                         r_last30=df.c.values[i_end] / df.o.values[i_30] - 1, r_trend=ref / o - 1,
                         i_rth0=rth[0]))
        ranges.append(df.h.values[rth].max() - df.l.values[rth].min())
        prev_close = df.c.values[i_end]
    res = {}
    def trade(rr, sgn, stop, i0, i1, entry):
        pts, ex = sim_path(df, i0, i1, entry, sgn, stop)
        return dict(day=str(rr["day"]), sign=sgn, i0=i0, i1=i1, entry=entry, stop_pts=stop, usd=pts * pu - cu)
    variants = {
        "A_trend_0930-1330": lambda r: (np.sign(r["r_trend"]) if (r["thr"] is None or abs(r["ref"] - r["o"]) >= r["thr"]) else 0),
        "A0_trend_nofilter": lambda r: np.sign(r["r_trend"]),
        "C_overnight_sign": lambda r: np.sign(r["r_on"]) if r["r_on"] is not None else 0,
        "D_trend_and_overnight_agree": lambda r: (np.sign(r["r_trend"]) if r["r_on"] is not None and np.sign(r["r_on"]) == np.sign(r["r_trend"]) else 0),
        "E_trend_plus_overnight": lambda r: np.sign(r["r_trend"] + (r["r_on"] or 0)),
    }
    for name, fn in variants.items():
        tr = []
        for r in rows:
            s = fn(r)
            if s == 0: continue
            tr.append(trade(r, int(s), stop_pts, r["i_ent"], r["i_end"], df.o.values[r["i_ent"]]))
        res[name] = dict(**stats([t["usd"] for t in tr]), **(random_baseline(tr, sym, df) if tr else {}))
    # last 30 minutes (15:30 open -> 16:00 close), no stop (very wide), sign of first-30-min [+ overnight]
    for name, fn in {
        "F_first30_to_last30": lambda r: np.sign(r["r_f30"]),
        "G_overnight+first30_to_last30": lambda r: np.sign(r["r_f30"] + (r["r_on"] or 0)) if r["r_on"] is not None else 0,
        "H_overnight_to_last30": lambda r: np.sign(r["r_on"]) if r["r_on"] is not None else 0,
    }.items():
        tr = []
        for r in rows:
            s = fn(r)
            if s == 0: continue
            tr.append(trade(r, int(s), 1e9, r["i_30"], r["i_end"], df.o.values[r["i_30"]]))
        res[name] = dict(**stats([t["usd"] for t in tr]), **(random_baseline(tr, sym, df) if tr else {}))
    # plain predictor stats (no costs): correlation of last-30 return with first-30 / overnight / sum
    ok = [r for r in rows if r["r_on"] is not None]
    if len(ok) > 5:
        y = np.array([r["r_last30"] for r in ok]); f = np.array([r["r_f30"] for r in ok]); on = np.array([r["r_on"] for r in ok])
        res["corr_last30_vs"] = dict(n=len(ok), first30=round(float(np.corrcoef(y, f)[0, 1]), 2), overnight=round(float(np.corrcoef(y, on)[0, 1]), 2),
                                    sum=round(float(np.corrcoef(y, f + on)[0, 1]), 2),
                                    sign_hit_sum=round(float(np.mean(np.sign(y) == np.sign(f + on))), 2))
    res["n_sessions"] = len(rows)
    return res

for sym, stop in (("MNQ", 60), ("MES", 16), ("MGC", 8)):
    OUT[sym] = dict(stop_pts=stop, **run(sym, stop))
    print(sym, "stop", stop, "sessions", OUT[sym]["n_sessions"])
    for k, v in OUT[sym].items():
        if k not in ("stop_pts", "n_sessions"): print("  ", k, v)
json.dump(OUT, open(Path(__file__).resolve().parent.parent / "late_day_results.json", "w"), indent=1, default=str)
