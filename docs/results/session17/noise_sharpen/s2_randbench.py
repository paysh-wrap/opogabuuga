"""Random-direction benchmark. Same entry TIMING (the normal 'close outside the 14-day noise band' signal at the same hourly checks, same max 3 entries/day),
direction replaced by a fair coin, same exits (band/VWAP trail, $250 stop, optional profit lock, flat 16:00) and same costs. 200 seeds per base.
Writes randbench.json (per-seed IS/HO stats + Pro 25K eval roll). usage: python -I s2_randbench.py [n_seeds]"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from multiprocessing import Pool
import nz, sim

BASES = {"nolock": None, "lock": (100, 10)}


def one(a):
    ln, seed = a
    t = nz.gen(lock=BASES[ln], rnd=seed)
    o = {e: nz.stats(t, e) for e in ("IS", "HO")}
    for e in ("IS", "HO"): o[e]["roll"] = sim.eval_roll(t, e)
    return ln, seed, o


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    nz.days()
    with Pool(4) as p: r = p.map(one, [(ln, s) for ln in BASES for s in range(n)], chunksize=2)
    out = {ln: {} for ln in BASES}
    for ln, s, o in r: out[ln][s] = o
    json.dump(out, open(HERE + "/randbench.json", "w"), indent=1, default=float)
    print("done", len(r))
