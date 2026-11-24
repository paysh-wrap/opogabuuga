"""Held-out tests 2026-11-24: baseline reproduction + 4 pre-registered ideas (8 variants) + random controls.
usage: python3 run_all.py   (writes results.json, prereg.json, *.csv into this folder; ~5 min on 4 cores)
Selection functions only see PICK-window numbers; the judge window is computed after the pick is frozen in prereg.json."""
import json, time
import numpy as np, pandas as pd
import hot_lib as H
from hot_lib import stats, paired_boot, win, PV

OUT = H.HERE
R = {}
NSEED = 500

PREREG = {
    "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "windows": H.WIN,
    "pass_rule": "judge net > base AND judge PF > base AND judge trades >= 60 AND beats its random control (pre-specified per idea); "
                 "an idea with no pick-window pick is REJECT without a judge verdict.",
    "ideas": {
        "1_entry_cadence": {"variants": {"E30a": "entry checks every 30 min 10:00..15:30 (k=29..359), exits stay hourly",
                                         "E30b": "entry checks every 30 min 10:00..15:00 (k=29..329), exits stay hourly"},
                            "pick_rule": "pick PF >= base AND pick net >= base; highest pick net among those",
                            "control": "(a) judge PF and net above the 95th pct of the random-direction version of the pick (500 seeds); "
                                       "(b) judge delta vs base above the 95th pct of random-direction deltas (same seeds)"},
        "2_vol_target_sizing": {"variants": {"VT": "Pro 50K frame (base = fixed 2 micros @ $250): q = clip(round(2 x target / vol14), 1, 3); "
                                                   "vol14 = std of the prior 14 RTH close-to-close returns; target = pick-window median vol14"},
                                "pick_rule": "pick net >= base AND pick Sharpe > base",
                                "extra_judge_rule": "judge Sharpe > base AND judge max DD <= base",
                                "control": "judge delta net above the 95th pct of 2000 random permutations of the same size vector"},
        "3_candace_regime_gate": {"variants": {"G1": "trade only if sig10 >= pick median", "G2": "only if sig10 < pick median",
                                               "G3": "only if or5 >= pick median", "G4": "only if or5 < pick median"},
                                  "features": "sig10 = prior-14-day mean |close(10:00)/open-1| (NOISE band at 10:00, known pre-open); "
                                              "or5 = 09:30-09:34 high-low / 14-day mean daily range (known at 09:35; every CANDACE entry is bar >= 5)",
                                  "pick_rule": "pick trades >= 60, pick PF > base, pick net >= base; highest pick PF",
                                  "control": "judge net and PF above the 95th pct of 5000 random subsets of the judge trades of the same size"},
        "4_leg_priority": {"variants": {"P1": "NOISE-first: if NOISE signals while a CANDACE/late position is open, flatten it at the open "
                                              "of the NOISE entry bar and enter NOISE one bar later (D139 wait-for-flat)"},
                           "baseline": "shipped first-come, one position per account; same-bar tie -> NOISE (dispatch order)",
                           "primary": "NOISE + CANDACE (1 micro each); secondary: + late-day leg",
                           "pick_rule": "pick combined net >= base AND pick PF >= base",
                           "control": "judge delta above the 95th pct of P1-vs-P0 deltas with a random-direction NOISE stream (500 seeds)"},
        "5_github_ports": "not run (no repo fetch; the two paper differences it would surface, 30-min checks and vol sizing, are ideas 1-2)",
    },
}


def pick_ok(rows, base, need):
    return [k for k, s in rows.items() if need(s, base)]


# ---------------------------------------------------------------- step 0: baselines
base = H.gen2()
ref = pd.read_csv(H.S20 + "/streams_BASE.csv")
assert len(base) == len(ref) == 654 and (base[["d", "ek", "xk", "side"]].values == ref[["d", "ek", "xk", "side"]].values).all()
assert np.allclose(base.pnl.values, ref.pnl.values) and round(base.pnl.sum()) == 19293
cand = H.candace(); late = H.late()
R["step0"] = {"noise": {w: stats(base, w) for w in ("pick", "judge", "all")},
              "noise_check": "654 trades, $19,293 = session20 BASE; trade-for-trade identical to session20/streams_BASE.csv",
              "candace":{w: stats(cand, w) for w in ("pick", "judge", "all")},
              "candace_full_IS": dict(n=int((cand.d <= "2023-12-31").sum()), net=round(float(cand[cand.d <= "2023-12-31"].pnl.sum()), 0)),
              "late": {w: stats(late, w) for w in ("pick", "judge", "all")}}
base.to_csv(OUT + "/noise_base_trades.csv", index=False)

# ---------------------------------------------------------------- idea 1: entry cadence
E1 = {"E30a": dict(ent_checks=range(29, 360, 30)), "E30b": dict(ent_checks=range(29, 330, 30))}
T1 = {k: H.gen2(**v) for k, v in E1.items()}
pick1 = {k: stats(t, "pick") for k, t in T1.items()}
bp = stats(base, "pick")
el = pick_ok(pick1, bp, lambda s, b: s["pf"] >= b["pf"] and s["net"] >= b["net"])
PREREG["ideas"]["1_entry_cadence"]["pick_result"] = (max(el, key=lambda k: pick1[k]["net"]) if el else None)
# ---------------------------------------------------------------- idea 2: vol-target sizing (picks need only pick-window data)
closes = np.array([a["close"][H.NB - 1] for _, a in H.D]); rets = np.r_[np.nan, closes[1:] / closes[:-1] - 1]
vol = {}
for i, d in enumerate(H.DATES):
    r = rets[max(1, i - 14):i]
    if len(r) >= 10: vol[d] = float(np.std(r, ddof=1))
pick_days = [d for d in H.DATES if H.PICK0 <= d <= H.PICK1 and d in vol]
target = float(np.median([vol[d] for d in pick_days]))
b2 = base.copy(); b2["q"] = 2; b2["pnl"] = base.pnl * 2
vt = base.copy(); vt["q"] = [int(np.clip(round(2 * target / vol[d]), 1, 3)) for d in vt.d]; vt["pnl"] = base.pnl * vt.q
s_b2, s_vt = stats(b2, "pick"), stats(vt, "pick")
PREREG["ideas"]["2_vol_target_sizing"]["target_vol14"] = target
PREREG["ideas"]["2_vol_target_sizing"]["pick_result"] = "VT" if (s_vt["net"] >= s_b2["net"] and s_vt["sharpe"] > s_b2["sharpe"]) else None
# ---------------------------------------------------------------- idea 3: CANDACE regime gate
rng_d = {d: float(np.nanmax(a["high"]) - np.nanmin(a["low"])) for d, a in H.D}
feat = {}
for i, (d, a) in enumerate(H.D):
    if i < 14: continue
    atr = np.mean([rng_d[x] for x in H.DATES[i - 14:i]])
    feat[d] = dict(sig10=float(np.mean(H.MOVES[i - 14:i, 29])), or5=float((np.nanmax(a["high"][:5]) - np.nanmin(a["low"][:5])) / atr))
fd = pd.DataFrame(feat).T
med = {f: float(fd.loc[(fd.index >= H.PICK0) & (fd.index <= H.PICK1), f].median()) for f in ("sig10", "or5")}
cand = cand[cand.d >= H.PICK0].copy()
cand["sig10"] = [feat[d]["sig10"] for d in cand.d]; cand["or5"] = [feat[d]["or5"] for d in cand.d]
G = {"G1": cand.sig10 >= med["sig10"], "G2": cand.sig10 < med["sig10"], "G3": cand.or5 >= med["or5"], "G4": cand.or5 < med["or5"]}
TG = {k: cand[m] for k, m in G.items()}
pick3 = {k: stats(t, "pick") for k, t in TG.items()}
cp = stats(cand, "pick")
el = pick_ok(pick3, cp, lambda s, b: s["n"] >= 60 and s["pf"] > b["pf"] and s["net"] >= b["net"])
PREREG["ideas"]["3_candace_regime_gate"]["medians"] = med
PREREG["ideas"]["3_candace_regime_gate"]["pick_result"] = (max(el, key=lambda k: pick3[k]["pf"]) if el else None)


# ---------------------------------------------------------------- idea 4: leg priority (combination engine)
def legs(noise, with_late):
    ev = {}
    for r in noise.itertuples(): ev.setdefault(r.d, []).append((r.ek, 0, r.xk, r.pnl, r.side, r.entry))
    for r in cand.itertuples(): ev.setdefault(r.d, []).append((r.idx, 1, r.exit_idx, r.pnl, r.side, r.entry))
    if with_late:
        for r in late.itertuples(): ev.setdefault(r.d, []).append((r.idx, 2, r.exit_idx, r.pnl, r.side, H.BARS[r.d]["open"][r.idx]))
    for v in ev.values(): v.sort(key=lambda x: (x[0], x[1]))
    return ev


def combine(ev, policy):
    """P0 first-come (NOISE may re-enter on the bar its own previous trade exits, as lib50.sim_a); P1 NOISE-first."""
    out, cnt = [], {"noise_blocked_by_cand": 0, "noise_blocked_by_late": 0, "cand_blocked_by_noise": 0, "late_blocked_by_noise": 0,
                    "late_blocked_by_cand": 0, "flattened_cand": 0, "flattened_late": 0}
    nm = {0: "noise", 1: "cand", 2: "late"}
    for d, v in ev.items():
        o = H.BARS[d]["open"]; free, last, cur = -1, -1, None
        for (m_in, kind, m_out, pnl, side, entry) in v:
            if m_in <= free and not (kind == 0 and last == 0):
                if policy == "P1" and kind == 0 and last in (1, 2) and m_in + 1 < H.NB:
                    k0, s0, e0 = cur
                    fl = s0 * (o[m_in] - e0) * PV - 2.0                     # flatten the other leg at the open of the NOISE entry bar
                    out[-1] = dict(d=d, kind=k0, pnl=fl, ek=out[-1]["ek"], xk=m_in)
                    cnt["flattened_" + nm[k0]] += 1
                    adj = pnl - side * (o[m_in + 1] - o[m_in]) * PV           # NOISE fills one bar later (wait for the flat)
                    out.append(dict(d=d, kind=0, pnl=adj, ek=m_in + 1, xk=m_out)); free, last, cur = m_out, 0, (0, side, entry)
                    continue
                key = f"{nm[kind]}_blocked_by_{nm[last]}"
                if key in cnt: cnt[key] += 1
                continue
            out.append(dict(d=d, kind=kind, pnl=pnl, ek=m_in, xk=m_out)); free, last, cur = m_out, kind, (kind, side, entry)
    return pd.DataFrame(out), cnt


EV = {wl: legs(base, wl) for wl in (False, True)}
C4 = {(wl, p): combine(EV[wl], p) for wl in (False, True) for p in ("P0", "P1")}
s40, s41 = stats(C4[(False, "P0")][0], "pick"), stats(C4[(False, "P1")][0], "pick")
PREREG["ideas"]["4_leg_priority"]["pick_result"] = "P1" if (s41["net"] >= s40["net"] and s41["pf"] >= s40["pf"]) else None
json.dump(PREREG, open(OUT + "/prereg.json", "w"), indent=1, default=str)

# ================================================================ JUDGE (picks frozen above)
WS = ("pick", "judge", "all")
R["idea1"] = {"base": {w: stats(base, w) for w in WS}, **{k: {w: stats(t, w) for w in WS} for k, t in T1.items()},
              "pick": PREREG["ideas"]["1_entry_cadence"]["pick_result"],
              "boot_judge": {k: paired_boot(base, t, "judge") for k, t in T1.items()},
              "by_year_pf": {k: {y: stats(t[t.d.str[:4] == y].assign(), "all")["pf"] for y in ("2022", "2023", "2024", "2025", "2026")}
                             for k, t in {"base": base, **T1}.items()}}
p1 = R["idea1"]["pick"] or "E30a"   # the control is run on the pick; if there is no pick, on E30a (FYI only)
rv, rb = [], []
for s in range(NSEED):
    tv = H.gen2(rnd=s, **E1[p1]); tb = H.gen2(rnd=s)
    rv.append(stats(tv, "judge")); rb.append(stats(tb, "judge"))
real = R["idea1"][p1]["judge"]; rbase = R["idea1"]["base"]["judge"]
pfv = np.array([x["pf"] for x in rv]); nv = np.array([x["net"] for x in rv]); dn = nv - np.array([x["net"] for x in rb])
R["idea1"]["control"] = dict(variant=p1, rand_pf_p95=round(float(np.percentile(pfv, 95)), 3), rand_net_p95=round(float(np.percentile(nv, 95)), 0),
                             rand_pf_mean=round(float(pfv.mean()), 3), real_pf=real["pf"], real_net=real["net"],
                             pct_rank_pf=round(float((pfv < real["pf"]).mean() * 100), 1),
                             rand_delta_p95=round(float(np.percentile(dn, 95)), 0), rand_delta_mean=round(float(dn.mean()), 0),
                             real_delta=real["net"] - rbase["net"], pct_rank_delta=round(float((dn < real["net"] - rbase["net"]).mean() * 100), 1))

R["idea2"] = {"base_2micro": {w: stats(b2, w) for w in WS}, "VT": {w: stats(vt, w) for w in WS},
              "base_1micro": {w: stats(base, w) for w in WS}, "pick": PREREG["ideas"]["2_vol_target_sizing"]["pick_result"],
              "avg_micros": {w: round(float(win(vt, w).q.mean()), 3) for w in WS},
              "size_mix_judge": win(vt, "judge").q.value_counts().sort_index().to_dict(),
              "boot_judge": paired_boot(b2, vt, "judge")}
rnd = np.random.default_rng(5); vj = win(vt, "judge"); q = vj.q.values; p = win(base, "judge").pnl.values
perm = np.array([(rnd.permutation(q) * p).sum() for _ in range(2000)])
R["idea2"]["control"] = dict(real_net=float((q * p).sum()), perm_p95=round(float(np.percentile(perm, 95)), 0), perm_mean=round(float(perm.mean()), 0),
                             pct_rank=round(float((perm < (q * p).sum()).mean() * 100), 1))

R["idea3"] = {"base": {w: stats(cand, w) for w in WS}, **{k: {w: stats(t, w) for w in WS} for k, t in TG.items()},
              "pick": PREREG["ideas"]["3_candace_regime_gate"]["pick_result"], "medians": med}
cj = win(cand, "judge").pnl.values; rnd = np.random.default_rng(9)
for k, t in TG.items():
    n = len(win(t, "judge")); nets, pfs = [], []
    for _ in range(5000):
        s = rnd.choice(cj, n, replace=False); nets.append(s.sum()); ls = -s[s < 0].sum(); pfs.append(s[s > 0].sum() / ls if ls > 0 else 9)
    R["idea3"][k]["control"] = dict(net_p95=round(float(np.percentile(nets, 95)), 0), pf_p95=round(float(np.percentile(pfs, 95)), 3),
                                    pct_rank_net=round(float((np.array(nets) < R["idea3"][k]["judge"]["net"]).mean() * 100), 1))

R["idea4"] = {}
for wl in (False, True):
    nm = "noise_cand_late" if wl else "noise_cand"
    R["idea4"][nm] = {p: {**{w: stats(C4[(wl, p)][0], w) for w in WS}, "counts_all": C4[(wl, p)][1],
                          "counts_judge": combine({d: v for d, v in EV[wl].items() if d >= H.JUD0}, p)[1]} for p in ("P0", "P1")}
    R["idea4"][nm]["boot_judge"] = paired_boot(C4[(wl, "P0")][0], C4[(wl, "P1")][0], "judge")
R["idea4"]["pick"] = PREREG["ideas"]["4_leg_priority"]["pick_result"]
R["idea4"]["standalone_sum_judge"] = round(float(win(base, "judge").pnl.sum() + win(cand, "judge").pnl.sum()), 0)
dl = []
for s in range(NSEED):
    ev = legs(H.gen2(rnd=s), False)
    dl.append(stats(combine(ev, "P1")[0], "judge")["net"] - stats(combine(ev, "P0")[0], "judge")["net"])
rd = R["idea4"]["noise_cand"]["P1"]["judge"]["net"] - R["idea4"]["noise_cand"]["P0"]["judge"]["net"]
R["idea4"]["control"] = dict(real_delta=rd, rand_delta_p95=round(float(np.percentile(dl, 95)), 0), rand_delta_mean=round(float(np.mean(dl)), 0),
                             pct_rank=round(float((np.array(dl) < rd).mean() * 100), 1))
R["variants_tried"] = {"idea1": 2, "idea2": 1, "idea3": 4, "idea4": 1, "idea5": 0, "total": 8}

json.dump(R, open(OUT + "/results.json", "w"), indent=1, default=str)
rows = []
for idea, keys in (("idea1", ["base", "E30a", "E30b"]), ("idea2", ["base_2micro", "VT"]), ("idea3", ["base", "G1", "G2", "G3", "G4"])):
    for k in keys:
        for w in ("pick", "judge"): rows.append(dict(idea=idea, variant=k, window=w, **{c: R[idea][k][w][c] for c in ("n", "win", "pf", "net", "avg", "dd", "sharpe")}))
for nm in ("noise_cand", "noise_cand_late"):
    for p in ("P0", "P1"):
        for w in ("pick", "judge"): rows.append(dict(idea="idea4_" + nm, variant=p, window=w, **{c: R["idea4"][nm][p][w][c] for c in ("n", "win", "pf", "net", "avg", "dd", "sharpe")}))
pd.DataFrame(rows).to_csv(OUT + "/pick_judge_table.csv", index=False)
print(json.dumps(PREREG["ideas"], indent=1, default=str)[:3000])
print(json.dumps(R, indent=1, default=str))
