"""Results K: offline Scalp-mode simulator over PASS candidates exported by research_scalp.py (one JSON per month).

Mirrors the app's Scalp management on 1-minute bars (validated against the real backtest trades, see Results K):
limit entry at the plan entry valid limit_timeout_bars x profile TF; stop-first on ambiguous bars; 1-tick stop slip;
fee $1.00 RT/contract; size = floor(risk$ / (stop_ticks*tv + fee + slip*tv)) capped at 10.
  1 contract : TP target_r, stop -> entry+lock_r once price reaches 75% of the target, closed at market HOLD bars
               after the fill bar (max_hold_s = 60 s on 1-minute bars).
  >= 2       : leg A at target_r; leg B aims at runner_r; after A, B stop -> BE (+fee) and trails trail_r behind
               the best price; no time stop for the runner (flat 16:40 ET).
Day rules: one position at a time, max 5 trades/day, 3 consecutive losses end the day (1:1/scalp rule).

Variants are keyword knobs of simulate(); filters are predicates on the candidate. Used as a library by k_report.py.
"""
import bisect
import glob
import json
import sys
from datetime import UTC, datetime, time
from decimal import Decimal as D
from zoneinfo import ZoneInfo

sys.path.insert(0, "/home/user/paytience/backend")
from app.backtest.data import load_csv  # noqa: E402
from app.clock import session_date  # noqa: E402

ET = ZoneInfo("America/New_York")
TICK, TV, FEE = D("0.25"), D("0.50"), D("1.00")
FLAT = time(16, 40)


def ts(s):
    d = datetime.fromisoformat(str(s).replace(" ", "T"))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


class Month:
    def __init__(self, res_json, csv):
        self.res = json.load(open(res_json))
        self.bars = load_csv(open(csv).read())
        self.opens = [b.open_ms for b in self.bars]
        self.trs = []  # rolling 14-bar 1m ATR (points) for volatility features
        prev = None
        for b in self.bars:
            tr = b.h - b.l if prev is None else max(b.h - b.l, abs(b.h - prev), abs(b.l - prev))
            self.trs.append(float(tr))
            prev = b.c

    def atr1m(self, i, n=14):
        a = self.trs[max(0, i - n):i]
        return sum(a) / len(a) if a else 0.0


def candidates(m: Month):
    out = []
    for c in m.res["signals"]:
        if c["status"] != "PASS":
            continue
        p = next((x for x in c["plans"] if x["mode"] == "ONE_TO_ONE"), None)
        if p is None:
            continue
        f = c["features"]
        items = {k: float(v) for k, v in f.get("score_items", {}).items()}
        t0 = ts(c["entry_bar_time"] or c["bar_time"])
        i0 = bisect.bisect_left(m.opens, int(t0.timestamp() * 1000))
        et = t0.astimezone(ET)
        out.append({
            "sid": c["id"], "t0": t0, "i0": i0, "sess": session_date(t0).isoformat(), "hour": et.hour,
            "hm": et.hour * 60 + et.minute, "profile": c["profile"], "dir": 1 if p["direction"] == "LONG" else -1,
            "entry": D(p["entry"]), "stop": D(p["stop"]), "risk": D(p["risk_pts"]), "score": float(c["score"] or 0),
            "choch": bool(f.get("choch")), "bos": bool(f.get("bos")), "brk": bool(f.get("choch") or f.get("bos")),
            "cisd_early": items.get("cisd_before_c2_close", 0) > 0, "osc_strong": items.get("osc_strength", 0) > 0,
            "htf": items.get("htf_mso_agrees", 0) > 0, "c1atr": float(c["c1_range_atr"] or 0),
            "atr_pct": float((f.get("tags") or {}).get("atr_pct") or -1), "atr1m": m.atr1m(i0), "m": m,
        })
    return out


def simulate(c, target_r=D("0.5"), hold=1, lock=True, lock_r=D("0.30"), runner=True, runner_r=D("2.0"),
             trail_r=D("0.5"), be_at=None, depth_r=D(0), buf_ticks=0, risk_usd=D(70), fixed_tp_all=False,
             all_runner=False, limit_bars=1, no_time_stop=False, buf_atr=0.0):
    """Mirror of SimAdapter.on_bar + OrderManager.on_bar + the scalp time stop (see module docstring)."""
    m = c["m"]
    bars, d = m.bars, c["dir"]
    entry = c["entry"] - d * D(depth_r) * c["risk"]
    entry = (entry / TICK).to_integral_value() * TICK
    buf_ticks = buf_ticks + int(buf_atr * c["atr1m"] / float(TICK))
    stop = c["stop"] - d * buf_ticks * TICK
    risk = (entry - stop) * d
    if risk <= 0:
        return None
    i, fill, fpx = c["i0"], None, None
    while i < len(bars) and i < c["i0"] + limit_bars:
        b = bars[i]
        if (d == 1 and b.l <= entry) or (d == -1 and b.h >= entry):
            fill, fpx = i, (min(b.o, entry) if d == 1 else max(b.o, entry))
            break
        i += 1
    if fill is None:
        return None
    per = risk / TICK * TV + FEE + TV
    qty = int(min(D(10), risk_usd // per))
    if qty < 1:
        return None
    two = runner and not fixed_tp_all and (qty >= 2 or all_runner)
    tp = entry + d * target_r * risk
    far = entry + d * runner_r * risk
    fee_ticks = -(-FEE // TV)
    be_px = entry + d * fee_ticks * TICK
    trig = entry + d * D("0.75") * target_r * risk
    lock_px = entry + d * lock_r * risk
    slip = TICK
    if two and qty == 1:  # all_runner on one contract: whole position becomes the runner at the first target
        qa, qb = 0, 1
    elif two:
        qa, qb = (qty + 1) // 2, qty // 2
    else:
        qa, qb = qty, 0
    open_legs = {"A": [qa, tp], "B": [qb, far]} if two else {"A": [qa, tp]}
    open_legs = {k: v for k, v in open_legs.items() if v[0] > 0}
    cur, best, locked, partial, moved = stop, None, False, False, False
    pnl = D(0)
    j = fill

    def close(q, px):
        return (px - fpx) * d / TICK * TV * q

    for j in range(fill, len(bars)):
        b = bars[j]
        et = datetime.fromtimestamp(b.open_ms / 1000, tz=UTC).astimezone(ET)
        if j > fill and et.time() >= FLAT:
            for k, (q, _) in list(open_legs.items()):
                pnl += close(q, b.o - d * slip)
            open_legs = {}
            break
        if j > fill:
            sh = (b.l <= cur) if d == 1 else (b.h >= cur)
            if sh:
                gap = (b.o <= cur) if d == 1 else (b.o >= cur)
                px = (b.o if gap else cur) - d * slip
                for k, (q, _) in list(open_legs.items()):
                    pnl += close(q, px)
                open_legs = {}
                break
            for k, (q, t) in list(open_legs.items()):
                if (b.h >= t) if d == 1 else (b.l <= t):
                    gap = (b.o >= t) if d == 1 else (b.o <= t)
                    pnl += close(q, b.o if gap else t)
                    del open_legs[k]
                    if k == "A" and "B" in open_legs:
                        partial = True
                        if (be_px - cur) * d > 0:
                            cur = be_px
            if two and qa == 0 and not partial and ((b.h >= tp) if d == 1 else (b.l <= tp)):
                partial = True  # all-runner: first target touched -> BE + trail
                if (be_px - cur) * d > 0:
                    cur = be_px
            if not open_legs:
                break
        fav = b.h if d == 1 else b.l
        best = fav if best is None or (fav - best) * d > 0 else best
        if partial:
            t = best - d * trail_r * risk
            t = (t / TICK).to_integral_value() * TICK
            if (t - cur) * d > 0:
                cur = t
        if lock and not two and not locked and (best - trig) * d >= 0:
            locked = True
            if (lock_px - cur) * d > 0:
                cur = lock_px
        if be_at is not None and not moved and (best - (entry + d * D(str(be_at)) * risk)) * d >= 0:
            moved = True
            if (be_px - cur) * d > 0:
                cur = be_px
        if not partial and not no_time_stop and j - fill >= hold:
            for k, (q, _) in list(open_legs.items()):
                pnl += close(q, b.c - d * slip)
            open_legs = {}
            break
    if open_legs:
        return None
    usd = pnl - FEE * qty
    return {"fill": fill, "qty": qty, "usd": float(usd), "r": float(usd / (qty * per)), "end": j}


def run(cands, filt=lambda c: True, max_day=5, max_consec=3, **kw):
    """Sequential day rules over time-ordered candidates; returns the taken trades."""
    out, day, busy = [], {}, (None, -1)
    for c in sorted(cands, key=lambda x: x["t0"]):
        if not filt(c):
            continue
        st = day.setdefault(c["sess"], {"n": 0, "cl": 0})
        if st["n"] >= max_day or st["cl"] >= max_consec:
            continue
        if busy[0] is c["m"] and c["i0"] <= busy[1]:
            continue  # one position at a time
        o = simulate(c, **kw)
        if o is None:
            continue
        busy = (c["m"], o["end"])
        st["n"] += 1
        st["cl"] = 0 if o["usd"] > 0 else st["cl"] + 1
        out.append({"sess": c["sess"], "hour": c["hour"], "sid": c["sid"], **o})
    return out


def stats(tr, sessions):
    n = len(tr)
    if not n:
        return {"n": 0}
    w = sum(1 for t in tr if t["usd"] > 0)
    gp = sum(t["usd"] for t in tr if t["usd"] > 0)
    gl = -sum(t["usd"] for t in tr if t["usd"] < 0)
    eq = pk = dd = 0.0
    for t in tr:
        eq += t["usd"]
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
    return {"n": n, "tpd": n / sessions, "win": w / n, "pf": gp / gl if gl else float("inf"), "net": eq, "dd": dd,
            "avg_r": sum(t["r"] for t in tr) / n}


def load(kdir, months, sub=""):
    ms = []
    for mo in months:
        try:
            ms.append(Month(f"{kdir}{sub}/r_{mo}.json", f"{kdir}/m/mnq_{mo}.csv"))
        except FileNotFoundError:
            pass
    return ms


if __name__ == "__main__":
    print(sorted(glob.glob(sys.argv[1] + "/r_*.json")))
