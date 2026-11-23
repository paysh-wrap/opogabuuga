"""App-faithful variant of the late leg: exit at the 15:59 bar close (study: 16:00 close) + a 3R (180 pt) safety target (study: none).
Writes trades_app.csv (same format as ../scripts/trades_lastmom239.csv) and prints the judge/pick stats."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE + "/../scripts")
import numpy as np, pandas as pd
from lib_ne import *
rows = []
for d in DAYS:
    a = BARS[d]; c, o = a["close"], a["open"]; at = ATR[d]
    r = c[239] - o[0]
    if abs(r) < 0.1 * at or r == 0: continue
    side = int(np.sign(r)); e, xe = 330, 388
    pts, k = run_trade(a, e, side, 60.0, 180.0, xe)
    rows.append(dict(day=d, idx=e, exit_idx=k, side=side, pts=pts, stop_pts=60.0))
tr = pd.DataFrame(rows); tr = tr[tr.stop_pts * 2 + 2 <= 125.0 + 1e-9]; tr["ptsB"] = tr.pts
tr.to_csv(HERE + "/trades_app.csv", index=False)
base = pd.read_csv(HERE + "/../scripts/trades_lastmom239.csv")
print(json.dumps(dict(app=stats(tr), study=stats(base)), indent=1, default=float))
