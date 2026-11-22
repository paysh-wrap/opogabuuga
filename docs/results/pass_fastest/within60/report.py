"""tables.md from results.json: top-5 per plan x objective x DLL, plus the pass-vs-micros curve for objective B."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import *

store = json.load(open(FN))
out = []


def desc(nm):
    c = json.loads(nm.split("|", 2)[2])
    f = lambda b: "/".join(f"<{x*MLL_[0]:.0f}:{m}" for x, m in b) or "-"
    s = f"N{c['N']}@${c['stop']} nb[{f(c['nbands'])}] + C{c['nc']} cb[{f(c['cbands'])}]"
    for x in ("taper", "grow", "dlock"):
        if c[x]: s += f" {x}{c[x]}"
    if c["cwin"] != 1000: s += " cwin10:30"
    if c["lock"] != 100: s += f" lock{c['lock']}"
    return s


def row(nm, r, tag=""):
    a = r["ALL"]
    return f"| {tag}{desc(nm)} | {a['pass']:.1f} | {a['stuck']:.1f} | **{a['p60']:.1f}** | {a['med']:.0f} | {r['JUDGE']['pass']:.1f} | {r['PICK']['pass']:.1f} | {r['profit']:,.0f} |"


H = "| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |\n|---|---|---|---|---|---|---|---|"
for k in (25, 150):
    MLL_ = [MLL[k]]
    for dll in (True, False):
        bn = f"{k}|{int(dll)}|{name(BASE[k])}"; b = store[bn]
        for obj, key in (("A maximise <=60d", lambda x: (x[1]["ALL"]["p60"], x[1]["ALL"]["pass"])), ("B maximise 5y pass (more micros)", lambda x: (x[1]["ALL"]["pass"], x[1]["ALL"]["p60"]))):
            out.append(f"\n### {k}K · DLL {'ON' if dll else 'OFF'} · objective {obj}\n\n{H}\n{row(bn, b, 'BASE: ')}")
            t = top(store, k, dll, ok_A, key, 5)
            t = [x for x in t if x[0] != bn]
            for i, (nm, r) in enumerate(t, 1): out.append(row(nm, r, f"#{i} "))
            if not t: out.append("| none | | | | | | | |")
        if True:   # pass-vs-micros curve: best pass per NOISE micros (any other stat), then best acceptable
            out.append(f"\nPass-vs-micros curve ({k}K, DLL {'ON' if dll else 'OFF'}): best 5y pass per NOISE micros N (any config / best config that is also acceptable)\n\n| N | best pass any | its <=60d | its stuck | its profit | best acceptable pass |\n|---|---|---|---|---|---|")
            for N in sorted({json.loads(nm.split('|', 2)[2])["N"] for nm in store if nm.startswith(f"{k}|{int(dll)}|")}):
                rs = [(nm, r) for nm, r in store.items() if nm.startswith(f"{k}|{int(dll)}|") and json.loads(nm.split('|', 2)[2])["N"] == N]
                if not rs: continue
                m = max(rs, key=lambda x: x[1]["ALL"]["pass"]); ac = [x for x in rs if ok_A(x[1], b)]
                am = max(ac, key=lambda x: x[1]["ALL"]["pass"])[1]["ALL"]["pass"] if ac else None
                out.append(f"| {N} | {m[1]['ALL']['pass']:.1f} | {m[1]['ALL']['p60']:.1f} | {m[1]['ALL']['stuck']:.1f} | {m[1]['profit']:,.0f} | {'none' if am is None else f'{am:.1f}'} |")
open(os.path.join(HERE, "tables.md"), "w").write("\n".join(out))
print("\n".join(out))
