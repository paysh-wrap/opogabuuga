"""Teacher CZT (Condition -> Zone -> Trigger, Jesse Rogers 4h, TEACHER_RULES_4H.md) on ESTIMATED order flow from cached MNQ.v.0 1m bars.
Same 1-year walk-forward as of1y.py. Gamma exposure skipped (no options data). LVN zones skipped (kept simple)."""
import json, itertools, numpy as np, pandas as pd
src = open("/home/user/opogabuuga/docs/results/session18/order_flow/of1y.py").read().split("cache = {}")[0]
exec(src)
full = pd.read_csv(CSV); full["t"] = pd.to_datetime(full.timestamp).dt.tz_convert("America/New_York")
full = full[(full.t >= "2025-11-01") & (full.t <= "2026-11-06")]
def profile(g):
    vp = g.groupby((g.close / 2).round() * 2).volume.sum().sort_index(); poc = vp.idxmax(); tot = vp.sum()
    px = list(vp.index); i = lo = hi = px.index(poc); acc = vp[poc]
    while acc < 0.7 * tot:
        up = vp.iloc[hi + 1] if hi + 1 < len(px) else -1; dn = vp.iloc[lo - 1] if lo > 0 else -1
        if up >= dn: hi += 1; acc += up
        else: lo -= 1; acc += dn
    return poc, px[hi], px[lo]
PROF = {d: profile(days[d]) for d in dl}
ON = {}
for d in dl:
    t0 = pd.Timestamp(d, tz="America/New_York")
    x = full[(full.t >= t0 - pd.Timedelta(hours=6)) & (full.t < t0 + pd.Timedelta(hours=9, minutes=30))]
    ON[d] = (x.high.max(), x.low.min()) if len(x) else (np.nan, np.nan)
vaw = pd.Series({d: PROF[d][1] - PROF[d][2] for d in dl}); vpct = vaw.rolling(60, min_periods=20).apply(lambda s: (s.iloc[-1] >= s).mean(), raw=False)

def czt_signals(d, n, k, cond_on):
    g = days[d]; b = bars5(g); poc, vah, val = PROF[dl[n - 1]]; onh, onl = ON[d]; op = g.open[0]
    if cond_on and not (vpct.get(dl[n - 1], 0) >= 0.2): return b, []  # flat/compressed prior value -> no trade
    lean = 1 if op > vah else (-1 if op < val else 0)
    ad = b.dlt.abs().rolling(20, min_periods=4).mean().shift(1).fillna(b.dlt.abs().expanding().mean()); av = b.v.rolling(20, min_periods=4).mean().shift(1).fillna(b.v.expanding().mean())
    out = []
    for j in range(2, len(b) - 2):
        if b.k[j] > 71: break
        r = b.iloc[j]; mid = (r.h + r.l) / 2
        rn = [np.floor(r.l / 100) * 100, np.ceil(r.h / 100) * 100]
        zl = [z for z in (val, poc, vah, onl, onh, *rn) if not np.isnan(z) and r.l <= z + 2 * TICK and r.c > z]  # support touched, held
        zh = [z for z in (val, poc, vah, onl, onh, *rn) if not np.isnan(z) and r.h >= z - 2 * TICK and r.c < z]
        heavy = abs(r.dlt) > k * ad[j]
        for side, zs in ((1, zl), (-1, zh)):
            if not zs: continue
            if cond_on:
                if lean == -side: continue
                if lean == 0 and not ((side == 1 and min(zs) <= val + 2 * TICK) or (side == -1 and max(zs) >= vah - 2 * TICK)): continue
            z = min(zs) if side == 1 else max(zs); rnd = z % 100 == 0
            stop = (min(r.l, z) - (3 if rnd else 1) * TICK) if side == 1 else (max(r.h, z) + (3 if rnd else 1) * TICK)
            absorb = heavy and side * r.dlt < 0 and side * (r.c - mid) > 0
            exh = (side * (b.c[j - 1] - b.c[j - 2]) < 0 and r.v < 0.7 * av[j] and abs(r.dlt) < 0.5 * ad[j] and side * (r.c - mid) > 0)
            if absorb: out.append(("ABSORB", j, side, stop))
            elif exh: out.append(("EXHAUST", j, side, stop))
        # continuation: aggression with acceptance - breakout through a zone in lean direction, next bar holds
        if cond_on and lean == 0: continue
        for side in (1, -1):
            if cond_on and side != lean: continue
            zs = [z for z in (val, poc, vah, onl, onh) if not np.isnan(z) and side * (b.o[j] - z) < 0 and side * (r.c - z) > 0]
            if zs and heavy and side * r.dlt > 0:
                j2 = j + 1; z = zs[0]
                if side * (b.c[j2] - z) > 0 and side * b.dlt[j2] >= 0:
                    out.append(("AGGR", j2, side, (min(b.l[j2], z) - TICK) if side == 1 else (max(b.h[j2], z) + TICK)))
    out.sort(key=lambda x: x[1]); return b, out

def trade_x(g, b, j, side, stop, mode):
    i0 = int(b.i1[j]) + 1; e = g.open[i0] + side * TICK; risk = side * (e - stop)
    if risk <= 0: return None
    tp = e + side * 2 * risk if mode == "2R" else (e + side * 3 * risk if mode == "trail3R" else None); mae = 0.0; st = stop; best = e
    for i in range(i0, len(g)):
        h, l = g.high[i], g.low[i]; mae = max(mae, side * (e - (l if side > 0 else h)))
        if (side > 0 and l <= st) or (side < 0 and h >= st): px = st - side * TICK; break
        if tp is not None and ((side > 0 and h >= tp) or (side < 0 and l <= tp)): px = tp; break
        if mode != "2R":  # trail behind each new balance: after +1R, stop under the last 15-minute (3 x 5m) balance, ratchet only
            best = max(best, h) if side > 0 else min(best, l)
            if side * (best - e) >= risk and (i - i0) % 5 == 4:
                w = g.iloc[max(i0, i - 14):i + 1]; ns = (w.low.min() - TICK) if side > 0 else (w.high.max() + TICK)
                st = max(st, ns, e + TICK) if side > 0 else min(st, ns, e - TICK)
    else: px = g.close.iloc[-1] - side * TICK; i = len(g) - 1
    return dict(pnl=(px - e) * side * PV - FEE, mae=mae * PV + FEE, xi=i, risk=risk * PV)

C = {}
for k in (1.0, 1.5, 2.0):
    for cond in (True, False):
        for n, d in enumerate(dl):
            if n: C[(d, k, cond)] = czt_signals(d, n, k, cond)
def run_c(k, cond, names, mode, maxd=2):
    rows = []
    for d in dl:
        if d < S0 or (d, k, cond) not in C: continue
        b, sg = C[(d, k, cond)]; g = days[d]; busy = -1; c = 0
        for name, j, side, stop in sg:
            if name not in names or b.i1[j] < busy or c >= maxd: continue
            t = trade_x(g, b, j, side, stop, mode)
            if t is None or t["risk"] > 400: continue
            rows.append(dict(d=d, **t)); busy = t["xi"]; c += 1
    return pd.DataFrame(rows, columns=["d", "pnl", "mae", "xi", "risk"])
TR = ["ABSORB", "EXHAUST", "AGGR"]; res = []
for k in (1.0, 1.5, 2.0):
    for cond in (True, False):
        for names in [[x] for x in TR] + [["ABSORB", "EXHAUST"], TR]:
            for mode in ("2R", "trail", "trail3R"):
                t = run_c(k, cond, names, mode)
                res.append(dict(k=k, cond=cond, trig="+".join(names), mode=mode, pick=stats(t, "PICK"), judge=stats(t, "JUDGE"), year=stats(t, "YEAR")))
                print({x: res[-1][x] for x in ("k", "cond", "trig", "mode")}, res[-1]["pick"].get("pf"), res[-1]["judge"].get("pf"), res[-1]["judge"].get("n"), flush=True)
json.dump(res, open("/home/user/opogabuuga/docs/results/session18/order_flow/czt1y.json", "w"), indent=1, default=str)
