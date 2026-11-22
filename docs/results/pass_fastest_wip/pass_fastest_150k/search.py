"""Pass-fastest search driver, Pro 150K EVAL (research only).  At most 2 worker processes (shared 4-CPU box).
Usage: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_fastest_150k/search.py <stage> [args]
Stages (each loads / extends the cache in the scratch dir and prints a summary):
  streams    generate every NOISE / fade stream once (stop x lock x max-entries x Mondays)
  stage1     one-factor sweeps around the three anchors (BASE, row A, NOISE-4@$100 alone)
  stage2a    full factorial stop x micros x grow x brake
  stage2b    top bases x taper x day-lock
  stage2c    top bases x (max entries, lock trigger, Mondays, fade, CANDACE, GALA)
  stage3cd   coordinate descent (extended numeric grids) from the best feasible configs
  stage3rnd  random combinations inside the space
"""
import sys, os, json, time, pickle, math, itertools, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import multiprocessing as mp
import numpy as np
import sim150 as S

CACHE = S.SCR + "/cache.pkl"
STOPS = (75, 100, 125, 150, 175, 200, 225, 250, 300)
NS = (2, 3, 4, 5, 6, 8)
GROWS = (None, (1200, 6), (1200, 8), (2000, 6), (2000, 8))
BRAKES = (None, 0.5, 0.35)
TAPERS = (None, 0.25, 0.5)
DLOCKS = (None, 0.25, 0.33, 0.5)
MAXTRS = (2, 3)
LOCKS = (80, 100, 120)
NCS = ((0, 1000), (1, 1000), (2, 1000), (3, 1000), (1, 1030), (2, 1030), (3, 1030))
NGS = (0, 1, 2)
FLOOR = 70.0


def half(n): return -(-n // 2)


def cfg(stop=250, N=3, grow=None, brk=None, tap=None, dl=None, maxtr=3, lock=100, mon=False, fade=False, nc=0, cwin=1000, ng=0, frule="causal", brake_n=None, taper_n=None):
    if grow and grow[1] <= N: return None
    if (brk or tap) and N < 2: return None
    brake = (brk, brake_n if brake_n else half(N)) if brk else None
    taper = (tap, taper_n if taper_n else half(N)) if tap else None
    if brake and not (1 <= brake[1] < N): return None
    if taper and not (1 <= taper[1] < N): return None
    return S.mk(stop=stop, N=N, grow=grow, brake=brake, taper=taper, dlock=dl, maxtr=maxtr, lock=lock, mon=mon, fade=fade, nc=nc, cwin=cwin, ng=ng, frule=frule)


def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE, "rb") as f: return pickle.load(f)
    return {}


def save_cache(c):
    tmp = CACHE + ".tmp"
    with open(tmp, "wb") as f: pickle.dump(c, f)
    os.replace(tmp, CACHE)


def work(c):
    r = S.evaluate(c)
    return S.compact(r)


def evaluate_many(cfgs, label="", nproc=2, cache=None):
    cache = load_cache() if cache is None else cache
    seen = set(); todo = []
    for c in cfgs:
        if c is None: continue
        k = S.key(c)
        if k in seen or k in cache: continue
        seen.add(k); todo.append(c)
    t0 = time.time()
    if todo:
        with mp.Pool(nproc) as pool:
            for i, res in enumerate(pool.imap_unordered(work, todo, chunksize=6), 1):
                cache[res["key"]] = res
                if i % 500 == 0: save_cache(cache); print(f"  [{label}] {i}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
        save_cache(cache)
    print(f"[{label}] new {len(todo)} (cache {len(cache)}) in {time.time() - t0:.0f}s", flush=True)
    return cache


def feas(r): return r["ALL"]["pass"] >= FLOOR


def row(r):
    a = r["ALL"]; ch = r["ch"]
    return (f"p60 {a['p60']:5.1f} p45 {a['p45']:5.1f} p30 {a['p30']:4.1f} | pass {a['pass']:5.1f} stuck {a['stuck']:5.1f} run {a['run']:5.1f} | med {a['med'] or 0:5.0f} p75 {a['p75'] or 0:5.0f} | "
            f"pick {r['PICK']['pass']:5.1f}/{r['PICK']['p60']:4.1f} judge {r['JUDGE']['pass']:5.1f}/{r['JUDGE']['p60']:4.1f} | chain {ch['mean'] or 0:6.1f}/{ch['att'] or 0:4.2f} c{ch['cens']:4.1f} | {r['key']}")


def top(cache, n=25, pred=feas, keyf=lambda r: (r["ALL"]["p60"], r["ALL"]["pass"])):
    rs = sorted([r for r in cache.values() if pred(r)], key=keyf, reverse=True)
    return rs[:n]


# ---------------------------------------------------------------------------------------------------------- stages
def stage_streams():
    t0 = time.time(); n = 0
    for stop in STOPS:
        for lock in LOCKS:
            for maxtr in MAXTRS:
                for mon in (False, True):
                    S.noise_df(stop, lock, maxtr, mon); n += 1
        S.fade_df(stop, False)
    print("streams ready:", n, "noise +", len(STOPS), "fade", round(time.time() - t0, 1), "s")


def anchors():
    return {"BASE": S.mk(), "A": S.mk(stop=100, N=4, brake=None, nc=2), "N100": S.mk(stop=100, N=4, brake=None)}


def one_factor(a):
    """every single-factor change of the anchor config a (sizing rows keep their shape when N changes)"""
    out = []
    N = a["N"]; fb = a["brake"][0] if a["brake"] else None; ft = a["taper"][0] if a["taper"] else None
    def mod(**kw):
        d = dict(stop=a["stop"], N=a["N"], grow=tuple(a["grow"]) if a["grow"] else None, brk=fb, tap=ft, dl=a["dlock"], maxtr=a["maxtr"], lock=a["lock"], mon=a["mon"],
                 fade=a["fade"], nc=a["nc"], cwin=a["cwin"], ng=a["ng"])
        d.update(kw); return cfg(**d)
    for v in STOPS: out.append(mod(stop=v))
    for v in NS: out.append(mod(N=v))
    for v in GROWS: out.append(mod(grow=v))
    for v in BRAKES: out.append(mod(brk=v))
    for v in TAPERS: out.append(mod(tap=v))
    for v in DLOCKS: out.append(mod(dl=v))
    for v in MAXTRS: out.append(mod(maxtr=v))
    for v in LOCKS: out.append(mod(lock=v))
    for v in (False, True): out.append(mod(mon=v))
    for v in (False, True): out.append(mod(fade=v))
    out.append(cfg(**dict(stop=a["stop"], N=a["N"], grow=tuple(a["grow"]) if a["grow"] else None, brk=fb, tap=ft, dl=a["dlock"], maxtr=a["maxtr"], lock=a["lock"], mon=a["mon"], fade=True, frule="strict")))
    for nc, w in NCS: out.append(mod(nc=nc, cwin=w))
    for v in NGS: out.append(mod(ng=v))
    return [c for c in out if c is not None]


def stage1():
    cfgs = []
    for nm, a in anchors().items():
        cfgs += one_factor(a)
    cache = evaluate_many(cfgs, "stage1")
    return cache


def stage2a():
    cfgs = [cfg(stop=s, N=n, grow=g, brk=b) for s in STOPS for n in NS for g in GROWS for b in BRAKES]
    return evaluate_many(cfgs, "stage2a")


def pick_bases(cache, n, lo=68.0, per_n=None):
    """top configs near / above the frontier (pass >= lo), diversified: at most `per_n` per (stop, N)"""
    rs = sorted([r for r in cache.values() if r["ALL"]["pass"] >= lo], key=lambda r: (r["ALL"]["p60"], r["ALL"]["pass"]), reverse=True)
    out = []; cnt = {}
    for r in rs:
        c = r["cfg"]; kk = (c["stop"], c["N"])
        if per_n and cnt.get(kk, 0) >= per_n: continue
        cnt[kk] = cnt.get(kk, 0) + 1; out.append(r)
        if len(out) >= n: break
    return out


def cfg_from(r, **kw):
    c = r["cfg"]
    d = dict(stop=c["stop"], N=c["N"], grow=tuple(c["grow"]) if c["grow"] else None, brk=c["brake"][0] if c["brake"] else None, tap=c["taper"][0] if c["taper"] else None,
             dl=c["dlock"], maxtr=c["maxtr"], lock=c["lock"], mon=c["mon"], fade=c["fade"], nc=c["nc"], cwin=c["cwin"], ng=c["ng"],
             brake_n=c["brake"][1] if c["brake"] else None, taper_n=c["taper"][1] if c["taper"] else None, frule=c.get("frule", "causal"))
    d.update(kw); return cfg(**d)


def stage2b(nbase=40):
    cache = load_cache()
    bases = pick_bases(cache, nbase, 68.0, per_n=3)
    cfgs = []
    for r in bases:
        for t in TAPERS:
            for d in DLOCKS: cfgs.append(cfg_from(r, tap=t, dl=d))
    return evaluate_many(cfgs, "stage2b", cache=cache)


def stage2c(nbase=16):
    cache = load_cache()
    bases = pick_bases(cache, nbase, 68.0, per_n=2)
    cfgs = []
    for r in bases:
        for mt, lk, mo, fd, (nc, cw), ng in itertools.product(MAXTRS, LOCKS, (False, True), (False, True), NCS, NGS):
            cfgs.append(cfg_from(r, maxtr=mt, lock=lk, mon=mo, fade=fd, nc=nc, cwin=cw, ng=ng))
    print("stage2c bases:", len(bases), "configs:", len([c for c in cfgs if c]))
    return evaluate_many(cfgs, "stage2c", cache=cache)


# ---- extended grids for the local search (sizing numbers only; streams stay inside the brief's discrete values)
EXT = dict(grow_per=(800, 1000, 1200, 1500, 2000, 2500, 3000), grow_max=(4, 5, 6, 7, 8, 10, 12), brake_frac=(0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7),
           taper_frac=(0.15, 0.25, 0.35, 0.5, 0.6), dlock=(0.15, 0.2, 0.25, 0.33, 0.4, 0.5, 0.75), N=(2, 3, 4, 5, 6, 7, 8, 10))


def neighbors(c):
    """all single-parameter moves of config c over the (extended) grids"""
    out = []
    g = tuple(c["grow"]) if c["grow"] else None; b = c["brake"]; t = c["taper"]
    def mk(**kw):
        d = dict(stop=c["stop"], N=c["N"], grow=g, brk=b[0] if b else None, tap=t[0] if t else None, dl=c["dlock"], maxtr=c["maxtr"], lock=c["lock"], mon=c["mon"],
                 fade=c["fade"], nc=c["nc"], cwin=c["cwin"], ng=c["ng"], brake_n=b[1] if b else None, taper_n=t[1] if t else None, frule=c.get("frule", "causal"))
        d.update(kw); return cfg(**d)
    for v in STOPS: out.append(mk(stop=v))
    for v in EXT["N"]:
        # N changes: keep brake / taper contracts proportional (half) and drop grow if no longer above N
        out.append(mk(N=v, brake_n=None, taper_n=None))
    out.append(mk(grow=None))
    for gp in EXT["grow_per"]:
        for gm in EXT["grow_max"]:
            out.append(mk(grow=(gp, gm)))
    out.append(mk(brk=None, brake_n=None))
    for bf in EXT["brake_frac"]:
        out.append(mk(brk=bf))
        for bn in range(1, c["N"]): out.append(mk(brk=bf, brake_n=bn))
    out.append(mk(tap=None, taper_n=None))
    for tf in EXT["taper_frac"]:
        out.append(mk(tap=tf))
        for tn in range(1, c["N"]): out.append(mk(tap=tf, taper_n=tn))
    for v in (None,) + EXT["dlock"]: out.append(mk(dl=v))
    for v in MAXTRS: out.append(mk(maxtr=v))
    for v in LOCKS: out.append(mk(lock=v))
    for v in (False, True): out.append(mk(mon=v)); out.append(mk(fade=v))
    for nc, w in NCS: out.append(mk(nc=nc, cwin=w))
    for v in NGS: out.append(mk(ng=v))
    # dedupe, drop None and the config itself
    seen = {S.key(c)}; res = []
    for x in out:
        if x is None: continue
        k = S.key(x)
        if k in seen: continue
        seen.add(k); res.append(x)
    return res


def better(r1, r2):
    """r1 better than r2: feasible beats infeasible; then p60; then pass"""
    f1, f2 = feas(r1), feas(r2)
    if f1 != f2: return f1
    a, b = r1["ALL"], r2["ALL"]
    return (a["p60"], a["pass"]) > (b["p60"], b["pass"])


def stage3cd(nstart=12, max_rounds=8):
    cache = load_cache()
    starts = []
    seen = set()
    for r in top(cache, 400):
        c = r["cfg"]; kk = (c["stop"], c["N"], bool(c["grow"]))
        if kk in seen: continue
        seen.add(kk); starts.append(r)
        if len(starts) >= nstart: break
    print("coordinate-descent starts:")
    for r in starts: print("  ", row(r))
    cur = {S.key(r["cfg"]): r for r in starts}
    for rnd in range(1, max_rounds + 1):
        cand = []
        for r in cur.values(): cand += neighbors(r["cfg"])
        cache = evaluate_many(cand, f"cd round {rnd}", cache=cache)
        new = {}; improved = 0
        for k, r in cur.items():
            best = r
            for x in neighbors(r["cfg"]):
                rx = cache[S.key(x)]
                if better(rx, best): best = rx
            if best is not r: improved += 1
            new[S.key(best["cfg"])] = best
        print(f"cd round {rnd}: improved {improved}/{len(cur)}", flush=True)
        for r in sorted(new.values(), key=lambda r: (feas(r), r["ALL"]["p60"]), reverse=True)[:5]: print("   ", row(r))
        cur = new
        if not improved: break
    return cache


def random_cfg(rng):
    for _ in range(100):
        N = rng.choice(NS); stop = rng.choice(STOPS)
        g = rng.choice([None] + [(gp, gm) for gp in EXT["grow_per"] for gm in EXT["grow_max"]])
        bf = rng.choice([None] + list(EXT["brake_frac"])); tf = rng.choice([None] * 2 + list(EXT["taper_frac"]))
        dl = rng.choice([None] * 2 + list(EXT["dlock"]))
        c = cfg(stop=stop, N=N, grow=g, brk=bf, tap=tf, dl=dl, brake_n=rng.randint(1, max(N - 1, 1)) if bf and N >= 2 else None, taper_n=rng.randint(1, max(N - 1, 1)) if tf and N >= 2 else None,
                maxtr=rng.choice(MAXTRS), lock=rng.choice(LOCKS), mon=rng.random() < 0.3, fade=rng.random() < 0.3, nc=rng.choice(NCS)[0], cwin=rng.choice((1000, 1030)), ng=rng.choice(NGS))
        if c is not None:
            if c["nc"] == 0: c["cwin"] = 1000
            return c
    return None


def stage3rnd(n=600, seed=11):
    rng = random.Random(seed)
    cfgs = [random_cfg(rng) for _ in range(n)]
    return evaluate_many(cfgs, "random", cache=load_cache())


def summary(cache, n=20):
    print("configs in cache:", len(cache), " feasible (pass>=70):", sum(1 for r in cache.values() if feas(r)))
    print("TOP by p60 (feasible):")
    for r in top(cache, n): print("  ", row(r))


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if st == "streams": stage_streams()
    elif st == "stage1": summary(stage1())
    elif st == "stage2a": summary(stage2a())
    elif st == "stage2b": summary(stage2b(int(sys.argv[2]) if len(sys.argv) > 2 else 40))
    elif st == "stage2c": summary(stage2c(int(sys.argv[2]) if len(sys.argv) > 2 else 16))
    elif st == "stage3cd": summary(stage3cd(int(sys.argv[2]) if len(sys.argv) > 2 else 12))
    elif st == "stage3rnd": summary(stage3rnd(int(sys.argv[2]) if len(sys.argv) > 2 else 600))
    else: summary(load_cache())
