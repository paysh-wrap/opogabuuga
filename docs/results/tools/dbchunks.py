"""Download Databento MGC.v.0 1m bars year by year (retries on 5xx), write one CSV."""
import os, sys, time
import databento as db
c = db.Historical(os.environ["DATABENTO_API_KEY"])
out = sys.argv[1]; first = True
spans = [(f"{y}-01-01", f"{y + 1}-01-01") for y in range(2019, 2026)] + [("2026-01-01", "2026-11-05T22:00")]
spans[0] = ("2019-05-06", "2020-01-01")
with open(out, "w") as f:
    for a, b in spans:
        for k in range(5):
            try:
                df = c.timeseries.get_range(dataset="GLBX.MDP3", symbols=["MGC.v.0"], stype_in="continuous",
                                            schema="ohlcv-1m", start=a, end=b).to_df()
                break
            except Exception as e:  # noqa: BLE001
                print("retry", a, type(e).__name__, str(e)[:80], flush=True); time.sleep(2 ** (k + 1))
        else:
            raise SystemExit(f"failed {a}")
        o = df[["open", "high", "low", "close", "volume"]].copy()
        o.index = o.index.strftime("%Y-%m-%dT%H:%M:%SZ"); o.index.name = "timestamp"
        o.to_csv(f, header=first); first = False
        print(a, len(o), flush=True)
