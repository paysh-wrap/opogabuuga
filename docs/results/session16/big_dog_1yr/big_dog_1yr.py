"""Big Dog Small Trade Aggressive - last 12 months (2025-11-01..2026-10-31), all Lucid plans in config/rules. Research only.
usage: python3 big_dog_1yr.py <MNQ.csv> <MGC.csv> [seeds=200] [acct_seeds=40] [paths=25]
Reuses data loader/VWAP/5m bars from ../ai_duo_window/ai_duo_window.py and the account engine (eval_run/funded_run/plan_rules) from ../../session15/lib.py.
AI side is SIMULATED (accuracy vs the day's real RTH open->close direction); NEUTRAL days skipped at random (27%). Results are BOUNDS, not evidence."""
import sys, os, json, pickle, random
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(HERE + "/../../../..")
sys.path[:0] = [HERE + "/../ai_duo_window", ROOT + "/docs/results/session15"]
import ai_duo_window as AD
import lib

LO, HI = "2025-11-01", "2026-10-31"
WS, WE, ANCHOR = 936, 1050, 930          # 09:36-11:30 ET, RTH VWAP anchored 09:30
INST = {"MNQ": dict(pv=2.0, tick=0.25, fee=1.0, jump=0.01, ffill=False), "MGC": dict(pv=10.0, tick=0.1, fee=1.6, jump=0.02, ffill=True)}
ACCS = [0.50, 0.60, 0.65, 0.70]; NEUTRAL = 0.27
PLAN_FILES = ["lucid_pro_25k", "lucid_pro_50k", "lucid_pro_100k", "lucid_pro_150k", "lucid_flex_25k", "lucid_flex_50k", "lucid_flex_100k",
              "lucid_flex_150k", "lucid_daily_25k"]
SIZE = {"25K": (1000, 1250), "50K": (2000, 3000), "100K": (3000, 6000), "150K": (4500, 9000)}   # (MLL, eval target)
RR = 2.0


def walk(a, s, me, K, e, stop, sp):
    """managed trade, 1 contract. BE at +1R, trail 1R from +1.5R, MNQ lock +100pt->entry+50pt, MGC step trail (20 ticks per 60 ticks). 2R limit target."""
    pv, tk, fee = K["pv"], K["tick"], K["fee"]; tgt = e + s * RR * sp; mfe = 0.0; mae = 0.0
    better = (lambda x, y: max(x, y)) if s > 0 else (lambda x, y: min(x, y))
    for j in range(me, WE):
        if np.isnan(a["close"][j]): continue
        hj, lj, oj = a["high"][j], a["low"][j], a["open"][j]
        mae = max(mae, ((e - lj) if s > 0 else (hj - e)) * pv)
        if (s > 0 and lj <= stop) or (s < 0 and hj >= stop):
            px = (min(stop, oj) if s > 0 else max(stop, oj)) - s * tk
            return (px - e) * s * pv - fee, j, mae + tk * pv
        if (s > 0 and hj >= tgt + tk) or (s < 0 and lj <= tgt - tk):
            return (tgt - e) * s * pv - fee, j, mae
        mfe = max(mfe, (hj - e) if s > 0 else (e - lj))
        new = stop
        if mfe >= sp: new = better(new, e)
        if mfe >= 1.5 * sp: new = better(new, e + s * (mfe - sp))
        if K["sym"] == "MNQ":
            if mfe >= 100: new = better(new, e + s * 50)
        else:
            st = int(mfe / tk // 60)
            if st >= 1: new = better(new, e + s * st * 20 * tk)
        stop = new
    j = WE - 1
    while j > me and np.isnan(a["close"][j]): j -= 1
    return (a["close"][j] - s * tk - e) * s * pv - fee, j, mae + tk * pv


def stream(a, b5, vw, s, K, cap_usd, maxn=5):
    """sequential trades, one market/day/side: VWAP pullback close in side; re-entry on later pullbacks after the previous exit."""
    out = []; start = WS
    while len(out) < maxn:
        got = None
        for bi in range(start // 5 - 1, WE // 5 - 1):
            b = bi * 5
            if b + 5 < start: continue
            if 930 <= b < 935: continue
            if b + 5 > WE - 5: break
            o, h, l, c = b5["open"][bi], b5["high"][bi], b5["low"][bi], b5["close"][bi]
            if np.isnan(c) or np.isnan(h): continue
            v = vw[b + 4]
            trig = (l <= v < c and c > o) if s > 0 else (h >= v > c and c < o)
            if not trig: continue
            pb = [bi, bi - 1] if bi > 0 else [bi]
            ext = np.nanmin(b5["low"][pb]) if s > 0 else np.nanmax(b5["high"][pb]); me = b + 5
            if np.isnan(a["open"][me]): continue
            e = a["open"][me] + s * K["tick"]; stop = ext - s * K["tick"]; sp = abs(e - stop)
            if sp < K["minstop"]: sp = K["minstop"]; stop = e - s * sp
            risk1 = sp * K["pv"] + K["fee"] + 2 * K["tick"] * K["pv"]
            if risk1 > cap_usd: continue      # structure stop too wide for even 1 micro inside the per-trade budget -> skip signal
            pnl, xj, mae = walk(a, s, me, K, e, stop, sp)
            got = (me, xj, pnl, mae, risk1); break
        if not got: break
        out.append(got); start = got[1] + 1
    return out


def build_cands(path_by_sym):
    caps = sorted({0.125 * m for m, _ in SIZE.values()})
    M = {}
    for sym, path in path_by_sym.items():
        K = dict(INST[sym]); K["sym"] = sym; K["minstop"] = 10.0 / K["pv"]
        days, sk = AD.load(path, K); days = [(d, a) for d, a in days if LO <= d <= HI]
        M[sym] = dict(date=[d for d, _ in days], tr=[], C={c: {1: [], -1: []} for c in caps})
        for d, a in days:
            cl = a["close"][930:1320]; cl = cl[~np.isnan(cl)]; M[sym]["tr"].append(np.sign(cl[-1] - a["open"][930]) or 1)
            b5 = AD.bars5(a); vw = AD.vwap_from(a, ANCHOR)
            for c in caps:
                for s in (1, -1): M[sym]["C"][c][s].append(stream(a, b5, vw, s, K, c))
        print(sym, "days", len(days), "skipped", sk, flush=True)
    return M


def day_apply(cands, mll, target, maxq):
    """cands: (entry m, exit m, pnl1, mae1, risk1) from both markets. Plan day rules -> taken [(pnl, mae, risk)] at plan size."""
    budget = 0.125 * mll; dll = 0.375 * mll; lock = 0.39 * target
    taken = []; done = []; ntr = 0
    for em, xm, pnl1, mae1, risk1 in sorted(cands):
        closed = [p for x, p in done if x <= em]; day = sum(closed); losses = sum(p < 0 for p in closed)
        if ntr >= 5 or losses >= 3 or day >= lock or day <= -dll: break
        q = int(min(maxq, budget // risk1, (dll + day) // risk1))
        if q < 1: continue
        ntr += 1; done.append((xm, pnl1 * q)); taken.append((pnl1 * q, mae1 * q, risk1 * q))
    return taken


def sim_cfg(M, size, acc, seed):
    mll, target = SIZE[size]; maxq = max(1, round(3 * mll / 1000)); cap = 0.125 * mll
    alld = sorted(set(M["MNQ"]["date"]) | set(M["MGC"]["date"])); ix = {d: i for i, d in enumerate(alld)}; N = len(alld)
    pos = {m: {d: k for k, d in enumerate(M[m]["date"])} for m in M}; calls = {}
    for mi, m in enumerate(("MNQ", "MGC")):
        rng = np.random.default_rng(seed * 7919 + mi * 104729 + int(acc * 100) * 31 + 27)
        tr = np.zeros(N); tr[[ix[d] for d in M[m]["date"]]] = M[m]["tr"]
        calls[m] = (np.where(rng.random(N) < acc, tr, -tr), rng.random(N) < NEUTRAL)
    days = []
    for i, d in enumerate(alld):
        c = []
        for m in ("MNQ", "MGC"):
            call, neutral = calls[m]
            if neutral[i] or d not in pos[m]: continue
            c += M[m]["C"][cap][1 if call[i] > 0 else -1][pos[m][d]]
        days.append(day_apply(c, mll, target, maxq))
    return alld, days


def tstats(days):
    p = np.array([x[0] for t in days for x in t]); nd = len(days)
    if len(p) == 0: return dict(n=0, win=np.nan, pf=np.nan, net=0.0, dd=0.0, per_day=0.0)
    w = p[p > 0].sum(); l = -p[p <= 0].sum(); eq = np.cumsum(p)
    return dict(n=len(p), win=(p > 0).mean() * 100, pf=min(w / l, 50) if l > 0 else 50.0, net=p.sum(), dd=(eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), per_day=len(p) / nd)


def boot(days, n, length, block, seed):
    rnd = random.Random(seed); N = len(days); out = []
    for _ in range(n):
        p = []
        while len(p) < length:
            i = rnd.randrange(N); p.extend(days[i:i + block])
        out.append(p[:length])
    return out


_M = None
def job(args):
    size, acc, nseeds, nacct, npaths = args
    M = _M; res = []; plans = [f for f in PLAN_FILES if f.endswith("_" + size.lower())]
    Rs = {}
    for f in plans:
        lib.PLANS["x"] = f; Rs[f] = lib.plan_rules("x")
    agg = []; acct = {f: dict(ep=[], eb=[], eo=[], emed=[], fb=[], fpay=[], fany=[]) for f in plans}
    cfg = {"q": 1}
    for seed in range(nseeds):
        alld, days = sim_cfg(M, size, acc, seed); agg.append(tstats(days))
        if seed < nacct:
            for f in plans:
                R = Rs[f]
                er = [lib.eval_run(p, R, cfg, 750) for p in boot(days, npaths, 750, 10, seed * 13 + 1)]
                ps = [s for o, s in er if o == "PASS"]
                a = acct[f]; a["ep"].append(100 * len(ps) / len(er)); a["eb"].append(100 * sum(o == "BUST" for o, _ in er) / len(er))
                a["eo"].append(100 * sum(o == "OPEN" for o, _ in er) / len(er)); a["emed"] += ps
                fr = [lib.funded_run(p, R, cfg, 10) for p in boot(days, npaths, 260, 10, seed * 17 + 5)]
                a["fb"].append(100 * sum(x["status"] == "BUST" for x in fr) / len(fr)); a["fany"].append(100 * sum(x["npay"] > 0 for x in fr) / len(fr))
                a["fpay"].append(np.mean([x["paid"] for x in fr]) / 26)
    ndays = len(days)
    base = {k: float(np.nanmean([x[k] for x in agg])) for k in ("n", "win", "pf", "net", "dd", "per_day")}
    base["net_p10"], base["net_p90"] = float(np.percentile([x["net"] for x in agg], 10)), float(np.percentile([x["net"] for x in agg], 90))
    base["ndays"] = ndays; base["per2w"] = base["net"] / (ndays / 10)
    for f in plans:
        a = acct[f]
        res.append(dict(plan=f, size=size, acc=acc, **base, eval_pass=float(np.mean(a["ep"])), eval_bust=float(np.mean(a["eb"])), eval_open=float(np.mean(a["eo"])),
                        med_days=float(np.median(a["emed"])) if a["emed"] else None, funded_bust=float(np.mean(a["fb"])), funded_any_pay=float(np.mean(a["fany"])),
                        funded_per2w=float(np.mean(a["fpay"]))))
    return res


if __name__ == "__main__":
    pk = HERE + "/cands.pkl"
    if os.path.exists(pk): _M = pickle.load(open(pk, "rb"))
    else:
        _M = build_cands({"MNQ": sys.argv[1], "MGC": sys.argv[2]}); pickle.dump(_M, open(pk, "wb"))
    ns = int(sys.argv[3]) if len(sys.argv) > 3 else 200; na = int(sys.argv[4]) if len(sys.argv) > 4 else 40; npth = int(sys.argv[5]) if len(sys.argv) > 5 else 25
    jobs = [(sz, acc, ns, na, npth) for sz in SIZE for acc in ACCS]
    with Pool(4) as p: out = p.map(job, jobs)
    flat = [r for x in out for r in x]
    json.dump(dict(rows=flat, ns=ns, na=na, npth=npth), open(HERE + "/results.json", "w"), indent=1); print("done", len(flat))
