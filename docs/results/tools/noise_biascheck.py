"""How much can a DAILY direction call (TradingAgents / Vibe-Trading) help the noise-area strategy?
Hindsight day direction = RTH open -> close. A bias with accuracy `a` blocks the side opposite to its call.
usage: noise_biascheck.py MNQ_1M.csv TRADES.csv   (TRADES = noise_area.py output; judged on 2024-01+)"""
import sys

import numpy as np
import pandas as pd

df = pd.read_csv(sys.argv[1], parse_dates=["timestamp"]).set_index("timestamp")
df.index = df.index.tz_convert("America/New_York")
rth = df.between_time("09:30", "15:59")
g = rth.groupby(rth.index.date)
dirn = np.sign(g.close.last() - g.open.first())
dirn.index = dirn.index.astype(str)
t = pd.read_csv(sys.argv[2])
t = t[pd.to_datetime(t.d) >= "2024-01-01"].copy()
t["with_day"] = t.side == t.d.astype(str).map(dirn)
for k, s in t.groupby("with_day"):
    print("WITH day" if k else "AGAINST day", f"n={len(s)} win={(s.pnl > 0).mean():.0%} avg$={s.pnl.mean():.1f} total=${s.pnl.sum():.0f}")
rng = np.random.default_rng(1)
days = t.d.unique()
for acc in (.50, .55, .60, .65, .70, .75, 1.0):
    res = []
    for _ in range(400):
        call = {d: (dirn[str(d)] if rng.random() < acc else -dirn[str(d)]) for d in days}
        kept = t[t.side == t.d.map(call)]
        res.append((kept.pnl.sum(), len(kept), (kept.pnl > 0).mean()))
    a = np.array(res)
    print(f"bias accuracy {acc:.0%}: keeps {a[:, 1].mean():.0f}/{len(t)} trades, win {a[:, 2].mean():.1%}, "
          f"total ${a[:, 0].mean():.0f} vs no bias ${t.pnl.sum():.0f}")
