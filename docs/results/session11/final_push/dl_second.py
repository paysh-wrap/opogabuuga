"""Download Databento GLBX.MDP3 ohlcv-1m for MES.v.0 / MYM.v.0 / M2K.v.0 (same call as rebuild_main_csv.py), per quarter, cached in
backend/app/backtest/data/raw/<sym>_v0_<start>.csv, merged to <sym>_5y.csv. usage: dl_second.py [mes mym m2k]"""
import os, subprocess, sys
import pandas as pd
RAW = "/home/user/opogabuuga/backend/app/backtest/data/raw"
spans = [(f"{y}-{m:02d}-01", f"{y + (m + 2) // 12}-{(m + 2) % 12 + 1:02d}-01") for y in range(2021, 2027) for m in (1, 4, 7, 10)]
spans = [(a, b) for a, b in spans if "2021-09-01" <= a <= "2026-10-31"]
spans[-1] = (spans[-1][0], "2026-11-01")
for s in (sys.argv[1:] or ["mes", "mym", "m2k"]):
    out = f"{RAW}/{s}_5y.csv"
    if os.path.exists(out): print(s, "cached"); continue
    parts = []
    for a, b in spans:
        f = f"{RAW}/{s}_v0_{a}.csv"
        for attempt in range(4):
            if os.path.exists(f) and os.path.getsize(f) > 100: break
            subprocess.run(["curl", "-sS", "--fail", "--retry", "4", "-u", "db-dummy:", "-o", f,
                            "https://hist.databento.com/v0/timeseries.get_range",
                            "-d", "dataset=GLBX.MDP3", "-d", f"symbols={s.upper()}.v.0", "-d", "stype_in=continuous",
                            "-d", "schema=ohlcv-1m", "-d", f"start={a}", "-d", f"end={b}", "-d", "encoding=csv",
                            "-d", "pretty_px=true", "-d", "pretty_ts=true", "-d", "map_symbols=false"])
        d = pd.read_csv(f); print(s, a, len(d), flush=True); parts.append(d)
    d = pd.concat(parts).drop_duplicates("ts_event").sort_values("ts_event").rename(columns={"ts_event": "timestamp"})
    d["timestamp"] = pd.to_datetime(d.timestamp).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    d[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(out, index=False)
