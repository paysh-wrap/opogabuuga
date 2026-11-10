"""Pick best bust<LIM setup per plan on IS (funded yr-1 bust and eval bust < LIM), report HO. usage: pick.py [LIM=30]"""
import json, sys, os
LIM = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
def fmt(c):
    d = dict(c["cfg"]); d.pop("_c", None)
    return f"q={d['q']} stop=${c['stop']} lock={'P1' if c['lock'] else '-'} brake={d.get('brake','-')} fit={d.get('fit','-')} kill={d.get('kill','-')} dlock={d.get('dlock','-')}"
res = {}
for plan in ("25K", "50K", "100K", "150K"):
    p = f"{OUT}/grid_{plan}.json"
    if not os.path.exists(p): continue
    G = json.load(open(p))
    ok = [g for g in G if g["f_IS"]["bust"] < LIM and g["e_IS"]["bust"] < LIM]
    ok2 = [g for g in ok if g["f_HO"]["bust"] < LIM and g["e_HO"]["bust"] < LIM]
    best = max(ok, key=lambda g: g["f_IS"]["per2w"]) if ok else None
    bestho = max(ok2, key=lambda g: g["f_IS"]["per2w"] + g["f_HO"]["per2w"]) if ok2 else None   # config that holds under BOTH eras
    print(plan, "configs", len(G), "IS-feasible", len(ok), "feasible both", len(ok2))
    for tag, b in (("IS-pick", best), ("holds both eras", bestho)):
        if b: print("  ", tag, fmt(b), "| funded IS/HO bust %.0f/%.0f  per2w IS/HO $%.0f/$%.0f frozen HO %.0f%% anypay HO %.0f%% | eval IS/HO pass %.0f/%.0f bust %.0f/%.0f" % (
            b["f_IS"]["bust"], b["f_HO"]["bust"], b["f_IS"]["per2w"], b["f_HO"]["per2w"], b["f_HO"]["frozen"], b["f_HO"]["any_pay"], b["e_IS"]["pass_"], b["e_HO"]["pass_"], b["e_IS"]["bust"], b["e_HO"]["bust"]))
        else: print("  ", tag, "none")
    res[plan] = dict(is_pick=best, both=bestho)
json.dump(res, open(f"{OUT}/picks_{int(LIM)}.json", "w"), default=float)
