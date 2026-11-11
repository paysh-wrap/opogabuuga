"""Stage 1: build candidates, simulate, grid of selection filters -> grid.csv (IS and HO stats per row). Run: PYTHONPATH=. python3 run_grid.py"""
import itertools, pickle, time, sys
import numpy as np, pandas as pd, lib
from multiprocessing import Pool

def work(a):
    win, tf, lev, disp = a
    c = lib.gen(win, tf, lev, disp)
    res = {}
    for entry, tgt in itertools.product(("mid", "near"), (1.5, 2.0, "liq")):
        res[(entry, tgt)] = lib.simulate(c, entry, tgt)
    return a, len(c), res

if __name__ == "__main__":
    lib.load()
    jobs = list(itertools.product(("AM", "PM", "LON"), (1, 5), ("all", "static"), (1.0, 0.5)))
    t = time.time()
    with Pool(4) as p: out = p.map(work, jobs)
    print("gen+sim", time.time() - t)
    pickle.dump(out, open("sims.pkl", "wb"))
    ncand = {a: n for a, n, _ in out}
    print({k: v for k, v in ncand.items()})
