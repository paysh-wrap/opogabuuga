"""Step 5: (a) today's app baseline = NOISE alone at the live size table, (b) NOISE + profit lock (N1) with a small list of brake settings per plan,
(c) profit-lock sensitivity (is +100 pt / +10 pt a knife-edge?).  Writes out/final.json.  S15_RAW must point at the raw folder for (c)."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
import lib, account as A

LIVE_F = {"25K": dict(q=1), "50K": dict(q=2, brake=(0.5, 1)), "100K": dict(q=2, brake=(0.3, 1)), "150K": dict(q=3, brake=(0.5, 2))}
LIVE_E = {"25K": dict(q=1), "50K": dict(q=2, brake=(0.5, 1)), "100K": dict(q=2, brake=(0.3, 1)), "150K": dict(q=4, brake=(0.5, 2))}
QS = {"25K": [1], "50K": [1, 2], "100K": [1, 2, 3], "150K": [2, 3, 4]}


def brakes(q):
    yield None
    if q >= 2:
        h = math.ceil(q / 2)
        for th in (0.3, 0.5, 0.7): yield (th, h)
        if h != 1: yield (0.5, 1)
        if q >= 3: yield (0.7, 1)


def job(a):
    tag, key, plan, ecfg, fcfg = a
    tab = lib.day_table(A.load(key)); R = lib.plan_rules(plan)
    return dict(tag=tag, stream=key, plan=plan, ecfg=ecfg, fcfg=fcfg, **A.full(tab, R, ecfg, fcfg))


if __name__ == "__main__":
    jobs = [("live", "N0_MNQ", p, LIVE_E[p], LIVE_F[p]) for p in LIVE_F]
    for p in QS:
        for q in QS[p]:
            for b in brakes(q):
                c = dict(q=q) if b is None else dict(q=q, brake=b)
                jobs.append(("n1", "N1_MNQ", p, c, c))
    with Pool(4) as pool: res = pool.map(job, jobs, chunksize=2)
    sens = []
    for trig, lk in ((75, 10), (100, 0), (100, 10), (100, 25), (150, 10), (200, 10)):
        t = lib.noise_stream("MNQ", lock=(trig, lk))
        sens.append(dict(trigger=trig, lock=lk, IS=dict(**lib.stream_stats(t, "IS"), **A.edge(t, "IS")), HO=dict(**lib.stream_stats(t, "HO"), **A.edge(t, "HO"))))
    json.dump(dict(rows=res, sens=sens), open(f"{A.OUT}/final.json", "w"), default=float)
