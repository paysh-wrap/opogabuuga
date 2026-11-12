import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, lib
J = json.load(open(lib.OUT + "/review_results.json")); R = J["results"]; P = J["picks"]; Vd = J["verdicts"]
R = dict(sorted(R.items(), key=lambda kv: (kv[1]["family"] != "BASE", kv[1]["family"], kv[0])))
b = R["BASE"]
f = lambda x, n=2: "-" if x is None else f"{x:.{n}f}"
def row(v, era):
    s = R[v][era]; bt = s["boot"]
    return f"| {v} | {R[v]['label']} | {s['n']:.0f} | {f(s['win'],1)} | {f(s['pf'])} | {f(s['avg'])} | {s['net']:.0f} | {s['dd']:.0f} | " + " | ".join(f"{bt[z]['pass_']:.0f}/{bt[z]['bust']:.0f}" for z in ("25","50","100","150")) + " |"
H = "| id | variant | trades | win% | PF | $/trade | net $ | maxDD $ | 25K p/b | 50K p/b | 100K p/b | 150K p/b |\n|---|---|---|---|---|---|---|---|---|---|---|---|"
L = []
L.append("# Session 20 strategy review - NOISE baseline refinements (MNQ, 1 micro)\n")
L.append("## 1. Verdict\n")
L.append("| family | pick (IS only) | IS PF / $/tr / net / 25K pass | J PF / $/tr / net / 25K pass | verdict | reason |\n|---|---|---|---|---|---|")
L.append(f"| BASE | - | {f(b['IS']['pf'])} / {f(b['IS']['avg'])} / {b['IS']['net']:.0f} / {b['IS']['boot']['25']['pass_']:.0f}% | {f(b['J']['pf'])} / {f(b['J']['avg'])} / {b['J']['net']:.0f} / {b['J']['boot']['25']['pass_']:.0f}% | - | shipped config |")
names = dict(F1="MES confirmation", F2="price-scaled lock", F3="band-scaled lock", F4="2nd ratchet", F5="exit cadence", F6="exit rule")
for fam in ("F1","F2","F3","F4","F5","F6"):
    p = P[fam]
    if not p:
        L.append(f"| {fam} {names[fam]} | none eligible | - | - | REJECT | no variant met IS eligibility (PF>=base, net>=90%, n>=100) |"); continue
    i, j, v = R[p]["IS"], R[p]["J"], Vd[fam]
    fails = [("J " if k in v["J"] else "")+k for k in []]
    fl = [f"J {k}" for k, ok in v["J"].items() if not ok] + [f"IS {k}" for k, ok in v["IS"].items() if not ok]
    L.append(f"| {fam} {names[fam]} | {p} ({R[p]['label']}) | {f(i['pf'])} / {f(i['avg'])} / {i['net']:.0f} / {i['boot']['25']['pass_']:.0f}% | {f(j['pf'])} / {f(j['avg'])} / {j['net']:.0f} / {j['boot']['25']['pass_']:.0f}% (bust {j['boot']['25']['bust']:.0f}%) | {'ADOPT' if v['adopt'] else 'REJECT'} | {'all criteria met' if v['adopt'] else 'failed: ' + ', '.join(fl)} |")
L.append(f"\nAdopted families: {J['adopted'] or 'none'}. Combination test: {'not run (needs >= 2 adopted)' if not J['combo'] else J['combo']}.\n")
rn = J["random"]; rp = np.array([r["Jboot"]["pass_"] for r in rn]); rpf = np.array([r["J"]["pf"] for r in rn]); rnet = np.array([r["J"]["net"] for r in rn]); rip = np.array([r["ISboot"]["pass_"] for r in rn]); ripf = np.array([r["IS"]["pf"] for r in rn])
L.append("**Random-direction benchmark** (baseline timing/exits/lock, side random, 30 seeds): "
 f"J 25K pass mean {rp.mean():.1f}% (min {rp.min():.0f}, max {rp.max():.0f}, sd {rp.std():.1f}) vs baseline {b['J']['boot']['25']['pass_']:.0f}%; J PF mean {rpf.mean():.2f} (range {rpf.min():.2f}-{rpf.max():.2f}) vs {b['J']['pf']:.2f}; J net mean {rnet.mean():.0f} vs {b['J']['net']:.0f}. "
 f"IS 25K pass mean {rip.mean():.1f}%, IS PF mean {ripf.mean():.2f} vs baseline IS {b['IS']['boot']['25']['pass_']:.0f}% / {b['IS']['pf']:.2f}.\n")
L.append("## 2. Baseline reproduction (step 0)\n")
L.append("Baseline stream (gen with Monday skip) vs `session19/refine/streams_noise_R6.csv` on 2021-10-21..2026-10-30: mine 654 trades, net $19,293; reference 654 trades, net $19,293; 654/654 (100%) identical on (d, ek, xk, side), identical P&L. Reproduction passes. (Reference 2019-2026 file apparently shares the same underlying bars/VWAP for this span.)\n")
L.append("## 3. Full tables (p/b = bootstrap pass % / bust %; Lucid Pro, 600 paths x 400 sessions, 10-day blocks, seed 7)\n")
for era, nm in (("IS","IS 2021-10-21..2025-11-05"),("J","J 2025-11-06..2026-10-30"),("ALL","ALL")):
    L.append(f"### {nm}\n\n{H}")
    for v in R:
        if v == "COMBO": pass
        tag = "" 
        L.append(row(v, era).replace(f"| {v} |", f"| {v}{' *PICK*' if v in P.values() else ''}{' (elig.)' if R[v].get('eligible') and v not in P.values() else ''} |", 1))
    L.append("")
L.append("(*PICK* = selected on IS; (elig.) = passed IS eligibility but not the best; unmarked rows were not picked, FYI only.)\n")
L.append("### Paired block-bootstrap 95% CI of net difference vs base ($)\n\n| id | J delta [lo, hi] | IS delta [lo, hi] |\n|---|---|---|")
for v in R:
    if v == "BASE": continue
    d, i = R[v]["dJ"], R[v]["dIS"]
    L.append(f"| {v} | {d[0]:.0f} [{d[1]:.0f}, {d[2]:.0f}] | {i[0]:.0f} [{i[1]:.0f}, {i[2]:.0f}] |")
L.append("\n### PF by calendar year (n trades)\n\n| id | 2022 | 2023 | 2024 | 2025 | 2026 |\n|---|---|---|---|---|---|")
for v in R:
    y = R[v]["years"]; L.append(f"| {v} | " + " | ".join((f"{f(y[k]['pf'])} ({y[k]['n']})" if k in y else "-") for k in ("2022","2023","2024","2025","2026")) + " |")
L.append("\n### Selection details\n")
for fam in ("F1","F2","F3","F4","F5","F6"):
    L.append(f"- {fam}: eligible = {[v for v in R if R[v]['family']==fam and R[v].get('eligible')]}; pick = {P[fam]}")
L.append("\n## 4. Caveats\n")
L.append("- J is ~245 sessions (118 baseline trades): wide uncertainty; see paired CIs. J was seen in earlier sessions, so it is not a pristine holdout.\n- Multiple testing: about 25 variant rows, so roughly one false positive is expected by chance.\n- News blackouts / event days are not modelled. No volume, VWAP is the precomputed series. Fees $1 RT + 1 tick per fill, 1 micro.\n- Interpretation choices: ratchet exits (F4) do not end NOISE for the day (only the +10 lock stop-out does); F5 extra exit checks at k=29+30n / 29+15n up to 15:00 (entries remain hourly); F3 sigma_k is the check-bar sigma at the entry decision; 'within 1 pt' = not worse by more than 1 pt.\n- Eval bootstraps for IS/J draw from a bday calendar of that window (days without trades count as zero).")
open(lib.OUT + "/RESULTS.md", "w").write("\n".join(L) + "\n")
