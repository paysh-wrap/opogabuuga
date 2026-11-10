"""kelly_engine.py - account engine for the Kelly / cushion-sizing study. Imports ../pm_fade_d57_study.py (the engine that reproduces live results)
and adds two knobs, nothing else:
  cfg["lock"]  = (be_pts, lock_pts): NOISE profit lock replayed INTRADAY on 1-minute bars inside the engine (same logic as winrate_study.noise_t
                 be=100, lock=10, norefire=True): a 1-min close >= be pts in profit moves the stop to entry + lock pts from the next bar; a stop-out at a
                 locked stop ends NOISE for the day. D57 stop-tightening, kill $50, DLL etc. all still apply (no day-level approximation needed).
  cfg["kelly"] = (k, cap): size at each session start n = clamp(floor(k * cushion / 1000), 1, cap), cushion = balance - current MLL floor
                 (replaces the table's brake / grow rows; taper and day lock-in of the eval rows stay).
Funded "bust" here = DEAD account = balance <= MLL (hard) OR frozen (kill switch $50 above the MLL: 20 sessions with no trade possible, never recovers).
In this engine nearly every death is the frozen kind (the kill switch stops trading before the MLL is touched). Survivor = not dead.
With neither knob, day_sim / sizes are the unmodified live ones (P.day_sim is called directly)."""
import os as _os; ROOT = _os.environ.get("PAYTIENCE_ROOT") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..", ".."))
import sys as _s; _s.path.insert(0, ROOT + "/docs/results/session14"); import causal_fade as CF   # FADE_RULE=hindsight reproduces the old numbers
import sys, math
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT + "/docs/results/session11")
import numpy as np
import pm_fade_d57_study as P
import base_sim as B
from base_sim import PV, TICK, FEE, CHECKS, first_hit
from pm_fade_d57_study import decide, I_TAKEN, I_SIG, I_SKIP, STALL_N, KILL, BP
CHECKSET = set(CHECKS)
LOCK = (100.0, 10.0)

_LC = {}
def lock_exit(D, side, entry, ek, stop, be, lk):
    key = (id(D), side, ek, stop, be, lk); r = _LC.get(key)
    if r is None: r = _LC[key] = _lock_exit(D, side, entry, ek, stop, be, lk)
    return r
def _lock_exit(D, side, entry, ek, stop, be, lk):
    """-> (pnl_per_micro, bar, kind, locked_stop)"""
    o, h, l, c = D.o, D.h, D.l, D.c; hs = stop; last = None
    for k in range(ek, 390):
        if np.isnan(c[k]): continue
        last = k
        if (side > 0 and l[k] <= hs) or (side < 0 and h[k] >= hs):
            px = (min(hs, o[k]) if side > 0 else max(hs, o[k])) - side * TICK
            return (px - entry) * side * PV - FEE, k, "stop", (hs - entry) * side >= 0
        if k == 389: break
        if (c[k] - entry) * side >= be and (hs - entry) * side < lk: hs = entry + side * lk
        if k in CHECKSET and k in D.trail and D.trail[k][0 if side > 0 else 1]:
            nk = k + 1
            px = (o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - side * TICK
            return (px - entry) * side * PV - FEE, k, "check", False
    return (c[last] - side * TICK - entry) * side * PV - FEE, 389, "eod", False

def day_sim(D, bal, floor, q, cfg, kill, st, log=None):
    if cfg.get("lock") is None and log is None: return P.day_sim(D, bal, floor, q, cfg, kill, st)
    lockp = cfg.get("lock") or (1e18, 0.0)
    rule = cfg["rule"]; bp = cfg["bp"]; dll = cfg.get("dll"); fm = cfg.get("fade_mode", "tighten")
    ntr = 0; taken = 0; idx = 0; n = len(CHECKS); o, c = D.o, D.c
    S = dict(bal=bal, day=0.0, dpk=0.0)
    def dll_left():
        if dll is None: return None
        return dll - (max(0.0, S["dpk"], S["day"]) - S["day"])
    def settle(p):
        if dll is not None and S["day"] + p <= -dll: p = -dll - S["day"]
        S["bal"] += p; S["day"] += p; S["dpk"] = max(S["dpk"], S["day"])
        return S["bal"] <= floor
    def dll_hit(): return (dll is not None and S["day"] <= -dll) or (cfg.get("lockv") is not None and S["day"] > 0 and S["day"] >= cfg["lockv"])
    if D.noise_ok:
        kstart = 0
        while idx < n:
            k = CHECKS[idx]
            if k < kstart: idx += 1; continue
            if ntr >= 3 or dll_hit(): break
            side = D.side.get(k, 0)
            if side == 0: idx += 1; continue
            ntr += 1
            if CF.noise_blocked(D, k): idx += 1; continue   # session 14: causal fade open -> NOISE signal dropped
            ek = next((j for j in range(k + 1, 390) if not np.isnan(c[j])), None)
            if ek is None: idx += 1; continue
            entry = o[ek] + side * TICK
            take, pts, why, tight = decide(S["bal"], floor, q, entry, bp, kill, dll_left(), rule)
            st[I_SIG] += 1
            if not take: st[I_SKIP] += 1; idx += 1; continue
            taken += 1
            pnl, xb, kind, locked = lock_exit(D, side, entry, ek, entry - side * pts, *lockp)
            st[I_TAKEN] += 1
            if log is not None: log.append(("NOISE", pnl))
            if settle(pnl * q): return S["bal"], True
            if locked: ntr = 3
            if kind == "check": idx = CHECKS.index(xb); kstart = xb
            elif kind == "stop": kstart = xb; idx = next((i for i in range(n) if CHECKS[i] >= xb), n)
            else: break
    if CF.fade_allowed(D, taken) and not dll_hit():
        k, s, e, tgt = D.fade
        take, pts, why, tight = decide(S["bal"], floor, q, e, bp, kill, dll_left(), rule, True, fm)
        st[I_SIG] += 1
        if not take: st[I_SKIP] += 1; return S["bal"], False
        stop = e - s * pts
        seg_s = (D.l[k + 1:386] <= stop) if s > 0 else (D.h[k + 1:386] >= stop)
        seg_t = (D.h[k + 1:386] >= tgt) if s > 0 else (D.l[k + 1:386] <= tgt)
        js, jt = first_hit(seg_s), first_hit(seg_t)
        if js is not None and (jt is None or js <= jt):
            j = js + k + 1; px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK; p = (px - e) * s * PV - FEE
        elif jt is not None: p = (tgt - e) * s * PV - FEE
        else: p = (c[385] - s * TICK - e) * s * PV - FEE
        st[I_TAKEN] += 1
        if log is not None: log.append(("PM_FADE", p))
        if settle(p * q): return S["bal"], True
    return S["bal"], False

def kq(kelly, cush):
    return int(min(kelly[1], max(1, math.floor(kelly[0] * cush / 1000.0))))

def run_eval(objs, i0, cfg, kill, horizon, st):
    S0, TARGET, MLL, LOCKT, LOCKL = cfg["S0"], cfg["TARGET"], cfg["MLL"], cfg["LOCKT"], cfg["LOCKL"]
    q0, taper, brake, kelly = cfg["q"], cfg.get("taper"), cfg.get("brake"), cfg.get("kelly")
    bal = peak = S0; floor = S0 - MLL; npos = 0; idle = 0
    end = min(len(objs), i0 + horizon)
    for n, i in enumerate(range(i0, end)):
        D = objs[i]; q = q0; rem = TARGET - (bal - S0); cush = bal - floor
        if kelly: q = kq(kelly, cush)
        else:
            g = cfg.get("grow")
            if g: q = min(g[1], q0 + max(0, int(cush // g[0]) - 1))
            if brake and cush < brake[0] * MLL: q = min(q, brake[1])
        if taper and rem < taper * TARGET: q = min(q, cfg.get("taper_q", 1))
        c2 = {**cfg, "lockv": (cfg["lock_pct"] * rem) if cfg.get("lock_pct") else None}
        b0 = bal; t0 = st[I_TAKEN]
        if D is not None:
            bal, bust = day_sim(D, bal, floor, q, c2, kill, st)
            if bust: return "BUST", n + 1
        idle = idle + 1 if st[I_TAKEN] == t0 else 0
        if idle >= STALL_N: return "STALL", n + 1
        if bal - b0 > 0: npos += 1
        peak = max(peak, bal)
        floor = LOCKL if peak >= LOCKT else max(floor, peak - MLL)
        if bal - S0 >= TARGET and npos >= 1: return "PASS", n + 1
    return "OPEN", end - i0

def run_funded(objs, i0, cfg, kill, st, horizon=260):
    F = cfg["F"]; S0 = F["start"]; MLL = F["mll"]; kelly = cfg.get("kelly")
    bal = peak = S0; floor = S0 - MLL; cycle = []; paid = 0.0; pays = 0; idle = 0; frozen = False; qs = 0
    c2 = {**cfg, "dll": F["dll"]}
    for n, i in enumerate(range(i0, min(len(objs), i0 + horizon))):
        D = objs[i]; q = cfg["q"]
        if kelly: q = kq(kelly, bal - floor)
        else:
            br = cfg.get("brake")
            if br and bal - floor < br[0] * MLL: q = min(q, br[1])
        qs += q
        t0 = st[I_TAKEN]; day0 = bal
        if D is not None:
            bal, bust = day_sim(D, bal, floor, q, c2, kill, st)
            if bust: return dict(paid=paid, status="BUST", pays=pays, frozen=frozen, n=n + 1, q=qs / (n + 1))
        executed = st[I_TAKEN] != t0
        idle = 0 if executed else idle + 1
        if idle >= STALL_N: frozen = True
        if executed: cycle.append(bal - day0)
        peak = max(peak, bal)
        floor = F["lock_level"] if peak >= F["lock_trigger"] else max(floor, peak - MLL)
        if (n + 1) % cfg["cadence"] == 0 and pays < F["max_payouts"]:
            amt = P.payout_amount(F, bal, cycle, pays)
            if amt > 0:
                bal -= amt; paid += round(amt * F["split"], 2); pays += 1; cycle = []
                if F["lock_on_payout"]: floor = max(floor, F["lock_level"])
        if pays >= F["max_payouts"]: return dict(paid=paid, status="MAX_PAYOUTS", pays=pays, frozen=frozen, n=n + 1, q=qs / (n + 1))
    return dict(paid=paid, status="OPEN", pays=pays, frozen=frozen, n=horizon, q=qs / horizon)

def era_mask(names, starts): return np.array([names[i] <= P.ERA_SPLIT for i in starts])

def ev_eval(cfg, names, objs, H):
    starts = list(range(0, len(objs) - H, 2)); res = [run_eval(objs, i, cfg, KILL, H, P.zeros()) for i in starts]
    era = era_mask(names, starts)
    def summ(m):
        r = [x for x, mm in zip(res, m) if mm]; n = len(r); ps = [s for sx, s in r if sx == "PASS"]
        return dict(n=n, pass_=100 * len(ps) / n, bust=100 * sum(sx == "BUST" for sx, _ in r) / n, frozen=100 * sum(sx == "STALL" for sx, _ in r) / n,
                    open_=100 * sum(sx == "OPEN" for sx, _ in r) / n, med=float(np.median(ps)) if ps else float("nan"))
    return dict(all=summ(np.ones(len(res), bool)), e1=summ(era), e2=summ(~era))

def ev_funded(cfg, names, objs, horizon=260):
    starts = list(range(0, len(objs) - horizon, 2)); res = [run_funded(objs, i, cfg, KILL, P.zeros(), horizon) for i in starts]
    era = era_mask(names, starts); per = horizon / 10.0
    def summ(m):
        r = [x for x, mm in zip(res, m) if mm]; n = len(r); pd_ = np.array([x["paid"] for x in r]); alive = np.array([x["status"] != "BUST" and not x["frozen"] for x in r])
        return dict(n=n, bust=100 * (1 - alive.mean()), hard=100 * sum(x["status"] == "BUST" for x in r) / n, inc=float(pd_.mean() / per), surv=float(pd_[alive].mean() / per) if alive.any() else float("nan"),
                    med=float(np.median(pd_) / per), frozen=100 * sum(x["frozen"] for x in r) / n, anypay=100 * sum(x["pays"] > 0 for x in r) / n,
                    maxpay=100 * sum(x["status"] == "MAX_PAYOUTS" for x in r) / n, q=float(np.mean([x["q"] for x in r])))
    return dict(all=summ(np.ones(len(res), bool)), e1=summ(era), e2=summ(~era))

G = {}
def init():
    G["names"], G["objs"] = B.calendar(B.prep()); G["V"] = P.load_views()

def verify():
    """(1) lock replay with no account rule at 1 micro must reproduce streams/noise_lock100_plus10_no_reentry.csv; (2) copy of day_sim == P.day_sim."""
    import pandas as pd
    init(); names, objs = G["names"], G["objs"]
    for lk, fn in ((LOCK, "streams/noise_lock100_plus10_no_reentry.csv"), (None, None)):
        rows = []
        for nm, D in zip(names, objs):
            if D is None: continue
            log = []; day_sim(D, 1e9, 0.0, 1, dict(rule="none", bp=BP, lock=lk), 0, P.zeros(), log)
            rows += [(nm, s, p) for s, p in log]
        df = pd.DataFrame(rows, columns=["date", "strategy", "pnl"])
        print("lock" if lk else "base", "replay: n", len(df), "win %.1f%%" % (100 * (df.pnl > 0).mean()), "mean %.2f sd %.1f sum %.0f" % (df.pnl.mean(), df.pnl.std(), df.pnl.sum()))
        if fn:
            ref = pd.read_csv(ROOT + "/docs/results/session11/final_push/" + fn)
            print("  csv: n", len(ref), "win %.1f%%" % (100 * (ref.pnl_per_micro > 0).mean()), "mean %.2f sd %.1f sum %.0f" % (ref.pnl_per_micro.mean(), ref.pnl_per_micro.std(), ref.pnl_per_micro.sum()))
            a = df.groupby("date").pnl.sum(); b = ref.groupby("date").pnl_per_micro.sum()
            j = a.to_frame("a").join(b.to_frame("b"), how="outer").fillna(0)
            print("  days differing > $0.5:", int(((j.a - j.b).abs() > 0.5).sum()), "of", len(j), "sum abs diff %.0f" % (j.a - j.b).abs().sum())
    V = G["V"]; cf = P.funded_configs(V, "code")["50K x2 brake<50%->1, pay/10"]
    a = P.evaluate_funded(cf, KILL, names, objs)["all"]; b = ev_funded(cf, names, objs)["all"]
    P.day_sim, keep = (lambda D, bal, floor, q, cfg, kill, st, slipx=0.0: day_sim(D, bal, floor, q, cfg, kill, st, log=[])), P.day_sim
    c = ev_funded(cf, names, objs)["all"]; P.day_sim = keep
    print("50K funded  P.engine bust %.1f take %.0f | mine %.1f %.0f | my day_sim copy (lock off) %.1f %.0f" % (100 * a["bust"], a["take"], b["bust"], b["inc"] * 26, c["bust"], c["inc"] * 26))

if __name__ == "__main__": verify()
