import sys; sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3")
import harness as H
H.PLANS[25] = (25000., 1250., 1000., 26100., 25100., 600., 500.)
H.PLANS[100] = (100000., 6000., 3000., 103100., 100100., 1800., 1500.)
H.MLL[25] = 1000.; H.MLL[100] = 3000.
H.BUILT[25] = dict(stop=75, N=1, nc=2, cb=((333, 1),))
H.BUILT[100] = dict(stop=100, N=3, nc=3, nb=((1000, 2),), cb=((600, 2),), dlock=0.5)
def sim(k, ds=0.38, cost=False):
    S = H.sim(k); S.DSTOP = ds * S.TARGET
    if cost: S.NADD = 2.0; S.COST1 = 4.0
    return S
