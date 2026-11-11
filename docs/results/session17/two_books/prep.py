"""Session 17 two-books study - data preparation (cache stays OUTSIDE git).
Input : Databento GLBX.MDP3 MNQ.v.0 ohlcv-1m yearly CSVs (2019-05-06 .. 2026-11-06, csv, pretty_px/pretty_ts) + NQ.v.0 ohlcv-1d (2017..)
        download: curl -u db-<dummy>: https://hist.databento.com/v0/timeseries.get_range -d dataset=GLBX.MDP3 -d symbols=MNQ.v.0
                  -d stype_in=continuous -d schema=ohlcv-1m -d start=.. -d end=.. -d encoding=csv -d pretty_px=true -d pretty_ts=true
Output: <cache>/mnq_1m.csv (layout of tools/noise_area.py) and <cache>/mnq_days.pkl
usage : python3 prep.py <folder with MNQ_20xx.csv, NQ_1d.csv>"""
import sys, glob, pickle
import numpy as np, pandas as pd

raw = sys.argv[1]
df = pd.concat([pd.read_csv(f, usecols=["ts_event", "instrument_id", "open", "high", "low", "close", "volume"]) for f in sorted(glob.glob(f"{raw}/MNQ_20*.csv"))])
df["timestamp"] = df.ts_event.str.slice(0, 19) + "Z"
df = df.drop_duplicates("timestamp").sort_values("timestamp")
df[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(f"{raw}/mnq_1m.csv", index=False)
df.index = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York"); df.index.name = None
# contract rolls: gap = first open of the new contract - last close of the old one (consecutive bars)
chg = np.flatnonzero(df.instrument_id.values[1:] != df.instrument_id.values[:-1]) + 1
rolls = [(df.index[i], float(df.open.values[i] - df.close.values[i - 1])) for i in chg]
print("rolls", len(rolls), [(str(t)[:16], round(g, 1)) for t, g in rolls][:40])
rth = df.between_time("09:30", "15:59")
days = []
for d, g in rth.groupby(rth.index.date):
    m = ((g.index.hour - 9) * 60 + g.index.minute - 30).values
    if len(g) < 380 or m[0] != 0: continue          # same rule as tools/noise_area.load_days
    a = {}
    for col in ("open", "high", "low", "close", "volume"):
        x = np.full(390, np.nan); x[m] = g[col].values; a[col] = x
    tp = (g.high + g.low + g.close).values / 3; v = g.volume.values
    x = np.full(390, np.nan); x[m] = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1); a["vwap"] = x
    # back-adjust offset: sum of the gaps of all rolls AFTER this day's 09:30 (adjusted price = raw + off)
    t0 = g.index[0]
    a["off"] = -sum(gp for t, gp in rolls if t > t0)
    a["iid"] = int(g.instrument_id.values[0])
    days.append((str(d), a))
nq = pd.read_csv(f"{raw}/NQ_1d.csv"); nq["d"] = nq.ts_event.str.slice(0, 10)
nq = nq[(nq.d < days[0][0]) & (nq.volume > 20000)]          # drop Sunday/holiday stubs
pickle.dump(dict(days=days, rolls=rolls, nq_pre=list(zip(nq.d, nq.close.astype(float)))), open(f"{raw}/mnq_days.pkl", "wb"))
print(len(days), "RTH days", days[0][0], days[-1][0], "| NQ warm-up days", len(nq))
