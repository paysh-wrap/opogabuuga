"""Rebuild backend/app/backtest/data/main_strategy_5y.csv = MAIN strategy (NOISE $250 fixed 124-pt stop + PM fade, fixed
124-pt stop, 1 micro MNQ, 2021-11-01 -> 2026-10-30), same rules as docs/results/session10/five_year/stops_250.py
("NOISE $250 + fade fixed $250"). Raw Databento MNQ.v.0 1m bars are cached in backend/app/backtest/data/raw/ (reused).
usage: rebuild_main_csv.py   (needs curl + proxy-injected Databento credentials; dummy key is fine)"""
import os, subprocess, sys
import numpy as np, pandas as pd

ROOT = "/home/user/opogabuuga"
RAW = f"{ROOT}/backend/app/backtest/data/raw"
OUT = f"{ROOT}/backend/app/backtest/data/main_strategy_5y.csv"
MNQ = f"{RAW}/mnq_5y.csv"
START, END = "2021-11-01", "2026-10-30"
PV, TICK, FEE, PTS = 2.0, 0.25, 1.0, (250 - 2) / 2
sys.path[:0] = [ROOT + "/docs/results/session10/five_year"]


def download():
    if os.path.exists(MNQ):
        return
    os.makedirs(RAW, exist_ok=True)
    parts = []
    spans = [(f"{y}-{m:02d}-01", f"{y + (m + 2) // 12}-{(m + 2) % 12 + 1:02d}-01")
             for y in range(2021, 2027) for m in (1, 4, 7, 10)]
    spans = [(a, b) for a, b in spans if "2021-09-01" <= a <= "2026-10-31"]
    spans[-1] = (spans[-1][0], "2026-11-01")
    for a, b in spans:
        f = f"{RAW}/mnq_v0_{a}.csv"
        if not os.path.exists(f) or os.path.getsize(f) < 100:
            subprocess.run(["curl", "-sS", "--fail", "--retry", "4", "-u", "db-dummy:", "-o", f,
                            "https://hist.databento.com/v0/timeseries.get_range",
                            "-d", "dataset=GLBX.MDP3", "-d", "symbols=MNQ.v.0", "-d", "stype_in=continuous",
                            "-d", "schema=ohlcv-1m", "-d", f"start={a}", "-d", f"end={b}", "-d", "encoding=csv",
                            "-d", "pretty_px=true", "-d", "pretty_ts=true", "-d", "map_symbols=false"], check=True)
        d = pd.read_csv(f)
        print(a, len(d), flush=True)
        parts.append(d)
    d = pd.concat(parts).drop_duplicates("ts_event").sort_values("ts_event")
    d = d.rename(columns={"ts_event": "timestamp"})
    d["timestamp"] = pd.to_datetime(d.timestamp).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    d[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(MNQ, index=False)


def noise_t(days, hard_pts, look=14, step=60, maxtr=3):
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, 360, step)); out = []
    for i in range(look, len(days)):
        d, a = days[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=None); ntr = pending = 0; hs = None
        def close_trade(px):
            out.append((d, (px - st["entry"]) * st["pos"] * PV - FEE)); st["pos"] = 0
        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                st["entry"] = o[k] + pending * TICK; st["pos"], pending = pending, 0
                hs = st["entry"] - st["pos"] * hard_pts
            pos = st["pos"]
            if pos and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                close_trade((min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos * TICK)
            if st["pos"] and k == 389: close_trade(c[k] - st["pos"] * TICK)
            if k in checks:
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK)
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side: pending, ntr = side, ntr + 1
    return pd.DataFrame(out, columns=["d", "pnl"])


def walk(s, e, stop, tgt, H, L, O, C, j0, j1):
    for j in range(j0, j1):
        if (s > 0 and L[j] <= stop) or (s < 0 and H[j] >= stop):
            return ((min(stop, O[j]) if s > 0 else max(stop, O[j])) - s * TICK - e) * s * PV - FEE
        if (s > 0 and H[j] >= tgt) or (s < 0 and L[j] <= tgt):
            return (tgt - e) * s * PV - FEE
    return (C[j1 - 1] - s * TICK - e) * s * PV - FEE


def pm_fade(days, noise_days):
    out = []
    for d, a in days:
        if d < START or d > END or d in noise_days: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK
            if (vw[k] - e) * s < 4 * TICK: break
            out.append((d, walk(s, e, e - s * PTS, vw[k], h, l, o, c, k + 1, 386))); break
    return pd.DataFrame(out, columns=["d", "pnl"])


if __name__ == "__main__":
    import noise_gen as NG  # load_days (same as tools/noise_area.py)
    download()
    days, nb = NG.load_days(MNQ)
    assert nb == 390
    f = lambda t: t[(t.d >= START) & (t.d <= END)]
    nt = f(noise_t(days, PTS))
    t = pd.concat([nt, pm_fade(days, set(nt.d))]).sort_values("d", kind="stable").reset_index(drop=True)
    w = t.pnl > 0
    print(f"trades {len(t)} win {w.mean():.1%} PF {t.pnl[w].sum() / -t.pnl[~w].sum():.2f} total ${t.pnl.sum():.2f}")
    with open(OUT, "w") as fh:
        fh.write("# MAIN strategy (NOISE $250 + PM fade $250), MNQ 1 micro, Databento MNQ.v.0, 2021-11-01..2026-10-30, net of costs\n")
        t.assign(pnl=t.pnl.round(2)).to_csv(fh, index=False)
