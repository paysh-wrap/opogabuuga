"""within60 search. Stage 1 = core grid (stop x NOISE micros x CANDACE micros x NOISE brake x CANDACE brake), stage 2 = extras
(taper, grow, day lock, CANDACE window 10:30, NOISE lock 80/120) on the best stage-1 configs, per plan x DLL x objective.
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/within60/search.py -> results.json
Brake band = (cushion as fraction of MLL, micros). T3 = MLL/3 ($333 on 25K, $1,500 on 150K)."""
import sys, os, json, time, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multiprocessing as mp
from lib import *

FN = os.path.join(HERE, "results.json")
MLL = {25: 1000., 150: 4500.}
BASE = {25: mkcfg(75, 1, 2, cb=((T3, 1),)), 150: mkcfg(100, 5, 4, nb=((T3, 2),), cb=((T3, 2),))}


def nopts(k, N):
    """NOISE brake options for N micros (bands must reduce below N)"""
    if k == 25:
        c = [(), ((T3, 1),), ((0.5, 1),), ((0.5, 2), (T3, 1)), ((T3, 2),), ((0.5, 2),)]
    else:
        T2 = 1000 / 4500.
        c = [(), ((T3, 2),), ((T3, 3),), ((T3, 4),), ((0.5, 2),), ((T3, 3), (T2, 2)), ((T3, 4), (T2, 2)), ((0.5, 4), (T3, 2)), ((0.5, 3), (T3, 2)), ((T3, 4), (T2, 1))]
    out = []
    for b in c:
        if all(m < N for _, m in b) and all(b[i][0] > b[i + 1][0] and b[i][1] > b[i + 1][1] for i in range(len(b) - 1)) or not b: out.append(b)
    return out


def copts(k, nc):
    if nc == 0: return [()]
    T2 = 1000 / 4500.
    if k == 25: c = [(), ((T3, 1),), ((0.5, 1),), ((0.5, 2), (T3, 1)), ((T3, 2),)]
    else: c = [(), ((T3, 2),), ((T3, 3),), ((T3, 1),), ((T3, 2), (T2, 1)), ((T3, 4),), ((0.5, 3), (T3, 2))]
    return [b for b in c if all(m < nc for _, m in b) or not b]


def stage1(k):
    out = {}
    stops = (50, 75, 100, 150) if k == 25 else (50, 75, 100, 125, 150)
    Ns = (1, 2, 3, 4, 5) if k == 25 else (3, 4, 5, 6, 7, 8, 10)
    ncs = (0, 1, 2, 3) if k == 25 else (0, 1, 2, 3, 4, 5, 6)
    for s, N, nc in itertools.product(stops, Ns, ncs):
        if k == 25 and N >= 4 and s > 75: continue
        for nb in nopts(k, N):
            for cb in copts(k, nc):
                out[(s, N, nc, nb, cb)] = mkcfg(s, N, nc, nb, cb)
    return out


def name(c):
    return json.dumps({x: c[x] for x in ("stop", "N", "nc", "nbands", "cbands", "taper", "grow", "dlock", "cwin", "lock")}, sort_keys=True, default=list)


def from_name(nm):
    d = json.loads(nm.split("|", 2)[2])
    return mkcfg(d["stop"], d["N"], d["nc"], tuple(map(tuple, d["nbands"])), tuple(map(tuple, d["cbands"])), tuple(d["taper"]) if d["taper"] else None, tuple(d["grow"]) if d["grow"] else None, d["dlock"], d["cwin"], d["lock"])


def run(jobs, store, pool):
    jobs = [j for j in jobs if f"{j[0]}|{int(j[1])}|{j[2]}" not in store]
    n = 0
    for key, r in pool.imap_unordered(ev, jobs, chunksize=8):
        store[key] = r; n += 1
        if n % 500 == 0: print(n, "/", len(jobs), flush=True)
    json.dump(store, open(FN, "w"), default=float)


def ok_A(r, b):
    return (r["ALL"]["pass"] >= b["ALL"]["pass"] - 1e-9 and r["ALL"]["stuck"] <= b["ALL"]["stuck"] + 1e-9 and r["profit"] >= b["profit"] - 1e-6
            and r["JUDGE"]["pass"] >= b["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= b["PICK"]["pass"] - 5
            and (r["ALL"]["med"] or 999) <= (b["ALL"]["med"] or 999) + 1e-9)


def ok_B(r, b):    # more passes, nothing else worse (same bar as A on stuck / profit / judge / pick / median)
    return ok_A(r, b)


def top(store, k, dll, filt, key, n):
    b = store[f"{k}|{int(dll)}|{name(BASE[k])}"]
    rs = [(nm, r) for nm, r in store.items() if nm.startswith(f"{k}|{int(dll)}|")]
    rs = [(nm, r) for nm, r in rs if filt(r, b)]
    return sorted(rs, key=key, reverse=True)[:n]


def extras(c):
    out = []
    for tp in ((0.25, 1), (0.25, 2)): out.append(dict(c, taper=tp))
    for gr in ((500., 6), (300., 6)): out.append(dict(c, grow=gr))
    for dl in (0.5, 0.7): out.append(dict(c, dlock=dl))
    out.append(dict(c, cwin=1030))
    for lk in (80, 120): out.append(dict(c, lock=lk))
    return out


if __name__ == "__main__":
    t0 = time.time()
    store = json.load(open(FN)) if os.path.exists(FN) else {}
    pool = mp.Pool(4)
    jobs = []
    for k in (25, 150):
        for dll in (True, False):
            jobs.append((k, dll, name(BASE[k]), BASE[k]))
            jobs += [(k, dll, name(c), c) for c in stage1(k).values()]
    print(len(jobs), "stage-1 jobs", flush=True)
    run(jobs, store, pool); print("stage1", round(time.time() - t0), flush=True)
    j2 = []
    for k in (25, 150):
        for dll in (True, False):
            sel = {}
            for filt, key in ((ok_A, lambda x: (x[1]["ALL"]["p60"], x[1]["ALL"]["pass"])), (ok_B, lambda x: (x[1]["ALL"]["pass"], x[1]["ALL"]["p60"]))):
                for nm, r in top(store, k, dll, filt, key, 12): sel[nm] = r
            for nm, r in sel.items():
                c = from_name(nm)
                j2 += [(k, dll, name(e), e) for e in extras(c)]
    print(len(j2), "stage-2 jobs", flush=True)
    run(j2, store, pool); print("done", round(time.time() - t0), flush=True)
