"""Noise-area on MNQ in the London/pre-market session 03:00-09:29 ET (390 bars, same structure as RTH).
open = 03:00 open, 'prior close' = prior RTH 15:59 close; hourly checks from 03:30; flat at 09:29 close."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/tools")
import noise_area as NA, sim25k as SM
S = "/tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad"
df = pd.read_csv(f"{S}/data/mnq_1m.csv", parse_dates=["timestamp"]).set_index("timestamp")
df.index = df.index.tz_convert("America/New_York")
rthc = df.between_time("15:59", "15:59").close; rthc.index = rthc.index.date
lon = df.between_time("03:00", "09:29")
days = []; prev = None
for d, g in lon.groupby(lon.index.date):
    m = ((g.index.hour - 3) * 60 + g.index.minute).values
    if len(g) < 370 or m[0] != 0: continue
    a = {}
    for col in ("open", "high", "low", "close"):
        x = np.full(390, np.nan); x[m[m < 390]] = g[col].values[m < 390]; a[col] = x
    tp = (g.high + g.low + g.close).values / 3; v = g.volume.values
    vw = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1); x = np.full(390, np.nan); x[m[m < 390]] = vw[m < 390]; a["vwap"] = x
    # prior RTH close stored in slot 389 of a fake previous-day close: emulate by inserting into NA's expectation
    days.append((str(d), a))
# NA.run uses days[i-1][1]["close"][389] as prior close -> build a parallel list with prior RTH close injected
rth_dates = sorted(rthc.index)
import bisect
fixed = []
for d, a in days:
    j = bisect.bisect_left(rth_dates, pd.Timestamp(d).date()) - 1
    pc = rthc.iloc[j] if j >= 0 else np.nan
    fake = {"close": np.full(390, np.nan)}; fake["close"][389] = pc
    fixed.append((d + "_prev", fake)); fixed.append((d, a))
def run(step, hard=0.01):
    t = NA.run(fixed, look=1, step=step, hard=hard)  # look handled below
    return t
# NA.run's sigma uses previous LOOK entries incl. fakes -> compute properly: re-implement minimal wrapper
moves = {d: np.abs(a["close"] / a["open"][0] - 1) for d, a in days}
out = []
ds = [d for d, _ in days]
for step in (60, 30):
    rows = []
    for i in range(14, len(days)):
        d, a = days[i]
        sub = [(ds[i - 1] + "_p", {"close": np.r_[np.full(389, np.nan), fixed[2 * i][1]["close"][389]]}), (d, a)]
        # temporarily monkeypatch moves: NA.run computes moves from given days, so pass 15 days: 14 history + today
        hist = days[i - 14:i] + [(d, a)]
        # prior close injection: replace hist[-2] close[389] view via copy
        h2 = [(x, dict(y)) for x, y in hist]
        cc = h2[-2][1]["close"].copy(); cc[389] = fixed[2 * i][1]["close"][389]; h2[-2][1]["close"] = cc
        # moves for history must use ORIGINAL closes -> NA.run computes |close/open-1| incl. slot 389 change (negligible: 1 minute of 390)
        t = NA.run(h2, look=14, step=step, hard=0.01)
        rows.append(t)
    t = pd.concat(rows); p = f"{S}/verify/london_{step}.csv"; t.to_csv(p, index=False)
    dt = pd.to_datetime(t.d); h = t[dt >= "2024"]; i_ = t[dt < "2024"]
    f = lambda g: f"n={len(g)} win={(g.pnl>0).mean():.1%} $/tr={g.pnl.mean():.2f} PF={g.pnl[g.pnl>0].sum()/-g.pnl[g.pnl<=0].sum():.2f} tot=${g.pnl.sum():.0f}"
    print(f"London step {step}: IN {f(i_)}\n                HELD {f(h)}", flush=True)
    for y, g in t.groupby(dt.dt.year): print("   ", y, f(g))
