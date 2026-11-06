"""Best 1.75R strategy search with a strict hold-out (session 8).

Rows: indscreen.py DUMP_ROWS output (every filled setup of the loose research plan, fixed K·R target, stop-first,
fees, slippage, flat 16:40 ET). Filters = indicator flags + engine settings (score, C1/ATR, T2 R:R, stop size,
structure, MSO, hours, side, profile, weekday). Selection uses ONLY sessions before TEST_FROM; the newest years
are reported but never used to pick.  usage: best175.py ROWS.json [TEST_FROM=2024-01-01] [MIN_TRAIN=100]"""
import itertools
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

rows = json.load(open(sys.argv[1]))
TEST_FROM = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
MIN_TRAIN = int(sys.argv[3]) if len(sys.argv) > 3 else 100
ET = ZoneInfo("America/New_York")
LIVE_HOURS = ((5, 0, 7, 0), (9, 0, 12, 0), (13, 0, 15, 30))  # D37 intraday_windows (MGC) — the live plan

feat: dict[str, list[bool]] = {}


def add(name, fn):
    feat[name] = [bool(fn(r)) for r in rows]


for r in rows:
    t = datetime.fromtimestamp(r["t0ms"] / 1000, ET)
    r["_h"] = t.hour + t.minute / 60
bool_keys = sorted({k for r in rows for k, v in r.items() if isinstance(v, bool) and k not in ("win",)
                    and not k.startswith("warm")})
for k in bool_keys:
    add(k, lambda r, k=k: r.get(k))
add("long", lambda r: r["d"] == 1)
add("short", lambda r: r["d"] == -1)
add("TIGHT", lambda r: r["profile"] == "TIGHT")
add("STD", lambda r: r["profile"] == "STD")
for v in (50, 60, 70, 75):
    add(f"score>={v}", lambda r, v=v: r["score"] >= v)
for v in (0.4, 0.6, 0.8, 1.0):
    add(f"c1atr>={v}", lambda r, v=v: r["c1atr"] >= v)
for v in (1.75, 2.0, 2.5, 3.0):
    add(f"T2rr>={v}", lambda r, v=v: r["plan_rr"] >= v)
for v in (20, 30, 40):
    add(f"stop>={v}t", lambda r, v=v: r["risk_ticks"] >= v)
for v in (30, 40, 60):
    add(f"stop<={v}t", lambda r, v=v: r["risk_ticks"] <= v)
add("atr10-90", lambda r: 10 <= r["atr_pct"] <= 90)
for a, b in ((3, 5), (5, 7), (7, 9), (9, 12), (12, 15.5), (9, 11), (13, 15.5)):
    add(f"h{a:g}-{b:g}", lambda r, a=a, b=b: a <= r["_h"] < b)
add("h_live", lambda r: any(a + am / 60 <= r["_h"] < b + bm / 60 for a, am, b, bm in LIVE_HOURS))
add("not_mon_fri", lambda r: r.get("weekday") not in ("Mon", "Fri"))

names = list(feat)
M = np.array([feat[k] for k in names]).T  # rows × features
W = np.array([r["win"] for r in rows], dtype=float)
R = np.array([r["r"] for r in rows])
TR = np.array([r["sess"] < TEST_FROM for r in rows])
yrs_tr = len({r["sess"][:7] for r in rows if r["sess"] < TEST_FROM}) / 12
yrs_te = len({r["sess"][:7] for r in rows if r["sess"] >= TEST_FROM}) / 12


def stats(m):
    a, b = m & TR, m & ~TR
    return (a.sum(), W[a].mean() if a.any() else 0, R[a].mean() if a.any() else 0,
            b.sum(), W[b].mean() if b.any() else 0, R[b].mean() if b.any() else 0)


res = []
for n in (1, 2, 3):
    for c in itertools.combinations(range(len(names)), n):
        m = M[:, c].all(1)
        if (m & TR).sum() < MIN_TRAIN:
            continue
        s = stats(m)
        res.append((s[1], s, [names[i] for i in c]))
res.sort(key=lambda x: -x[0])
base = stats(np.ones(len(rows), bool))
print(f"{len(rows)} setups · {len(names)} filters · {len(res)} combos with ≥{MIN_TRAIN} train trades · "
      f"train < {TEST_FROM} ({yrs_tr:.1f} y) · test ≥ {TEST_FROM} ({yrs_te:.1f} y) · fixed 1.75R")
print(f"{'no filter':58s} train {base[0]:5d} {base[1]:4.0%} {base[2]:+.2f}R | test {base[3]:5d} {base[4]:4.0%} {base[5]:+.2f}R")
print("TOP 25 picked on TRAIN only (test = unseen years):")
out = []
for w, s, k in res[:25]:
    print(f"{' & '.join(k):58s} train {s[0]:5d} {s[1]:4.0%} {s[2]:+.2f}R | test {s[3]:5d} {s[4]:4.0%} {s[5]:+.2f}R"
          f" ({s[3] / yrs_te / 52:.1f}/wk)")
    out.append({"filters": k, "train": [int(s[0]), s[1], s[2]], "test": [int(s[3]), s[4], s[5]]})
print("\nhighest win rate seen on TEST among combos with ≥40 test trades (optimistic: picked on test):")
te = sorted((x for x in res if x[1][3] >= 40), key=lambda x: -x[1][4])[:5]
for w, s, k in te:
    print(f"{' & '.join(k):58s} train {s[0]:5d} {s[1]:4.0%} {s[2]:+.2f}R | test {s[3]:5d} {s[4]:4.0%} {s[5]:+.2f}R")
json.dump({"test_from": TEST_FROM, "min_train": MIN_TRAIN, "base": base, "top": out}, open(sys.argv[1].replace(
    ".json", "_best175.json"), "w"), default=float)
