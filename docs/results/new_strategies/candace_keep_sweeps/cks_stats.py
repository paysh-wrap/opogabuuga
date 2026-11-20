"""Stats extensions (same rules as ctm_lib; adds contracts list, days-to-pass, still-running)."""
import statistics, bisect
from collections import defaultdict
from decimal import Decimal as D
import cks_lib  # noqa  (sets sys.path for ctm_lib)
import ctm_lib as L
from ctm_lib import effective_dll, dll_remaining, full_fit, pnl_usd


def fit2(k, trades, var, cost):
    p, rc = L.PLANS[k], L.RISKCFG[k]
    eq = peak = dd = 0.0
    cs, zero = [], 0
    for t in trades:
        c = var.size(t, full_fit(p, rc, t, D(p["dll"]) if p["dll"] is not None else None, p["mll"]))
        if c < 1:
            zero += 1
            continue
        cs.append(c)
        eq += pnl_usd(t, c, cost)
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dict(n=len(cs), zero=zero, total=eq, mdd=dd, med_c=(statistics.median(cs) if cs else 0))


def eval_run2(p, rc, var, tdays, start_i, cost):
    """identical to ctm_lib.eval_run but returns (status, day index of pass)."""
    S = p["S"]; bal = S; peak = S; locked = False; mllv = S - p["mll"]; big = None; pdays = 0
    for di, tl in tdays:
        if di < start_i:
            continue
        pnl_day = D(0); peak_day = D(0); free = -1; stopped = False
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
                return "BUST", di
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
        if prof >= p["target"] and big <= p["cons"] / 100 * prof and pdays >= p["mind"]:
            return "PASS", di
    return "RUNNING", None


def eval2(k, trades, var, daylist, lo, hi, cost):
    p, rc = L.PLANS[k], L.RISKCFG[k]
    days = [d for d in daylist if lo <= d <= hi]
    di = {d: i for i, d in enumerate(days)}
    by = defaultdict(list)
    for t in trades:
        if t["day"] in di:
            by[t["day"]].append(t)
    tdays = sorted((di[d], sorted(v, key=lambda t: t["idx"])) for d, v in by.items())
    tdi = [x[0] for x in tdays]
    n = len(days)
    cnt = {"PASS": 0, "BUST": 0, "RUNNING": 0}
    cache, dtp = {}, []
    for s in range(n):
        j = bisect.bisect_left(tdi, s)
        key = tdi[j] if j < len(tdi) else None
        if key not in cache:
            cache[key] = ("RUNNING", None) if key is None else eval_run2(p, rc, var, tdays, key, cost)
        st, pd = cache[key]
        cnt[st] += 1
        if st == "PASS":
            dtp.append(pd - s + 1)
    return dict(starts=n, pas=100 * cnt["PASS"] / n if n else 0, bust=100 * cnt["BUST"] / n if n else 0,
                run=100 * cnt["RUNNING"] / n if n else 0, med_days=(statistics.median(dtp) if dtp else None))
