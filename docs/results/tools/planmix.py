"""Live-plan backtest summary from research.py month exports: win rate, $ and R split by planned target
(1R no-break trades vs 1.75R+ structure trades), by year and by ET hour.  usage: planmix.py DIR"""
import glob
import json
import sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
rows = []
for f in sorted(glob.glob(f"{sys.argv[1]}/*.csv.json")):
    mon = f.split("/")[-1][:7]
    d = json.load(open(f))
    rr = {}
    for s in d["signals"]:
        for p in s["plans"]:
            if p["mode"] == "STANDARD":
                rr[s["id"]] = float(p["rr"])
    for t in d["trades"]:
        if t["pnl_usd"] is None or t["opened_at"][:7] != mon:  # warm-up week belongs to the previous month
            continue
        rows.append({"mon": mon, "rr": rr.get(t["signal_id"], 0.0), "pnl": float(t["pnl_usd"]),
                     "r": float(t["net_r"] or 0), "exit": t["exit_reason"],
                     "hour": datetime.fromisoformat(t["opened_at"]).astimezone(ET).hour})


def st(rs):
    n = len(rs)
    if not n:
        return "    0 tr"
    w = sum(r["pnl"] > 0 for r in rs)
    gw = sum(r["pnl"] for r in rs if r["pnl"] > 0)
    gl = -sum(r["pnl"] for r in rs if r["pnl"] < 0)
    pf = gw / gl if gl else float("inf")
    return f"{n:5d} tr {w / n:4.0%} win  PF {pf:4.2f}  ${sum(r['pnl'] for r in rs):+9.0f}  {sum(r['r'] for r in rs) / n:+.2f}R/tr"


one = [r for r in rows if r["rr"] < 1.5]
big = [r for r in rows if r["rr"] >= 1.5]
print("ALL              ", st(rows))
print("target ~1R        ", st(one))
print("target 1.75R+     ", st(big))
print("excl. RR_INVALID  ", st([r for r in rows if r["exit"] != "RR_INVALID_AFTER_FILL"]))
by = defaultdict(list)
for r in rows:
    by[r["mon"][:4]].append(r)
for y in sorted(by):
    print(f"{y}             ", st(by[y]))
print("by hour ET:")
bh = defaultdict(list)
for r in rows:
    bh[r["hour"]].append(r)
for h in sorted(bh):
    print(f"  {h:02d}            ", st(bh[h]))
ex = defaultdict(int)
for r in rows:
    ex[r["exit"]] += 1
print("exits:", dict(ex))
