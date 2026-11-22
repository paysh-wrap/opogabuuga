"""Ten-account study (research only). 5 EVAL + 5 FUNDED per Lucid Pro plan, 5-year history + last 12 months + rolling 12-month starts.
Account logic = pass_fastest sim150 (via brake150.load_sim + smaller_plans plan constants) re-stepped day by day so that many accounts share one trade tape.
Run: cd backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/ten_accounts/ten.py"""
import sys, os, math, json, statistics as st
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); PF = HERE + "/../pass_fastest"
sys.path.insert(0, PF); sys.path.insert(0, PF + "/brake150"); sys.path.insert(0, PF + "/smaller_plans")
import brake150 as B
import run_small as R

T3 = 1.0 / 3.0
# setups: eval-account config per scenario (funded accounts always use the plan's today row; fast-pass is EVAL-only, D157)
TODAY = {25: dict(stop=250, N=1, brake=None), 50: dict(stop=250, N=2, brake=(0.5, 1)), 100: dict(stop=250, N=2, brake=(0.3, 1)), 150: dict(stop=250, N=3, brake=(0.5, 2))}
FAST = {25: dict(stop=75, N=1, nc=2, brake=None, cbands=((T3, 1),)), 50: TODAY[50],
        100: dict(stop=250, N=2, nc=3, brake=(T3, 1), cbands=((T3, 2),)), 150: dict(stop=100, N=5, nc=4, brake=(T3, 2), cbands=((T3, 2),))}
# fees: 25K eval 116 / reset 81 = user's card (verified); 50/100/150 = UNVERIFIED third-party figures 120/190/255 used for both purchase and reset
FEE = {25: (116., 81.), 50: (120., 120.), 100: (190., 190.), 150: (255., 255.)}
PAY = {25: (500, 250, 1000, 1500), 50: (500, 500, 2000, 2500), 100: (500, 750, 2500, 3000), 150: (500, 1000, 3000, 3500)}  # min_req, min_cycle, cap_first, cap_next (yaml; caps UNVERIFIED)
SPLIT, MAXPAY, MINDAYS, PCONS = 0.9, 5, 3, 0.40
_S = {}


def sim(k):
    if k not in _S:
        if k == 150:
            S = B.load_sim(); S.CONS = 40.0; S.DSTOP = 0.38 * S.TARGET
        else: S = R.sim(k, "C40")
        S.SIZE_K = k
        _S[k] = S
    return _S[k]


class Acct:
    def __init__(s, S, c, funded, start, born=None):
        s.S, s.c, s.funded, s.start = S, c, funded, start
        s.bal = S.SIZE; s.floor = s.bal - S.MLL; s.peak = s.bal; s.peak_e = s.bal; s.locked = False
        s.pdays = 0; s.best = 0.0; s.alive = True; s.npay = 0; s.chain0 = born if born is not None else start
        s.cyc = 0.0; s.cdays = 0; s.cmax = 0.0; s.dstop = 1e18 if funded else S.DSTOP

    def day_start(s):
        S = s.S; s.today = 0.0; s.stop = False; s.peak_day = 0.0; s.free = -1.0; s.last = -1
        s.dll = S.DLL0
        if S.SCALE and s.locked: s.dll = 0.6 * (s.peak_e - S.SIZE)

    def trade(s, tr):
        """returns 'skip' | 'taken' | 'dead'"""
        S, c = s.S, s.c; m_in, m_out, kind, a, b, cc, d, side = tr
        if s.stop: return "skip"
        if m_in <= s.free and not (kind == S.KN and s.last == S.KN): return "skip"
        kd, mg, dll = S.KILL, S.MARGIN, s.dll
        if kind <= S.KF:
            cush = s.bal - s.floor; q = c["N"]; br = c["brake"]
            if br is not None and cush / S.MLL < br[0]: q = min(q, br[1])
            q = min(q, int(S.CAP_TRADE // cc))
            if cush <= kd: return "dead"
            room0 = cush - kd
            if dll: room0 = min(room0, dll + s.today)
            pp = None; eff = b
            while q > 0:
                S_ = cc
                if q * cc > S.SHRINK * room0:
                    pt = math.floor(((S.SHRINK * room0 / q) - S.FEE) / S.TV - S.SLIP)
                    if pt * 0.25 < S.MINPCT * d or pt <= 0: q = -1; break
                    S_ = pt * S.TV + S.FEE + S.TV
                if q * S_ + mg <= room0:
                    pp = -S_ if (S_ < cc and b >= S_) else a
                    eff = min(b, S_) if S_ < cc else b
                    break
                q -= 1
            if q <= 0:
                return "dead" if S.SHRINK * (cush - kd) < S.GMIN else "skip"
            pq = q * pp; dead = False
            if q * eff >= cush - kd: pq = -(cush - kd); dead = True
        else:
            per = b * 2.0 + 2.0; left = None
            if dll:
                left = dll - (max(0.0, s.peak_day, s.today) - s.today)
                if left <= 0: s.stop = True; return "skip"
            lim = s.bal - s.floor - kd
            if left is not None and left < lim: lim = left
            q = c["nc"]
            for fb, fn in c.get("cbands", ()):
                if (s.bal - s.floor) / S.MLL < fb: q = min(q, fn)
            while q >= 1 and q * per + mg > lim: q -= 1
            if q < 1: return "skip"
            pq = q * (a * S.PV - S.COST1); dead = False
        s.free = m_out; s.last = kind
        if dll and s.today + pq <= -dll: pq = -dll - s.today; s.stop = True
        if s.today + pq > s.dstop: pq = s.dstop - s.today; s.stop = True
        s.today += pq; s.bal += pq
        if s.today > s.peak_day: s.peak_day = s.today
        if dead or s.bal <= s.floor + kd: return "dead"
        return "taken"

    def day_end(s, weekly_ok=True):
        """returns None | 'pass' | gross payout amount"""
        S = s.S
        if s.today > 0:
            s.pdays += 1; s.best = max(s.best, s.today)
            if s.funded: s.cdays += 1; s.cmax = max(s.cmax, s.today)
        if s.funded: s.cyc += s.today
        if s.bal > s.peak_e: s.peak_e = s.bal
        if s.bal > s.peak and not s.locked:
            s.peak = s.bal
            if s.peak >= S.LOCK_TRIG: s.locked = True; s.floor = S.LOCK_LVL
            else: s.floor = s.peak - S.MLL
        if not s.funded:
            prof = s.bal - S.SIZE
            if prof >= S.TARGET and s.pdays >= S.MPD and s.best <= S.CONS / 100 * prof: return "pass"
            return None
        mr, mc, c1, cn = PAY[S.SIZE_K]
        if weekly_ok and s.cdays >= MINDAYS and s.cyc >= mc and s.cmax <= PCONS * s.cyc:
            amt = min(c1 if s.npay == 0 else cn, s.cyc, s.bal - S.LOCK_TRIG)
            if amt >= mr: return amt
        return None


def tapes(S, cfgs):
    L = S.L; noise = {}; cand = [[] for _ in range(L)]
    for c in cfgs:
        k = c["stop"]
        if k in noise: continue
        by = [[] for _ in range(L)]
        for r in S.noise_df(k, c["lock"], c["maxtr"], c["mon"]).itertuples():
            by[S.IDX[r.d]].append((float(r.ek), float(r.xk) + 0.5, S.KN, float(r.pnl), float(r.mae), float(r.risk), float(r.entry), int(r.side)))
        noise[k] = by
    for r in S.candace_df(1000).itertuples():
        if r.day in S.IDX: cand[S.IDX[r.day]].append((float(r.idx), float(r.exit_idx), S.KC, float(r.p1), float(r.stop_pts), 0.0, 0.0, 1 if r.dir == "LONG" else -1))
    return noise, cand


_T = {}


def run(k, fast, d0, d1, weekly=False):
    S = sim(k)
    ce = S.mk(**(FAST[k] if fast else TODAY[k])); cf = S.mk(**TODAY[k])
    if (k, fast) not in _T: _T[(k, fast)] = tapes(S, [ce, cf])
    noise, cand = _T[(k, fast)]
    fee_e, fee_r = FEE[k]
    accts = [Acct(S, ce, False, d0) for _ in range(5)] + [Acct(S, cf, True, d0) for _ in range(5)]
    fees = 5 * fee_e; nreset = 0; nbuy = 0; passed = 0; lost_f = 0; pay_total = 0.0; npay = 0; days_first = []; live_n = 0
    pending = []; rot = 0
    for di in range(d0, d1):
        accts += [Acct(S, ce if not f else cf, f, di, b) for (sd, f, b) in pending if sd <= di]; pending = [p for p in pending if p[0] > di]
        act = [a for a in accts if a.alive and a.start <= di]
        for a in act: a.day_start()
        stops = {a.c["stop"] for a in act}
        ev = []
        for sk in stops:
            for t in noise[sk][di]: ev.append((t[0], 0, t, sk))
        for t in cand[di]: ev.append((t[0], 1, t, None))
        ev.sort(key=lambda x: (x[0], x[1]))
        raw = [x[2] for x in ev if x[1] == 0]
        cand_open = []; dead = []
        for (m_in, isc, t, sk) in ev:
            if not isc:
                if any(mo > m_in and sd_ != t[7] for mo, sd_ in cand_open): continue    # household hedge lock vs a CANDACE position
                for a in act:
                    if a.alive and a.c["stop"] == sk:
                        if a.trade(t) == "dead": a.alive = False; dead.append(a)
            else:
                if any(n[1] > m_in and n[7] != t[7] for n in raw): continue             # an opposite NOISE position is open somewhere
                if any(mo > m_in and sd_ != t[7] for mo, sd_ in cand_open): continue
                el = [a for a in act if a.alive and a.c["nc"] > 0]
                n_ = len(el)
                for j in range(n_):                                                      # one free account per CANDACE trade, rotating
                    a = el[(rot + j) % n_]; r_ = a.trade(t)
                    if r_ != "skip":
                        rot = (rot + j + 1) % n_; cand_open.append((t[1], t[7]))
                        if r_ == "dead": a.alive = False; dead.append(a)
                        break
        wk = (not weekly) or S.DOW[S.DATES[di]] == 4
        for a in act:
            if not a.alive: continue
            r_ = a.day_end(wk)
            if r_ == "pass":
                a.alive = False; passed += 1; days_first.append(di - a.chain0 + 1)
                accts.append(Acct(S, cf, True, di + 1))             # converted account = fresh FUNDED account (activation fee assumed $0)
            elif r_ is not None:
                a.bal -= r_; a.cyc = 0.0; a.cdays = 0; a.cmax = 0.0; a.npay += 1
                pay_total += SPLIT * r_; npay += 1
                if a.npay >= MAXPAY: a.alive = False; live_n += 1
        for a in dead:
            if a.funded: lost_f += 1; fees += fee_e; nbuy += 1; pending.append((di + 1, False, di + 1))
            else: fees += fee_r; nreset += 1; pending.append((di + 1, False, a.chain0))
    return dict(passed=passed, resets=nreset, bought=nbuy, fees=fees, funded_alive=sum(1 for a in accts if a.alive and a.funded), funded_lost=lost_f,
                to_live=live_n, eval_alive=sum(1 for a in accts if a.alive and not a.funded), payouts=pay_total, n_payouts=npay, net=pay_total - fees,
                med_first=(st.median(days_first) if days_first else None), n_first=len(days_first))


def job(x):
    k, fast, view, w = x
    L = sim(k).L
    if view == "5y": return x, run(k, fast, 0, L, w)
    if view == "12m": return x, run(k, fast, L - 252, L, w)
    out = [run(k, fast, s, s + 252, w) for s in range(0, L - 252, 21)]   # rolling 12-month starts every 21 sessions
    nets = [o["net"] for o in out]
    return x, dict(n=len(out), net_med=st.median(nets), net_min=min(nets), net_max=max(nets), pos=sum(1 for n in nets if n > 0) / len(nets),
                   pass_med=st.median([o["passed"] for o in out]), pay_med=st.median([o["payouts"] for o in out]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        import time
        for f in (False, True):
            t = time.time(); print(run(25, f, 0, sim(25).L), round(time.time() - t, 1), "s")
        sys.exit()
    jobs = [(k, f, v, w) for k in (25, 50, 100, 150) for f in (False, True) for v in ("5y", "12m", "roll") for w in (False, True)]
    with mp.Pool(4) as p: res = dict(p.imap_unordered(job, jobs))
    json.dump({str(k): v for k, v in res.items()}, open(HERE + "/results.json", "w"), indent=1, default=float)
    print("done", len(res))
