"""Offline screening of PASS candidates exported by research.py.

Simulates every candidate's bracket on the 1-minute CSV the same way the backtest does (limit entry at the plan
entry, valid limit_timeout_bars × profile timeframe; stop-first on the same bar; 1-tick stop slippage; fees; flat at
16:40 ET), then measures win rate / expectancy per filter on TRAIN (older sessions) and TEST (newest sessions).

usage: screen.py RES.json CSV TICK TICK_VALUE FEE_RT [train_share]"""
import itertools
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime, time
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/home/user/paytience/backend")
from app.backtest.data import load_csv  # noqa: E402
from app.clock import session_date  # noqa: E402

ET = ZoneInfo("America/New_York")
res = json.load(open(sys.argv[1]))
bars = load_csv(Path(sys.argv[2]).read_text())
TICK, TV, FEE = D(sys.argv[3]), D(sys.argv[4]), D(sys.argv[5])
TRAIN = float(sys.argv[6]) if len(sys.argv) > 6 else 0.73
LIMIT_BARS = 4
FLAT = time(16, 40)
idx = {b.open_ms: i for i, b in enumerate(bars)}
opens = [b.open_ms for b in bars]


def ts(s):
    d = datetime.fromisoformat(str(s).replace(" ", "T"))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def first_bar_at_or_after(ms):
    import bisect

    return bisect.bisect_left(opens, ms)


def simulate(c):
    p = next((x for x in c["plans"] if x["mode"] == "STANDARD"), None)
    if p is None:
        return None
    d = 1 if p["direction"] == "LONG" else -1
    entry, stop, tp, risk = D(p["entry"]), D(p["stop"]), D(p["take_profit"]), D(p["risk_pts"])
    t0 = ts(c["entry_bar_time"] or c["bar_time"])
    tf = 5 if c["profile"] == "STD" else 1
    i = first_bar_at_or_after(int(t0.timestamp() * 1000))
    deadline = int(t0.timestamp() * 1000) + LIMIT_BARS * tf * 60_000
    fill = None
    while i < len(bars) and bars[i].open_ms < deadline:
        b = bars[i]
        if (d == 1 and b.l <= entry) or (d == -1 and b.h >= entry):
            fill = i
            break
        i += 1
    if fill is None:
        return {"filled": False}
    fee_r = FEE / (risk / TICK * TV)
    slip_r = TICK / risk
    fee_ticks = -(-FEE // TV)  # ceil: breakeven stop covers the round-trip fee

    def manage(be_at):
        cur_stop, moved = stop, False
        for j in range(fill, len(bars)):
            b = bars[j]
            et = datetime.fromtimestamp(b.open_ms / 1000, tz=UTC).astimezone(ET)
            if j > fill and et.time() >= FLAT:
                r = (b.o - entry) * d / risk
                return {"r": float(r - fee_r), "win": r - fee_r > 0, "exit": "FLAT"}
            if (d == 1 and b.l <= cur_stop) or (d == -1 and b.h >= cur_stop):  # stop-first on ambiguous bars
                if moved:
                    r = (cur_stop - entry) * d / risk - slip_r
                    return {"r": float(r - fee_r), "win": False, "exit": "BE"}
                return {"r": float(D(-1) - slip_r - fee_r), "win": False, "exit": "STOP"}
            if j > fill and ((d == 1 and b.h >= tp) or (d == -1 and b.l <= tp)):
                r = (tp - entry) * d / risk
                return {"r": float(r - fee_r), "win": True, "exit": "TP"}
            if be_at is not None and not moved and j > fill:
                if (d == 1 and b.h >= entry + D(str(be_at)) * risk) or (d == -1 and b.l <= entry - D(str(be_at)) * risk):
                    cur_stop, moved = entry + d * fee_ticks * TICK, True  # takes effect from the NEXT bar
        return {"r": 0.0, "win": False, "exit": "END"}

    base, be1, be125 = manage(None), manage(1.0), manage(1.25)
    return {"filled": True, **base, "be1_r": be1["r"], "be1_exit": be1["exit"], "be125_r": be125["r"],
            "be125_exit": be125["exit"]}


cands = []
for c in res["signals"]:
    if c["status"] != "PASS" or not c["plans"]:
        continue
    o = simulate(c)
    if not o or not o["filled"]:
        continue
    f = c["features"]
    t0 = ts(c["entry_bar_time"] or c["bar_time"])
    et = t0.astimezone(ET)
    items = {k: float(v) for k, v in f.get("score_items", {}).items()}
    p = next(x for x in c["plans"] if x["mode"] == "STANDARD")
    cands.append({
        "sess": session_date(t0).isoformat(),
        "hour": et.hour,
        "profile": c["profile"],
        "dir": c["direction"],
        "choch": bool(f.get("choch")),
        "bos": bool(f.get("bos")),
        "brk": bool(f.get("choch")) or bool(f.get("bos")),
        "score": float(c["score"] or 0),
        "cisd_early": items.get("cisd_before_c2_close", 0) > 0,
        "osc_strong": items.get("osc_strength", 0) > 0,
        "htf_agree": items.get("htf_mso_agrees", 0) > 0,
        "c1atr": float(c["c1_range_atr"] or 0),
        "atr_pct": float((f.get("tags") or {}).get("atr_pct") or -1),
        "weekday": (f.get("tags") or {}).get("weekday"),
        "news": bool((f.get("tags") or {}).get("news_day")),
        "rr": float(D(p["rr"])),
        "risk_pts": float(D(p["risk_pts"])),
        **o,
    })

json.dump(cands, open(sys.argv[1].replace(".json", "_cands.json"), "w"))
days = sorted({x["sess"] for x in cands})
cut = days[int(len(days) * TRAIN)] if days else None
for x in cands:
    x["part"] = "train" if x["sess"] < cut else "test"


def st(rows):
    n = len(rows)
    if not n:
        return (0, None, None)
    w = sum(1 for r in rows if r["win"])
    return (n, w / n, sum(r["r"] for r in rows) / n)


def fmt(s):
    n, w, e = s
    return f"{n:3d} tr {('%3.0f%%' % (w * 100)) if w is not None else '  — '} {('%+.2fR' % e) if e is not None else '   —  '}"


tr = [x for x in cands if x["part"] == "train"]
te = [x for x in cands if x["part"] == "test"]
print(f"{res['symbol']}: {len(cands)} filled candidates · sessions {len(days)} (train {sum(1 for d in days if d < cut)}, test {sum(1 for d in days if d >= cut)})")
print(f"ALL            train {fmt(st(tr))} | test {fmt(st(te))}")


def mg(rows, key):
    """Management variant summary: TP rate, non-loss rate (TP or BE), R/trade."""
    n = len(rows)
    if not n:
        return "  0 tr"
    tp = sum(1 for r in rows if r[f"{key}_exit"] == "TP")
    nl = sum(1 for r in rows if r[f"{key}_exit"] in ("TP", "BE") or (r[f"{key}_exit"] == "FLAT" and r[f"{key}_r"] > 0))
    return f"{n:3d} tr TP {tp / n:4.0%} non-loss {nl / n:4.0%} {sum(r[f'{key}_r'] for r in rows) / n:+.2f}R"


for key, label in (("be1", "BE at +1R"), ("be125", "BE at +1.25R")):
    print(f"ALL {label:13s} train {mg(tr, key)} | test {mg(te, key)}")

conds = {
    "brk": lambda x: x["brk"], "choch": lambda x: x["choch"], "no_brk": lambda x: not x["brk"],
    "TIGHT": lambda x: x["profile"] == "TIGHT", "STD": lambda x: x["profile"] == "STD",
    "LONG": lambda x: x["dir"] == "LONG", "SHORT": lambda x: x["dir"] == "SHORT",
    "cisd_early": lambda x: x["cisd_early"], "osc_strong": lambda x: x["osc_strong"], "htf_agree": lambda x: x["htf_agree"],
    "no_htf": lambda x: not x["htf_agree"], "no_news": lambda x: not x["news"],
    **{f"score>={s}": (lambda s: lambda x: x["score"] >= s)(s) for s in (50, 60, 70, 80)},
    **{f"c1atr>={v}": (lambda v: lambda x: x["c1atr"] >= v)(v) for v in (0.4, 0.6, 0.8, 1.0)},
    **{f"atr<={v}": (lambda v: lambda x: 0 <= x["atr_pct"] <= v)(v) for v in (50, 75, 90)},
    **{f"atr>={v}": (lambda v: lambda x: x["atr_pct"] >= v)(v) for v in (25, 50)},
    **{f"rr<={v}": (lambda v: lambda x: x["rr"] <= v)(v) for v in (2.0, 2.5)},
    **{f"rr>={v}": (lambda v: lambda x: x["rr"] >= v)(v) for v in (2.5,)},
    "h03-07": lambda x: 3 <= x["hour"] < 7, "h07-09": lambda x: 7 <= x["hour"] < 9, "h09-12": lambda x: 9 <= x["hour"] < 12,
    "h12-16": lambda x: 12 <= x["hour"] < 16, "not_h12": lambda x: x["hour"] != 12, "not_h03_04": lambda x: x["hour"] not in (3, 4),
}
print("\nby hour (train | test):")
for h in sorted({x["hour"] for x in cands}):
    print(f"  {h:02d} ET  {fmt(st([x for x in tr if x['hour'] == h]))} | {fmt(st([x for x in te if x['hour'] == h]))}")
print("\nsingle filters:")
for k, f in conds.items():
    print(f"  {k:12s} train {fmt(st([x for x in tr if f(x)]))} | test {fmt(st([x for x in te if f(x)]))}")
MIN = int(sys.argv[7]) if len(sys.argv) > 7 else 8
best = []
for n in (1, 2, 3):
    for combo in itertools.combinations(conds, n):
        rows = [x for x in tr if all(conds[k](x) for k in combo)]
        s = st(rows)
        if s[0] >= MIN and s[1] >= 0.60 and s[2] > 0:
            best.append((s[2], s[1], combo, s, st([x for x in te if all(conds[k](x) for k in combo)])))
best.sort(key=lambda z: (z[1], z[0]), reverse=True)
print(f"\nfilter combos with TRAIN win >= 60% and >= {MIN} trades (top 25), then their TEST result:")
for e, w, combo, s, t in best[:25]:
    te_rows = [x for x in te if all(conds[k](x) for k in combo)]
    tr_rows = [x for x in tr if all(conds[k](x) for k in combo)]
    print(f"  {' & '.join(combo):40s} train {fmt(s)} | test {fmt(t)}")
    print(f"  {'':40s}   +BE1R train {mg(tr_rows, 'be1')} | test {mg(te_rows, 'be1')}")
