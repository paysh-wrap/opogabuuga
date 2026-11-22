"""Verdict checks + paired quarterly comparison. Prints; report.py reuses the functions."""
import json, os, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(HERE + "/results.json"))
TESTS = ["LOCK80", "N+CANDACE", "N+VWAP"]


def g(mix, k, meth, w): return R[f"{mix}|{k}|{meth}|{w}"]


def verdict_cell(test, k, w, meth="roll", stuck="roll"):
    b = g("BASE", k, meth, w); t = g(test, k, meth, w if meth != "static" else w)
    sb = g("BASE", k, "static", w if w in ("ALL", "PICK", "JUDGE") else "ALL"); st = g(test, k, "static", w if w in ("ALL", "PICK", "JUDGE") else "ALL")
    a = (t["med"] is not None and b["med"] is not None and t["med"] < b["med"]) or t["pass_"] > b["pass_"]
    bb = t["bust_all"] <= b["bust_all"] + 2
    c = st["tp"] >= sb["tp"] and st["t1"] >= sb["t1"]
    return dict(faster_or_more=a, bust_ok=bb, profit_ok=c, ok=a and bb and c,
                d_pass=t["pass_"] - b["pass_"], d_bust=t["bust_all"] - b["bust_all"], d_med=(t["med"] - b["med"]) if t["med"] and b["med"] else None,
                d_tp=st["tp"] - sb["tp"], d_t1=st["t1"] - sb["t1"])


def quarterly(test, k):
    """paired by start quarter (rolling, window ALL): pass % of test minus pass % of BASE; returns list of diffs, mean, se, #better/#worse/#equal"""
    b = g("BASE", k, "roll", "ALL")["detail"]; t = g(test, k, "roll", "ALL")["detail"]
    qb = collections.defaultdict(list); qt = collections.defaultdict(list)
    for (d, o, s), (d2, o2, s2) in zip(b, t):
        assert d == d2
        q = d[:4] + "Q" + str((int(d[5:7]) - 1) // 3 + 1)
        qb[q].append(o == "pass"); qt[q].append(o2 == "pass")
    qs = sorted(qb)
    diffs = [100 * (np.mean(qt[q]) - np.mean(qb[q])) for q in qs]
    return qs, diffs, float(np.mean(diffs)), float(np.std(diffs, ddof=1) / np.sqrt(len(diffs))), sum(x > 0.5 for x in diffs), sum(x < -0.5 for x in diffs), sum(abs(x) <= 0.5 for x in diffs)


if __name__ == "__main__":
    for test in TESTS:
        for k in (25, 50):
            for w in ("JUDGE", "ALL"):
                print(test, k, w, "roll", {x: (round(y, 1) if isinstance(y, float) else y) for x, y in verdict_cell(test, k, w).items()})
                print(test, k, w, "boot", {x: (round(y, 1) if isinstance(y, float) else y) for x, y in verdict_cell(test, k, w, "boot").items()})
            q = quarterly(test, k)
            print(test, k, "quarterly: mean diff %.1f se %.1f better %d worse %d equal %d" % q[2:])
