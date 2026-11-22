"""Fixed-size study: NOISE 1 micro ($250 stop) + CANDACE fixed micros (25K: 1, 50K: 2), variants A (one at a time) and B (both at once, same direction only).
Builds on ../pass_faster/pf_sim.py (NOISE sizing/shrink/room/STUCK rule, rolling protocol, summarize) - only the account loop is new.
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_faster_fixed/run_fixed.py [check]   -> results.json
"""
import sys, os, json, time, math, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../pass_faster"); sys.path.insert(0, HERE + "/../pass_faster_c125")
import numpy as np, pandas as pd, multiprocessing as mp
import pf_sim as F

N, C = 0, 1
CAPC = 125.0
dates, op = F.trading_days()
P = F.load_plans(); t, t80, c, v = F.load_streams()
GMIN = F.smin(float(t[t.d >= '2025-11-06'].entry.mean()))
cst = c[c.day >= "2021-10-21"]


def build(n_df, c_df):
    """date -> sorted tuples (m_in, m_out, kind, a, b, c, d, dir)  N: (pnl, mae, risk, entry)  C: (pts, stop_pts, 0, 0)"""
    by = {}
    for r in n_df.itertuples():
        by.setdefault(r.d, []).append((float(r.ek), float(r.xk) + 0.5, N, float(r.pnl), float(r.mae), float(r.risk), float(r.entry), int(r.side)))
    if c_df is not None:
        for r in c_df.itertuples():
            by.setdefault(r.day, []).append((float(r.idx), float(r.exit_idx), C, float(r.p1), float(r.stop_pts), 0.0, 0.0, 1 if r.dir == "LONG" else -1))
    for d in by: by[d].sort(key=lambda x: (x[0], x[2]))
    return by


def new_cnt():
    return {"sig": [0, 0], "taken": [0, 0], "open": [0, 0], "hedge": [0, 0], "room": [0, 0], "dll": [0, 0], "shrunk": [0, 0], "over125": 0}


def closes(o, kind, m_in):
    """is position o (m_out, kind, ...) closed before a new signal of `kind` at m_in? (NOISE flips on its own exit bar)"""
    return o[0] < m_in or (kind == N and o[1] == N and o[0] - 0.5 <= m_in)


def simulate(days, idx, p, gmin, cfg, maxs=100000):
    """cfg: nc (CANDACE micros), nn (NOISE micros), both (True = variant B). Open positions realise their P&L at their exit."""
    kd = p["kill"]; mg = p["margin"]; size = p["size"]; nc = cfg["nc"]; both = cfg["both"]
    bal = size; floor = bal - p["mll"]; peak = bal; locked = False; mll = p["mll"]; dll0 = p["dll"]
    pdays = 0; best = 0.0; s = 0; peak_e = bal
    dstop = (p["cons"] - p["buf"]) / 100 * p["target"]
    for di in idx:
        s += 1
        if s > maxs: break
        st = {"today": 0.0, "pk": 0.0, "stop": False, "open": []}
        dll = dll0
        if p["scale"] and locked: dll = 0.6 * (peak_e - size)

        def settle(pred):
            nonlocal bal
            st["open"].sort(key=lambda o: o[0]); rest = []
            for o in st["open"]:
                if st["stop"]: continue
                if not pred(o): rest.append(o); continue
                pq = o[4]
                if dll and st["today"] + pq <= -dll: pq = -dll - st["today"]; st["stop"] = True
                if st["today"] + pq > dstop: pq = dstop - st["today"]; st["stop"] = True
                st["today"] += pq; bal += pq; st["pk"] = max(st["pk"], st["today"])
                if o[5] or bal <= floor + kd: return True
            st["open"] = [] if st["stop"] else rest
            return False

        for (m_in, m_out, kind, a, b, cc, d, dr) in days[di]:
            if st["stop"]: break
            if settle(lambda o: closes(o, kind, m_in)): return "bust", s
            if st["stop"]: break
            op_ = st["open"]; today = st["today"]
            if op_:
                if not both: continue
                if any(o[2] != dr for o in op_): continue
            ow = sum(o[3] for o in op_)
            room_m = bal - floor - kd - ow
            if kind == N:
                pnl, mae, risk, entry = a, b, cc, d
                if bal - floor <= kd: return "stuck", s
                room0 = room_m
                if dll: room0 = min(room0, dll + today - ow)
                q = cfg["nn"]; pp = None; eff = mae; S_ = risk
                while q > 0:
                    S_ = risk
                    if q * risk > F.SHRINK * room0:
                        pt = math.floor(((F.SHRINK * room0 / q) - F.FEE) / F.TV - F.SLIP)
                        if pt * 0.25 < F.MINPCT * entry or pt <= 0: q = -1; break
                        S_ = pt * F.TV + F.FEE + F.TV
                    if q * S_ + mg <= room0:
                        pp = -S_ if (S_ < risk and mae >= S_) else pnl
                        eff = min(mae, S_) if S_ < risk else mae
                        break
                    q -= 1
                if q <= 0:
                    if not op_ and F.SHRINK * (bal - floor - kd) < gmin: return "stuck", s
                    continue
                worst = q * S_; dead = (q * eff >= bal - floor - kd - ow); pq = q * pp
                if dead: pq = -(bal - floor - kd - ow)
            else:
                per = b / p["tick"] * p["tv"] + p["fee"] + 2 * p["slip"] * p["tv"]
                left = None
                if dll:
                    left = dll - (max(0.0, st["pk"], today) - today) - ow
                    if left <= 0:
                        if not op_: st["stop"] = True
                        continue
                lim = room_m if left is None else min(room_m, left)
                q = nc
                while q >= 1 and q * per + mg > lim: q -= 1
                if q < 1: continue
                worst = q * per; dead = False; pq = q * (a * F.PV - p["cost"])
            st["open"].append([m_out, kind, dr, worst, pq, dead])
        if not st["stop"] and settle(lambda o: True): return "bust", s
        today = st["today"]
        if today > 0: pdays += 1; best = max(best, today)
        peak_e = max(peak_e, bal)
        if bal > peak and not locked:
            peak = bal
            if peak >= p["lock_trig"]: locked = True; floor = p["lock_lvl"]
            else: floor = peak - mll
        prof = bal - size
        if prof >= p["target"] and pdays >= p["mpd"] and (not p["cons"] or best <= p["cons"] / 100 * prof): return "pass", s
    return "open", s


def roll(by, win, p, cfg):
    a, b = F.WIN[win]; ds = [d for d in dates if a <= d <= b]
    days = F.day_lists(by, ds); L = len(days)
    return F.summarize([simulate(days, range(s, L), p, GMIN, cfg) for s in range(L)])


def static(by, win, p, cfg):
    """fresh account, balance-independent: skip reasons, plan-sized profit, worst closed-trade drawdown, trades per week."""
    a, b = F.WIN[win]; ds = [d for d in dates if a <= d <= b]
    cnt = new_cnt(); eq = pk = dd = 0.0; both = cfg["both"]; dll = p["dll"]; mll = p["mll"]
    def real(o):
        nonlocal eq, pk, dd
        eq += o[4]; pk = max(pk, eq); dd = max(dd, pk - eq)
    for d in ds:
        openp = []
        for (m_in, m_out, kind, x, y, z, w, dr) in by.get(d, []):
            cnt["sig"][kind] += 1
            for o in sorted([o for o in openp if closes(o, kind, m_in)], key=lambda o: o[0]): real(o)
            openp = [o for o in openp if not closes(o, kind, m_in)]
            if openp:
                if not both: cnt["open"][kind] += 1; continue
                if any(o[2] != dr for o in openp): cnt["hedge"][kind] += 1; continue
            ow = sum(o[3] for o in openp); lim = min(mll - p["kill"], dll) - ow
            if kind == N:
                q = cfg["nn"]
                if q * z + p["margin"] > lim: cnt["room"][kind] += 1; continue
                worst = q * z; pq = q * x
            else:
                per = y / p["tick"] * p["tv"] + p["fee"] + 2 * p["slip"] * p["tv"]
                if per > CAPC: cnt["over125"] += 1
                q = cfg["nc"]
                while q >= 1 and q * per + p["margin"] > lim: q -= 1
                if q < 1: cnt["room"][kind] += 1; continue
                if q < cfg["nc"]: cnt["shrunk"][kind] += 1
                worst = q * per; pq = q * (x * F.PV - p["cost"])
            cnt["taken"][kind] += 1; openp.append([m_out, kind, dr, worst, pq])
        for o in sorted(openp, key=lambda o: o[0]): real(o)
    return dict(profit=eq, dd=dd, cnt=cnt, tpw=sum(cnt["taken"]) / (len(ds) / 5.0), ndays=len(ds))


T_N = build(t, None); T_NC = build(t, cst)
BASE_T = F.build_table(t)


def pcopy(k, **kw):
    p = copy.deepcopy(P[k]); p["row"].update(kw); return p


ROWS = []
for k, nc in ((25, 1), (50, 2)):
    ROWS += [("BASE", k, "base", None), ("NOISE1", k, "n1", None),
             ("A", k, "mix", {"nc": nc, "nn": 1, "both": False}), ("B", k, "mix", {"nc": nc, "nn": 1, "both": True})]
ROWS += [("C125_1", 25, "c125_1", None)]


def job(a):
    name, k, meth, win = a
    row = [r for r in ROWS if r[0] == name and r[1] == k][0]; kind, spec = row[2], row[3]
    p = P[k]
    if kind in ("base", "n1"):
        if kind == "n1":
            p = pcopy(k, contracts=1); p["row"].pop("brake_below", None); p["row"].pop("brake_contracts", None)
        if meth == "roll": return a, F.run_roll(BASE_T, win, p, GMIN, dates)
        return a, F.static_stats(BASE_T, win, p, dates, None)
    if kind == "c125_1":
        import run_c125 as R; R.VARIANT["mode"] = "c125_1"
        by, ref, _ = R.MIX["C125_1"]
        if meth == "roll": return a, F.run_roll(by, win, p, GMIN, dates, ref)
        return a, F.static_stats(by, win, p, dates, None)
    by = T_NC if spec["nc"] else T_N
    if meth == "roll": return a, roll(by, win, p, spec)
    return a, static(by, win, p, spec)


if __name__ == "__main__":
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        old = json.load(open(HERE + "/../pass_faster_c125/results.json"))
        for nm in ("BASE", "C125_1"):
            for w in ("ALL", "JUDGE"):
                _, r = job((nm, 25, "roll", w)); o = old[f"{nm}|25|roll|{w}"]
                print(nm, w, "MATCH" if all(abs((r[x] or 0) - (o[x] or 0)) < 1e-9 for x in ("pass_", "bust_all", "run", "med", "p75")) else "DIFF", r["pass_"], o["pass_"])
        sys.exit()
    wins = ("ALL", "PICK", "JUDGE")
    names = sorted({(r[0], r[1]) for r in ROWS})
    jobs = [(n, k, m, w) for n, k in names for m in ("roll", "static") for w in wins]
    with mp.Pool(4) as pool: res = pool.map(job, jobs, chunksize=1)
    out = {"|".join(map(str, a)): r for a, r in res}; out["_meta"] = dict(gmin=GMIN)
    json.dump(out, open(HERE + "/results.json", "w"), indent=1, default=float)
    print("done", time.time() - t0)
