"""Session 17 two-books study - shared code (research only, floats; nothing here is app code).
Data  : MNQ.v.0 1-minute RTH day arrays from prep.py (env TB_CACHE = folder with mnq_days.pkl).
Costs : 1 micro MNQ, $1.00 fee per round trip + 1 tick ($0.50) adverse slippage on every market/stop fill; limit targets need a 1-tick
        trade-through; stop first when stop and target share a 1-minute bar (same as sessions 9-15).
Split : IS (pick) = 2019-05 .. 2023-12, HO (judge) = 2024-01 .. 2026-11."""
import os, pickle
import numpy as np, pandas as pd

CACHE = os.environ.get("TB_CACHE", "/tmp/claude-0/-home-user-opogabuuga/91ade7f5-a723-5dc9-ba25-2d30265bd584/scratchpad/data")
PV, TICK, FEE = 2.0, 0.25, 1.0
SPLIT = "2023-12-31"
HO_START, HO_END = "2024-01-01", "2026-11-06"
NB = 390
_c = {}


def load():
    if "d" not in _c:
        _c["d"] = pickle.load(open(f"{CACHE}/mnq_days.pkl", "rb"))
    return _c["d"]


def stop_pts(stop_usd):
    return (stop_usd - FEE - 2 * TICK * PV) / PV


# ---------------------------------------------------------------------------------------------- NOISE (rules = tools/noise_area.py)
def noise(days, stop_usd=250.0, hard_pct=None, lock=None, allow=None, look=14, step=60, maxtr=3):
    """Verified NOISE rules (bar loop copied from docs/results/tools/noise_area.py). stop_usd = fixed $ emergency stop (D58, app default 250);
    hard_pct = the old 1% stop instead. lock=(trigger_pts, lock_pts) = D75-P1 profit lock (a locked-stop exit ends NOISE for the day).
    allow(i, side, k) -> bool : optional entry filter (a refused signal does not use up one of the max 3 entries).
    rows: d, side, ek, xk, pnl, mae (worst open loss in $, >= 0)"""
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, 360, step)); out = []
    hp = stop_pts(stop_usd) if stop_usd else None
    for i in range(look, len(days)):
        d, a = days[i]
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        pos = ntr = pending = 0; entry = hs = None; ek = 0; mae = 0.0; locked = False

        def close_trade(px, xk):
            nonlocal pos, ntr
            if locked and xk > ek and ((pos > 0 and px <= entry + lock[1] + 1e-9) or (pos < 0 and px >= entry - lock[1] - 1e-9)): ntr = maxtr
            out.append((d, pos, ek, xk, (px - entry) * pos * PV - FEE, mae + TICK * PV)); pos = 0

        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and pos == 0:
                entry = o[k] + pending * TICK; pos, pending = pending, 0; ek = k; mae = 0.0; locked = False
                hs = entry - pos * hp if hp else (entry - pos * hard_pct * entry if hard_pct else None)
            if pos:
                mae = max(mae, ((entry - l[k]) if pos > 0 else (h[k] - entry)) * PV)
                if hs is not None and ((pos > 0 and l[k] <= hs) or (pos < 0 and h[k] >= hs)):
                    close_trade((min(hs, o[k]) if pos > 0 else max(hs, o[k])) - pos * TICK, k)
                elif lock and not locked and ((pos > 0 and h[k] >= entry + lock[0]) or (pos < 0 and l[k] <= entry - lock[0])):
                    locked = True; hs = max(hs, entry + lock[1]) if pos > 0 else min(hs, entry - lock[1])
            if pos and k == 389: close_trade(c[k] - pos * TICK, k)
            if k in checks:
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK, min(nk, 389))
                if pos == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side and (allow is None or allow(i, side, k)):
                        pending, ntr = side, ntr + 1
    return pd.DataFrame(out, columns=["d", "side", "ek", "xk", "pnl", "mae"])


# ---------------------------------------------------------------------------------------------- generic trade walker (1-minute bars)
def walk(a, s, ek, stop_dist, tgt_dist, xend, entry_px=None, exit_fn=None):
    """One trade on day arrays. Entry = open of bar ek + 1 tick slippage (or entry_px = stop-order trigger: fill = worse of trigger/open + 1 tick,
    stop/target distances are then measured from the TRIGGER price). Stop = market with 1 tick slippage, gap-aware. Target = limit, needs a 1-tick
    trade-through. Same bar: stop first. exit_fn(k) -> True = leave at the open of bar k+1 (app-initiated market exit). Flat at close of bar xend-1.
    returns pnl $ net, exit bar, mae $ (>= 0)"""
    o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    if entry_px is None:
        e = o[ek] + s * TICK; ref = e
    else:
        ref = entry_px; e = (max(entry_px, o[ek]) if s > 0 else min(entry_px, o[ek])) + s * TICK
    stop = ref - s * stop_dist
    tgt = ref + s * tgt_dist if tgt_dist else None
    mae = 0.0
    for j in range(ek, xend):
        if np.isnan(c[j]): continue
        mae = max(mae, ((e - l[j]) if s > 0 else (h[j] - e)) * PV)
        if (s > 0 and l[j] <= stop) or (s < 0 and h[j] >= stop):
            px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK
            return (px - e) * s * PV - FEE, j, mae + TICK * PV
        if tgt is not None and ((s > 0 and h[j] >= tgt + TICK) or (s < 0 and l[j] <= tgt - TICK)):
            return (tgt - e) * s * PV - FEE, j, mae
        if exit_fn is not None and j + 1 < xend and exit_fn(j):
            nj = j + 1
            if not np.isnan(o[nj]): return (o[nj] - s * TICK - e) * s * PV - FEE, nj, mae
    j = xend - 1
    while j > ek and np.isnan(c[j]): j -= 1
    return (c[j] - s * TICK - e) * s * PV - FEE, j, mae


def merge(*streams):
    """several streams -> one stream obeying 'max 1 open position per account' (a trade whose entry falls while an earlier one is open is dropped)."""
    t = pd.concat(streams).sort_values(["d", "ek"], kind="stable").reset_index(drop=True)
    keep = []; last = None; busy = -1
    for r in t.itertuples():
        if r.d != last: last, busy = r.d, -1
        if r.ek <= busy: keep.append(False); continue
        keep.append(True); busy = r.xk
    return t[keep].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------- stats
def stats(t, era="HO"):
    t = t[t.d <= SPLIT] if era == "IS" else (t[t.d > SPLIT] if era == "HO" else t)
    if not len(t): return dict(n=0, win=float("nan"), avg=0.0, net=0.0, pf=float("nan"), dd=0.0)
    w = t.pnl > 0; gl = -t.pnl[~w].sum()
    cum = np.concatenate([[0], t.pnl.cumsum().values])
    return dict(n=int(len(t)), win=float(100 * w.mean()), avg=float(t.pnl.mean()), net=float(t.pnl.sum()),
                pf=float(t.pnl[w].sum() / gl) if gl > 0 else float("inf"), dd=float(np.max(np.maximum.accumulate(cum) - cum)))


# ---------------------------------------------------------------------------------------------- Lucid Pro 25K evaluation simulation
B0, TGT, MLL = 25000.0, 1250.0, 1000.0


def eval_sim(t, strict=False, start=HO_START, end=HO_END, horizon=120, step=2):
    """Pro 25K EVAL on real consecutive days, rolling starts every 2nd business day (same engine/assumptions as docs/results/tools/sim25k.py:
    target $1,250, $1,000 EOD-trailing loss limit that locks at 25,100 once the EOD peak reaches 26,100, breach checked after every trade,
    120-business-day horizon, runs that neither pass nor bust count as 'open').
    strict=False : sim25k 'Pro' assumptions (no DLL in eval, no consistency, open-trade drawdown not modelled)  <- comparable with sessions 9/10
    strict=True  : + intraday breach on each trade's worst open loss (MAE), + $600 soft daily loss limit, + pass needs best day <= 40% of profit.
    returns dict(pass_, bust, open_, med)  (% of starts; med = median business days to pass)"""
    t = t[(t.d >= start) & (t.d <= end)].sort_values(["d", "ek"], kind="stable")
    tr = {}
    for d, p, m in zip(t.d, t.pnl, t.mae): tr.setdefault(d, []).append((p, m))
    days = pd.bdate_range(start, end).strftime("%Y-%m-%d").tolist()
    res = []
    for s0 in range(0, len(days) - 40, step):
        bal = peak = B0; floor = B0 - MLL; i = s0; status = "open"; dp = []
        while i < len(days) and i - s0 < horizon:
            day = 0.0; dead = False
            for p, m in tr.get(days[i], []):
                if strict:
                    if bal - max(m, -p, 0.0) <= floor: dead = True; break
                    if day + p <= -600.0: p = -600.0 - day
                bal += p; day += p
                if bal <= floor: dead = True; break
                if strict and day <= -600.0: break
            i += 1
            if dead: status = "bust"; break
            if day != 0.0: dp.append(day)
            peak = max(peak, bal)
            floor = B0 + 100 if peak >= B0 + MLL + 100 else max(floor, peak - MLL)
            prof = bal - B0
            if prof >= TGT and (not strict or max(dp) <= 0.40 * prof): status = "pass"; break
        res.append((status, i - s0))
    n = len(res); ps = [x for s, x in res if s == "pass"]
    return dict(pass_=100 * len(ps) / n, bust=100 * sum(s == "bust" for s, _ in res) / n, open_=100 * sum(s == "open" for s, _ in res) / n,
                med=float(np.median(ps)) if ps else float("nan"), n=n)


def row(name, t, extra=""):
    """one result row (dict) for the tables: IS + HO stream stats and HO Pro-25K eval sim (both assumption sets)."""
    i, h = stats(t, "IS"), stats(t, "HO")
    if h["n"]:
        e, s = eval_sim(t), eval_sim(t, strict=True)
    else:
        e = s = dict(pass_=0.0, bust=0.0, open_=100.0, med=float("nan"))
    return dict(name=name, IS=i, HO=h, ev=e, evs=s, note=extra)


def fmt(r):
    i, h, e, s = r["IS"], r["HO"], r["ev"], r["evs"]
    med = "-" if e["med"] != e["med"] else f"{e['med']:.0f}"
    return (f"| {r['name']} | {i['n']} / {i['win']:.1f}% / {i['pf']:.2f} / {i['net']:+,.0f} | {h['n']} | {h['win']:.1f}% | {h['avg']:+.2f} | {h['pf']:.2f} | "
            f"{h['net']:+,.0f} | {h['dd']:,.0f} | {e['pass_']:.1f}% | {e['bust']:.1f}% | {med} | {s['pass_']:.1f}% / {s['bust']:.1f}% | {r['note']} |")


HDR = ("| variant | IS: trades / win / PF / net $ | HO trades | HO win | HO $/trade | HO PF | HO net $ | HO max DD $ | eval PASS | eval BUST | median days to pass | strict eval pass / bust | note |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
