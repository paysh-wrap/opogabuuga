"""Session 16 fast-evaluation study. Stream = session15 N1_MNQ (NOISE + D75-P1 lock, fade OFF), per-1-micro trades.
Pick on IS (2021-11..2023-12), judge on HO (2024-01..2026-10) and L12 (2025-11..2026-10). Raw bars are not in the repo -> day filters use stream-only proxies.
Reading A: best day <= 40% of target AND >=3 profitable days. Reading B: 40% of day-start balance (never binds) + >=3 profitable days."""
import sys, os, json, random, itertools, statistics as st
from multiprocessing import Pool
S15 = "/home/user/opogabuuga/docs/results/session15"
sys.path.insert(0, S15)
import lib, account as A
from pathlib import Path
OUT = os.path.dirname(os.path.abspath(__file__))
tab = lib.day_table(A.load("N1_MNQ"))
def era(e):
    if e == "IS": return [t for d, t in tab if d <= lib.SPLIT]
    if e == "HO": return [t for d, t in tab if d > lib.SPLIT]
    return [t for d, t in tab if d >= "2025-11-01"]
PLANS = {  # name: yaml, qmax, base size (s15 rec), base brake frac
 "Daily25K": ("lucid_daily_25k", 2, 1), "Flex25K": ("lucid_flex_25k", 2, 1), "Flex50K": ("lucid_flex_50k", 3, 1),
 "Flex100K": ("lucid_flex_100k", 4, 2), "Flex150K": ("lucid_flex_150k", 6, 3)}
_RC={}
def rules(name):
    if name in _RC: return _RC[name]
    r = lib.load_rules(Path(f"/home/user/opogabuuga/config/rules/{PLANS[name][0]}.yaml")).rules; e = r.eval
    f = lambda x: None if x is None else float(x)
    _RC[name] = dict(start=float(r.account_size), target=f(e.profit_target), mll=f(e.max_loss_limit), lt=f(e.lock_trigger), ll=f(e.lock_level), dll=f(e.daily_loss_limit)); return _RC[name]
def paths(e, n, seed, cap=750, block=10):
    d = era(e); rnd = random.Random(seed); out = []
    for _ in range(n):
        p = []
        while len(p) < cap:
            i = rnd.randrange(len(d)); p.extend(d[i:i + block])
        out.append(p[:cap])
    return out
def run(path, R, c, reading):
    bal = peak = R["start"]; floor = bal - R["mll"]; pos = []; tgt = R["target"]; mll = R["mll"]; dll = R["dll"]
    last_loss = False; prev_day = 0.0; hist = []
    for n, trades in enumerate(path):
        b0 = bal; day = 0.0; traded = False
        cush = bal - floor; prof = bal - R["start"]
        q = c["lo"]
        if c["hi"] > c["lo"] and cush >= c["X"] * mll and not (c["droploss"] and last_loss) and (c["early"] is None or prof < c["early"] * tgt):
            q = c["hi"]
        f = c["filt"]
        skip = (f == "prev" and prev_day < 0) or (f == "tr10" and sum(hist[-10:]) < 0)
        if skip: trades = []
        for pnl, mae, risk in trades:
            if c["dstop"] is not None and day >= c["dstop"] * tgt: break
            worst = -max(mae, -pnl) if mae > 0 else min(pnl, 0)
            if bal + q * worst <= floor: return "BUST", n + 1
            p = pnl * q
            if dll is not None and day + p <= -dll: p = -dll - day
            bal += p; day += p; traded = True; last_loss = p < 0
            if bal <= floor: return "BUST", n + 1
            if dll is not None and day <= -dll: break
        if traded: pos.append(bal - b0)
        prev_day = bal - b0; hist.append(prev_day)
        peak = max(peak, bal); floor = R["ll"] if peak >= R["lt"] else max(floor, peak - mll)
        prof = bal - R["start"]
        if prof >= tgt and sum(1 for x in pos if x > 0) >= 3 and (reading == "B" or max(pos, default=0) <= 0.4 * tgt):
            return "PASS", n + 1
    return "OPEN", len(path)
def summ(res):
    n = len(res); P = sorted(s for o, s in res if o == "PASS"); np_ = len(P)
    q = lambda p: P[min(len(P) - 1, int(p * len(P)))] if P else None
    tot = sum(s for _, s in res)
    return dict(pass_=100 * np_ / n, bust=100 * sum(o == "BUST" for o, _ in res) / n, open_=100 * sum(o == "OPEN" for o, _ in res) / n,
                p25=q(.25), med=q(.5), p75=q(.75), per_pass=(tot / np_) if np_ else None)
def evaluate(plan, c, reading, e, n, seed=5):
    R = rules(plan); return summ([run(p, R, c, reading) for p in paths(e, n, seed)])
def grid(plan):
    _, qmax, q0 = PLANS[plan]; out = []
    for hi in range(1, qmax + 1):
        for X in ([0.5] if hi == 1 else [0.3, 0.5, 0.7, 0.9]):
            for dl in ([False] if hi == 1 else [False, True]):
                for early in ([None] if hi == 1 else [None, 0.5]):
                    for dstop in (None, 0.35):
                        for filt in (None, "prev", "tr10"):
                            out.append(dict(lo=1, hi=hi, X=X, droploss=dl, early=early, dstop=dstop, filt=filt))
    return out
def key(c): return json.dumps(c, sort_keys=True)
def job(a):
    plan, reading, c = a
    return plan, reading, c, {e: evaluate(plan, c, reading, e, 1000 if e != "IS" else 400) for e in ("IS", "HO", "L12")} 
def job_is(a):
    plan, reading, c = a
    return plan, reading, c, evaluate(plan, c, reading, "IS", 300)
for _p in PLANS: rules(_p)
if __name__ == "__main__":
    reading = sys.argv[1]
    res = {}
    with Pool(4) as pool:
        for plan in PLANS:
            _, qmax, q0 = PLANS[plan]
            G = grid(plan)
            r = pool.map(job_is, [(plan, reading, c) for c in G], chunksize=8)
            ok = [(x[3]["per_pass"], x) for x in r if x[3]["per_pass"] and x[3]["bust"] <= 40]
            ok.sort(key=lambda t: t[0]); picks = [x[2] for _, x in ok[:12]]
            # fixed reference set (judged regardless): baseline flat, s15 recommended ladder, flat sizes
            ref = [dict(lo=1, hi=1, X=.5, droploss=False, early=None, dstop=None, filt=None)]
            ref += [dict(lo=1, hi=h, X=x, droploss=False, early=None, dstop=None, filt=None) for h in range(2, qmax + 1) for x in (.5,)]
            ref += [dict(lo=1, hi=1, X=.5, droploss=False, early=None, dstop=0.35, filt=None)]
            allc = {key(c): c for c in picks + ref}
            out = pool.map(job, [(plan, reading, c) for c in allc.values()], chunksize=2)
            res[plan] = dict(is_all=[(x[2], x[3]) for x in r], final=[(x[2], x[3], key(x[2]) in {key(p) for p in picks}) for x in out])
            print(plan, reading, len(G), "done", flush=True)
    json.dump(res, open(f"{OUT}/out_{reading}.json", "w"), default=float)
