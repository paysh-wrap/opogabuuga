"""Screen well-known open-source TradingView indicators as extra filters on the strategy's own setups.

Input: research.py export (every PASS setup). For each filled setup the bracket is re-simulated with a FIXED
target of K·R (default 1.75R, user's minimum R:R) — same fills as screen.py: limit at the plan entry, 4-bar timeout,
stop-first on ambiguous bars, 1-tick stop slip, fees, flat 16:40 ET. Indicator values use ONLY bars closed before
the entry bar (no lookahead). Train = older 70% of sessions, test = newest 30%.

Indicators (math re-implemented from the public formulas; no protected code):
  VWAP (session, built-in) · EMA 50/200 (built-in) · Supertrend 10/3 (built-in / KivancOzbilgic) ·
  ADX/DMI 14 (built-in) · RSI 14 (built-in) · Squeeze Momentum [LazyBear] · WaveTrend [LazyBear] ·
  UT Bot Alerts [QuantNomad] · Chandelier Exit [everget] · Relative volume.

usage: indscreen.py RES.json CSV TICK TICK_VALUE FEE_RT [K=1.75] [train=0.7]"""
import bisect
import json
import sys
from datetime import UTC, datetime, time
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
from app.backtest.data import load_csv  # noqa: E402
from app.clock import session_date  # noqa: E402

ET = ZoneInfo("America/New_York")
res = json.load(open(sys.argv[1]))
bars = load_csv(Path(sys.argv[2]).read_text())
TICK, TV, FEE = D(sys.argv[3]), D(sys.argv[4]), D(sys.argv[5])
K = float(sys.argv[6]) if len(sys.argv) > 6 else 1.75
TRAIN = float(sys.argv[7]) if len(sys.argv) > 7 else 0.7
FLAT = time(16, 40)
opens = np.array([b.open_ms for b in bars], dtype=np.int64)
O = np.array([float(b.o) for b in bars]); H = np.array([float(b.h) for b in bars])
L = np.array([float(b.l) for b in bars]); C = np.array([float(b.c) for b in bars])
V = np.array([float(getattr(b, "v", 0) or 0) for b in bars])


def resample(minutes):
    """OHLCV bars of `minutes` built from 1m bars; returns arrays + each bar's CLOSE time (ms)."""
    key = opens // (minutes * 60_000)
    idx = np.flatnonzero(np.diff(key)) + 1
    starts = np.concatenate([[0], idx]); ends = np.concatenate([idx, [len(key)]])
    o = O[starts]; c = C[ends - 1]
    h = np.maximum.reduceat(H, starts); lo = np.minimum.reduceat(L, starts); v = np.add.reduceat(V, starts)
    close_ms = (key[starts] + 1) * minutes * 60_000
    return {"o": o, "h": h, "l": lo, "c": c, "v": v, "t": close_ms}


def ema(x, n):
    a = 2 / (n + 1); out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rma(x, n):
    a = 1 / n; out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def sma(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0)); out = np.full_like(x, np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def tr(b):
    pc = np.roll(b["c"], 1); pc[0] = b["c"][0]
    return np.maximum(b["h"] - b["l"], np.maximum(abs(b["h"] - pc), abs(b["l"] - pc)))


def supertrend(b, n=10, m=3.0):
    atr = rma(tr(b), n); hl2 = (b["h"] + b["l"]) / 2
    up = hl2 - m * atr; dn = hl2 + m * atr; d = np.ones(len(hl2)); fu, fd = up.copy(), dn.copy()
    for i in range(1, len(hl2)):
        fu[i] = max(up[i], fu[i - 1]) if b["c"][i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if b["c"][i - 1] < fd[i - 1] else dn[i]
        d[i] = 1 if b["c"][i] > fd[i - 1] else -1 if b["c"][i] < fu[i - 1] else d[i - 1]
    return d


def adx(b, n=14):
    h, lo = b["h"], b["l"]
    up = np.diff(h, prepend=h[0]); dn = -np.diff(lo, prepend=lo[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = rma(tr(b), n) + 1e-12
    pdi = 100 * rma(pdm, n) / atr; ndi = 100 * rma(ndm, n) / atr
    dx = 100 * abs(pdi - ndi) / (pdi + ndi + 1e-12)
    return rma(dx, n), pdi, ndi


def rsi(x, n=14):
    d = np.diff(x, prepend=x[0]); g = rma(np.maximum(d, 0), n); lo = rma(np.maximum(-d, 0), n)
    return 100 - 100 / (1 + g / (lo + 1e-12))


def linreg_last(y, n):
    """Pine ta.linreg(y, n, 0): value of the least-squares line at the newest bar of each window."""
    out = np.full_like(y, np.nan); xs = np.arange(n); xm = xs.mean(); den = ((xs - xm) ** 2).sum()
    for i in range(n - 1, len(y)):
        w = y[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        slope = ((xs - xm) * (w - w.mean())).sum() / den
        out[i] = w.mean() + slope * (n - 1 - xm)
    return out


def squeeze(b, n=20, mult_bb=2.0, mult_kc=1.5):
    c = b["c"]; basis = sma(c, n)
    dev = np.array([np.std(c[max(0, i - n + 1):i + 1]) for i in range(len(c))]) * mult_bb
    rng = sma(tr(b), n) * mult_kc
    sq_on = (basis - dev > basis - rng) & (basis + dev < basis + rng)
    hh = np.array([b["h"][max(0, i - n + 1):i + 1].max() for i in range(len(c))])
    ll = np.array([b["l"][max(0, i - n + 1):i + 1].min() for i in range(len(c))])
    val = linreg_last(c - ((hh + ll) / 2 + basis) / 2, n)
    return val, sq_on


def wavetrend(b, n1=10, n2=21):
    ap = (b["h"] + b["l"] + b["c"]) / 3; esa = ema(ap, n1); d = ema(abs(ap - esa), n1)
    ci = (ap - esa) / (0.015 * d + 1e-12); wt1 = ema(ci, n2); wt2 = sma(wt1, 4)
    return wt1, wt2


def utbot(b, key=1.0, n=10):
    atr = rma(tr(b), n); c = b["c"]; stop = np.zeros(len(c)); d = np.zeros(len(c))
    for i in range(1, len(c)):
        loss = key * atr[i]; p = stop[i - 1]
        if c[i] > p and c[i - 1] > p:
            stop[i] = max(p, c[i] - loss)
        elif c[i] < p and c[i - 1] < p:
            stop[i] = min(p, c[i] + loss)
        else:
            stop[i] = c[i] - loss if c[i] > p else c[i] + loss
        d[i] = 1 if c[i] > stop[i] else -1
    return d


def chandelier(b, n=22, m=3.0):
    atr = rma(tr(b), n) * m; c = b["c"]; d = np.ones(len(c))
    hh = np.array([c[max(0, i - n + 1):i + 1].max() for i in range(len(c))])
    ll = np.array([c[max(0, i - n + 1):i + 1].min() for i in range(len(c))])
    ls, ss = hh - atr, ll + atr
    for i in range(1, len(c)):
        ls[i] = max(ls[i], ls[i - 1]) if c[i - 1] > ls[i - 1] else ls[i]
        ss[i] = min(ss[i], ss[i - 1]) if c[i - 1] < ss[i - 1] else ss[i]
        d[i] = 1 if c[i] > ss[i - 1] else -1 if c[i] < ls[i - 1] else d[i - 1]
    return d


TF = {m: resample(m) for m in (5, 15, 60)}
IND = {}
for m, b in TF.items():
    IND[m] = {"ema50": ema(b["c"], 50), "ema200": ema(b["c"], 200), "st": supertrend(b), "rsi": rsi(b["c"]),
              "ut": utbot(b), "ce": chandelier(b), "rvol": b["v"] / (sma(b["v"], 20) + 1e-12)}
    IND[m]["adx"], IND[m]["pdi"], IND[m]["ndi"] = adx(b)
    IND[m]["sqz"], IND[m]["sqz_on"] = squeeze(b)
    IND[m]["wt1"], IND[m]["wt2"] = wavetrend(b)

# session VWAP on 1m (session starts 18:00 ET)
sess_key = np.array([session_date(datetime.fromtimestamp(t / 1000, tz=UTC)).toordinal() for t in opens[::1]])
tp_ = (H + L + C) / 3; pv = tp_ * np.maximum(V, 1e-9); vv = np.maximum(V, 1e-9)
VW = np.empty_like(C); acc_pv = acc_v = 0.0
for i in range(len(C)):
    if i == 0 or sess_key[i] != sess_key[i - 1]:
        acc_pv = acc_v = 0.0
    acc_pv += pv[i]; acc_v += vv[i]; VW[i] = acc_pv / acc_v


def at(m, ms):
    """Index of the newest `m`-minute bar CLOSED at or before ms."""
    return bisect.bisect_right(TF[m]["t"], ms) - 1


def ts(s):
    d = datetime.fromisoformat(str(s).replace(" ", "T"))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def simulate(c):
    p = next((x for x in c["plans"] if x["mode"] == "STANDARD"), None)
    if p is None:
        return None
    d = 1 if p["direction"] == "LONG" else -1
    entry, stop, risk = D(p["entry"]), D(p["stop"]), D(p["risk_pts"])
    tp = entry + d * D(str(K)) * risk
    t0 = ts(c["entry_bar_time"] or c["bar_time"]); t0ms = int(t0.timestamp() * 1000)
    tf = 5 if c["profile"] == "STD" else 1
    i = bisect.bisect_left(opens, t0ms); deadline = t0ms + 4 * tf * 60_000; fill = None
    while i < len(bars) and bars[i].open_ms < deadline:
        if (d == 1 and bars[i].l <= entry) or (d == -1 and bars[i].h >= entry):
            fill = i
            break
        i += 1
    if fill is None:
        return None
    fee_r = float(FEE / (risk / TICK * TV)); slip_r = float(TICK / risk)
    for j in range(fill, len(bars)):
        b = bars[j]
        if j > fill and datetime.fromtimestamp(b.open_ms / 1000, tz=UTC).astimezone(ET).time() >= FLAT:
            r = float((b.o - entry) * d / risk) - fee_r
            return {"r": r, "win": r > 0, "t0ms": t0ms, "d": d}
        if (d == 1 and b.l <= stop) or (d == -1 and b.h >= stop):
            return {"r": -1 - slip_r - fee_r, "win": False, "t0ms": t0ms, "d": d}
        if j > fill and ((d == 1 and b.h >= tp) or (d == -1 and b.l <= tp)):
            return {"r": K - fee_r, "win": True, "t0ms": t0ms, "d": d}
    return None


def path(c):
    """Full path after the fill (session 8): max favourable excursion in R on bars AFTER the fill bar and BEFORE the
    stop bar (stop-first, same as simulate), whether the stop was hit before 16:40, R at the 16:40 flat otherwise.
    Lets any target K (or min(T2, cap)) be scored without re-simulating: win if mfe >= K."""
    p = next((x for x in c["plans"] if x["mode"] == "STANDARD"), None)
    if p is None:
        return None
    d = 1 if p["direction"] == "LONG" else -1
    entry, stop, risk = D(p["entry"]), D(p["stop"]), D(p["risk_pts"])
    t0 = ts(c["entry_bar_time"] or c["bar_time"]); t0ms = int(t0.timestamp() * 1000)
    tf = 5 if c["profile"] == "STD" else 1
    i = bisect.bisect_left(opens, t0ms); deadline = t0ms + 4 * tf * 60_000; fill = None
    while i < len(bars) and bars[i].open_ms < deadline:
        if (d == 1 and bars[i].l <= entry) or (d == -1 and bars[i].h >= entry):
            fill = i
            break
        i += 1
    if fill is None:
        return None
    t2 = (c.get("features") or {}).get("t2")
    out = {"fee_r": float(FEE / (risk / TICK * TV)), "slip_r": float(TICK / risk), "mfe": 0.0, "stopped": False,
           "flat_r": None, "t2rr": float((D(str(t2)) - entry) * d / risk) if t2 is not None else None}
    for j in range(fill, len(bars)):
        b = bars[j]
        if j > fill and datetime.fromtimestamp(b.open_ms / 1000, tz=UTC).astimezone(ET).time() >= FLAT:
            out["flat_r"] = float((b.o - entry) * d / risk)
            return out
        if (d == 1 and b.l <= stop) or (d == -1 and b.h >= stop):
            out["stopped"] = True
            return out
        if j > fill:
            out["mfe"] = max(out["mfe"], float(((b.h if d == 1 else b.l) - entry) * d / risk))
    return out


rows = []
for c in res["signals"]:
    if c["status"] != "PASS" or not c["plans"]:
        continue
    o = simulate(c)
    if not o:
        continue
    pth = path(c)
    if pth:
        o = {**o, **pth}
    ms, d = o["t0ms"], o["d"]
    f = c["features"]; x = {"sess": session_date(ts(c["entry_bar_time"] or c["bar_time"])).isoformat(), **o,
                            "brk": bool(f.get("choch")) or bool(f.get("bos")), "profile": c["profile"]}
    # engine-side fields (session 8): what the live plan's settings can filter on directly
    p0 = next(p for p in c["plans"] if p["mode"] == "STANDARD")
    si, tg = f.get("score_items") or {}, f.get("tags") or {}
    g4 = (c.get("gates") or {}).get("G4") or {}
    x.update({"sid": c["id"], "score": float(c["score"] or 0), "c1atr": float(c["c1_range_atr"] or 0),
              "plan_rr": float(p0["rr"]), "risk_ticks": float(D(p0["risk_pts"]) / TICK),
              "choch": bool(f.get("choch")), "bos": bool(f.get("bos")),
              "cisd": float(si.get("cisd_before_c2_close") or 0) > 0, "osc": float(si.get("osc_strength") or 0) > 0,
              "htf": float(si.get("htf_mso_agrees") or 0) > 0, "mso": "disagrees" not in str(g4.get("detail", "")),
              "weekday": tg.get("weekday"), "slice": tg.get("slice"), "atr_pct": float(tg.get("atr_pct") or -1)})
    for k, v in (f.get("trend") or {}).items():  # D44: what the ENGINE's own trend switches saw (live code path)
        x[f"eng_{k}"] = (v == d) if v is not None else None
    i1 = bisect.bisect_left(opens, ms) - 1  # newest 1m bar closed before the entry bar
    x["vwap"] = d * (C[i1] - VW[i1]) > 0
    for m in (5, 15, 60):
        k = at(m, ms)
        if k < 210:
            x[f"warm{m}"] = False
            continue
        g = IND[m]; cl = TF[m]["c"][k]
        x[f"ema50_{m}"] = d * (cl - g["ema50"][k]) > 0
        x[f"ema200_{m}"] = d * (cl - g["ema200"][k]) > 0
        x[f"st_{m}"] = g["st"][k] == d
        x[f"ut_{m}"] = g["ut"][k] == d
        x[f"ce_{m}"] = g["ce"][k] == d
        x[f"adx20_{m}"] = g["adx"][k] >= 20
        x[f"adx25_{m}"] = g["adx"][k] >= 25
        x[f"adx<20_{m}"] = g["adx"][k] < 20
        x[f"dmi_{m}"] = d * (g["pdi"][k] - g["ndi"][k]) > 0
        x[f"rsi_side_{m}"] = d * (g["rsi"][k] - 50) > 0
        x[f"rsi_notext_{m}"] = (g["rsi"][k] < 70) if d == 1 else (g["rsi"][k] > 30)
        x[f"sqz_mom_{m}"] = d * g["sqz"][k] > 0
        x[f"sqz_rising_{m}"] = d * (g["sqz"][k] - g["sqz"][k - 1]) > 0
        x[f"sqz_off_{m}"] = not g["sqz_on"][k]
        x[f"wt_cross_{m}"] = d * (g["wt1"][k] - g["wt2"][k]) > 0
        x[f"wt_ext_{m}"] = (g["wt1"][k] < -53) if d == 1 else (g["wt1"][k] > 53)
        x[f"wt_notext_{m}"] = (g["wt1"][k] < 53) if d == 1 else (g["wt1"][k] > -53)
        x[f"rvol>1_{m}"] = g["rvol"][k] > 1
    if "sqz_rising_5" in x and "sqz_rising_15" in x:
        x["sqz_5_15"] = bool(x["sqz_rising_5"] and x["sqz_rising_15"])  # = engine switch squeeze_5m_15m (D45)
    rows.append(x)

import os
if os.environ.get("DUMP_ROWS"):  # per-setup rows for deeper combo searches (session 8)
    json.dump([{k: (bool(v) if isinstance(v, (bool, np.bool_)) else v) for k, v in r.items()} for r in rows],
              open(os.environ["DUMP_ROWS"], "w"), default=str)
for own, eng in (("vwap", "eng_vwap"), ("ema200_5", "eng_ema200_5m"), ("ut_5", "eng_utbot_5m"),
                 ("sqz_5_15", "eng_squeeze_5m_15m")):
    both = [r for r in rows if r.get(eng) is not None and own in r]
    if both:
        agree = sum(r[own] == r[eng] for r in both) / len(both)
        print(f"parity {own:9s} vs engine {eng:14s}: {agree:5.1%} agree over {len(both)} setups")
days = sorted({r["sess"] for r in rows}); cut = days[int(len(days) * TRAIN)]
tr_, te_ = [r for r in rows if r["sess"] < cut], [r for r in rows if r["sess"] >= cut]


def st(rs):
    n = len(rs)
    return (n, sum(r["win"] for r in rs) / n if n else 0, sum(r["r"] for r in rs) / n if n else 0)


def fmt(s):
    return f"{s[0]:4d} tr {s[1]:4.0%} {s[2]:+.2f}R"


keys = sorted({k for r in rows for k, v in r.items() if isinstance(v, (bool, np.bool_)) and k not in ("win",)
               and not k.startswith("warm")})
out = {"K": K, "sessions": len(days), "train_sessions": sum(d < cut for d in days),
       "all": {"train": st(tr_), "test": st(te_)}, "filters": {}}
print(f"{res['symbol']} fixed target {K}R · {len(rows)} filled setups · {len(days)} sessions (train {out['train_sessions']})")
print(f"{'ALL':22s} train {fmt(st(tr_))} | test {fmt(st(te_))}")
lines = []
for k in keys:
    a, b = st([r for r in tr_ if r.get(k)]), st([r for r in te_ if r.get(k)])
    out["filters"][k] = {"train": a, "test": b}
    lines.append((a[1] if a[0] >= 10 else -1, k, a, b))
lines.sort(reverse=True)
for _, k, a, b in lines:
    print(f"{k:22s} train {fmt(a)} | test {fmt(b)}")
pairs = []
for i, k1 in enumerate(keys):
    for k2 in keys[i + 1:]:
        a = st([r for r in tr_ if r.get(k1) and r.get(k2)])
        if a[0] >= max(15, len(tr_) // 10):
            pairs.append((a[1], a[2], k1, k2, a, st([r for r in te_ if r.get(k1) and r.get(k2)])))
pairs.sort(reverse=True)
print("\nbest pairs (train win, ≥10% of setups):")
for w, e, k1, k2, a, b in pairs[:20]:
    print(f"{k1 + ' & ' + k2:40s} train {fmt(a)} | test {fmt(b)}")
out["pairs"] = [{"k": [k1, k2], "train": a, "test": b} for _, _, k1, k2, a, b in pairs[:40]]
# Per-year view (session 8): long data spans regimes (2019 MGC: ~$1,300 gold, thin volume) → check each year.
YK = ["sqz_5_15", "sqz_rising_5", "ut_5", "vwap", "ema200_5"]
years = sorted({str(r["sess"])[:4] for r in rows})
out["by_year"] = {}
print(f"\nby year (fixed {K}R): {'none':>20s} " + " ".join(f"{k:>20s}" for k in YK))
for y in years:
    ry = [r for r in rows if str(r["sess"])[:4] == y]
    cells = {"none": st(ry), **{k: st([r for r in ry if r.get(k)]) for k in YK}}
    out["by_year"][y] = cells
    print(f"{y:12s} " + " ".join(f"{fmt(cells[k]):>20s}" for k in ["none", *YK]))
json.dump(out, open(sys.argv[1].replace(".json", f"_ind{K}.json"), "w"), default=float)
