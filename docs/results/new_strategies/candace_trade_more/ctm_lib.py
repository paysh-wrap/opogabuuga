"""CANDACE ICT SCALP, "why so few trades / how to trade more" study: library (data, engine mirror, offline management
variants D4 / D5 / C4, Lucid sizing and eval sim, stats). NO app code is changed; the engine is called unchanged
(`candace_ict.replay_day`) and mirrored step by step (`run_day`, baseline flags assert-equal to the engine).
Run via run_ctm.py. Needs NS_CACHE (own scratch path) and the days.pkl path as argv[1].
"""
import sys, os, math, statistics
from collections import defaultdict
from datetime import timedelta, time as dtime
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
NS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, NS)
import backtest_new as B  # loader / build / plan / cost (sets sys.path to this worktree's backend)
from app.config import CandaceIctCfg, load_rules
from app.engine import candace_ict as CE
from app.engine.candace_ict import fvgs, hourly, pools, grade, rth_gap_levels, _session, GRADE_MULT, Fvg
from app.engine.trade_plan import Direction, round_to_tick
from app.engine.lucid_fit import contracts_for, trade_risk_usd, grade_contracts
from app.risk.checks import dll_remaining
from app.risk.lucid_scale import effective_dll

ET, TICK, PV = B.ET, B.TICK, B.PV
IS_END, J_START = "2023-12-31", "2024-01-01"
IS_START = "2021-10-01"
HIST_N = 3  # same history window as the existing CANDACE harness (3 prior days)
BUILT = None  # set before forking


def mi(t):
    t = t.astimezone(ET)
    return (t.hour - 9) * 60 + t.minute - 30


# ----------------------------------------------------------------------------------------------------------------
# mirror of candace_ict.replay_day with (a) stage tracking, (b) optional offline D4 / D5 / C4
# ----------------------------------------------------------------------------------------------------------------
STAGES = ["C1", "C2", "C5", "C3", "A2", "D2", "TRADE"]


def stage_of(ep):
    if ep["trade"]:
        return "TRADE"
    if ep["d2fail"]:
        return "D2"
    if ep["a2fail"]:
        return "A2"
    if ep["ifvg"]:
        return "C3"
    if ep["through"]:
        return "C5"
    if ep["fvg"]:
        return "C2"
    return "C1"


def _swing_levels(bars, k=2):
    """minor 2-bar swing highs / lows of the bars known so far (confirmed: k bars on each side)."""
    hs, ls = [], []
    for i in range(k, len(bars) - k):
        nb = [bars[j] for j in range(i - k, i + k + 1) if j != i]
        if all(bars[i].h > x.h for x in nb):
            hs.append(bars[i].h)
        if all(bars[i].l < x.l for x in nb):
            ls.append(bars[i].l)
    return hs, ls


def partial_level(bars_known, entry, tp, s):
    """D4: nearest internal liquidity between entry and target: minor 2-bar swing high (long) / low (short) or the
    near edge of a 1-minute FVG lying between entry and target (long: FVG low above entry; short: FVG high below)."""
    hs, ls = _swing_levels(bars_known)
    cands = []
    if s > 0:
        cands += [h for h in hs if entry < h < tp]
        cands += [f.lo for f in fvgs(bars_known) if entry < f.lo < tp]
        return min(cands) if cands else None
    cands += [l for l in ls if tp < l < entry]
    cands += [f.hi for f in fvgs(bars_known) if tp < f.hi < entry]
    return max(cands) if cands else None


def run_day(hist, today, cfg, tick, d4=False, d5=False, c4=False):
    """Returns dict(signals=[trade dict], episodes=[episode dict], flags). With d4=d5=c4=False it must equal the engine."""
    res = dict(signals=[], episodes=[], had_break=False, n_bars=0, loss_cap=False, pos_blocked_sweeps=0)
    if not today:
        return res
    d = today[-1].close_time.astimezone(ET).date()
    bars = sorted((b for b in today if b.close_time.astimezone(ET).date() == d), key=lambda b: b.close_time)
    prior = [b for b in hist if b.close_time.astimezone(ET).date() < d]
    pdays = sorted({b.close_time.astimezone(ET).date() for b in prior})
    prev = [b for b in prior if pdays and b.close_time.astimezone(ET).date() == pdays[-1]]
    prev_rth = [b for b in prev if dtime(9, 30) < b.close_time.astimezone(ET).time() <= dtime(16, 0)]
    first_rth = next((b for b in bars if b.close_time.astimezone(ET).time() == dtime(9, 31)), None)
    gap_levels = rth_gap_levels(prev_rth[-1].c if prev_rth else None, first_rth.o if first_rth else None)
    h1 = hourly([*prior[-60 * 24:], *bars])
    pos = None
    losses = 0
    swept_used = set()
    sweep = None
    ifvg = None
    ep = None
    D0 = D(0)

    def end_ep(why):
        nonlocal ep
        if ep is not None:
            ep["end"] = why
            ep["stage"] = stage_of(ep)
            res["episodes"].append(ep)
        ep = None

    for i, b in enumerate(bars):
        if pos is not None:
            closed = _step_pos(pos, b, d4, d5)
            if closed:
                x_px = pos["exit_price"]
                if (x_px - pos["entry"]) * pos["s"] < 0:
                    losses += 1
                _finish(res, pos, d)
                pos, sweep, ifvg = None, None, None
            else:
                # sweeps that happen while a position is open cannot be traded (max 1 position)
                pass
            continue
        sess = _session(b.close_time, cfg)
        if sess is None or losses >= cfg.max_losses_per_day:
            if sweep is not None:
                end_ep("WINDOW" if sess is None else "LOSSCAP")
            if sess is not None:
                res["loss_cap"] = True
            sweep = ifvg = None
            continue
        res["n_bars"] += 1
        before = bars[:i]
        h1_known = [x for x in h1 if x.close_time <= b.close_time]
        pl = pools(prev, before, h1_known, cfg, tick)
        new_sweep = False
        for p in pl:
            if (p.price, p.side) in swept_used:
                continue
            if (p.side > 0 and b.h > p.price > b.c) or (p.side < 0 and b.l < p.price < b.c):
                swept_used.add((p.price, p.side))
                if sweep is not None:
                    end_ep("REPLACED")
                sweep, ifvg = (i, p, b.h if p.side > 0 else b.l), None
                si0, sp0, ext0 = sweep
                sign0 = -sp0.side
                run0 = [f for f in fvgs(bars[max(0, si0 - cfg.fvg_lookback): si0 + 1]) if f.color == -sign0]
                ep = dict(day=str(d), idx=i, kind=sp0.kind, sign=sign0, fvg=bool(run0), through=False, ifvg=False,
                          a2fail=False, d2fail=False, trade=False, end=None, stage=None, ifvg_idx=None)
                new_sweep = True
                break
            # a bar that breaks a pool and CLOSES beyond it = a breakout, not a sweep
            if (p.side > 0 and b.c > p.price and b.h > p.price) or (p.side < 0 and b.c < p.price and b.l < p.price):
                res["had_break"] = True
        if sweep is None:
            continue
        si, sp, ext = sweep
        sign = -sp.side
        entry = None
        sig_conf0 = ["DISPLACEMENT"]
        if ifvg is None:
            run = [f for f in fvgs(bars[max(0, si - cfg.fvg_lookback): si + 1]) if f.color == -sign]
            if not run or i == si:
                continue
            f = run[-1]
            if c4:
                trig = (b.l <= f.hi) if sign < 0 else (b.h >= f.lo)
                if trig:
                    entry = (f.hi if b.o > f.hi else b.o) if sign < 0 else (f.lo if b.o < f.lo else b.o)
                    sig_conf0 = []
                    ep["ifvg"] = True  # "entry model reached" for the funnel
                elif i - si > cfg.ifvg_max_bars:
                    end_ep("TIMEOUT")
                    sweep = None
                    continue
                else:
                    continue
            else:
                body = abs(b.c - b.o)
                ref = bars[max(0, i - cfg.displacement_bars): i]
                avg = sum((abs(x.c - x.o) for x in ref), D0) / max(len(ref), 1)
                through = (b.c < f.lo and b.o > f.lo) if sign < 0 else (b.c > f.hi and b.o < f.hi)
                if through:
                    ep["through"] = True
                if through and body >= cfg.displacement_mult * avg:
                    ifvg = (i, f)
                    ep["ifvg"] = True
                    ep["ifvg_idx"] = i
                elif i - si > cfg.ifvg_max_bars:
                    end_ep("TIMEOUT")
                    sweep = None
                continue
        else:
            fi, f = ifvg
            if i - fi > cfg.ifvg_max_bars:
                end_ep("TIMEOUT")
                sweep = ifvg = None
                continue
            into = (b.h >= f.lo and b.c <= f.hi) if sign < 0 else (b.l <= f.hi and b.c >= f.lo)
            if not into:
                continue
            entry = b.c
        # ---- common entry checks (A2, D1/D2, D3) ----
        rng = bars[max(0, i - cfg.range_bars): i + 1]
        lo, hi = min(x.l for x in rng), max(x.h for x in rng)
        mid = lo + cfg.premium_pct * (hi - lo)
        if (sign < 0 and entry < mid) or (sign > 0 and entry > mid):
            ep["a2fail"] = True
            end_ep("A2")
            sweep = ifvg = None
            continue
        stop = round_to_tick(ext - sign * cfg.stop_buffer_ticks * tick, tick, away_from=entry)
        risk = (entry - stop) * sign
        cap = cfg.ny_max_stop_pts if sess == "NY" else cfg.london_max_stop_pts
        if risk <= 0 or risk > cap:
            ep["d2fail"] = True
            end_ep("D2")
            sweep = ifvg = None
            continue
        min_tp = entry + sign * cfg.min_rr * risk
        ahead = [p.price for p in pl if p.side == sign and (p.price - min_tp) * sign >= 0]
        tp_raw = min(ahead, key=lambda x: abs(x - entry)) if ahead else min_tp
        tp = round_to_tick(tp_raw, tick, toward=entry)
        if (tp - entry) * sign < cfg.min_rr * risk:
            tp = round_to_tick(min_tp, tick, away_from=entry)
        extended = bool(ahead)
        conf = list(sig_conf0)
        if sp.kind == "EQUAL":
            conf.append("EQUAL_POOL")
        if sp.kind == "FVG1H" or any(p.kind == "FVG1H" and abs(p.price - ext) <= cfg.gap_level_tol_pts for p in pl):
            conf.append("HTF_FVG")
        if any(abs(g - ext) <= cfg.gap_level_tol_pts or abs(g - entry) <= cfg.gap_level_tol_pts for g in gap_levels):
            conf.append("RTH_GAP")
        if sp.kind in ("PDH", "PDL"):
            conf.append("PREV_DAY")
        hold = cfg.ny_max_hold_minutes if sess == "NY" else cfg.london_max_hold_minutes
        until = b.close_time + timedelta(minutes=hold)
        plevel = partial_level(bars[: i + 1], entry, tp, sign) if d4 else None
        pos = dict(time=b.close_time, s=sign, entry=entry, stop=stop, stop0=stop, tp=tp, hold_until=until, conf=conf,
                   grade=grade(len(conf), cfg), swept=sp, plevel=plevel, pdone=False, pA=None, armed=False,
                   outcome="OPEN", exit_time=None, exit_price=None, risk=risk, extended=extended, sess=sess,
                   si=si, fi=(ifvg[0] if ifvg else None), c4=c4, i=i)
        ep["trade"] = True
        end_ep("TRADE")
        if c4:  # the entry bar itself: only the stop is checked (conservative: the bar's extreme may have come after the fill)
            if (b.h >= stop) if sign < 0 else (b.l <= stop):
                pos["outcome"], pos["exit_time"], pos["exit_price"] = "STOP", b.close_time, stop
                losses += 1
                _finish(res, pos, d)
                pos, sweep, ifvg = None, None, None
    if ep is not None:
        end_ep("WINDOW")
    if pos is not None:  # still open at the last bar: marked to market (cannot happen with <= 120 min windows + 15 min hold)
        pos["outcome"], pos["exit_time"], pos["exit_price"] = "MTM", None, bars[-1].c
        _finish(res, pos, d)
    return res


def _step_pos(p, b, d4, d5):
    """Same order as the engine's _step (stop first, then target, then time); D4 partial and D5 break-even added."""
    s = p["s"]
    stop_hit = (b.l <= p["stop"]) if s > 0 else (b.h >= p["stop"])
    if stop_hit:
        p["outcome"] = "STOP" if p["stop"] == p["stop0"] else "BE"
        p["exit_time"], p["exit_price"] = b.close_time, p["stop"]
        return True
    pl = p["plevel"]
    if pl is not None and not p["pdone"] and ((b.h >= pl) if s > 0 else (b.l <= pl)):
        p["pdone"] = True
        p["pA"] = float((pl - p["entry"]) * s)
    if (b.h >= p["tp"]) if s > 0 else (b.l <= p["tp"]):
        p["outcome"], p["exit_time"], p["exit_price"] = "TP", b.close_time, p["tp"]
        return True
    if b.close_time >= p["hold_until"]:
        p["outcome"], p["exit_time"], p["exit_price"] = "TIME", b.close_time, b.c
        return True
    if d5 and not p["armed"]:
        fav = (b.h - p["entry"]) if s > 0 else (p["entry"] - b.l)
        if fav >= D("0.25") * abs(p["tp"] - p["entry"]):
            p["armed"] = True
            p["stop"] = p["entry"]  # break-even from the NEXT bar on
    return False


def _finish(res, p, d):
    s = p["s"]
    pts = float((p["exit_price"] - p["entry"]) * s)
    if p["pA"] is not None:  # D4 partial booked: leg A at the level, leg B (runner) at the final exit
        pA, pB = p["pA"], pts
        p1 = pB
        blend = 0.5 * (pA + pB)
        partial = True
    else:
        pA = pB = p1 = blend = pts
        partial = False
    p["trade"] = dict(
        day=str(d), time=p["time"].astimezone(ET).strftime("%H:%M"), idx=mi(p["time"]),
        exit_idx=mi(p["exit_time"]) if p["exit_time"] is not None else 390,
        dir="LONG" if s > 0 else "SHORT", entry=float(p["entry"]), stop=float(p["stop0"]),
        tp=float(p["tp"]), stop_pts=float(p["risk"]), tp_pts=float((p["tp"] - p["entry"]) * s),
        exit_price=float(p["exit_price"]), outcome=p["outcome"], grade=p["grade"], nconf=len(p["conf"]),
        conf="+".join(p["conf"]), swept=p["swept"].kind, pts=pts, pA=pA, pB=pB, p1=p1, pts1m=blend, partial=partial,
        extended=p["extended"], sess_idx=p["i"], sweep_idx=p["si"], ifvg_idx=p["fi"] if p["fi"] is not None else -1)
    res["signals"].append(p["trade"])


def trades_of(res):
    return res["signals"]


def engine_trades(hist, today, cfg, tick):
    """Engine called UNCHANGED -> trade dicts in the same shape."""
    out = []
    r = CE.replay_day(hist, today, cfg, tick)
    d = today[-1].close_time.astimezone(ET).date()
    for s in r.signals:
        sg = s.direction.sign
        if s.outcome == "OPEN" or s.exit_price is None:
            xp, et, oc = today[-1].c, None, "MTM"
        else:
            xp, et, oc = s.exit_price, s.exit_time, s.outcome
        pts = float((xp - s.entry) * sg)
        risk = abs(s.entry - s.stop)
        out.append(dict(day=str(d), time=s.time.astimezone(ET).strftime("%H:%M"), idx=mi(s.time),
                        exit_idx=mi(et) if et is not None else 390, dir=s.direction.name, entry=float(s.entry),
                        stop=float(s.stop), tp=float(s.take_profit), stop_pts=float(risk),
                        tp_pts=float((s.take_profit - s.entry) * sg), exit_price=float(xp), outcome=oc, grade=s.grade,
                        nconf=len(s.confluences), conf="+".join(s.confluences), swept=s.swept.kind, pts=pts, pA=pts,
                        pB=pts, p1=pts, pts1m=pts, partial=False, extended=False, sess_idx=-1, sweep_idx=-1, ifvg_idx=-1))
    return out


KEYS = ("day", "time", "dir", "entry", "stop", "tp", "exit_idx", "exit_price", "outcome", "grade", "conf")


def same(a, b):
    return [tuple(x[k] for k in KEYS) for x in a] == [tuple(x[k] for k in KEYS) for x in b]


# ----------------------------------------------------------------------------------------------------------------
# parallel day runners
# ----------------------------------------------------------------------------------------------------------------
def _hist(i):
    return [b for x in BUILT[max(0, i - HIST_N): i] for b in x[2]]


def _job(args):
    lo, hi, cfgd, flags, mode = args
    cfg = CandaceIctCfg(**cfgd)
    out = []
    for i in range(lo, hi):
        ds, gb, mb = BUILT[i]
        h = _hist(i)
        if mode == "engine":
            out.append((ds, engine_trades(h, mb, cfg, TICK), None))
        else:
            r = run_day(h, mb, cfg, TICK, *flags)
            out.append((ds, trades_of(r), r))
    return out


def run_all(cfgd, flags=(False, False, False), mode="mirror", pool=None):
    """-> list of (ds, trades, mirror-result or None) in day order."""
    n = len(BUILT)
    step = 40
    jobs = [(a, min(a + step, n), cfgd, flags, mode) for a in range(0, n, step)]
    parts = pool.map(_job, jobs) if pool else [_job(j) for j in jobs]
    return [x for p in parts for x in p]


# ----------------------------------------------------------------------------------------------------------------
# sizing, P&L, eval sim, stats
# ----------------------------------------------------------------------------------------------------------------
PLANS = {}
RISKCFG = {}


def load_plans():
    for k in (25, 50, 100, 150):
        PLANS[k] = B.plan(k)
        st = load_rules(B.Path(B.ROOT) / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules.strategy.candace_ict_cfg
        RISKCFG[k] = (st.risk_pct_of_drawdown, st.dll_use_pct, st.max_losses_per_day)
    return PLANS


class Variant:
    """sizing variant: grade thresholds (a_min, b_min) and the grade floor (C / B get >= 1 micro when the full fit >= 1)."""

    def __init__(self, name="base", a_min=4, b_min=3, floor=False):
        self.name, self.a_min, self.b_min, self.floor = name, a_min, b_min, floor

    def grade(self, t):
        n = t["nconf"]
        return "A+" if n >= self.a_min else "B" if n >= self.b_min else "C"

    def size(self, t, c_full):
        c = grade_contracts(c_full, GRADE_MULT[self.grade(t)])
        if self.floor and c_full >= 1:
            c = max(c, 1)
        return c


BASEV = Variant()


def pnl_usd(t, c, cost):
    if t["partial"] and c >= 2:
        a = c // 2
        return (a * t["pA"] + (c - a) * t["pB"]) * PV - c * cost
    return c * (t["p1"] * PV - cost)


def full_fit(p, rcfg, t, left, room):
    rp, up, n = rcfg
    r = trade_risk_usd(p["mll"], rp, n, left, up, room, p["cap_trade"], p["day_stop"])
    return min(contracts_for(r, D(str(t["stop_pts"])), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"])


def fit_static(k, trades, var, cost):
    """static Lucid-fit (full DLL and MLL room, no day stop), as the existing harness: n sized, total $, max DD $."""
    p, rc = PLANS[k], RISKCFG[k]
    eq = peak = dd = 0.0
    n = 0
    zero = 0
    for t in trades:
        c = var.size(t, full_fit(p, rc, t, D(p["dll"]) if p["dll"] is not None else None, p["mll"]))
        if c < 1:
            zero += 1
            continue
        n += 1
        eq += pnl_usd(t, c, cost)
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dict(n=n, zero=zero, total=eq, mdd=dd)


def eval_run(p, rc, var, tdays, start_i, cost, ndays):
    """tdays = [(day_index, [trades sorted by idx])] for days with trades only (a day without trades cannot change the
    state: peak / lock / MLL / profit stay, so it is skipped without changing any result). Same rules as the harness:
    EOD trailing MLL with lock, DLL (effective_dll), 40% consistency + day stop, kill distance, 1 position, size shrinks
    with MLL room."""
    S = p["S"]
    bal = S
    peak = S
    locked = False
    mllv = S - p["mll"]
    big = None
    pdays = 0
    for di, tl in tdays:
        if di < start_i:
            continue
        pnl_day = D(0)
        peak_day = D(0)
        free = -1
        stopped = False
        dll = effective_dll(p["dll"], p["scale"], locked, peak, S)
        for t in tl:
            if stopped:
                break
            if t["idx"] <= free:
                continue
            left = dll_remaining(dll, pnl_day, peak_day) if dll is not None else None
            if left is not None and left <= 0:
                stopped = True
                break
            c = var.size(t, full_fit(p, rc, t, left, (bal + pnl_day) - mllv - p["kill"]))
            if c < 1:
                continue
            free = max(t["exit_idx"], t["idx"])
            pnl_day += D(str(round(pnl_usd(t, c, cost), 2)))
            peak_day = max(peak_day, pnl_day)
            if (bal + pnl_day) <= mllv:
                return "BUST"
            if pnl_day >= p["day_stop"]:
                stopped = True
        bal += pnl_day
        big = pnl_day if big is None else max(big, pnl_day)
        pdays += pnl_day > 0
        peak = max(peak, bal)
        if not locked and peak >= p["lt"]:
            locked = True
        mllv = p["ll"] if locked else peak - p["mll"]
        prof = bal - S
        if prof >= p["target"]:
            if big <= p["cons"] / 100 * prof and pdays >= p["mind"]:
                return "PASS"
    return "RUNNING"


def eval_stats(k, trades, var, daylist, lo, hi, cost):
    """rolling start on every trading day in [lo, hi]; the run uses only days in [lo, hi] (no look into the other period)."""
    p, rc = PLANS[k], RISKCFG[k]
    days = [d for d in daylist if lo <= d <= hi]
    di = {d: i for i, d in enumerate(days)}
    by = defaultdict(list)
    for t in trades:
        if t["day"] in di:
            by[t["day"]].append(t)
    tdays = sorted((di[d], sorted(v, key=lambda t: t["idx"])) for d, v in by.items())
    tdi = [x[0] for x in tdays]
    cnt = {"PASS": 0, "BUST": 0, "RUNNING": 0}
    n = len(days)
    # starts on a no-trade day behave exactly like a start on the next trade day
    import bisect
    cache = {}
    for s in range(n):
        j = bisect.bisect_left(tdi, s)
        key = tdi[j] if j < len(tdi) else None
        if key not in cache:
            cache[key] = "RUNNING" if key is None else eval_run(p, rc, var, tdays, key, cost, n)
        cnt[cache[key]] += 1
    return dict(starts=n, pas=100 * cnt["PASS"] / n if n else 0, bust=100 * cnt["BUST"] / n if n else 0,
                run=100 * cnt["RUNNING"] / n if n else 0)


def stats1(trades, cost, months):
    """1 micro (D4 rows: 50/50 blended per-contract points)."""
    n = len(trades)
    if not n:
        return dict(n=0, pm=0, win=0, pf=0, avg=0, total=0, mdd=0)
    u = [t["pts1m"] * PV - cost for t in trades]
    gw = sum(x for x in u if x > 0)
    gl = -sum(x for x in u if x < 0)
    eq = peak = dd = 0.0
    for x in u:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dict(n=n, pm=n / months, win=100 * sum(1 for x in u if x > 0) / n, pf=(gw / gl if gl else float("inf")),
                avg=sum(u) / n, total=sum(u), mdd=dd)


def months_between(a, b):
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb_ = int(b[:4]), int(b[5:7])
    return (yb - ya) * 12 + (mb_ - ma) + 1
