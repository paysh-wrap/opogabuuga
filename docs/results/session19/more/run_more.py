import json, numpy as np, pandas as pd, lib, noise2
from lib import stats, eval_boot, ACC
D, F, moves = noise2.data()
FOMC = """2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11 2020-01-29 2020-03-03 2020-03-15 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28""".split()
FOMC = set(FOMC)
ds = [d for d, _ in D]; idx = {d: i for i, d in enumerate(ds)}
mon = lambda d, f: f["dow"] == 0
gap = {}
for i in range(2, len(D)):
    gap[ds[i]] = abs(D[i-1][1]["open"][0] / D[i-2][1]["close"][389] - 1)
bymonth = {}
for d in ds: bymonth.setdefault(d[:7], []).append(d)
mend = {v[-1] for v in bymonth.values()}
opex = set()
for v in bymonth.values():
    fr = [d for d in v if pd.Timestamp(d).day_of_week == 4 and 15 <= int(d[8:]) <= 21]
    opex |= set(fr)
def ds_(extra): return lambda d, f: mon(d, f) or extra(d, f)
V = {
 "B  baseline: preset C + Mondays off": {},
 "1a first check 10:30": dict(first_check=59),
 "1b first check 11:00": dict(first_check=89),
 "2  last entry 14:00": dict(hours={29, 89, 149, 209, 269}),
 "3a band x0.9": dict(bm=0.9), "3b band x1.1": dict(bm=1.1),
 "4a lookback 10d": dict(look=10), "4b lookback 20d": dict(look=20),
 "5a stop $200": dict(stop_usd=200.), "5b stop $300": dict(stop_usd=300.),
 "6a lock trigger 80pt": dict(lock=(80., 10.)), "6b lock trigger 120pt": dict(lock=(120., 10.)),
 "7  skip FOMC days": dict(dayskip=ds_(lambda d, f: d in FOMC)),
 "8a skip day after >2% gap": dict(dayskip=ds_(lambda d, f: gap.get(d, 0) > .02)),
 "8b skip day after >1% gap": dict(dayskip=ds_(lambda d, f: gap.get(d, 0) > .01)),
 "11a skip month-end day": dict(dayskip=ds_(lambda d, f: d in mend)),
 "11b skip opex Friday": dict(dayskip=ds_(lambda d, f: d in opex)),
}
for k, v in V.items():
    if "dayskip" not in v: v["dayskip"] = mon
SIZES = {25: 1, 50: 2, 100: 2, 150: 3}
def boots(t, e, over=None):
    o = {}
    for sz, n in SIZES.items():
        if over and sz in over: n = over[sz]
        r = eval_boot(t, e, sz, n_paths=300, n=n); fin = r["pass_"] + r["bust"]
        o[sz] = round(100 * r["pass_"] / fin) if fin else None
    return o
rows = []
def rec(name, t, over=None):
    r = dict(name=name, IS=stats(t, "IS"), J=stats(t, "J"), bIS=boots(t, "IS", over), bJ=boots(t, "J", over))
    rows.append(r); print(name, r["IS"]["n"], round(r["IS"]["pf"], 2), round(r["IS"]["avg"], 1), r["J"]["n"], round(r["J"]["pf"], 2), round(r["J"]["avg"], 1), r["bIS"], r["bJ"], flush=True)
base = None
for name, kw in V.items():
    t = noise2.gen(**kw)
    if base is None: base = t
    rec(name, t)
rec("10 50K size 1 micro (vs baseline 2)", base, over={50: 1})
rec("10b 50K size 3 micros", base, over={50: 3})
json.dump(rows, open("more_results.json", "w"), indent=1, default=float)
