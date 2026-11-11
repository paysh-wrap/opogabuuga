"""Session 17 split-combo study: data loader. Databento GLBX.MDP3 <SYM>.v.0 (volume roll) ohlcv-1m CSVs -> RTH (09:30-16:00 ET) day arrays,
cached as a pickle OUTSIDE git (scratchpad). Same loader rules as docs/results/session10/five_year/noise_gen.load_days (MNQ >= 97% bars and a 09:30 bar;
MGC thin market: forward-fill, needs >= 50% minutes) plus a volume array. usage: python3 data.py <cache.pkl> <csv> [<csv> ...]  (one symbol per call via SYM env)"""
import sys, os, pickle, glob
import numpy as np, pandas as pd

NB = 390
JUMP = {"MNQ": None, "MGC": 0.02}   # MGC: drop a day with any 1-minute close-to-close jump > 2% (roll / bad print), as in session 16; MNQ: none (same as NOISE research)


def load(sym, files):
    df = pd.concat([pd.read_csv(f, usecols=["ts_event", "open", "high", "low", "close", "volume"]) for f in files])
    df["ts"] = pd.to_datetime(df.ts_event, utc=True)
    df = df.drop_duplicates("ts").sort_values("ts").set_index("ts").drop(columns="ts_event")
    df.index = df.index.tz_convert("America/New_York")
    rth = df.between_time("09:30", "15:59")
    ffill = sym == "MGC"
    days = []; skipped = 0
    for d, g in rth.groupby(rth.index.date):
        if d.weekday() >= 5: continue
        if ffill:
            if len(g) < NB * 0.5: skipped += 1; continue
            idx = pd.date_range(pd.Timestamp(d, tz=g.index.tz) + pd.Timedelta(minutes=570), periods=NB, freq="min")
            c0 = g["close"].reindex(idx).ffill().bfill()
            g2 = pd.DataFrame({"close": c0})
            for col in ("open", "high", "low"): g2[col] = g[col].reindex(idx).fillna(g2["close"])
            g2["volume"] = g["volume"].reindex(idx).fillna(0)
            g = g2
        m = ((g.index.hour - 9) * 60 + g.index.minute - 30).values
        if len(g) < NB * 0.97 or m[0] != 0: skipped += 1; continue
        a = {}
        for col in ("open", "high", "low", "close", "volume"):
            x = np.full(NB, np.nan); x[m] = g[col].values.astype(float); a[col] = x
        cl = a["close"][~np.isnan(a["close"])]
        if JUMP[sym] and np.abs(np.diff(cl) / cl[:-1]).max() > JUMP[sym]: skipped += 1; continue
        tp = (g.high + g.low + g.close).values / 3; v = g.volume.values.astype(float)
        vw = np.full(NB, np.nan); vw[m] = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1)
        a["vwap"] = vw
        days.append((str(d), a))
    return days, skipped


if __name__ == "__main__":
    sym, out = sys.argv[1], sys.argv[2]
    files = sorted(sys.argv[3:])
    days, sk = load(sym, files)
    pickle.dump(days, open(out, "wb"))
    print(sym, len(days), "days", days[0][0], days[-1][0], "skipped", sk)
