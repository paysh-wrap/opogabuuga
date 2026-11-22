"""Brake variants on the recommended Pro 150K EVAL config (research only; nothing in backend/app, config/ or frontend/ is touched).
Reuses ../sim150.py unchanged on disk: its source is patched in memory with two extra size bands (applied after the existing brake):
  nbands = [(frac, micros), ...]  NOISE  -> q = min(q, micros) when cushion / MLL < frac   (cushion = equity - MLL floor)
  cbands = [(frac, micros), ...]  CANDACE fixed micros -> same rule (needs code in the app: CANDACE has no brake today)
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/brake150/brake150.py  -> results.json + table
"""
import sys, os, json, types
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); PF = os.path.dirname(HERE)
sys.path.insert(0, PF)


def load_sim():
    src = open(PF + "/sim150.py").read()
    reps = [
        ('fade=False, nc=0, cwin=1000, ng=0,', 'fade=False, nc=0, cwin=1000, ng=0, nbands=(), cbands=(),'),
        ('                if bb is not None and cush / MLL < bb: q = min(q, bc)\n',
         '                if bb is not None and cush / MLL < bb: q = min(q, bc)\n'
         '                for fb_, fn_ in c["nbands"]:\n'
         '                    if cush / MLL < fb_: q = min(q, fn_)\n'),
        ('                q = nc if kind == KC else ng\n',
         '                q = nc if kind == KC else ng\n'
         '                if kind == KC:\n'
         '                    for fb_, fn_ in c["cbands"]:\n'
         '                        if (bal - floor) / MLL < fb_: q = min(q, fn_)\n'),
    ]
    for a, b in reps:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    m = types.ModuleType("sim150b"); m.__file__ = PF + "/sim150.py"
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    return m


T = 1500.0 / 4500.0      # $1,500 of the $4,500 MLL = 0.3333
CFG = {
    "BASE": dict(stop=250, N=3, nc=0, brake=(0.5, 2)),
    "REC":  dict(stop=100, N=4, nc=3, brake=(0.5, 2)),
    "U1":   dict(stop=100, N=4, nc=3, brake=(T, 2), cbands=((T, 2),)),
    "U3":   dict(stop=100, N=4, nc=3, brake=(T, 2)),
}
CONS = {"C40": (40.0, 0.38), "C50": (50.0, 0.48)}


def ev(job):
    name, cn = job
    S = load_sim(); S.CONS, ds = CONS[cn]; S.DSTOP = ds * S.TARGET
    e = S.evaluate(S.mk(**CFG[name]))
    r = {w: {k: e[w][k] for k in ("pass", "stuck", "run", "p60", "med")} for w in ("ALL", "PICK", "JUDGE")}
    r["chain"] = {k: e["ch"][k] for k in ("mean", "med", "cens")}
    r["profit"] = e["static"]["profit"]
    return f"{name}|{cn}", r


if __name__ == "__main__":
    jobs = [(n, c) for n in CFG for c in CONS]
    with mp.Pool(4) as p:
        res = dict(p.imap_unordered(ev, jobs))
    res = {k: res[k] for k in sorted(res)}
    json.dump(res, open(HERE + "/results.json", "w"), indent=1, default=float)
    for cn in CONS:
        b = res[f"BASE|{cn}"]
        print(f"\n{cn}  (ROBUST: 5y>=70, judge>={b['JUDGE']['pass']-3:.1f}, pick>={b['PICK']['pass']-5:.1f})")
        print("| row | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ | ROBUST |")
        for n in CFG:
            r = res[f"{n}|{cn}"]; a = r["ALL"]
            rob = a["pass"] >= 70 and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5
            print(f"| {n} | {a['pass']:.1f} | {a['stuck']:.1f} | {a['p60']:.1f} | {a['med']:.0f} | {r['chain']['mean']:.0f} ({r['chain']['cens']:.0f} %) | "
                  f"{r['PICK']['pass']:.1f} | {r['JUDGE']['pass']:.1f} | {r['JUDGE']['p60']:.1f} | {r['profit']:,.0f} | {'YES' if rob else 'no'} |")
