"""Download Databento <ROOT>.v.0 (volume roll) 1m bars for a date range, year chunks with retries → one CSV.
usage: DATABENTO_API_KEY=… dbget2y.py ROOT START END OUT.csv   (e.g. MNQ 2024-10-24 2026-11-05T22:00)"""
import os, sys, time
import databento as db
root, start, end, out = sys.argv[1:5]
c = db.Historical(os.environ["DATABENTO_API_KEY"])
spans, y = [], int(start[:4])
while f"{y}" <= end[:4]:
    a = max(start, f"{y}-01-01"); b = min(end, f"{y + 1}-01-01")
    if a < b: spans.append((a, b))
    y += 1
with open(out, "w") as f:
    first = True
    for a, b in spans:
        for k in range(5):
            try:
                df = c.timeseries.get_range(dataset="GLBX.MDP3", symbols=[f"{root}.v.0"], stype_in="continuous",
                                            schema="ohlcv-1m", start=a, end=b).to_df()
                break
            except Exception as e:  # noqa: BLE001
                print("retry", a, type(e).__name__, str(e)[:80], flush=True); time.sleep(2 ** (k + 1))
        else:
            raise SystemExit(f"failed {a}")
        o = df[["open", "high", "low", "close", "volume"]].copy()
        o.index = o.index.strftime("%Y-%m-%dT%H:%M:%SZ"); o.index.name = "timestamp"
        o.to_csv(f, header=first); first = False
        print(root, a, len(o), flush=True)
