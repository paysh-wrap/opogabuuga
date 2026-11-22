"""passfloor search (research only): fastest configs whose 5-yr pass >= the new-best pass floor, per plan 25K / 100K / 150K (C40, DLL ON).
Reuses ../within60/lib.py (sim150 + brake150 bands + plan constants). Brake band = (cushion as fraction of MLL, micros), strict '<'.
Stage 1: stop x NOISE micros x CANDACE micros x NOISE brake x CANDACE brake.  Stage 2: move each band's cushion, then cross extras
(NOISE lock 80/100/120, day lock, taper, grow, CANDACE window 10:30) on the feasible seeds.
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/passfloor/search.py [stage1|stage2|stage3]
"""
import sys, os, json, time, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../within60")
from lib import *
HERE = os.path.dirname(os.path.abspath(__file__))   # lib.py also defines HERE (within60): reset it
import multiprocessing as mp

FN = HERE + "/results.json"
T3 = 1 / 3.
FLOOR = {25: 62.2, 100: 79.9, 150: 79.1}          # new-best 5-yr pass %
REFSTUCK = {25: 29.4, 100: 9.3, 150: 9.8}          # stuck % of that reference setup (repro.json)
BASE = {25: mkcfg(250, 1, 0), 100: mkcfg(250, 2, 0, brake=(0.3, 1)), 150: mkcfg(250, 3, 0, brake=(0.5, 2))}
FS1 = (0.5, T3, 0.2)
FS2 = (0.15, 0.2, 0.25, T3, 0.4, 0.5, 0.6)


def bands(n, fs):
    """none, single-step and two-step brake options for n micros (every step must reduce below n)"""
    if n <= 1: return [()]
    out = [()]
    for f in fs:
        for m in range(1, n): out.append(((f, m),))
    for (f1, f2) in itertools.combinations(sorted(fs, reverse=True), 2):
        for m1 in range(2, n):
            for m2 in range(1, m1): out.append(((f1, m1), (f2, m2)))
    return out


def name(c):
    return json.dumps({x: c[x] for x in ("stop", "N", "nc", "nbands", "cbands", "brake", "taper", "grow", "dlock", "cwin", "lock")}, sort_keys=True, default=list)


def from_name(nm):
    d = json.loads(nm.split("|", 2)[2])
    t = lambda v: tuple(tuple(x) for x in v) if v else ()
    return mkcfg(d["stop"], d["N"], d["nc"], t(d["nbands"]), t(d["cbands"]), tuple(d["taper"]) if d["taper"] else None,
                 tuple(d["grow"]) if d["grow"] else None, d["dlock"], d["cwin"], d["lock"], tuple(d["brake"]) if d["brake"] else None)


GRID = {25: dict(stops=(50, 75, 100, 150), Ns=(1, 2), ncs=(0, 1, 2, 3)),
        100: dict(stops=(100, 150, 250), Ns=(1, 2, 3), ncs=(0, 1, 2, 3, 4)),
        150: dict(stops=(75, 100, 150, 250), Ns=(2, 3, 4, 5), ncs=(0, 1, 2, 3, 4, 5))}


def stage1(k):
    g = GRID[k]; out = {}
    for s, N, nc in itertools.product(g["stops"], g["Ns"], g["ncs"]):
        for nb in bands(N, FS1):
            for cb in (bands(nc, FS1) if nc else [()]):
                c = mkcfg(s, N, nc, nb, cb); out[name(c)] = c
    return out


def run(jobs, store, pool):
    jobs = [j for j in jobs if f"{j[0]}|{int(j[1])}|{j[2]}" not in store]
    n = 0
    for key, r in pool.imap_unordered(ev, jobs, chunksize=16):
        store[key] = r; n += 1
        if n % 2000 == 0: print(n, "/", len(jobs), flush=True)
    json.dump(store, open(FN, "w"), default=float)


def feasible(k, r, b):
    return (r["ALL"]["pass"] >= FLOOR[k] - 1e-9 and r["ALL"]["stuck"] <= REFSTUCK[k] + 1e-9 and r["profit"] >= b["profit"] - 1e-6
            and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5)


def speed(r): return (r["ALL"]["med"] or 999, -r["ALL"]["p60"], r["chain"]["mean"])


def rows(store, k):
    return [(nm, r) for nm, r in store.items() if nm.startswith(f"{k}|1|")]


def move_bands(c):
    out = []
    for fld in ("nbands", "cbands"):
        for i, (f, m) in enumerate(c[fld]):
            for nf in FS2:
                if nf == f: continue
                b = list(c[fld]); b[i] = (nf, m)
                if all(b[j][0] > b[j + 1][0] for j in range(len(b) - 1)): out.append(dict(c, **{fld: tuple(b)}))
    return out


def extras(c):
    out = []
    for lk, dl, cw, tp, gr in itertools.product((80, 100, 120), (None, .5, .7), (1000, 1030), (None, (0.25, 1)), (None, (500., 6))):
        out.append(dict(c, lock=lk, dlock=dl, cwin=cw, taper=tp, grow=gr))
    return out


def seeds(store, k, n=40):
    b = store[f"{k}|1|{name(BASE[k])}"]
    fe = [(nm, r) for nm, r in rows(store, k) if feasible(k, r, b)]
    pareto = sorted(fe, key=lambda x: speed(x[1]))[:n]
    byp60 = sorted(fe, key=lambda x: (-x[1]["ALL"]["p60"], speed(x[1])))[:n]
    near = sorted([(nm, r) for nm, r in rows(store, k) if r["ALL"]["pass"] >= FLOOR[k] - 1.5 and r["ALL"]["stuck"] <= REFSTUCK[k] + 1.5], key=lambda x: speed(x[1]))[:n]
    return {nm for nm, _ in pareto + byp60 + near}


if __name__ == "__main__":
    t0 = time.time(); stg = sys.argv[1] if len(sys.argv) > 1 else "stage1"
    store = json.load(open(FN)) if os.path.exists(FN) else {}
    pool = mp.Pool(4)
    if stg == "stage1":
        jobs = []
        for k in (25, 100, 150):
            jobs.append((k, True, name(BASE[k]), BASE[k]))
            jobs += [(k, True, nm, c) for nm, c in stage1(k).items()]
        print(len(jobs), "stage-1 jobs", flush=True); run(jobs, store, pool)
    elif stg == "stage2":
        jobs = []
        for k in (25, 100, 150):
            for nm in seeds(store, k):
                c = from_name(nm); jobs += [(k, True, name(e), e) for e in move_bands(c)]
        print(len(jobs), "stage-2 jobs", flush=True); run(jobs, store, pool)
    elif stg == "stage3":
        jobs = []
        for k in (25, 100, 150):
            for nm in seeds(store, k, 25):
                c = from_name(nm); jobs += [(k, True, name(e), e) for e in extras(c)]
        print(len(jobs), "stage-3 jobs", flush=True); run(jobs, store, pool)
    print(stg, "done", round(time.time() - t0), "s", flush=True)
