import sys; sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3")
import harness as H
S = H.sim(150)
for d in (None, 0.1, 0.2, 0.3, 0.4, 0.7):
    m = H.metrics(S, H.cfg(150, **dict(H.BUILT[150], dlock=d)))
    print("dlock", d, [(round(m[w]["pass_"], 1), m[w]["med"]) for w in ("PICK", "JUDGE", "ALL")], round(m["profit"]))
