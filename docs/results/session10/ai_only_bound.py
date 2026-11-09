"""Upper bound for an AI-only (TradingAgents + Vibe-Trading) MNQ day strategy.

HINDSIGHT: the LLM tools cannot be run on past dates (spec §15, training-data leakage), so this shows what a daily
direction call of accuracy `a` WOULD earn: a=100% is the ceiling (knows the day's direction), a=50% is a coin flip.
Entry 09:30 RTH open (market), broker stop stop_pct away (checked on 1m highs/lows, stop wins ties), exit 16:00 close.
1 micro MNQ ($2/pt), costs $1.00 fee + 2 ticks slippage round trip. Data: Databento GLBX.MDP3 ohlcv-1m MNQ.v.0.
Usage: python ai_only_bound.py mnq1y.csv [stop_pct]"""
import sys
import pandas as pd

csv, stop_pct = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.005
PV, COST = 2.0, 1.00 + 2 * 0.5
df = pd.read_csv(csv, usecols=["ts_event", "open", "high", "low", "close"])
df["t"] = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert("America/New_York")
df = df[(df.t.dt.hour * 60 + df.t.dt.minute >= 570) & (df.t.dt.hour * 60 + df.t.dt.minute < 960)]
rows = []
for d, g in df.groupby(df.t.dt.date):
    if len(g) < 300 or g.t.iloc[0].strftime("%H:%M") != "09:30":
        continue
    e = g.open.iloc[0]
    out = {"day": d, "open": e, "close": g.close.iloc[-1]}
    for side, sg in (("L", 1), ("S", -1)):
        stop = e * (1 - sg * stop_pct)
        hit = (g.low <= stop) if sg == 1 else (g.high >= stop)
        exit_px = stop if hit.any() else g.close.iloc[-1]
        out[side] = (exit_px - e) * sg * PV - COST
        out[side + "_stop"] = bool(hit.any())
    rows.append(out)
r = pd.DataFrame(rows)
up = r.close > r.open
r["correct"] = r.L.where(up, r.S)
r["wrong"] = r.S.where(up, r.L)
print(f"days {len(r)} {r.day.min()} → {r.day.max()} | stop {stop_pct:.2%} (~${r.open.mean()*stop_pct*PV:.0f}/trade)")
print(f"always long: ${r.L.sum():,.0f} (win {(r.L>0).mean():.0%}) | always short: ${r.S.sum():,.0f}")
print("accuracy | $/trade | total $ | win% | worst day | PF")
for a in (1.0, 0.7, 0.65, 0.6, 0.55, 0.5):
    pnl = a * r.correct + (1 - a) * r.wrong  # expected value per day
    w = a * (r.correct > 0) + (1 - a) * (r.wrong > 0)
    gp = (a * r.correct.clip(lower=0) + (1 - a) * r.wrong.clip(lower=0)).sum()
    gl = -(a * r.correct.clip(upper=0) + (1 - a) * r.wrong.clip(upper=0)).sum()
    print(f"{a:>7.0%} | {pnl.mean():>7.2f} | {pnl.sum():>8,.0f} | {w.mean():>4.0%} | {min(r.correct.min(), r.wrong.min()):>8.0f} | {gp/gl if gl else float('inf'):.2f}")
