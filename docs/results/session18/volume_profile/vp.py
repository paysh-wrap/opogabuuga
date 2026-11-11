"""Session 18 volume-profile study (SOURCE_RULES.md). MKT=MNQ|MGC python3 -I vp.py. Reuses rsi_dmi/lib.py loader + run_trade sim."""
import sys, os, json, random
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/rsi_dmi")
import numpy as np, pandas as pd
import lib
from lib import *
OUTD = "/home/user/opogabuuga/docs/results/session18/volume_profile/out"
S.RANGES["ALL"] = (START, END)
if MKT == "MNQ": PS, PE, BIN, TKFIX = 570, 960, 1.0, 30.0       # RTH 09:30-16:00
else:             PS, PE, BIN, TKFIX = 500, 810, 0.5, 5.0       # COMEX RTH 08:20-13:30 ET
EXPECT = PE - PS
# 15m ATR(14) known at the open
b15 = df.resample("15min", label="right", closed="right").agg(dict(high="max", low="min", close="last")).dropna()
pc = b15.close.shift(); trr = np.maximum(b15.high - b15.low, np.maximum((b15.high - pc).abs(), (b15.low - pc).abs()))
atr15 = trr.rolling(14).mean()

if MKT == "MNQ": VOL = df.volume.values.astype(float)
else:
    vv = pd.concat([pd.read_csv(SP + f"split_raw/MGC_{y}.csv", usecols=["ts_event", "volume"]) for y in (2025, 2026)])
    vv.index = pd.to_datetime(vv.ts_event, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    vv = vv.volume[~vv.index.duplicated()]; VOL = vv.reindex(df.index).fillna(0).values.astype(float)
dates = sorted(set(DATE)); idx = {}
for d in dates:
    ii = np.nonzero((DATE == d) & (MOD >= PS) & (MOD < PE))[0]
    if len(ii) >= 0.7 * EXPECT: idx[d] = ii
def profile(ii):
    px = np.round(C[ii] / BIN) * BIN; v = VOL[ii]
    s = pd.Series(v, index=px).groupby(level=0).sum().sort_index()
    p = s.index.values; vv = s.values; k = int(np.argmax(vv)); lo = hi = k; tot = vv.sum(); acc = vv[k]
    while acc < 0.7 * tot and (lo > 0 or hi < len(vv) - 1):
        a = vv[lo - 1] + (vv[lo - 2] if lo > 1 else 0) if lo > 0 else -1
        b = vv[hi + 1] + (vv[hi + 2] if hi < len(vv) - 2 else 0) if hi < len(vv) - 1 else -1
        if a >= b: acc += vv[lo - 1] + (vv[lo - 2] if lo > 1 else 0); lo = max(lo - 2, 0)
        else: acc += vv[hi + 1] + (vv[hi + 2] if hi < len(vv) - 2 else 0); hi = min(hi + 2, len(vv) - 1)
    return p[k], p[hi], p[lo]

PROF = {}; ds = sorted(idx)
for a, d in zip(ds[:-1], ds[1:]):
    ii = idx[a]; PROF[d] = dict(zip(("poc", "vah", "val"), profile(ii)), pdh=H[ii].max(), pdl=L[ii].min())
def first_touch(j0, j1, lvl, side):   # first bar in [j0,j1) whose low<=lvl (side=1, buy dips) or high>=lvl (side=-1)
    seg = (L[j0:j1] <= lvl) if side == 1 else (H[j0:j1] >= lvl)
    k = np.nonzero(seg)[0]; return j0 + k[0] if len(k) else None
SKIP = 5; LASTENT = PE - 60 if MKT == "MNQ" else PE - 30
EVENTS = []   # one per candidate: dict(d, var, side, j, level, poc, opp, pdx, atr)
ST80 = []
for d in ds:
    if d not in PROF: continue
    ii = idx[d]; p = PROF[d]; i0 = ii[0]; op = O[i0]; j1 = ii[0] + (LASTENT - PS); j1 = min(j1, ii[-1]); jend = ii[-1] + 1
    t = C[:0]
    k = np.searchsorted(b15.index.values, np.datetime64(df.index[i0]), side="right") - 1
    atr = float(atr15.values[k]) if k >= 0 and not np.isnan(atr15.values[k]) else np.nan
    pe = np.nonzero((DATE == d) & (MOD >= PE))[0]; exit_i = int(pe[0]) if len(pe) else None
    base = dict(d=d, atr=atr, exit_i=exit_i, poc=p["poc"], vah=p["vah"], val=p["val"], pdh=p["pdh"], pdl=p["pdl"], px=op)
    js = i0 + SKIP
    if op > p["vah"]:
        j = first_touch(i0, j1, p["vah"], 1)
        if j is not None and j >= js: EVENTS.append(dict(base, var="V1", side=1, j=j, level=p["vah"], struct=p["pdh"], opp=p["pdh"]))
    elif op < p["val"]:
        j = first_touch(i0, j1, p["val"], -1)
        if j is not None and j >= js: EVENTS.append(dict(base, var="V2", side=-1, j=j, level=p["val"], struct=p["pdl"], opp=p["pdl"]))
    else:
        jl = first_touch(i0, j1, p["val"], 1); jh = first_touch(i0, j1, p["vah"], -1)
        if jl is not None and jl >= js: EVENTS.append(dict(base, var="V3", side=1, j=jl, level=p["val"], struct=p["poc"], opp=p["vah"]))
        if jh is not None and jh >= js: EVENTS.append(dict(base, var="V3", side=-1, j=jh, level=p["vah"], struct=p["poc"], opp=p["val"]))
        # 80% rule stat: first edge touched (>= SKIP min) then does price reach the opposite edge before RTH end
        c = [(j, s2, lv, op2) for j, s2, lv, op2 in ((jl, 1, p["val"], p["vah"]), (jh, -1, p["vah"], p["val"])) if j is not None and j >= js]
        if c:
            j, s2, lv, opp = min(c, key=lambda x: x[0]); k2 = first_touch(j + 1, ii[-1] + 1, opp, -s2)
            # also "accepted" version: a 30m-style acceptance = the touch bar's close back inside VA
            ST80.append(dict(d=d, d1=j, side=s2, hit=k2 is not None, acc=bool(p["val"] < C[j] < p["vah"]), mins=int(k2 - j) if k2 is not None else -1))
EVENTS = sorted(EVENTS, key=lambda e: e["j"])
print(MKT, "events", {v: sum(e["var"] == v for e in EVENTS) for v in ("V1", "V2", "V3")}, "days", len(PROF), flush=True)

def stopdist(e, kind):
    px = e["level"]
    if kind == "pct8": r = 8.0 / 6000.0 * px
    elif kind == "atr": r = 1.5 * e["atr"]
    else: r = TKFIX
    r = max(MINPT, min(MAXPT, r)) if r == r else None
    return None if r is None else round(r / TICK) * TICK
def build(evs, stopk, tgtk, rnd=None):
    rr = random.Random(rnd) if rnd is not None else None; out = []; busy = -1
    for e in evs:
        if e["j"] <= busy: continue
        dist = stopdist(e, stopk)
        if not dist: continue
        side = rr.choice((1, -1)) if rr else e["side"]; lv = e["level"]
        if rr and not (L[e["j"]] <= lv <= H[e["j"]]): continue   # random side must actually trade at the level
        stop = lv - side * dist
        if tgtk in ("1.5", "2.0"): tgt = lv + side * float(tgtk) * dist
        else:
            x = e["struct"] if tgtk == "STRUCT" else e["opp"]
            if rr is None and (e["side"] * (x - lv) < 4 * TICK) : x = lv + e["side"] * 2.0 * dist if e["var"] != "V3" else None
            if x is None: continue
            tgt = x if rr is None else lv + side * abs(x - lv)
        if rr is None and e["var"] != "V3" and tgtk in ("STRUCT", "OPP") and e["side"] * (tgt - lv) < 0.75 * dist: tgt = lv + e["side"] * 2.0 * dist  # trend: PDH too close -> 2R
        t = run_trade(e["j"], side, stop, tgt, e["exit_i"], min(lv, O[e["j"]]) if side == 1 else max(lv, O[e["j"]]))
        if t: out.append(t); busy = t["xi"]
    return pd.DataFrame(out, columns=["d", "ei", "xi", "side", "pnl", "mae", "risk"])
def st(t, era, boot=False):
    s, e = S.RANGES[era]; x = t[(t.d >= s) & (t.d <= e)]
    if len(x) == 0: return dict(n=0)
    p = x.pnl.values; eq = np.cumsum(p); dd = float(np.max(np.maximum.accumulate(np.r_[0, eq])[1:] - eq))
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    r = dict(n=len(p), win=round(100 * (p > 0).mean(), 1), pf=round(gp / gl, 2) if gl else 99, avg=round(p.mean(), 2), net=round(p.sum()), dd=round(dd))
    if era in ("HO", "ALL"):
        ev = S.eval_roll(x, era); r.update(passp=round(ev["pass_"], 1), bust=round(ev["bust"], 1), med=ev["med"])
    return r
VARS = {"V1 above-VAH buy": ["V1"], "V2 below-VAL sell": ["V2"], "V1+V2 trend-only": ["V1", "V2"], "V3 inside fade": ["V3"], "V5 combined": ["V1", "V2", "V3"]}
TGT = ["1.5", "2.0", "STRUCT", "OPP"]
res = {}
for vn, vs in VARS.items():
    evs = [e for e in EVENTS if e["var"] in vs]
    for sk in ("pct8", "atr", "tick"):
        for tk in TGT:
            if tk == "OPP" and "V3" not in vs: continue
            t = build(evs, sk, tk); name = f"{vn} / stop={sk} / tgt={tk}"
            rb = [st(build(evs, sk, tk, rnd=s), "HO") for s in range(15)] if len(t) > 20 else []
            rd = dict(IS=st(t, "IS"), HO=st(t, "HO"), ALL=st(t, "ALL"),
                      rand=dict(pf=round(float(np.mean([a.get("pf", 0) for a in rb])), 2), avg=round(float(np.mean([a.get("avg", 0) for a in rb])), 2), win=round(float(np.mean([a.get("win", 0) for a in rb])), 1)) if rb else None)
            res[name] = rd; t.to_csv(f"{OUTD}/stream_{MKT}_" + "".join(c if c.isalnum() else "_" for c in name) + ".csv", index=False)
d80 = pd.DataFrame(ST80)
def sm(x): return dict(days=len(x), hit=round(100 * x.hit.mean(), 1) if len(x) else None, med_min=float(x[x.hit].mins.median()) if x.hit.any() else None)
res["_80rule"] = dict(all=sm(d80), IS=sm(d80[d80.d <= SPLIT]), HO=sm(d80[d80.d > SPLIT]), long_from_VAL=sm(d80[d80.side == 1]), short_from_VAH=sm(d80[d80.side == -1]), accepted_close_inside=sm(d80[d80.acc]))
res["_events"] = {v: sum(e["var"] == v for e in EVENTS) for v in ("V1", "V2", "V3")}; res["_days"] = len(PROF)
if MKT == "MNQ":
    base = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE__lock_.csv")
    res["_noiseC"] = dict(IS=st(base, "IS"), HO=st(base, "HO"), ALL=st(base, "ALL"))
json.dump(res, open(f"{OUTD}/results_{MKT}.json", "w"), indent=1, default=str)
print("done", len(res))
