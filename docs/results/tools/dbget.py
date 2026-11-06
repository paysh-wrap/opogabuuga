"""Download MGC/MNQ 1m continuous futures from Databento. Usage: DATABENTO_API_KEY=... python dbget.py data/futures"""
# MGC: use .v.0 (highest-volume contract). .c.0 follows the nearest CALENDAR month, which for gold is often an
# illiquid serial month (e.g. 13 one-minute bars on 2026-06-02 vs ~1,380 in the active contract) → broken backtests.
import os, sys
import databento as db
c = db.Historical(os.environ["DATABENTO_API_KEY"])
for sym, f in [("MGC.v.0", "mgc"), ("MNQ.v.0", "mnq")]:
    df = c.timeseries.get_range(dataset="GLBX.MDP3", symbols=[sym], stype_in="continuous",
          schema="ohlcv-1m", start="2019-05-06", end="2026-11-05T22:00").to_df()
    out = df[["open", "high", "low", "close", "volume"]].copy()
    out.index = out.index.strftime("%Y-%m-%dT%H:%M:%SZ"); out.index.name = "timestamp"
    out.to_csv(f"{sys.argv[1]}/{f}_databento_1m.csv")
    print(f, len(out), out.index[0], out.index[-1])
