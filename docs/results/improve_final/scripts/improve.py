"""improve_final part B: new rows vs D163 built. Reuses final.py machinery (same sim). Run: cd <main>/backend; PYTHONPATH=. python3 improve.py"""
import sys, json, os
sys.path.insert(0, "/home/user/opogabuuga/docs/results/pass_fastest/final_search")
import final as F
F.FN = os.path.dirname(os.path.abspath(__file__)) + "/../results.json"
B = {k: dict(v) for k, v in F.BUILT.items()}
B[150]["cgrow"] = (1500., 6); B[50]["dlock"] = 0.4
F.BUILT.update(B)
def V(k):
    b = B[k]; o = []
    for dl in (0.3, 0.35, 0.45, 0.6): o.append(dict(b, dlock=dl))
    for lk in (60, 70, 90): o.append(dict(b, lock=lk))
    for t in ((0.15, 1), (0.35, 1), (0.5, 2)): o.append(dict(b, taper=t))
    for s in (0.9, 1.1): o.append(dict(b, cb=tuple((round(d * s), m) for d, m in b.get("cb", ()))))
    for s in (0.85, 0.9, 1.1): o.append(dict(b, nb=tuple((round(d * s), m) for d, m in b.get("nb", ()))))
    for dl in (0.4, 0.5): o.append(dict(b, dlock=dl, dlall=True))
    # extra CANDACE band step, extra NOISE brake step
    M = F.MLL[k]
    o.append(dict(b, cb=tuple(b.get("cb", ())) + ((round(M * .45), max(b["nc"] - 1, 1)),)))
    o.append(dict(b, nb=tuple(b.get("nb", ())) + ((round(M * .4), max(b["N"] - 1, 1)),)))
    return [dict(sorted(v.items())) for v in o]
if __name__ == "__main__":
    store = json.load(open(F.FN)) if os.path.exists(F.FN) else {}
    F.run([(k, dict(sorted(B[k].items()))) for k in B] + [(k, v) for k in B for v in V(k)], store)
    for k in B:
        br = store[F.nm(k, dict(sorted(B[k].items())))]
        print(k, "BASE", br["ALL"]["pass"], br["ALL"]["med"], br["JUDGE"]["pass"], br["PICK"]["pass"], br["profit"])
        for key, r in store.items():
            if key.startswith(f"{k}|") and F.feas(k, r, br): print("  FEAS", key[:200], r["ALL"]["pass"], r["ALL"]["med"], r["JUDGE"]["pass"], r["PICK"]["pass"], r["profit"])
