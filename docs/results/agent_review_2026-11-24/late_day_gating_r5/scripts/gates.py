"""Late-day leg gating study (research only). Gates are pre-registered; gate-4 threshold chosen on PICK only. Study variant = published (exit 15:59 close, no target)."""
import sys, os, json; HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd
from lib_ne import *
R = "/home/user/paytience/docs/results/"
SP = "/tmp/claude-0/-home-user/a273a314-1ab3-5e31-93aa-00499fccb9da/scratchpad/"
rng = np.random.default_rng(11)
nz = pd.read_csv(SP + "nz/base.csv")                                   # verified NOISE stream (654 trades, $19,293 = streams_BASE)
cd = pd.read_csv(R + "pass_faster_c125/streams_candace_base.csv")
vx = pd.read_csv(SP + "vix.csv"); vx = vx[vx.VIXCLS != "."]; vx["v"] = vx.VIXCLS.astype(float); VIX = dict(zip(vx.observation_date, vx.v))
vd = sorted(VIX)
def prev_vix(d):
    i = np.searchsorted(vd, d) - 1; return VIX[vd[i]]
NZ = {d: g for d, g in nz.groupby("d")}

def make(entry, hold_target=0, xend=389):
    rows = []
    for d in DAYS:
        a = BARS[d]; r = a["close"][239] - a["open"][0]
        if abs(r) < 0.1 * ATR[d] or r == 0: continue
        side = int(np.sign(r)); pts, k = run_trade(a, entry, side, 60.0, hold_target, xend)
        pf_, _ = run_trade(a, entry, -side, 60.0, hold_target, xend)
        rows.append(dict(day=d, idx=entry, exit_idx=k, side=side, pts=pts, flip=pf_, stop_pts=60.0, mv=abs(r) / ATR[d],
                         dow=pd.Timestamp(d).dayofweek, vix=prev_vix(d)))
    t = pd.DataFrame(rows); t["ptsB"] = t.pts; return t
def noise_feat(t):
    a, b, c, e = [], [], [], []
    for r in t.itertuples():
        g = NZ.get(r.day)
        if g is None: a.append(False); b.append(0.0); c.append(False); e.append(0); continue
        a.append(bool((g.ek < r.idx).any()))                                      # NOISE entered before the leg's entry bar
        b.append(float(g[g.xk < r.idx].pnl.sum()))                                # realized NOISE P&L so far (causal)
        c.append(bool(((g.ek <= r.idx) & (g.xk > r.idx)).any()))                  # NOISE position open at entry
        p = g[g.ek < r.idx]; e.append(int(p.iloc[-1].side) if len(p) else 0)      # side of NOISE's last signal
    t["nz_any"], t["nz_pnl"], t["nz_open"], t["nz_side"] = a, b, c, e
    return t
def stat(t, ctrl=True):
    out = {}
    for nm, m in (("pick", t.day <= PICK_END), ("judge", t.day >= JUDGE0)):
        x = t[m]; net = (x.pts - COST_PTS).values
        w, l = net[net > 0].sum(), -net[net < 0].sum()
        d = dict(n=len(x), wr=round(100 * float((net > 0).mean()), 1) if len(x) else None, pf=round(float(w / l), 3) if l > 0 else None, net=round(float(net.sum() * PV)))
        if ctrl and len(x) >= 20:
            own = (x.pts.values - COST_PTS); fl = (x.flip.values - COST_PTS); pfs = []
            for _ in range(2000):
                s = rng.random(len(x)) < 0.5; z = np.where(s, own, fl); ww, ll = z[z > 0].sum(), -z[z < 0].sum(); pfs.append(ww / ll if ll > 0 else 9)
            d["rand_p95"] = round(float(np.percentile(pfs, 95)), 3); d["p_rand"] = round(float(np.mean(np.array(pfs) >= (d["pf"] or 0))), 4)
        out[nm] = d
    return out
idx = pd.Index(DAYS); S = lambda s: s.reindex(idx).fillna(0.0)
dn = nz.groupby("d").pnl.sum(); dc = cd.groupby("day").p1.sum() * 2.0 - 2.0 * cd.groupby("day").size(); dnc = dn.add(dc, fill_value=0)
def corr(t):
    dl = ((t.pts - COST_PTS) * PV).groupby(t.day).sum()
    return round(float(np.corrcoef(S(dl), S(dnc))[0, 1]), 3)

T = noise_feat(make(330))
base_t = T
print("ungated", stat(T, False)); assert stat(T, False)["pick"]["n"] == 465 and stat(T, False)["judge"]["n"] == 602
pk = T[T.day <= PICK_END]
med_vix = float(pk.vix.median())
# gate 4: grid {0.25, 0.5, 0.75} x 14d avg range, choose highest PICK PF with pick n >= 150 (pre-registered rule)
g4 = {}
for th in (0.25, 0.5, 0.75):
    x = pk[pk.mv >= th]; net = x.pts - COST_PTS; g4[th] = (len(x), float(net[net > 0].sum() / -net[net < 0].sum()))
ok = {k: v for k, v in g4.items() if v[0] >= 150}; TH = max(ok, key=lambda k: ok[k][1]); print("gate4 grid (pick n, PF):", g4, "chosen", TH)
GATES = {
    "G0 ungated": (T, "all signals"),
    "G0b app rule: skip if NOISE open at entry": (T[~T.nz_open], "what the app does today"),
    "G1 skip if NOISE traded today (before entry)": (T[~T.nz_any], ""),
    "G2 skip if NOISE realized P&L today < 0": (T[~(T.nz_pnl < 0)], ""),
    "G3 NOISE flat, traded today, trend side == NOISE last side": (T[(~T.nz_open) & (T.nz_side == T.side)], "strict: needs a NOISE trade today"),
    f"G4 |move|>={TH} x 14d range": (T[T.mv >= TH], "threshold picked on pick"),
    f"G5 skip if prior-day VIX > pick median {med_vix:.2f}": (T[T.vix <= med_vix], ""),
    "G6 skip Mondays": (T[T.dow != 0], ""),
    "G7a entry 14:30": (noise_feat(make(300)), ""),
    "G7b entry 15:30": (noise_feat(make(360)), ""),
}
res = {}
for k, (t, note) in GATES.items():
    s = stat(t); s["corr_noise_candace_daily"] = corr(t); s["note"] = note
    s["net_vs_ungated_pick"] = s["pick"]["net"] - stat(T, False)["pick"]["net"]; s["net_vs_ungated_judge"] = s["judge"]["net"] - stat(T, False)["judge"]["net"]
    res[k] = s; print(k, json.dumps({w: s[w] for w in ("pick", "judge")}), "corr", s["corr_noise_candace_daily"], flush=True)
U = res["G0 ungated"]
for k, s in res.items():
    s["adopt_tests"] = dict(
        beats_ungated_pf_both=bool(s["pick"]["pf"] > U["pick"]["pf"] and s["judge"]["pf"] > U["judge"]["pf"]),
        net_not_cut_both=bool(s["pick"]["net"] >= U["pick"]["net"] and s["judge"]["net"] >= U["judge"]["net"]),
        judge_n_ge_60=bool(s["judge"]["n"] >= 60),
        beats_random_p95_judge=bool(s["judge"]["pf"] > s["judge"]["rand_p95"]))
    s["ADOPT_CANDIDATE"] = bool(all(s["adopt_tests"].values())) and not k.startswith("G0")
json.dump(dict(median_vix_pick=med_vix, gate4_grid={str(a): b for a, b in g4.items()}, gate4_chosen=TH, gates=res), open(HERE + "/../gates_results.json", "w"), indent=1, default=float)
# day sets for sims: app variant (exit 15:59 close + 180 pt target), same gates -> same day sets (7a/7b regenerated)
def app(entry): 
    t = make(entry, 180.0, 388); return t
A = {330: app(330), 300: app(300), 360: app(360)}
for k, (t, _) in GATES.items():
    e = 300 if k.startswith("G7a") else 360 if k.startswith("G7b") else 330
    a = A[e]; a = a[a.day.isin(t.day)] if e == 330 else a
    a[["day", "idx", "exit_idx", "side", "pts", "stop_pts", "ptsB"]].to_csv(HERE + "/legsets/" + k.split()[0] + "_app.csv", index=False) if os.path.isdir(HERE + "/legsets") else None
