"""Exhaustive search (≤3 boolean filters + hour + direction + break) on indscreen rows at a fixed K·R target.
Ranked by the WORSE of the two halves' win rates (both must hold), min N trades per half.  usage: combo3.py ROWS.json [N]"""
import itertools, json, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
rows = json.load(open(sys.argv[1])); N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
ET = ZoneInfo("America/New_York")
for r in rows:
    h = datetime.fromtimestamp(r["t0ms"] / 1000, ET).hour
    for a, b in ((3, 5), (5, 7), (7, 9), (9, 12), (12, 15)):
        r[f"h{a:02d}-{b:02d}"] = a <= h < b
    r["long"] = r["d"] == 1; r["short"] = r["d"] == -1; r["break"] = bool(r["brk"]); r["nobreak"] = not r["brk"]
keys = sorted({k for r in rows for k, v in r.items() if isinstance(v, bool) and k != "win" and not k.startswith("warm")})
days = sorted({r["sess"] for r in rows}); cut = days[len(days) // 2]
M = np.array([[bool(r.get(k)) for k in keys] for r in rows]); W = np.array([r["win"] for r in rows]); R = np.array([r["r"] for r in rows])
A = np.array([r["sess"] < cut for r in rows])
best = []
for n in (1, 2, 3):
    for c in itertools.combinations(range(len(keys)), n):
        m = M[:, c].all(1); a, b = m & A, m & ~A
        na, nb = a.sum(), b.sum()
        if na < N or nb < N: continue
        wa, wb = W[a].mean(), W[b].mean()
        best.append((min(wa, wb), wa, wb, na, nb, R[a].mean(), R[b].mean(), [keys[i] for i in c]))
best.sort(reverse=True)
print(f"{len(rows)} setups, {len(keys)} filters, cut {cut}, min {N}/half; top 15 by worse-half win rate:")
for x in best[:15]:
    print(f"{' & '.join(x[7]):55s} old {x[3]:4d} tr {x[1]:4.0%} {x[5]:+.2f}R | new {x[4]:4d} tr {x[2]:4.0%} {x[6]:+.2f}R")
