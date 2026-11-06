"""Best strategy in the user's R:R window 1.5–2.5 (session 8, D49) with a strict hold-out.

Rows: indscreen.py DUMP_ROWS with path fields (mfe/stopped/flat_r/t2rr). Engine target rule = (rr_min, rr_max):
skip if T2 < rr_min·R, else TP = min(T2, rr_max·R). Outcome per setup: win if the max favourable move before the
stop bar reaches the target; else −1R (stop, + slippage) or the 16:40 flat result; fees always.
Base = what the engine requires anyway: score ≥ 60 (risk tiers start at 60) and C1 ≥ 0.4 ATR.
Pick on sessions < TEST_FROM, judge on the rest.   usage: best1525.py ROWS.json [TEST_FROM] [MIN_TRAIN]"""
import itertools
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

rows = [r for r in json.load(open(sys.argv[1])) if r.get("t2rr") is not None and r.get("mfe") is not None]
TEST_FROM = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
MIN_TRAIN = int(sys.argv[3]) if len(sys.argv) > 3 else 60
SESSIONS = int(sys.argv[4]) if len(sys.argv) > 4 else 1672  # sessions in the export (for trades/day)
ET = ZoneInfo("America/New_York")
for r in rows:
    t = datetime.fromtimestamp(r["t0ms"] / 1000, ET)
    r["_h"] = t.hour + t.minute / 60
base = np.array([r["score"] >= 60 and r["c1atr"] >= 0.4 for r in rows])
T2 = np.array([r["t2rr"] for r in rows]); MFE = np.array([r["mfe"] for r in rows])
STOP = np.array([r["stopped"] for r in rows]); FLAT = np.array([r["flat_r"] if r["flat_r"] is not None else 0.0 for r in rows])
FEE = np.array([r["fee_r"] for r in rows]); SLIP = np.array([r["slip_r"] for r in rows])
TR = np.array([r["sess"] < TEST_FROM for r in rows])
n_tr = len({r["sess"] for r in rows if r["sess"] < TEST_FROM}) or 1
n_te = len({r["sess"] for r in rows if r["sess"] >= TEST_FROM}) or 1
share_tr = n_tr / (n_tr + n_te)


def outcome(rr_min, rr_max):
    ok = T2 >= rr_min
    k = np.minimum(T2, rr_max)
    win = MFE >= k
    r = np.where(win, k - FEE, np.where(STOP, -1 - SLIP - FEE, FLAT - FEE))
    return ok, win, r


feat = {}
bool_keys = sorted({k for r in rows for k, v in r.items() if isinstance(v, bool) and k not in ("win", "stopped")
                    and not k.startswith("warm")})
for k in bool_keys:
    feat[k] = np.array([bool(r.get(k)) for r in rows])
feat["long"] = np.array([r["d"] == 1 for r in rows]); feat["short"] = ~feat["long"]
feat["TIGHT"] = np.array([r["profile"] == "TIGHT" for r in rows]); feat["STD"] = ~feat["TIGHT"]
for v in (70, 75):
    feat[f"score>={v}"] = np.array([r["score"] >= v for r in rows])
for v in (0.6, 0.8):
    feat[f"c1atr>={v}"] = np.array([r["c1atr"] >= v for r in rows])
for a, b in ((3, 7), (7, 12), (12, 15.5), (5, 7), (9, 12)):
    feat[f"h{a:g}-{b:g}"] = np.array([a <= r["_h"] < b for r in rows])
names = list(feat)
RULES = [(a, b) for a in (1.5, 1.75, 2.0) for b in (1.55, 1.75, 2.0, 2.25, 2.5) if b >= a]
res = []
for rr_min, rr_max in RULES:
    ok, win, rv = outcome(rr_min, rr_max)
    m0 = base & ok
    for n in (0, 1, 2):
        for c in itertools.combinations(range(len(names)), n):
            m = m0.copy()
            for i in c:
                m &= feat[names[i]]
            a, b = m & TR, m & ~TR
            if a.sum() < MIN_TRAIN:
                continue
            res.append({"rule": (rr_min, rr_max), "f": [names[i] for i in c],
                        "tr": (int(a.sum()), win[a].mean(), rv[a].mean(), a.sum() / n_tr),
                        "te": (int(b.sum()), win[b].mean() if b.any() else 0, rv[b].mean() if b.any() else 0, b.sum() / n_te)})


def line(x):
    tr, te = x["tr"], x["te"]
    f = " & ".join(x["f"]) or "(base only)"
    return (f"R:R {x['rule'][0]:.2f}–{min(x['rule'][1], 2.5):.2f}  {f:40s} pick {tr[0]:4d} tr {tr[1]:4.0%} {tr[2]:+.2f}R"
            f" {tr[3]:.2f}/d | UNSEEN {te[0]:4d} tr {te[1]:4.0%} {te[2]:+.2f}R {te[3]:.2f}/d")


print(f"{len(rows)} setups · {len(names)} filters · {len(RULES)} target rules · {len(res)} candidates · pick < {TEST_FROM}")
print("\nNo extra filter, by target rule (base = score 60 + C1 0.4):")
for x in [x for x in res if not x["f"]]:
    print("  " + line(x))
for floor in (0.05, 0.15, 0.3, 0.6, 1.0):
    cand = [x for x in res if x["tr"][3] >= floor]
    if not cand:
        continue
    cand.sort(key=lambda x: -x["tr"][2])
    print(f"\nBest R/trade on the PICK years with ≥ {floor} trades/day — top 5 (UNSEEN = honest check):")
    for x in cand[:5]:
        print("  " + line(x))
json.dump(res, open(sys.argv[1].replace(".json", "_1525.json"), "w"), default=float)
