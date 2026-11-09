import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session10/five_year")
import types
_src=open("/home/user/opogabuuga/docs/results/session10/five_year/run_b.py").read().rsplit("\nmain()",1)[0]
B=types.ModuleType("B"); exec(compile(_src,"run_b","exec"),B.__dict__)
NA, sim25k = B.NA, B.sim25k
PV, TICK, FEE = 2.0, 0.25, 1.0
days = NA.load_days(B.CSV)
raw = pd.read_csv(B.CSV, parse_dates=["timestamp"]).set_index("timestamp"); raw.index = raw.index.tz_convert("America/New_York")
# ---- day features (past data only)
moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
rng = np.array([np.nanmax(a["high"]) - np.nanmin(a["low"]) for _, a in days])
F = {}
sigs = []
for i in range(14, len(days)):
    d, a = days[i]; pa = days[i-1][1]
    sig = np.nanmean(moves[i-14:i]); 
    past = np.array(sigs[-500:]) if len(sigs) >= 60 else None
    lowvol = bool(past is not None and sig <= np.quantile(past, 1/3))
    sigs.append(sig)
    day0 = pd.Timestamp(d, tz="America/New_York")
    on = raw[day0 - pd.Timedelta(hours=6): day0 + pd.Timedelta(hours=9, minutes=29, seconds=59)]
    onmove = (on.close.iloc[-1] - on.open.iloc[0]) if len(on) > 50 else np.nan
    onrng = (on.high.max() - on.low.min()) if len(on) > 50 else np.nan
    F[d] = dict(i=i, prior_dir=np.sign(pa["close"][389] - pa["open"][0]), onmove=onmove, onrng=onrng, lowvol=lowvol,
                gap=a["open"][0] / pa["close"][389] - 1, avgrng=np.mean(rng[i-14:i]), pdh=np.nanmax(pa["high"]), pdl=np.nanmin(pa["low"]),
                dow=pd.Timestamp(d).day_of_week)
ons = [(d, f["onrng"]) for d, f in F.items()]
for j, (d, v) in enumerate(ons):
    prev = [x for _, x in ons[max(0, j-14):j] if not np.isnan(x)]
    F[d]["onrng_ratio"] = v / np.mean(prev) if len(prev) >= 10 and not np.isnan(v) else np.nan

def noise(flt=None, hard_pts=124.0, maxtr=3, skip_k=()):
    out = []
    for i in range(14, len(days)):
        d, a = days[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i-1][1]["close"][389]
        if np.isnan(pc) or abs(o[0]/pc - 1) > 0.015: continue
        f = F[d]
        sig = np.nanmean(moves[i-14:i], axis=0)
        ub = max(o[0], pc)*(1+sig); lb = min(o[0], pc)*(1-sig)
        if flt and flt.get("day") and not flt["day"](f): continue
        st = dict(pos=0, entry=None, ek=None); ntr = pending = 0; hs = None; todays = []
        def close_trade(px, k):
            p = (px - st["entry"])*st["pos"]*PV - FEE; todays.append(p)
            out.append((d, st["pos"], p, st["ek"], k)); st["pos"] = 0
        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                st["entry"] = o[k] + pending*TICK; st["pos"], pending = pending, 0; st["ek"] = k
                hs = st["entry"] - st["pos"]*hard_pts
            pos = st["pos"]
            if pos and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                close_trade((min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos*TICK, k)
            if st["pos"] and k == 389: close_trade(c[k] - st["pos"]*TICK, k)
            if k in set(range(29, 360, 60)):
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k+1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos*TICK, nk if nk < 390 else k)
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        if k in skip_k: continue
                        if flt and flt.get("entry") and not flt["entry"](f, side, k, todays, ntr, o, c): continue
                        pending, ntr = side, ntr+1
    return pd.DataFrame(out, columns=["d", "side", "pnl", "ek", "xk"])

def walk_be(s, e, stop, tgt, H, L, O, C, j0, j1, be_pts):
    for j in range(j0, j1):
        if (s > 0 and L[j] <= stop) or (s < 0 and H[j] >= stop):
            px = (min(stop, O[j]) if s > 0 else max(stop, O[j])) - s*TICK
            return (px-e)*s*PV - FEE
        if (s > 0 and H[j] >= tgt) or (s < 0 and L[j] <= tgt):
            return (tgt-e)*s*PV - FEE
        if be_pts and ((s > 0 and H[j]-e >= be_pts) or (s < 0 and e-L[j] >= be_pts)):
            stop = e if (e-stop)*s > 0 else stop
    return (C[j1-1] - s*TICK - e)*s*PV - FEE

def fade(noise_days, flt=None, last_k=359, stop_pts=124.0, be_pts=None):
    out = []
    for d, a in days:
        if d < B.START or d > B.END or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        f = F.get(d)
        if f is None: continue
        for k in range(210, last_k):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k+1] - vw[:k+1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2*sd else (1 if c[k] < vw[k] - 2*sd else 0)
            if not s: continue
            e = o[k+1] + s*TICK
            if (vw[k]-e)*s < 4*TICK: break
            if flt:
                rs = np.nanmax(h[:k+1]) - np.nanmin(l[:k+1])
                ctx = dict(f=f, s=s, k=k, tgt_usd=(vw[k]-e)*s*PV, stop_usd=stop_pts*PV, rs=rs,
                           slope=abs(vw[k]-vw[k-30])/f["avgrng"], beyond=(c[k] > f["pdh"] if s < 0 else c[k] < f["pdl"]))
                if not flt(ctx): break
            p = walk_be(s, e, e - s*stop_pts, vw[k], h, l, o, c, k+1, 386, be_pts)
            out.append((d, p)); break
    return pd.DataFrame(out, columns=["d", "pnl"])

def build(nflt=None, nkw={}, fflt=None, fkw={}):
    nt = noise(nflt, **nkw); nt = nt[(nt.d >= B.START) & (nt.d <= B.END)]
    ft = fade(set(nt.d), fflt, **fkw)
    t = pd.concat([nt[["d", "pnl"]], ft]).sort_values("d", kind="stable").reset_index(drop=True)
    return t, nt, ft

def st(t):
    if not len(t): return dict(n=0, win=0, avg=0, tot=0, pf=0, dd=0)
    w = t.pnl > 0; gl = -t.pnl[~w].sum(); eq = t.pnl.cumsum()
    return dict(n=len(t), win=w.mean(), avg=t.pnl.mean(), tot=t.pnl.sum(), pf=t.pnl[w].sum()/gl if gl else 9, dd=(eq-eq.cummax()).min())
H1 = ("2021-11-01", "2023-12-31"); H2 = ("2024-01-01", "2026-10-30")
def half(t, h): return st(t[(t.d >= h[0]) & (t.d <= h[1])])
def lossyears(t):
    y = t.groupby(pd.to_datetime(t.d).dt.year).pnl.sum(); return ",".join(str(k) for k, v in y.items() if v < 0) or "-"

if __name__ == "__main__":
    base, bn, bf = build()
    print("BASE", len(base), base.pnl.sum(), (base.pnl > 0).mean(), len(bn), len(bf))
    # verify vs reference
    ref_n = B.noise_t(days, hard=type("P", (), {"__bool__": lambda s: True, "__rmul__": lambda s, pos: type("Q", (), {"__mul__": lambda q, e: pos*124.0})()})())
    print("ref noise", len(ref_n[(ref_n.d >= B.START)&(ref_n.d <= B.END)]), ref_n[(ref_n.d >= B.START)&(ref_n.d <= B.END)].pnl.sum())
    base.to_csv("base.csv", index=False)
