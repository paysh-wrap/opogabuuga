"""passfloor step 1: reproduce BUILT yaml setups + reference 'new best' setups + BASE per plan (C40, DLL ON). Research only."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../within60")
from lib import *
HERE = os.path.dirname(os.path.abspath(__file__))
import multiprocessing as mp
T3 = 1 / 3.; EPS = 1e-4
CFGS = {
    # BASE (shipped size rows)
    "25|BASE": mkcfg(250, 1, 0), "100|BASE": mkcfg(250, 2, 0, brake=(0.3, 1)), "150|BASE": mkcfg(250, 3, 0, brake=(0.5, 2)),
    # BUILT yaml
    "25|BUILT": mkcfg(75, 1, 2, cb=((T3, 1),)),
    "100|BUILT": mkcfg(250, 2, 3, nb=((T3, 1),), cb=((T3, 2),)),
    "150|BUILT": mkcfg(100, 5, 4, nb=((T3, 2),), cb=((T3, 2),)),
    "150|BUILT_incl": mkcfg(100, 5, 4, nb=((T3 + EPS, 2),), cb=((T3 + EPS, 2),)),
    # reference "new best"
    "25|REF": mkcfg(75, 1, 2, cb=((0.5, 1),), lock=80),
    "100|REF": mkcfg(250, 2, 3, nb=((T3, 1),), cb=((T3, 1),)),
    "150|REF": mkcfg(100, 4, 3, nb=((0.5, 2),)),
    "150|U1": mkcfg(100, 4, 3, nb=((T3, 2),), cb=((T3, 2),)),
}


def job(n):
    k = int(n.split("|")[0]); return ev((k, True, n, CFGS[n]))


if __name__ == "__main__":
    t = time.time()
    with mp.Pool(4) as p: res = dict(p.map(job, list(CFGS)))
    json.dump(res, open(HERE + "/repro.json", "w"), indent=1, default=float)
    for n, r in res.items():
        a = r["ALL"]
        print(f"{n:16s} pass {a['pass']:.1f} stuck {a['stuck']:.1f} <=60 {a['p60']:.1f} med {a['med']} chain {r['chain']['mean']:.0f} judge {r['JUDGE']['pass']:.1f} pick {r['PICK']['pass']:.1f} profit {r['profit']:.0f}")
    print(round(time.time() - t), "s")
