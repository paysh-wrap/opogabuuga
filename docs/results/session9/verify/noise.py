"""Independent re-implementation of Zarattini-Aziz-Barbon (2024) noise-area intraday momentum on MNQ 1m.
Bars are labeled by OPEN time (ET). Decision at check time T uses the close of the bar that opened at T-1min;
entry/exit fill at the OPEN of bar T (+1 tick slippage). Costs: $1 fee RT + 1 tick each side. Point value $2."""
import sys, numpy as np, pandas as pd
import os; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); from load import load
PV, TICK, FEE = 2.0, 0.25, 1.0
LOOK = 14
df = load("mnq")
rth = df.between_time("09:30", "15:59")
rth = rth.assign(d=rth.index.normalize().tz_localize(None).date if False else rth.index.date)
days = []
for d, g in rth.groupby("d"):
    if len(g) < 380: continue  # half days / gaps skipped
    m = ((g.index.hour - 9) * 60 + g.index.minute - 30).values
    if m[0] != 0: continue
    o = g.open.values; h = g.high.values; l = g.low.values; c = g.close.values; v = g.volume.values
    full = np.full(390, np.nan); cc = full.copy(); cc[m[m < 390]] = c[m < 390]
    oo = full.copy(); oo[m[m < 390]] = o[m < 390]
    tp = (h + l + c) / 3; vw = np.cumsum(tp * v) / np.maximum(np.cumsum(v), 1); vv = full.copy(); vv[m[m < 390]] = vw[m < 390]
    days.append((d, oo, cc, vv))
print("days", len(days), days[0][0], days[-1][0])
moves = np.array([np.abs(cc / oo[0] - 1) for _, oo, cc, _ in days])
checks = list(range(29, 360, 30))  # bar opened at 09:59 (closes 10:00) ... 15:29 (closes 15:30)
def run(maxtr=3, hard_stop_pts=None):
    out = []
    for i in range(LOOK, len(days)):
        d, oo, cc, vv = days[i]
        prev_close = days[i - 1][2][389]
        if abs(oo[0] / prev_close - 1) > 0.015 or np.isnan(prev_close):  # roll/gap guard
            continue
        sig = np.nanmean(moves[i - LOOK:i], axis=0)
        ub = max(oo[0], prev_close) * (1 + sig); lb = min(oo[0], prev_close) * (1 - sig)
        pos = 0; ntr = 0; entry = stop0 = None
        for k in checks + [389]:
            px = cc[k]
            if np.isnan(px): continue
            fill_i = k + 1
            if pos != 0:
                trail = max(ub[k], vv[k]) if pos > 0 else min(lb[k], vv[k])
                if k == 389 or (pos > 0 and px < trail) or (pos < 0 and px > trail):
                    exitp = cc[389] if k == 389 or fill_i >= 390 or np.isnan(oo[fill_i]) else oo[fill_i]
                    exitp -= pos * TICK
                    pnl = (exitp - entry) * pos * PV - FEE
                    out.append((d, pos, entry, exitp, stop0, pnl, (exitp - entry) * pos / stop0))
                    pos = 0
            if k == 389: break
            if pos == 0 and ntr < maxtr and fill_i < 390 and not np.isnan(oo[fill_i]):
                side = 1 if px > ub[k] else (-1 if px < lb[k] else 0)
                if side:
                    entry = oo[fill_i] + side * TICK
                    st = max(ub[k], vv[k]) if side > 0 else min(lb[k], vv[k])
                    stop0 = max(abs(entry - st), entry * 0.001)
                    pos = side; ntr += 1
    return pd.DataFrame(out, columns=["d", "side", "entry", "exit", "risk_pts", "pnl", "r"])
def stats(t, label):
    if t.empty: print(label, "no trades"); return
    w = t.pnl > 0; eq = t.pnl.cumsum(); dd = (eq - eq.cummax()).min()
    daily = t.groupby("d").pnl.sum()
    print(f"{label:22s} n={len(t):5d} /day={len(t)/t.d.nunique()*t.d.nunique()/max(1,len(set(t.d))) :.2f} win={w.mean():.1%} "
          f"avg$={t.pnl.mean():7.2f} PF={t.pnl[w].sum()/-t.pnl[~w].sum():.2f} DD$={dd:8.0f} "
          f"worst trade={t.pnl.min():7.0f} worst day={daily.min():7.0f} days_traded={t.d.nunique()}")
t = run()
t["y"] = pd.to_datetime(t.d).dt.year
ins = t[pd.to_datetime(t.d) < "2024-01-01"]; hold = t[pd.to_datetime(t.d) >= "2024-01-01"]
stats(ins, "IN 2019-23"); stats(hold, "HELD 2024-26")
for y, g in t.groupby("y"): stats(g, f"  {y}")
t.to_csv(HERE + "/noise_trades.csv", index=False)
