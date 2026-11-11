"""Context-over-signals add-on (Jesse Rogers chapter list; content unavailable): premium/discount + volatility regime filters on the of1y.py signals.
PD_SESS: long only if close <= midpoint of session range so far, short only if >= it. PD_PREV: same vs prior session's range midpoint.
VOL: skip days whose prior-session range is below the 33rd percentile of the trailing 60 sessions (no lookahead). Gamma exposure: skipped (needs options data)."""
import json, itertools, numpy as np, pandas as pd
src = open("/home/user/opogabuuga/docs/results/session18/order_flow/of1y.py").read().split("cache = {}")[0]
exec(src)
rngd = pd.Series({d: days[d].high.max() - days[d].low.min() for d in dl})
pct = rngd.shift(1).rolling(60, min_periods=20).apply(lambda s: (s.iloc[-1] >= s).mean(), raw=False)
def ctx_ok(d, n, b, j, side, f):
    c = b.c[j]
    if "PD_SESS" in f:
        mid = (b.h[:j + 1].max() + b.l[:j + 1].min()) / 2
        if side * (c - mid) > 0: return False
    if "PD_PREV" in f and n:
        p = days[dl[n - 1]]; mid = (p.high.max() + p.low.min()) / 2
        if side * (c - mid) > 0: return False
    if "VOL" in f and not (pct.get(d, np.nan) >= 1 / 3): return False
    return True
def run(P, names, R, f=(), maxd=3):
    rows = []
    for n, d in enumerate(dl):
        if d < S0: continue
        b, sg = cache[(d, P["k"], P["m"])]; g = days[d]; busy = -1; c = 0
        for name, j, side, stop in sg:
            if name not in names or b.i1[j] < busy or c >= maxd or not ctx_ok(d, n, b, j, side, f): continue
            t = trade(g, b, j, side, stop, R)
            if t is None or t["risk"] > 400: continue
            rows.append(dict(d=d, **t)); busy = t["xi"]; c += 1
    return pd.DataFrame(rows, columns=["d", "pnl", "mae", "xi", "risk"])
cache = {}
grid = [dict(k=k, m=m) for k in (1.0, 1.5, 2.0) for m in (1.5, 2.5)]
for P in grid:
    for n, d in enumerate(dl): cache[(d, P["k"], P["m"])] = signals(d, dl[n - 1] if n else None, P)
SIG = ["ABS", "DIV", "SWEEP", "POC", "STACK"]
FS = [(), ("PD_SESS",), ("PD_PREV",), ("VOL",), ("PD_SESS", "VOL"), ("PD_PREV", "VOL")]
out = dict(filter_effect=[], best=[])
for s in SIG + ["ALL"]:
    names = SIG if s == "ALL" else [s]
    for f in FS:  # pick params per (signal, filter) on PICK by PF (n>=25), judge on JUDGE
        c = []
        for P in grid:
            for R in (1.5, 2.0):
                t = run(P, names, R, f); c.append((P, R, t, stats(t, "PICK")))
        cc = [x for x in c if x[3].get("n", 0) >= 25] or c
        P, R, t, pk = max(cc, key=lambda x: x[3].get("pf", 0))
        out["filter_effect"].append(dict(sig=s, filt="+".join(f) or "none", P=P, R=R, pick=pk, judge=stats(t, "JUDGE"), year=stats(t, "YEAR")))
        print(out["filter_effect"][-1], flush=True)
json.dump(out, open("/home/user/opogabuuga/docs/results/session18/order_flow/of1y_ctx.json", "w"), indent=1, default=str)
