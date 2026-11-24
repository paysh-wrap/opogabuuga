import sys, json, time; sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3")
import harness as H
for k in (150, 50):
    t = time.time(); S = H.sim(k); m = H.metrics(S, H.cfg(k, **H.BUILT[k]))
    print(k, {w: (round(m[w]["pass_"], 1), m[w]["med"], round(m[w]["stuck_bust"], 1)) for w in ("ALL", "PICK", "JUDGE")}, round(m["profit"]), round(m["dd"]), round(time.time() - t), flush=True)
    print(m["hy"])
