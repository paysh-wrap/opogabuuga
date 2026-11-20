"""CANDACE ICT SCALP "keep the sweeps" study: offline mirror of candace_ict.replay_day with a multi-episode tracker.
NO app code is changed. Policies for a NEW sweep while episodes are pending:
  REPLACE  engine as is (base_mode: one slot, every new sweep replaces it; bars with an open position are skipped and the
           state is cleared when the position closes)  -> used to validate this generic code against the engine
  V1       KEEP_ALL: every sweep is its own episode, tracked in parallel
  V2       SAME_SIDE: a new sweep replaces the pending episode of the SAME side only; the other side runs in parallel
  V3       PROTECT_FORMED: single slot; a new sweep replaces the pending episode only while it has no valid IFVG; once it
           has one the new sweep is ignored (pool not consumed) until the pending episode retraces / times out / fails
Trade taking (V1-V3): episodes keep being tracked while a position is open; a signal on a bar where a position was open at
the bar start (incl. the exit bar) is SKIPPED (counted, episode consumed). One entry per episode. Several signals on one bar:
higher grade (A+ > B > C) first, then the earlier sweep; the others are skipped (counted). Everything else = engine.
"""
import sys, os
from datetime import timedelta
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "candace_trade_more"))
import ctm_lib as L
from ctm_lib import (fvgs, pools, grade, rth_gap_levels, _session, Fvg, round_to_tick, dtime, mi, _step_pos, _finish)

RANK = {"A+": 2, "B": 1, "C": 0}


def run_day_v(hist, today, cfg, tick, policy="REPLACE"):
    res = dict(signals=[], ep_created=0, ep_ifvg=0, ep_retrace=0, ep_a2=0, ep_d2=0, ep_timeout=0, skipped_pos=0,
               skipped_same_bar=0, ep_replaced=0, ep_ignored_protected=0)
    if not today:
        return res
    base_mode = policy == "REPLACE"
    d = today[-1].close_time.astimezone(L.ET).date()
    bars = sorted((b for b in today if b.close_time.astimezone(L.ET).date() == d), key=lambda b: b.close_time)
    prior = [b for b in hist if b.close_time.astimezone(L.ET).date() < d]
    pdays = sorted({b.close_time.astimezone(L.ET).date() for b in prior})
    prev = [b for b in prior if pdays and b.close_time.astimezone(L.ET).date() == pdays[-1]]
    prev_rth = [b for b in prev if dtime(9, 30) < b.close_time.astimezone(L.ET).time() <= dtime(16, 0)]
    first_rth = next((b for b in bars if b.close_time.astimezone(L.ET).time() == dtime(9, 31)), None)
    gap_levels = rth_gap_levels(prev_rth[-1].c if prev_rth else None, first_rth.o if first_rth else None)
    h1 = L.hourly([*prior[-60 * 24:], *bars])
    pos = None
    losses = 0
    swept_used = set()
    eps = []  # dict(si, sp, ext, ifvg=None|(idx, Fvg))
    D0 = D(0)
    for i, b in enumerate(bars):
        pos_at_start = pos is not None
        if pos is not None:
            if _step_pos(pos, b, False, False):
                if (pos["exit_price"] - pos["entry"]) * pos["s"] < 0:
                    losses += 1
                _finish(res, pos, d)
                pos = None
                if base_mode:
                    eps = []
            if base_mode:
                continue
        sess = _session(b.close_time, cfg)
        if sess is None or losses >= cfg.max_losses_per_day:
            eps = []
            continue
        before = bars[:i]
        h1_known = [x for x in h1 if x.close_time <= b.close_time]
        pl = pools(prev, before, h1_known, cfg, tick)
        new = None
        if policy == "V3" and any(e["ifvg"] is not None for e in eps):
            res["ep_ignored_protected"] += any(
                (p.price, p.side) not in swept_used and ((p.side > 0 and b.h > p.price > b.c) or (p.side < 0 and b.l < p.price < b.c))
                for p in pl)
        else:
            for p in pl:
                if (p.price, p.side) in swept_used:
                    continue
                if (p.side > 0 and b.h > p.price > b.c) or (p.side < 0 and b.l < p.price < b.c):
                    swept_used.add((p.price, p.side))
                    new = dict(si=i, sp=p, ext=b.h if p.side > 0 else b.l, ifvg=None)
                    res["ep_created"] += 1
                    if policy in ("REPLACE", "V3"):
                        res["ep_replaced"] += len(eps)
                        eps = [new]
                    elif policy == "V1":
                        eps = eps + [new]
                    elif policy == "V2":
                        res["ep_replaced"] += sum(1 for e in eps if e["sp"].side == p.side)
                        eps = [e for e in eps if e["sp"].side != p.side] + [new]
                    else:
                        raise ValueError(policy)
                    break
        cands = []
        keep = []
        for e in eps:
            if e is new:
                keep.append(e)
                continue
            si, sp, ext = e["si"], e["sp"], e["ext"]
            sign = -sp.side
            if e["ifvg"] is None:
                run = [f for f in fvgs(bars[max(0, si - cfg.fvg_lookback): si + 1]) if f.color == -sign]
                if not run or i == si:
                    keep.append(e)
                    continue
                f = run[-1]
                body = abs(b.c - b.o)
                ref = bars[max(0, i - cfg.displacement_bars): i]
                avg = sum((abs(x.c - x.o) for x in ref), D0) / max(len(ref), 1)
                through = (b.c < f.lo and b.o > f.lo) if sign < 0 else (b.c > f.hi and b.o < f.hi)
                if through and body >= cfg.displacement_mult * avg:
                    e["ifvg"] = (i, f)
                    res["ep_ifvg"] += 1
                    keep.append(e)
                elif i - si > cfg.ifvg_max_bars:
                    res["ep_timeout"] += 1
                else:
                    keep.append(e)
                continue
            fi, f = e["ifvg"]
            if i - fi > cfg.ifvg_max_bars:
                res["ep_timeout"] += 1
                continue
            into = (b.h >= f.lo and b.c <= f.hi) if sign < 0 else (b.l <= f.hi and b.c >= f.lo)
            if not into:
                keep.append(e)
                continue
            res["ep_retrace"] += 1
            rng = bars[max(0, i - cfg.range_bars): i + 1]
            lo, hi = min(x.l for x in rng), max(x.h for x in rng)
            mid = lo + cfg.premium_pct * (hi - lo)
            entry = b.c
            if (sign < 0 and entry < mid) or (sign > 0 and entry > mid):
                res["ep_a2"] += 1
                continue
            stop = round_to_tick(ext - sign * cfg.stop_buffer_ticks * tick, tick, away_from=entry)
            risk = (entry - stop) * sign
            cap = cfg.ny_max_stop_pts if sess == "NY" else cfg.london_max_stop_pts
            if risk <= 0 or risk > cap:
                res["ep_d2"] += 1
                continue
            min_tp = entry + sign * cfg.min_rr * risk
            ahead = [p.price for p in pl if p.side == sign and (p.price - min_tp) * sign >= 0]
            tp_raw = min(ahead, key=lambda x: abs(x - entry)) if ahead else min_tp
            tp = round_to_tick(tp_raw, tick, toward=entry)
            if (tp - entry) * sign < cfg.min_rr * risk:
                tp = round_to_tick(min_tp, tick, away_from=entry)
            conf = ["DISPLACEMENT"]
            if sp.kind == "EQUAL":
                conf.append("EQUAL_POOL")
            if sp.kind == "FVG1H" or any(p.kind == "FVG1H" and abs(p.price - ext) <= cfg.gap_level_tol_pts for p in pl):
                conf.append("HTF_FVG")
            if any(abs(g - ext) <= cfg.gap_level_tol_pts or abs(g - entry) <= cfg.gap_level_tol_pts for g in gap_levels):
                conf.append("RTH_GAP")
            if sp.kind in ("PDH", "PDL"):
                conf.append("PREV_DAY")
            cands.append((-RANK[grade(len(conf), cfg)], si, e, dict(sign=sign, entry=entry, stop=stop, risk=risk, tp=tp,
                                                                     conf=conf, sp=sp, fi=fi)))
        eps = keep
        if cands:
            cands.sort(key=lambda c: (c[0], c[1]))
            if pos_at_start or pos is not None:
                res["skipped_pos"] += len(cands)
                continue
            res["skipped_same_bar"] += len(cands) - 1
            _, _, e, s = cands[0]
            hold = cfg.ny_max_hold_minutes if sess == "NY" else cfg.london_max_hold_minutes
            until = b.close_time + timedelta(minutes=hold)
            pos = dict(time=b.close_time, s=s["sign"], entry=s["entry"], stop=s["stop"], stop0=s["stop"], tp=s["tp"],
                       hold_until=until, conf=s["conf"], grade=grade(len(s["conf"]), cfg), swept=s["sp"], plevel=None,
                       pdone=False, pA=None, armed=False, outcome="OPEN", exit_time=None, exit_price=None,
                       risk=s["risk"], extended=False, sess=sess, si=e["si"], fi=s["fi"], c4=False, i=i)
            if base_mode:
                eps = []
    if pos is not None:
        pos["outcome"], pos["exit_time"], pos["exit_price"] = "MTM", None, bars[-1].c
        _finish(res, pos, d)
    return res


# ---------------------------------------------------------------- parallel runner
def _job(args):
    lo, hi, cfgd, policy = args
    cfg = L.CandaceIctCfg(**cfgd)
    out = []
    for i in range(lo, hi):
        ds, gb, mb = L.BUILT[i]
        h = L._hist(i)
        if policy == "ENGINE":
            out.append((ds, L.engine_trades(h, mb, cfg, L.TICK), None))
        else:
            r = run_day_v(h, mb, cfg, L.TICK, policy)
            out.append((ds, r["signals"], {k: v for k, v in r.items() if k != "signals"}))
    return out


def run_all(cfgd, policy, pool):
    n = len(L.BUILT)
    jobs = [(a, min(a + 40, n), cfgd, policy) for a in range(0, n, 40)]
    return [x for p in pool.map(_job, jobs) for x in p]
