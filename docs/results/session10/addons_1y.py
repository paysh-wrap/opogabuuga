"""1-year test of two add-ons that never overlap NOISE (one position per account), MNQ 1 micro, same cost model.

usage: addons_1y.py MNQ_1M.csv NOISE_1Y_TRADES.csv   (trades CSV from one_year_compare.py; START 2025-11-03)
Rules fixed a priori (not tuned on this year):
  OVERNIGHT  Asia range 18:00–20:00 ET; first 1m close outside it 20:00–01:59 → next open; stop = other side of the
             range (skip if < 8 ticks or > 0.6% of price); target 1.5R; flat 02:59 (before London). Labeled with the
             next trading day (Lucid's trading day starts 18:00). Max 1/night.
  PM_FADE    only on days with NO NOISE trade: 13:00–15:29, close beyond VWAP ± 2.0 × std(close − VWAP since 09:30)
             → fade toward VWAP at next open; target = VWAP at signal time; stop = 1 band-width beyond entry;
             flat 15:55. Max 1/day.
Combined = NOISE + both add-ons, then the Lucid Pro 25K rolling eval sim (tools/sim25k.py) on the same year."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/docs/", 1)[0] + "/docs/results/tools")
import noise_area as NA  # noqa: E402
import sim25k  # noqa: E402

PV, TICK, FEE, START = 2.0, 0.25, 1.0, "2025-11-03"


def walk(s, e, stop, tgt, H, L, O, C, j0, j1):
    for j in range(j0, j1):
        if (s > 0 and L[j] <= stop) or (s < 0 and H[j] >= stop):
            px = (min(stop, O[j]) if s > 0 else max(stop, O[j])) - s * TICK
            return (px - e) * s * PV - FEE
        if (s > 0 and H[j] >= tgt) or (s < 0 and L[j] <= tgt):
            return (tgt - e) * s * PV - FEE
    return (C[j1 - 1] - s * TICK - e) * s * PV - FEE


def overnight(df):
    out = []
    t = df.index
    mins = t.hour * 60 + t.minute
    shifted = (t + pd.Timedelta(hours=6)).date  # 18:00 ET → next calendar day = trading day label
    df = df.assign(td=shifted, m=mins)
    for td, g in df.groupby("td"):
        if pd.Timestamp(td).weekday() >= 5:
            continue
        g = g[(g.m >= 1080) | (g.m < 179)]  # 18:00 → 02:59
        rng = g[(g.m >= 1080) & (g.m < 1200)]
        if len(rng) < 100:
            continue
        hi, lo = rng.high.max(), rng.low.min()
        w = g[(g.m >= 1200) | (g.m < 179)]
        H, L, O, C = w.high.values, w.low.values, w.open.values, w.close.values
        tm = w.m.values
        for k in range(len(w) - 1):
            if not (tm[k] >= 1200 or tm[k] < 120):
                break
            s = 1 if C[k] > hi else (-1 if C[k] < lo else 0)
            if not s:
                continue
            e = O[k + 1] + s * TICK
            stop = lo if s > 0 else hi
            risk = (e - stop) * s
            if risk < 8 * TICK or risk > 0.006 * e:
                break
            out.append((str(td), walk(s, e, stop, e + s * 1.5 * risk, H, L, O, C, k + 1, len(w))))
            break
    return pd.DataFrame(out, columns=["d", "pnl"])


def pm_fade(days, noise_days):
    out = []
    for d, a in days:
        if d < START or d in noise_days:
            continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):  # bar opening 13:00 .. 15:28
            if np.isnan(c[k]) or np.isnan(vw[k]):
                continue
            dev = c[: k + 1] - vw[: k + 1]
            sd = np.nanstd(dev)
            if sd <= 0:
                continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s:
                continue
            e = o[k + 1] + s * TICK
            tgt = vw[k]
            if (tgt - e) * s < 4 * TICK:
                break
            stop = e - s * 2 * sd
            out.append((d, walk(s, e, stop, tgt, h, l, o, c, k + 1, 386)))
            break
    return pd.DataFrame(out, columns=["d", "pnl"])


def line(t, name, nd):
    w = t.pnl > 0
    eq = t.pnl.cumsum()
    return (f"{name:22s} {len(t):4d} tr  {len(t) / nd:4.2f}/day  win {w.mean():5.1%}  $/tr {t.pnl.mean():7.2f}  "
            f"total ${t.pnl.sum():7.0f}  PF {t.pnl[w].sum() / -t.pnl[~w].sum():4.2f}  maxDD ${(eq - eq.cummax()).min():6.0f}")


if __name__ == "__main__":
    raw = pd.read_csv(sys.argv[1], parse_dates=["timestamp"]).set_index("timestamp")
    raw.index = raw.index.tz_convert("America/New_York")
    days = NA.load_days(sys.argv[1])
    nd = sum(1 for d, _ in days if d >= START)
    noise = pd.read_csv(sys.argv[2])[["d", "pnl"]]
    on = overnight(raw)
    on = on[on.d >= START]
    pm = pm_fade(days, set(noise.d))
    sets = {"NOISE": noise, "OVERNIGHT": on, "PM_FADE": pm, "NOISE+OVERNIGHT": pd.concat([noise, on]),
            "NOISE+PM_FADE": pd.concat([noise, pm]), "NOISE+BOTH": pd.concat([noise, on, pm])}
    print(f"MNQ 1 micro {START} → {days[-1][0]} ({nd} sessions)")
    for name, t in sets.items():
        t = t.sort_values("d", kind="stable").reset_index(drop=True)
        print(line(t, name, nd))
        f = f"addon_{name}.csv"
        t.to_csv(f, index=False)
        sim25k.summary("   Pro 25K", sim25k.run("Pro", f, dll_funded=600, start=START, end="2026-10-30"))
