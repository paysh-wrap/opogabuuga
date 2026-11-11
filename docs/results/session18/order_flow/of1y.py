"""1-year ESTIMATED order-flow study, MNQ.v.0 1m (cached Databento csv, no downloads). Pick 2025-11-06..2026-07-03, judge 2026-07-06..2026-11-05.
Order flow is ESTIMATED from OHLCV: signed vol = CLV*V (tick rule when H==L). Costs as session 17: $1 fee, 1 tick slip on entry and every exit."""
import sys, json, random, itertools
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session17/noise_sharpen")
import sim
CSV = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/mnq_2019_2026.csv"
PV, TICK, FEE = 2.0, 0.25, 1.0
S0, PE, J0, E = "2025-11-06", "2026-07-03", "2026-07-06", "2026-11-05"
sim.RANGES.update(PICK=(S0, PE), JUDGE=(J0, E), YEAR=(S0, E))
df = pd.read_csv(CSV); df["t"] = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York")
df = df[(df.t >= "2025-11-05") & (df.t <= "2026-11-06")]
df = df[(df.t.dt.time >= pd.Timestamp("09:30").time()) & (df.t.dt.time < pd.Timestamp("16:00").time())].copy()
df["d"] = df.t.dt.strftime("%Y-%m-%d")
rng = (df.high - df.low).values; clv = np.where(rng > 0, ((df.close - df.low) - (df.high - df.close)).values / np.where(rng > 0, rng, 1), np.nan)
tr = np.sign(df.close.diff().fillna(0).values)
df["sv"] = np.where(np.isnan(clv), tr, clv) * df.volume.values
days = {d: g.reset_index(drop=True) for d, g in df.groupby("d")}
dl = sorted(days)

def bars5(g):
    k = (g.t.dt.hour * 60 + g.t.dt.minute - 570) // 5; g = g.assign(k=k)
    b = g.groupby("k").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"), v=("volume", "sum"), dlt=("sv", "sum"), i1=("open", lambda s: s.index[-1]))
    b = b.reset_index(); b["i1"] = b.i1.astype(int); return b

def signals(d, prev, P):
    g = days[d]; b = bars5(g); out = []
    pdh, pdl = (days[prev].high.max(), days[prev].low.min()) if prev else (np.nan, np.nan)
    ad = b.dlt.abs().rolling(20, min_periods=6).mean().shift(1); av = b.v.rolling(20, min_periods=6).mean().shift(1)
    cd = b.dlt.cumsum(); K, N = P["k"], 12
    for j in range(6, len(b) - 1):
        if b.k[j] > 71: break  # no entries after 15:30
        r = b.iloc[j]; sh, sl = b.h[:j].max(), b.l[:j].min()
        # session profile from 1m closes so far -> POC
        gg = g.iloc[:int(r.i1) + 1]; vp = gg.groupby((gg.close / 2).round() * 2).volume.sum(); poc = vp.idxmax()
        def add(name, side, stop):
            if side * (r.c - stop) > 2 * TICK: out.append((name, j, side, stop))
        levlo = [x for x in (sl, pdl) if not np.isnan(x)]; levhi = [x for x in (sh, pdh) if not np.isnan(x)]
        heavy = abs(r.dlt) > K * ad[j]
        # 1 absorption: tests level, heavy opposing delta, holds (close back beyond level, upper/lower half)
        for L in levlo:
            if r.l <= L + TICK and r.dlt < 0 and heavy and r.c > L and r.c > (r.h + r.l) / 2: add("ABS", 1, min(r.l, L) - TICK); break
        for L in levhi:
            if r.h >= L - TICK and r.dlt > 0 and heavy and r.c < L and r.c < (r.h + r.l) / 2: add("ABS", -1, max(r.h, L) + TICK); break
        # 2 delta divergence at new N-bar extreme
        lo0 = b.l[j - N:j]; hi0 = b.h[j - N:j]
        if r.l < lo0.min():
            jp = lo0.idxmin()
            if cd[j] > cd[jp] and r.dlt > 0: add("DIV", 1, r.l - TICK)
        if r.h > hi0.max():
            jp = hi0.idxmax()
            if cd[j] < cd[jp] and r.dlt < 0: add("DIV", -1, r.h + TICK)
        # 3 sweep + volume spike + reclaim
        spike = r.v > P["m"] * av[j]
        for L in levlo:
            if spike and r.l < L - TICK and r.c > L: add("SWEEP", 1, r.l - TICK); break
        for L in levhi:
            if spike and r.h > L + TICK and r.c < L: add("SWEEP", -1, r.h + TICK); break
        # 4 POC rejection
        if r.l <= poc <= r.o and r.c > poc and r.dlt > 0 and heavy: add("POC", 1, min(r.l, poc) - TICK)
        if r.h >= poc >= r.o and r.c < poc and r.dlt < 0 and heavy: add("POC", -1, max(r.h, poc) + TICK)
        # 5 stacked same-sign heavy delta (imbalance proxy)
        w = b.dlt[j - 2:j + 1]; aw = ad[j - 2:j + 1]
        if (w > K * aw).all(): add("STACK", 1, b.l[j - 2:j + 1].min() - TICK)
        if (w < -K * aw).all(): add("STACK", -1, b.h[j - 2:j + 1].max() + TICK)
    return b, out

def trade(g, b, j, side, stop, R):
    i0 = int(b.i1[j]) + 1; e = g.open[i0] + side * TICK; risk = side * (e - stop)
    if risk <= 0: return None
    tp = e + side * R * risk; mae = 0.0
    for i in range(i0, len(g)):
        h, l = g.high[i], g.low[i]; mae = max(mae, side * (e - (l if side > 0 else h)))
        if (side > 0 and l <= stop) or (side < 0 and h >= stop): px = stop - side * TICK; break
        if (side > 0 and h >= tp) or (side < 0 and l <= tp): px = tp; break
    else: px = g.close.iloc[-1] - side * TICK; i = len(g) - 1
    return dict(pnl=(px - e) * side * PV - FEE, mae=mae * PV + FEE, xi=i, risk=risk * PV)

def run(P, names, R, maxd=3, rand=None):
    rows = []; rnd = random.Random(rand)
    for n, d in enumerate(dl):
        if d < S0: continue
        b, sg = cache[(d, P["k"], P["m"])]; g = days[d]; busy = -1; c = 0
        for name, j, side, stop in sg:
            if name not in names or b.i1[j] < busy or c >= maxd: continue
            if rand is not None:
                dist = abs(b.c[j] - stop); side = rnd.choice((1, -1)); stop = b.c[j] - side * dist
            t = trade(g, b, j, side, stop, R)
            if t is None or t["risk"] > 400: continue
            rows.append(dict(d=d, **t)); busy = t["xi"]; c += 1
    return pd.DataFrame(rows, columns=["d", "pnl", "mae", "xi", "risk"])

def stats(t, era):
    s, e = sim.RANGES[era]; x = t[(t.d >= s) & (t.d <= e)]
    if len(x) == 0: return dict(n=0)
    w = x.pnl[x.pnl > 0].sum(); lo = -x.pnl[x.pnl < 0].sum(); eq = x.pnl.cumsum()
    ev = sim.eval_roll(x, era, horizon=60, step=1) if len(sim.pd.bdate_range(s, e)) > 45 else {}
    bo = sim.eval_boot(x, era, n_paths=500, cap=250)
    return dict(n=len(x), win=round(100 * (x.pnl > 0).mean(), 1), pf=round(w / lo, 2) if lo else 99, avg=round(x.pnl.mean(), 2), net=round(x.pnl.sum()),
                dd=round((eq.cummax().clip(lower=0) - eq).max()), roll_pass=round(ev.get("pass_", np.nan)), roll_bust=round(ev.get("bust", np.nan)),
                boot_pass=round(bo["pass_"]), boot_bust=round(bo["bust"]), med_days=bo["med"])

cache = {}
grid = [dict(k=k, m=m) for k in (1.0, 1.5, 2.0) for m in (1.5, 2.5)]
for P in grid:
    for n, d in enumerate(dl):
        cache[(d, P["k"], P["m"])] = signals(d, dl[n - 1] if n else None, P)
SIG = ["ABS", "DIV", "SWEEP", "POC", "STACK"]
res = []
for P in grid:
    for R in (1.5, 2.0):
        for names in [[s] for s in SIG] + [list(c) for c in itertools.combinations(SIG, 2)] + [SIG]:
            t = run(P, names, R); res.append(dict(P=P, R=R, names=names, pick=stats(t, "PICK"), t=t))
# select on PICK only: PF with n>=40
ok = [r for r in res if r["pick"].get("n", 0) >= 40]
ok.sort(key=lambda r: -r["pick"]["pf"])
out = dict(per_signal=[], top=[])
for s in SIG:  # best params per single signal chosen on PICK
    c = [r for r in ok if r["names"] == [s]]
    if not c: c = [r for r in res if r["names"] == [s]]
    r = max(c, key=lambda r: r["pick"].get("pf", 0))
    rnds = [stats(run(r["P"], r["names"], r["R"], rand=sd), "JUDGE") for sd in range(20)]
    out["per_signal"].append(dict(sig=s, P=r["P"], R=r["R"], pick=r["pick"], judge=stats(r["t"], "JUDGE"),
        rand_judge_avg=round(float(np.mean([x.get("avg", 0) for x in rnds])), 2), rand_judge_pf=round(float(np.median([x.get("pf", 0) for x in rnds])), 2)))
for r in ok[:5]:
    rnds = [stats(run(r["P"], r["names"], r["R"], rand=sd), "JUDGE") for sd in range(20)]
    out["top"].append(dict(sig="+".join(r["names"]), P=r["P"], R=r["R"], pick=r["pick"], judge=stats(r["t"], "JUDGE"), year=stats(r["t"], "YEAR"),
        rand_judge_avg=round(float(np.mean([x.get("avg", 0) for x in rnds])), 2), rand_judge_pf=round(float(np.median([x.get("pf", 0) for x in rnds])), 2)))
nz = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE_250_lock100_10.csv")
out["noise"] = dict(pick=stats(nz, "PICK"), judge=stats(nz, "JUDGE"), year=stats(nz, "YEAR"))
out["n_configs"] = len(res)
json.dump(out, open("/home/user/opogabuuga/docs/results/session18/order_flow/of1y.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
