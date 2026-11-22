"""final_search: last compact search for FASTER Lucid Pro eval passes (research only, 2026-11-22).
Reuses ../pass70 + ../within60/lib.py + ../brake150 + ../sim150.py (same sim, C40 day stop 38 %, DLL ON, EOD MLL, 1 position).
New knobs on top of the pass70 grid (patched into the sim source, defaults = old behaviour):
  cgrow=(per $, max)  CANDACE +1 micro per `per` $ of cushion beyond the first (bands still shrink)
  dlall=True          the day lock also stops CANDACE (pass70 day lock = NOISE only)
  ndow/cdow=(days,)   skip NOISE / CANDACE on these weekdays (0=Mon)
Run from backend/: PYTHONPATH=. python3 <this> [base|search|report].  PF = main checkout pass_fastest (data + sims live there)."""
import sys, os, json, time, itertools, types
HERE = os.path.dirname(os.path.abspath(__file__))
PF = "/home/user/opogabuuga/docs/results/pass_fastest"
sys.path.insert(0, PF + "/within60"); sys.path.insert(0, PF + "/brake150")
import brake150 as B
_old = B.load_sim


def load_sim():
    src = open(PF + "/sim150.py").read()
    # rebuild from the brake150-patched source with extra patches
    reps = [
        ('fade=False, nc=0, cwin=1000, ng=0,', 'fade=False, nc=0, cwin=1000, ng=0, nbands=(), cbands=(), cgrow=None, dlall=False, ndow=(), cdow=(),'),
        ('                if bb is not None and cush / MLL < bb: q = min(q, bc)\n',
         '                if bb is not None and cush / MLL < bb: q = min(q, bc)\n'
         '                for fb_, fn_ in c["nbands"]:\n'
         '                    if cush / MLL < fb_: q = min(q, fn_)\n'),
        ('                q = nc if kind == KC else ng\n',
         '                q = nc if kind == KC else ng\n'
         '                if kind == KC and c["cgrow"]:\n'
         '                    ex_ = int((bal - floor) // c["cgrow"][0]) - 1\n'
         '                    if ex_ > 0: q = min(c["cgrow"][1], nc + ex_)\n'
         '                if kind == KC:\n'
         '                    for fb_, fn_ in c["cbands"]:\n'
         '                        if (bal - floor) / MLL < fb_: q = min(q, fn_)\n'),
        ('                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0\n',
         '                if kind == KC and DOWL[di] in c["cdow"]: continue\n'
         '                if c["dlall"] and (lockday or (dlk and today > 0 and rem0 > 0 and today >= dlk * rem0)):\n'
         '                    if not lockday: lockday = True; dlkd += 1\n'
         '                    continue\n'
         '                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0\n'),
        ('            if kind <= KF:                                           # NOISE / fade: size table + checks\n',
         '            if kind <= KF and DOWL[di] in c["ndow"]: continue\n'
         '            if kind <= KF:                                           # NOISE / fade: size table + checks\n'),
    ]
    for a, b in reps:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    m = types.ModuleType("simfinal"); m.__file__ = PF + "/sim150.py"
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    m.DOWL = [m.DOW[d] for d in m.DATES]
    return m


B.load_sim = load_sim
from lib import mkcfg, sim, R
import lib as L
import multiprocessing as mp

FN = HERE + "/results.json"
MLL = {25: 1000., 50: 2000., 100: 3000., 150: 4500.}
FLOOR = {25: 62.0, 50: 62.0, 100: 70.0, 150: 70.0}


def cfg(k, stop, N, nc, nb=(), cb=(), grow=None, dlock=None, lock=100, taper=None, **x):
    f = lambda bands: tuple((d / MLL[k], m) for d, m in bands)      # bands in $ cushion
    c = mkcfg(stop, N, nc, f(nb), f(cb), taper, grow, dlock, 1000, lock, None); c.update(x); return c


BUILT = {150: dict(stop=100, N=5, nc=5, nb=((2250, 2), (1500, 1)), cb=((2700, 4), (1500, 1)), grow=(500., 6), dlock=0.7),
         100: dict(stop=100, N=3, nc=3, nb=((1000, 2),), cb=((600, 2),), dlock=0.5),
         50: dict(stop=75, N=2, nc=4, nb=((667, 1),), cb=((1000, 3),), dlock=0.5, lock=80),
         25: dict(stop=75, N=1, nc=2, cb=((333, 1),))}


def nm(k, p): return f"{k}|" + json.dumps(p, sort_keys=True, default=list)


def evj(job):
    k, p = job
    S = sim(k, True); e = S.evaluate(S.mk(**cfg(k, **p)))
    r = {w: {x: e[w][x] for x in ("pass", "stuck", "run", "p60", "med")} for w in ("ALL", "PICK", "JUDGE")}
    r["chain"] = {x: e["ch"][x] for x in ("mean", "med", "cens")}; r["profit"] = e["static"]["profit"]
    return nm(k, p), r


def variants(k):
    b = BUILT[k]; out = []
    M = MLL[k]
    # 1) CANDACE grow
    for per in (M / 6, M / 4.5, M / 3):
        for mx in (b["nc"] + 1, b["nc"] + 2):
            out.append(dict(b, cgrow=(round(per), mx)))
    # 2) day lock variants, incl. on CANDACE too
    for dl in (None, 0.4, 0.5, 0.6, 0.7, 0.8):
        for da in (False, True):
            out.append(dict(b, dlock=dl, dlall=da))
    # 3) NOISE lock trigger
    for lk in (80, 90, 110, 120):
        out.append(dict(b, lock=lk))
    # 4) brake shapes: shift every band +/-, single vs two-step
    for s in (0.75, 0.9, 1.1, 1.25):
        out.append(dict(b, nb=tuple((round(d * s), m) for d, m in b.get("nb", ())), cb=tuple((round(d * s), m) for d, m in b.get("cb", ()))))
    for s in (0.75, 1.25):
        out.append(dict(b, cb=tuple((round(d * s), m) for d, m in b.get("cb", ()))))
        out.append(dict(b, nb=tuple((round(d * s), m) for d, m in b.get("nb", ()))))
    # 5) size +/- 1
    out.append(dict(b, nc=b["nc"] + 1)); out.append(dict(b, N=b["N"] + 1)); out.append(dict(b, nc=max(b["nc"] - 1, 0)))
    # 6) weekday skips
    for d in range(5):
        out.append(dict(b, cdow=(d,))); out.append(dict(b, ndow=(d,)))
    # 7) taper near target
    for tn in (1, 2):
        out.append(dict(b, taper=(0.25, tn)))
    return [dict(sorted(v.items())) for v in out]


def feas(k, r, br):
    return (r["ALL"]["pass"] >= FLOOR[k] and r["profit"] >= br["profit"] - 1e-6 and r["JUDGE"]["pass"] >= br["JUDGE"]["pass"] - 3
            and r["PICK"]["pass"] >= br["PICK"]["pass"] - 5 and (r["ALL"]["med"] or 999) < (br["ALL"]["med"] or 999))


def run(jobs, store):
    jobs = [j for j in jobs if nm(*j) not in store]
    seen = set(); jobs = [j for j in jobs if not (nm(*j) in seen or seen.add(nm(*j)))]
    print(len(jobs), "jobs", flush=True)
    with mp.Pool(4) as pool:
        for key, r in pool.imap_unordered(evj, jobs, chunksize=2):
            store[key] = r
    json.dump(store, open(FN, "w"), default=float, indent=0)


if __name__ == "__main__":
    stg = sys.argv[1] if len(sys.argv) > 1 else "search"
    store = json.load(open(FN)) if os.path.exists(FN) else {}
    t0 = time.time()
    if stg == "base":
        run([(k, dict(sorted(BUILT[k].items()))) for k in BUILT], store)
    elif stg == "search":
        run([(k, v) for k in BUILT for v in variants(k)], store)
    elif stg == "combo":          # stage 2: combine the feasible single changes (pairs) per plan
        jobs = []
        for k in BUILT:
            br = store[nm(k, dict(sorted(BUILT[k].items())))]; b = json.loads(json.dumps(BUILT[k], default=list))
            ok = [json.loads(key.split("|", 1)[1]) for key, r in store.items() if key.startswith(f"{k}|") and feas(k, r, br)]
            ok = sorted(ok, key=lambda p: store[nm(k, p)]["ALL"]["med"])[:8]
            diffs = [{x: v for x, v in p.items() if b.get(x) != v and not (x not in b and v in (None, False, []))} for p in ok]
            for d1, d2 in itertools.combinations(diffs, 2):
                if set(d1) & set(d2): continue
                jobs.append((k, dict(sorted(dict(b, **d1, **d2).items()))))
        run(jobs, store)
    print(stg, "done", round(time.time() - t0), "s", flush=True)
