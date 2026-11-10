"""LunqFX offline evaluation of OB / SMT (filter-only and stop-anchor) on engine candidates.
Candidates = every setup the REAL engine took to outcome PASS (shadow plan: entry/stop/tp) on MNQ 1-min bars 2021-11..2026-10
(dump: research.py per month with config/rules/lucid_pro_25k.yaml, filters as in the plan). Trade simulation: fill at plan entry
at the bar the signal closes, stop first if both touched, flat 15:55 ET, 1 micro, fee $1 RT, stop slippage 1 tick, max 3 trades/day,
one position at a time. rr must be 1.75..3.0 (user R:R rule). Pick 2021-11..2023-12, judge 2024-01..2026-10."""
import sys, glob, json, pickle, os
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from datetime import datetime
import numpy as np, pandas as pd
ROOT = "/home/user/opogabuuga"
sys.path[:0] = [ROOT + "/backend"]
from app.indicators.bars import Bar
from app.indicators.order_block import ObConfig, find_blocks, blocked_by_opposing, anchor_stop
from app.indicators.smt import SmtConfig, find_smt, blocked_by_smt
RAW = ROOT + "/backend/app/backtest/data/raw"
ET = ZoneInfo("America/New_York")
SPLIT = "2023-12-31"; TICK, PV, FEE = 0.25, 2.0, 1.0
HIST = 240  # minutes of closed bars used by OB/SMT

def load_bars(p):
    d = pd.read_csv(p); d["t"] = (pd.to_datetime(d.timestamp, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(milliseconds=1)
    return d.set_index("t")[["open", "high", "low", "close"]]
def cands(dirp):
    out = []
    for f in sorted(glob.glob(dirp + "/*.csv.json")):
        mon = f.split("/")[-1][:7]
        for s in json.load(open(f))["signals"]:
            sh = s["features"].get("shadow")
            if not sh or sh["outcome"] != "PASS" or not sh["plan"]: continue
            t = datetime.fromisoformat(s["updated_at"][:19]).replace(tzinfo=ET)
            if str(t.date())[:7] != mon: continue
            p = sh["plan"]
            out.append(dict(t=int(t.timestamp() * 1000), day=str(t.date()), dir=1 if s["direction"] == "LONG" else -1, entry=float(p["entry"]),
                            stop=float(p["stop"]), tp=float(p["take_profit"]), rr=float(p["rr"]), key=s["model_key"], score=float(s["score"] or 0)))
    return sorted(cands_dedupe(out), key=lambda x: x["t"])
def cands_dedupe(c):
    seen = {}
    for x in c: seen.setdefault((x["key"], x["t"]), x)
    return list(seen.values())

class Ctx:
    def __init__(s, mnq, mes):
        s.mnq, s.mes = mnq, mes; s.ix = mnq.index.values; s.cache = {}
        s.eix = set(mes.index.values)
    def bars(s, df, t):  # closed bars: open_ms < t  (bar open + 1 min <= t)
        j = np.searchsorted(df.index.values, t - 60_000, side="right")
        seg = df.iloc[max(0, j - HIST):j]
        return [Bar(int(i), int(i) + 60_000, D(repr(float(o))), D(repr(float(h))), D(repr(float(l))), D(repr(float(c)))) for i, (o, h, l, c) in zip(seg.index, seg.values)]
    def get(s, t):
        if t not in s.cache:
            m = s.bars(s.mnq, t); e = s.bars(s.mes, t)
            ms = {b.open_ms for b in m} & {b.open_ms for b in e}
            s.cache[t] = ([b for b in m if b.open_ms in ms], [b for b in e if b.open_ms in ms])
        return s.cache[t]

def sim(ctx, c, stop):
    """walk 1-min bars from the signal bar; -> pnl $ (1 micro)"""
    e, s, tp = c["entry"], c["dir"], c["tp"]
    j0 = np.searchsorted(ctx.ix, c["t"], side="left")
    end = datetime.fromtimestamp(c["t"] / 1000, ET).replace(hour=15, minute=55, second=0, microsecond=0)
    endms = int(end.timestamp() * 1000)
    df = ctx.mnq
    for j in range(j0, len(ctx.ix)):
        t = ctx.ix[j]; o, h, l, cl = df.iloc[j].values
        if t >= endms: return (cl - s * TICK - e) * s * PV - FEE, t
        if (s > 0 and l <= stop) or (s < 0 and h >= stop):
            px = (min(stop, o) if s > 0 else max(stop, o)) - s * TICK
            return (px - e) * s * PV - FEE, t
        if (s > 0 and h >= tp) or (s < 0 and l <= tp): return (tp - e) * s * PV - FEE, t
    return 0.0, c["t"]

def run(ctx, C, spec, rr_min=1.75, rr_max=3.0, maxday=3):
    out = []; busy = 0; per = {}
    for c in C:
        if not (rr_min <= c["rr"] <= rr_max) or c["t"] < busy or per.get(c["day"], 0) >= maxday: continue
        m, e = ctx.get(c["t"]); s = c["dir"]; price = D(repr(c["entry"]))
        if spec.get("ob"):
            tf, body, swing, dist = spec["ob"]
            if blocked_by_opposing(s, price, find_blocks(agg(m, tf), ObConfig(body_atr=D(str(body)), swing_bars=swing)), D(str(dist))): continue
        if spec.get("smt") and len(m) > spec["smt"][0] + 2:
            look, valid = spec["smt"]; cf = SmtConfig(look, valid)
            if blocked_by_smt(s, find_smt(m, e, cf), len(m) - 1, cf): continue
        stop = c["stop"]
        if spec.get("anchor"):
            tf, body, swing, buf = spec["anchor"]
            r = anchor_stop(s, price, D(repr(stop)), find_blocks(agg(m, tf), ObConfig(body_atr=D(str(body)), swing_bars=swing)), D(str(buf)), D("0.25"))
            ns = float(r); rr = abs(c["tp"] - c["entry"]) / abs(c["entry"] - ns) if ns != c["entry"] else 99
            if ns != stop and rr_min <= rr <= rr_max: stop = ns
        p, tend = sim(ctx, c, stop); busy = tend; per[c["day"]] = per.get(c["day"], 0) + 1
        out.append((c["day"], p))
    return pd.DataFrame(out, columns=["date", "pnl"])

def agg(bars, n):
    if n == 1: return bars
    out = []
    for i in range(0, len(bars) - n + 1, n):
        g = bars[i:i + n]; out.append(Bar(g[0].open_ms, g[-1].close_ms, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
    return out

def stats(t):
    if len(t) == 0: return dict(n=0, win=0.0, pf=0.0, usd=0.0)
    w = t.pnl > 0
    return dict(n=len(t), win=round(w.mean() * 100, 2), pf=round(t.pnl[w].sum() / max(-t.pnl[~w].sum(), 1e-9), 2), usd=round(t.pnl.sum(), 0))
def halves(t): return stats(t[t.date <= SPLIT]), stats(t[t.date > SPLIT])
