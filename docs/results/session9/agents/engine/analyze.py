"""Feature screen on research.py+indscreen DUMP_ROWS. Engine target rule 1.5-2.5R (skip T2<1.5R, TP=min(T2,2.5R)).
usage: analyze.py SYMBOL ROWS_IS.json ROWS_OOS.json USD_PER_R_HINT(ignored)"""
import itertools, json, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
ET = ZoneInfo("America/New_York")


def load(p):
    rows = [r for r in json.load(open(p)) if r.get("t2rr") is not None and r.get("mfe") is not None]
    out = {}
    T2 = np.array([r["t2rr"] for r in rows]); MFE = np.array([r["mfe"] for r in rows])
    STOP = np.array([r["stopped"] for r in rows]); FLAT = np.array([r["flat_r"] or 0.0 for r in rows])
    FEE = np.array([r["fee_r"] for r in rows]); SLIP = np.array([r["slip_r"] for r in rows])
    k = np.minimum(T2, 2.5); win = MFE >= k
    R = np.where(win, k - FEE, np.where(STOP, -1 - SLIP - FEE, FLAT - FEE))
    h = np.array([(lambda t: t.hour + t.minute / 60)(datetime.fromtimestamp(r["t0ms"] / 1000, ET)) for r in rows])
    f = {"all": np.ones(len(rows), bool)}
    base = np.array([r["score"] >= 60 and r["c1atr"] >= 0.4 for r in rows]) & (T2 >= 1.5)
    for key in ("brk", "choch", "bos", "cisd", "osc", "htf", "mso", "vwap", "eng_utbot_5m", "eng_ema200_5m",
                "ema200_5", "ut_5", "st_15", "ema200_15", "st_60", "ema200_60", "adx20_5", "rsi_side_15"):
        f[key] = np.array([bool(r.get(key)) for r in rows])
    f["long"] = np.array([r["d"] == 1 for r in rows]); f["short"] = ~f["long"]
    f["STD"] = np.array([r["profile"] == "STD" for r in rows]); f["TIGHT"] = ~f["STD"]
    f["c1atr>=0.7"] = np.array([r["c1atr"] >= 0.7 for r in rows])
    f["score>=70"] = np.array([r["score"] >= 70 for r in rows])
    f["T2>=2.5"] = T2 >= 2.5
    f["asia/ldn<09:30"] = h < 9.5; f["rth_am 9.5-11.5"] = (h >= 9.5) & (h < 11.5); f["pm>=11.5"] = h >= 11.5
    f["ny 8-11.5"] = (h >= 8) & (h < 11.5); f["<8"] = h < 8
    f["trend3"] = f["eng_utbot_5m"] & f["eng_ema200_5m"]
    sess = np.array([r["sess"] for r in rows])
    return dict(R=R, win=win, base=base, f=f, sess=sess, n_sess=len(set(sess)))


def st(d, m):
    r = d["R"][m]; n = len(r)
    if not n:
        return f"{0:4d}"
    pf = r[r > 0].sum() / max(-r[r < 0].sum(), 1e-9)
    return f"{n:4d} {d['win'][m].mean():4.0%} {r.mean():+.2f}R PF{pf:4.2f}"


sym, a, b = sys.argv[1:4]
A, B = load(a), load(b)
print(f"{sym}: IS sessions {A['n_sess']} | OOS sessions {B['n_sess']}  (base = score>=60, C1>=0.4ATR, T2>=1.5R; TP min(T2,2.5R))")
print(f"{'feature':22s} {'IS true':24s} {'IS false':24s} | {'OOS true':24s} {'OOS false':24s}")
for k in A["f"]:
    print(f"{k:22s} {st(A, A['base'] & A['f'][k]):24s} {st(A, A['base'] & ~A['f'][k]):24s} | "
          f"{st(B, B['base'] & B['f'][k]):24s} {st(B, B['base'] & ~B['f'][k]):24s}")
names = [k for k in A["f"] if k != "all"]
res = []
for n in (1, 2, 3):
    for c in itertools.combinations(names, n):
        m = A["base"].copy()
        for k in c:
            m &= A["f"][k]
        if m.sum() < 40:
            continue
        res.append((A["R"][m].mean(), c))
res.sort(reverse=True)
print("\nTop 15 combos picked on IS (>=40 IS trades), judged on OOS:")
for e, c in res[:15]:
    ma = A["base"].copy(); mb = B["base"].copy()
    for k in c:
        ma &= A["f"][k]; mb &= B["f"][k]
    print(f"  {' & '.join(c):45s} IS {st(A, ma)} | OOS {st(B, mb)} {mb.sum() / B['n_sess']:.2f}/d")
for spec in sys.argv[4:]:
    c = spec.split("+")
    ma = A["base"].copy(); mb = B["base"].copy()
    for k in c:
        ma &= A["f"][k]; mb &= B["f"][k]
    print(f"  [named] {spec:37s} IS {st(A, ma)} | OOS {st(B, mb)} {mb.sum() / B['n_sess']:.2f}/d")
