"""Pass-faster study: shared library (research only, nothing in backend/app is changed).

One account simulator for NOISE alone and for NOISE + CANDACE / NOISE + CONTI VWAP on the SAME account.
 - NOISE sizing / room check / D57 shrink / brake / kill-by-MAE / STUCK rule = session-21 sim2.py (copied logic; validated to
   reproduce sim2 exactly in NOISE-only mode, see validate.py).
 - CANDACE / CONTI VWAP sizing = the controller's Lucid fit (lucid_fit.trade_risk_usd + contracts_for, CANDACE also the grade rule),
   re-implemented in floats (validated against the Decimal functions in validate.py).
 - All strategies share: balance, trailing EOD MLL + lock, DLL incl. LucidScale (NOISE: sim2 reading, fit strategies: D18 dll_remaining),
   40 % consistency + 38 % day stop (a trade is capped at the day stop and the day ends), kill distance, room check, max ONE position per
   account (a signal whose entry minute is <= the exit minute of the open position is skipped), flat by close (streams already are).
"""
import sys, os, math, pickle, glob
import numpy as np, pandas as pd, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
sys.path.insert(0, WT + "/backend")
sys.path.insert(0, WT + "/docs/results/session21/pro_rules")
sys.path.insert(0, WT + "/docs/results/new_strategies")
import sim as S21
S21.R = WT + "/"
import backtest_new as B                       # plan(), cost1()  (sets nothing else)
from app.config import load_rules
from app.engine.candace_ict import GRADE_MULT

SHRINK = 0.6; MINPCT = 0.002; TV = 0.5; FEE = 1.0; SLIP = 1; PV = 2.0
WIN = {  # (first day, last day)
    "ALL": ("2021-10-21", "2026-10-30"),
    "PICK": ("2021-10-21", "2023-12-31"),
    "JUDGE": ("2024-01-01", "2026-10-30"),
    "L12": ("2025-11-06", "2026-10-30"),
    "IS": ("2021-10-21", "2025-11-05"),
}
STRAT_N, STRAT_C, STRAT_V = 0, 1, 2


def trading_days():
    D, _ = pickle.load(open(PKL, "rb"))
    return [d for d, _a in D], {d: a["open"] for d, a in D}


def smin(entry):
    pt = math.ceil(MINPCT * entry / 0.25 - 1e-9)
    return pt * TV + FEE + TV


def load_plans():
    P = S21.load_plans()
    out = {}
    for k in (25, 50):
        nm = f"lucid_pro_{k}k"; p = dict(P[nm]); b = B.plan(k)
        r = load_rules(__import__("pathlib").Path(WT + f"/config/rules/{nm}.yaml")).rules
        c = r.strategy.candace_ict_cfg
        assert abs(float(b["day_stop"]) - (p["cons"] - p["buf"]) / 100 * p["target"]) < 1e-9
        p.update(k=k, tick=float(b["tick"]), tv=float(b["tv"]), fee=float(b["fee"]), slip=int(b["slip"]), cap_trade=float(b["cap_trade"]),
                 maxmicros=int(b["maxmicros"]), cost=float(B.cost1(b)), day_stop=float(b["day_stop"]),
                 fitC=(float(c.risk_pct_of_drawdown), float(c.dll_use_pct), int(c.max_losses_per_day)),
                 fitV=tuple(float(x) for x in b["fit"]["VWAP"]), row=p["tabs"]["regular"])
        out[k] = p
    return out


# ---------------------------------------------------------------------------------------------------------------- streams
def load_streams():
    t = pd.read_csv(HERE + "/streams_noise_base.csv"); t80 = pd.read_csv(HERE + "/streams_noise_lock80.csv")
    c = pd.read_csv(HERE + "/streams_candace.csv"); v = pd.read_csv(HERE + "/streams_vwap.csv")
    _, op = trading_days()
    for df in (t, t80):
        df["entry"] = [float(op[d][int(k)]) for d, k in zip(df.d, df.ek)]
    return t, t80, c, v


def build_table(n_df=None, c_df=None, v_df=None):
    """date -> list of trade tuples sorted by entry minute: (m_in, m_out, kind, a, b, c, d)
    N: (ek, xk+.5, 0, pnl, mae, risk, entry)  C: (idx, exit_idx, 1, pts, stop_pts, grade_mult, 0)  V: (idx, exit_idx, 2, pts, 25, 2.0, 0)"""
    by = {}
    if n_df is not None:
        for r in n_df.itertuples():
            by.setdefault(r.d, []).append((float(r.ek), float(r.xk) + 0.5, STRAT_N, float(r.pnl), float(r.mae), float(r.risk), float(r.entry)))
    if c_df is not None:
        for r in c_df.itertuples():
            by.setdefault(r.day, []).append((float(r.idx), float(r.exit_idx), STRAT_C, float(r.p1), float(r.stop_pts), float(GRADE_MULT[r.grade]), 0.0))
    if v_df is not None:
        for r in v_df.itertuples():
            by.setdefault(r.day, []).append((float(r.idx), float(r.exit_idx), STRAT_V, float(r.pts), float(r.stop_pts), 2.0, 0.0))
    for d in by:
        by[d].sort(key=lambda x: (x[0], x[2]))
    return by


# ---------------------------------------------------------------------------------------------------------------- fit sizing (floats)
def fit_contracts(p, fit, stop_pts, gmult, left, room, day_cap=None):
    rp, up, n = fit
    parts = [rp * p["mll"], max(room, 0.0) / n, p["cap_trade"], p["day_stop"] / n]
    if left is not None:
        parts.append(max(left, 0.0) * up / n)
    risk = math.floor(min(parts) * 100 + 1e-7) / 100
    per = stop_pts / p["tick"] * p["tv"] + p["fee"] + 2 * p["slip"] * p["tv"]
    c = int(risk // per)
    c = min(c, p["maxmicros"])
    if gmult is not None and gmult < 2.0:      # grade rule (grade_contracts, top = 2): CANDACE B / C
        c = min(c, int(c * gmult / 2.0 + 1e-9))
    return c


# ---------------------------------------------------------------------------------------------------------------- account simulation
def simulate(days, idx, p, gmin, ref_stops=None, cnt=None, maxs=100000, stuck_mix=False):
    """days: list indexed by day number of trade-tuple lists; idx: sequence of day numbers. Returns (outcome, sessions).
    ref_stops = {STRAT_C: stop, STRAT_V: stop} of the fit strategies present in the mix.
    stuck_mix=False (primary, = baseline definition): the account is STUCK as soon as NOISE can no longer be sized (0.6 x room < D57 min stop),
    whatever the other strategy could still do. stuck_mix=True (sensitivity): not stuck while a fit strategy could still size >= 1 micro."""
    kd = p["kill"]; mg = p["margin"]; size = p["size"]
    bal = size; floor = bal - p["mll"]; peak = bal; locked = False; mll = p["mll"]
    dll0 = p["dll"]; pdays = 0; best = 0.0; s = 0; peak_e = bal
    dstop = (p["cons"] - p["buf"]) / 100 * p["target"]
    row = p["row"]; cn = row["contracts"]; bb = row.get("brake_below"); bc = row.get("brake_contracts")
    fitmix = ref_stops is not None and stuck_mix
    for di in idx:
        s += 1
        if s > maxs: break
        tl = days[di]
        today = 0.0; stop = False; peak_day = 0.0; free = -1.0; last = -1
        dll = dll0
        if p["scale"] and locked: dll = 0.6 * (peak_e - size)
        for (m_in, m_out, kind, a, b, c, d) in tl:
            if stop: break
            if m_in <= free and not (kind == STRAT_N and last == STRAT_N):   # NOISE's own flip on the same bar is its own rule
                if cnt is not None: cnt["skip_open"][kind] += 1
                continue
            if kind == STRAT_N:
                pnl, mae, risk, entry = a, b, c, d
                q = cn
                if bb is not None and (bal - floor) / mll < bb: q = bc
                if bal - floor <= kd:
                    if not fitmix or not _fit_can(p, ref_stops, bal, floor, today, dll, peak_day): return "stuck", s
                    continue
                room0 = bal - floor - kd
                if dll: room0 = min(room0, dll + today)
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
                    if SHRINK * (bal - floor - kd) < gmin:
                        if not fitmix or not _fit_can(p, ref_stops, bal, floor, today, dll, peak_day): return "stuck", s
                    if cnt is not None: cnt["size0"][kind] += 1
                    continue
                pq = q * pp; dead = False
                if q * eff_mae >= bal - floor - kd:
                    pq = -(bal - floor - kd); dead = True
            else:
                fit = p["fitC"] if kind == STRAT_C else p["fitV"]
                left = None
                if dll:
                    left = dll - (max(0.0, peak_day, today) - today)
                    if left <= 0: stop = True; break
                room = (bal + today) - floor - kd
                q = fit_contracts(p, fit, b, c if kind == STRAT_C else None, left, room)
                if q < 1:
                    if cnt is not None: cnt["size0"][kind] += 1
                    continue
                pq = q * (a * PV - p["cost"]); dead = False
            free = m_out; last = kind
            if cnt is not None: cnt["taken"][kind] += 1
            if dll and today + pq <= -dll: pq = -dll - today; stop = True
            if today + pq > dstop: pq = dstop - today; stop = True
            today += pq; bal += pq; peak_day = max(peak_day, today)
            if dead: return "bust", s
            if bal <= floor + kd: return "bust", s
        if today > 0: pdays += 1; best = max(best, today)
        peak_e = max(peak_e, bal)
        if bal > peak and not locked:
            peak = bal
            if peak >= p["lock_trig"]: locked = True; floor = p["lock_lvl"]
            else: floor = peak - mll
        prof = bal - size
        if prof >= p["target"] and pdays >= p["mpd"] and (not p["cons"] or best <= p["cons"] / 100 * prof): return "pass", s
        if fitmix and SHRINK * (bal - floor - kd) < gmin and not _fit_can(p, ref_stops, bal, floor, 0.0, dll, 0.0): return "stuck", s
    return "open", s


def _fit_can(p, ref_stops, bal, floor, today, dll, peak_day):
    """can any fit strategy of the mix still size >= 1 micro (reference stop, grade top)?"""
    room = (bal + today) - floor - p["kill"]
    left = None if not dll else dll - (max(0.0, peak_day, today) - today)
    if left is not None and left <= 0: return False
    for kind, st in ref_stops.items():
        fit = p["fitC"] if kind == STRAT_C else p["fitV"]
        if fit_contracts(p, fit, st, None, left, room) >= 1: return True
    return False


# ---------------------------------------------------------------------------------------------------------------- run protocols
def bdays(win):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(*WIN[win])]


def day_lists(by, dates):
    return [by.get(d, []) for d in dates]


def boot_paths(L, paths=600, cap=400, block=10, seed=7):
    rnd = np.random.default_rng(seed); out = []
    for _ in range(paths):
        pth = []
        while len(pth) < cap:
            i = int(rnd.integers(0, L)); pth.extend(range(i, min(i + block, L)))
        out.append(np.array(pth[:cap]))
    return out


def summarize(res):
    n = len(res); ps = sorted(s for o, s in res if o == "pass")
    cnt = {k: sum(1 for o, _ in res if o == k) for k in ("pass", "bust", "stuck", "open")}
    return dict(n=n, pass_=100 * cnt["pass"] / n, bust=100 * cnt["bust"] / n, stuck=100 * cnt["stuck"] / n, bust_all=100 * (cnt["bust"] + cnt["stuck"]) / n,
                run=100 * cnt["open"] / n, p60=100 * sum(1 for x in ps if x <= 60) / n, med=float(np.median(ps)) if ps else None, p75=float(np.percentile(ps, 75)) if ps else None, npass=len(ps))


def run_boot(by, win, p, gmin, ref_stops=None, maxs=400, stuck_mix=False):
    days = day_lists(by, bdays(win)); paths = boot_paths(len(days))
    return summarize([simulate(days, pth, p, gmin, ref_stops, maxs=maxs, stuck_mix=stuck_mix) for pth in paths])


def run_roll(by, win, p, gmin, dates_all, ref_stops=None, stuck_mix=False):
    """rolling start on every trading day of the window; each run uses only the days of the window (start .. window end)."""
    a, b = WIN[win]
    dates = [d for d in dates_all if a <= d <= b]
    days = day_lists(by, dates); L = len(days)
    res = [simulate(days, range(s, L), p, gmin, ref_stops, stuck_mix=stuck_mix) for s in range(L)]
    out = summarize(res); out["detail"] = [[dates[i], o, s] for i, (o, s) in enumerate(res)]
    return out


# ---------------------------------------------------------------------------------------------------------------- static totals
def static_stats(by, win, p, dates_all, mix, ref_cnt=True):
    """fresh-account static replay (no balance dependence): one position at a time, 1-micro and plan-sized totals, drawdown, counts.
    Plan sizing: NOISE = size-table contracts (no brake / shrink), CANDACE & VWAP = full-room Lucid fit incl. grade rule."""
    a, b = WIN[win]; dates = [d for d in dates_all if a <= d <= b]
    out = dict(t1=0.0, tp=0.0, ndays=len(dates), taken={0: 0, 1: 0, 2: 0}, sig={0: 0, 1: 0, 2: 0}, skip_open={0: 0, 1: 0, 2: 0}, skip_other={0: 0, 1: 0, 2: 0}, size0={0: 0, 1: 0, 2: 0})
    eq1 = eqp = pk1 = pkp = dd1 = ddp = 0.0; cn = p["row"]["contracts"]
    for d in dates:
        free = -1.0; free1 = -1.0; last = last1 = -1
        for (m_in, m_out, kind, x, y, z, w) in by.get(d, []):
            out["sig"][kind] += 1
            u1 = x if kind == 0 else x * PV - p["cost"]
            if not (m_in <= free1 and not (kind == 0 and last1 == 0)):   # 1-micro stream: every signal counts as taken
                free1 = m_out; last1 = kind; eq1 += u1; pk1 = max(pk1, eq1); dd1 = max(dd1, pk1 - eq1)
            if m_in <= free and not (kind == 0 and last == 0):
                out["skip_open"][kind] += 1
                if last != kind: out["skip_other"][kind] += 1
                continue
            if kind == 0: q = cn
            else: q = fit_contracts(p, p["fitC"] if kind == 1 else p["fitV"], y, z if kind == 1 else None, p["dll"], p["mll"])
            if q < 1: out["size0"][kind] += 1; continue
            free = m_out; last = kind; out["taken"][kind] += 1
            eqp += q * u1; pkp = max(pkp, eqp); ddp = max(ddp, pkp - eqp)
    out.update(t1=eq1, tp=eqp, dd1=dd1, ddp=ddp)
    return out
