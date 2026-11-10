"""Pro 25K eval study with the LIVE D57 stop-tightening (checks.py pretrade, fixed-size branch) applied per trade.
Per-trade re-simulation of MAIN (NOISE hourly-check momentum + afternoon VWAP fade) on 1-minute bars, the stop distance
of each trade set from the account's CURRENT cushion at trade start. Generators copied from agent1/gen.py (NOISE look 14,
step 60, max 3 entries, gap guard; fade 2-sd VWAP afternoon) - verified identical to trades_main.csv at the fixed 124-pt stop.
usage: livestop.py [verify|run]"""
import sys, json, math
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path[:0] = ["/home/user/opogabuuga/docs/results/tools"]
import noise_area as NA
SP = "/tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad"
CSV = SP + "/data/mnq_5y.csv"; OUT = SP + "/agentP"
START, END = "2021-11-01", "2026-10-30"
PV, TICK, FEE, TV, SLIP = 2.0, 0.25, 1.0, 0.5, 1
BASE_PTS = 124.0                                  # $250 emergency stop = (250-1-1)/2
S0, TARGET, MLL, LOCKT, LOCKL, H = 25000.0, 1250.0, 1000.0, 26100.0, 25100.0, 120
KILL, MARGIN, MIN_PCT = 100.0, 40.0, 0.002
VALUE_FUNDED = 1646.41
CHECKS = list(range(29, 360, 60))
STALL_N = 20

# ---------------------------------------------------------------- live rule (checks.py pretrade, fixed-size branch)
def per_contract(ticks): return ticks * TV + FEE + SLIP * TV
def live_decide(bal, floor, n, entry, rule):
    """returns (take, stop_pts, reason, n). rule: ('none',) | ('frac', f) | ('room', margin)  [room = allowed = room0 - margin]
    ('step_frac', f) / ('step_room', m): NOT LIVE - same arithmetic but drop contracts (n -> 1) until the stop fits instead of skipping."""
    if rule[0].startswith("step"):
        base = ("frac" if rule[0] == "step_frac" else "room", rule[1]); r = None
        for m in range(n, 0, -1):
            r = live_decide(bal, floor, m, entry, base)
            if r[0]: return r
        return r
    t, pts, why = _decide(bal, floor, n, entry, rule)
    return t, pts, why, n
def _decide(bal, floor, n, entry, rule):
    base_ticks = BASE_PTS / TICK
    if rule[0] == "none": return True, BASE_PTS, None
    dist = bal - floor                              # acct.equity - acct.mll
    if not dist > KILL: return False, 0, "NEAR_MLL"
    room0 = dist - KILL                             # no DLL on the Pro eval
    usd = n * per_contract(base_ticks)
    allowed = room0 * rule[1] if rule[0] == "frac" else room0 - rule[1]
    ticks = base_ticks
    if usd > allowed:
        ticks = math.floor((allowed / n - FEE) / TV - SLIP)          # ROUND_DOWN (toward 0 for positives; negative -> skip)
        if ticks * TICK < entry * MIN_PCT: return False, 0, "DRAWDOWN_TOO_DEEP"
        usd = n * per_contract(ticks)
    if not usd + MARGIN <= room0: return False, 0, "WORST_CASE"    # _finish worst-case check
    return True, ticks * TICK, None

# ---------------------------------------------------------------- per-day precompute
class Day: pass
def prep():
    days = NA.load_days(CSV)
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    out = {}
    for i, (d, a) in enumerate(days):
        if d < START or d > END: continue
        D = Day(); D.o, D.h, D.l, D.c, D.vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        D.noise_ok = False; D.side = {}; D.trail = {}
        o, c, vw = D.o, D.c, D.vw
        if i >= 14:
            pc = days[i - 1][1]["close"][389]
            if not (np.isnan(pc) or abs(o[0] / pc - 1) > 0.015):
                sig = np.nanmean(moves[i - 14:i], axis=0)
                ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
                D.noise_ok = True
                for k in CHECKS:
                    if np.isnan(c[k]): continue
                    D.side[k] = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    D.trail[k] = (c[k] < max(ub[k], vw[k]), c[k] > min(lb[k], vw[k]))   # long exit, short exit
        D.nv = None
        # fade signal (stop independent)
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
        out[d] = D
    return out

def first_hit(arr_cond):
    if arr_cond.size == 0: return None
    j = int(arr_cond.argmax()); return j if arr_cond[j] else None

def trade_stop_exit(D, s, entry, ek, stop):
    """first 1-min bar >= ek whose range touches the stop -> (pnl_per_micro, bar) else None"""
    seg = (D.l[ek:390] <= stop) if s > 0 else (D.h[ek:390] >= stop)
    j = first_hit(seg)
    if j is None: return None
    j += ek
    px = (min(stop, D.o[j]) if s > 0 else max(stop, D.o[j])) - s * TICK
    return (px - entry) * s * PV - FEE, j

def day_sim(D, bal, floor, q, rule, st):
    """simulate one session with the account state; returns (bal, busted). st = stats accumulator list"""
    ntr = 0; taken = 0; idx = 0; n = len(CHECKS); o, c = D.o, D.c
    def settle(p, qn):
        nonlocal bal
        bal += p * qn
        if p * qn > 0: st[5] += 1; st[6] += p * qn
        else: st[7] += 1; st[8] += p * qn
        return bal <= floor
    if D.noise_ok:
        kstart = 0
        while idx < n:
            k = CHECKS[idx]
            if k < kstart: idx += 1; continue
            if ntr >= 3: break
            side = D.side.get(k, 0)
            if side == 0: idx += 1; continue
            ntr += 1
            ek = next((j for j in range(k + 1, 390) if not np.isnan(c[j])), None)
            if ek is None: idx += 1; continue
            entry = o[ek] + side * TICK
            take, pts, why, qq = live_decide(bal, floor, q, entry, rule)
            st[0] += 1
            if not take: st[1] += 1; idx += 1; continue            # signal consumed, position stays flat
            st[2] += pts * PV; st[3] += 1; st[4] += qq; taken += 1
            stop = entry - side * pts
            so = trade_stop_exit(D, side, entry, ek, stop)
            j = so[1] if so else None
            ex = None
            for ci in range(idx, n):                                # trail exit at a later check
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
            if settle(ex[0], qq): return bal, True
            if ex[2] == "check": idx = CHECKS.index(ex[1]); kstart = ex[1]       # re-evaluate same check, flat
            elif ex[2] == "stop": kstart = ex[1]; idx = next((i for i in range(n) if CHECKS[i] >= ex[1]), n)
            else: break
    if taken == 0 and ntr == 0 or taken == 0:        # fade only on days NOISE took no trade
        if D.fade is not None:
            k, s, e, tgt = D.fade
            take, pts, why, qq = live_decide(bal, floor, q, e, rule)
            st[0] += 1
            if not take: st[1] += 1; return bal, False
            st[2] += pts * PV; st[3] += 1; st[4] += qq
            stop = e - s * pts
            seg_s = (D.l[k + 1:386] <= stop) if s > 0 else (D.h[k + 1:386] >= stop)
            seg_t = (D.h[k + 1:386] >= tgt) if s > 0 else (D.l[k + 1:386] <= tgt)
            js, jt = first_hit(seg_s), first_hit(seg_t)
            if js is not None and (jt is None or js <= jt):
                j = js + k + 1; px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK
                p = (px - e) * s * PV - FEE
            elif jt is not None: p = (tgt - e) * s * PV - FEE
            else: p = (c[385] - s * TICK - e) * s * PV - FEE
            if settle(p, qq): return bal, True
    return bal, False

# ---------------------------------------------------------------- eval engine (same as agent1/sim.py)
def calendar(DAYS):
    from datetime import date, timedelta
    names, objs, x = [], [], date.fromisoformat(START)
    while x <= date.fromisoformat(END):
        if x.weekday() < 5: names.append(x.isoformat()); objs.append(DAYS.get(x.isoformat()))
        x += timedelta(days=1)
    return names, objs

def run_eval(objs, i0, cfg, horizon, st):
    q0, sprint, rule = cfg["q"], cfg.get("sprint"), cfg["rule"]
    bal = peak = S0; floor = S0 - MLL; npos = 0; idle = 0
    end = len(objs) if horizon is None else min(len(objs), i0 + horizon)
    for n, i in enumerate(range(i0, end)):
        D = objs[i]; q = q0; rem = TARGET - (bal - S0)
        if sprint and rem < sprint * TARGET: q = 1
        b0 = bal; t0 = st[3]
        if D is not None:
            bal, bust = day_sim(D, bal, floor, q, rule, st)
            if bust: return "BUST", n + 1
        idle = idle + 1 if st[3] == t0 else 0
        if idle >= STALL_N: return "STALL", n + 1          # frozen: 20 sessions in a row without one executed trade
        if bal - b0 > 0: npos += 1
        peak = max(peak, bal)
        floor = LOCKL if peak >= LOCKT else max(floor, peak - MLL)
        if bal - S0 >= TARGET and npos >= 1: return "PASS", n + 1
    return "OPEN", end - i0

def evaluate(cfg, names, objs):
    starts = list(range(0, len(objs) - H, 2))
    res, sts = [], []
    for i in starts:
        st = [0, 0, 0.0, 0, 0, 0, 0.0, 0, 0.0]; res.append(run_eval(objs, i, cfg, H, st)); sts.append(st)
    tot = np.sum(sts, axis=0)
    pas = [st for st, (sx, _) in zip(sts, res) if sx == "PASS"]; psum = np.sum(pas, axis=0) if pas else np.zeros(9)
    stats_h = tot
    chain = []
    dummy = [0, 0, 0.0, 0, 0, 0, 0.0, 0, 0.0]
    for i in starts:
        t, tot, ok = i, 0, False
        while t < len(objs):
            s, n = run_eval(objs, t, cfg, None, dummy); tot += n
            if s == "PASS": ok = True; break
            if s == "OPEN": break   # BUST and STALL both restart
            t += n
        chain.append(tot if ok else None)
    era = np.array([names[i] <= "2023-12-31" for i in starts])
    def summ(mask):
        r = [x for x, m in zip(res, mask) if m]; c = [x for x, m in zip(chain, mask) if m]
        n = len(r); ps = [s for sx, s in r if sx == "PASS"]; cc = [x for x in c if x is not None]
        return dict(n=n, pass_=len(ps) / n, bust=sum(sx == "BUST" for sx, _ in r) / n, stall=sum(sx == "STALL" for sx, _ in r) / n, open_=sum(sx == "OPEN" for sx, _ in r) / n,
                    med=float(np.median(ps)) if ps else float("nan"), p75=float(np.percentile(ps, 75)) if ps else float("nan"),
                    chain_med=float(np.median(cc)) if cc else float("nan"), chain_cens=1 - len(cc) / len(c))
    a = summ(np.ones(len(res), bool))
    sig, skip, stopsum, taken, qsum, nw, sw, nl, sl = stats_h
    a.update(winrate=nw / (nw + nl) if nw + nl else float('nan'), avg_win=sw / nw if nw else float('nan'), avg_loss=sl / nl if nl else float('nan'), ntr=nw + nl,
             skip_share=skip / sig if sig else 0.0, avg_stop_usd=stopsum / taken if taken else float("nan"), signals=sig, taken=taken, avg_q=qsum / taken if taken else float('nan'),
             skip_share_pass=psum[1] / psum[0] if psum[0] else 0.0, chain_cens_all=a['chain_cens'])
    return dict(all=a, e1=summ(era), e2=summ(~era))

def pts_of(usd): return round(((usd - 2) / 2) / TICK) * TICK      # stop points per micro for a given $ stop/micro
RULES = {"L60": ("frac", 0.6), "R40": ("room", MARGIN), "NO": ("none",)}
# (micros, stop $ per micro)
PROFILES = [(1, 250), (2, 250), (3, 250), (4, 250),
            (1, 350), (2, 175), (3, 117), (4, 87),
            (1, 450), (2, 225), (3, 150), (4, 112), (6, 75),
            (2, 270), (3, 180), (4, 135), (6, 90)]
def configs():
    c = {}
    for q, usd in PROFILES:
        for taper in ((None, 0.5) if q > 1 else (None,)):
            for rn, rule in RULES.items():
                nm = f"{q}x${usd} {'taper50' if taper else 'notaper'} {rn}"
                c[nm] = dict(q=q, usd=usd, sprint=taper, rule=rule, bp=pts_of(usd))
    return c

G = {}
def work(name):
    global BASE_PTS
    cfg = configs()[name]; BASE_PTS = cfg['bp']
    return name, cfg, evaluate(cfg, G["names"], G["objs"])

def init():
    G["names"], G["objs"] = calendar(prep())

def verify():
    global BASE_PTS; BASE_PTS = 124.0
    init(); objs = G["objs"]; names = G["names"]
    ref = pd.read_csv(SP + "/agent1/trades_main.csv")
    got = []
    for nm, D in zip(names, objs):
        if D is None: continue
        bal = 1e9  # huge cushion, rule none: log trades via q=1 deltas
        b, _ = day_sim(D, bal, 0.0, 1, ("none",), [0, 0, 0.0, 0, 0, 0, 0.0, 0, 0.0])
        if b != bal: got.append((nm, b - bal))
    got = pd.DataFrame(got, columns=["d", "pnl"])
    rd = ref.groupby("d").pnl.sum().reset_index()
    m = rd.merge(got, on="d", how="outer", suffixes=("_ref", "_got")).fillna(0)
    print("ref trades", len(ref), "total", round(ref.pnl.sum(), 2), "| day-level total got", round(got.pnl.sum(), 2),
          "| day mismatches", int((abs(m.pnl_ref - m.pnl_got) > 1e-6).sum()), "of", len(m))
    # live arithmetic example
    for bal in (25000, 25500, 26000):
        for q in (4, 3, 2, 1):
            t, pts, w, _ = live_decide(bal, 24000, q, 20000, ("frac", 0.6)); t2, pts2, w2, _ = live_decide(bal, 24000, q, 20000, ("room", MARGIN))
            print(f"bal {bal} floor 24000 q={q}: frac0.6 take={t} stop={pts} pts (${pts*2:.0f}/micro) {w or ''} | room-40 take={t2} stop={pts2} (${pts2*2:.0f}/micro) {w2 or ''}")

def main():
    cf = configs(); names = list(cf)
    if len(sys.argv) > 2: names = [n for n in names if sys.argv[2] in n]
    with Pool(4, initializer=init) as p:
        res = p.map(work, names, chunksize=1)
    out = {n: dict(cfg={k: v for k, v in c.items()}, **r) for n, c, r in res}
    json.dump(out, open(OUT + "/results.json", "w"), indent=1, default=str)
    L = ["| config | total worst $ | pass | bust | stall | open | med | p75 | chain med | skip share | win rate | avg win | avg loss | avg stop $/micro | avg micros | chain cens | value/eval | era1 pass/bust/med/chain | era2 pass/bust/med/chain |", "|" + "---|" * 19]
    for n, v in out.items():
        a, e1, e2, c = v["all"], v["e1"], v["e2"], v["cfg"]
        L.append(f"| {n} | ${c['q']*c['usd']} | {a['pass_']:.1%} | {a['bust']:.1%} | {a['stall']:.1%} | {a['open_']:.1%} | {a['med']:.0f} | {a['p75']:.0f} | {a['chain_med']:.0f} | {a['skip_share']:.1%} | {a['winrate']:.1%} | ${a['avg_win']:.0f} | ${a['avg_loss']:.0f} | ${a['avg_stop_usd']:.0f} | {a['avg_q']:.2f} | {a['chain_cens']:.0%} | ${a['pass_']*VALUE_FUNDED:,.0f} | "
                 f"{e1['pass_']:.0%}/{e1['bust']:.0%}/{e1['med']:.0f}/{e1['chain_med']:.0f} | {e2['pass_']:.0%}/{e2['bust']:.0%}/{e2['med']:.0f}/{e2['chain_med']:.0f} |")
    open(OUT + "/table.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))

if __name__ == "__main__":
    verify() if sys.argv[1:] == ["verify"] else main()
