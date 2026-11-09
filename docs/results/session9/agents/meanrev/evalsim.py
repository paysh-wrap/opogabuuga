"""Lucid 25K eval bootstrap: python evalsim.py "<SYM>" "<variant name>"
Resamples held-out trading DAYS (with their trades in order), 10,000 paths, sizes 1-3 micros.
Target +$1,250; EOD trailing max loss $1,000 (trails EOD peak; checked on EOD balance; intraday not modeled);
consistency 40% and DLL not modeled. Path capped at 120 trading days (=> 'neither')."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sym, var = sys.argv[1], sys.argv[2]
t = pd.read_pickle(os.path.join(HERE, "trades.pkl"))[(sym, var)]
t = t[t.date >= pd.Timestamp("2024-01-01")]
# all held-out trading days incl. zero-trade days
alld = pd.read_parquet(os.path.join(HERE, f"{sym.lower()}.parquet"), columns=["date"]).date.unique()
alld = alld[alld >= np.datetime64("2024-01-01")]
day = t.groupby("date").usd.sum().reindex(alld, fill_value=0.0).to_numpy()
rng = np.random.default_rng(7)
for n in (1, 2, 3):
    res = {"pass": 0, "bust": 0, "neither": 0}; days = []
    for _ in range(10000):
        bal = peak = 0.0; out = "neither"
        for k, d in enumerate(rng.choice(day, 120)):
            bal += d * n
            if bal >= 1250: out = "pass"; break
            if bal <= peak - 1000: out = "bust"; break
            peak = max(peak, bal)
        res[out] += 1
        if out == "pass": days.append(k + 1)
    print(f"{n} micro: pass {res['pass']/100:.1f}%  bust {res['bust']/100:.1f}%  neither(120d) {res['neither']/100:.1f}%  median days to pass {np.median(days) if days else 'n/a'}")
