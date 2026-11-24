import sys; sys.path.insert(0, sys.path[0])
import sim150 as S, numpy as np
cfg = S.mk(stop=100, N=4, nc=3, brake=(0.5, 2))
def run(lab, c=cfg):
    r = S.evaluate(c, with_static=True); print(f"{lab:34s} pass {r['ALL']['pass']:.1f} p60 {r['ALL']['p60']:.1f} med {r['ALL']['med']} judge {r['JUDGE']['pass']:.1f} pick {r['PICK']['pass']:.1f} profit {r['static']['profit']:.0f}")
run("150K #2 N4@100+C3+brake (as reported)")
S.COST1 = 4.0; S._cache.clear(); run("  CANDACE +$2 RT per micro")
S.COST1 = 2.0; S._cache.clear(); run("  CANDACE off", S.mk(stop=100, N=4, nc=0, brake=(0.5, 2)))
# NOISE +$2 RT per micro
orig = S.noise_df
def nd(*a):
    df = orig(*a).copy(); df["pnl"] = df["pnl"] - 2.0; return df
S._cache.clear(); S.noise_df = nd; run("  NOISE +$2 RT per micro")
S.COST1 = 4.0; S._cache.clear(); run("  both +$2 RT per micro")
S.noise_df = orig; S.COST1 = 2.0; S._cache.clear()
S.KILL = 100.0; run("  kill distance $100 (CLAUDE.md) not $50")
