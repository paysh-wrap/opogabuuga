"""Stage 2: IS-only selection per family, best-2 combination, Lucid Pro 150K account harness (session-15 engine, 3 micros / 1 while cushion < $2,250).
Writes stage2.json."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "/home/user/opogabuuga/docs/results/session15")
from multiprocessing import Pool
import numpy as np, pandas as pd
import sharpen as S, lib, account as A
import study

CFG = dict(q=3, brake=(0.5, 1))   # 150K: cushion < 0.5 * 4,500 = $2,250 -> 1 micro


def ratio(t, era):
    x = t[t.d <= S.SPLIT] if era == "IS" else t[t.d > S.SPLIT]
    return float(2 * x.pnl.mean() / x.pnl.std() ** 2 * 1000)


def acct(a):
    name, fn = a
    t = pd.read_csv(f"{HERE}/streams/{fn}.csv", dtype={"d": str})
    return name, A.full(lib.day_table(t), lib.plan_rules("150K"), CFG, CFG)


def family(n):
    if n.startswith("lock"): return "lock"
    if n.startswith("no entry"): return "hours"
    if "reverse" in n or "flip" in n: return "norev"
    if n.startswith("VWAP"): return "vwap"
    if n.startswith("min"): return "width"
    return "base"


if __name__ == "__main__":
    s1 = json.load(open(HERE + "/stage1.json"))["variants"]
    base = s1["BASE (lock 100->+10)"]
    streams = {n: pd.read_csv(f"{HERE}/streams/{d['file']}.csv", dtype={"d": str}) for n, d in s1.items()}
    rb = ratio(streams["BASE (lock 100->+10)"], "IS")
    # ---- IS-only selection: eligible = IS PF >= base, IS net >= 90% of base, IS maxdd <= base*1.05 ; pick best IS edge ratio
    sel = {}; table = []
    for n, d in s1.items():
        f = family(n)
        if f == "base": continue
        r = ratio(streams[n], "IS")
        ok = d["IS"]["pf"] >= base["IS"]["pf"] and d["IS"]["net"] >= 0.9 * base["IS"]["net"] and d["IS"]["dd"] <= 1.05 * base["IS"]["dd"]
        table.append(dict(name=n, family=f, is_ratio=r, eligible=bool(ok)))
        if ok and (f not in sel or r > sel[f][1]): sel[f] = (n, r)
    print("IS-selected per family:", {f: v for f, v in sel.items()}, "base IS ratio", rb)
    # ---- best 2 families by IS ratio -> combination
    ranked = sorted([(r, f, n) for f, (n, r) in sel.items() if r > rb], reverse=True)
    combo = None
    if len(ranked) >= 2:
        kw = {}
        for _, f, n in ranked[:2]:
            k = dict(s1[n]["kw"])
            if "hours" in k: k["hours"] = set(k["hours"])
            if "lock" in k: k["lock"] = tuple(k["lock"])
            kw.update(k)
        t = S.gen(**kw)
        cn = "COMBO " + " + ".join(n for _, f, n in ranked[:2])
        fn = "COMBO"; t.to_csv(f"{HERE}/streams/{fn}.csv", index=False)
        s1[cn] = dict(file=fn, kw={k: (sorted(v) if isinstance(v, set) else v) for k, v in kw.items()}, **{e: S.stats(t, e) for e in ("IS", "HO", "L12")})
        combo = cn
    # ---- account harness
    todo = {"BASE (lock 100->+10)"} | {n for n, d in s1.items() if family(n) == "lock"} | {v[0] for v in sel.values()} | ({combo} if combo else set())
    # also run the single best-by-HO-visible? no: only IS-selected + lock grid + base + combo
    with Pool(4) as p: acc = dict(p.map(acct, [(n, s1[n]["file"]) for n in sorted(todo)], chunksize=1))
    json.dump(dict(variants=s1, selected={f: v[0] for f, v in sel.items()}, is_table=table, base_is_ratio=rb, combo=combo, ranked=[(f, n, r) for r, f, n in ranked], acct=acc),
              open(HERE + "/stage2.json", "w"), indent=1, default=float)
    print("done")
