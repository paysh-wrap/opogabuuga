"""Join the quarterly Databento downloads (GLBX.MDP3, <SYM>.v.0 continuous by volume roll, ohlcv-1m, csv) into <sym>_5y.csv
(timestamp,open,high,low,close,volume - same layout as mnq_5y.csv).  usage: python3 build_raw.py <raw folder> MES MGC
Download (the session proxy adds the key):  curl -u db-dummy: https://hist.databento.com/v0/timeseries.get_range -d dataset=GLBX.MDP3
  -d symbols=MES.v.0 -d stype_in=continuous -d schema=ohlcv-1m -d start=2021-10-01 -d end=2022-01-01 -d encoding=csv -d pretty_px=true -d pretty_ts=true"""
import sys, glob
import pandas as pd
raw = sys.argv[1]
for sym in sys.argv[2:]:
    fs = sorted(glob.glob(f"{raw}/{sym}_20*.csv"))
    df = pd.concat([pd.read_csv(f, usecols=["ts_event", "open", "high", "low", "close", "volume"]) for f in fs])
    df["timestamp"] = df.ts_event.str.slice(0, 19) + "Z"
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    df[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(f"{raw}/{sym.lower()}_5y.csv", index=False)
    print(sym, len(fs), "files", len(df), "bars", df.timestamp.iloc[0], df.timestamp.iloc[-1])
