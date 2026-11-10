"""Format out/results_pm_fade.json (from pm_fade_d57_study.py run) as markdown tables."""
import json
R = json.load(open("/home/user/opogabuuga/docs/results/session11/out/results_pm_fade.json"))
g = {(r["kind"], r["name"], r["fm"]): r for r in R}
p = lambda x: "nan" if x != x else f"{x:.1%}"
L = []
names_e = [k[1] for k in g if k[0] == "E" and k[2] == "code"]; names_f = [k[1] for k in g if k[0] == "F" and k[2] == "code"]
L.append("### EVAL (kill $50; pass / bust / frozen / median sessions to pass)\n")
L.append("| plan | variant | pass | bust | frozen | med sess | held-out pass 2024-26 / frozen | era1 pass 2021-23 / frozen |\n|---|---|---|---|---|---|---|---|")
for n in names_e:
    for fm, lab in (("code", "V0 current"), ("tighten", "V1 tightened")):
        r = g[("E", n, fm)]; a, e1, e2 = r["all"], r["e1"], r["e2"]
        L.append(f"| {n} | {lab} | {p(a['pass_'])} | {p(a['bust'])} | {p(a['frozen'])} | {a['med']:.0f} | {p(e2['pass_'])} / {p(e2['frozen'])} (bust {p(e2['bust'])}) | {p(e1['pass_'])} / {p(e1['frozen'])} (bust {p(e1['bust'])}) |")
L.append("\n### FUNDED year 1, per account (260 sessions, D68 cadence)\n")
L.append("| plan | variant | bust | mean per 2 wk | mean yr-1 | held-out 2024-26 per 2 wk / bust | era1 2021-23 per 2 wk / bust | frozen |\n|---|---|---|---|---|---|---|---|")
for n in names_f:
    for fm, lab in (("code", "V0 current"), ("tighten", "V1 tightened")):
        r = g[("F", n, fm)]; a, e1, e2 = r["all"], r["e1"], r["e2"]
        L.append(f"| {n} | {lab} | {p(a['bust'])} | ${a['take']/26:,.0f} | ${a['take']:,.0f} | ${e2['take']/26:,.0f} / {p(e2['bust'])} | ${e1['take']/26:,.0f} / {p(e1['bust'])} | {p(a['frozen'])} |")
L.append("\n### FADE trades (aggregated over all rolling starts; fade signals = signals on days NOISE took no trade)\n")
L.append("| run | variant | fade trades | win% | PF | avg win/loss | tightened % of fade trades | tightened trades stopped | fade signals | skipped | of which PAUSE / DEEP / WORST |\n|---|---|---|---|---|---|---|---|---|---|---|")
for k, r in g.items():
    kind, n, fm = k; a = r["all"]
    lab = "V0" if fm == "code" else "V1"
    L.append(f"| {kind} {n} | {lab} | {a['fade_n']:,.0f} | {p(a['fade_wr'])} | {a['fade_pf']:.2f} | ${a['fade_aw']:.0f} / ${a['fade_al']:.0f} | {p(a['fade_tight'])} | {p(a['fade_stop_of_tight'])} | {a['fsig']:,.0f} | {p(a['fskip']/a['fsig'] if a['fsig'] else 0)} | {a['fpause']:,.0f} / {a['fdeep']:,.0f} / {a['fworst']:,.0f} |")
L.append("\n### NOISE side (should be identical V0 vs V1 only when path is the same; differences come from account paths)\n")
L.append("| run | variant | NOISE trades | win% | PF | all-trades win% | PF |\n|---|---|---|---|---|---|---|")
for k, r in g.items():
    kind, n, fm = k; a = r["all"]
    L.append(f"| {kind} {n} | {'V0' if fm=='code' else 'V1'} | {a['noise_n']:,.0f} | {p(a['noise_wr'])} | {a['noise_pf']:.2f} | {p(a['all_wr'])} | {a['all_pf']:.2f} |")
open("/home/user/opogabuuga/docs/results/session11/out/tables.md", "w").write("\n".join(L)); print("\n".join(L))
