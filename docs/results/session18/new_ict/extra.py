import pickle, numpy as np, pandas as pd, lib
out = pickle.load(open("sims.pkl", "rb")); S = {}
for (win, tf, lev, disp), n, res in out:
    for k, df in res.items(): S[(win, tf, lev, disp) + k] = df
L = []
def sel(ws, md=1): return lib.select(pd.concat([S[(w, 1, "all", 1.0, "mid", 2.0)] for w in ws], ignore_index=True), md)
L.append("### per-year, untuned 2R, 1m-FVG, all levels (n / $/trade / PF)\n| year | AM | PM | LON | AM+PM | ALL3 |\n|---|---|---|---|---|---|")
T = {nm: sel(ws) for nm, ws in {"AM": ["AM"], "PM": ["PM"], "LON": ["LON"], "AM+PM": ["AM", "PM"], "ALL3": ["AM", "PM", "LON"]}.items()}
for y in range(2019, 2027):
    row = []
    for nm, t in T.items():
        x = t[t.d.str[:4] == str(y)]; s = lib.stats(x); row.append(f"{s['n']} / {s['avg']:.1f} / {s['pf']:.2f}")
    L.append(f"| {y} | " + " | ".join(row) + " |")
# t-stats
L.append("\n### mean $/trade t-statistic (untuned 2R)\n| set | IS t | HO t | ALL t |\n|---|---|---|---|")
for nm, t in T.items():
    f = lambda x: (x.pnl.mean() / (x.pnl.std() / np.sqrt(len(x)))) if len(x) > 2 else float("nan")
    L.append(f"| {nm} | {f(t[t.d<=lib.SPLIT]):.2f} | {f(t[t.d>lib.SPLIT]):.2f} | {f(t):.2f} |")
# hold sensitivity
L.append("\n### time-exit sensitivity (untuned AM+PM 1m mid 2R; hold = minutes after window end)\n| hold | IS n/$tr/PF | HO n/$tr/PF/net |\n|---|---|---|")
cs = {w: lib.gen(w, 1, "all", 1.0) for w in ("AM", "PM")}
for hold in (0, 30, 60, 120):
    df = pd.concat([lib.simulate(cs[w], "mid", 2.0, hold=hold) for w in cs], ignore_index=True); t = lib.select(df, 1)
    a = lib.stats(t[t.d <= lib.SPLIT]); b = lib.stats(t[t.d > lib.SPLIT])
    L.append(f"| {hold} | {a['n']}/{a['avg']:.1f}/{a['pf']:.2f} | {b['n']}/{b['avg']:.1f}/{b['pf']:.2f}/{b['net']:,.0f} |")
# FVG size filter + bias (AM+PM, 2R) IS vs HO
L.append("\n### FVG size filter (gap / ATR14) and HTF bias on AM+PM untuned 2R (IS | HO: n, $/trade, PF)\n| filter | IS | HO |\n|---|---|---|")
df = pd.concat([S[(w, 1, "all", 1.0, "mid", 2.0)] for w in ("AM", "PM")], ignore_index=True)
for lab, kw in [("none", {}), ("gap>=0.5", dict(gapmin=.5)), ("gap>=1", dict(gapmin=1)), ("gap>=2", dict(gapmin=2)), ("bias prior-day", dict(bias="pd")), ("bias 15m", dict(bias="15")),
                ("bias 1H", dict(bias="1h")), ("bias pd+1H", dict(bias="pd+1h")), ("max 2/day", dict(maxday=2))]:
    t = lib.select(df, **{"maxday": 1, **kw}); a = lib.stats(t[t.d <= lib.SPLIT]); b = lib.stats(t[t.d > lib.SPLIT])
    L.append(f"| {lab} | {a['n']}, {a['avg']:.1f}, {a['pf']:.2f} | {b['n']}, {b['avg']:.1f}, {b['pf']:.2f} |")
open("extra_tables.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
