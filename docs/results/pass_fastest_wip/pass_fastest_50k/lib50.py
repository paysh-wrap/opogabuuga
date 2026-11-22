"""Pass-fastest 50K study: shared library (research only; nothing in backend/app, config/ or frontend/ is changed).

Account simulator for Lucid Pro 50K EVALUATION (EOD), generalised from `../pass_faster/pf_sim.py` (NOISE) and `../pass_faster_fixed/run_fixed.py`
(NOISE + CANDACE on one account).  Everything the earlier studies enforce is enforced here: trailing EOD MLL + lock, DLL incl. LucidScale
(NOISE reading dll+today, fixed-size strategies the D18 reading), 40 % consistency + 38 % day stop (a trade is capped at the day stop and the day
ends), kill distance + pre-trade room check, D57 shrink for NOISE, one position at a time (A) / both at once, same direction only (B), flat by close
(streams are flat by 16:00), STUCK = NOISE can no longer be sized (counts as a non-pass, as in eval_odds.yaml).
New (all existing app settings, see SizeTierCfg / auto_contracts / controller):
  grow_per/max_contracts, brake_below/brake_contracts, taper_below_remaining/taper_contracts (remaining share at the START of the session),
  day_lock_pct (EVAL_DAY_LOCK: no new NOISE / PM_FADE entry once today's profit >= pct x remaining target at the start of the session).
Run scripts from <worktree>/backend with PYTHONPATH=. and /usr/local/bin/python3.
"""
import sys, os, math, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE + "/../pass_faster")
import numpy as np, pandas as pd
import pf_sim as F

CACHE = os.environ.get("PF50_CACHE", "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/pf50/streams")
SHR, MINP, TV, FEE, SLIP, PV = F.SHRINK, F.MINPCT, F.TV, F.FEE, F.SLIP, F.PV
CAP_C = 125.0                     # per-micro risk cap of the fixed CANDACE / GALA micros (D154 defaults, $125 per micro: stop $ + fee + slippage)

DATES, OPEN = F.trading_days()
P = F.load_plans()[50]
ALL_D = [d for d in DATES if F.WIN["ALL"][0] <= d <= F.WIN["ALL"][1]]
NPICK = sum(1 for d in ALL_D if d <= F.WIN["PICK"][1])
assert NPICK == 547 and len(ALL_D) == 1252 and ALL_D[NPICK] >= F.WIN["JUDGE"][0]
SLICES = {"ALL": (0, len(ALL_D)), "PICK": (0, NPICK), "JUDGE": (NPICK, len(ALL_D))}
WD = {d: pd.Timestamp(d).dayofweek for d in ALL_D}

# ------------------------------------------------------------------------------------------------------------------ configs
DEFAULT = dict(stop=250, trig=100, mx=3, mon=0,                       # NOISE stream (generator level)
               nn=2, grow=0, gmax=0, bb=0.0, bc=1, tb=0.0, tc=1, dl=0.0,  # size-table row (existing settings)
               fade=0, nc=0, cwin=1000, gala=0, ng=1,                 # add-ons
               both=0, fsh=0)                                        # both=1: NOISE+CANDACE at once (B, needs a rule change); fsh=1: fade treated like NOISE (D57 shrink, legacy sim2)
BASE = dict(DEFAULT, bb=0.5, bc=1)                                    # shipped 50K: 2 micros, 1 micro below 50 % cushion, $250 stop, lock 100, max 3, Mondays off, fade off
ROW_A = dict(DEFAULT, stop=100, nn=2, nc=1)                           # NOISE 2 micros @ $100 + CANDACE 1 micro (no brake)
NOISE2_100 = dict(DEFAULT, stop=100, nn=2)


def cfg_of(**kw):
    c = dict(DEFAULT); c.update(kw)
    bad = set(kw) - set(DEFAULT)
    assert not bad, bad
    return c


def cfg_key(c):
    return json.dumps({k: c[k] for k in DEFAULT}, sort_keys=True)


def sim_tuple(c, use_cap=True, use_cons=True, nofade_cap=False):
    return (int(c["nn"]), float(c["grow"] or 0), int(c["gmax"] or 0), float(c["bb"] or 0), int(c["bc"] or 0), float(c["tb"] or 0), int(c["tc"] or 0),
            float(c["dl"] or 0), int(c["nc"]), int(c["ng"]) if c["gala"] else 0, int(c["fsh"]), bool(use_cap), bool(use_cons))


# ------------------------------------------------------------------------------------------------------------------ streams -> tables
_noise = {}; _fade = None; _cand = {}; _gala = None


def noise_tuples(stop, trig, mx, mon):
    k = (int(stop), int(trig), int(mx), int(mon))
    if k not in _noise:
        df = pd.read_csv(f"{CACHE}/s{k[0]}_t{k[1]}_m{k[2]}_mon{k[3]}.csv")
        by = {}; first = {}
        for r in df.itertuples():
            ek = int(r.ek)
            by.setdefault(r.d, []).append((float(ek), float(r.xk) + 0.5, 0, float(r.pnl), float(r.mae), float(r.risk), float(OPEN[r.d][ek]), int(r.side)))
            if ek < first.get(r.d, 10 ** 9): first[r.d] = ek
        _noise[k] = (by, first, df)
    return _noise[k]


def fade_list():
    global _fade
    if _fade is None:
        df = pd.read_csv(f"{CACHE}/fade_all_days.csv"); df = df[(df.d >= ALL_D[0]) & (df.d <= ALL_D[-1])]
        _fade = [(r.d, int(r.ek), (float(r.ek), float(r.xk) + 0.5, 2, float(r.pnl), float(r.mae), 250.0, float(OPEN[r.d][int(r.ek)]), int(r.side)), WD[r.d]) for r in df.itertuples()]
    return _fade


def cand_tuples(cwin, cap=CAP_C):
    if cwin not in _cand:
        fn = WT + "/docs/results/pass_faster_c125/streams_candace_" + ("base" if cwin == 1000 else "w1030") + ".csv"
        df = pd.read_csv(fn); df = df[df.day >= ALL_D[0]]
        per = df.stop_pts / 0.25 * TV + FEE + 2 * SLIP * TV
        kept = df[per <= cap + 1e-9]
        _cand[cwin] = ({}, len(df), len(kept))
        for r in kept.itertuples():
            _cand[cwin][0].setdefault(r.day, []).append((float(r.idx), float(r.exit_idx), 1, float(r.p1), float(r.stop_pts), 0.0, 0.0, 1 if r.dir == "LONG" else -1))
    return _cand[cwin]


def gala_tuples(cap=CAP_C):
    global _gala
    if _gala is None:
        df = pd.read_csv(WT + "/docs/results/new_strategies/gala_trade_more/trades_window_end_1230.csv"); df = df[df.day >= ALL_D[0]]
        per = df.stop_pts / 0.25 * TV + FEE + 2 * SLIP * TV
        kept = df[per <= cap + 1e-9]; _gala = ({}, len(df), len(kept))
        for r in kept.itertuples():
            _gala[0].setdefault(r.day, []).append((float(r.idx), float(r.exit_idx), 3, float(r.pts), float(r.stop_pts), 0.0, 0.0, 1 if r.dir == "LONG" else -1))
    return _gala


def build_days(c, fade_hindsight=False):
    """list (index = position in ALL_D) of the sorted trade tuples of config c: (m_in, m_out, kind, a, b, c, d, dir);
    kind 0 NOISE (pnl, mae, risk, entry) / 2 PM_FADE (same) / 1 CANDACE and 3 GALA (pts, stop_pts)."""
    by_n, first, _ = noise_tuples(c["stop"], c["trig"], c["mx"], c["mon"])
    tab = {d: list(v) for d, v in by_n.items()}
    if c["fade"]:
        for (d, ek, tup, wd) in fade_list():
            if wd == 0 and not c["mon"]: continue                                  # skip_weekdays applies to the fade too (D132)
            if fade_hindsight:
                if d in by_n: continue                                             # legacy session-21 rule: fade only on days NOISE never traded
            else:
                fe = first.get(d)
                if fe is not None and fe <= ek: continue                           # causal rule: NOISE already entered earlier (or on the same bar) today
            tab.setdefault(d, []).append(tup)
    if c["nc"]:
        for d, v in cand_tuples(c["cwin"])[0].items(): tab.setdefault(d, []).extend(v)
    if c["gala"]:
        for d, v in gala_tuples()[0].items(): tab.setdefault(d, []).extend(v)
    for v in tab.values(): v.sort(key=lambda x: (x[0], x[2]))
    return [tab.get(d, ()) for d in ALL_D]


def _gmin():
    by, _, df = noise_tuples(250, 100, 3, 0)
    ent = [float(OPEN[r.d][int(r.ek)]) for r in df.itertuples() if r.d >= "2025-11-06"]
    return F.smin(float(np.mean(ent)))


GMIN = None


def gmin():
    global GMIN
    if GMIN is None: GMIN = _gmin()
    return GMIN


# ------------------------------------------------------------------------------------------------------------------ account simulator, A (one position at a time)
def sim_a(days, idx, p, c, gm):
    """One evaluation. days: list of per-day trade tuples, idx: iterable of day indices, c: sim_tuple. -> (outcome, sessions, day-stop hits, consistency-blocked EODs)
    outcome: 'pass' | 'stuck' | 'bust' | 'open'."""
    nn, grow, gmax, bb, bc, tb, tc, dl, nc, ng, fsh, use_cap, use_cons = c
    kd = p["kill"]; mg = p["margin"]; size = p["size"]; mll = p["mll"]; dll0 = p["dll"]; tgt = p["target"]
    scale = p["scale"]; ltrig = p["lock_trig"]; llvl = p["lock_lvl"]; cons = p["cons"]; mpd = p["mpd"]
    dstop = p["day_stop"] if use_cap else 1e18; cost = p["cost"]
    bal = size; floor = size - mll; peak = size; locked = False; peak_e = size
    pdays = 0; best = 0.0; s = 0; capd = 0; cblk = 0
    for di in idx:
        s += 1
        tl = days[di]
        if not tl: continue
        bal0 = bal; today = 0.0; stop = False; pkd = 0.0; free = -1.0; last = -1
        dll = dll0
        if scale and locked: dll = 0.6 * (peak_e - size)
        for (m_in, m_out, kind, a, b, cc, d, dr) in tl:
            if stop: break
            if m_in <= free and not (kind == 0 and last == 0): continue
            cush = bal - floor
            if kind == 0 or kind == 2:
                if dl and today > 0.0:                                          # D66 day lock (NOISE + PM_FADE, eval table row)
                    rem = tgt - (bal0 - size)
                    if rem > 0.0 and today >= dl * rem: continue
                q = nn                                                          # auto_contracts: grow -> taper -> brake
                if grow:
                    e = int(cush // grow) - 1
                    if e > 0: q = nn + e
                    if q > gmax: q = gmax
                if tb and (tgt - (bal0 - size)) < tb * tgt:
                    if tc < q: q = tc
                if bb and cush < bb * mll:
                    if bc < q: q = bc
                if kind == 0 or fsh:                                            # NOISE: D57 shrink + room check + STUCK rule (session-21 sim)
                    if cush <= kd: return ("stuck", s, capd, cblk)
                    room0 = cush - kd
                    if dll: room0 = min(room0, dll + today)
                    pp = None; eff = b
                    while q > 0:
                        S_ = cc
                        if q * cc > SHR * room0:
                            pt = math.floor(((SHR * room0 / q) - FEE) / TV - SLIP)
                            if pt * 0.25 < MINP * d or pt <= 0: q = -1; break
                            S_ = pt * TV + FEE + TV
                        if q * S_ + mg <= room0:
                            if S_ < cc and b >= S_: pp = -S_
                            else: pp = a
                            eff = min(b, S_) if S_ < cc else b
                            break
                        q -= 1
                    if q <= 0:
                        if SHR * (cush - kd) < gm: return ("stuck", s, capd, cblk)
                        continue
                    pq = q * pp; dead = False
                    if q * eff >= cush - kd: pq = -(cush - kd); dead = True
                else:                                                           # PM_FADE: no D57 shrink (D73), keeps the $500 pause floor, $250 stop
                    if cush < 500.0: continue
                    room0 = cush - kd
                    if dll: room0 = min(room0, dll + today)
                    while q > 0 and q * cc + mg > room0: q -= 1
                    if q <= 0: continue
                    pq = q * a; dead = False
                    if q * b >= cush - kd: pq = -(cush - kd); dead = True
            else:                                                               # CANDACE (kind 1) / GALA (kind 3): fixed micros, stop-based worst case
                q = nc if kind == 1 else ng
                per = b / 0.25 * TV + FEE + 2 * SLIP * TV
                left = None
                if dll:
                    left = dll - (max(0.0, pkd, today) - today)
                    if left <= 0: stop = True; break
                lim = cush - kd
                if left is not None and left < lim: lim = left
                while q >= 1 and q * per + mg > lim: q -= 1
                if q < 1: continue
                pq = q * (a * PV - cost); dead = False
            free = m_out; last = kind
            if dll and today + pq <= -dll: pq = -dll - today; stop = True
            if today + pq > dstop: pq = dstop - today; stop = True; capd += 1
            today += pq; bal += pq
            if today > pkd: pkd = today
            if dead or bal <= floor + kd: return ("bust", s, capd, cblk)
        if today > 0:
            pdays += 1
            if today > best: best = today
        if bal > peak_e: peak_e = bal
        if bal > peak and not locked:
            peak = bal
            if peak >= ltrig: locked = True; floor = llvl
            else: floor = peak - mll
        prof = bal - size
        if prof >= tgt and pdays >= mpd:
            if (not cons) or (not use_cons) or best <= cons / 100.0 * prof: return ("pass", s, capd, cblk)
            cblk += 1
    return ("open", s, capd, cblk)


# ------------------------------------------------------------------------------------------------------------------ account simulator, B (NOISE + CANDACE/GALA at once, same direction nets, opposite skipped)
def sim_b(days, idx, p, c, gm):
    """Variant B of run_fixed.simulate generalised to the new NOISE sizing; open positions realise their P&L at their exit. Needs a rule change (max 1 open position)."""
    nn, grow, gmax, bb, bc, tb, tc, dl, nc, ng, fsh, use_cap, use_cons = c
    kd = p["kill"]; mg = p["margin"]; size = p["size"]; mll = p["mll"]; dll0 = p["dll"]; tgt = p["target"]
    scale = p["scale"]; ltrig = p["lock_trig"]; llvl = p["lock_lvl"]; cons = p["cons"]; mpd = p["mpd"]
    dstop = p["day_stop"] if use_cap else 1e18; cost = p["cost"]
    bal = size; floor = size - mll; peak = size; locked = False; peak_e = size
    pdays = 0; best = 0.0; s = 0; capd = 0; cblk = 0
    for di in idx:
        s += 1
        tl = days[di]
        if not tl: continue
        bal0 = bal
        st = {"today": 0.0, "pk": 0.0, "stop": False, "open": []}
        dll = dll0
        if scale and locked: dll = 0.6 * (peak_e - size)

        def settle(pred):
            nonlocal bal, capd
            st["open"].sort(key=lambda o: o[0]); rest = []
            for o in st["open"]:
                if st["stop"]: continue
                if not pred(o): rest.append(o); continue
                pq = o[4]
                if dll and st["today"] + pq <= -dll: pq = -dll - st["today"]; st["stop"] = True
                if st["today"] + pq > dstop: pq = dstop - st["today"]; st["stop"] = True; capd += 1
                st["today"] += pq; bal += pq; st["pk"] = max(st["pk"], st["today"])
                if o[5] or bal <= floor + kd: return True
            st["open"] = [] if st["stop"] else rest
            return False

        for (m_in, m_out, kind, a, b, cc, d, dr) in tl:
            if st["stop"]: break
            if settle(lambda o: o[0] < m_in or (kind == 0 and o[1] == 0 and o[0] - 0.5 <= m_in) or (kind == 2 and o[1] == 2 and o[0] - 0.5 <= m_in)): return ("bust", s, capd, cblk)
            if st["stop"]: break
            op_ = st["open"]; today = st["today"]
            if op_ and any(o[2] != dr for o in op_): continue
            ow = sum(o[3] for o in op_)
            cush = bal - floor
            room_m = cush - kd - ow
            if kind == 0 or kind == 2:
                if dl and today > 0.0:
                    rem = tgt - (bal0 - size)
                    if rem > 0.0 and today >= dl * rem: continue
                q = nn
                if grow:
                    e = int(cush // grow) - 1
                    if e > 0: q = nn + e
                    if q > gmax: q = gmax
                if tb and (tgt - (bal0 - size)) < tb * tgt:
                    if tc < q: q = tc
                if bb and cush < bb * mll:
                    if bc < q: q = bc
                room0 = room_m
                if dll: room0 = min(room0, dll + today - ow)
                if kind == 0 or fsh:
                    if cush <= kd: return ("stuck", s, capd, cblk)
                    pp = None; eff = b; S_ = cc
                    while q > 0:
                        S_ = cc
                        if q * cc > SHR * room0:
                            pt = math.floor(((SHR * room0 / q) - FEE) / TV - SLIP)
                            if pt * 0.25 < MINP * d or pt <= 0: q = -1; break
                            S_ = pt * TV + FEE + TV
                        if q * S_ + mg <= room0:
                            pp = -S_ if (S_ < cc and b >= S_) else a
                            eff = min(b, S_) if S_ < cc else b
                            break
                        q -= 1
                    if q <= 0:
                        if not op_ and SHR * (cush - kd) < gm: return ("stuck", s, capd, cblk)
                        continue
                    worst = q * S_; dead = (q * eff >= cush - kd - ow); pq = q * pp
                    if dead: pq = -(cush - kd - ow)
                else:
                    if cush < 500.0: continue
                    while q > 0 and q * cc + mg > room0: q -= 1
                    if q <= 0: continue
                    worst = q * cc; dead = (q * b >= cush - kd - ow); pq = q * a
                    if dead: pq = -(cush - kd - ow)
            else:
                per = b / 0.25 * TV + FEE + 2 * SLIP * TV
                left = None
                if dll:
                    left = dll - (max(0.0, st["pk"], today) - today) - ow
                    if left <= 0:
                        if not op_: st["stop"] = True
                        continue
                lim = room_m if left is None else min(room_m, left)
                q = nc if kind == 1 else ng
                while q >= 1 and q * per + mg > lim: q -= 1
                if q < 1: continue
                worst = q * per; dead = False; pq = q * (a * PV - cost)
            st["open"].append([m_out, kind, dr, worst, pq, dead])
        if not st["stop"] and settle(lambda o: True): return ("bust", s, capd, cblk)
        today = st["today"]
        if today > 0:
            pdays += 1
            if today > best: best = today
        if bal > peak_e: peak_e = bal
        if bal > peak and not locked:
            peak = bal
            if peak >= ltrig: locked = True; floor = llvl
            else: floor = peak - mll
        prof = bal - size
        if prof >= tgt and pdays >= mpd:
            if (not cons) or (not use_cons) or best <= cons / 100.0 * prof: return ("pass", s, capd, cblk)
            cblk += 1
    return ("open", s, capd, cblk)


# ------------------------------------------------------------------------------------------------------------------ rolling starts, summaries, chains
OC = {"pass": 0, "stuck": 1, "bust": 2, "open": 3}


def roll(days, c, win, both=False, use_cap=True, use_cons=True, p=None):
    """rolling start on every trading day of the window; each run uses only the days of the window. -> (outcome codes, sessions, cap hits, consistency blocks)"""
    p = p or P; lo, hi = SLICES[win]; dd = days[lo:hi]; L = len(dd); f = sim_b if both else sim_a
    ct = sim_tuple(c, use_cap, use_cons); gm = gmin()
    o = np.empty(L, dtype=np.int8); n = np.empty(L, dtype=np.int32); cp = np.empty(L, dtype=np.int32); cb = np.empty(L, dtype=np.int32)
    for s in range(L):
        r = f(dd, range(s, L), p, ct, gm)
        o[s] = OC[r[0]]; n[s] = r[1]; cp[s] = r[2]; cb[s] = r[3]
    return o, n, cp, cb


def summ(o, n):
    N = len(o); ps = n[o == 0]
    return dict(n=int(N), pass_=100.0 * float((o == 0).sum()) / N, bust=100.0 * float((o == 2).sum()) / N, stuck=100.0 * float((o == 1).sum()) / N,
                run=100.0 * float((o == 3).sum()) / N, p30=100.0 * float((ps <= 30).sum()) / N, p45=100.0 * float((ps <= 45).sum()) / N,
                p60=100.0 * float((ps <= 60).sum()) / N, med=float(np.median(ps)) if len(ps) else None, p75=float(np.percentile(ps, 75)) if len(ps) else None,
                npass=int(len(ps)))


def chain(o, n):
    """Renewal chain from every start: a stuck/bust account is reset and restarted on the NEXT trading day, until the first pass.
    Uses only chains that finish inside the data (censored = the chain reaches the data end first, or an attempt is still running)."""
    L = len(o); T = [None] * (L + 1); A = [None] * (L + 1); R = [None] * (L + 1)
    for i in range(L - 1, -1, -1):
        if o[i] == 0: T[i] = int(n[i]); A[i] = 1
        elif o[i] == 3: T[i] = None
        else:
            j = i + int(n[i])
            if j < L and T[j] is not None: T[i] = int(n[i]) + T[j]; A[i] = 1 + A[j]
    fin = [i for i in range(L) if T[i] is not None]
    # censoring-robust versions: restricted mean time to first pass within H sessions and P(first pass within H), over the starts with >= H sessions of data left
    # (for those starts min(T, H) is known exactly even when the chain itself is cut by the data end)
    rob = {}
    for H in (60, 120, 250):
        ss = [i for i in range(L) if i + H <= L]
        if not ss: rob[f"rmst{H}"] = None; rob[f"chp{H}"] = None; continue
        v = np.array([min(T[i], H) if T[i] is not None else H for i in ss], dtype=float)
        rob[f"rmst{H}"] = float(v.mean()); rob[f"chp{H}"] = 100.0 * float(np.mean([1.0 if (T[i] is not None and T[i] <= H) else 0.0 for i in ss]))
    if not fin: return dict(ch_days=None, ch_att=None, ch_cens=100.0, ch_med=None, ch_p60=0.0, **rob)
    td = np.array([T[i] for i in fin], dtype=float); ta = np.array([A[i] for i in fin], dtype=float)
    # Wald / renewal-reward cross-check: E[T] = E[attempt length] / P(pass) over the FINISHED attempts (uses starts the chain DP drops)
    done = o != 3
    wald = (float(n[done].mean()) / float((o[done] == 0).mean())) if done.any() and (o[done] == 0).any() else None
    return dict(ch_days=float(td.mean()), ch_att=float(ta.mean()), ch_cens=100.0 * (1 - len(fin) / L), ch_med=float(np.median(td)),
                ch_p60=100.0 * float((td <= 60).sum()) / L, wald=wald, wald_att=(1.0 / float((o[done] == 0).mean())) if done.any() and (o[done] == 0).any() else None, **rob)


# ------------------------------------------------------------------------------------------------------------------ static replay (fresh account, balance independent)
def static(days, c, win, p=None):
    """Fresh account every trade (full room, no balance dependence): NOISE/fade at the size a fresh account trades (grow at full cushion, no brake/taper), D57 shrink at that room,
    CANDACE / GALA at their fixed micros; one position at a time (A) / both (B, same direction). Plan-sized profit, worst closed-trade drawdown, trades per week, skips."""
    p = p or P; lo, hi = SLICES[win]; dd = days[lo:hi]; mll = p["mll"]; kd = p["kill"]; mg = p["margin"]; dll = p["dll"]; cost = p["cost"]
    nn = c["nn"]; qf = nn
    if c["grow"]:
        e = int(mll // c["grow"]) - 1
        if e > 0: qf = nn + e
        qf = min(qf, c["gmax"])
    room0 = min(mll - kd, dll)
    both = bool(c["both"])
    eq = pk = ddn = 0.0; taken = [0, 0, 0, 0]; sig = [0, 0, 0, 0]; skip_open = [0, 0, 0, 0]; size0 = [0, 0, 0, 0]; t1 = 0.0
    for tl in dd:
        openp = []
        for (m_in, m_out, kind, a, b, cc, d, dr) in tl:
            sig[kind] += 1
            for o in sorted([o for o in openp if o[0] < m_in or (kind in (0, 2) and o[1] == kind and o[0] - 0.5 <= m_in)], key=lambda o: o[0]):
                eq += o[2]; pk = max(pk, eq); ddn = max(ddn, pk - eq)
            openp = [o for o in openp if not (o[0] < m_in or (kind in (0, 2) and o[1] == kind and o[0] - 0.5 <= m_in))]
            if openp and (not both or any(o[3] != dr for o in openp)): skip_open[kind] += 1; continue
            if kind == 0 or kind == 2:
                q = qf; pq = None
                if kind == 2 and not c["fsh"]:
                    while q > 0 and q * cc + mg > room0: q -= 1
                    if q > 0: pq = q * a
                else:
                    while q > 0:
                        S_ = cc
                        if q * cc > SHR * room0:
                            pt = math.floor(((SHR * room0 / q) - FEE) / TV - SLIP)
                            if pt * 0.25 < MINP * d or pt <= 0: q = -1; break
                            S_ = pt * TV + FEE + TV
                        if q * S_ + mg <= room0:
                            pq = q * (-S_ if (S_ < cc and b >= S_) else a); break
                        q -= 1
                if q <= 0 or pq is None: size0[kind] += 1; continue
            else:
                per = b / 0.25 * TV + FEE + 2 * SLIP * TV
                q = c["nc"] if kind == 1 else c["ng"]
                while q >= 1 and q * per + mg > room0: q -= 1
                if q < 1: size0[kind] += 1; continue
                pq = q * (a * PV - cost)
            taken[kind] += 1; openp.append([m_out, kind, pq, dr])
        for o in sorted(openp, key=lambda o: o[0]):
            eq += o[2]; pk = max(pk, eq); ddn = max(ddn, pk - eq)
    return dict(profit=eq, dd=ddn, tpw=sum(taken) / (len(dd) / 5.0), taken=taken, sig=sig, skip_open=skip_open, size0=size0, qf=qf)


# ------------------------------------------------------------------------------------------------------------------ bootstrap
def boot_paths(L, paths=600, cap=400, block=10, seed=7):
    return F.boot_paths(L, paths, cap, block, seed)


def bd_days(days, win):
    """per-day tables on the BUSINESS days of the window (holidays = empty days), the day axis of the session-20/21 bootstrap protocol (pf_sim.bdays)."""
    m = dict(zip(ALL_D, days))
    return [m.get(d, ()) for d in F.bdays(win)]


def boot_paths_for(win, paths=600, cap=400, seed=7):
    return F.boot_paths(len(F.bdays(win)), paths, cap, 10, seed)


def boot(days, c, win="ALL", paths=600, cap=400, seed=7, both=False, p=None):
    """session-20/21 protocol on one window (pf_sim.run_boot): business-day axis, 10-day blocks, 600 paths x 400 sessions, seed 7."""
    p = p or P; dd = bd_days(days, win); f = sim_b if both else sim_a; ct = sim_tuple(c); gm = gmin()
    res = [f(dd, pth, p, ct, gm) for pth in F.boot_paths(len(dd), paths, cap, 10, seed)]
    o = np.array([OC[r[0]] for r in res], dtype=np.int8); n = np.array([r[1] for r in res], dtype=np.int32)
    return summ(o, n)


# ------------------------------------------------------------------------------------------------------------------ one-config evaluation + parallel runner
_tabs = {}


def table_for(c, fade_hindsight=False):
    k = (c["stop"], c["trig"], c["mx"], c["mon"], c["fade"], c["cwin"] if c["nc"] else 0, c["gala"], fade_hindsight)
    if k not in _tabs:
        if len(_tabs) > 40: _tabs.pop(next(iter(_tabs)))
        _tabs[k] = build_days(c, fade_hindsight)
    return _tabs[k]


def evaluate(c, static_wins=("ALL", "PICK", "JUDGE"), keep_detail=False):
    """rolling starts on ALL / PICK / JUDGE + renewal chains (ALL) + static replay. Metrics are plain floats (JSON friendly)."""
    days = table_for(c); both = bool(c["both"]); out = {}
    for w in ("ALL", "PICK", "JUDGE"):
        o, n, cp, cb = roll(days, c, w, both=both)
        out[w] = summ(o, n)
        if w == "ALL":
            out["chain"] = chain(o, n)
            if keep_detail: out["detail"] = (o.tolist(), n.tolist())
    out["static"] = {w: static(days, c, w) for w in static_wins}
    return out


def _worker(c):
    return cfg_key(c), evaluate(c)


def run_many(cfgs, procs=2, chunk=8, label=""):
    """evaluate configs in parallel (at most 2 worker processes on this shared box); returns {cfg_key: metrics}"""
    import multiprocessing as mp
    t0 = time.time(); res = {}
    if procs <= 1:
        for i, c in enumerate(cfgs):
            k, r = _worker(c); res[k] = r
        return res
    with mp.Pool(procs) as pool:
        for i, (k, r) in enumerate(pool.imap_unordered(_worker, cfgs, chunksize=chunk)):
            res[k] = r
            if (i + 1) % 200 == 0: print(f"  {label} {i + 1}/{len(cfgs)}  {time.time() - t0:.0f}s", flush=True)
    return res
