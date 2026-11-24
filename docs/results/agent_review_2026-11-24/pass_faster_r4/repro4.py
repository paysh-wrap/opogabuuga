import time, h4; H = h4.H
for k in (25, 50, 100, 150):
    t = time.time(); S = h4.sim(k); m = H.metrics(S, H.cfg(k, **H.BUILT[k]))
    print(k, {w: (round(m[w]["pass_"], 1), m[w]["med"], round(m[w]["stuck_bust"], 1)) for w in ("ALL", "PICK", "JUDGE")}, round(m["profit"]), round(time.time() - t), flush=True)
