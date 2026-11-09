"""Generalized noise-area intraday momentum (copy of docs/results/tools/noise_area.py; rules identical).
Parameters: point value, tick, fee RT, session start/end (ET), fixed emergency stop USD per contract."""
import argparse
import numpy as np
import pandas as pd


def load_days(csv, start="09:30", end="16:00", roll_guard=True, ffill=False, min_bars=0.97):
    df = pd.read_csv(csv, parse_dates=["timestamp"]).set_index("timestamp")
    df.index = df.index.tz_convert("America/New_York")
    sh, sm = map(int, start.split(":")); eh, em = map(int, end.split(":"))
    nb = (eh * 60 + em) - (sh * 60 + sm)
    last = pd.Timestamp(2000, 1, 1, eh, em) - pd.Timedelta(minutes=1)
    rth = df.between_time(start, last.strftime("%H:%M"))
    days = []
    for d, g in rth.groupby(rth.index.date):
        if ffill:  # thin markets: a minute with no trade = price unchanged (needs >=50% of minutes traded)
            if len(g) < nb * 0.5:
                continue
            idx = pd.date_range(pd.Timestamp(d, tz=g.index.tz) + pd.Timedelta(minutes=sh * 60 + sm), periods=nb, freq="min")
            c0 = g["close"].reindex(idx).ffill().bfill()
            g2 = pd.DataFrame({"close": c0})
            for col in ("open", "high", "low"):
                g2[col] = g[col].reindex(idx).fillna(g2["close"])
            g2["volume"] = g["volume"].reindex(idx).fillna(0)
            g = g2
        m = ((g.index.hour - sh) * 60 + g.index.minute - sm).values
        if len(g) < nb * min_bars or m[0] != 0:
            continue
        ok = m < nb
        a = {}
        for col in ("open", "high", "low", "close"):
            x = np.full(nb, np.nan); x[m[ok]] = g[col].values[ok]; a[col] = x
        tp = (g.high + g.low + g.close).values / 3
        v = g.volume.values
        vw = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1)
        x = np.full(nb, np.nan); x[m[ok]] = vw[ok]; a["vwap"] = x
        days.append((str(d), a))
    return days, nb


def run(days, nb, pv, tick, fee, stop_usd=250.0, look=14, step=60, maxtr=3, roll=0.015):
    tv = pv * tick
    hard_pts = (stop_usd - fee - 2 * tv) / pv if stop_usd else None  # fixed $ stop in points
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, nb - 30, step))
    out = []
    for i in range(look, len(days)):
        d, a = days[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or abs(o[0] / pc - 1) > roll:
            continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        pos = ntr = pending = 0
        entry = hs = None; et = None

        def close_trade(px, k):
            nonlocal pos
            out.append((d, pos, entry, px, (px - entry) * pos * pv - fee, et, k))
            pos = 0

        for k in range(nb):
            if np.isnan(c[k]):
                continue
            if pending and pos == 0:
                entry = o[k] + pending * tick; et = k
                pos, pending = pending, 0
                hs = entry - pos * hard_pts if hard_pts else None
            if pos and hs is not None and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                close_trade((min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos * tick, k)
            if pos and k == nb - 1:
                close_trade(c[k] - pos * tick, k)
            if k in checks:
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < nb and not np.isnan(o[nk]) else c[k]) - pos * tick, k)
                if pos == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        pending, ntr = side, ntr + 1
    return pd.DataFrame(out, columns=["d", "side", "entry", "exit", "pnl", "ek", "xk"])


def stats(t, label):
    if len(t) == 0:
        return f"{label:14s} n=0"
    w = t.pnl > 0
    eq = t.pnl.cumsum()
    pf = t.pnl[w].sum() / max(-t.pnl[~w].sum(), 1e-9)
    return (f"{label:14s} n={len(t):4d} win={w.mean():.1%} avg$={t.pnl.mean():6.2f} PF={pf:.2f} "
            f"maxDD$={(eq - eq.cummax()).min():6.0f} total$={t.pnl.sum():7.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("out")
    ap.add_argument("--pv", type=float, required=True); ap.add_argument("--tick", type=float, required=True)
    ap.add_argument("--fee", type=float, default=1.0)
    ap.add_argument("--start", default="09:30"); ap.add_argument("--end", default="16:00")
    ap.add_argument("--stop", type=float, default=250.0)
    ap.add_argument("--roll", type=float, default=0.015)
    ap.add_argument("--from", dest="frm", default=None)
    a = ap.parse_args()
    days, nb = load_days(a.csv, a.start, a.end)
    if a.frm: days = [x for x in days if x[0] >= a.frm]
    t = run(days, nb, a.pv, a.tick, a.fee, a.stop, roll=a.roll)
    t.to_csv(a.out, index=False)
    dt = pd.to_datetime(t.d)
    print(stats(t[dt < "2024-01-01"], "IN"), "\n" + stats(t[dt >= "2024-01-01"], "HELD"))
    for y, g in t.groupby(dt.dt.year): print(stats(g, f"  {y}"))
