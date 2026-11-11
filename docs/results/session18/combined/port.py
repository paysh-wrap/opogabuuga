"""Account-level portfolio simulator for the combined study (pure python/numpy; works on the candidate files from cands.py).
One account = ONE open position at a time (Lucid rule / CLAUDE.md #7), across both markets (MNQ = EQUITY_INDEX group, MGC = METALS group).  Because only one position can be
open, the household hedge lock (no opposite direction inside a group) can never be violated by a single account; the selector counts the signals that WOULD have been
opposite-direction in the same group while a position was open ('hedge_vetoes') for information.
Sizing: n = max(1, min(cap, floor(budget / per_micro_risk))), per_micro_risk = stop distance $ + fee RT + 1 tick slippage; budget = RISK_FRAC x MLL (0.25 = the NOISE
convention: 1 micro x $250 stop on a 25K = 25% of its $1,000 MLL).  P&L / MAE scale linearly with n.
Day rules (app, plan yaml `internal`): max 3 trades/day, day stop after 2 consecutive losses, soft DLL (eval yaml: none / 1,200 / 1,800 / 2,700) with a $40 margin.
Eval = Lucid Pro eval of the plan: target, EOD-trailing MLL, lock at start+100 once peak >= start+MLL+100, bust on the worst open loss (strict MAE), 120-session horizon."""
import bisect, random
import numpy as np, pandas as pd

HERE = "/home/user/opogabuuga/docs/results/session18/combined"
START, SPLIT, END = "2025-11-06", "2026-06-30", "2026-11-05"
ERAS = dict(IS=(START, SPLIT), HO=("2026-07-01", END), FULL=(START, END))
MK = dict(MNQ=dict(fee=1.0, tick=0.25, pv=2.0, grp="EQUITY_INDEX"), MGC=dict(fee=1.6, tick=0.10, pv=10.0, grp="METALS"))
# plan files config/rules/lucid_pro_{25,50,100,150}k.yaml : eval target / MLL / soft DLL ; max_contracts.micros = 20 / 40 / 60 / 100 ; internal_max_micros 10 / 20? / 40 / 60 (app)
ACCT = {25: dict(start=25000, tgt=1250, mll=1000, dll=None, plan_micros=20, cap=2, noise_n=1),
        50: dict(start=50000, tgt=3000, mll=2000, dll=1200, plan_micros=40, cap=2, noise_n=2),
        100: dict(start=100000, tgt=6000, mll=3000, dll=1800, plan_micros=60, cap=60, noise_n=2),
        150: dict(start=150000, tgt=9000, mll=4500, dll=2700, plan_micros=100, cap=100, noise_n=3)}
RULES = dict(max_trades=3, max_consec=2, dll_margin=40.0)
STRAT_DAY_CAP = {"ICT": 1}        # ICT study = max 1 trade/day (per market)


def load_cands():
    c = pd.concat([pd.read_pickle(HERE + f"/out/cands_{m}.pkl") for m in ("MNQ", "MGC")], ignore_index=True)
    c = c[(c.d >= START) & (c.d <= END)].reset_index(drop=True)
    return c


def vote_mask(c, window=30):
    """True if >=1 OTHER strategy has a same-market same-side candidate within the previous `window` minutes (<= now) and none has the opposite side.  Uses the REAL sides."""
    ok = np.zeros(len(c), bool)
    for m, g in c.groupby("mkt"):
        t0 = g.t0.values; side = g.side.values; st = g.strat.values; idx = g.index.values
        order = np.argsort(t0, kind="stable"); t0s = t0[order]; sd = side[order]; ss = st[order]; ix = idx[order]
        for k in range(len(t0s)):
            lo = bisect.bisect_left(t0s, t0s[k] - window); hi = bisect.bisect_right(t0s, t0s[k])
            agree = opp = False
            for j in range(lo, hi):
                if ss[j] == ss[k]: continue
                if sd[j] == sd[k]: agree = True
                else: opp = True
            ok[ix[k]] = agree and not opp
    return ok


def select(c, acct, rank, cap=None, frac=0.25, rules=RULES, rand_seed=None, fixed_n=None, day_rules=True, mask=None):
    """c: candidate rows (any mix of strategies/markets).  rank: dict strat -> priority (lower = first) used to break ties at the same entry minute.
    rand_seed: use the random-direction twin of every candidate (coin flip per candidate).  fixed_n: 1 = raw single-micro sim (no day rules, no budget) for the reproduction tables."""
    a = ACCT[acct]; cap = a["cap"] if cap is None else cap; budget = frac * a["mll"]
    if mask is not None: c = c[mask]
    if len(c) == 0: return pd.DataFrame(columns=["d", "t0", "t1", "mkt", "strat", "var", "side", "n", "pnl", "mae", "risk"])
    c = c.assign(_r=c.strat.map(rank)).sort_values(["t0", "_r"], kind="stable")
    arr = {k: c[k].values for k in ("d", "t0", "t1", "mkt", "strat", "var", "side", "pnl", "mae", "risk", "sideF", "pnlF", "maeF", "t1F")}
    if rand_seed is not None:
        rnd = np.random.default_rng(rand_seed).random(len(c)) < 0.5
        ok = ~np.isnan(arr["pnlF"])
        flip = rnd & ok
        for k, kf in (("side", "sideF"), ("pnl", "pnlF"), ("mae", "maeF"), ("t1", "t1F")): arr[k] = np.where(flip, arr[kf], arr[k])
    out = []; busy = -1; busy_side = 0; busy_mkt = None; cur = None; cnt = 0; consec = 0; dpnl = 0.0; scnt = {}; veto = 0
    for i in range(len(c)):
        d = arr["d"][i]; t0 = arr["t0"][i]
        if d != cur: cur = d; cnt = 0; consec = 0; dpnl = 0.0; scnt = {}
        if t0 <= busy:
            if arr["mkt"][i] == busy_mkt and arr["side"][i] != busy_side: veto += 1
            continue
        m = arr["mkt"][i]; st = arr["strat"][i]
        if fixed_n is None:
            if day_rules:
                if cnt >= rules["max_trades"] or consec >= rules["max_consec"]: continue
                if a["dll"] is not None and dpnl <= -a["dll"] + rules["dll_margin"]: continue
            if STRAT_DAY_CAP.get(st) is not None and scnt.get((st, m), 0) >= STRAT_DAY_CAP[st]: continue
            per = arr["risk"][i] + MK[m]["fee"] + MK[m]["tick"] * MK[m]["pv"]
            n = max(1, min(cap, int(budget // per)))
            if day_rules and a["dll"] is not None:
                room = a["dll"] + dpnl - rules["dll_margin"]
                n = min(n, int(room // per))
                if n < 1: continue
        else:
            n = fixed_n
            if STRAT_DAY_CAP.get(st) is not None and scnt.get((st, m), 0) >= STRAT_DAY_CAP[st]: continue
        pnl = arr["pnl"][i] * n
        out.append((d, t0, arr["t1"][i], m, st, arr["var"][i], arr["side"][i], n, pnl, arr["mae"][i] * n, arr["risk"][i] * n))
        busy = arr["t1"][i]; busy_side = arr["side"][i]; busy_mkt = m
        cnt += 1; consec = consec + 1 if pnl < 0 else 0; dpnl += pnl; scnt[(st, m)] = scnt.get((st, m), 0) + 1
    t = pd.DataFrame(out, columns=["d", "t0", "t1", "mkt", "strat", "var", "side", "n", "pnl", "mae", "risk"])
    t.attrs["hedge_vetoes"] = veto
    return t


# ---------------------------------------------------------------------------------------------- stats
def era_slice(t, era):
    lo, hi = ERAS[era]; return t[(t.d >= lo) & (t.d <= hi)]


def pstats(x):
    if len(x) == 0: return dict(n=0, win=np.nan, pf=np.nan, payoff=np.nan, avg=np.nan, net=0.0, dd=0.0)
    p = x.pnl.values; eq = np.cumsum(p); dd = float(np.max(np.maximum.accumulate(np.r_[0, eq])[1:] - eq))
    w = p[p > 0]; l = p[p < 0]; gl = -l.sum()
    return dict(n=len(p), win=100 * (p > 0).mean(), pf=(w.sum() / gl) if gl > 0 else (np.inf if w.sum() > 0 else np.nan),
                payoff=(w.mean() / -l.mean()) if len(w) and len(l) else np.nan, avg=p.mean(), net=p.sum(), dd=dd)


def consistency(x):
    if len(x) == 0 or x.pnl.sum() <= 0: return np.nan
    return 100 * x.groupby("d").pnl.sum().max() / x.pnl.sum()


def bdays(era):
    lo, hi = ERAS[era]; return pd.bdate_range(lo, hi).strftime("%Y-%m-%d").tolist()


def day_table(t, era):
    days = bdays(era); by = {}
    for r in t[(t.d >= ERAS[era][0]) & (t.d <= ERAS[era][1])].itertuples(): by.setdefault(r.d, []).append((r.pnl, r.mae))
    return [by.get(d, []) for d in days]


def eval_run(tab, A, horizon=120):
    B0, TGT, MLL = A["start"], A["tgt"], A["mll"]
    bal = peak = B0; floor = B0 - MLL
    for n, trades in enumerate(tab[:horizon]):
        for pnl, mae in trades:
            if bal - max(mae, -pnl, 0.0) <= floor: return "BUST", n + 1
            bal += pnl
            if bal <= floor: return "BUST", n + 1
        peak = max(peak, bal)
        floor = B0 + 100 if peak >= B0 + MLL + 100 else max(floor, peak - MLL)
        if bal - B0 >= TGT: return "PASS", n + 1
    return "OPEN", min(horizon, len(tab))


def _sum(res):
    n = len(res); ps = [s for o, s in res if o == "PASS"]
    return dict(n=n, pas=100 * len(ps) / n, bust=100 * sum(o == "BUST" for o, _ in res) / n, med=float(np.median(ps)) if ps else np.nan)


def eval_roll(t, A, era, step=2, horizon=120):
    tab = day_table(t, era); n = len(tab)
    res = [eval_run(tab[s0:], A, horizon) for s0 in range(0, max(1, n - 40), step)]
    return _sum(res)


def eval_boot(t, A, era, n_paths=600, cap=500, block=10, seed=7):
    tab = day_table(t, era); rnd = random.Random(seed); out = []
    for _ in range(n_paths):
        p = []
        while len(p) < cap:
            i = rnd.randrange(len(tab)); p.extend(tab[i:i + block])
        out.append(eval_run(p[:cap], A, cap))
    return _sum(out)
