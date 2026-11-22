"""beat109: search for Pro 150K EVAL configs with median days-to-pass < 109 (U1 reproduction + grid). Research only.
Reuses ../brake150/brake150.py load_sim() (sim150 patched in memory). Run from backend/: PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/beat109/beat109.py
Config tuple: (stop, N NOISE micros, nc CANDACE micros, brake cushion $, brake micros, taper, grow, dlock). Brake applies to NOISE and CANDACE."""
import sys, os, json, time, itertools
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); PF = os.path.dirname(HERE)
sys.path.insert(0, PF); sys.path.insert(0, PF + "/brake150")
import brake150 as B
CONS = B.CONS; MLL = 4500.0


def cfg(stop, N, nc, bc, bm, taper=0, grow=0, dlock=0):
    f = bc / MLL
    return dict(stop=stop, N=N, nc=nc, brake=(f, bm), cbands=((f, bm),), taper=(0.25, 2) if taper else None,
                grow=(2000.0, N + 2) if grow else None, dlock=0.33 if dlock else None)


def key(s, N, nc, bc, bm, t, g, d): return f"s{s}|N{N}|c{nc}|b{bc}/{bm}|t{t}|g{g}|d{d}"


def ev(job):
    k, a, cn = job
    S = B.load_sim(); S.CONS, ds = CONS[cn]; S.DSTOP = ds * S.TARGET
    e = S.evaluate(S.mk(**cfg(*a)))
    r = {w: {x: e[w][x] for x in ("pass", "stuck", "run", "p60", "med")} for w in ("ALL", "PICK", "JUDGE")}
    r["chain"] = {x: e["ch"][x] for x in ("mean", "med", "cens")}; r["profit"] = e["static"]["profit"]
    return f"{k}|{cn}", dict(a=a, **r)


def run(jobs, store):
    jobs = [j for j in jobs if f"{j[0]}|{j[2]}" not in store]
    with mp.Pool(4) as p:
        for k, r in p.imap_unordered(ev, jobs): store[k] = r


if __name__ == "__main__":
    t0 = time.time(); store = {}; fn = HERE + "/results.json"
    if os.path.exists(fn): store = json.load(open(fn))
    def J(al): return [(key(*a), a, cn) for a in al for cn in CONS]
    st1 = [(s, N, nc, 1500, 2, 0, 0, 0) for s in (75, 100, 125, 150) for N in (4, 5, 6, 8) for nc in (2, 3, 4, 5)]
    run(J(st1), store); print("stage1", len(store), f"{time.time()-t0:.0f}s", flush=True)
    def top(cn, n):
        rs = [(r["ALL"]["med"] if r["ALL"]["med"] else 1e9, k) for k, r in store.items() if k.endswith("|" + cn) and r["ALL"]["pass"] >= 70]
        return [tuple(store[k]["a"]) for _, k in sorted(rs)[:n]]
    seeds = {tuple(a) for cn in CONS for a in top(cn, 5)} | {(100, 4, 3, 1500, 2, 0, 0, 0)}
    st2 = {(s, N, nc, bc, bm, 0, 0, 0) for s, N, nc, *_ in seeds for bc, bm in itertools.product((1000, 1500, 2000), (2, 3))}
    run(J(sorted(st2)), store); print("stage2", len(store), f"{time.time()-t0:.0f}s", flush=True)
    seeds2 = {tuple(a) for cn in CONS for a in top(cn, 5)}
    st3 = set()
    for s, N, nc, bc, bm, *_ in seeds2:
        for t, g, d in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 0), (0, 1, 1), (1, 1, 1)):
            if g and N < 4: continue
            st3.add((s, N, nc, bc, bm, t, g, d))
    run(J(sorted(st3)), store); print("stage3", len(store), f"{time.time()-t0:.0f}s", flush=True)
    json.dump(store, open(fn, "w"), indent=0, default=float)
