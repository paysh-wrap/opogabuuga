import json
R = json.load(open("/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3/results_r3.json")); b = R["BUILT"]
def hs(m):
    v = [x for k, x in m["hy"].items() if k != "2026H2"]; return min(v), sorted(v)[len(v)//2], max(v)
f = lambda x: "-" if x is None else f"{x:.0f}"
print("| variant | pick pass/med | judge pass/med | all pass/med | stuck+bust % | profit | maxDD | +$2 all pass/judge/med | HY min/med/max | candidate |")
print("|---|---|---|---|---|---|---|---|---|---|")
for n, m in R.items():
    P, J, A, c = m["PICK"], m["JUDGE"], m["ALL"], m["cost2"]
    cand = "-"
    if n != "BUILT":
        ok = all(m[w]["pass_"] > b[w]["pass_"] and (m[w]["med"] or 999) < (b[w]["med"] or 999) for w in ("PICK", "JUDGE")) and m["profit"] >= b["profit"] - 1e-6 and A["pass_"] >= 70 and A["stuck_bust"] <= b["ALL"]["stuck_bust"] + 2
        near = m["JUDGE"]["pass_"] >= b["JUDGE"]["pass_"] and m["PICK"]["pass_"] >= b["PICK"]["pass_"] and (A["med"] or 999) < b["ALL"]["med"]
        cand = "**ADOPT CANDIDATE**" if ok else ("partial" if near else "no")
    h = hs(m)
    print(f"| {n} | {P['pass_']:.1f}/{f(P['med'])} | {J['pass_']:.1f}/{f(J['med'])} | {A['pass_']:.1f}/{f(A['med'])} | {A['stuck_bust']:.1f} | {m['profit']:.0f} | {m['dd']:.0f} | {c['ALL']['pass_']:.1f}/{c['JUDGE']['pass_']:.1f}/{f(c['ALL']['med'])} | {h[0]:.0f}/{h[1]:.0f}/{h[2]:.0f} | {cand} |")
