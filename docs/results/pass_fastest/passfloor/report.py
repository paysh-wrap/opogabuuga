"""Tables from results.json (run after search.py). Writes tables.md and prints it."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = sys.argv[:1]
sys.path.insert(0, HERE)
import search as S
store = json.load(open(HERE + "/results.json")); rep = json.load(open(HERE + "/repro.json"))
out = []


def desc(c):
    f = lambda b: ",".join(f"<{x*S.MLLK:.0f}:{m}" for x, m in b) or "-"
    ex = "".join([f" lock{c['lock']}" if c["lock"] != 100 else "", f" dlock{c['dlock']}" if c["dlock"] else "", " taper" if c["taper"] else "", " grow" if c["grow"] else "", " c1030" if c["cwin"] != 1000 else ""])
    return f"N{c['N']}@{c['stop']}+C{c['nc']} nb[{f(c['nbands'])}] cb[{f(c['cbands'])}]{ex}"


def line(nm, r, tag=""):
    a = r["ALL"]; c = S.from_name(nm)
    return f"| {desc(c)} | {a['pass']:.1f} | {a['stuck']:.1f} | {a['p60']:.1f} | {a['med']:.0f} | {r['chain']['mean']:.0f} | {r['JUDGE']['pass']:.1f} | {r['PICK']['pass']:.1f} | {r['profit']:,.0f} |{tag}"


HDR = "| config | pass | stuck | <=60d | median d | exp days w/ resets | judge | pick | profit $ |\n|---|---|---|---|---|---|---|---|---|"
for k in (25, 100, 150):
    S.MLLK = {25: 1000, 100: 3000, 150: 4500}[k]
    b = store[f"{k}|1|{S.name(S.BASE[k])}"]
    rows = S.rows(store, k); fe = [(nm, r) for nm, r in rows if S.feasible(k, r, b)]
    out.append(f"\n## {k}K  (floor pass >= {S.FLOOR[k]}, stuck <= {S.REFSTUCK[k]}, profit >= {b['profit']:,.0f}, judge >= {b['JUDGE']['pass']-3:.1f}, pick >= {b['PICK']['pass']-5:.1f}; {len(rows)} runs, {len(fe)} feasible)\n")
    out.append(HDR)
    for n in ("BASE", "REF", "BUILT"):
        r = rep[f"{k}|1|{k}|{n}"]; out.append(f"| {n} | {r['ALL']['pass']:.1f} | {r['ALL']['stuck']:.1f} | {r['ALL']['p60']:.1f} | {r['ALL']['med']:.0f} | {r['chain']['mean']:.0f} | {r['JUDGE']['pass']:.1f} | {r['PICK']['pass']:.1f} | {r['profit']:,.0f} |")
    out.append("\nTop 6 feasible by median days (then <=60d):\n"); out.append(HDR)
    for nm, r in sorted(fe, key=lambda x: S.speed(x[1]))[:6]: out.append(line(nm, r))
    out.append("\nTop 4 feasible by <=60d:\n"); out.append(HDR)
    for nm, r in sorted(fe, key=lambda x: (-x[1]["ALL"]["p60"], S.speed(x[1])))[:4]: out.append(line(nm, r))
    out.append("\nTop 3 feasible by expected days with resets:\n"); out.append(HDR)
    for nm, r in sorted(fe, key=lambda x: x[1]["chain"]["mean"])[:3]: out.append(line(nm, r))
    # Pareto pass vs median over all runs meeting stuck/profit/judge/pick (pass free, >= floor-6)
    ok = [(nm, r) for nm, r in rows if r["ALL"]["stuck"] <= S.REFSTUCK[k] + 1e-9 and r["profit"] >= b["profit"] - 1e-6 and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5 and r["ALL"]["pass"] >= S.FLOOR[k] - 8]
    pf = []; best = -1
    for nm, r in sorted(ok, key=lambda x: (x[1]["ALL"]["med"] or 999, -x[1]["ALL"]["pass"])):
        if r["ALL"]["pass"] > best + 1e-9: pf.append((nm, r)); best = r["ALL"]["pass"]
    out.append("\nPareto, pass % vs median days (other constraints kept, pass >= floor-8): as median rises, pass rises\n"); out.append(HDR)
    for nm, r in pf: out.append(line(nm, r, " floor met" if r["ALL"]["pass"] >= S.FLOOR[k] else ""))
open(HERE + "/tables.md", "w").write("\n".join(out)); print("\n".join(out))
