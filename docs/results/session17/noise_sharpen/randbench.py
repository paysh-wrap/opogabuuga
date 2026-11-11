"""Candidate 6: random-direction benchmark. Same entry timing (the normal 'close outside the 14-day noise band' signal at the same hourly checks),
random +-1 direction, same exits (band/VWAP trail, profit lock 100->+10, $250 stop, flat 16:00) and costs. 200 seeds. writes randbench.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from multiprocessing import Pool
import numpy as np
import sharpen as S


def one(seed):
    t = S.gen(rnd=seed)
    return seed, {e: S.stats(t, e) for e in ("IS", "HO", "L12")}


if __name__ == "__main__":
    S.days("MNQ")
    with Pool(4) as p: r = p.map(one, range(200), chunksize=2)
    json.dump(dict(seeds=dict(r)), open(HERE + "/randbench.json", "w"), indent=1, default=float)
    print("done")
