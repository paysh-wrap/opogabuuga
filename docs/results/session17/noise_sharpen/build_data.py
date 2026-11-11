"""Join the yearly Databento MNQ.v.0 ohlcv-1m downloads (scratchpad/data/MNQ_<year>.csv) into one csv with a 'timestamp' column."""
import glob, sys
import pandas as pd
SP = "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad"
fs = sorted(glob.glob(SP + "/data/MNQ_20??.csv"))
df = pd.concat([pd.read_csv(f, usecols=["ts_event", "open", "high", "low", "close", "volume"]) for f in fs])
df["timestamp"] = df.ts_event.str.slice(0, 19) + "Z"
df = df.drop_duplicates("timestamp").sort_values("timestamp")
df[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(SP + "/mnq_2019_2026.csv", index=False)
print(len(fs), "files", len(df), "bars", df.timestamp.iloc[0], df.timestamp.iloc[-1])
