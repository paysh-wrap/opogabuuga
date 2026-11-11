import json
R = {m: json.load(open(f"out/results_{m}.json")) for m in ("MNQ", "MGC")}
f = lambda h, k: h.get(k, "-") if h.get("n") else "-"
L = []
for m in R:
    r = R[m]; L.append(f"\n### {m}\n80% rule: {json.dumps(r['_80rule'])}\n")
    L.append("| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net | HO maxDD | roll PASS/BUST % | med d | 12mo n | 12mo win% | 12mo PF | 12mo net | 12mo PASS/BUST | rand-entry HO PF |\n|" + "---|" * 17)
    for k, v in r.items():
        if k.startswith("_"): continue
        i, h, a = v["IS"], v["HO"], v["ALL"]
        L.append(f"| {k} | {f(i,'n') if i.get('n') else 0} | {f(i,'pf')} | {h.get('n',0)} | {f(h,'win')} | {f(h,'pf')} | {f(h,'avg')} | {f(h,'net')} | {f(h,'dd')} | {f(h,'passp')}/{f(h,'bust')} | {f(h,'med')} | {a.get('n',0)} | {f(a,'win')} | {f(a,'pf')} | {f(a,'net')} | {f(a,'passp')}/{f(a,'bust')} | {v['rand']['pf'] if v['rand'] else '-'} |")
    # pick per variant
    L.append(f"\n**IS-pick (best IS PF, IS n>=15) per variant, judged on HO ({m})**\n\n| variant | pick | IS n/PF | HO n | win% | PF | $/tr | net | maxDD | PASS/BUST | rand PF |\n|---|---|---|---|---|---|---|---|---|---|---|")
    vs = sorted({k.split(" / ")[0] for k in r if not k.startswith("_")})
    for vn in vs:
        c = [(k, v) for k, v in r.items() if k.startswith(vn + " /") and v["IS"].get("n", 0) >= 15]
        if not c: L.append(f"| {vn} | (IS n<15) | | | | | | | | | |"); continue
        k, v = max(c, key=lambda x: x[1]["IS"]["pf"]); h = v["HO"]
        L.append(f"| {vn} | {k.split(' / ',1)[1]} | {v['IS']['n']}/{v['IS']['pf']} | {h.get('n',0)} | {f(h,'win')} | {f(h,'pf')} | {f(h,'avg')} | {f(h,'net')} | {f(h,'dd')} | {f(h,'passp')}/{f(h,'bust')} | {v['rand']['pf'] if v['rand'] else '-'} |")
n = R["MNQ"]["_noiseC"]; L.append(f"\nNOISE preset C (MNQ): HO {json.dumps(n['HO'])} | 12mo {json.dumps(n['ALL'])}")
open("tables.md", "w").write("\n".join(L)); print("\n".join(L))
