import sys, json, time; sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3")
import harness as H
K = 150; B = H.BUILT[K]
V = {"BUILT": B}
# (a) NOISE profit lock trigger/offset (shipped 100/10 = built); 11 new
for t in (80, 100, 120):
    for o in (0, 10, 20, 30):
        if (t, o) != (100, 10): V[f"a_lock{t}/{o}"] = dict(B, lock=(t, o))
# (b) emergency stop
for s in (75, 125, 150): V[f"b_stop{s}"] = dict(B, stop=s)
# (c) day lock
for d in (0.5, 0.6, 0.8): V[f"c_dl{d}"] = dict(B, dlock=d)
# (d) CANDACE vs NOISE size balance
for N, nc in ((5, 3), (5, 4), (4, 5), (4, 4), (6, 5), (5, 6)): V[f"d_N{N}C{nc}"] = dict(B, N=N, nc=nc)
def run_all(S, S2, tag):
    pass
R = {}
S = H.sim(K)
for n, v in V.items():
    c = H.cfg(K, **v); R[n] = H.metrics(S, c); print(n, flush=True)
# cost sensitivity: +$2 per micro RT on NOISE and CANDACE
S2 = H.sim(K); S2.NADD = 2.0; S2.COST1 = 4.0
for n, v in V.items():
    S2._cache.clear(); R[n]["cost2"] = H.metrics(S2, H.cfg(K, **v))
json.dump(R, open("/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3/results_r3.json", "w"), indent=1, default=float)
