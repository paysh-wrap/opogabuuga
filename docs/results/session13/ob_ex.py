"""Session 12: order blocks (OB) + SMT (MNQ vs MES) on NOISE + PM fade, MNQ 1 micro, 2021-11 -> 2026-10.
Uses the REAL indicator code (backend/app/indicators/order_block.py, smt.py) on closed 1-minute bars (OB also on 5-minute bars).
Baseline trade generation = docs/results/session11/final_push/winrate_study.py (noise_t / pm_fade), copied with two hooks:
  veto(d, k, s)            -> True blocks the entry decided on the close of bar k   (FILTER role; can only remove trades)
  anchor(d, k, s, entry)   -> stop price (ANCHOR role; only used when tighter than the fixed 124-pt stop)
A vetoed NOISE entry consumes the day's entry (no replacement trade); the fade's 'NOISE day' set always comes from the
UNFILTERED baseline, so a filter never adds a trade. Pick on 2021-11..2023-12, judge on 2024-01..2026-10."""
import sys, pickle, os, itertools, json
from decimal import Decimal as D
import numpy as np, pandas as pd
ROOT = "/home/user/opogabuuga"
sys.path[:0] = [ROOT + "/backend", ROOT + "/docs/results/session10/five_year"]
import noise_gen as NG
from app.indicators.bars import Bar
from app.indicators.order_block import ObConfig, find_blocks, blocked_by_opposing, anchor_stop
from app.indicators.smt import SmtConfig, find_smt, blocked_by_smt
RAW = ROOT + "/backend/app/backtest/data/raw"
HERE = ROOT + "/docs/results/session12"
START, END, SPLIT = "2021-11-01", "2026-10-30", "2023-12-31"
PV, TICK, FEE, PTS = 2.0, 0.25, 1.0, 124.0
M = 60_000

def hm(k): return f"{9 + (30 + k) // 60:02d}:{(30 + k) % 60:02d}"

def load():
    c = HERE + "/days.pkl"
    if os.path.exists(c): return pickle.load(open(c, "rb"))
    a, _ = NG.load_days(RAW + "/mnq_5y.csv"); b, _ = NG.load_days(RAW + "/mes_5y.csv")
    r = (a, dict(b)); pickle.dump(r, open(c, "wb")); return r

class DayBars:
    """Decimal Bar lists of one day for MNQ and MES (NaN minutes -> flat bar at previous close). Index = minute k."""
    def __init__(self, a, bm):
        self.m = self._mk(a); self.e = self._mk(bm) if bm is not None else None
        self.cache = {}
    @staticmethod
    def _mk(a):
        out = []; pc = None
        for k in range(390):
            o, h, l, c = (a[x][k] for x in ("open", "high", "low", "close"))
            if np.isnan(c):
                if pc is None: pc = a["open"][0]
                o = h = l = c = pc
            pc = c
            out.append(Bar(k * M, (k + 1) * M, D(repr(float(o))), D(repr(float(h))), D(repr(float(l))), D(repr(float(c)))))
        return out
    @staticmethod
    def agg(bars, n):
        out = []
        for i in range(0, len(bars) - n + 1, n):
            g = bars[i:i + n]
            out.append(Bar(g[0].open_ms, g[-1].close_ms, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
        return out
    def blocks(self, k, tf, cfg):
        """OBs alive after the CLOSE of bar k (only closed bars: for tf>1 only whole tf-bars ending <= k+1)."""
        key = (k, tf, cfg)
        if key not in self.cache:
            n = (k + 1) // tf
            bars = self.m[:k + 1] if tf == 1 else self.agg(self.m[:n * tf], tf)
            self.cache[key] = find_blocks(bars, cfg)
        return self.cache[key]

def mk_hooks(bars_by_day, spec):
    """spec: dict(ob=(tf, body, swing, dist_pts) or None, smt=(look, valid) or None, anchor=(tf, body, swing, buf_pts) or None)"""
    def veto(d, k, s, price):
        db = bars_by_day[d]
        if spec.get("ob"):
            tf, body, swing, dist = spec["ob"]
            cfg = ObConfig(body_atr=D(str(body)), swing_bars=swing)
            if blocked_by_opposing(s, D(repr(float(price))), db.blocks(k, tf, cfg), D(str(dist))): return True
        if spec.get("smt") and db.e is not None:
            look, valid = spec["smt"]; cfg = SmtConfig(look, valid)
            key = ("smt", k, cfg)
            if key not in db.cache:
                sg = find_smt(db.m[:k + 1], db.e[:k + 1], cfg); db.cache[key] = sg
            if blocked_by_smt(s, db.cache[key], k, cfg): return True
        return False
    def anchor(d, k, s, entry):
        if not spec.get("anchor"): return None
        tf, body, swing, buf = spec["anchor"]
        db = bars_by_day[d]; cfg = ObConfig(body_atr=D(str(body)), swing_bars=swing)
        e = D(repr(float(entry))); stop = e - s * D(str(PTS))
        r = anchor_stop(s, e, stop, db.blocks(k, tf, cfg), D(str(buf)), D("0.25"))
        return float(r) if r != stop else None
    return veto, anchor

def noise_t(days, veto=None, anchor=None, look=14, maxtr=3, step=60):
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, 360, step)); out = []; last = {}
    for i in range(look, len(days)):
        d, a = days[i]
        if d < START or d > END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0); ntr = pending = 0; pk = None
        def close_trade(px, k):
            out.append((d, (px - st["entry"]) * st["pos"] * PV - FEE, "NOISE", hm(st["ek"]), st["ek"], k)); st["pos"] = 0; last[d] = k
        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                e = o[k] + pending * TICK
                hs = e - pending * PTS
                if anchor:
                    x = anchor(d, pk, pending, e)
                    if x is not None: hs = x
                st.update(entry=e, pos=pending, ek=k, hs=hs); pending = 0
            pos = st["pos"]
            if pos and ((pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"])):
                close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * TICK, k)
            if st["pos"] and k == 389: close_trade(c[k] - st["pos"] * TICK, k)
            if k in checks:
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK, nk)
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        ntr += 1
                        if not (veto and veto(d, k, side, c[k])): pending, pk = side, k
    return out

def walk(s, e, stop, tgt, H, L, O, C, j0, j1):
    for j in range(j0, j1):
        if (s > 0 and L[j] <= stop) or (s < 0 and H[j] >= stop):
            return ((min(stop, O[j]) if s > 0 else max(stop, O[j])) - s * TICK - e) * s * PV - FEE, j
        if (s > 0 and H[j] >= tgt) or (s < 0 and L[j] <= tgt): return (tgt - e) * s * PV - FEE, j
    return (C[j1 - 1] - s * TICK - e) * s * PV - FEE, j1 - 1

def pm_fade(days, noise_days, veto=None, anchor=None, band=2.0, k0=210, k1=359):
    out = []
    for d, a in days:
        if d < START or d > END or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(k0, k1):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + band * sd else (1 if c[k] < vw[k] - band * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK
            if (vw[k] - e) * s < 4 * TICK: break
            if veto and veto(d, k, s, c[k]): break      # day's single fade consumed
            stop = e - s * PTS
            if anchor:
                x = anchor(d, k, s, e)
                if x is not None: stop = x
            out.append((d, walk(s, e, stop, vw[k], h, l, o, c, k + 1, 386), "FADE", hm(k + 1))); break
    return out

def stats(t):
    if len(t) == 0: return dict(n=0, win=0.0, pf=0.0, usd=0.0, dd=0.0)
    w = t.pnl > 0; dly = t.groupby("date").pnl.sum(); eq = dly.cumsum()
    return dict(n=len(t), win=w.mean() * 100, pf=t.pnl[w].sum() / max(-t.pnl[~w].sum(), 1e-9), usd=t.pnl.sum(),
                dd=(eq.cummax().clip(lower=0) - eq).max())

def build(days, base_noise_days, vN=None, aN=None, vF=None, aF=None):
    nt = noise_t(days, vN, aN)
    ft = pm_fade(days, base_noise_days, vF, aF)
    return pd.DataFrame(nt + ft, columns=["date", "pnl", "strategy", "entry_time"])

def halves(t): return stats(t[t.date <= SPLIT]), stats(t[t.date > SPLIT])
