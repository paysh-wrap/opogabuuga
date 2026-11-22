"""Print tables for pass70 (reads results.json). Run from backend/: PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/pass70/report.py"""
import sys, json
sys.argv = ["x", "none"]
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pass70 as P

store = json.load(open(P.FN))


def desc(nm):
    c = json.loads(nm.split("|", 1)[1])
    nb = ",".join(f"{round(f*P.MLL[K])}>{m}" for f, m in c["nbands"] or [])
    cb = ",".join(f"{round(f*P.MLL[K])}>{m}" for f, m in c["cbands"] or [])
    br = f" brk{c['brake']}" if c.get("brake") else ""
    ex = "".join([f" tap{c['taper']}" if c.get("taper") else "", f" grow{c['grow']}" if c.get("grow") else "", f" dl{c['dlock']}" if c.get("dlock") else "",
                  f" lock{c['lock']}" if c.get("lock", 100) != 100 else "", f" cw{c['cwin']}" if c.get("cwin", 1000) != 1000 else ""])
    tag = "config-only" if (c["nc"] == 0 and not c.get("brake") and not c["cbands"]) else "needs-code(CANDACE size/brake)"
    if c["N"] > {25: 2, 50: 4, 100: 5, 150: 5}[K]: tag += "+micro cap lift"
    return f"s${c['stop']} N{c['N']}[{nb or '-'}] C{c['nc']}[{cb or '-'}]{br}{ex} | {tag}"


def row(nm, r):
    return f"{r['ALL']['pass']:.1f} | {r['ALL']['med']} | {r['ALL']['p60']:.1f} | {r['chain']['mean']:.0f} | {r['JUDGE']['pass']:.1f} | {r['PICK']['pass']:.1f} | {r['profit']:.0f} | {r['ALL']['stuck']:.1f} | {desc(nm)}"


H = "| pass | med d | w60 % | d to pass w/ resets | judge | pick | profit | stuck | config |\n|---|---|---|---|---|---|---|---|---|"
for K in (150, 100, 50, 25):
    rows = [(nm, r) for nm, r in store.items() if nm.startswith(f"{K}|")]
    b = store[f"{K}|{P.name(P.BASEREF[K])}"]
    print(f"\n## {K}K  ({len(rows)} configs)  BASE pass {b['ALL']['pass']:.1f} med {b['ALL']['med']} profit {b['profit']:.0f} judge {b['JUDGE']['pass']:.1f} pick {b['PICK']['pass']:.1f}")
    for key, (lab, c) in P.BUILT.items():
        if str(key).startswith(str(K)):
            r = store.get(f"{K}|{P.name(c)}")
            if r: print("BUILT", lab, "|", row(f"{K}|{P.name(c)}", r))
    fe = [(nm, r) for nm, r in rows if P.feas(r, b)]
    print(f"feasible (pass>=70, profit>=BASE, judge, pick): {len(fe)}; best pass overall {max(r['ALL']['pass'] for _, r in rows):.1f}")
    if fe:
        print("\nTop-5 by median days\n" + H)
        for nm, r in sorted(fe, key=lambda x: P.metrics(x[1]))[:5]: print("|", row(nm, r), "|")
        print("\nPareto (pass vs median), feasible\n" + H)
        best = 1e9
        for nm, r in sorted(fe, key=lambda x: (-x[1]["ALL"]["pass"], P.metrics(x[1]))):
            m = r["ALL"]["med"] or 999
            if m < best: best = m; print("|", row(nm, r), "|")
    else:
        # relaxed: pass-first
        print("\nBest pass (profit>=BASE, judge/pick ok)\n" + H)
        ok = [(nm, r) for nm, r in rows if r["profit"] >= b["profit"] - 1e-6 and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5]
        for nm, r in sorted(ok, key=lambda x: (-x[1]["ALL"]["pass"], P.metrics(x[1])))[:3]: print("|", row(nm, r), "|")
    # fastest at any pass >= BASE pass-ish
    print("\nBest pass any (constraints ok) top-3 by pass\n" + H)
    ok = [(nm, r) for nm, r in rows if r["profit"] >= b["profit"] - 1e-6 and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5]
    for nm, r in sorted(ok, key=lambda x: (-x[1]["ALL"]["pass"], P.metrics(x[1])))[:3]: print("|", row(nm, r), "|")
