"""Session 17: "NOISE + AI Duo split 50/50" vs NOISE alone. Research only (no app code touched). Pure numpy/python, floats.
Parts: NOISE trade stream (same bar loop + costs as session 15/17 `sharpen.gen`, profit lock 100 -> +10), AI Duo candidate trades (same model as
session 16 `ai_duo_window.py`, window 09:36-11:30, 2.0R target, RTH VWAP), simulated AI calls (accuracy + 27% NEUTRAL skips), the one-account day engine
(strategy budgets, hedge lock, size tables + brake, Lucid Pro MLL/DLL), eval and continuous runs."""
import os, sys, pickle
import numpy as np, pandas as pd
sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))

INST = {"MNQ": dict(pv=2.0, tick=0.25, fee=1.0), "MGC": dict(pv=10.0, tick=0.1, fee=1.5)}
SPLIT = "2023-12-31"                      # IS <= 2023-12-31 (pick), HO >= 2024-01-01 (judge)
NB = 390
RR = 2.0                                  # Duo target (config rr_target)
MARGIN = 40.0                             # internal.dll_safety_margin
MINSTOP_USD = 10.0                        # session-16 study assumption (structure stop widened to >= $10 of price risk)

# ------------------------------------------------------------------------------------------------ NOISE stream
def noise_gen(days, sym="MNQ", stop_usd=250.0, look=14, step=60, maxtr=3, first_check=29, lock=(100.0, 10.0)):
    """copy of sharpen.gen defaults (session 15 N1 + D75-P1 lock) with START = first usable date. rows: d, ek, xk, pnl, mae, risk, side (per 1 micro)"""
    I = INST[sym]; PV, TICK, FEE = I["pv"], I["tick"], I["fee"]
    Dd = days; nb = NB
    hard = (stop_usd - FEE - 2 * TICK * PV) / PV
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in Dd])
    checks = set(range(first_check, 360, step)); out = []
    for i in range(look, len(Dd)):
        d, a = Dd[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = Dd[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=0.0, ek=0, mae=0.0, hs=0.0, locked=False)
        ntr = pending = 0
        def close_trade(px, xk):
            nonlocal ntr
            if st["locked"] and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)) and xk > st["ek"]: ntr = maxtr
            p = (px - st["entry"]) * st["pos"] * PV - FEE
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, mae=st["mae"] + TICK * PV, risk=hard * PV + FEE + 2 * TICK * PV, side=st["pos"]))
            st["pos"] = 0
        for k in range(nb):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                st.update(entry=o[k] + pending * TICK, pos=pending, ek=k, mae=0.0, locked=False); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hard
            pos = st["pos"]
            if pos:
                e = st["entry"]
                st["mae"] = max(st["mae"], ((e - l[k]) if pos > 0 else (h[k] - e)) * PV)
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * TICK, k)
                if st["pos"] and lock and not st["locked"] and ((pos > 0 and h[k] >= e + lock[0]) or (pos < 0 and l[k] <= e - lock[0])):
                    st["locked"] = True; st["hs"] = max(st["hs"], e + lock[1]) if pos > 0 else min(st["hs"], e - lock[1])
            if st["pos"] and k == nb - 1: close_trade(c[k] - st["pos"] * TICK, k)
            if k in checks:
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < nb and not np.isnan(o[nk]) else c[k]) - pos * TICK, min(nk, nb - 1))
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side: pending, ntr = side, ntr + 1
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ AI Duo candidates (session 16 model, RTH arrays: k = minutes from 09:30)
def bars5(a):
    r = {}
    for k in ("open", "high", "low", "close"):
        x = a[k].reshape(78, 5); ok = ~np.isnan(x)
        if k == "open": r[k] = np.array([row[m][0] if m.any() else np.nan for row, m in zip(x, ok)])
        elif k == "close": r[k] = np.array([row[m][-1] if m.any() else np.nan for row, m in zip(x, ok)])
        elif k == "high": r[k] = np.array([row[m].max() if m.any() else np.nan for row, m in zip(x, ok)])
        else: r[k] = np.array([row[m].min() if m.any() else np.nan for row, m in zip(x, ok)])
    return r


def duo_trade(a, b5, s, K, ws=6, we=120):
    """first 5-minute bar that pulls back to VWAP and closes in direction s (window 09:36-11:30, bar 09:30-09:35 excluded); entry next 1-min open + 1 tick.
    returns (pnl, ek, xk, mae, risk) per 1 micro or None"""
    vw = a["vwap"]
    for bi in range(ws // 5 - 1, we // 5 - 1):
        b = bi * 5
        if b + 5 < ws: continue
        if b < 5: continue                        # 09:30-09:35 excluded
        if b + 5 > we - 5: break
        o, h, l, c = b5["open"][bi], b5["high"][bi], b5["low"][bi], b5["close"][bi]
        if np.isnan(c) or np.isnan(h): continue
        v = vw[b + 4]
        trig = (l <= v < c and c > o) if s > 0 else (h >= v > c and c < o)
        if not trig: continue
        pb = [bi, bi - 1] if bi > 0 else [bi]
        ext = np.nanmin(b5["low"][pb]) if s > 0 else np.nanmax(b5["high"][pb])
        me = b + 5
        if np.isnan(a["open"][me]): continue
        e = a["open"][me] + s * K["tick"]
        stop = ext - s * K["tick"]
        sp = abs(e - stop)
        if sp > K["cap"]: continue                 # STOP_TOO_WIDE skip (session-16 study rule)
        if sp < K["minstop"]: sp = K["minstop"]; stop = e - s * sp
        tgt = e + s * RR * sp
        pnl = None; mae = 0.0
        for j in range(me, we):
            if np.isnan(a["close"][j]): continue
            hj, lj, oj = a["high"][j], a["low"][j], a["open"][j]
            mae = max(mae, ((e - lj) if s > 0 else (hj - e)) * K["pv"])
            if (s > 0 and lj <= stop) or (s < 0 and hj >= stop):
                px = (min(stop, oj) if s > 0 else max(stop, oj)) - s * K["tick"]
                pnl = (px - e) * s * K["pv"] - K["fee"]; xj = j; break
            if (s > 0 and hj >= tgt + K["tick"]) or (s < 0 and lj <= tgt - K["tick"]):
                pnl = (tgt - e) * s * K["pv"] - K["fee"]; xj = j; break
        if pnl is None:
            j = we - 1
            while j > me and np.isnan(a["close"][j]): j -= 1
            pnl = (a["close"][j] - s * K["tick"] - e) * s * K["pv"] - K["fee"]; xj = j
        risk = sp * K["pv"] + K["fee"] + 2 * K["tick"] * K["pv"]
        return (pnl, me, xj, mae + K["tick"] * K["pv"], risk)
    return None


def duo_candidates(days, sym):
    I = INST[sym]; K = dict(I); K["cap"] = (250.0 - I["fee"] - 2 * I["tick"] * I["pv"]) / I["pv"]; K["minstop"] = MINSTOP_USD / I["pv"]
    n = len(days); cand = np.full((n, 2, 5), np.nan); truth = np.zeros(n)
    for i, (d, a) in enumerate(days):
        c = a["close"][~np.isnan(a["close"])]; truth[i] = np.sign(c[-1] - a["open"][0]) or 1.0
        b5 = bars5(a)
        for si, s in enumerate((1, -1)):
            t = duo_trade(a, b5, s, K)
            if t: cand[i, si] = t
    return dict(dates=[d for d, _ in days], cand=cand, truth=truth)


# ------------------------------------------------------------------------------------------------ plans / sizing
from types import SimpleNamespace as NS
import yaml
PLANS = {"25K": "lucid_pro_25k", "50K": "lucid_pro_50k", "100K": "lucid_pro_100k", "150K": "lucid_pro_150k"}


def plan_rules(name):
    """Lucid Pro plan numbers read straight from config/rules/<plan>.yaml (no invented numbers)."""
    y = yaml.safe_load(open(f"{ROOT}/config/rules/{PLANS[name]}.yaml"))
    f, e = y["funded"], y["eval"]
    fl = lambda x: None if x is None else float(x)
    return NS(start=float(y["account_size"]),
              budget=float(f["daily_loss_limit"]),      # ASSUMPTION: internal daily loss budget = the plan's funded DLL, in every stage
              e=NS(target=fl(e["profit_target"]), mll=fl(e["max_loss_limit"]), lt=fl(e["lock_trigger"]), ll=fl(e["lock_level"]), dll=fl(e["daily_loss_limit"]),
                   cons=fl(e["consistency_max_day_pct"]), mpd=int(e["min_profitable_days"])),
              f=NS(mll=fl(f["max_loss_limit"]), dll=fl(f["daily_loss_limit"])))


# full size per account (contracts, brake_below fraction of MLL, brake contracts)
SIZES = {
    "APP":   {"25K": (1, None, 1), "50K": (2, 0.5, 1), "100K": (2, 0.3, 1), "150K": (3, 0.5, 2)},   # config/rules lucid_pro_*.yaml strategy.size_table (default, no preset)
    "S15":   {"25K": (1, None, 1), "50K": (1, None, 1), "100K": (2, 0.7, 1), "150K": (3, 0.5, 1)},   # session-15 recommended (preset C style)
}


def make_qfun(sizes, acct, mll, split):
    q, br, bq = sizes[acct]
    def qf(cush):
        qq = bq if (br is not None and cush < br * mll) else q
        return max(1, qq // 2) if split else qq
    return qf


# ------------------------------------------------------------------------------------------------ account engine
def day_sim(trades, bal, floor, qf, dll, budgets, mode, collect=False):
    """trades: list of (ek, strat, mkt, side, pnl, mae, risk, xk) sorted by (ek, strat) per 1 micro.
    strat 0 = NOISE, 1 = AI Duo; mkt 0 = MNQ, 1 = MGC. budgets = (B_noise, B_duo) internal daily loss budgets in $ (None = no budget for that strat).
    mode 'hedge' = opposite sides may not be open at the same time in the same equity-index group (MNQ NOISE vs MNQ Duo); 'strict1' = at most 1 open position.
    returns (bal, bust, traded, accepted)  accepted = [(strat, mkt, q, p)] (p = $ after size and DLL clip)"""
    if not trades: return bal, False, False, []
    acc = []; dayp = 0.0; traded = False
    for ek, strat, mkt, side, pnl, mae, risk, xk in trades:
        r = [0.0, 0.0]; openw = 0.0; conflict = False
        for axk, astrat, amkt, aside, aq, ap, aw in acc:
            if axk < ek: r[astrat] += ap
            else:
                openw += aw
                if astrat != strat or amkt != mkt:
                    if mode == "strict1": conflict = True
                    elif mode == "hedge" and aside != side and amkt == 0 and mkt == 0: conflict = True      # both MNQ = same EQUITY_INDEX group, opposite directions
        if conflict: continue
        rtot = r[0] + r[1]
        if dll is not None and rtot <= -dll: break
        q = qf(bal + rtot - floor)
        B = budgets[strat]
        if B is not None:
            room = B - max(0.0, -r[strat]) - MARGIN
            q = min(q, int(room // risk)) if room > 0 else 0
        if q < 1: continue
        worst = -max(mae, -pnl) if mae > 0 else min(pnl, 0.0)
        if bal + rtot + q * worst + openw <= floor: return floor, True, True, acc
        p = pnl * q
        if dll is not None and dayp + p <= -dll: p = -dll - dayp
        acc.append((xk, strat, mkt, side, q, p, q * worst)); dayp += p; traded = True
    bal += dayp
    out = [(a[1], a[2], a[4], a[5]) for a in acc] if collect else None
    return bal, bal <= floor, traded, out


def eval_run(tab, R, qf, budgets, mode, horizon=250):
    e = R.e; bal = peak = R.start; floor = R.start - e.mll; pos = []
    for n, trades in enumerate(tab[:horizon]):
        b0 = bal
        bal, bust, traded, _ = day_sim(trades, bal, floor, qf, e.dll, budgets, mode)
        if bust: return "BUST", n + 1
        if traded: pos.append(bal - b0)
        peak = max(peak, bal)
        floor = e.ll if peak >= e.lt else max(floor, peak - e.mll)
        prof = bal - R.start
        if prof >= e.target and sum(1 for x in pos if x > 0) >= e.mpd and (e.cons is None or max(pos, default=0) <= e.cons / 100 * prof):
            return "PASS", n + 1
    return "OPEN", min(horizon, len(tab))


def era_starts(dates, length, step):
    i_split = next(i for i, d in enumerate(dates) if d > SPLIT)
    allr = list(range(0, max(1, len(dates) - length), step))
    return dict(IS=[i for i in allr if i + length <= i_split], HO=[i for i in allr if i >= i_split])


def eval_stats(tab, dates, R, qf, budgets, mode, era, horizon=250, step=3):
    idx = era_starts(dates, horizon, step)[era]
    res = [eval_run(tab[i:i + horizon], R, qf, budgets, mode, horizon) for i in idx]
    n = len(res); ps = [s for o, s in res if o == "PASS"]
    return dict(n=n, pas=100 * sum(o == "PASS" for o, _ in res) / n, bust=100 * sum(o == "BUST" for o, _ in res) / n,
                open=100 * sum(o == "OPEN" for o, _ in res) / n, med_days=float(np.median(ps)) if ps else float("nan"))


def stream_stats(tab, dates, R, qf, budgets, mode, era):
    """continuous account over the era (reset to the start balance after a bust; bust counted). Trade-level stats of the accepted trades."""
    lo, hi = {"IS": (0, next(i for i, d in enumerate(dates) if d > SPLIT)), "HO": (next(i for i, d in enumerate(dates) if d > SPLIT), len(dates))}[era]
    bal = peak = R.start; floor = R.start - R.f.mll; pnls = []; busts = 0; strat_n = [0, 0]; strat_p = [0.0, 0.0]
    # funded-style limits for the continuous run? use the eval limits (same MLL/lock); DLL = eval DLL
    e = R.e; floor = R.start - e.mll
    for i in range(lo, hi):
        bal, bust, traded, acc = day_sim(tab[i], bal, floor, qf, e.dll, budgets, mode, collect=True)
        if bust:
            busts += 1; bal = peak = R.start; floor = R.start - e.mll; continue
        for s, m, q, p in acc or []: pnls.append(p); strat_n[s] += 1; strat_p[s] += p
        peak = max(peak, bal); floor = e.ll if peak >= e.lt else max(floor, peak - e.mll)
    p = np.array(pnls)
    if not len(p): return dict(n=0, win=float("nan"), net=0.0, dd=0.0, busts=busts, n_noise=0, n_duo=0, net_noise=0.0, net_duo=0.0)
    cum = np.concatenate([[0], p.cumsum()])
    return dict(n=int(len(p)), win=float(100 * (p > 0).mean()), net=float(p.sum()), dd=float(np.max(np.maximum.accumulate(cum) - cum)), busts=busts,
                n_noise=strat_n[0], n_duo=strat_n[1], net_noise=strat_p[0], net_duo=strat_p[1])


# ------------------------------------------------------------------------------------------------ tabs
def bdays(first, last):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(first, last)]


def noise_tab(nt, dates):
    ix = {d: i for i, d in enumerate(dates)}; tab = [[] for _ in dates]
    for r in nt.itertuples():
        if r.d in ix: tab[ix[r.d]].append((int(r.ek), 0, 0, int(r.side), float(r.pnl), float(r.mae), float(r.risk), int(r.xk)))
    return tab


def ai_calls(duo, dates, seed, acc, neutral=0.27, markets=("MNQ", "MGC")):
    """per-day Duo trades for one seed/accuracy. Common random numbers: the same uniforms for every accuracy, so a higher accuracy flips a subset of calls."""
    ix = {d: i for i, d in enumerate(dates)}; out = {}
    for mi, m in enumerate(("MNQ", "MGC")):
        if m not in markets: continue
        D = duo[m]; n = len(D["dates"])
        rng = np.random.default_rng(seed * 1009 + mi * 7919 + 17)
        u = rng.random(n); un = rng.random(n)
        call = np.where(u < acc, D["truth"], -D["truth"])
        sel = np.where((call > 0)[:, None], D["cand"][:, 0], D["cand"][:, 1])     # (n,5) pnl, ek, xk, mae, risk
        ok = ~np.isnan(sel[:, 0]) & (un >= neutral)
        for i in np.flatnonzero(ok):
            j = ix.get(D["dates"][i])
            if j is None: continue
            p, ek, xk, mae, risk = sel[i]
            out.setdefault(j, []).append((int(ek), 1, mi, int(call[i]), float(p), float(mae), float(risk), int(xk)))
    return out


def combine(ntab, calls):
    tab = [list(x) for x in ntab]
    for j, L in calls.items():
        tab[j].extend(L); tab[j].sort(key=lambda t: (t[0], t[1]))
    return tab
