"""eval_speed_engine.py - eval-only speed/pass study engine (session 11 final push).
Extends docs/results/session11/pm_fade_d57_study.py (the engine that reproduces the LIVE-rule eval numbers) with knobs:
 checks step (60/30 min), maxtr, opening-drive (od_t copied from session10/five_year/run_b.py; keeps pause floor + structural stop),
 shrink / min_pct, unfreeze tier (fixed $ stop when DRAWDOWN_TOO_DEEP), recover (retry with fewer micros), sizer paths,
 day cap, optional consistency requirement. Defaults == live rules (verified: `eval_speed_engine.py verify`)."""
import sys, math
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/user/opogabuuga/backend"); sys.path.insert(0, "/home/user/opogabuuga/docs/results/session11")
import numpy as np
import base_sim as B
import pm_fade_d57_study as P
from base_sim import PV, TICK, FEE, TV, SLIP, MARGIN, first_hit, trade_stop_exit, per_contract
NA = B.NA
C60 = list(range(29, 360, 60)); C30 = list(range(29, 360, 30))
SPLIT = "2023-12-31"; KILL = 50; STALL_N = 20
_cache = {}
_ld = NA.load_days
def _load(csv):
    if csv not in _cache: _cache[csv] = _ld(csv)
    return _cache[csv]
NA.load_days = _load

def od_t(days, i):
    d, a = days[i]; o, h, l, c = a["open"], a["high"], a["low"], a["close"]
    pc = days[i - 1][1]["close"][389]
    if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: return None
    rngs = [np.nanmax(x["high"]) - np.nanmin(x["low"]) for _, x in days[max(0, i - 14):i]]
    if len(rngs) < 10: return None
    move = c[29] - o[0]
    if not abs(move) >= 0.35 * np.mean(rngs) or move == 0: return None
    s = 1 if move > 0 else -1
    ext = np.nanmax(h[:30]) if s > 0 else np.nanmin(l[:30])
    leg = abs(ext - o[0]); entry = ext - s * 0.382 * leg; stop = ext - s * 0.786 * leg; tgt = ext
    fill = None
    for k in range(30, 181):
        if (s > 0 and l[k] <= entry - TICK) or (s < 0 and h[k] >= entry + TICK): fill = k; break
    if fill is None: return None
    sp = abs(entry - stop) + TICK
    for k in range(fill, 210):
        if (s > 0 and l[k] <= stop) or (s < 0 and h[k] >= stop): return fill, k, (stop - s * TICK - entry) * s * PV - FEE, sp
        if (s > 0 and h[k] >= tgt) or (s < 0 and l[k] <= tgt): return fill, k, (tgt - entry) * s * PV - FEE, sp
    px = c[209] - s * TICK
    return fill, 209, (px - entry) * s * PV - FEE, sp

def prep_all():
    B.CHECKS = C30
    DAYS = B.prep(); days = _load(B.CSV)
    for i, (d, a) in enumerate(days):
        if d in DAYS: DAYS[d].od = od_t(days, i) if i >= 1 else None
    names, objs = B.calendar(DAYS)
    return names, objs

def decide(dist, n, entry, bp, dll_left, cfg, keep_floor=False):
    """live checks.pretrade rule. -> (take, stop_pts, reason). keep_floor = PM_FADE / OPEN_DRIVE path (pause floor, no shrink)."""
    if keep_floor and dist < 500 and not cfg.get("fade_tighten"): return False, 0, "PAUSE"
    if not dist > KILL: return False, 0, "NEAR"
    room0 = dist - KILL
    if dll_left is not None: room0 = min(room0, dll_left)
    ticks = bp / TICK; usd = n * per_contract(ticks)
    if not keep_floor or cfg.get("fade_tighten"):
        allowed = room0 * cfg.get("shrink", 0.6)
        if usd > allowed:
            ticks = math.floor((allowed / n - FEE) / TV - SLIP)
            if ticks * TICK < entry * cfg.get("min_pct", 0.002):
                tier = cfg.get("tier")
                if tier is None: return False, 0, "DEEP"
                ticks = min(bp, P.pts_of(tier)) / TICK      # un-freeze: fixed small stop, only the plain worst-case check below
            usd = n * per_contract(ticks)
    if not usd + MARGIN <= room0: return False, 0, "WORST"
    return True, ticks * TICK, None

def decide_q(dist, q, entry, bp, dll_left, cfg, keep_floor=False):
    take, pts, why = decide(dist, q, entry, bp, dll_left, cfg, keep_floor)
    if not take and cfg.get("recover") and q > 1 and why in ("DEEP", "WORST"):
        for n in range(q - 1, 0, -1):
            take, pts, why = decide(dist, n, entry, bp, dll_left, cfg, keep_floor)
            if take: return True, pts, n
    return take, pts, q

def day_sim(D, bal, floor, q, cfg, lockv):
    """-> (bal, busted, n_taken)"""
    bp = cfg["bp"]; dll = cfg.get("dll"); CH = cfg.get("checks", C60); maxtr = cfg.get("maxtr", 3)
    ntr = 0; taken = 0; tk_all = 0; idx = 0; n = len(CH); o, c = D.o, D.c
    S = [bal, 0.0, 0.0]   # bal, day, daypeak
    def dll_left(): return None if dll is None else dll - (max(0.0, S[2], S[1]) - S[1])
    def settle(p):
        if dll is not None and S[1] + p <= -dll: p = -dll - S[1]
        S[0] += p; S[1] += p; S[2] = max(S[2], S[1]); return S[0] <= floor
    def stopday(): return (dll is not None and S[1] <= -dll) or (lockv is not None and S[1] > 0 and S[1] >= lockv)
    od = D.od if cfg.get("od") else None
    def run_od():
        fill, xk, p, sp = od
        take, _, nq = decide_q(S[0] - floor, q, 0, sp, dll_left(), cfg, True)
        if not take: return None
        return settle(p * nq), xk
    kstart = 0
    if D.noise_ok or od:
        while idx < n and D.noise_ok:
            k = CH[idx]
            if k < kstart: idx += 1; continue
            if ntr >= maxtr or stopday(): break
            side = D.side.get(k, 0)
            if side == 0: idx += 1; continue
            if od and od[0] <= k:
                if od[0] >= kstart:
                    r = run_od(); od = None
                    if r:
                        tk_all += 1
                        if r[0]: return S[0], True, tk_all
                        kstart = r[1]; continue
                od = None
            ntr += 1
            ek = next((j for j in range(k + 1, 390) if not np.isnan(c[j])), None)
            if ek is None: idx += 1; continue
            entry = o[ek] + side * TICK
            take, pts, nq = decide_q(S[0] - floor, q, entry, bp, dll_left(), cfg)
            if not take: idx += 1; continue
            taken += 1; tk_all += 1
            stop = entry - side * pts
            so = trade_stop_exit(D, side, entry, ek, stop)
            j = so[1] if so else None
            ex = None
            for ci in range(idx, n):
                kc = CH[ci]
                if kc < ek: continue
                if j is not None and kc >= j: break
                if kc in D.trail and D.trail[kc][0 if side > 0 else 1]:
                    nk = kc + 1
                    px = (o[nk] if nk < 390 and not np.isnan(o[nk]) else c[kc]) - side * TICK
                    ex = ((px - entry) * side * PV - FEE, kc, "check"); break
            if ex is None and so is not None: ex = (so[0], so[1], "stop")
            if ex is None:
                lastv = max(j2 for j2 in range(390) if not np.isnan(c[j2]))
                ex = ((c[lastv] - side * TICK - entry) * side * PV - FEE, 389, "eod")
            pnl_pm, xb, kind = ex
            if settle(pnl_pm * nq): return S[0], True, tk_all
            if kind == "check": idx = CH.index(xb); kstart = xb
            elif kind == "stop": kstart = xb; idx = next((i for i in range(n) if CH[i] >= xb), n)
            else: kstart = 390; break
        if od and od[0] >= kstart and not stopday():
            r = run_od()
            if r:
                tk_all += 1
                if r[0]: return S[0], True, tk_all
    if taken == 0 and D.fade is not None and not stopday():
        k, s, e, tgt = D.fade
        take, pts, nq = decide_q(S[0] - floor, q, e, cfg.get("fade_bp", bp), dll_left(), cfg, True)
        if not take: return S[0], False, tk_all
        tk_all += 1
        stop = e - s * pts
        seg_s = (D.l[k + 1:386] <= stop) if s > 0 else (D.h[k + 1:386] >= stop)
        seg_t = (D.h[k + 1:386] >= tgt) if s > 0 else (D.l[k + 1:386] <= tgt)
        js, jt = first_hit(seg_s), first_hit(seg_t)
        if js is not None and (jt is None or js <= jt):
            j = js + k + 1; px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK
            p = (px - e) * s * PV - FEE
        elif jt is not None: p = (tgt - e) * s * PV - FEE
        else: p = (c[385] - s * TICK - e) * s * PV - FEE
        if settle(p * nq): return S[0], True, tk_all
    return S[0], False, tk_all

def size(cfg, cush, rem):
    MLL, TARGET = cfg["MLL"], cfg["TARGET"]; q0 = cfg["q"]; sz = cfg.get("sizer")
    def live():
        q = q0; g = cfg.get("grow")
        if g: q = min(g[1], q0 + max(0, int(cush // g[0]) - 1))
        if cfg.get("taper") and rem < cfg["taper"] * TARGET: q = min(q, cfg.get("taper_q", 1))
        br = cfg.get("brake")
        if br and cush < br[0] * MLL: q = min(q, br[1])
        return q
    if not sz: return live()
    if sz[0] == "front":      # (front, qhi, thr): qhi while cushion >= thr*MLL, else the live table
        return sz[1] if cush >= sz[2] * MLL else live()
    if sz[0] == "prop":       # (prop, unit_usd, qmin, qmax): q = cushion // unit
        return int(max(sz[2], min(sz[3], cush // sz[1])))
    if sz[0] == "ladder":     # (ladder, [(thr_frac, q), ...] descending)
        for thr, q in sz[1]:
            if cush >= thr * MLL: return q
        return sz[1][-1][1]
    raise ValueError(sz)

def run_eval(objs, i0, cfg, horizon):
    S0, TARGET, MLL, LOCKT, LOCKL = cfg["S0"], cfg["TARGET"], cfg["MLL"], cfg["LOCKT"], cfg["LOCKL"]
    bal = peak = S0; floor = S0 - MLL; npos = 0; idle = 0; maxday = 0.0
    end = min(len(objs), i0 + horizon); cons = cfg.get("consist")
    for n, i in enumerate(range(i0, end)):
        D = objs[i]; rem = TARGET - (bal - S0); cush = bal - floor
        q = size(cfg, cush, rem)
        if cfg.get("end_taper") and rem < cfg["end_taper"][0] * TARGET: q = min(q, cfg["end_taper"][1])
        lockv = cfg["lock_pct"] * rem if cfg.get("lock_pct") else None
        if cfg.get("day_cap"): lockv = min(lockv, cfg["day_cap"] * TARGET) if lockv is not None else cfg["day_cap"] * TARGET
        b0 = bal; tk = 0
        if D is not None:
            bal, bust, tk = day_sim(D, bal, floor, q, cfg, lockv)
            if bust: return "BUST", n + 1
        idle = idle + 1 if tk == 0 else 0
        if idle >= STALL_N: return "STALL", n + 1
        if bal - b0 > 0: npos += 1
        maxday = max(maxday, bal - b0)
        peak = max(peak, bal)
        floor = LOCKL if peak >= LOCKT else max(floor, peak - MLL)
        if bal - S0 >= TARGET and npos >= 1 and (not cons or maxday <= cons * (bal - S0)): return "PASS", n + 1
    return "OPEN", end - i0

def evaluate(cfg, names, objs, H):
    starts = list(range(0, len(objs) - H, 2))
    res = [run_eval(objs, i, cfg, H) for i in starts]
    era = np.array([names[i] <= SPLIT for i in starts])
    def summ(mask):
        r = [x for x, m in zip(res, mask) if m]; n = len(r); ps = [s for sx, s in r if sx == "PASS"]
        f = lambda t: round(100 * sum(sx == t for sx, _ in r) / n, 1)
        return dict(n=n, pas=f("PASS"), bust=f("BUST"), frozen=f("STALL"), open=f("OPEN"), med=float(np.median(ps)) if ps else float("nan"),
                    spp=round(sum(s for _, s in r) / max(1, len(ps)), 1))   # sessions consumed (all attempts) per pass
    return dict(IS=summ(era), OOS=summ(~era))

def base_cfgs():
    V = P.load_views(); c = P.eval_configs(V, "code")
    return {"25K": c["25K Regular (1x$250)"], "25K-HR": c["25K High risk (3x$150 taper)"], "50K": c["50K"], "100K": c["100K"], "150K": c["150K"]}
HZ = {"25K": 120, "25K-HR": 120, "50K": 120, "100K": 250, "150K": 250}

if __name__ == "__main__":
    import time; t = time.time()
    names, objs = prep_all(); print("prep", round(time.time() - t), "s")
    for k, cfg in base_cfgs().items():
        t = time.time(); r = evaluate(cfg, names, objs, HZ[k])
        a, b = r["IS"], r["OOS"]; n = a["n"] + b["n"]
        print(k, {x: cfg[x] for x in ("S0", "TARGET", "MLL", "dll", "q")}, "ALL pass %.1f frozen %.1f bust %.1f" % tuple((a[x] * a["n"] + b[x] * b["n"]) / n for x in ("pas", "frozen", "bust")), "IS", a, "OOS", b, round(time.time() - t), "s")
