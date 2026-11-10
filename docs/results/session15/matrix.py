"""Step 4: every surviving stream x every Pro plan x a SMALL fixed sizing list (micros 1..N, optional drawdown brake = half size while the
cushion above the loss limit is under 50% of the limit).  Writes out/matrix.json.  Pick on IS, judge on HO (see report.py)."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
import lib, account as A

STREAMS = ["N0_MNQ", "N1_MNQ", "N6_MNQ", "N7_MNQ", "N2_MNQ", "N3_MNQ"]
QS = {"25K": [1, 2], "50K": [1, 2, 3], "100K": [1, 2, 3, 4], "150K": [1, 2, 3, 4, 5]}


def cfgs(plan):
    for q in QS[plan]:
        yield dict(q=q)
        if q >= 2: yield dict(q=q, brake=(0.5, math.ceil(q / 2)))


def job(a):
    key, plan, cfg = a
    t = A.load(key); tab = lib.day_table(t); R = lib.plan_rules(plan)
    return dict(stream=key, plan=plan, cfg=cfg, **A.full(tab, R, cfg, cfg))


if __name__ == "__main__":
    jobs = [(k, p, c) for k in STREAMS for p in QS for c in cfgs(p)]
    with Pool(4) as pool: res = pool.map(job, jobs, chunksize=2)
    edges = {k: {e: A.edge(A.load(k), e) for e in ("IS", "HO")} for k in STREAMS}
    json.dump(dict(rows=res, edges=edges), open(f"{A.OUT}/matrix.json", "w"), default=float)
    print(len(res))
