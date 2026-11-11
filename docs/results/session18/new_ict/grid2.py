import itertools, pickle, time
import numpy as np, pandas as pd, lib
out = pickle.load(open("sims.pkl", "rb"))
S = {}
for (win, tf, lev, disp), n, res in out:
    for k, df in res.items(): S[(win, tf, lev, disp) + k] = df
WS = {"AM": ["AM"], "PM": ["PM"], "LON": ["LON"], "AM+PM": ["AM", "PM"], "ALL3": ["AM", "PM", "LON"]}
rows = []
t0 = time.time()
for tf, lev, disp, entry, tgt in itertools.product((1, 5), ("all", "static"), (1.0, 0.5), ("mid", "near"), (1.5, 2.0, "liq")):
    for wn, ws in WS.items():
        df = pd.concat([S[(w, tf, lev, disp, entry, tgt)] for w in ws], ignore_index=True)
        if not len(df): continue
        for md, bias, gm in itertools.product((1, 2), (None, "pd", "15", "1h", "pd+1h", "15+1h"), (0.0, 0.5, 1.0, 2.0)):
            t = lib.select(df, md, None, bias, gm)
            r = dict(win=wn, tf=tf, lev=lev, disp=disp, entry=entry, tgt=str(tgt), maxday=md, bias=bias or "-", gapmin=gm)
            for e in ("IS", "HO"):
                s = lib.stats(t[t.d <= lib.SPLIT] if e == "IS" else t[t.d > lib.SPLIT])
                r.update({f"{e}_{k}": v for k, v in s.items()})
                x = (t[t.d <= lib.SPLIT] if e == "IS" else t[t.d > lib.SPLIT]).pnl
                r[f"{e}_sd"] = float(x.std()) if len(x) > 2 else np.nan
            rows.append(r)
print(len(rows), time.time() - t0)
pd.DataFrame(rows).to_csv("grid.csv", index=False)
