"""Two-market account engine = multi-instrument port of ../pm_fade_d57_study.py (live rules: D57 stop-shrink 0.6 for NOISE, PM fade "as coded"
= $500 pause floor + worst-case check, kill $50, soft DLL, D68 cadence, D66 eval rows). One shared balance; trades of all instruments are settled in
exit-time order. Mixing rules (no hedging): MNQ is primary. A second-market entry is skipped while MNQ is open the other way (or on a conflicting
simultaneous signal); if MNQ enters against an open second-market trade, that trade is flattened at the MNQ entry bar. Planned worst-case $ of trades
still open is deducted from the room before a new entry is sized (D57 / worst-case check see total open risk).
Size rule: with base size q0 >= 2 and q >= q0 (not braked): MNQ q-1 micros + `nx` micros of the other market; braked: MNQ only.
usage: mix_engine.py verify | run"""
import sys, json, math
sys.dont_write_bytecode = True
ROOT = "/home/user/opogabuuga"
sys.path[:0] = [ROOT + "/backend", ROOT + "/docs/results/session11", ROOT + "/docs/results/session10/five_year"]
from multiprocessing import Pool
import numpy as np
import noise_gen as NG
HERE = ROOT + "/docs/results/session11/final_push"
RAW = ROOT + "/backend/app/backtest/data/raw"
START, END, ERA_SPLIT = "2021-11-01", "2026-10-30", "2023-12-31"
FEE, SLIP, MARGIN, MIN_PCT, SHRINK, STALL_N, KILL = 1.0, 1, 40.0, 0.002, 0.6, 20, 50
CHECKS = list(range(29, 360, 60))
PVT = {"mnq": (2.0, 0.25), "mes": (5.0, 0.25), "mym": (0.5, 1.0), "m2k": (5.0, 0.10)}

class Spec:
    def __init__(s, name, bp):
        s.name = name; s.PV, s.TICK = PVT[name]; s.TV = s.PV * s.TICK; s.bp = bp
    def per(s, ticks): return ticks * s.TV + FEE + SLIP * s.TV
class Day: pass

def prep(name):
    TICK = PVT[name][1]
    days, nb = NG.load_days(f"{RAW}/{name}_5y.csv")
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days]); out = {}
    for i, (d, a) in enumerate(days):
        if d < START or d > END: continue
        D = Day(); D.o, D.h, D.l, D.c, D.vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        D.noise_ok = False; D.side = {}; D.trail = {}; o, c, vw = D.o, D.c, D.vw
        if i >= 14:
            pc = days[i - 1][1]["close"][389]
            if not (np.isnan(pc) or abs(o[0] / pc - 1) > 0.015):
                sig = np.nanmean(moves[i - 14:i], axis=0)
                ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig); D.noise_ok = True
                for k in CHECKS:
                    if np.isnan(c[k]): continue
                    D.side[k] = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    D.trail[k] = (c[k] < max(ub[k], vw[k]), c[k] > min(lb[k], vw[k]))
        D.fade = None
        for k in range(210, 359):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + 2 * sd else (1 if c[k] < vw[k] - 2 * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK
            if (vw[k] - e) * s < 4 * TICK: break
            D.fade = (k, s, e, vw[k]); break
        D.lastsig = max([k for k, v in D.side.items() if v], default=-1)
        ev = [(k, 0) for k in CHECKS] if D.noise_ok else []
        if D.fade is not None: ev.append((D.fade[0], 1))
        D.ev = ev
        out[d] = D
    return out

def calendar(DAYS):
    from datetime import date, timedelta
    names, objs, x = [], [], date.fromisoformat(START)
    while x <= date.fromisoformat(END):
        if x.weekday() < 5: names.append(x.isoformat()); objs.append(DAYS.get(x.isoformat()))
        x += timedelta(days=1)
    return names, objs

def first_hit(a):
    if a.size == 0: return None
    j = int(a.argmax()); return j if a[j] else None

def decide(S, room_extra, bal, floor, n, entry, kill, dll_left, is_fade):
    """copy of pm_fade_d57_study.decide (rule live, fade_mode code); room_extra = planned risk of trades still open"""
    dist = bal - floor
    if is_fade and dist < 500: return False, 0, 0
    if not dist > kill: return False, 0, 0
    room0 = dist - kill
    if dll_left is not None: room0 = min(room0, dll_left)
    room0 -= room_extra
    if room0 <= 0: return False, 0, 0
    ticks = S.bp / S.TICK; usd = n * S.per(ticks)
    if not is_fade:
        allowed = room0 * SHRINK
        if usd > allowed:
            ticks = math.floor((allowed / n - FEE) / S.TV - SLIP)
            if ticks * S.TICK < entry * MIN_PCT: return False, 0, 0
            usd = n * S.per(ticks)
    if not usd + MARGIN <= room0: return False, 0, 0
    return True, ticks * S.TICK, usd

def noise_exit(D, S, side, entry, ek, pts):
    o, c = D.o, D.c; stop = entry - side * pts
    seg = (D.l[ek:390] <= stop) if side > 0 else (D.h[ek:390] >= stop)
    j = first_hit(seg)
    if j is not None: j += ek
    for kc in CHECKS:
        if kc < ek: continue
        if j is not None and kc >= j: break
        if kc in D.trail and D.trail[kc][0 if side > 0 else 1]:
            nk = kc + 1
            px = (o[nk] if nk < 390 and not np.isnan(o[nk]) else c[kc]) - side * S.TICK
            return (px - entry) * side * S.PV - FEE, kc, "check"
    if j is not None:
        px = (min(stop, o[j]) if side > 0 else max(stop, o[j])) - side * S.TICK
        return (px - entry) * side * S.PV - FEE, j, "stop"
    lastv = max(j2 for j2 in range(390) if not np.isnan(c[j2]))
    return (c[lastv] - side * S.TICK - entry) * side * S.PV - FEE, 389, "eod"

def fade_exit(D, S, k, s, e, tgt, pts):
    o, c = D.o, D.c; stop = e - s * pts
    seg_s = (D.l[k + 1:386] <= stop) if s > 0 else (D.h[k + 1:386] >= stop)
    seg_t = (D.h[k + 1:386] >= tgt) if s > 0 else (D.l[k + 1:386] <= tgt)
    js, jt = first_hit(seg_s), first_hit(seg_t)
    if js is not None and (jt is None or js <= jt):
        j = js + k + 1; px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * S.TICK
        return (px - e) * s * S.PV - FEE, j, "stop"
    if jt is not None: return (tgt - e) * s * S.PV - FEE, jt + k + 1, "tp"
    return (c[385] - s * S.TICK - e) * s * S.PV - FEE, 385, "eod"

def day_sim(Ds, specs, qs, bal, floor, dll, lockv, kill, cnt):
    """Ds / specs / qs: per instrument (0 = MNQ). returns (bal, busted, n_taken). cnt = [taken per inst..., conflicts skipped, forced closes]"""
    ni = len(Ds); day = 0.0; dpk = 0.0; taken_total = 0
    ntr = [0] * ni; taken = [0] * ni; done = [False] * ni; opn = [None] * ni      # opn: [side, entry, xb, pnl_total, risk, q]
    ev = sorted((k, t, i) for i in range(ni) if Ds[i] is not None and qs[i] > 0 for k, t in Ds[i].ev)
    def settle_upto(k):
        nonlocal bal, day, dpk
        for i in sorted((i for i in range(ni) if opn[i] is not None and opn[i][2] <= k), key=lambda i: opn[i][2]):
            p = opn[i][3]; opn[i] = None
            if dll is not None and day + p <= -dll: p = -dll - day
            bal += p; day += p; dpk = max(dpk, day)
            if bal <= floor: return True
        return False
    def stopped(): return (dll is not None and day <= -dll) or (lockv is not None and day > 0 and day >= lockv)
    for k, typ, i in ev:
        if settle_upto(k): return bal, True, taken_total
        if done[i] or opn[i] is not None: continue
        D, S, q = Ds[i], specs[i], qs[i]
        if typ == 0:
            if ntr[i] >= 3 or stopped(): done[i] = True; continue
            side = D.side.get(k, 0)
            if side == 0: continue
            ntr[i] += 1
            ek = next((j for j in range(k + 1, 390) if not np.isnan(D.c[j])), None)
            if ek is None: continue
            entry = D.o[ek] + side * S.TICK
        else:
            if taken[i] or D.lastsig > k or stopped(): continue
            _, side, entry, tgt = D.fade; ek = k + 1
        if i > 0 and opn[0] is not None and opn[0][0] != side: cnt[ni] += 1; continue          # no hedging: MNQ has priority
        if i > 0 and typ == 0 and Ds[0] is not None and qs[0] > 0 and Ds[0].side.get(k, 0) == -side: cnt[ni] += 1; continue
        extra = sum(opn[j][4] for j in range(ni) if opn[j] is not None)
        dl = None if dll is None else dll - (max(0.0, dpk, day) - day)
        ok, pts, usd = decide(S, extra, bal, floor, q, entry, kill, dl, typ == 1)
        if not ok: continue
        if i == 0:
            for j in range(1, ni):                                                                # flatten opposite second-market trades
                t = opn[j]
                if t is not None and t[0] != side:
                    Dj, Sj = Ds[j], specs[j]; px = Dj.o[ek] if not np.isnan(Dj.o[ek]) else Dj.c[max(x for x in range(ek) if not np.isnan(Dj.c[x]))]
                    t[3] = ((px - t[0] * Sj.TICK - t[1]) * t[0] * Sj.PV - FEE) * t[5]; t[2] = k; cnt[ni + 1] += 1
            if settle_upto(k): return bal, True, taken_total
        p, xb, kind = noise_exit(D, S, side, entry, ek, pts) if typ == 0 else fade_exit(D, S, k, side, entry, tgt, pts)
        opn[i] = [side, entry, xb, p * q, usd, q]; taken[i] += 1; taken_total += 1; cnt[i] += 1
        if typ == 0 and kind == "eod": done[i] = True
    if settle_upto(999): return bal, True, taken_total
    return bal, False, taken_total

def split_q(q, q0, nx, ni):
    if ni == 1 or nx == 0: return [q] + [0] * (ni - 1)
    if q0 >= 2 and q >= q0: return [q - 1, nx]
    return [q, 0]

def run_eval(objs, specs, i0, cfg, kill, horizon, cnt):
    S0, TARGET, MLL, LOCKT, LOCKL = cfg["S0"], cfg["TARGET"], cfg["MLL"], cfg["LOCKT"], cfg["LOCKL"]
    q0, taper, brake = cfg["q"], cfg.get("taper"), cfg.get("brake"); ni = len(specs)
    bal = peak = S0; floor = S0 - MLL; npos = 0; idle = 0
    end = min(len(objs[0]), i0 + horizon)
    for n, i in enumerate(range(i0, end)):
        q = q0; rem = TARGET - (bal - S0); cush = bal - floor
        g = cfg.get("grow")
        if g: q = min(g[1], q0 + max(0, int(cush // g[0]) - 1))
        if taper and rem < taper * TARGET: q = min(q, cfg.get("taper_q", 1))
        if brake and cush < brake[0] * MLL: q = min(q, brake[1])
        lockv = (cfg["lock_pct"] * rem) if cfg.get("lock_pct") else None
        b0 = bal
        bal, bust, tk = day_sim([o[i] for o in objs], specs, split_q(q, q0, cfg.get("nx", 0), ni), bal, floor, cfg.get("dll"), lockv, kill, cnt)
        if bust: return "BUST", n + 1
        idle = idle + 1 if tk == 0 else 0
        if idle >= STALL_N: return "STALL", n + 1
        if bal - b0 > 0: npos += 1
        peak = max(peak, bal)
        floor = LOCKL if peak >= LOCKT else max(floor, peak - MLL)
        if bal - S0 >= TARGET and npos >= 1: return "PASS", n + 1
    return "OPEN", end - i0

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

def run_funded(objs, specs, i0, cfg, kill, cnt, horizon=260):
    F = cfg["F"]; S0 = F["start"]; MLL = F["mll"]; ni = len(specs)
    bal = peak = S0; floor = S0 - MLL; cycle = []; paid = 0.0; pays = 0; idle = 0; frozen = False
    for n, i in enumerate(range(i0, min(len(objs[0]), i0 + horizon))):
        q = cfg["q"]; br = cfg.get("brake")
        if br and bal - floor < br[0] * MLL: q = min(q, br[1])
        day0 = bal
        bal, bust, tk = day_sim([o[i] for o in objs], specs, split_q(q, cfg["q"], cfg.get("nx", 0), ni), bal, floor, F["dll"], None, kill, cnt)
        if bust: return dict(paid=paid, status="BUST", pays=pays, frozen=frozen)
        idle = 0 if tk else idle + 1
        if idle >= STALL_N: frozen = True
        if tk: cycle.append(bal - day0)
        peak = max(peak, bal)
        floor = F["lock_level"] if peak >= F["lock_trigger"] else max(floor, peak - MLL)
        if (n + 1) % cfg["cadence"] == 0 and pays < F["max_payouts"]:
            amt = payout_amount(F, bal, cycle, pays)
            if amt > 0:
                bal -= amt; paid += round(amt * F["split"], 2); pays += 1; cycle = []
                if F["lock_on_payout"]: floor = max(floor, F["lock_level"])
        if pays >= F["max_payouts"]: return dict(paid=paid, status="MAX_PAYOUTS", pays=pays, frozen=frozen)
    return dict(paid=paid, status="OPEN", pays=pays, frozen=frozen)

def evaluate(kind, cfg, names, objs, specs, H):
    starts = list(range(0, len(names) - H, 2)); cnt = [0] * (len(specs) + 2)
    res = [run_eval(objs, specs, i, cfg, KILL, H, cnt) if kind == "E" else run_funded(objs, specs, i, cfg, KILL, cnt, H) for i in starts]
    era = np.array([names[i] <= ERA_SPLIT for i in starts])
    def summ(mask):
        r = [x for x, m in zip(res, mask) if m]; n = len(r)
        if kind == "E":
            ps = [s for sx, s in r if sx == "PASS"]
            return dict(n=n, pass_=len(ps) / n, bust=sum(sx == "BUST" for sx, _ in r) / n, frozen=sum(sx == "STALL" for sx, _ in r) / n,
                        med=float(np.median(ps)) if ps else float("nan"))
        pd_ = np.array([x["paid"] for x in r])
        return dict(n=n, take=float(pd_.mean()), take_med=float(np.median(pd_)), bust=sum(x["status"] == "BUST" for x in r) / n,
                    frozen=sum(x["frozen"] for x in r) / n, anypay=sum(x["pays"] > 0 for x in r) / n)
    return dict(all=summ(np.ones(len(res), bool)), e1=summ(era), e2=summ(~era), cnt=cnt)

# ------------------------------------------------------------ configs (same rows as pm_fade_d57_study.py)
def configs():
    import pm_fade_d57_study as P
    V = P.load_views(); BP = P.BP
    E = {"50K": (dict(**V["50k"]["E"], q=2, brake=(0.5, 1)), 120),
         "100K": (dict(**V["100k"]["E"], q=2, brake=(0.3, 1), grow=(1200, 4), lock_pct=0.33), 250),
         "150K": (dict(**V["150k"]["E"], q=4, brake=(0.5, 2)), 250)}
    Fd = {"50K": (dict(F=V["50k"]["F"], q=2, brake=(0.5, 1), cadence=10), 260),
          "100K": (dict(F=V["100k"]["F"], q=2, brake=(0.3, 1), cadence=5), 260),
          "150K": (dict(F=V["150k"]["F"], q=3, brake=(0.5, 2), cadence=5), 260)}
    return E, Fd, BP

G = {}
def init():
    st = json.load(open(f"{HERE}/second_streams.json"))
    G["E"], G["F"], BP = configs(); G["spec"] = {"mnq": Spec("mnq", BP)}; G["objs"] = {}
    for m in ("mnq", "mes", "mym", "m2k"):
        if m != "mnq": G["spec"][m] = Spec(m, st[m]["stop_pts"])
        G["names"], G["objs"][m] = calendar(prep(m))
def work(job):
    kind, plan, mkt, nx = job
    cfg, H = (G["E"] if kind == "E" else G["F"])[plan]
    if mkt is None: specs, objs = [G["spec"]["mnq"]], [G["objs"]["mnq"]]
    else: specs, objs = [G["spec"]["mnq"], G["spec"][mkt]], [G["objs"]["mnq"], G["objs"][mkt]]
    return job, evaluate(kind, {**cfg, "nx": nx}, G["names"], objs, specs, H)

def verify():
    """all-MNQ in this engine vs the reference engine pm_fade_d57_study (fade_mode code, kill 50)"""
    import pm_fade_d57_study as P
    init(); P.init()
    for kind, plan, name in (("F", "50K", "50K x2 brake<50%->1, pay/10"), ("F", "150K", "150K x3 brake<50%->2, pay/5"), ("E", "50K", "50K"), ("E", "100K", "100K")):
        _, r = work((kind, plan, None, 0))
        if kind == "F":
            ref = P.evaluate_funded(P.funded_configs(P.G["V"], "code")[name], KILL, P.G["names"], P.G["objs"])["all"]
            print(kind, plan, f"mix_engine take {r['all']['take']:.0f} bust {r['all']['bust']:.1%} frozen {r['all']['frozen']:.1%} | reference take {ref['take']:.0f} bust {ref['bust']:.1%} frozen {ref['frozen']:.1%}")
        else:
            ref = P.evaluate(P.eval_configs(P.G["V"], "code")[name], KILL, P.G["names"], P.G["objs"], H=P.HZ[name], chain=False)["all"]
            print(kind, plan, f"mix_engine pass {r['all']['pass_']:.1%} bust {r['all']['bust']:.1%} frozen {r['all']['frozen']:.1%} med {r['all']['med']:.0f} | reference pass {ref['pass_']:.1%} bust {ref['bust']:.1%} frozen {ref['frozen']:.1%} med {ref['med']:.0f}")

def main():
    st = json.load(open(f"{HERE}/second_streams.json"))
    jobs = [(k, p, None, 0) for k in "FE" for p in ("50K", "100K", "150K")]
    for m in ("mes", "mym", "m2k"):
        keq = max(1, round(251.0 / st[m]["stop_usd"]))                       # micros of the other market with the $ risk of 1 MNQ
        for k in "FE":
            for p in ("50K", "100K", "150K"):
                for nx in sorted({1, 2, keq} if p == "150K" else {1, keq}): jobs.append((k, p, m, nx))
    with Pool(4, initializer=init) as pool: res = pool.map(work, jobs, chunksize=1)
    json.dump([dict(kind=j[0], plan=j[1], mkt=j[2], nx=j[3], **r) for j, r in res], open(f"{HERE}/second_mix.json", "w"), indent=1)

if __name__ == "__main__":
    if sys.argv[1:2] == ["verify"]: verify()
    elif sys.argv[1:2] == ["run"]: main()
