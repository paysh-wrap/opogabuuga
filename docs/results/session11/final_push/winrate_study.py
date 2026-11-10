"""Final-push win-rate study. Trade generation = rebuild_main_csv.py noise_t / pm_fade (copied, generalised with variant knobs;
defaults reproduce the MAIN stream). Pick on 2021-11..2023-12, judge on 2024-01..2026-10. Closed bars only: stop moves / BE
take effect from the bar AFTER the bar whose close triggered them. Multi-micro variants report pnl PER MICRO (average)."""
import sys, pickle, os
import numpy as np, pandas as pd
ROOT = "/home/user/opogabuuga"
sys.path[:0] = [ROOT + "/docs/results/session10/five_year"]
import noise_gen as NG
MNQ = f"{ROOT}/backend/app/backtest/data/raw/mnq_5y.csv"
HERE = f"{ROOT}/docs/results/session11/final_push"
START, END, SPLIT = "2021-11-01", "2026-10-30", "2023-12-31"
PV, TICK, FEE, PTS = 2.0, 0.25, 1.0, (250 - 2) / 2

def hm(k): return f"{9 + (30 + k) // 60:02d}:{(30 + k) % 60:02d}"

def noise_t(days, be=None, lock=0.0, part=None, look=14, maxtr=3, step=60, confirm=0, norefire=False):
    """be: pts of close-profit that moves stop to entry+lock; part: (pts) -> 2 micros, one takes +pts limit, then rest stop->entry"""
    moves = np.array([np.abs(a["close"] / a["open"][0] - 1) for _, a in days])
    checks = set(range(29, 360, step)); out = []; last_exit = {}
    for i in range(look, len(days)):
        d, a = days[i]
        if d < START or d > END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = days[i - 1][1]["close"][389]
        if np.isnan(pc) or abs(o[0] / pc - 1) > 0.015: continue
        sig = np.nanmean(moves[i - look:i], axis=0)
        ub = max(o[0], pc) * (1 + sig); lb = min(o[0], pc) * (1 - sig)
        st = dict(pos=0); ntr = pending = 0
        def close_trade(px, k):
            legs = st["legs"]  # remaining legs + banked
            p = st["bank"] + legs * ((px - st["entry"]) * st["pos"] * PV - FEE)
            out.append((d, p / st["n"], "NOISE", hm(st["ek"]))); st["pos"] = 0; last_exit[d] = k
        for k in range(390):
            if np.isnan(c[k]): continue
            if pending and st["pos"] == 0:
                e = o[k] + pending * TICK
                st.update(entry=e, pos=pending, ek=k, hs=e - pending * PTS, n=2 if part else 1, legs=2 if part else 1, bank=0.0, armed=False)
                pending = 0
            pos = st["pos"]
            if pos:
                if (pos > 0 and l[k] <= st["hs"]) or (pos < 0 and h[k] >= st["hs"]):
                    if norefire and (st["hs"] - st["entry"]) * pos >= 0: ntr = maxtr   # locked/BE stop-out -> done for the day
                    close_trade((min(st["hs"], o[k]) if pos > 0 else max(st["hs"], o[k])) - pos * TICK, k)
                elif part and st["legs"] == 2:
                    tg = st["entry"] + pos * part
                    if (pos > 0 and h[k] >= tg) or (pos < 0 and l[k] <= tg):
                        st["bank"] = part * PV - FEE; st["legs"] = 1; st["armed"] = True
            if st["pos"] and k == 389: close_trade(c[k] - st["pos"] * TICK, k)
            if st["pos"]:
                pos = st["pos"]
                if be is not None and (c[k] - st["entry"]) * pos >= be: st["hs"] = st["entry"] + pos * lock if (st["hs"] - st["entry"]) * pos < lock else st["hs"]
                if st["armed"]: st["hs"] = st["entry"] if (st["hs"] - st["entry"]) * pos < 0 else st["hs"]; st["armed"] = False
            if k in checks:
                pos = st["pos"]
                if pos:
                    trail = max(ub[k], vw[k]) if pos > 0 else min(lb[k], vw[k])
                    if (pos > 0 and c[k] < trail) or (pos < 0 and c[k] > trail):
                        nk = k + 1
                        close_trade((o[nk] if nk < 390 and not np.isnan(o[nk]) else c[k]) - pos * TICK, nk)
                if st["pos"] == 0 and ntr < maxtr:
                    side = 1 if c[k] > ub[k] else (-1 if c[k] < lb[k] else 0)
                    if side and confirm and k >= confirm:   # last `confirm` closed 1-min bars must all be beyond the band too
                        seg = c[k - confirm:k]; bnd = (ub if side > 0 else lb)[k - confirm:k]
                        if not np.all((seg - bnd) * side > 0): side = 0
                    if side: pending, ntr = side, ntr + 1
    return out, last_exit

def walk(s, e, stop, tgt, H, L, O, C, j0, j1, half=False, be=None):
    """-> (pnl per micro, exit bar). half: 2 micros, one at halfway to tgt, then stop->entry. be: pts close-profit -> stop to entry."""
    legs, bank, n = (2, 0.0, 2) if half else (1, 0.0, 1)
    mid = e + (tgt - e) / 2; nstop = stop
    for j in range(j0, j1):
        stop = nstop
        if (s > 0 and L[j] <= stop) or (s < 0 and H[j] >= stop):
            return (bank + legs * (((min(stop, O[j]) if s > 0 else max(stop, O[j])) - s * TICK - e) * s * PV - FEE)) / n, j
        if half and legs == 2 and ((s > 0 and H[j] >= mid) or (s < 0 and L[j] <= mid)):
            bank = (mid - e) * s * PV - FEE; legs = 1; nstop = e
        if (s > 0 and H[j] >= tgt) or (s < 0 and L[j] <= tgt):
            return (bank + legs * ((tgt - e) * s * PV - FEE)) / n, j
        if be is not None and (C[j] - e) * s >= be: nstop = e if (nstop - e) * s < 0 else nstop
    return (bank + legs * ((C[j1 - 1] - s * TICK - e) * s * PV - FEE)) / n, j1 - 1

def pm_fade(days, noise_days, last_exit, band=2.0, k0=210, k1=359, maxf=1, after_noise=False, half=False, be=None, ok_days=None):
    out = []
    for d, a in days:
        if d < START or d > END: continue
        ks = k0
        if d in noise_days:
            if not after_noise or (ok_days is not None and d not in ok_days): continue
            ks = max(k0, last_exit[d] + 1)
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        nf = 0; k = ks
        while k < k1 and nf < maxf:
            if np.isnan(c[k]) or np.isnan(vw[k]): k += 1; continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: k += 1; continue
            s = -1 if c[k] > vw[k] + band * sd else (1 if c[k] < vw[k] - band * sd else 0)
            if not s: k += 1; continue
            e = o[k + 1] + s * TICK
            if (vw[k] - e) * s < 4 * TICK: break
            p, jx = walk(s, e, e - s * PTS, vw[k], h, l, o, c, k + 1, 386, half, be)
            out.append((d, p, "FADE", hm(k + 1))); nf += 1; k = jx + 1
    return out

def stats(t):
    if len(t) == 0: return dict(n=0, win=0, pf=0, usd=0, dd=0, wd=0)
    w = t.pnl > 0; dly = t.groupby("date").pnl.sum(); eq = dly.cumsum()
    return dict(n=len(t), win=w.mean() * 100, pf=t.pnl[w].sum() / -t.pnl[~w].sum(), usd=t.pnl.sum(),
                dd=(eq.cummax().clip(lower=0) - eq).max(), wd=dly.min())

def build(days, nkw={}, fkw={}, after_if=None):
    """after_if: 'win' -> fade after NOISE only on days whose closed NOISE trades net > 0 (known at fade time: fade starts after last NOISE exit)"""
    nt, le = noise_t(days, **nkw)
    ok = None
    if after_if:
        dp = {}
        for x in nt: dp[x[0]] = dp.get(x[0], 0) + x[1]
        ok = {d for d, p in dp.items() if p > 0}
    ft = pm_fade(days, {x[0] for x in nt}, le, ok_days=ok, **fkw)
    return pd.DataFrame(nt + ft, columns=["date", "pnl", "strategy", "entry_time"]).sort_values(["date", "entry_time"]).reset_index(drop=True)

def halves(t): return stats(t[t.date <= SPLIT]), stats(t[t.date > SPLIT])

if __name__ == "__main__":
    cache = HERE + "/days.pkl"
    if os.path.exists(cache): days = pickle.load(open(cache, "rb"))
    else:
        days, nb = NG.load_days(MNQ); pickle.dump(days, open(cache, "wb"))
    V = {"BASE": ({}, {})}
    for x in (20, 40, 60, 80): V[f"N_BE{x}"] = ({"be": x}, {})
    for x in (40, 60): V[f"N_LOCK{x}_+10"] = ({"be": x, "lock": 10}, {})
    for x in (20, 40, 60, 80): V[f"N_PART{x}"] = ({"part": x}, {})
    for b in (1.5, 2.5, 3.0): V[f"F_BAND{b}"] = ({}, {"band": b})
    V["F_2ND"] = ({}, {"maxf": 2}); V["F_AFTER_NOISE"] = ({}, {"after_noise": True})
    V["F_2ND+AFTER"] = ({}, {"maxf": 2, "after_noise": True})
    V["F_HALF"] = ({}, {"half": True})
    for x in (10, 20): V[f"F_BE{x}"] = ({}, {"be": x})
    for k0 in (180, 240, 270): V[f"F_START{hm(k0)}"] = ({}, {"k0": k0})
    V["F_END14:30"] = ({}, {"k1": 300})
    rows = []; T = {}
    for name, (nk, fk) in V.items():
        t = build(days, nk, fk); T[name] = t; a, b = halves(t); rows.append((name, a, b))
        print(name, {k: round(v, 2) for k, v in a.items()}, {k: round(v, 2) for k, v in b.items()}, flush=True)
    pickle.dump((rows, T), open(HERE + "/results.pkl", "wb"))
