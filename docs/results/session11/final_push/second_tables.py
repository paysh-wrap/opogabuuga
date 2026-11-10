"""print markdown tables from second_mix.json. usage: second_tables.py"""
import json
R = json.load(open("/home/user/opogabuuga/docs/results/session11/final_push/second_mix.json"))
base = {(r["kind"], r["plan"]): r for r in R if r["mkt"] is None}
print("| plan | size | funded $/yr all (H1 / H2) | bust | frozen | eval pass all (H1 / H2) | eval bust | eval frozen | beats MNQ both halves? |"); print("|---|---|---|---|---|---|---|---|---|")
for p in ("50K", "100K", "150K"):
    for m, nx in sorted({(r["mkt"] or "", r["nx"]) for r in R if r["plan"] == p}):
        f = next(r for r in R if r["kind"] == "F" and r["plan"] == p and (r["mkt"] or "") == m and r["nx"] == nx)
        e = next(r for r in R if r["kind"] == "E" and r["plan"] == p and (r["mkt"] or "") == m and r["nx"] == nx)
        bf, be = base[("F", p)], base[("E", p)]
        q = {"50K": 2, "100K": 2, "150K": 3}[p]
        size = f"{q} MNQ (today)" if not m else f"{q - 1} MNQ + {nx} {m.upper()}"
        ok = "-" if not m else ("YES" if all(f[h]["take"] > bf[h]["take"] and e[h]["pass_"] > be[h]["pass_"] and f[h]["bust"] <= bf[h]["bust"] and e[h]["bust"] <= be[h]["bust"] for h in ("e1", "e2")) else
              "no (" + ", ".join(x for x, c in (("income H1", f["e1"]["take"] > bf["e1"]["take"]), ("income H2", f["e2"]["take"] > bf["e2"]["take"]), ("pass H1", e["e1"]["pass_"] > be["e1"]["pass_"]),
                                                  ("pass H2", e["e2"]["pass_"] > be["e2"]["pass_"]), ("bust", all(f[h]["bust"] <= bf[h]["bust"] and e[h]["bust"] <= be[h]["bust"] for h in ("e1", "e2")))) if not c) + " worse)")
        print(f"| {p} | {size} | {f['all']['take']:,.0f} ({f['e1']['take']:,.0f} / {f['e2']['take']:,.0f}) | {f['all']['bust']:.1%} | {f['all']['frozen']:.0%} | "
              f"{e['all']['pass_']:.1%} ({e['e1']['pass_']:.1%} / {e['e2']['pass_']:.1%}) | {e['all']['bust']:.1%} | {e['all']['frozen']:.0%} | {ok} |")
print(); print("conflict skips / forced closes (funded runs):", {(r["plan"], r["mkt"], r["nx"]): r["cnt"] for r in R if r["kind"] == "F" and r["mkt"]})
