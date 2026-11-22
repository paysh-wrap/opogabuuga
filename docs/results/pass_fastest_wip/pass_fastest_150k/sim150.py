"""Pass-fastest study, Pro 150K EVALUATION (research only; nothing in backend/app, config/ or frontend/ is touched).

One account simulator = the validated pass_faster / pass_faster_fixed (variant A, one position at a time) logic, generalised with the size-table
features the app already has (SizeTierCfg: contracts, brake, grow_per/max_contracts, taper, day_lock_pct, stop_usd) and the plan's per-trade cap.
Rules in every run (150K, EOD): trailing EOD MLL + lock (154,600 -> 150,100), DLL 2,700 incl. LucidScale (60 % of peak EOD profit once locked),
40 % consistency at pass + 38 % day stop (a trade is capped at the day stop, the day ends), min profitable days, kill distance 50 + pre-trade room check
(+$40 margin), D57 shrink (0.6 of the room), plan per-trade cap 2,250 (max_trade_risk_usd), max ONE open position, never hedge, flat by close
(streams already are).  Non-pass = stuck (NOISE can no longer be sized) / bust / still running, exactly as pass_faster.

Sizing per signal (controller order): auto_contracts = grow -> taper -> brake (risk/strategy_sizing.py), then the day lock (EVAL_DAY_LOCK),
then pretrade: plan cap, D57 shrink, room check.  NOISE and the afternoon fade are sized by the table; CANDACE / GALA use FIXED micro counts
(needs code in the app: today they are sized by their Lucid fit).
"""
import sys, os, math, pickle
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
SCR = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/pf150k"

# ------------------------------------------------------------------------------------------------ plan constants (asserted against the old loader in validate.py)
SIZE = 150000.0; TARGET = 9000.0; MLL = 4500.0; LOCK_TRIG = 154600.0; LOCK_LVL = 150100.0; DLL0 = 2700.0; CONS = 40.0; MPD = 1
KILL = 50.0; MARGIN = 40.0; DSTOP = 3420.0; CAP_TRADE = 2250.0; SCALE = True
SHRINK = 0.6; MINPCT = 0.002; TV = 0.5; FEE = 1.0; SLIP = 1; PV = 2.0; TICK = 0.25; COST1 = 2.0     # COST1 = cost1() of the old plan (CANDACE / GALA round trip per micro)
GMIN = 112.0                                                                                      # run_fixed.GMIN (smin of the base stream) - same constant for every stream
WIN = {"ALL": ("2021-10-21", "2026-10-30"), "PICK": ("2021-10-21", "2023-12-31"), "JUDGE": ("2024-01-01", "2026-10-30")}
KN, KF, KC, KG = 0, 1, 2, 3     # kinds: NOISE, afternoon fade, CANDACE, GALA

_D, _E = pickle.load(open(PKL, "rb"))
ALL_DATES = [d for d, _a in _D]
OPEN = {d: a["open"] for d, a in _D}
DATES = [d for d in ALL_DATES if WIN["ALL"][0] <= d <= WIN["ALL"][1]]
L = len(DATES)
IDX = {d: i for i, d in enumerate(DATES)}
J0 = next(i for i, d in enumerate(DATES) if d >= WIN["JUDGE"][0])          # first judge start
P1 = max(i for i, d in enumerate(DATES) if d <= WIN["PICK"][1])            # last pick day
DOW = {d: pd.Timestamp(d).dayofweek for d in DATES}
del _D, _E


# ------------------------------------------------------------------------------------------------ streams (cached per process)
_cache = {}


def _load_gen():
    import gen_lib as G
    return G


def noise_df(stop, lock, maxtr, mon):
    k = ("N", stop, lock, maxtr, mon)
    if k not in _cache:
        fn = f"{SCR}/streams/noise_s{int(stop)}_l{int(lock)}_m{maxtr}_{'M' if mon else 'x'}.csv"
        if os.path.exists(fn): df = pd.read_csv(fn)
        else:
            G = _load_gen(); df = G.noise_stream(stop, lock, maxtr, mon)
            os.makedirs(os.path.dirname(fn), exist_ok=True); df.to_csv(fn, index=False)
        df = df[(df.d >= WIN["ALL"][0]) & (df.d <= WIN["ALL"][1])].copy()
        df["entry"] = [float(OPEN[d][int(k_)]) for d, k_ in zip(df.d, df.ek)]
        _cache[k] = df
    return _cache[k]


def fade_df(stop, mon):
    """causal fade stream for a NOISE stream key is built in fade_for(); this returns the raw all-day stream at `stop`"""
    k = ("Fraw", stop)
    if k not in _cache:
        fn = f"{SCR}/streams/fade_s{int(stop)}.csv"
        if os.path.exists(fn): df = pd.read_csv(fn)
        else:
            G = _load_gen(); df = G.fade_stream(float(stop)); os.makedirs(os.path.dirname(fn), exist_ok=True); df.to_csv(fn, index=False)
        df = df[(df.d >= WIN["ALL"][0]) & (df.d <= WIN["ALL"][1])].copy()
        df["entry"] = [float(OPEN[d][int(k_)]) for d, k_ in zip(df.d, df.ek)]
        _cache[k] = df
    return _cache[k]


def fade_for(stop, mon, noise_stream_df, rule="causal"):
    """fade trades allowed under the live rule: not on a skipped weekday (Mondays off unless mon) and only if NOISE has not entered EARLIER that day
    (a NOISE signal at the same bar counts as earlier: NOISE runs first in the dispatcher).  rule='strict' = session-19 F0 (no NOISE entry at all that day = look-ahead)."""
    f = fade_df(stop, mon)
    if not mon: f = f[[DOW[d] != 0 for d in f.d]]
    first = noise_stream_df.groupby("d").ek.min()
    nf = f.d.map(first)
    keep = nf.isna() if rule == "strict" else (nf.isna() | (nf > f.sk + 1))
    return f[keep.values]


def candace_df(win):
    k = ("C", win)
    if k not in _cache:
        fn = WT + ("/docs/results/pass_faster_c125/streams_candace_base.csv" if win == 1000 else "/docs/results/pass_faster_c125/streams_candace_w1030.csv")
        c = pd.read_csv(fn); c = c[(c.day >= WIN["ALL"][0]) & (c.day <= WIN["ALL"][1])]
        per = c.stop_pts * 2.0 + 2.0                      # per-micro risk (stop $ + fee + slippage), same as run_fixed
        _cache[k] = c[per <= 125.0 + 1e-9]
    return _cache[k]


def gala_df():
    k = ("G",)
    if k not in _cache:
        g = pd.read_csv(WT + "/docs/results/new_strategies/gala_trade_more/trades_window_end_1230.csv")
        _cache[k] = g[(g.day >= WIN["ALL"][0]) & (g.day <= WIN["ALL"][1])]
    return _cache[k]


# ------------------------------------------------------------------------------------------------ configuration
DEF = dict(stop=250, lock=100, maxtr=3, mon=False, N=3, brake=(0.5, 2), grow=None, taper=None, dlock=None,
           fade=False, nc=0, cwin=1000, ng=0, consoff=False, frule="causal", dllread="sim")


def mk(**kw):
    c = dict(DEF); c.update(kw)
    bad = set(kw) - set(DEF)
    assert not bad, bad
    return c


def key(c):
    b = "-" if not c["brake"] else f"{c['brake'][0]:g}/{c['brake'][1]}"
    g = "-" if not c["grow"] else f"{c['grow'][0]:g}/{c['grow'][1]}"
    t = "-" if not c["taper"] else f"{c['taper'][0]:g}/{c['taper'][1]}"
    d = "-" if not c["dlock"] else f"{c['dlock']:g}"
    return (f"s{c['stop']}_l{c['lock']}_m{c['maxtr']}_{'M' if c['mon'] else 'x'}_N{c['N']}_b{b}_g{g}_t{t}_d{d}_f{int(bool(c['fade']))}{'s' if c['frule']=='strict' else ''}"
            f"_c{c['nc']}w{c['cwin']}_G{c['ng']}{'_cOFF' if c['consoff'] else ''}{'_dllAPP' if c['dllread'] == 'app' else ''}")


def build_days(c, dates=None):
    """list over `dates` (default: the trading days of the 5-year window) of tuples (m_in, m_out, kind, a, b, cc, d) sorted by entry bar"""
    by = {}
    n = noise_df(c["stop"], c["lock"], c["maxtr"], c["mon"])
    for r in n.itertuples():
        by.setdefault(r.d, []).append((float(r.ek), float(r.xk) + 0.5, KN, float(r.pnl), float(r.mae), float(r.risk), float(r.entry)))
    if c["fade"]:
        f = fade_for(c["stop"], c["mon"], n, c["frule"])
        for r in f.itertuples():
            by.setdefault(r.d, []).append((float(r.ek), float(r.xk) + 0.5, KF, float(r.pnl), float(r.mae), float(r.risk), float(r.entry)))
    if c["nc"]:
        for r in candace_df(c["cwin"]).itertuples():
            by.setdefault(r.day, []).append((float(r.idx), float(r.exit_idx), KC, float(r.p1), float(r.stop_pts), 0.0, 0.0))
    if c["ng"]:
        for r in gala_df().itertuples():
            by.setdefault(r.day, []).append((float(r.idx), float(max(r.exit_idx, r.idx)), KG, float(r.pts), float(r.stop_pts), float(r.ptsB), 0.0))
    for d in by: by[d].sort(key=lambda x: (x[0], x[2]))
    return [by.get(d, ()) for d in (DATES if dates is None else dates)]


# ------------------------------------------------------------------------------------------------ the account
OUT_PASS, OUT_STUCK, OUT_OPEN, OUT_BUST = 0, 1, 2, 3


def simulate(days, idx, c, maxs=10 ** 9):
    """one fresh account that trades the days idx[0], idx[1], ... (day indices into `days`) until pass / stuck / bust / data end / maxs sessions.
    Returns (outcome, sessions, day_stop_hits, dll_hits, dlock_days)."""
    N = c["N"]; br = c["brake"]; gr = c["grow"]; tp = c["taper"]; dlk = c["dlock"]; nc = c["nc"]; ng = c["ng"]
    bb, bc = (br if br else (None, None)); gper, gmax = (gr if gr else (None, None)); tfr, tn = (tp if tp else (None, None))
    dstop = 1e18 if c["consoff"] else DSTOP
    bal = SIZE; floor = bal - MLL; peak = bal; locked = False; pdays = 0; best = 0.0; s = 0; peak_e = bal
    dsh = dllh = dlkd = 0
    kd = KILL; mg = MARGIN; appdll = c["dllread"] == "app"
    for di in idx:
        s += 1
        if s > maxs: break
        tl = days[di]
        if not tl: continue
        today = 0.0; stop = False; peak_day = 0.0; free = -1.0; last = -1; lockday = False
        dll = DLL0
        if SCALE and locked: dll = 0.6 * (peak_e - SIZE)
        rem0 = TARGET - (bal - SIZE)
        for (m_in, m_out, kind, a, b, cc, d) in tl:
            if stop: break
            if m_in <= free and not (kind == KN and last == KN):
                continue
            if kind <= KF:                                           # NOISE / fade: size table + checks
                if lockday: continue
                if dlk and today > 0 and rem0 > 0 and today >= dlk * rem0:
                    lockday = True; dlkd += 1; continue
                cush = bal - floor
                q = N
                if gper:
                    ex = int(cush // gper) - 1
                    if ex > 0: q = min(gmax, N + ex)
                if tfr and (max(rem0, 0.0) / TARGET) < tfr: q = min(q, tn)
                if bb is not None and cush / MLL < bb: q = min(q, bc)
                pnl, mae, risk, entry = a, b, cc, d
                q = min(q, int(CAP_TRADE // risk))
                if cush <= kd: return OUT_STUCK, s, dsh, dllh, dlkd
                room0 = cush - kd
                if dll:
                    if appdll: room0 = min(room0, dll - (max(0.0, peak_day, today) - today))      # app reading (risk.checks.dll_remaining, D18)
                    else: room0 = min(room0, dll + today)                                         # session-21 reading used by every earlier study
                pp = None; eff_mae = mae
                while q > 0:
                    S_ = risk
                    if q * risk > SHRINK * room0:
                        pt = math.floor(((SHRINK * room0 / q) - FEE) / TV - SLIP)
                        if pt * 0.25 < MINPCT * entry or pt <= 0: q = -1; break
                        S_ = pt * TV + FEE + TV
                    if q * S_ + mg <= room0:
                        if S_ < risk and mae >= S_: pp = -S_
                        else: pp = pnl
                        eff_mae = min(mae, S_) if S_ < risk else mae
                        break
                    q -= 1
                if q <= 0:
                    if SHRINK * (cush - kd) < GMIN: return OUT_STUCK, s, dsh, dllh, dlkd
                    continue
                pq = q * pp; dead = False
                if q * eff_mae >= cush - kd:
                    pq = -(cush - kd); dead = True
            else:                                                    # CANDACE / GALA: FIXED micros, per_micro risk checked against room and DLL left
                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0
                left = None
                if dll:
                    left = dll - (max(0.0, peak_day, today) - today)
                    if left <= 0: stop = True; break
                lim = bal - floor - kd
                if left is not None and left < lim: lim = left
                q = nc if kind == KC else ng
                while q >= 1 and q * per + mg > lim: q -= 1
                if q < 1: continue
                if kind == KC: pq = q * (a * PV - COST1)
                elif q >= 2:
                    ha = -(-q // 2); hb = q - ha
                    pq = PV * (ha * a + hb * cc) - q * COST1
                else: pq = q * (a * 2.0 - COST1)
                dead = False
            free = m_out; last = kind
            if dll and today + pq <= -dll: pq = -dll - today; stop = True; dllh += 1
            if today + pq > dstop: pq = dstop - today; stop = True; dsh += 1
            today += pq; bal += pq
            if today > peak_day: peak_day = today
            if dead: return OUT_BUST, s, dsh, dllh, dlkd
            if bal <= floor + kd: return OUT_BUST, s, dsh, dllh, dlkd
        if today > 0:
            pdays += 1
            if today > best: best = today
        if bal > peak_e: peak_e = bal
        if bal > peak and not locked:
            peak = bal
            if peak >= LOCK_TRIG: locked = True; floor = LOCK_LVL
            else: floor = peak - MLL
        prof = bal - SIZE
        if prof >= TARGET and pdays >= MPD and (c["consoff"] or best <= CONS / 100 * prof): return OUT_PASS, s, dsh, dllh, dlkd
    return OUT_OPEN, s, dsh, dllh, dlkd


# ------------------------------------------------------------------------------------------------ rolling run + metrics
def roll(c, days=None):
    """rolling start on every trading day of the 5-year window. returns per-start arrays."""
    if days is None: days = build_days(c)
    out = np.zeros(L, dtype=np.int8); ses = np.zeros(L, dtype=np.int32); dsh = np.zeros(L, dtype=np.int16); dllh = np.zeros(L, dtype=np.int16); dlk = np.zeros(L, dtype=np.int16)
    for s in range(L):
        o, n, a, b, e = simulate(days, range(s, L), c)
        out[s] = o; ses[s] = n; dsh[s] = a; dllh[s] = b; dlk[s] = e
    return dict(out=out, ses=ses, dsh=dsh, dllh=dllh, dlk=dlk)


def window_view(r, win):
    """per-start (outcome, sessions) for a window, derived from the 5-year rolling run (identical to running the window alone: the sim is path-causal)."""
    out, ses = r["out"], r["ses"]
    if win == "ALL": return out, ses, np.arange(L)
    if win == "JUDGE":
        sl = np.arange(J0, L); return out[sl], ses[sl], sl
    sl = np.arange(0, P1 + 1)                                         # PICK: starts 2021-10-21..2023-12-31, accounts cut at the window end
    ev = sl + ses[sl] - 1                                             # day index of the account's last session
    cut = ev > P1
    o = np.where(cut, OUT_OPEN, out[sl]); n = np.where(cut, P1 - sl + 1, ses[sl])
    return o, n, sl


def summ(o, n):
    N_ = len(o); p = (o == OUT_PASS)
    d = {"n": N_, "pass": 100.0 * p.sum() / N_, "stuck": 100.0 * ((o == OUT_STUCK) | (o == OUT_BUST)).sum() / N_, "run": 100.0 * (o == OUT_OPEN).sum() / N_}
    for lim in (30, 45, 60, 90): d[f"p{lim}"] = 100.0 * (p & (n <= lim)).sum() / N_
    pn = n[p]
    d["med"] = float(np.median(pn)) if len(pn) else None
    d["p75"] = float(np.percentile(pn, 75)) if len(pn) else None
    d["mean_pass_days"] = float(pn.mean()) if len(pn) else None
    return d


def chains(out, ses, frm=0, to=None, T=None):
    """renewal chains: a stuck/bust account is reset and a new one starts the NEXT trading day; chain ends at the first pass.
    T (optional) = time-stop: an account that has not passed within T sessions is also reset at T (a limbo account is not kept for ever).
    returns finished/censored share, mean / median / p75 days to the first pass, mean attempts, over starts frm..to-1 of the 5-year run."""
    n = len(out); days_to = np.zeros(n + 1); att = np.zeros(n + 1); fin = np.zeros(n + 1, dtype=bool)
    for s in range(n - 1, -1, -1):
        o = out[s]; k = ses[s]
        if T is not None and k > T:                                   # not resolved within T sessions: reset at T
            nx = s + T
            if nx < n and fin[nx]: days_to[s] = T + days_to[nx]; att[s] = 1 + att[nx]; fin[s] = True
            continue
        if o == OUT_PASS: days_to[s] = k; att[s] = 1; fin[s] = True
        elif o in (OUT_STUCK, OUT_BUST):
            nx = s + k
            if nx < n and fin[nx]: days_to[s] = k + days_to[nx]; att[s] = 1 + att[nx]; fin[s] = True
    to = n if to is None else to
    m = fin[frm:to]; dd = days_to[frm:to][m]; aa = att[frm:to][m]
    if not m.sum(): return dict(fin=0.0, cens=100.0, mean=None, med=None, p75=None, att=None, n=int(to - frm))
    return dict(fin=100.0 * m.mean(), cens=100.0 * (1 - m.mean()), mean=float(dd.mean()), med=float(np.median(dd)), p75=float(np.percentile(dd, 75)), att=float(aa.mean()), n=int(to - frm))


def static(c, days=None):
    """fresh-account static replay (no balance logic): one position at a time, NOISE/fade at the base N, CANDACE/GALA at their fixed micros.
    plan-sized profit, closed-trade worst drawdown, trades per week.  Mirrors run_fixed.static without the room skip (never binds on a fresh account)."""
    if days is None: days = build_days(c)
    N = c["N"]; eq = pk = dd = 0.0; taken = 0; sig = 0; dlkn = 0
    for di in range(L):
        free = -1.0; last = -1
        for (m_in, m_out, kind, a, b, cc, d) in days[di]:
            sig += 1
            if m_in <= free and not (kind == KN and last == KN): continue
            if kind <= KF:
                q = min(N, int(CAP_TRADE // cc)); pq = q * a
            elif kind == KC:
                q = c["nc"]; pq = q * (a * PV - COST1)
            else:
                q = c["ng"]
                if q >= 2:
                    ha = -(-q // 2); hb = q - ha; pq = PV * (ha * a + hb * cc) - q * COST1
                else: pq = q * (a * 2.0 - COST1)
            free = m_out; last = kind; taken += 1; eq += pq
            if eq > pk: pk = eq
            if pk - eq > dd: dd = pk - eq
    return dict(profit=eq, dd=dd, taken=taken, signals=sig, tpw=taken / (L / 5.0))


def evaluate(c, with_static=True):
    days = build_days(c)
    r = roll(c, days)
    res = {"key": key(c), "cfg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in c.items()}}
    for w in ("ALL", "PICK", "JUDGE"):
        o, n, sl = window_view(r, w); res[w] = summ(o, n)
    o, n, _ = window_view(r, "ALL")
    p = o == OUT_PASS
    res["ch"] = chains(r["out"], r["ses"])
    res["ch_early"] = chains(r["out"], r["ses"], 0, int(L * 0.5))      # starts in the first half: >= ~600 sessions of data ahead (little censoring)
    res["ch_T120"] = chains(r["out"], r["ses"], T=120)                 # + time-stop: reset when not passed within 120 sessions
    res["ch_T90"] = chains(r["out"], r["ses"], T=90)
    res["dsh_pass_share"] = float(100.0 * ((r["dsh"] > 0) & p).sum() / max(p.sum(), 1)) if p.sum() else None
    res["dsh_mean_pass"] = float(r["dsh"][p].mean()) if p.sum() else None
    res["dll_pass_share"] = float(100.0 * ((r["dllh"] > 0) & p).sum() / max(p.sum(), 1)) if p.sum() else None
    res["dlock_mean_pass"] = float(r["dlk"][p].mean()) if p.sum() else None
    if with_static: res["static"] = static(c, days)
    res["_roll"] = r
    return res


def compact(res, nd=2):
    """result without the per-start arrays, floats rounded (what goes into results.json)"""
    def rnd(x):
        if isinstance(x, float): return round(x, nd)
        if isinstance(x, dict): return {k: rnd(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)): return [rnd(v) for v in x]
        return x
    return rnd({k: v for k, v in res.items() if not k.startswith("_")})


# ------------------------------------------------------------------------------------------------ bootstrap (session-21 protocol: business days incl. holidays, 10-day blocks, 600 paths x 400 sessions, seed 7)
BD = [d.strftime("%Y-%m-%d") for d in pd.bdate_range(*WIN["ALL"])]
LB = len(BD)


def boot_paths(Lb=LB, paths=600, cap=400, block=10, seed=7):
    rnd = np.random.default_rng(seed); out = []
    for _ in range(paths):
        pth = []
        while len(pth) < cap:
            i = int(rnd.integers(0, Lb)); pth.extend(range(i, min(i + block, Lb)))
        out.append(pth[:cap])
    return out


def boot_summary(days_bd, c, paths, maxs=400):
    res = [simulate(days_bd, p, c, maxs=maxs)[:2] for p in paths]
    return summ(np.array([x[0] for x in res]), np.array([x[1] for x in res]))


def resample_history(Lb=LB, block=10, seed=0):
    """block-bootstrap of the 5-year day history itself (10-day blocks): used for the intervals (history uncertainty), on top of the path draw"""
    rnd = np.random.default_rng(seed); idx = []
    while len(idx) < Lb:
        i = int(rnd.integers(0, Lb)); idx.extend(range(i, min(i + block, Lb)))
    return idx[:Lb]


def boot_intervals(c, reps=60, seed0=1000, q=(5, 95)):
    """point estimate = the protocol on the real history (seed 7); interval = percentiles over `reps` block-resampled histories, each with the same 600 x 400 path draw"""
    days_bd = build_days(c, BD); paths = boot_paths()
    pt = boot_summary(days_bd, c, paths)
    ps, p60, p45, md = [], [], [], []
    for r in range(reps):
        h = resample_history(seed=seed0 + r); dh = [days_bd[i] for i in h]
        s = boot_summary(dh, c, paths)
        ps.append(s["pass"]); p60.append(s["p60"]); p45.append(s["p45"]); md.append(s["med"] if s["med"] is not None else float("nan"))
    f = lambda a: [float(np.percentile(a, q[0])), float(np.percentile(a, q[1]))]
    return dict(point=pt, pass_ci=f(ps), p60_ci=f(p60), p45_ci=f(p45), med_ci=[float(np.nanpercentile(md, q[0])), float(np.nanpercentile(md, q[1]))], reps=reps)
