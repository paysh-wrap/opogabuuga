"""1-year comparison on real MNQ 1m bars (Databento MNQ.v.0): NOISE (verified baseline) vs the next three strategies.

usage: one_year_compare.py MNQ_1M.csv [START=2025-11-03]   (the CSV may start earlier: 14-day lookback warm-up)
Same cost model as session 9 (1 micro, $2/pt, $1.00 fee RT + 1 tick slippage on entry and market/stop exits, limit
targets no slippage, stop first when stop and target share a 1-minute bar, flat 16:00, roll guard |gap| > 1.5%).
Strategies (rules fixed a priori, none tuned on this year):
  NOISE       noise_area.py defaults (hourly checks, 1% emergency stop, max 3/day)
  OPEN_DRIVE  app D55 button: 09:59 drive >= 0.35 x 14d avg range -> limit at 38.2% retrace, stop 78.6%, target = drive
              extreme, expires 12:30, time stop 13:00
  ORB15       15-min opening range; first 1-min close beyond it (k>=15, until 14:00) -> next open; stop = opposite
              side of the range; target 1.5R; one trade/day
  LHH         last-half-hour momentum (Gao et al. 2018): sign(09:59 close - prior close) -> enter 15:30 open, exit 16:00
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/docs/", 1)[0] + "/docs/results/tools")
import noise_area as NA  # noqa: E402

PV, TICK, FEE = 2.0, 0.25, 1.0


def open_drive(days, i):
    d, a = days[i]
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    pc = days[i - 1][1]["close"][389]
    if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015:
        return None
    rngs = [np.nanmax(x["high"]) - np.nanmin(x["low"]) for _, x in days[max(0, i - 14):i]]
    if len(rngs) < 10:
        return None
    move = c[29] - o[0]
    if move == 0 or abs(move) < 0.35 * np.mean(rngs):
        return None
    s = 1 if move > 0 else -1
    ext = np.nanmax(h[:30]) if s > 0 else np.nanmin(l[:30])
    leg = abs(ext - o[0])
    entry = ext - s * 0.382 * leg
    stop = ext - s * 0.786 * leg
    tgt = ext
    fill = None
    for k in range(30, 181):  # resting limit works until the bar opening 12:30
        if (s > 0 and l[k] <= entry - TICK) or (s < 0 and h[k] >= entry + TICK):
            fill = k
            break
    if fill is None:
        return None
    for k in range(fill, 210):
        if (s > 0 and l[k] <= stop) or (s < 0 and h[k] >= stop):
            return d, s, entry, stop - s * TICK, (stop - s * TICK - entry) * s * PV - FEE
        if (s > 0 and h[k] >= tgt) or (s < 0 and l[k] <= tgt):
            return d, s, entry, tgt, (tgt - entry) * s * PV - FEE
    px = c[209] - s * TICK  # 13:00 time stop
    return d, s, entry, px, (px - entry) * s * PV - FEE


def orb15(days, i):
    d, a = days[i]
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    pc = days[i - 1][1]["close"][389]
    if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015:
        return None
    oh, ol = np.nanmax(h[:15]), np.nanmin(l[:15])
    for k in range(15, 270):
        s = 1 if c[k] > oh else (-1 if c[k] < ol else 0)
        if not s:
            continue
        e = o[k + 1] + s * TICK
        stop = ol if s > 0 else oh
        risk = (e - stop) * s
        if risk < 8 * TICK:
            return None
        tgt = e + s * 1.5 * risk
        for j in range(k + 1, 390):
            if (s > 0 and l[j] <= stop) or (s < 0 and h[j] >= stop):
                px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK
                return d, s, e, px, (px - e) * s * PV - FEE
            if (s > 0 and h[j] >= tgt) or (s < 0 and l[j] <= tgt):
                return d, s, e, tgt, (tgt - e) * s * PV - FEE
        px = c[389] - s * TICK
        return d, s, e, px, (px - e) * s * PV - FEE
    return None


def lhh(days, i):
    d, a = days[i]
    o, c = a["open"], a["close"]
    pc = days[i - 1][1]["close"][389]
    if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015:
        return None
    r = c[29] - pc
    if r == 0:
        return None
    s = 1 if r > 0 else -1
    e = o[360] + s * TICK
    px = c[389] - s * TICK
    return d, s, e, px, (px - e) * s * PV - FEE


def stats(t, label):
    if len(t) == 0:
        return f"{label:11s} no trades"
    w = t.pnl > 0
    eq = t.pnl.cumsum()
    gl = -t.pnl[~w].sum()
    return (f"{label:11s} n={len(t):4d} win={w.mean():5.1%} avg$={t.pnl.mean():7.2f} total$={t.pnl.sum():8.0f} "
            f"PF={t.pnl[w].sum() / gl if gl else float('inf'):4.2f} maxDD$={(eq - eq.cummax()).min():6.0f} "
            f"worst trade={t.pnl.min():5.0f} worst day={t.groupby('d').pnl.sum().min():5.0f}")


if __name__ == "__main__":
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-11-03"
    days = NA.load_days(sys.argv[1])
    res = {"NOISE": NA.run(days, 14, 60, 0.01, 3)}
    for name, fn in (("OPEN_DRIVE", open_drive), ("ORB15", orb15), ("LHH", lhh)):
        rows = [r for i in range(14, len(days)) if (r := fn(days, i))]
        res[name] = pd.DataFrame(rows, columns=["d", "side", "entry", "exit", "pnl"])
    nd = sum(1 for d, _ in days if d >= start)
    print(f"MNQ 1 micro, {start} → {days[-1][0]} ({nd} sessions)")
    for name, t in res.items():
        t = t[pd.to_datetime(t.d) >= start]
        print(stats(t, name), f"| trades/wk {len(t) / nd * 5:.1f}")
        t.to_csv(f"{name.lower()}_1y_trades.csv", index=False)
