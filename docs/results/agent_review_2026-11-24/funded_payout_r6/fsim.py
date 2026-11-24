"""Funded-account life simulator (research only). Reuses refine_round3/harness.py + pass_faster_r4/h4.py (the real fast-pass sim, streams, pre-trade checks)
and replaces the EVAL pass logic by the FUNDED life: EOD MLL + lock, DLL (+LucidScale), kill $50, day stop, payout cycle
(3 profitable days, cycle profit >= min, payout consistency largest day / cycle profit <= cap, amount = min(balance - buffer, cap 1st/next)), max 5 payouts,
news hard-breach filter (flat 1 min before / no entry until 1 min after). Pick = starts 2021-10..2023-12, judge = 2024-01..2026-10."""
import sys, math, pickle
sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/pass_faster_r4")
sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3")
import numpy as np, pandas as pd
import h4, harness as H

HERE = "/home/user/paytience/docs/results/agent_review_2026-11-24/"
EV = pd.read_csv(HERE + "news_and_ideas_r5/dates_us_releases.csv")
EV = EV[EV.date != "event"]
EV["off"] = EV.time_et.map(lambda t: int(t.split(":")[0]) * 60 + int(t.split(":")[1]) - 570)
BYDAY = {d: sorted(set(g.off)) for d, g in EV.groupby("date")}
PAY = {  # min_cycle_profit, max_first, max_next (yaml funded.payout)
    25: (250., 1000., 1500.), 50: (500., 2000., 2500.), 100: (750., 2500., 3000.), 150: (1000., 3000., 3500.)}
KN, KC = 0, 2
_pk = pickle.load(open("/home/user/days.pkl", "rb"))[0]
CLOSE = {d: a["close"] for d, a in _pk}; OPENA = {d: a["open"] for d, a in _pk}
del _pk


def build_days(S, c, news):
    """like S.build_days (NOISE + CANDACE only) but with the news hard-breach filter. returns (days, stats)"""
    by = {}; st = dict(total=0, blocked=0, cut=0, usd_total=0.0)
    n = S.noise_df(c["stop"], c["lock"], c["maxtr"], c["mon"])
    for r in n.itertuples():
        ek, xk, p, e0 = float(r.ek), float(r.xk), float(r.pnl), float(r.entry) + r.side * 0.25
        st["total"] += 1; ev = BYDAY.get(r.d, []) if news else []
        if any(e - 1 <= ek <= e + 1 for e in ev): st["blocked"] += 1; continue
        cut = [e - 1 for e in ev if e - 1 > ek and xk >= e - 1]
        if cut:
            Tf = min(cut); px = CLOSE[r.d][int(Tf) - 1]
            p = (px - r.side * 0.25 - e0) * r.side * 2 - 1 - S.NADD; xk = Tf - 0.5; st["cut"] += 1
        by.setdefault(r.d, []).append((ek, xk + 0.5, KN, p, float(r.mae), float(r.risk), float(r.entry)))
    for r in S.candace_df(c["cwin"]).itertuples():
        st["total"] += 1; ev = BYDAY.get(r.day, []) if news else []
        ek, xk, p1 = float(r.idx), float(r.exit_idx), float(r.p1)
        if any(e - 1 <= ek <= e + 1 for e in ev): st["blocked"] += 1; continue
        cut = [e - 1 for e in ev if e - 1 > ek and xk >= e - 1]
        if cut:
            Tf = min(cut); sg = 1 if r.dir == "LONG" else -1; p1 = (CLOSE[r.day][int(Tf) - 1] - r.entry) * sg; xk = Tf; st["cut"] += 1
        by.setdefault(r.day, []).append((ek, xk, KC, p1, float(r.stop_pts), 0.0, 0.0))
    for d in by: by[d].sort(key=lambda x: (x[0], x[2]))
    return [by.get(d, ()) for d in S.DATES], st


def life(S, k, days, di0, c, cap, ds_frac, horizon=250, eval_mode=False, cad=0, od=False, pause=True):
    """one funded account from day index di0. returns dict(status, sessions, pays=[(session, gross)], dll, dstop, maxdd, blocked_days, maxday, big6k, lost)
    Payout timing (r9, 2026-11-24): od=False: a payout is requested at the END of a session, only on sessions divisible by `cad` (cad 0 = every session).
    od=True = Lucid ON-DEMAND (CONFIRMED, help center user screenshot 2026-11-24; needs DLL ON, which this sim always has): the payout is requested
    INTRADAY as soon as the session profit makes the account eligible (min request $500, cycle profit >= plan minimum, 3 profitable days incl. today as in
    the weekly model, consistency incl. today's partial day <= cap, amount = min(balance - buffer, plan cap, SESSION profit)). After the request the account
    trades no more that day (pause=True, the real rule); remaining trades are counted in `lost`. pause=False = research counterfactual (NOT allowed by Lucid):
    keep trading after the request (one request per day). A hedging violation (not modelled: the app never hedges) would block it."""
    SIZE, TARGET, MLL, LT, LL, DLL0 = S.SIZE, S.TARGET, S.MLL, S.LOCK_TRIG, S.LOCK_LVL, S.DLL0
    CAPT, KILL, MG, SH, PV, FEE, TV, SLIP, MINPCT = S.CAP_TRADE, S.KILL, S.MARGIN, S.SHRINK, S.PV, S.FEE, S.TV, S.SLIP, S.MINPCT
    mincyc, mfirst, mnext = PAY[k]; buffer = LT; COST1 = S.COST1
    dstop = ds_frac * TARGET
    N, nc, dlk = c["N"], c["nc"], c["dlock"]
    gper, gmax = c["grow"] if c["grow"] else (None, None)
    bal = SIZE; floor = bal - MLL; peak = bal; locked = False; peak_e = bal
    cyc = []; pays = []; dllh = dsh = 0; maxdd = 0.0; blocked = 0; maxday = 0.0; big6k = 0; pdays = 0; best = 0.0
    status = "OPEN"; s = 0; eq_hi = SIZE; lost = 0; od_pause_days = 0; base_today = 0.0
    for di in range(di0, len(days)):
        s += 1
        if s > horizon: break
        tl = days[di]; today = 0.0; stop = False; paid_today = 0.0; od_done = False; peak_day = 0.0; free = -1.0; last = -1; lockday = False; dead_ = False
        dll = DLL0
        if locked: dll = 0.6 * (peak_e - SIZE)
        rem0 = TARGET - (bal - SIZE)
        for ti, (m_in, m_out, kind, a, b, cc, d) in enumerate(tl):
            if stop: break
            if m_in <= free and not (kind == KN and last == KN): continue
            if kind == KN:
                if lockday: continue
                if dlk and today > 0 and rem0 > 0 and today >= dlk * rem0: lockday = True; continue
                cush = bal - floor; q = N
                if gper:
                    ex = int(cush // gper) - 1
                    if ex > 0: q = min(gmax, N + ex)
                for fb_, fn_ in c["nbands"]:
                    if cush / MLL < fb_: q = min(q, fn_)
                pnl, mae, risk, entry = a, b, cc, d
                q = min(q, int(CAPT // risk))
                if cush <= KILL: status = "STUCK"; break
                room0 = cush - KILL
                if dll: room0 = min(room0, dll + today)
                pp = None; eff = mae
                while q > 0:
                    S_ = risk
                    if q * risk > SH * room0:
                        pt = math.floor(((SH * room0 / q) - FEE) / TV - SLIP)
                        if pt * 0.25 < MINPCT * entry or pt <= 0: q = -1; break
                        S_ = pt * TV + FEE + TV
                    if q * S_ + MG <= room0:
                        pp = -S_ if (S_ < risk and mae >= S_) else pnl
                        eff = min(mae, S_) if S_ < risk else mae
                        break
                    q -= 1
                if q <= 0:
                    if SH * (cush - KILL) < S.GMIN: status = "STUCK"; break
                    continue
                pq = q * pp; dead = False
                if q * eff >= cush - KILL: pq = -(cush - KILL); dead = True
            else:
                per = b * 2.0 + 2.0; left = None
                if dll:
                    left = dll - (max(0.0, peak_day, today) - today)
                    if left <= 0: stop = True; break
                lim = bal - floor - KILL
                if left is not None and left < lim: lim = left
                q = nc
                if c["cgrow"]:
                    ex = int((bal - floor) // c["cgrow"][0]) - 1
                    if ex > 0: q = min(c["cgrow"][1], nc + ex)
                for fb_, fn_ in c["cbands"]:
                    if (bal - floor) / MLL < fb_: q = min(q, fn_)
                while q >= 1 and q * per + MG > lim: q -= 1
                if q < 1: continue
                pq = q * (a * PV - COST1); dead = False
            free = m_out; last = kind
            if dll and today + pq <= -dll: pq = -dll - today; stop = True; dllh += 1
            if today + pq > dstop: pq = dstop - today; stop = True; dsh += 1
            today += pq; bal += pq
            if today > peak_day: peak_day = today
            if dead or bal <= floor + KILL: dead_ = True; break
            if od and not od_done and today > 0 and len(pays) < 5:
                cp = sum(cyc) + today
                if cp >= mincyc and (sum(1 for x in cyc if x > 0) + 1) >= 3 and max(max(cyc, default=0.0), today) <= cap * cp:
                    amt = min(bal - buffer, mfirst if not pays else mnext, today if od != "bal" else 1e18)  # od="bal": SENSITIVITY only (amount not limited to session profit, an unconfirmed reading)
                    if amt >= 500:
                        assert bal - amt >= buffer - 1e-9 and bal - amt > floor
                        bal -= amt; paid_today += amt; pays.append((s, amt)); od_done = True; cyc = []; base_today = today
                        if pause: lost += len(tl) - ti - 1; od_pause_days += 1; break
        if status == "STUCK": break
        if dead_: status = "BUST"; break
        cyc.append(today - base_today if (od and od_done) else today)
        if today > 0: pdays += 1; best = max(best, today)
        maxday = max(maxday, today)
        if today >= 6000: big6k += 1
        eod_bal = bal + paid_today  # an intraday payout does not lower the EOD high that trails the MLL (conservative: same floor as the weekly model)
        if eod_bal > peak_e: peak_e = eod_bal
        if eod_bal > peak and not locked:
            peak = eod_bal
            if peak >= LT: locked = True; floor = LL
            else: floor = peak - MLL
        eq_hi = max(eq_hi, bal + sum(g for _, g in pays)); maxdd = max(maxdd, eq_hi - (bal + sum(g for _, g in pays)))
        if eval_mode:
            prof = bal - SIZE
            if prof >= TARGET and pdays >= 1 and best <= 0.40 * prof: status = "PASS"; break
            continue
        if od: continue
        cp = sum(cyc)
        if (cad == 0 or s % cad == 0) and cp > 0 and cp >= mincyc and sum(1 for x in cyc if x > 0) >= 3 and bal - buffer >= 500:
            amt = min(bal - buffer, mfirst if not pays else mnext)
            if max(cyc) > cap * cp: blocked += 1                          # eligible except consistency: waits
            elif amt >= 500:
                assert max(cyc) <= cap * cp + 1e-9 and bal - amt >= buffer - 1e-9 and bal - amt > floor
                bal -= amt; pays.append((s, amt)); cyc = []
                if len(pays) >= 5: status = "MAXPAY"; break
    return dict(status=status, sessions=s, pays=pays, dll=dllh, dstop=dsh, maxdd=maxdd, blocked=blocked, maxday=maxday, big6k=big6k, lost=lost, od_pause_days=od_pause_days)


def run(k, c, cap=0.35, ds_frac=0.38, news=True, cost=False, horizon=250):
    S = h4.sim(k, ds=0.38, cost=cost); c = S.mk(**c)
    days, st = build_days(S, c, news)
    res = []
    for i in range(S.L): res.append(life(S, k, days, i, c, cap, ds_frac, horizon))
    return S, res, st


def summarize(S, res, hz_list=(60, 120)):
    out = {}
    dates = S.DATES; L = len(dates)
    for w, (lo, hi) in dict(ALL=(0, L), PICK=(0, S.P1 + 1), JUDGE=(S.J0, L)).items():
        for H_ in hz_list:
            ix = [i for i in range(lo, hi) if i + H_ <= L]            # starts with H_ sessions of data ahead
            if not ix: continue
            pn = []; npay = []; bust = []; first = []; fh = 0
            for i in ix:
                r = res[i]; pp = [g for (s_, g) in r["pays"] if s_ <= H_]
                pn.append(0.9 * sum(pp)); npay.append(len(pp))
                bust.append(r["status"] in ("BUST", "STUCK") and r["sessions"] <= H_)
                if pp: first.append(next(s_ for (s_, g) in r["pays"] if s_ <= H_))
            out[f"{w}{H_}"] = dict(n=len(ix), pay_net=float(np.mean(pn)), npay=float(np.mean(npay)), p_any=100 * float(np.mean([x > 0 for x in npay])),
                                    breach=100 * float(np.mean(bust)), first_med=float(np.median(first)) if first else None, first_mean=float(np.mean(first)) if first else None,
                                    dll=float(np.mean([res[i]["dll"] for i in ix])), blocked=float(np.mean([res[i]["blocked"] for i in ix])),
                                    maxdd=float(np.mean([res[i]["maxdd"] for i in ix])), big6k=float(np.mean([res[i]["big6k"] for i in ix])))
    hy = {}
    for i, d in enumerate(dates):
        if i + 120 <= L:
            kk = d[:4] + ("H1" if int(d[5:7]) <= 6 else "H2"); hy.setdefault(kk, []).append(0.9 * sum(g for s_, g in res[i]["pays"] if s_ <= 120))
    v = {a: float(np.mean(b)) for a, b in hy.items()}
    out["hy120"] = v; out["hy_min"] = min(v.values()); out["hy_med"] = float(np.median(list(v.values())))
    return out
