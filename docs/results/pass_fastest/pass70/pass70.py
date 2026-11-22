"""pass70: fastest setups (median days to pass) subject to 5-yr pass >= 70 % per plan 25K/50K/100K/150K (C40 day stop 38 %, DLL ON). Research only.
Reuses ../within60/lib.py (sim + mkcfg + plan constants) and the existing results.json of passfloor/, within60/, smaller_plans/ (all DLL ON, C40).
Run from backend/: PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/pass70/pass70.py [inspect|grid|report]
Constraints vs BASE: profit >= BASE profit, judge pass >= BASE judge - 3, pick pass >= BASE pick - 5, pass >= 70 (floor of this study)."""
import sys, os, json, time, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); PF = os.path.dirname(HERE)
sys.path.insert(0, PF + "/within60")
from lib import *
HERE = os.path.dirname(os.path.abspath(__file__)); PF = os.path.dirname(HERE)
import multiprocessing as mp

FN = HERE + "/results.json"
T3 = 1 / 3.
FLOOR = 70.0
# BASE of the earlier studies (reference for profit / judge / pick), and the BUILT setups (speed to beat)
BASEREF = {25: mkcfg(250, 1, 0), 50: mkcfg(250, 2, 0, nb=((0.5, 1),)), 100: mkcfg(250, 2, 0, brake=(0.3, 1)), 150: mkcfg(250, 3, 0, brake=(0.5, 2))}
BUILT = {150: ("N5@100+C4 both->2 at cushion<=1500", mkcfg(100, 5, 4, nb=((T3, 2),), cb=((T3, 2),))),
         100: ("N2@250(1<750)+C4(1<1500)", mkcfg(250, 2, 4, nb=((0.25, 1),), cb=((0.5, 1),))),
         "100old": ("N2@250+C3 (old built)", mkcfg(250, 2, 3, nb=((0.25, 1),), cb=((0.5, 1),)))}
MLL = {25: 1000., 50: 2000., 100: 3000., 150: 4500.}


def name(c):
    return json.dumps({x: c[x] for x in ("stop", "N", "nc", "nbands", "cbands", "brake", "taper", "grow", "dlock", "cwin", "lock")}, sort_keys=True, default=list)


def norm(c):
    """canonical form so configs from older stores (no brake / no cwin key) match"""
    d = dict(c)
    for k, v in (("brake", None), ("taper", None), ("grow", None), ("dlock", None), ("cwin", 1000), ("lock", 100), ("nbands", ()), ("cbands", ())):
        d.setdefault(k, v)
    return d


def from_d(d):
    t = lambda v: tuple(tuple(x) for x in v) if v else ()
    return mkcfg(d["stop"], d["N"], d["nc"], t(d.get("nbands")), t(d.get("cbands")), tuple(d["taper"]) if d.get("taper") else None,
                 tuple(d["grow"]) if d.get("grow") else None, d.get("dlock"), d.get("cwin", 1000), d.get("lock", 100), tuple(d["brake"]) if d.get("brake") else None)


def load_old():
    out = {}
    for sub in ("passfloor", "within60"):
        d = json.load(open(f"{PF}/{sub}/results.json"))
        for k, r in d.items():
            kk, dl, nm = k.split("|", 2)
            if dl != "1": continue
            c = norm(json.loads(nm)); out[f"{kk}|{name(from_d(c))}"] = r
    return out


def ev2(job):
    k, nm, cfg = job
    return ev((k, True, nm, cfg))[0].split("|", 2)[0] + "|" + nm, ev((k, True, nm, cfg))[1]


def evq(job):
    k, nm, cfg = job
    key, r = ev((k, True, nm, cfg))
    return f"{k}|{nm}", r


def bandsets(n, fs, kind):
    if n <= 1: return [()]
    out = [()]
    for f in fs:
        for m in range(1, n): out.append(((f, m),))
    for f1, f2 in itertools.combinations(sorted(fs, reverse=True), 2):
        for m1 in range(2, n):
            for m2 in range(1, m1): out.append(((f1, m1), (f2, m2)))
    return out


def grid(k):
    out = {}
    if k == 150:
        stops, Ns, ncs, fs = (50, 75, 100, 125), (5, 6, 7, 8, 10), (3, 4, 5, 6, 8), (1000 / 4500., 1500 / 4500., 2500 / 4500.)
    elif k == 100:
        stops, Ns, ncs, fs = (75, 100, 150, 250), (2, 3, 4, 5, 6), (2, 3, 4, 5, 6), (750 / 3000., 1500 / 3000., 2000 / 3000.)
    elif k == 50:
        stops, Ns, ncs, fs = (50, 75, 100, 150, 250), (1, 2, 3, 4), (0, 1, 2, 3, 4), (0.15, 0.25, T3, 0.5)
    else:
        stops, Ns, ncs, fs = (50, 75, 100, 150), (1, 2, 3), (0, 1, 2, 3), (0.2, T3, 0.5)
    def one(n):
        return [()] + [((f, m),) for f in fs for m in range(1, min(n, 4))] if n > 1 else [()]
    for s, N, nc in itertools.product(stops, Ns, ncs):
        for nb in one(N):
            for cb in (one(nc) if nc else [()]):
                c = mkcfg(s, N, nc, nb, cb); out[name(c)] = c
    return out


def extras(c):
    out = []
    for lk, dl, tp, gr in itertools.product((80, 100, 120), (None, .5, .7), (None, (0.25, 1)), (None, (500., 12), (1000., 12))):
        e = dict(c, lock=lk, dlock=dl, taper=tp, grow=gr)
        if gr and gr[1] <= c["N"]: continue
        out.append(e)
    return out


def metrics(r): return (r["ALL"]["med"] or 999, -r["ALL"]["p60"], r["chain"]["mean"])


def pools(store, k, refs):
    return [(nm, r) for nm, r in store.items() if nm.startswith(f"{k}|")]


def feas(r, b):
    return (r["ALL"]["pass"] >= FLOOR and r["profit"] >= b["profit"] - 1e-6 and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5)


if __name__ == "__main__":
    stg = sys.argv[1] if len(sys.argv) > 1 else "grid"
    store = json.load(open(FN)) if os.path.exists(FN) else {}
    if not store:
        store = load_old(); print("loaded old", len(store), flush=True)
    t0 = time.time()
    if stg == "grid":
        pool = mp.Pool(3)
        jobs = []
        for k in (150, 100, 50, 25):
            refs = [(k, name(BASEREF[k]), BASEREF[k])] + [(k, name(c), c) for _, c in BUILT.values()] * (k in (100, 150))
            jobs += refs
            jobs += [(k, nm, c) for nm, c in grid(k).items()]
        jobs = [j for j in jobs if f"{j[0]}|{j[1]}" not in store]
        seen = set(); jobs = [j for j in jobs if not (f"{j[0]}|{j[1]}" in seen or seen.add(f"{j[0]}|{j[1]}"))]
        print(len(jobs), "new jobs", flush=True)
        n = 0
        for key, r in pool.imap_unordered(evq, jobs, chunksize=16):
            store[key] = r; n += 1
            if n % 2000 == 0:
                print(n, "/", len(jobs), round(time.time() - t0), flush=True); json.dump(store, open(FN, "w"), default=float)
        json.dump(store, open(FN, "w"), default=float)
    elif stg == "extras":
        pool = mp.Pool(3)
        jobs = []
        for k in (150, 100, 50, 25):
            b = store[f"{k}|{name(BASEREF[k])}"]
            fe = sorted([(nm, r) for nm, r in pools(store, k, 0) if feas(r, b)], key=lambda x: metrics(x[1]))[:25]
            hi = sorted([(nm, r) for nm, r in pools(store, k, 0) if r["ALL"]["pass"] >= 66 and r["profit"] >= b["profit"]], key=lambda x: -x[1]["ALL"]["pass"])[:15]
            for nm, _ in fe + hi:
                c = from_d(norm(json.loads(nm.split("|", 1)[1])))
                for e in extras(c):
                    jobs.append((k, name(e), e))
        jobs = [j for j in jobs if f"{j[0]}|{j[1]}" not in store]
        print(len(jobs), "extras jobs", flush=True)
        n = 0
        for key, r in pool.imap_unordered(evq, jobs, chunksize=16):
            store[key] = r; n += 1
            if n % 2000 == 0: json.dump(store, open(FN, "w"), default=float); print(n, round(time.time() - t0), flush=True)
        json.dump(store, open(FN, "w"), default=float)
    print(stg, "done", round(time.time() - t0), "s", len(store), flush=True)
