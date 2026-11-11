"""Driver: IS-pick one variant per strategy, build separate + combined configs, run account sims for 25K/50K/100K/150K, random-direction benchmark, NOISE preset C.
python3 -I run.py  -> out/results.json , out/picks.json"""
import sys, json, time
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/combined")
import numpy as np, pandas as pd
from port import *

t_start = time.time()
c = load_cands()
STR = ["ICT", "SMC", "DMI", "RSI"]
MINN = dict(ICT=25, SMC=25, DMI=30, RSI=30)
rank0 = {s: i for i, s in enumerate(STR)}

# ------------------------------------------------------------------ 1. IS pick per strategy (1 micro, pooled MNQ+MGC, one position at a time, no day rules)
vtab = []
for (strat, var), g in c.groupby(["strat", "var"]):
    t = select(g, 25, rank0, fixed_n=1)
    i, h, f = (pstats(era_slice(t, e)) for e in ("IS", "HO", "FULL"))
    vtab.append(dict(strat=strat, var=var, IS_n=i["n"], IS_pf=i["pf"], IS_net=i["net"], HO_n=h["n"], HO_pf=h["pf"], HO_net=h["net"], HO_win=h["win"], FULL_n=f["n"], FULL_pf=f["pf"], FULL_net=f["net"]))
vtab = pd.DataFrame(vtab); vtab.to_csv(HERE + "/out/variants_pooled_1micro.csv", index=False)
picks = {}
for s in STR:
    v = vtab[(vtab.strat == s) & (vtab.IS_n >= MINN[s])].sort_values("IS_pf", ascending=False)
    picks[s] = v.iloc[0].to_dict()
order = sorted(STR, key=lambda s: -picks[s]["IS_pf"]); RANK = {s: i for i, s in enumerate(order)}
gated = [s for s in order if picks[s]["IS_pf"] >= 1.2]   # gate: clear in-sample edge (IS PF >= 1.2), at least the top 2
if len(gated) < 2: gated = order[:2]
json.dump(dict(picks=picks, order=order, gated=gated), open(HERE + "/out/picks.json", "w"), indent=1, default=float)
print("picks", {s: (picks[s]["var"], round(picks[s]["IS_pf"], 2)) for s in STR}, "order", order, "gated", gated, flush=True)

pc = c[[(r.strat, r.var) in {(s, picks[s]["var"]) for s in STR} for r in c.itertuples()]].reset_index(drop=True) if False else None
keep = np.zeros(len(c), bool)
for s in STR: keep |= ((c.strat == s) & (c["var"] == picks[s]["var"])).values
P = c[keep].reset_index(drop=True)
VM = vote_mask(P, 30)
CONF = {  # name -> (strategies, vote?)
    "ICT": (["ICT"], False), "SMC": (["SMC"], False), "DMI": (["DMI"], False), "RSI": (["RSI"], False),
    "COMB-1 first signal wins": (STR, False), "COMB-2 IS-PF gated priority": (gated, False), "COMB-3 vote (2 agree <=30 min)": (STR, True)}


def build(conf, scope):
    ss, vote = CONF[conf]
    m = P.strat.isin(ss).values & (np.ones(len(P), bool) if scope == "BOTH" else (P.mkt == scope).values)
    if vote: m &= VM
    return P[m]


def summarize(t, A, boot=False):
    out = {}
    for e in ("IS", "HO", "FULL"):
        x = era_slice(t, e); s = pstats(x)
        s["by_mkt"] = {m: pstats(x[x.mkt == m]) for m in ("MNQ", "MGC")}
        s["avg_n"] = float(x.n.mean()) if len(x) else np.nan
        s["max_n"] = int(x.n.max()) if len(x) else 0
        s["cons"] = consistency(x)
        s["days_traded"] = int(x.d.nunique())
        if e in ("HO", "FULL"): s["roll"] = eval_roll(t, A, e); s["roll_seq"] = eval_roll(t, A, e, strict=False)
        if boot and e == "FULL": s["boot"] = eval_boot(t, A, "FULL"); s["boot_seq"] = eval_boot(t, A, "FULL", strict=False)
        if boot and e == "HO": s["boot"] = eval_boot(t, A, "HO")
        out[e] = s
    out["hedge_vetoes"] = int(t.attrs.get("hedge_vetoes", 0))
    return out


def rand_summary(g, acct, kw, seeds=20):
    A = ACCT[acct]; acc = {e: [] for e in ("HO", "FULL")}
    for sd in range(seeds):
        t = select(g, acct, RANK, rand_seed=sd, **kw)
        for e in acc:
            s = pstats(era_slice(t, e)); s["roll"] = eval_roll(t, A, e); acc[e].append(s)
    o = {}
    for e, v in acc.items():
        o[e] = dict(n=float(np.mean([x["n"] for x in v])), win=float(np.nanmean([x["win"] for x in v])), pf=float(np.nanmean([min(x["pf"], 9) for x in v])), avg=float(np.nanmean([x["avg"] for x in v])),
                    net=float(np.mean([x["net"] for x in v])), net_list=[float(x["net"]) for x in v], pas=float(np.mean([x["roll"]["pas"] for x in v])), bust=float(np.mean([x["roll"]["bust"] for x in v])))
    return o


# ------------------------------------------------------------------ 2. NOISE preset C reference (session-17 stream, MNQ, 1 micro scaled by the plan size table 1/2/2/3)
base = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE__lock_.csv")
base = base[(base.d >= START) & (base.d <= END)].copy(); base["mkt"] = "MNQ"; base["strat"] = "NOISE"; base["var"] = "C"
RES = {}
for acct in (25, 50, 100, 150):
    A = ACCT[acct]; R = {}
    nz = base.assign(pnl=base.pnl * A["noise_n"], mae=base.mae * A["noise_n"], n=A["noise_n"])
    R["NOISE preset C (ref)"] = {"BOTH": summarize(nz, A, boot=True)}
    for conf in CONF:
        R[conf] = {}
        for scope in ("BOTH", "MNQ", "MGC"):
            g = build(conf, scope)
            if scope != "BOTH" and conf.startswith("COMB-3"): g = g
            t = select(g, acct, RANK)
            R[conf][scope] = summarize(t, A, boot=(scope == "BOTH"))
        R[conf]["RAND"] = rand_summary(build(conf, "BOTH"), acct, {}, seeds=20)
        # trades log for the combined (HO) for later inspection
        if conf.startswith("COMB") and acct == 25:
            select(build(conf, "BOTH"), acct, RANK).to_csv(HERE + f"/out/trades_{conf.split()[0]}_{acct}k.csv", index=False)
    # sensitivities (combined only)
    S = {}
    for conf in [k for k in CONF if k.startswith("COMB")]:
        g = build(conf, "BOTH")
        S[conf] = {"no day rules": summarize(select(g, acct, RANK, day_rules=False), A),
                   "budget 12.5% MLL": summarize(select(g, acct, RANK, frac=0.125), A),
                   "cap 2 micros": summarize(select(g, acct, RANK, cap=2), A),
                   "budget 50% MLL": summarize(select(g, acct, RANK, frac=0.5), A)}
    R["_sens"] = S
    RES[acct] = R
    print("acct", acct, "done", round(time.time() - t_start), "s", flush=True)
# ------------------------------------------------------------------ 3. every subset of the 4 strategies, first-signal-wins, 25K and 150K sizing (exploratory; IS-chosen subset judged on HO)
import itertools
SUB = []
for acct in (25, 150):
    A = ACCT[acct]
    for k in (1, 2, 3, 4):
        for ss in itertools.combinations(STR, k):
            g = P[P.strat.isin(ss).values]; t = select(g, acct, RANK)
            x = {e: pstats(era_slice(t, e)) for e in ("IS", "HO", "FULL")}
            SUB.append(dict(acct=acct, subset="+".join(ss), **{f"{e}_{k2}": v for e, d in x.items() for k2, v in d.items()},
                            HO_pass=eval_roll(t, A, "HO")["pas"], HO_bust=eval_roll(t, A, "HO")["bust"], FULL_pass=eval_roll(t, A, "FULL")["pas"], FULL_bust=eval_roll(t, A, "FULL")["bust"]))
pd.DataFrame(SUB).to_csv(HERE + "/out/subsets.csv", index=False)
json.dump(RES, open(HERE + "/out/results.json", "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print("done")
