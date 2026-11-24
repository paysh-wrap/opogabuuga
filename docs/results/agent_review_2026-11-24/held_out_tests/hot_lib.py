"""Held-out tests 2026-11-24 (research only, app code untouched). Shared library.

Data: /home/user/days.pkl = (D, E): D = list of (date, MNQ 1-min RTH arrays open/high/low/close/vwap, idx 0 = 09:30 bar), E = MES.
NOISE generator = docs/results/session20/strategy_review/noise3.gen (the shipped baseline: $250 stop/micro, lock +100 -> entry+10,
hourly checks 10:00-15:00, max 3 entries, Mondays skipped, flat 16:00), copied here as gen2() with ONE change: entry checks and
exit checks are separate parameters. gen2() with defaults is asserted identical to noise3.gen() (see run_all.py step 0).
Costs: $1 fee + 1 tick slippage per fill = $2 per micro round trip. Entry at next bar open; stop checked first.
Windows: PICK = 2021-10-21 (first day with 14 days of history) .. 2023-12-31; JUDGE = 2024-01-01 .. 2026-10-30."""
import os, sys, types, pickle
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PKL = "/home/user/days.pkl"
S20 = REPO + "/docs/results/session20/strategy_review"
sys.path.insert(0, S20)
_src = open(S20 + "/lib.py").read().replace('SP + "/data/days12.pkl"', repr(PKL))
nlib = types.ModuleType("lib"); nlib.__file__ = S20 + "/lib.py"; sys.modules["lib"] = nlib
exec(compile(_src, S20 + "/lib.py", "exec"), nlib.__dict__)
import noise3  # noqa: E402  (session-20 shipped-baseline generator, unchanged)
from lib import PV, TICK, FEE, NB  # noqa: E402

PICK0, PICK1, JUD0, JUD1 = "2021-10-21", "2023-12-31", "2024-01-01", "2026-10-30"
WIN = dict(pick=(PICK0, PICK1), judge=(JUD0, JUD1), all=(PICK0, JUD1))
D, F, MOVES = noise3.data()
BARS = {d: a for d, a in D}
DATES = [d for d, _ in D]
monday = noise3.monday


def gen2(stop_usd=250.0, look=14, ent_checks=None, exit_checks=None, maxtr=3, lock=(100.0, 10.0), dayskip=monday, rnd=None, roll=0.015):
    """noise3.gen with separate entry / exit check sets (bar indices k; decision on the close of bar k). Defaults = shipped."""
    ent_checks = set(range(29, 360, 60)) if ent_checks is None else set(ent_checks)
    exit_checks = set(range(29, 360, 60)) if exit_checks is None else set(exit_checks)
    pv, tick, fee, nb = PV, TICK, FEE, NB
    hard = (stop_usd - fee - 2 * tick * pv) / pv
    rng = np.random.default_rng(rnd) if rnd is not None else None
    out = []
    for i in range(look, len(D)):
        d, a = D[i]
        if d < PICK0 or d > JUD1 or d not in F: continue
        f = F[d]
        if dayskip is not None and dayskip(d, f): continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = D[i - 1][1]["close"][nb - 1]
        if pc != pc or abs(o[0] / pc - 1) > roll: continue
        sig = np.nanmean(MOVES[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=0., ek=0, locked=False, hs=0.)
        ntr = pending = 0

        def close_trade(px, xk):
            nonlocal ntr
            if lock and st["locked"] and xk > st["ek"] and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)): ntr = maxtr
            p = (px - st["entry"]) * st["pos"] * pv - fee
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, side=st["pos"], entry=st["entry"]))
            st["pos"] = 0
        for k in range(nb):
            if c[k] != c[k]: continue
            if pending and st["pos"] == 0:
                en = o[k] + pending * tick
                st.update(entry=en, pos=pending, ek=k, locked=False); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hard
            pos = st["pos"]
            if pos:
                e = st["entry"]
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * tick, k)
                if st["pos"] and lock and not st["locked"] and ((pos > 0 and h[k] >= e + lock[0]) or (pos < 0 and l[k] <= e - lock[0])):
                    st["locked"] = True; st["hs"] = max(st["hs"], e + lock[1]) if pos > 0 else min(st["hs"], e - lock[1])
            if st["pos"] and k == nb - 1: close_trade(c[k] - st["pos"] * tick, k)
            if k in exit_checks:
                pos = st["pos"]
                if pos:
                    tr = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < tr) or (pos < 0 and c[k] > tr):
                        nk = k + 1
                        close_trade((o[nk] if nk < nb and o[nk] == o[nk] else c[k]) - pos * tick, min(nk, nb - 1))
            if k in ent_checks and k < nb - 1:
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side:
                        if rng is not None: side = 1 if rng.random() < 0.5 else -1
                        pending, ntr = side, ntr + 1
    return pd.DataFrame(out)


def win(t, w, col="d"):
    s, e = WIN[w]
    return t[(t[col] >= s) & (t[col] <= e)]


def bdays(w):
    s, e = WIN[w]
    return pd.bdate_range(s, e).strftime("%Y-%m-%d")


def stats(t, w, pnl="pnl", col="d"):
    """trades, win %, PF, net $, $/trade, max DD $ (closed-trade equity), daily Sharpe (annualised, bdays incl. zero days)."""
    t = win(t, w, col)
    if not len(t): return dict(n=0, win=np.nan, pf=np.nan, net=0.0, avg=np.nan, dd=0.0, sharpe=np.nan)
    p = t[pnl].values; g = p[p > 0].sum(); ls = -p[p < 0].sum()
    cum = np.concatenate([[0], np.cumsum(p)]); dd = float(np.max(np.maximum.accumulate(cum) - cum))
    daily = t.groupby(col)[pnl].sum().reindex(bdays(w), fill_value=0.0).values
    sh = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else np.nan
    return dict(n=int(len(t)), win=round(100 * float((p > 0).mean()), 1), pf=round(float(g / ls), 3) if ls > 0 else np.inf,
                net=round(float(p.sum()), 0), avg=round(float(p.mean()), 2), dd=round(dd, 0), sharpe=round(sh, 2))


def paired_boot(base, var, w, pnl="pnl", col="d", n=2000, block=10, seed=11):
    """95% CI of (var net - base net) in window w, moving-block bootstrap over business days (paired: same days drawn)."""
    days = bdays(w)
    b = win(base, w, col).groupby(col)[pnl].sum().reindex(days, fill_value=0.0).values
    v = win(var, w, col).groupby(col)[pnl].sum().reindex(days, fill_value=0.0).values
    dlt = v - b; L = len(dlt); rnd = np.random.default_rng(seed); nb = int(np.ceil(L / block)); out = []
    for _ in range(n):
        st = rnd.integers(0, L - block + 1, nb)
        out.append(np.concatenate([dlt[s:s + block] for s in st])[:L].sum())
    return round(float(dlt.sum()), 0), round(float(np.percentile(out, 2.5)), 0), round(float(np.percentile(out, 97.5)), 0)


def candace():
    """CANDACE ICT keep_all_sweeps ON (D154) 1-micro stream, as used by pass_fastest/lib50.py; pnl $ = p1 pts * 2 - $2."""
    c = pd.read_csv(REPO + "/docs/results/pass_faster_c125/streams_candace_base.csv")
    c = c.rename(columns={"day": "d"})
    c["side"] = np.where(c.dir == "LONG", 1, -1); c["pnl"] = c.p1 * PV - 2.0
    return c


def late():
    """late-day momentum leg, app-faithful (D166) 1-micro stream from new_edge/late_leg_sizes; pnl $ = pts * 2 - $2."""
    t = pd.read_csv(REPO + "/docs/results/new_edge/late_leg_sizes/trades_app.csv").rename(columns={"day": "d"})
    t["pnl"] = t.pts * PV - 2.0
    return t
