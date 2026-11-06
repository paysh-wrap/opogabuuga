"""Combine engine month exports of several markets (same plan) → per-market + combined trades/day, win rate, $.
Per-market runs are independent (one account each); combined counts ignore the 1-position / hedge-lock interaction
across markets, so treat combined trades/day as an upper bound.  usage: combo_markets.py NAME=DIR [NAME=DIR ...]"""
import glob
import json
import sys
from collections import defaultdict


def load(d):
    out = []
    for f in sorted(glob.glob(f"{d}/*.csv.json")):
        mon = f.rsplit("/", 1)[1][:7]
        js = json.load(open(f))
        for t in js["trades"]:
            if t["pnl_usd"] is not None and t["opened_at"][:7] == mon:
                out.append({"mon": mon, "pnl": float(t["pnl_usd"]), "r": float(t["net_r"] or 0), "exit": t["exit_reason"],
                            "day": str(t["opened_at"])[:10]})
    sessions = sum(json.load(open(f)).get("sessions", 0) - 5 for f in glob.glob(f"{d}/*.csv.json"))  # minus warm-up
    return out, max(sessions, 1), len(glob.glob(f"{d}/*.csv.json"))


def st(rs, sessions):
    n = len(rs)
    if not n:
        return "   0 tr"
    w = sum(r["pnl"] > 0 for r in rs)
    gw = sum(r["pnl"] for r in rs if r["pnl"] > 0)
    gl = -sum(r["pnl"] for r in rs if r["pnl"] < 0)
    pf = gw / gl if gl else float("inf")
    days = defaultdict(float)
    for r in rs:
        days[r["day"]] += r["pnl"]
    worst = min(days.values())
    return (f"{n:4d} tr {n / sessions:4.2f}/day  win {w / n:4.0%}  PF {pf:4.2f}  ${sum(r['pnl'] for r in rs):+8.0f}  "
            f"{sum(r['r'] for r in rs) / n:+.2f}R/tr  worst day ${worst:+.0f}")


allr, total_s = [], None
for arg in sys.argv[1:]:
    name, d = arg.split("=", 1)
    rs, sessions, months = load(d)
    total_s = sessions if total_s is None else min(total_s, sessions)
    print(f"{name:4s} ({months:2d} months) {st(rs, sessions)}")
    by = defaultdict(list)
    for r in rs:
        by[r["mon"][:4]].append(r)
    print("      " + " · ".join(f"{y}: {len(v)} tr ${sum(x['pnl'] for x in v):+.0f}" for y, v in sorted(by.items())))
    allr += rs
if len(sys.argv) > 2:
    print(f"ALL  combined   {st(allr, total_s or 1)}")
