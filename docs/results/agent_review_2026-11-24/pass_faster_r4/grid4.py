# PRE-REGISTERED GRID (written before any judge-window result was viewed). Rule: ADOPT CANDIDATE iff
# strictly better than BUILT on PICK and JUDGE for pass % AND median days, static profit >= built,
# all-window pass >= plan floor (25K 62 / 50K 62 / 100K 70 / 150K 70, or built if lower), +$2 cost all-window pass >= built at +$2,
# and half-year min pass >= built HY min.
import json, h4; H = h4.H
B = H.BUILT
def sc(steps, f): return tuple((round(c * f), n) for c, n in steps)
G = {}
for k in (25, 50, 100, 150):
    b = B[k]; G[(k, "BUILT", 0.38)] = b
    for f in (0.75, 1.33):                       # (1) brake ladder thresholds
        G[(k, f"brake_x{f}", 0.38)] = dict(b, nb=sc(b.get("nb", ()), f), cb=sc(b.get("cb", ()), f))
    for ds in (0.30, 0.45):                      # (3) day stop vs 40 % consistency
        G[(k, f"dstop{ds}", ds)] = b
    G[(k, "dstop0.38_dl0.3", 0.38)] = dict(b, dlock=0.3)
# (1) grow rules
for g in (300, 750): G[(150, f"ngrow{g}", 0.38)] = dict(B[150], grow=(float(g), 6))
for g in (1000, 2250): G[(150, f"cgrow{g}", 0.38)] = dict(B[150], cgrow=(g, 6))
G[(100, "ngrow1000max4", 0.38)] = dict(B[100], grow=(1000., 4))
G[(100, "cgrow1000max4", 0.38)] = dict(B[100], cgrow=(1000, 4))
G[(50, "cgrow700max5", 0.38)] = dict(B[50], cgrow=(700, 5))
G[(25, "cgrow400max3", 0.38)] = dict(B[25], cgrow=(400, 3))
# (4) front-load: start bigger, brake back when cushion thin
G[(100, "front_N4C4", 0.38)] = dict(B[100], N=4, nc=4, nb=((1000, 2),), cb=((600, 2),))
G[(50, "front_C5", 0.38)] = dict(B[50], nc=5, cb=((1000, 3),))
G[(25, "front_C3", 0.38)] = dict(B[25], nc=3, cb=((333, 1),))
R = {}
for (k, n, ds), v in G.items():
    r = {}
    for cost in (False, True):
        S = h4.sim(k, ds, cost); m = H.metrics(S, H.cfg(k, **v)); r["c2" if cost else "base"] = m
    R[f"{k}|{n}"] = r; print(k, n, flush=True)
json.dump(R, open("results4.json", "w"), default=float, indent=0)
print("variants (excl built):", len(G) - 4)
