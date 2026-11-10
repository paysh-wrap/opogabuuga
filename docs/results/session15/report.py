"""Print the markdown tables used in README.md from out/*.json, and write out/recommend.json (input of make_pdf.py)."""
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
F = json.load(open(f"{OUT}/final.json")); M = json.load(open(f"{OUT}/matrix.json"))
REC = {"25K": dict(q=1), "50K": dict(q=1), "100K": dict(q=2, brake=[0.7, 1]), "150K": dict(q=3, brake=[0.5, 1])}      # recommended (bust <= 25% = 10-pt margin)
THIN = {"50K": dict(q=1), "100K": dict(q=2, brake=[0.5, 1]), "150K": dict(q=3, brake=[0.5, 2])}                       # most income still < 35%
MLL = {"25K": 1000, "50K": 2000, "100K": 3000, "150K": 4500}


def size(c, plan=None):
    if "brake" not in c: return f"{c['q']} micro{'s' if c['q'] > 1 else ''}"
    th = f"${c['brake'][0] * MLL[plan]:,.0f}" if plan else f"{c['brake'][0] * 100:.0f}%"
    return f"{c['q']} micros, {c['brake'][1]} while the cushion is under {th}"


def find(tag, plan, cfg):
    for r in F["rows"]:
        if r["tag"] == tag and r["plan"] == plan and (tag == "live" or json.loads(json.dumps(r["fcfg"])) == cfg): return r


def cell(r, era):
    x = r[era]
    return (f"{x['eb']['pass_']:.0f}% / {x['eb']['bust']:.0f}%", f"{x['eh']['pass_']:.0f} / {x['eh']['bust']:.0f} / {x['eh']['open_']:.0f}", f"{x['eb']['med']:.0f}",
            f"{x['fb']['bust']:.0f}% ({x['fh']['bust']:.0f}%)", f"${x['fb']['per2w']:.0f}", f"${5 * x['fb']['per2w']:.0f}")


if __name__ == "__main__":
    print("## candidates")
    rows = []
    for f in ("candidates.json", "candidates2_mnq.json", "candidates2_mes.json", "candidates2_mgc.json", "candidates3.json"):
        rows += json.load(open(f"{OUT}/{f}"))
    seen = set()
    print("| candidate | market | target R:R | IS trades / win / PF / profit | HO trades / win / PF / profit | verdict |\n|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["name"].split()[0], r["sym"])):
        if r["key"] in seen: continue
        seen.add(r["key"])
        i, h = r["IS"], r["HO"]
        okis = i["pf"] >= 1.15 and i["n"] >= 100 and i["profit"] > 0
        v = ("passes IS and HO" if h["pf"] >= 1.15 and h["profit"] > 0 else "passes IS, FAILS held-out") if okis else ("too few trades" if i["n"] < 100 and i["pf"] >= 1.15 else "fails IS")
        rr = "trailing exit" if r["rr"] is None else (f"{r['rr']}" + (" **(violates R:R >= 1.5)**" if r["rr"] < 1.5 else ""))
        nm = r["name"]; nm = nm[:nm.rfind("(")].strip() if nm.endswith(")") and r["sym"] in nm[nm.rfind("("):] else nm
        print(f"| {nm} | {r['sym']} | {rr} | {i['n']} / {i['win']:.1f}% / {i['pf']:.2f} / ${i['profit']:,.0f} | {h['n']} / {h['win']:.1f}% / {h['pf']:.2f} / ${h['profit']:,.0f} | {v} |")
    print("\n## edges (mean $, sd $, ratio)"); print(json.dumps({k: {e: {a: round(b, 2) for a, b in v.items()} for e, v in d.items()} for k, d in M["edges"].items()}))
    print("\n## lock sensitivity")
    for s in F["sens"]: print(f"| +{s['trigger']} pt -> entry +{s['lock']} pt | {s['IS']['win']:.1f}% / {s['IS']['pf']:.2f} / ${s['IS']['profit']:,.0f} / {s['IS']['ratio']:.2f} | {s['HO']['win']:.1f}% / {s['HO']['pf']:.2f} / ${s['HO']['profit']:,.0f} / {s['HO']['ratio']:.2f} |")
    rec = {}
    for plan in REC:
        print(f"\n## {plan}")
        print("| setup | era | eval pass / bust (bootstrap) | eval pass / bust / open at 250 sessions (history) | median sessions to pass | funded bust yr 1: bootstrap (history) | income / 2 wk, 1 account | 5 accounts |\n|---|---|---|---|---|---|---|---|")
        sets = [("TODAY: NOISE alone, live sizes (eval " + size(find("live", plan, None)["ecfg"], plan) + "; funded " + size(find("live", plan, None)["fcfg"], plan) + ")", find("live", plan, None)),
                ("RECOMMENDED: NOISE + profit lock, " + size(REC[plan], plan), find("n1", plan, REC[plan]))]
        if plan in THIN and THIN[plan] != REC[plan]: sets.append(("most income still under 35%: " + size(THIN[plan], plan), find("n1", plan, THIN[plan])))
        for nm, r in sets:
            for era in ("IS", "HO"):
                print(f"| {nm} | {era} | " + " | ".join(cell(r, era)) + " |")
        rec[plan] = dict(size=size(REC[plan], plan), cfg=REC[plan], rec=find("n1", plan, REC[plan]), live=find("live", plan, None), thin=find("n1", plan, THIN[plan]) if plan in THIN else None,
                         thin_size=size(THIN[plan], plan) if plan in THIN else None, live_size_e=size(find("live", plan, None)["ecfg"], plan), live_size_f=size(find("live", plan, None)["fcfg"], plan))
        print(f"\n### {plan} all N1 sizings (HO bootstrap; IS in brackets)")
        print("| size | eval pass / bust | median sessions | funded bust yr 1 | income / 2 wk | OK? |\n|---|---|---|---|---|---|")
        for r in F["rows"]:
            if r["tag"] != "n1" or r["plan"] != plan: continue
            h, i = r["HO"], r["IS"]
            ok = all(x["eb"]["bust"] < 35 and x["fb"]["bust"] < 35 and x["eb"]["pass_"] >= 60 for x in (h, i)) and h["eh"]["bust"] < 35 and h["fh"]["bust"] < 35
            print(f"| {size(r['fcfg'], plan)} | {h['eb']['pass_']:.0f}% / {h['eb']['bust']:.0f}% [{i['eb']['pass_']:.0f} / {i['eb']['bust']:.0f}] | {h['eb']['med']:.0f} [{i['eb']['med']:.0f}] | {h['fb']['bust']:.0f}% [{i['fb']['bust']:.0f}] | ${h['fb']['per2w']:.0f} [${i['fb']['per2w']:.0f}] | {'yes' if ok else 'no'} |")
    json.dump(rec, open(f"{OUT}/recommend.json", "w"), default=float, indent=1)
    print("\n## strategies at the same size (HO bootstrap)")
    for plan, cfg in (("50K", dict(q=1)), ("150K", dict(q=3, brake=[0.5, 2]))):
        for r in M["rows"]:
            if r["plan"] == plan and json.loads(json.dumps(r["cfg"])) == cfg:
                h, i = r["HO"], r["IS"]
                print(f"| {r['stream']} | {plan} {size(cfg, plan)} | IS {i['eb']['pass_']:.0f}/{i['eb']['bust']:.0f}, funded bust {i['fb']['bust']:.0f}, ${i['fb']['per2w']:.0f} | HO {h['eb']['pass_']:.0f}/{h['eb']['bust']:.0f}, funded bust {h['fb']['bust']:.0f}, ${h['fb']['per2w']:.0f} |")
