"""Third-leg test: candidate trades -> (a) correlation / overlap with NOISE+CANDACE, (b) eval sim (pass_fastest sim150 via final_search/final.py) with the leg added.
Run from <worktree>/backend with PYTHONPATH=. : /usr/local/bin/python3 ../docs/results/new_edge/scripts/run_leg.py <name> [nolegs]
Candidates are defined in CAND below (strategy, params from research.py)."""
import sys, os, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import research as R
from lib_ne import *
PF = "/home/user/opogabuuga/docs/results/pass_fastest"
CAND = {
    "gapcont": ("gapfade", {"mode": "cont", "mingap": 0.8, "e": 5, "xend": 389, "stop": 0.2, "fill": 1.0}),
    "lastmom239": ("lastmom_day", {"ref": 239, "minr": 0.1, "hold": 59, "stop": 60}),
}
name = sys.argv[1]
strat, p = CAND[name]
tr = R.gen(strat, p)
tr = tr[tr.stop_pts * 2 + 2 <= 125.0 + 1e-9].copy()                      # same $125 per-micro cap as CANDACE/GALA rows
tr["ptsB"] = tr.pts
csv = os.path.join(HERE, f"trades_{name}.csv"); tr.to_csv(csv, index=False)
res = dict(name=name, strategy=strat, params=p, stats=stats(tr))

# ---- correlation with NOISE + CANDACE (per-micro $ per day, 5y)
nz = pd.read_csv(PF + "/../pass_faster/streams_noise_base.csv"); cd = pd.read_csv(PF + "/../pass_faster/streams_candace.csv")
dn = nz.groupby("d").pnl.sum(); dc = (cd.groupby("day").p1.sum() * 2.0 - 2.0 * cd.groupby("day").size())
dnc = dn.add(dc, fill_value=0)
net = (tr.pts - COST_PTS) * PV
dl = net.groupby(tr.day).sum()
idx = pd.Index(DAYS)
S = lambda s: s.reindex(idx).fillna(0.0)
res["corr_daily_vs_noise"] = round(float(np.corrcoef(S(dl), S(dn))[0, 1]), 3)
res["corr_daily_vs_candace"] = round(float(np.corrcoef(S(dl), S(dc))[0, 1]), 3)
res["corr_daily_vs_noise+candace"] = round(float(np.corrcoef(S(dl), S(dnc))[0, 1]), 3)
# overlap: share of candidate trade intervals overlapping a NOISE/CANDACE interval the same day
iv = {}
for r in nz.itertuples(): iv.setdefault(r.d, []).append((r.ek, r.xk))
for r in cd.itertuples(): iv.setdefault(r.day, []).append((r.idx, r.exit_idx))
ov = [any(not (r.exit_idx < a or r.idx > b) for a, b in iv.get(r.day, [])) for r in tr.itertuples()]
res["overlap_share_with_noise_candace"] = round(float(np.mean(ov)), 3)
res["same_day_share"] = round(float(np.mean([r.day in iv for r in tr.itertuples()])), 3)
print(json.dumps(res, indent=1, default=float), flush=True)

if len(sys.argv) > 2 and sys.argv[2] == "nolegs":
    json.dump(res, open(os.path.join(HERE, f"leg_{name}.json"), "w"), indent=1, default=float); sys.exit()

# ---- eval sim with the leg
sys.path.insert(0, PF + "/final_search")
import final as FN
_lo = FN.B.load_sim
def load_sim2():
    m = _lo()
    g = tr.rename(columns={}).copy()
    m.gala_df = lambda: g[(g.day >= m.WIN["ALL"][0]) & (g.day <= m.WIN["ALL"][1])]
    return m
FN.B.load_sim = load_sim2
import lib as L
L._S.clear()
out = {}
for k in (25, 50, 100, 150):
    base = FN.BUILT[k]
    for ng in (0, 1, 2, 3):
        c = dict(base)
        if ng: c["ng"] = ng
        S_ = L.sim(k, True); e = S_.evaluate(S_.mk(**FN.cfg(k, **{x: v for x, v in c.items() if x != "ng"}, **({"ng": ng} if ng else {}))))
        r = {w: {x: e[w][x] for x in ("pass", "stuck", "p60", "med")} for w in ("ALL", "PICK", "JUDGE")}
        r["profit"] = e["static"]["profit"]; r["chain"] = {x: e["ch"][x] for x in ("mean", "med")}
        out[f"{k}|ng{ng}"] = r
        print(k, "ng", ng, "ALL pass %.1f med %s | pick %.1f judge %.1f | profit %.0f | chain mean %.1f" % (r["ALL"]["pass"], r["ALL"]["med"], r["PICK"]["pass"], r["JUDGE"]["pass"], r["profit"], r["chain"]["mean"]), flush=True)
res["sim"] = out
json.dump(res, open(os.path.join(HERE, f"leg_{name}.json"), "w"), indent=1, default=float)
