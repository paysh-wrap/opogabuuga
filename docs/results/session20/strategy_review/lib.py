"""Session 20 strategy review (adapted from session 19 lib; days12.pkl MNQ+MES, no volume)\nSession 19 refine study - shared library (self-contained, numpy/pandas only).  Research only; nothing in the app is touched.
Data: cached Databento 1m (MNQ.v.0 mnq_2019_2026.csv; MGC split_raw/MGC_<year>.csv).  Databento is locked: no downloads.
Windows: IS (pick) = 2019-05-06..2025-11-05, JUDGE = last 12 months 2025-11-06..2026-11-06.  (HO24 = 2024-01..2026-11 shown as secondary.)"""
import os, glob, pickle
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-opogabuuga/50bc3d78-c0a4-5955-9229-af69d0b1b2e9/scratchpad"
OUT = os.path.dirname(os.path.abspath(__file__))
PV, TICK, FEE = 2.0, 0.25, 1.0
NB = 390

_D0 = None
PKL = SP + "/data/days12.pkl"
def build_days(sym="MNQ"):
    D, E = pickle.load(open(PKL, "rb"))
    if sym == "MNQ": return D
    return [(d, E[d]) for d, _ in D]

def day_feats(days):
    """per-day features, past data only (no volume): dow, prior close/high/low, ATR14 of daily ranges."""
    F = {}
    rng = np.array([np.nanmax(a["high"]) - np.nanmin(a["low"]) for _, a in days])
    for i in range(1, len(days)):
        d, a = days[i]
        f = dict(pclose=days[i - 1][1]["close"][NB - 1], pH=np.nanmax(days[i - 1][1]["high"]), pL=np.nanmin(days[i - 1][1]["low"]), dow=pd.Timestamp(d).day_of_week)
        if i >= 14: f["atr"] = rng[i - 14:i].mean()
        F[d] = f
    return F

S0 = build_days("MNQ")[14][0]   # first tradeable date after 14-day lookback
IS_END, J0, J1 = "2025-11-05", "2025-11-06", "2026-10-30"

def era(t, e):
    if e == "IS": return t[(t.d >= S0) & (t.d <= IS_END)]
    if e == "J": return t[(t.d >= J0) & (t.d <= J1)]
    return t[(t.d >= S0) & (t.d <= J1)]

RANGES = dict(IS=(S0, IS_END), J=(J0, J1), ALL=(S0, J1))

def stats(t, e):
    t = era(t, e)
    if not len(t): return dict(n=0, win=np.nan, pf=np.nan, avg=0.0, net=0.0, dd=0.0)
    w = t.pnl > 0; gl = -t.pnl[~w].sum(); cum = np.concatenate([[0], t.pnl.cumsum().values])
    return dict(n=len(t), win=100 * w.mean(), pf=(t.pnl[w].sum() / gl) if gl > 0 else np.inf, avg=t.pnl.mean(), net=t.pnl.sum(), dd=np.max(np.maximum.accumulate(cum) - cum))

# ---------------- Lucid Pro eval simulator (generalised from session-17 sim.py) ----------------
ACC = {  # size: (start, target, mll, lock_trigger_gain, lock_floor_gain, soft DLL in eval, micros used)
    25: dict(B0=25000., TGT=1250., MLL=1000., DLL=None, N=1),
    50: dict(B0=50000., TGT=3000., MLL=2000., DLL=1200., N=2),
    100: dict(B0=100000., TGT=6000., MLL=3000., DLL=1800., N=3),
    150: dict(B0=150000., TGT=9000., MLL=4500., DLL=2700., N=5)}
def day_table(t, e, n=1):
    s, en = RANGES[e]; days = pd.bdate_range(s, en).strftime("%Y-%m-%d").tolist(); by = {}
    for r in t.itertuples():
        if s <= r.d <= en: by.setdefault(r.d, []).append(r.pnl * n)
    return [by.get(d, []) for d in days]
def _day(bal, trades, dll):
    start = bal
    for p in trades:
        if dll is not None and bal - start <= -dll: break      # soft DLL: stop the session, account lives
        bal += p; yield bal
def eval_run(tab, A, horizon=120):
    B0, TGT, MLL, DLL = A["B0"], A["TGT"], A["MLL"], A["DLL"]
    bal = peak = B0; floor = B0 - MLL
    for n, trades in enumerate(tab[:horizon]):
        for bal in _day(bal, trades, DLL):
            if bal <= floor: return "BUST", n + 1
        peak = max(peak, bal)                                   # EOD trailing
        floor = B0 + 100 if peak >= B0 + MLL + 100 else max(floor, peak - MLL)
        if bal - B0 >= TGT: return "PASS", n + 1
    return "OPEN", min(horizon, len(tab))
def _sum(res):
    n = len(res); ps = [s for o, s in res if o == "PASS"]
    return dict(pass_=100 * len(ps) / n, bust=100 * sum(o == "BUST" for o, _ in res) / n, med=float(np.median(ps)) if ps else np.nan)
def eval_boot(t, e, size, n_paths=600, cap=400, block=10, seed=7, n=None):
    A = ACC[size]; tab = day_table(t, e, A["N"] if n is None else n); rnd = np.random.default_rng(seed); out = []
    L = len(tab)
    for _ in range(n_paths):
        p = []
        while len(p) < cap:
            i = int(rnd.integers(0, L)); p.extend(tab[i:i + block])
        out.append(eval_run(p[:cap], A, cap))
    return _sum(out)
def eval_roll(t, e, size, horizon=120, step=2, n=None):
    A = ACC[size]; tab = day_table(t, e, A["N"] if n is None else n)
    res = [eval_run(tab[s:], A, horizon) for s in range(0, max(len(tab) - 40, 1), step)]
    return _sum(res)
def delta_ci(t, base, e, n=2000, block=10, seed=3):
    s, en = RANGES[e]; days = pd.bdate_range(s, en).strftime("%Y-%m-%d")
    f = lambda x: x[(x.d >= s) & (x.d <= en)].groupby("d").pnl.sum().reindex(days).fillna(0.0)
    d = (f(t) - f(base)).values; L = len(d); rnd = np.random.default_rng(seed); nb = int(np.ceil(L / block))
    cs = np.concatenate([[0.0], np.cumsum(d)]); st = rnd.integers(0, max(L - block, 1), (n, nb))
    res = (cs[st + block] - cs[st]).sum(axis=1)
    return float(d.sum()), float(np.percentile(res, 2.5)), float(np.percentile(res, 97.5))
