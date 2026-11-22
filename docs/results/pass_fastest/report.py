"""Tables from results.json (pass_fastest). Run: python3 report.py [top|slices|chk]"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from search import BASE, ROWA, FLOOR, gkey, norm, robust
R = json.load(open(HERE + "/results.json"))["runs"]


def f(x, d=1): return "-" if x is None else f"{x:.{d}f}"


def name(g):
    s = f"NOISE {g['nn']}@${g['stop']}"
    if g["nc"]: s += f" + CAND {g['nc']}"
    if g["brake"]: s += " +brake"
    if g["taper"]: s += " +taper"
    return s


HDR = "| config | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ |\n|---|---|---|---|---|---|---|---|---|---|"


def row(r, tag=""):
    a, p, j, ch = r["ALL"], r["PICK"], r["JUDGE"], r["chain"]
    return (f"| {tag}{name(r['g'])} | {f(a['pass'])} | {f(a['stuck'])} | **{f(a['p60'])}** | {f(a['med'], 0)} | {f(ch['mean'], 0)} ({f(ch['cens'], 0)} %) | "
            f"{f(p['pass'])} | {f(j['pass'])} | {f(j['p60'])} | {r['profit']:,.0f} |")


def get(k, g, cn): return R[gkey(k, norm(g), cn)]


def top(k, cn, n=5):
    base = get(k, BASE[k], cn)
    rs = sorted([r for r in R.values() if r["plan"] == k and r["cons"] == cn and robust(r, base)], key=lambda r: (-r["ALL"]["p60"], -r["ALL"]["pass"]))
    out = [f"\n**Pro {k}K · {cn}** (ROBUST: 5y pass >= {FLOOR[k]:.0f} %, judge >= {base['JUDGE']['pass'] - 3:.1f}, pick >= {base['PICK']['pass'] - 5:.1f}; {len(rs)} robust configs)\n", HDR,
           row(base, "BASE: "), row(get(k, ROWA[k], cn), "row A: ")]
    out += [row(r, f"#{i + 1} ") for i, r in enumerate(rs[:n])]
    return "\n".join(out), rs


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "top"
    if what == "chk":
        for k in (50, 150):
            for nm, g in (("BASE", BASE[k]), ("A", ROWA[k])):
                r = get(k, g, "C40"); print(k, nm, round(r["ALL"]["pass"], 2), round(r["ALL"]["p60"], 2))
    if what == "top":
        for k in (50, 150):
            for cn in ("C40", "C50"): print(top(k, cn)[0])
    if what == "slices":
        for k in (50, 150):
            for cn in ("C40", "C50"):
                for an, a in (("BASE", BASE[k]), ("A", ROWA[k])):
                    print(f"\n{k}K {cn} one-factor around {an}")
                    for fct, vals in (("stop", (100, 150, 200, 250)), ("nn", (1, 2, 3) if k == 50 else (3, 4, 5, 6)), ("nc", (0, 1, 2) if k == 50 else (0, 1, 2, 3)), ("brake", (0, 1)), ("taper", (0, 1))):
                        cells = []
                        for v in vals:
                            r = R.get(gkey(k, norm(dict(a, **{fct: v})), cn))
                            if r: cells.append(f"{v}: {r['ALL']['pass']:.1f}/{r['ALL']['p60']:.1f}/j{r['JUDGE']['pass']:.1f}")
                        print(f"  {fct:5s} " + "  ".join(cells))
