"""yf30 combo: NOISE + CANDACE + LATE-DAY momentum on MNQ (30 Yahoo days). RESEARCH ONLY.
Run: PYTHONPATH=backend:docs/results/yf30/scripts <yfvenv>/bin/python docs/results/yf30/combo/combo.py"""
import json, random, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from lib import *
import noise_candace as NC

SYM = "MNQ"; OUT = Path(__file__).resolve().parent
pu, cu = pt_usd(SYM), cost_usd(SYM)

def late_trades(df):
    days = {}
    for i, ts in enumerate(df.index): days.setdefault(ts.date(), []).append(i)
    rows, out, rngs, prev = [], [], [], None
    for d in sorted(days):
        rth = [i for i in days[d] if time(9, 30) <= df.index[i].time() < time(16, 0)]
        if len(rth) < 180: continue
        g = lambda t: next((i for i in rth if df.index[i].time() == t), None)
        i_ref, i_ent = g(time(13, 28)), g(time(15, 0))
        if i_ref is None or i_ent is None: continue
        o = df.o.values[rth[0]]; ref = df.c.values[i_ref]
        thr = np.mean(rngs[-14:]) * 0.1 if len(rngs) >= 5 else None
        rngs.append(df.h.values[rth].max() - df.l.values[rth].min())
        if thr is not None and abs(ref - o) < thr: continue
        s = int(np.sign(ref / o - 1))
        if s == 0: continue
        e = float(df.o.values[i_ent]); i_end = rth[-1]
        pts, ex = sim_path(df, i_ent, i_end, e, s, 60)
        out.append(dict(day=str(d), sign=s, i0=i_ent, i1=i_end, ex=ex, entry=e, stop_pts=60, why="LATE", usd=pts * pu - cu))
    return out

def merge(legs, df, separate_late):
    """legs: dict name->trades. Sequential by entry bar (tie: NOISE, CANDACE, LATE). Returns accepted, skips."""
    order = {"NOISE": 0, "CANDACE": 1, "LATE": 2}
    allt = sorted(((t["i0"], order[n], n, t) for n, ts in legs.items() for t in ts), key=lambda x: x[:2])
    acc, skips = [], {}
    def skip(n, r): skips.setdefault(n, {}); skips[n][r] = skips[n].get(r, 0) + 1
    for i0, _, n, t in allt:
        end = lambda a: a.get("ex", a["i1"])
        openp = [a for a in acc if a["i0"] <= i0 <= end(a)]
        # opposite-side lock across ALL accounts (hedge lock)
        if any(a["sign"] != t["sign"] for a in openp): skip(n, "HEDGE_LOCK"); continue
        if separate_late and n == "LATE": same_acct = [a for a in openp if a["leg"] != "LATE"]; same_acct = []  # own account: free unless LATE open
        group = [a for a in openp if (not separate_late) or ((a["leg"] == "LATE") == (n == "LATE"))]
        if group: skip(n, "POSITION_OPEN"); continue
        acc.append(dict(t, leg=n))
    return acc, skips

def maxdd(trs):
    eq = pk = dd = 0.0
    for t in sorted(trs, key=lambda x: (x["i1"])): eq += t["usd"]; pk = max(pk, eq); dd = max(dd, pk - eq)
    return round(dd, 1)

def daily(trs, days):
    d = {x: 0.0 for x in days}
    for t in trs: d[t["day"]] += t["usd"]
    return d

def summ(trs, df):
    s = stats([t["usd"] for t in trs]); s["maxdd"] = maxdd(trs)
    s["shorts"] = sum(1 for t in trs if t["sign"] < 0)
    return s

def combo_p(trs, df, draws=2000, seed=11):
    rnd = random.Random(seed); act = sum(t["usd"] for t in trs); nets = []
    for _ in range(draws):
        tot = 0.0
        for t in trs:
            sg = rnd.choice((-1, 1)); pts, _ = sim_path(df, t["i0"], t["i1"], t["entry"], sg, t["stop_pts"], t.get("tp_pts")); tot += pts * pu - cu
        nets.append(tot)
    nets.sort()
    return dict(actual=round(act, 1), rand_mean=round(sum(nets) / draws, 1), rand_p95=round(nets[int(.95 * draws)], 1), p_net=round(sum(1 for x in nets if x >= act) / draws, 3))

def eval_sim(acc, days, plan):
    """Lucid Pro eval, EOD drawdown. sizes: dict leg->(contracts, brake_cushion, reduced). Scales each trade's $ by contracts."""
    start, target, dd, dll = plan["start"], plan["target"], plan["dd"], plan["dll"]
    bal = start; peak = start; mll = start - dd; locked = False; dayp = []
    log = []
    for d in days:
        day_trs = sorted([t for t in acc if t["day"] == d], key=lambda t: t["i0"]); dpnl = 0.0; stopday = False
        for t in day_trs:
            cush = bal + dpnl - mll
            n, brk, red = plan["size"][t["leg"]]
            c = red if cush < brk else n
            if stopday or dpnl <= -0.9 * dll or dpnl >= plan["day_lock"] * target: continue
            if cush < 100: continue
            dpnl += t["usd"] * c
            if bal + dpnl - mll <= 0: log.append((d, "MLL_BREACH")); return dict(result="BUST", day=d, bal=round(bal + dpnl), days=len(dayp), trades_log=log)
        bal += dpnl; dayp.append(dpnl)
        if not locked and bal > peak: peak = bal; mll = peak - dd
        if bal - start >= dd + 100 and not locked: locked = True; mll = start + 100
        prof = bal - start; best = max(dayp)
        pdays = sum(1 for x in dayp if x > 0)
        if prof >= target and pdays >= 3 and best <= 0.4 * prof:
            return dict(result="PASS", day=d, bal=round(bal), days=len(dayp), profit=round(prof))
    prof = bal - start
    return dict(result="NOT_REACHED", bal=round(bal), profit=round(prof), days=len(dayp), best_day=round(max(dayp), 1),
                profitable_days=sum(1 for x in dayp if x > 0), pct_of_target=round(100 * prof / target, 1),
                best_day_pct_of_profit=round(100 * max(dayp) / prof, 1) if prof > 0 else None, peak_balance=round(max(start, start + max(np.cumsum(dayp)))))

if __name__ == "__main__":
    nt, df = NC.noise_run(SYM, 250, (100, 10), True, 10)
    ct, _ = NC.candace_run(SYM, dict(ny_max_stop_pts=40, ny_max_hold_minutes=30, ny_window="08:20-11:00", gap_level_tol_pts=5))
    lt = late_trades(df)
    legs = {"NOISE": nt, "CANDACE": ct, "LATE": lt}
    days = sorted({str(d.date()) if hasattr(d, "date") else str(d) for d in df.index.date})
    days = sorted({str(x) for x in df.index.date})[:-0 or None]
    sess = sorted(str(d) for d, ix in NC.sessions(df).items() if len(ix) >= 150)
    R = {"standalone": {n: summ(ts, df) for n, ts in legs.items()}}
    for tag, sep in (("a_one_account", False), ("b_late_separate_account", True)):
        acc, sk = merge(legs, df, sep)
        per = {n: summ([t for t in acc if t["leg"] == n], df) for n in legs}
        dl = {n: daily([t for t in acc if t["leg"] == n], sess) for n in legs}
        cor = {}
        for a, b in (("NOISE", "CANDACE"), ("NOISE", "LATE"), ("CANDACE", "LATE")):
            x, y = np.array(list(dl[a].values())), np.array(list(dl[b].values()))
            cor[f"{a}-{b}"] = round(float(np.corrcoef(x, y)[0, 1]), 2) if x.std() > 0 and y.std() > 0 else None
        R[tag] = dict(combined=summ(acc, df), per_leg=per, skips=sk, daily_corr=cor, p_random=combo_p(acc, df), n_sessions=len(sess))
        # Lucid eval sims
        plans = {
          "25K_1micro": dict(start=25000, target=1250, dd=1000, dll=600, day_lock=0.38, size={"NOISE": (1, 0, 1), "CANDACE": (1, 0, 1), "LATE": (1, 0, 1)}),
          "25K_D157_N1_C2": dict(start=25000, target=1250, dd=1000, dll=600, day_lock=0.38, size={"NOISE": (1, 0, 1), "CANDACE": (2, 333, 1), "LATE": (1, 0, 1)}),
          "50K_1micro": dict(start=50000, target=3000, dd=2000, dll=1200, day_lock=0.38, size={"NOISE": (1, 0, 1), "CANDACE": (1, 0, 1), "LATE": (1, 0, 1)}),
          "50K_D163_N2_C4": dict(start=50000, target=3000, dd=2000, dll=1200, day_lock=0.4, size={"NOISE": (2, 667, 1), "CANDACE": (4, 1000, 3), "LATE": (1, 0, 1)}),
        }
        R[tag]["eval"] = {k: eval_sim(acc, sess, p) for k, p in plans.items()}
        R[tag]["trades"] = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in t.items() if k in ("day", "leg", "sign", "why", "usd")} for t in sorted(acc, key=lambda t: t["i0"])]
    json.dump(R, open(OUT / "results.json", "w"), indent=1, default=str)
    for k in ("standalone",): print(k, json.dumps(R[k]))
    for tag in ("a_one_account", "b_late_separate_account"):
        r = R[tag]; print(tag, json.dumps({x: r[x] for x in r if x != "trades"}, default=str))
