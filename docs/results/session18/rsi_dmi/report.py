import sys, json, os
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/rsi_dmi")
from lib import stats, S, pd, np, OUT
def fn(k, m): return OUT + f"/stream_{m}_" + k.replace(" ", "_").replace("=", "").replace("+", "p").replace(">", "g").replace("(", "").replace(")", "").replace(",", "") + ".csv.gz"
R = {m: json.load(open(OUT + f"/results_{m}.json")) for m in ("MNQ", "MGC")}
names = [k for k in R["MNQ"] if k != "NOISE preset C"]
comb = {}
for k in names:
    ts = [pd.read_csv(fn(k, m)) for m in ("MNQ", "MGC") if os.path.exists(fn(k, m))]
    t = pd.concat(ts, ignore_index=True)
    comb[k] = dict(fam=R["MNQ"][k]["fam"], IS=stats(t, "IS"), HO=stats(t, "HO"))
R["COMB"] = comb
json.dump(comb, open(OUT + "/results_COMB.json", "w"), indent=1)
def f(x, key, d=1): return "-" if x.get(key) is None or x.get(key) != x.get(key) else (f"{x[key]:,.{d}f}")
L = []
for m, title in (("MNQ", "MNQ (1 micro)"), ("MGC", "MGC (1 micro gold, info only - OFF in app plans)"), ("COMB", "MNQ + MGC combined (one account trades both, concatenated streams)")):
    L += [f"\n### {title}", "| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net $ | HO maxDD $ | roll PASS/BUST % | med days | random-dir HO PF |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    fams = {}
    for k in names:
        r = R[m][k]; fams.setdefault(r["fam"], []).append(k)
    picks = set()
    for fam, ks in fams.items():
        c = [k for k in ks if R[m][k]["IS"].get("n", 0) >= 30]
        if c: picks.add(max(c, key=lambda k: R[m][k]["IS"]["pf"]))
    for k in names:
        r = R[m][k]; i, h = r["IS"], r["HO"]
        if h.get("n", 0) == 0: L.append(f"| {k} | {i.get('n',0)} | - | 0 | - | - | - | - | - | - | - | - |"); continue
        rb = (r.get("rand_HO") or {}).get("pf", "-")
        nm = f"**PICK** {k}" if k in picks else k
        L.append(f"| {nm} | {i.get('n',0)} | {i.get('pf','-')} | {h['n']} | {h['win']} | {h['pf']} | {h['avg']} | {h['net']:,} | {h['dd']:,} | {f(h,'passp')}/{f(h,'bust')} | {f(h,'med',0)} | {rb} |")
    if m == "MNQ":
        base = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE__lock_.csv"); base = base[base.d >= "2025-11-06"]; h = stats(base, "HO"); i = stats(base, "IS")
        L.append(f"| NOISE preset C (same 12 mo) | {i['n']} | {i['pf']} | {h['n']} | {h['win']} | {h['pf']} | {h['avg']} | {h['net']:,} | {h['dd']:,} | {f(h,'passp')}/{f(h,'bust')} | {f(h,'med',0)} | - |")
open(OUT + "/tables.md", "w").write("\n".join(L)); print("\n".join(L))
