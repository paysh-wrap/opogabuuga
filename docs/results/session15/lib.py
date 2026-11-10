"""Session 15 research library (CAUSAL, no look-ahead). Trade-stream generators + account engine.
Data: Databento 1-minute bars, MNQ.v.0 / MES.v.0 / MGC.v.0 (cached CSV; env S15_RAW = folder with mnq_5y.csv, mes_5y.csv, mgc_5y.csv).
Costs: 1 tick adverse slippage on every market entry/exit and on stop fills; limit targets need a 1-tick trade-through; fee per micro round trip
(MNQ/MES $1.00, MGC $1.50 - same convention as sessions 10-14 for MNQ).  All P&L per 1 micro contract, USD, net of costs.
IS = 2021-11..2023-12 (pick), HO = 2024-01..2026-10 (judge)."""
import os, sys
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path[:0] = [ROOT + "/docs/results/session10/five_year"]
import noise_gen as NG  # load_days (RTH 09:30-16:00 arrays incl. session VWAP)

RAW = os.environ.get("S15_RAW", ROOT + "/backend/app/backtest/data/raw")
START, END, SPLIT = "2021-11-01", "2026-10-30", "2023-12-31"
INST = {  # point value $/pt per micro, tick, fee RT per micro
    "MNQ": dict(pv=2.0, tick=0.25, fee=1.0, csv="mnq_5y.csv"),
    "MES": dict(pv=5.0, tick=0.25, fee=1.0, csv="mes_5y.csv"),
    "MGC": dict(pv=10.0, tick=0.1, fee=1.5, csv="mgc_5y.csv"),
}
_cache = {}


def days(sym, start="09:30", end="16:00", **kw):
    key = (sym, start, end)
    if key not in _cache:
        _cache[key] = NG.load_days(f"{RAW}/{INST[sym]['csv']}", start=start, end=end, **kw)
    return _cache[key]


def hm(k, base=(9, 30)):
    m = base[0] * 60 + base[1] + k
    return f"{m // 60:02d}:{m % 60:02d}"


# ------------------------------------------------------------------------------------------------ trade walker
def walk(a, s, ek, stop_pts, tgt_pts, xend, inst, tgt_px=None, partial=None, be_after_partial=True, trail_fn=None):
    """Simulate one trade on day arrays `a` (open/high/low/close/vwap, 1-min). Entry = open of bar ek + 1 tick slippage.
    stop = entry - s*stop_pts (market, 1 tick slippage, gap-aware); target = entry + s*tgt_pts or absolute tgt_px (limit, needs 1-tick trade-through).
    partial = (frac, pts): `frac` of the position exits at +pts (limit, trade-through), the rest moves its stop to entry (+fee cover) if be_after_partial.
    Same-bar stop+target -> stop first. Exit at bar xend close - slippage if nothing hit.
    returns (pnl_usd_per_micro_net, exit_bar, mae_usd_per_micro (>=0, adverse excursion incl. slippage), risk_usd_per_micro)"""
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    pv, tk, fee = INST[inst]["pv"], INST[inst]["tick"], INST[inst]["fee"]
    e = o[ek] + s * tk
    stop = e - s * stop_pts
    tgt = tgt_px if tgt_px is not None else (e + s * tgt_pts if tgt_pts else None)
    risk = stop_pts * pv + fee + 2 * tk * pv
    pnl = 0.0; rem = 1.0; mae = 0.0; moved = False
    for j in range(ek, xend):
        if np.isnan(c[j]): continue
        hj, lj, oj = h[j], l[j], o[j]
        adverse = (e - lj) if s > 0 else (hj - e)
        mae = max(mae, adverse * pv)
        if (s > 0 and lj <= stop) or (s < 0 and hj >= stop):
            px = (min(stop, oj) if s > 0 else max(stop, oj)) - s * tk
            pnl += rem * (px - e) * s * pv; rem = 0; return pnl - fee, j, mae + tk * pv, risk
        if partial and not moved and rem == 1.0:
            ppx = e + s * partial[1]
            if (s > 0 and hj >= ppx + tk) or (s < 0 and lj <= ppx - tk):
                pnl += partial[0] * (ppx - e) * s * pv; rem -= partial[0]; moved = True
                if be_after_partial: stop = e + s * (fee / pv)  # breakeven incl. fee cover
        if tgt is not None and ((s > 0 and hj >= tgt + tk) or (s < 0 and lj <= tgt - tk)):
            pnl += rem * (tgt - e) * s * pv; rem = 0; return pnl - fee, j, mae, risk
    j = xend - 1
    while j > ek and np.isnan(c[j]): j -= 1
    px = c[j] - s * tk
    pnl += rem * (px - e) * s * pv
    return pnl - fee, j, mae, risk


# ------------------------------------------------------------------------------------------------ NOISE (verified rules, = rebuild_main_csv.noise_t) + MAE
def noise_stream(sym="MNQ", stop_usd=250.0, look=14, step=60, maxtr=3, scale=None, first_check=29, lock=None):
    """NOISE-area momentum, same bar loop as docs/results/session11/rebuild_main_csv.noise_t (hourly checks at bar 29, 89, ..., exit on the
    band/VWAP trail at the next bar open, flat at the last bar, fixed $ emergency stop) + MAE + optional scale-out.
    scale = (frac, mult): `frac` of the position exits at +mult*R (R = stop distance in points, limit with 1-tick trade-through), the rest gets a
    breakeven stop. Trade-level pnl = both legs net of costs.  lock = (trigger_pts, lock_pts): D75-P1 once price is +trigger_pts in favour the stop moves to entry+lock_pts; a stop-out from the locked stop ends NOISE for the day.
    rows: d, ek, xk, pnl, mae, risk, side"""
    I = INST[sym]; PV, TICK, FEE = I["pv"], I["tick"], I["fee"]
    Dd, nb = days(sym)
    hard = (stop_usd - FEE - 2 * TICK * PV) / PV
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in Dd])
    checks = set(range(first_check, 360, step)); out = []
    for i in range(look, len(Dd)):
        d, a = Dd[i]
        if d < START or d > END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = Dd[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0, entry=0.0, ek=0, mae=0.0, got=0.0, rem=1.0, moved=False, hs=0.0, locked=False)
        ntr = pending = 0
        def close_trade(px, xk):
            nonlocal ntr
            if st["locked"] and px * 0 == 0 and ((st["pos"] > 0 and px <= st["entry"] + lock[1] + 1e-9) or (st["pos"] < 0 and px >= st["entry"] - lock[1] - 1e-9)) and xk > st["ek"]: ntr = maxtr
            p = st["got"] + st["rem"] * (px - st["entry"]) * st["pos"] * PV - FEE
            out.append(dict(d=d, ek=st["ek"], xk=xk, pnl=p, mae=st["mae"] + TICK * PV, risk=hard * PV + FEE + 2 * TICK * PV, side=st["pos"])); st["pos"] = 0
        for k in range(nb):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                st.update(entry=o[k] + pending * TICK, pos=pending, ek=k, mae=0.0, got=0.0, rem=1.0, moved=False, locked=False); pending = 0
                st["hs"] = st["entry"] - st["pos"] * hard
            pos = st["pos"]
            if pos:
                e = st["entry"]
                st["mae"] = max(st["mae"], ((e - l[k]) if pos > 0 else (h[k] - e)) * PV)
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * TICK, k)
                elif scale and not st["moved"]:
                    ppx = e + pos * scale[1] * hard
                    if (pos > 0 and h[k] >= ppx + TICK) or (pos < 0 and l[k] <= ppx - TICK):
                        st["got"] += scale[0] * (ppx - e) * pos * PV; st["rem"] -= scale[0]; st["moved"] = True
                        st["hs"] = e + pos * (FEE / PV)
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


# ------------------------------------------------------------------------------------------------ account engine (plain per-trade replay; floats)
def day_table(trades):
    """trades df -> list of (date, [(pnl, mae, risk)...]) for every business day START..END (zero-trade days included)."""
    by = {}
    for r in trades.itertuples():
        by.setdefault(r.d, []).append((r.pnl, r.mae, r.risk))
    rng = pd.bdate_range(START, END)
    return [(d.strftime("%Y-%m-%d"), by.get(d.strftime("%Y-%m-%d"), [])) for d in rng]


# ------------------------------------------------------------------------------------------------ account engine
from types import SimpleNamespace as NS
sys.path[:0] = [ROOT + "/backend"]
from app.config import load_rules  # noqa: E402

PLANS = {"25K": "lucid_pro_25k", "50K": "lucid_pro_50k", "100K": "lucid_pro_100k", "150K": "lucid_pro_150k"}


def plan_rules(name):
    r = load_rules(__import__("pathlib").Path(f"{ROOT}/config/rules/{PLANS[name]}.yaml")).rules
    f, e, p = r.funded, r.eval, r.funded.payout
    fl = lambda x: None if x is None else float(x)
    return NS(
        start=float(r.account_size),
        f=NS(mll=fl(f.max_loss_limit), lt=fl(f.lock_trigger), ll=fl(f.lock_level), dll=fl(f.daily_loss_limit), split=fl(p.split), buffer=fl(p.buffer),
             minreq=fl(p.min_request), mincyc=fl(p.min_cycle_profit), maxfirst=fl(p.max_first), maxnext=fl(p.max_next), pct=fl(p.max_pct_of_profit),
             mpd=int(p.min_profitable_days), mdp=fl(p.min_day_profit), maxpay=p.max_payouts, cons=fl(f.consistency_max_day_pct), lockpay=bool(p.lock_mll_on_payout)),
        e=NS(target=fl(e.profit_target), mll=fl(e.max_loss_limit), lt=fl(e.lock_trigger), ll=fl(e.lock_level), dll=fl(e.daily_loss_limit),
             cons=fl(e.consistency_max_day_pct), mpd=int(e.min_profitable_days)),
    )


def _qty(cfg, bal, floor, mll, risk):
    q = cfg["q"]
    br = cfg.get("brake")
    if br and bal - floor < br[0] * mll: q = min(q, br[1])
    fit, kill = cfg.get("fit"), cfg.get("kill")
    cush = bal - floor
    if fit is None and kill is None: return q
    while q >= 1 and ((fit is not None and q * risk > fit * cush) or (kill is not None and cush - q * risk < kill)): q -= 1
    return q


def _day(trades, bal, floor, dll, cfg, mll):
    """one session -> (bal, bust, traded). trades = [(pnl, mae, risk)] at 1 micro in time order."""
    day = 0.0; dpk = 0.0; traded = False
    lock, dloss = cfg.get("dlock"), cfg.get("dloss")
    for pnl, mae, risk in trades:
        if lock is not None and day >= lock: break
        if dloss is not None and day <= -dloss: break
        q = _qty(cfg, bal, floor, mll, risk)
        if q < 1: continue
        traded = True
        worst = -max(mae, -pnl) if mae > 0 else min(pnl, 0)
        if bal + q * worst <= floor: return floor, True, True       # intraday breach of the (EOD-updated) floor
        p = pnl * q
        if dll is not None and day + p <= -dll: p = -dll - day
        bal += p; day += p
        if bal <= floor: return bal, True, True
        if dll is not None and day <= -dll: break
    return bal, False, traded


def _payout(r, bal, cyc, npaid):
    cp = sum(cyc)
    if cp < r.mincyc or cp <= 0: return 0.0
    if r.cons is not None and max(cyc) > r.cons / 100 * cp: return 0.0
    if r.mpd and sum(1 for x in cyc if x >= r.mdp) < r.mpd: return 0.0
    amt = bal - r.buffer
    if r.pct is not None: amt = min(amt, r.pct * cp)
    cap = r.maxfirst if npaid == 0 else r.maxnext
    if cap is not None: amt = min(amt, cap)
    return round(amt, 2) if amt >= r.minreq else 0.0


def funded_run(tab, R, cfg, cadence=10):
    """tab = list of per-day trade lists (1 micro). -> dict(paid (to trader), status BUST|MAX|OPEN, n, npay, first, frozen)
    frozen = account alive at the end with no trade taken in the last 40 sessions (the 'freeze' failure of the D57 rules)."""
    r = R.f
    bal = peak = R.start; floor = R.start - r.mll; cyc = []; paid = 0.0; pays = []; idle = 0
    for n, trades in enumerate(tab):
        b0 = bal
        bal, bust, traded = _day(trades, bal, floor, r.dll, cfg, r.mll)
        if bust: return dict(paid=paid, status="BUST", n=n + 1, npay=len(pays), first=pays[0] if pays else None, frozen=False)
        idle = 0 if traded else idle + 1
        if traded: cyc.append(bal - b0)
        peak = max(peak, bal)
        floor = r.ll if peak >= r.lt else max(floor, peak - r.mll)
        if (n + 1) % cadence == 0 and (r.maxpay is None or len(pays) < r.maxpay):
            amt = _payout(r, bal, cyc, len(pays))
            if amt > 0:
                bal -= amt; paid += amt * r.split; pays.append(n + 1); cyc = []
                if r.lockpay: floor = max(floor, r.ll)
        if r.maxpay is not None and len(pays) >= r.maxpay:
            return dict(paid=paid, status="MAX", n=n + 1, npay=len(pays), first=pays[0], frozen=False)
    return dict(paid=paid, status="OPEN", n=len(tab), npay=len(pays), first=pays[0] if pays else None, frozen=idle >= 40)


def eval_run(tab, R, cfg, horizon=120):
    """-> (PASS|BUST|OPEN, sessions)."""
    e = R.e
    bal = peak = R.start; floor = R.start - e.mll; pos = []
    for n, trades in enumerate(tab[:horizon]):
        b0 = bal
        bal, bust, traded = _day(trades, bal, floor, e.dll, cfg, e.mll)
        if bust: return "BUST", n + 1
        if traded: pos.append(bal - b0)
        peak = max(peak, bal)
        floor = e.ll if peak >= e.lt else max(floor, peak - e.mll)
        prof = bal - R.start
        if prof >= e.target and sum(1 for x in pos if x > 0) >= e.mpd and (e.cons is None or max(pos, default=0) <= e.cons / 100 * prof):
            return "PASS", n + 1
    return "OPEN", min(horizon, len(tab))


def era_starts(tab, length, step=2):
    """start indexes by era: 'IS' windows end by 2023-12-31, 'HO' windows start 2024-01-01 or later, 'ALL' every start."""
    dates = [d for d, _ in tab]
    i_split = next(i for i, d in enumerate(dates) if d > SPLIT)
    n = len(tab)
    allr = list(range(0, max(1, n - length), step))
    return dict(ALL=allr, IS=[i for i in allr if i + length <= i_split], HO=[i for i in allr if i >= i_split])


def funded_stats(tab, R, cfg, era="ALL", horizon=260, cadence=10, step=2):
    days_ = [t for _, t in tab]
    idx = era_starts(tab, horizon, step)[era]
    res = [funded_run(days_[i:i + horizon], R, cfg, cadence) for i in idx]
    n = len(res)
    per2w = float(np.mean([x["paid"] for x in res])) / (horizon / 10) if n else float("nan")
    return dict(n=n, bust=100 * sum(x["status"] == "BUST" for x in res) / n, any_pay=100 * sum(x["npay"] > 0 for x in res) / n,
                frozen=100 * sum(x["frozen"] for x in res) / n, per2w=per2w, year=per2w * 26,
                year_median=float(np.median([x["paid"] for x in res])), npay=float(np.mean([x["npay"] for x in res])))


def eval_stats(tab, R, cfg, era="ALL", horizon=120, step=2):
    days_ = [t for _, t in tab]
    idx = era_starts(tab, horizon, step)[era]
    res = [eval_run(days_[i:i + horizon], R, cfg, horizon) for i in idx]
    n = len(res)
    ps = [s for o, s in res if o == "PASS"]
    return dict(n=n, pass_=100 * sum(o == "PASS" for o, _ in res) / n, bust=100 * sum(o == "BUST" for o, _ in res) / n,
                open_=100 * sum(o == "OPEN" for o, _ in res) / n, med_sessions=float(np.median(ps)) if ps else float("nan"))


def stream_stats(t, era="ALL"):
    """win rate / PF / profit / trades per year / max closed-trade drawdown for a trades df (1 micro)."""
    if era == "IS": t = t[t.d <= SPLIT]
    elif era == "HO": t = t[t.d > SPLIT]
    if not len(t): return dict(n=0, win=float("nan"), pf=float("nan"), profit=0.0, per_year=0.0, maxdd=0.0)
    w = t.pnl > 0
    gl = -t.pnl[~w].sum()
    yrs = (pd.Timestamp(t.d.max()) - pd.Timestamp(t.d.min())).days / 365.25
    yrs = {"IS": 2.17, "HO": 2.83, "ALL": 5.0}[era]
    cum = t.pnl.cumsum().values
    dd = float(np.max(np.maximum.accumulate(np.concatenate([[0], cum])) - np.concatenate([[0], cum])))
    return dict(n=len(t), win=100 * w.mean(), pf=(t.pnl[w].sum() / gl) if gl > 0 else float("inf"), profit=float(t.pnl.sum()), per_year=len(t) / yrs, maxdd=dd)
