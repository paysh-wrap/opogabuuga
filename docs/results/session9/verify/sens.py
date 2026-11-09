import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import noise2 as N   # reuses loaded days (runs its own default table first)
def run(look, step):
    N.LOOK = look; N.checks = set(range(29 + (step - 30 if step < 30 else 0), 360, step)) if step != 30 else set(range(29, 360, 30))
    if step == 15: N.checks = set(range(29, 360, 15))
    if step == 60: N.checks = set(range(29, 360, 60))
    t = N.run(); t["dt"] = pd.to_datetime(t.d); out = []
    for nm, g in (("IN", t[t.dt < "2024"]), ("HELD", t[t.dt >= "2024"])):
        w = g.pnl > 0; out.append(f"{nm} n={len(g)} win={w.mean():.0%} $={g.pnl.mean():.1f} PF={g.pnl[w].sum()/-g.pnl[~w].sum():.2f}")
    return " | ".join(out)
N.moves_cache = N.moves
for look in (7, 14, 21, 28):
    for step in (15, 30, 60):
        print(f"look={look:2d} step={step:2d}m  ", run(look, step), flush=True)
