"""Lucid Pro 25K evaluation simulator - same assumptions as docs/results/tools/sim25k.py (session 9):
start 25,000, target +1,250 (Pro: pass in one day allowed, no consistency, no DLL in the eval), MLL 1,000 EOD-trailing floor, lock at 25,100 once the
EOD peak >= 26,100; breach checked after every trade ('seq'); 1 micro; rolling starts every 2nd business day of the era, horizon 120 sessions,
days with no trade count as sessions (as in session 9).  strict=True additionally kills the account when a trade's worst open loss (MAE) touches
the floor intraday (session-15 convention; stricter than session 9).
era 'HO' = 2024-01-01..2026-11-06 (same window as session 9), era 'IS' = 2019-05-06..2023-12-29.
Also a block bootstrap (10-session blocks, paths cut at 500 sessions) for a smoother PASS / BUST estimate."""
import random
import numpy as np, pandas as pd

B0, TGT, MLL = 25000.0, 1250.0, 1000.0
RANGES = dict(HO=("2024-01-01", "2026-11-06"), IS=("2019-05-06", "2023-12-29"))


def day_table(t, e):
    s, en = RANGES[e]
    days = pd.bdate_range(s, en).strftime("%Y-%m-%d").tolist()
    by = {}
    for r in t.itertuples():
        if s <= r.d <= en: by.setdefault(r.d, []).append((r.pnl, r.mae))
    return days, [by.get(d, []) for d in days]


def _step(bal, peak, floor, trades, strict):
    for pnl, mae in trades:
        if strict and bal - max(mae, -pnl, 0.0) <= floor: return bal, peak, floor, True
        bal += pnl
        if bal <= floor: return bal, peak, floor, True
    peak = max(peak, bal)
    floor = B0 + 100 if peak >= B0 + MLL + 100 else max(floor, peak - MLL)
    return bal, peak, floor, False


def eval_run(tab, horizon=120, strict=False):
    bal = peak = B0; floor = B0 - MLL
    for n, trades in enumerate(tab[:horizon]):
        bal, peak, floor, bust = _step(bal, peak, floor, trades, strict)
        if bust: return "BUST", n + 1
        if bal - B0 >= TGT: return "PASS", n + 1
    return "OPEN", min(horizon, len(tab))


def _sum(res):
    n = len(res); ps = [s for o, s in res if o == "PASS"]
    return dict(n=n, pass_=100 * len(ps) / n, bust=100 * sum(o == "BUST" for o, _ in res) / n, open_=100 * sum(o == "OPEN" for o, _ in res) / n,
                med=float(np.median(ps)) if ps else float("nan"))


def eval_roll(t, e="HO", horizon=120, step=2, strict=False):
    days, tab = day_table(t, e)
    res = [eval_run(tab[s0:], horizon, strict) for s0 in range(0, len(days) - 40, step)]
    return _sum(res)


def eval_boot(t, e="HO", n_paths=1000, cap=500, block=10, seed=7, strict=False):
    days, tab = day_table(t, e); rnd = random.Random(seed); out = []
    for _ in range(n_paths):
        p = []
        while len(p) < cap:
            i = rnd.randrange(len(tab)); p.extend(tab[i:i + block])
        out.append(eval_run(p[:cap], cap, strict))
    return _sum(out)


def daily(t, e):
    s, en = RANGES[e]
    days = pd.bdate_range(s, en).strftime("%Y-%m-%d")
    x = t[(t.d >= s) & (t.d <= en)].groupby("d").pnl.sum()
    return x.reindex(days).fillna(0.0)


def delta_ci(t, base, e="HO", n=2000, block=10, seed=3):
    """paired block-bootstrap 95% CI of (net profit of t - net profit of base) over the era's days (same day sample for both)."""
    d = (daily(t, e) - daily(base, e)).values; rnd = np.random.default_rng(seed); L = len(d); nb = int(np.ceil(L / block))
    cs = np.concatenate([[0.0], np.cumsum(d)]); st = rnd.integers(0, L - block + 1, (n, nb))
    res = (cs[st + block] - cs[st]).sum(axis=1)
    return float(d.sum()), float(np.percentile(res, 2.5)), float(np.percentile(res, 97.5))
