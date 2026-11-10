"""PM_FADE under D57? V0 = fade as coded (controller.py:508: no shrink -> pause floor $500 + plain worst-case check, $250 stop never tightened)
vs V1 = fade covered like NOISE (stop tightened by checks.pretrade rule: allowed = 0.6 x min(DLL left, equity - MLL - kill); new stop < 0.2% of price -> DRAWDOWN_TOO_DEEP;
scaled -> pause floor bypassed), same VWAP target. Engine = copy of session10/five_year/kill_study.py (itself a copy of eval25k_total_risk.py's verified per-trade
1-minute simulator) with: 100K plan, Eval-Mode size tables (grow / brake / taper / day lock-in), fade-only skip counters.
usage: pm_fade_d57_study.py verify | run"""
import sys, json, math
sys.dont_write_bytecode = True
sys.path.insert(0, "/home/user/opogabuuga/backend")
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session11")
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import base_sim as B
from base_sim import PV, TICK, FEE, TV, SLIP, MARGIN, MIN_PCT, CHECKS, first_hit, trade_stop_exit, per_contract

OUT = B.OUT
SHRINK = 0.6
STALL_N = 20
ERA_SPLIT = "2023-12-31"
RULES_DIR = Path("/home/user/opogabuuga/config/rules")

# ------------------------------------------------------------ stats vector layout
(I_SIG, I_SKIP, I_STOPSUM, I_TAKEN, I_QSUM) = range(5)
NB = 5          # NOISE block start; FADE block = NB + 10
# block: n, wins, sumwin, losses, sumloss, stopouts, tightened, tight_stopouts
(K_N, K_W, K_SW, K_L, K_SL, K_STOP, K_TIGHT, K_TSTOP) = range(8)
I_NEAR, I_DEEP, I_WORST, I_PAUSE = 25, 26, 27, 28
I_Z100, I_Z50, I_Z0, I_ZK = 29, 30, 31, 32      # trades whose intraday equity came within $100 / $50 / $0 / kill of the floor
I_X0, I_X25, I_X40, I_X50, I_XSUM, I_XMAX = 33, 34, 35, 36, 37, 38
I_KS = 39      # realised equity after a trade within the kill distance of the floor (controller would kill-switch + pause, never auto-resume)  # loss beyond planned worst case
I_FSIG, I_FSKIP, I_FDEEP, I_FPAUSE, I_FWORST, I_FNEAR = 40, 41, 42, 43, 44, 45
NS = 46
def zeros(): return np.zeros(NS)
def agg(sts):
    a = np.sum(sts, axis=0); a[I_XMAX] = np.max([s[I_XMAX] for s in sts]) if len(sts) else 0
    return a

# ------------------------------------------------------------ live rule
def decide(bal, floor, n, entry, bp, kill, dll_left, rule="live", is_fade=False, fade_mode="tighten"):
    """-> (take, stop_pts, reason, tightened). rule 'none' = study assumption (no check at all)."""
    if rule == "none": return True, bp, None, False
    dist = bal - floor
    if is_fade and fade_mode == "code":
        # live controller applies shrink only to NOISE/AI_BIAS; PM_FADE keeps the pause floor ($500 risk base) and the worst-case check
        if dist < 500: return False, 0, "PAUSE", False
    if not dist > kill: return False, 0, "NEAR", False
    room0 = dist - kill
    if dll_left is not None: room0 = min(room0, dll_left)
    base_ticks = bp / TICK
    usd = n * per_contract(base_ticks); ticks = base_ticks; tight = False
    if not (is_fade and fade_mode == "code"):
        allowed = room0 * SHRINK
        if usd > allowed:
            ticks = math.floor((allowed / n - FEE) / TV - SLIP)
            if ticks * TICK < entry * MIN_PCT: return False, 0, "DEEP", False
            usd = n * per_contract(ticks); tight = True
    if not usd + MARGIN <= room0: return False, 0, "WORST", False
    return True, ticks * TICK, None, tight

def wmin(D, s, entry, a, b):
    """worst gross unrealised $ per micro over bars a..b inclusive (<= 0 typically)"""
    if b < a: return 0.0
    seg = D.l[a:b + 1] if s > 0 else D.h[a:b + 1]
    if np.all(np.isnan(seg)): return 0.0
    w = (np.nanmin(seg) - entry) if s > 0 else (entry - np.nanmax(seg))
    return w * PV

class Acc:  # per-run mutable state shared by day_sim
    pass

def record(st, t, qq, pts, base_pts, tight, kind, pnl_pm, worst_pm, bal0, floor, kill, rule):
    p = pnl_pm * qq; b = NB + 10 * t
    st[I_TAKEN] += 1; st[I_QSUM] += qq; st[I_STOPSUM] += pts * PV
    st[b + K_N] += 1
    if p > 0: st[b + K_W] += 1; st[b + K_SW] += p
    else: st[b + K_L] += 1; st[b + K_SL] += p
    if kind == "stop": st[b + K_STOP] += 1
    if tight:
        st[b + K_TIGHT] += 1
        if kind == "stop": st[b + K_TSTOP] += 1
    md = bal0 + qq * min(worst_pm, pnl_pm) - floor
    if md <= 100: st[I_Z100] += 1
    if md <= 50: st[I_Z50] += 1
    if md <= 0: st[I_Z0] += 1
    if kill and md <= kill: st[I_ZK] += 1
    if rule != "none":
        planned = qq * per_contract(pts / TICK)
        x = -p - planned
        if x > 0:
            st[I_X0] += 1; st[I_XSUM] += x; st[I_XMAX] = max(st[I_XMAX], x)
            if x > 25: st[I_X25] += 1
            if x > 40: st[I_X40] += 1
            if x > 50: st[I_X50] += 1

REASON_IDX = {"NEAR": I_NEAR, "DEEP": I_DEEP, "WORST": I_WORST, "PAUSE": I_PAUSE}

def day_sim(D, bal, floor, q, cfg, kill, st, slipx=0.0):
    """one session. cfg: bp, dll, rule, fade_mode. returns (bal, busted)"""
    rule = cfg["rule"]; bp = cfg["bp"]; dll = cfg.get("dll"); fm = cfg.get("fade_mode", "tighten")
    ntr = 0; taken = 0; idx = 0; n = len(CHECKS); o, c = D.o, D.c
    A = Acc(); A.bal = bal; A.day = 0.0; A.dpk = 0.0
    def dll_left():
        if dll is None: return None
        return dll - (max(0.0, A.dpk, A.day) - A.day)
    def settle(p_total):
        if dll is not None and A.day + p_total <= -dll: p_total = -dll - A.day      # soft DLL: day stops at -DLL
        A.bal += p_total; A.day += p_total; A.dpk = max(A.dpk, A.day)
        if kill and floor < A.bal <= floor + kill: st[I_KS] += 1
        return A.bal <= floor
    def dll_hit(): return (dll is not None and A.day <= -dll) or (cfg.get("lockv") is not None and A.day > 0 and A.day >= cfg["lockv"])
    if D.noise_ok:
        kstart = 0
        while idx < n:
            k = CHECKS[idx]
            if k < kstart: idx += 1; continue
            if ntr >= 3 or dll_hit(): break
            side = D.side.get(k, 0)
            if side == 0: idx += 1; continue
            ntr += 1
            ek = next((j for j in range(k + 1, 390) if not np.isnan(c[j])), None)
            if ek is None: idx += 1; continue
            entry = o[ek] + side * TICK
            take, pts, why, tight = decide(A.bal, floor, q, entry, bp, kill, dll_left(), rule)
            st[I_SIG] += 1
            if not take: st[I_SKIP] += 1; st[REASON_IDX[why]] += 1; idx += 1; continue
            taken += 1
            stop = entry - side * pts
            so = trade_stop_exit(D, side, entry, ek, stop)
            j = so[1] if so else None
            ex = None
            for ci in range(idx, n):
                kc = CHECKS[ci]
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
            if kind == "stop": pnl_pm -= slipx / q
            if kind == "stop":
                w = min(wmin(D, side, entry, ek, xb - 1), (pnl_pm + FEE))
            else:
                w = wmin(D, side, entry, ek, min(xb, 389))
            bal0 = A.bal
            busted = settle(pnl_pm * q)
            record(st, 0, q, pts, bp, tight, kind, pnl_pm, w, bal0, floor, kill, rule)
            if busted: return A.bal, True
            if kind == "check": idx = CHECKS.index(xb); kstart = xb
            elif kind == "stop": kstart = xb; idx = next((i for i in range(n) if CHECKS[i] >= xb), n)
            else: break
    if taken == 0 and D.fade is not None and not dll_hit():
        k, s, e, tgt = D.fade
        take, pts, why, tight = decide(A.bal, floor, q, e, bp, kill, dll_left(), rule, True, fm)
        st[I_SIG] += 1; st[I_FSIG] += 1
        if not take:
            st[I_SKIP] += 1; st[REASON_IDX[why]] += 1; st[{"DEEP": I_FDEEP, "PAUSE": I_FPAUSE, "WORST": I_FWORST, "NEAR": I_FNEAR}[why]] += 1; st[I_FSKIP] += 1
            return A.bal, False
        stop = e - s * pts
        seg_s = (D.l[k + 1:386] <= stop) if s > 0 else (D.h[k + 1:386] >= stop)
        seg_t = (D.h[k + 1:386] >= tgt) if s > 0 else (D.l[k + 1:386] <= tgt)
        js, jt = first_hit(seg_s), first_hit(seg_t)
        if js is not None and (jt is None or js <= jt):
            j = js + k + 1; px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK
            p = (px - e) * s * PV - FEE - slipx / q; kind = "stop"
            w = min(wmin(D, s, e, k + 1, j - 1), p + FEE)
        elif jt is not None:
            p = (tgt - e) * s * PV - FEE; kind = "tp"; w = wmin(D, s, e, k + 1, jt + k + 1)
        else:
            p = (c[385] - s * TICK - e) * s * PV - FEE; kind = "eod"; w = wmin(D, s, e, k + 1, 385)
        bal0 = A.bal
        busted = settle(p * q)
        record(st, 1, q, pts, bp, tight, kind, p, w, bal0, floor, kill, rule)
        if busted: return A.bal, True
    return A.bal, False

# ------------------------------------------------------------ eval engine
def run_eval(objs, i0, cfg, kill, horizon, st, slipx=0.0):
    S0, TARGET, MLL, LOCKT, LOCKL = cfg["S0"], cfg["TARGET"], cfg["MLL"], cfg["LOCKT"], cfg["LOCKL"]
    q0, taper, brake = cfg["q"], cfg.get("taper"), cfg.get("brake")
    bal = peak = S0; floor = S0 - MLL; npos = 0; idle = 0
    end = len(objs) if horizon is None else min(len(objs), i0 + horizon)
    for n, i in enumerate(range(i0, end)):
        D = objs[i]; q = q0; rem = TARGET - (bal - S0); cush = bal - floor
        g = cfg.get("grow")
        if g: q = min(g[1], q0 + max(0, int(cush // g[0]) - 1))
        if taper and rem < taper * TARGET: q = min(q, cfg.get("taper_q", 1))
        if brake and cush < brake[0] * MLL: q = min(q, brake[1])
        cfg = {**cfg, "lockv": (cfg["lock_pct"] * rem) if cfg.get("lock_pct") else None}
        b0 = bal; t0 = st[I_TAKEN]
        if D is not None:
            bal, bust = day_sim(D, bal, floor, q, cfg, kill, st, slipx)
            if bust: return "BUST", n + 1
        idle = idle + 1 if st[I_TAKEN] == t0 else 0
        if idle >= STALL_N: return "STALL", n + 1
        if bal - b0 > 0: npos += 1
        peak = max(peak, bal)
        floor = LOCKL if peak >= LOCKT else max(floor, peak - MLL)
        if bal - S0 >= TARGET and npos >= 1: return "PASS", n + 1
    return "OPEN", end - i0

def evaluate(cfg, kill, names, objs, H=120, slipx=0.0, chain=True):
    chain_on = chain
    starts = list(range(0, len(objs) - H, 2))
    res, sts = [], []
    for i in starts:
        st = zeros(); res.append(run_eval(objs, i, cfg, kill, H, st, slipx)); sts.append(st)
    tot = agg(sts)
    chain = [] if chain_on else [None] * len(starts); dummy = zeros()
    for i in (starts if chain_on else []):
        t, tt, ok = i, 0, False
        while t < len(objs):
            s, n = run_eval(objs, t, cfg, kill, None, dummy, slipx); tt += n
            if s == "PASS": ok = True; break
            if s == "OPEN": break
            t += n
        chain.append(tt if ok else None)
    era = np.array([names[i] <= ERA_SPLIT for i in starts])
    def summ(mask):
        r = [x for x, m in zip(res, mask) if m]; c = [x for x, m in zip(chain, mask) if m]
        n = len(r); ps = [s for sx, s in r if sx == "PASS"]; cc = [x for x in c if x is not None]
        return dict(n=n, pass_=len(ps) / n, bust=sum(sx == "BUST" for sx, _ in r) / n, frozen=sum(sx == "STALL" for sx, _ in r) / n,
                    open_=sum(sx == "OPEN" for sx, _ in r) / n, med=float(np.median(ps)) if ps else float("nan"),
                    p75=float(np.percentile(ps, 75)) if ps else float("nan"),
                    chain_med=float(np.median(cc)) if cc else float("nan"), chain_cens=1 - len(cc) / len(c))
    a = summ(np.ones(len(res), bool)); a.update(trade_stats(tot))
    return dict(all=a, e1=summ(era), e2=summ(~era))

def trade_stats(t):
    d = {}
    def blk(b, nm):
        n, w, sw, l, sl = t[b + K_N], t[b + K_W], t[b + K_SW], t[b + K_L], t[b + K_SL]
        d[nm + "_n"] = n; d[nm + "_wr"] = w / n if n else float("nan")
        d[nm + "_aw"] = sw / w if w else float("nan"); d[nm + "_al"] = sl / l if l else float("nan")
        d[nm + "_pf"] = sw / -sl if sl else float("nan")
        d[nm + "_stop"] = t[b + K_STOP] / n if n else float("nan")
        d[nm + "_tight"] = t[b + K_TIGHT] / n if n else float("nan")
        d[nm + "_tstop"] = t[b + K_TSTOP] / n if n else float("nan")
        d[nm + "_stop_of_tight"] = t[b + K_TSTOP] / t[b + K_TIGHT] if t[b + K_TIGHT] else float("nan")
        d[nm + "_net"] = sw + sl
    blk(NB, "noise"); blk(NB + 10, "fade")
    both = np.array(t, copy=True); both[NB:NB + 8] += t[NB + 10:NB + 18]
    blk(NB, "all")
    n = both[NB + K_N]
    d["all_n"] = n; d["all_wr"] = both[NB + K_W] / n if n else float("nan")
    d["all_aw"] = both[NB + K_SW] / both[NB + K_W] if both[NB + K_W] else float("nan")
    d["all_al"] = both[NB + K_SL] / both[NB + K_L] if both[NB + K_L] else float("nan")
    d["all_pf"] = both[NB + K_SW] / -both[NB + K_SL] if both[NB + K_SL] else float("nan")
    d["all_stop"] = both[NB + K_STOP] / n if n else float("nan")
    d["all_tight"] = both[NB + K_TIGHT] / n if n else float("nan")
    d["all_tstop"] = both[NB + K_TSTOP] / n if n else float("nan")
    d["all_stop_of_tight"] = both[NB + K_TSTOP] / both[NB + K_TIGHT] if both[NB + K_TIGHT] else float("nan")
    d["all_net"] = both[NB + K_SW] + both[NB + K_SL]
    sig = t[I_SIG]
    d.update(signals=sig, skip_share=t[I_SKIP] / sig if sig else 0.0, near=t[I_NEAR] / sig if sig else 0, deep=t[I_DEEP] / sig if sig else 0,
             worst=t[I_WORST] / sig if sig else 0, pause=t[I_PAUSE] / sig if sig else 0,
             avg_stop_usd=t[I_STOPSUM] / t[I_TAKEN] if t[I_TAKEN] else float("nan"), avg_q=t[I_QSUM] / t[I_TAKEN] if t[I_TAKEN] else float("nan"),
             z100=t[I_Z100], z50=t[I_Z50], z0=t[I_Z0], zk=t[I_ZK], x0=t[I_X0], x25=t[I_X25], x40=t[I_X40], x50=t[I_X50], xmax=t[I_XMAX], xsum=t[I_XSUM], ks=t[I_KS],
             taken=t[I_TAKEN], fsig=t[I_FSIG], fskip=t[I_FSKIP], fdeep=t[I_FDEEP], fpause=t[I_FPAUSE], fworst=t[I_FWORST], fnear=t[I_FNEAR])
    return d

# ------------------------------------------------------------ funded engine
def payout_amount(F, balance, cycle, n_paid):
    cp = sum(cycle)
    if cp < F["min_cycle"] or cp <= 0: return 0.0
    if F["consist"] is not None and max(cycle) > F["consist"] / 100 * cp: return 0.0
    if F["min_pd"] and sum(1 for x in cycle if x >= F["min_day"]) < F["min_pd"]: return 0.0
    amt = balance - F["buffer"]
    cap = F["max_first"] if n_paid == 0 else F["max_next"]
    if cap is not None: amt = min(amt, cap)
    amt = round(amt, 2)
    return amt if amt >= F["min_request"] else 0.0

def run_funded(objs, i0, cfg, kill, st, horizon=260, slipx=0.0):
    F = cfg["F"]; S0 = F["start"]; MLL = F["mll"]
    bal = peak = S0; floor = S0 - MLL; cycle = []; paid = 0.0; pays = 0; idle = 0; frozen = False
    for n, i in enumerate(range(i0, min(len(objs), i0 + horizon))):
        D = objs[i]; q = cfg["q"]
        br = cfg.get("brake")
        if br and bal - floor < br[0] * MLL: q = min(q, br[1])
        t0 = st[I_TAKEN]; day0 = bal
        if D is not None:
            bal, bust = day_sim(D, bal, floor, q, {**cfg, "dll": F["dll"]}, kill, st, slipx)
            if bust: return dict(paid=paid, status="BUST", pays=pays, frozen=frozen, n=n + 1)
        executed = st[I_TAKEN] != t0
        idle = 0 if executed else idle + 1
        if idle >= STALL_N: frozen = True
        if executed: cycle.append(bal - day0)       # funded_path appends the day P&L whenever the day had trades
        peak = max(peak, bal)
        floor = F["lock_level"] if peak >= F["lock_trigger"] else max(floor, peak - MLL)
        if (n + 1) % cfg["cadence"] == 0 and pays < F["max_payouts"]:
            amt = payout_amount(F, bal, cycle, pays)
            if amt > 0:
                bal -= amt; paid += round(amt * F["split"], 2); pays += 1; cycle = []
                if F["lock_on_payout"]: floor = max(floor, F["lock_level"])
        if pays >= F["max_payouts"]: return dict(paid=paid, status="MAX_PAYOUTS", pays=pays, frozen=frozen, n=n + 1)
    return dict(paid=paid, status="OPEN", pays=pays, frozen=frozen, n=min(horizon, len(objs) - i0))

def evaluate_funded(cfg, kill, names, objs, horizon=260, slipx=0.0):
    starts = list(range(0, len(objs) - horizon, 2))
    res, sts = [], []
    for i in starts:
        st = zeros(); res.append(run_funded(objs, i, cfg, kill, st, horizon, slipx)); sts.append(st)
    tot = agg(sts)
    era = np.array([names[i] <= ERA_SPLIT for i in starts])
    def summ(mask):
        r = [x for x, m in zip(res, mask) if m]; n = len(r); pd_ = np.array([x["paid"] for x in r])
        return dict(n=n, take=float(pd_.mean()), take_med=float(np.median(pd_)), bust=sum(x["status"] == "BUST" for x in r) / n,
                    frozen=sum(x["frozen"] for x in r) / n, maxpay=sum(x["status"] == "MAX_PAYOUTS" for x in r) / n,
                    anypay=sum(x["pays"] > 0 for x in r) / n, pays=float(np.mean([x["pays"] for x in r])))
    a = summ(np.ones(len(res), bool)); a.update(trade_stats(tot))
    return dict(all=a, e1=summ(era), e2=summ(~era))

# ------------------------------------------------------------ configs
def load_views():
    from app.config import load_rules
    from app.backtest.income_projection import rules_view, eval_view
    out = {}
    for p in ("25k", "50k", "100k", "150k"):
        rc = load_rules(RULES_DIR / f"lucid_pro_{p}.yaml").rules
        f, e = rules_view(rc), eval_view(rc)
        out[p] = dict(
            F=dict(start=float(f.start), mll=float(f.mll), lock_trigger=float(f.lock_trigger), lock_level=float(f.lock_level), dll=float(f.dll) if f.dll is not None else None,
                   split=float(f.split), buffer=float(f.buffer), min_request=float(f.min_request), min_cycle=float(f.min_cycle_profit),
                   max_first=float(f.max_first) if f.max_first is not None else None, max_next=float(f.max_next) if f.max_next is not None else None,
                   max_payouts=f.max_payouts, consist=float(f.consistency_pct) if f.consistency_pct is not None else None,
                   min_pd=f.min_profitable_days, min_day=float(f.min_day_profit), lock_on_payout=f.lock_mll_on_payout),
            E=dict(S0=float(e.start), TARGET=float(e.target), MLL=float(e.mll), LOCKT=float(e.lock_trigger), LOCKL=float(e.lock_level),
                   dll=float(e.dll) if e.dll is not None else None))
    return out

def pts_of(usd): return round(((usd - 2) / 2) / TICK) * TICK
KILL = 50
BP = pts_of(250)
PLAN_KEYS = ["25K Regular (1x$250)", "25K High risk (3x$150 taper)", "50K", "100K", "150K"]
def eval_configs(V, fm):
    c = {}
    c["25K Regular (1x$250)"] = dict(**V["25k"]["E"], q=1, bp=BP, rule="live", fade_mode=fm)
    c["25K High risk (3x$150 taper)"] = dict(**V["25k"]["E"], q=3, bp=pts_of(150), taper=0.5, rule="live", fade_mode=fm)
    c["50K"] = dict(**V["50k"]["E"], q=2, bp=BP, brake=(0.5, 1), rule="live", fade_mode=fm)                       # D66 eval row
    c["100K"] = dict(**V["100k"]["E"], q=2, bp=BP, brake=(0.3, 1), grow=(1200, 4), lock_pct=0.33, rule="live", fade_mode=fm)
    c["150K"] = dict(**V["150k"]["E"], q=4, bp=BP, brake=(0.5, 2), rule="live", fade_mode=fm)
    return c
HZ = {"25K Regular (1x$250)": 120, "25K High risk (3x$150 taper)": 120, "50K": 120, "100K": 250, "150K": 250}
def funded_configs(V, fm):
    c = {}
    c["25K x1, pay/10"] = dict(F=V["25k"]["F"], q=1, bp=BP, cadence=10, rule="live", fade_mode=fm)
    c["50K x2 brake<50%->1, pay/10"] = dict(F=V["50k"]["F"], q=2, bp=BP, brake=(0.5, 1), cadence=10, rule="live", fade_mode=fm)
    c["100K x2 brake<30%->1, pay/5"] = dict(F=V["100k"]["F"], q=2, bp=BP, brake=(0.3, 1), cadence=5, rule="live", fade_mode=fm)
    c["150K x3 brake<50%->2, pay/5"] = dict(F=V["150k"]["F"], q=3, bp=BP, brake=(0.5, 2), cadence=5, rule="live", fade_mode=fm)
    return c
G = {}
def init():
    G["names"], G["objs"] = B.calendar(B.prep()); G["V"] = load_views()
def work(job):
    kind, name, fm = job
    if kind == "E":
        cfg = eval_configs(G["V"], fm)[name]; r = evaluate(cfg, KILL, G["names"], G["objs"], H=HZ[name], chain=False)
    else:
        cfg = funded_configs(G["V"], fm)[name]; r = evaluate_funded(cfg, KILL, G["names"], G["objs"])
    return job, r
def run_jobs(jobs, procs=4):
    with Pool(procs, initializer=init) as p: return p.map(work, jobs, chunksize=1)

def verify():
    """V0 at kill 100 / 50 must reproduce kill_distance_report.md 'fade as in live controller' (Regular eval 49.7% -> 56.2%); V1 kill 50 = 56.0% (study main)."""
    init(); V = G["V"]; names, objs = G["names"], G["objs"]
    print("calendar", names[0], names[-1], len(names), "days with data", sum(o is not None for o in objs))
    for fm, k, ref in (("tighten", 100, "55.5% / 0 / 43.7% med 35"), ("tighten", 50, "56.0%"), ("code", 100, "49.7%"), ("code", 50, "56.2%")):
        r = evaluate(eval_configs(V, fm)["25K Regular (1x$250)"], k, names, objs, chain=False)["all"]
        print(f"E25 Regular fade={fm} kill {k}: pass {r['pass_']:.1%} bust {r['bust']:.1%} frozen {r['frozen']:.1%} med {r['med']:.0f} win {r['all_wr']:.1%} fadeWR {r['fade_wr']:.1%}  [report: {ref}]")
    cfg = eval_configs(V, "tighten")["25K Regular (1x$250)"]; cfg = {**cfg, "rule": "none"}
    r = evaluate(cfg, 100, names, objs, chain=False)["all"]; print("no rule:", f"{r['pass_']:.1%} / {r['bust']:.1%}", f"win {r['all_wr']:.1%} [study 63.4/34.4, 50.5%]")

def main():
    FN = ["25K x1, pay/10", "50K x2 brake<50%->1, pay/10", "100K x2 brake<30%->1, pay/5", "150K x3 brake<50%->2, pay/5"]
    jobs = [(k, n, fm) for fm in ("code", "tighten") for k, names in (("E", PLAN_KEYS), ("F", FN)) for n in names]
    res = run_jobs(jobs)
    out = [dict(kind=j[0], name=j[1], fm=j[2], **r) for j, r in res]
    Path(OUT).mkdir(parents=True, exist_ok=True)
    json.dump(out, open(f"{OUT}/results_pm_fade.json", "w"), indent=1, default=str)
    return out

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["verify"]: verify()
    elif a[:1] == ["run"]: main()
