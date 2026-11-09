"""Noise-area intraday momentum (Zarattini, Aziz & Barbon 2024, "Beat the Market") on MNQ 1-minute bars.
Independent re-implementation used to verify the momentum agent (session 9, 2026-11-09).

usage: noise_area.py MNQ_1M.csv OUT_TRADES.csv [--look 14] [--step 60] [--hard 0.01] [--maxtr 3]
  MNQ_1M.csv = Databento MNQ.v.0 ohlcv-1m (timestamp UTC, open, high, low, close, volume) — see dbget2y.py
Rules (RTH 09:30–16:00 ET):
  sigma_t   = mean over the previous LOOK days of |close_t / open_0930 - 1| for minute-of-day t (no lookahead)
  upper     = max(today's open, prior RTH close) * (1 + sigma_t); lower = min(open, prior close) * (1 - sigma_t)
  every STEP minutes from 10:00 (decision on the close of the bar ending at the check time):
     flat and close > upper -> long; close < lower -> short (fill = next bar open + 1 tick)
     long and close < max(upper, VWAP) -> exit next bar open (short mirrored with min(lower, VWAP))
  optional emergency stop at entry -/+ HARD * entry, checked on every 1-minute bar (stop first, gaps fill at open)
  flat at 16:00 (close of the 15:59 bar); max MAXTR entries per day; days with |open/prior close - 1| > 1.5% skipped
  (contract-roll guard for the unadjusted .v.0 series).
Costs per round trip, 1 micro: $1.00 fee + 1 tick ($0.50) slippage on entry and on every exit. Point value $2."""
import argparse

import numpy as np
import pandas as pd

PV, TICK, FEE = 2.0, 0.25, 1.0


def load_days(csv: str):
    df = pd.read_csv(csv, parse_dates=["timestamp"]).set_index("timestamp")
    df.index = df.index.tz_convert("America/New_York")
    rth = df.between_time("09:30", "15:59")
    days = []
    for d, g in rth.groupby(rth.index.date):
        m = ((g.index.hour - 9) * 60 + g.index.minute - 30).values
        if len(g) < 380 or m[0] != 0:  # half days / data gaps
            continue
        a = {}
        for col in ("open", "high", "low", "close"):
            x = np.full(390, np.nan)
            x[m[m < 390]] = g[col].values[m < 390]
            a[col] = x
        tp = (g.high + g.low + g.close).values / 3
        v = g.volume.values
        vw = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1)
        x = np.full(390, np.nan)
        x[m[m < 390]] = vw[m < 390]
        a["vwap"] = x
        days.append((str(d), a))
    return days


def run(days, look=14, step=60, hard=None, maxtr=3):
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, 360, step))  # bar opening 09:59 closes at 10:00
    out = []
    for i in range(look, len(days)):
        d, a = days[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015:
            continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig)
        lb = min(o[0], pc) * (1 - sig)
        pos = ntr = pending = 0
        entry = hs = None

        def close_trade(px):
            nonlocal pos
            out.append((d, pos, entry, px, (px - entry) * pos * PV - FEE))
            pos = 0

        for k in range(390):
            if np.isnan(c[k]):
                continue
            if pending and pos == 0:
                entry = o[k] + pending * TICK
                pos, pending = pending, 0
                hs = entry - pos * hard * entry if hard else None
            if pos and hs is not None and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                close_trade((min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos * TICK)
            if pos and k == 389:
                close_trade(c[k] - pos * TICK)
            if k in checks:
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK)
                if pos == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        pending, ntr = side, ntr + 1
    return pd.DataFrame(out, columns=["d", "side", "entry", "exit", "pnl"])


def stats(t: pd.DataFrame, label: str) -> str:
    w = t.pnl > 0
    eq = t.pnl.cumsum()
    return (f"{label:14s} n={len(t):4d} win={w.mean():.1%} avg$={t.pnl.mean():6.2f} "
            f"PF={t.pnl[w].sum() / -t.pnl[~w].sum():.2f} maxDD$={(eq - eq.cummax()).min():6.0f} "
            f"worst trade={t.pnl.min():5.0f} worst day={t.groupby('d').pnl.sum().min():5.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--look", type=int, default=14)
    ap.add_argument("--step", type=int, default=60)
    ap.add_argument("--hard", type=float, default=0.01)
    ap.add_argument("--maxtr", type=int, default=3)
    a = ap.parse_args()
    t = run(load_days(a.csv), a.look, a.step, a.hard or None, a.maxtr)
    t.to_csv(a.out, index=False)
    dt = pd.to_datetime(t.d)
    print(stats(t[dt < "2024-01-01"], "IN 2019-2023"))
    print(stats(t[dt >= "2024-01-01"], "HELD 2024-26"))
    for y, g in t.groupby(dt.dt.year):
        print(stats(g, f"  {y}"))
