"""Pass-fastest 50K study: build every NOISE stream variant + the unrestricted afternoon-fade stream (research only; nothing in backend/app is touched).

NOISE   : session-20 generator `noise3.gen` (shipped engine mirror: hourly checks 10:00..15:00, band/VWAP exits, flat 16:00, roll guard) with
          stop_usd (risk per micro = exactly this many $), lock trigger (+lock_pts -> stop to entry+10), max entries a day, Mondays off/on.
          Shipped = stop 250, trigger 100, max 3, Mondays off (reproduces pass_faster/streams_noise_base.csv exactly).
FADE    : session-19 `fade2.gen(set())` = the PM_FADE signals of EVERY day (13:01-15:29 ET, band 2.0, $250 stop, target VWAP, one try per day);
          the causal rule (fade only if the config's NOISE has not entered earlier that day) is applied per config inside the simulator.
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest_50k/gen_streams.py [check|all]
Streams go to $PF50_CACHE (default: scratchpad/pf50/streams), they are not part of the deliverable (regenerate with this script).
"""
import sys, os, types, time, pickle, itertools
MODE = sys.argv[1] if len(sys.argv) > 1 else "all"
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PKL = "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/data/days.pkl"
CACHE = os.environ.get("PF50_CACHE", "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/pf50/streams")
os.makedirs(CACHE, exist_ok=True)

STOPS = (75, 100, 125, 150, 175, 200, 225, 250, 300)
TRIGS = (80, 100, 120)
MAXES = (2, 3)
MONS = (0, 1)          # 0 = Mondays off (shipped), 1 = Mondays on


def _setup():
    sys.argv = [sys.argv[0], PKL]
    S20 = WT + "/docs/results/session20/strategy_review"
    S19 = WT + "/docs/results/session19/refine"
    sys.path.insert(0, S19); sys.path.insert(0, S20)
    src = open(S20 + "/lib.py").read().replace('SP + "/data/days12.pkl"', repr(PKL))
    nlib = types.ModuleType("lib"); nlib.__file__ = S20 + "/lib.py"; sys.modules["lib"] = nlib
    exec(compile(src, S20 + "/lib.py", "exec"), nlib.__dict__)
    import noise3, noise2, fade2
    return nlib, noise3, noise2, fade2


def fade_gen_xk(lib, noise2, band=2.0, stop_usd=250.0, first=210, last=358, min_ticks=4, flat_k=385):
    """Copy of session19 fade2.gen (noise_days = {} i.e. every day) that also records the exit bar xk. Identical rules: close_k > VWAP + band*sd -> SHORT,
    < VWAP - band*sd -> LONG, sd = population std of (close - VWAP) over today's bars <= k; fill next bar open +/- 1 tick; target = VWAP at the signal;
    stop = $250; flat 15:55 (bar 385); one try per day (TARGET_TOO_CLOSE ends the day)."""
    import numpy as np, pandas as pd
    PV, TICK, FEE = lib.PV, lib.TICK, lib.FEE
    D, F, moves = noise2.data(); out = []
    hard = (stop_usd - FEE - 2 * TICK * PV) / PV
    for i in range(14, len(D)):
        d, a = D[i]
        if d < lib.S0 or d > lib.J1 or d not in F: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        dev = np.nan_to_num(c - vw); n = np.cumsum(~np.isnan(c - vw)); s1 = np.cumsum(dev); s2 = np.cumsum(dev * dev)
        for k in range(first, last + 1):
            if np.isnan(c[k]) or np.isnan(vw[k]) or n[k] < 5: continue
            m = s1[k] / n[k]; sd = np.sqrt(max(s2[k] / n[k] - m * m, 0))
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + band * sd else (1 if c[k] < vw[k] - band * sd else 0)
            if not s: continue
            e = o[k + 1] + s * TICK; tgt = vw[k]
            if (tgt - e) * s < min_ticks * TICK: break
            stop = e - s * hard; px = None; mae = 0.; xj = None
            for j in range(k + 1, flat_k + 1):
                mae = max(mae, s * (e - (l[j] if s > 0 else h[j])))
                if (s > 0 and l[j] <= stop) or (s < 0 and h[j] >= stop): px = (min(stop, o[j]) if s > 0 else max(stop, o[j])) - s * TICK; xj = j; break
                if (s > 0 and h[j] >= tgt) or (s < 0 and l[j] <= tgt): px = tgt; xj = j; break
                if j == flat_k: px = c[j] - s * TICK; xj = j
            out.append(dict(d=d, ek=k + 1, xk=xj, pnl=(px - e) * s * PV - FEE, mae=mae * PV + FEE, side=s)); break
    return pd.DataFrame(out)


def key(stop, trig, mx, mon):
    return f"s{int(stop)}_t{int(trig)}_m{int(mx)}_mon{int(mon)}"


def gen_noise(noise3, nlib, stop, trig, mx, mon):
    dayskip = None if mon else noise3.monday
    return noise3.gen(stop_usd=float(stop), maxtr=int(mx), lock=(float(trig), 10.0), dayskip=dayskip)


def main():
    mode = MODE
    nlib, noise3, noise2, fade2 = _setup()
    import pandas as pd, numpy as np
    t0 = time.time()
    # ---- checks against the stored streams
    ref250 = pd.read_csv(WT + "/docs/results/pass_faster/streams_noise_base.csv")
    ref100 = pd.read_csv(WT + "/docs/results/pass_faster_100/streams_noise_stop100.csv")
    b250 = gen_noise(noise3, nlib, 250, 100, 3, 0); b100 = gen_noise(noise3, nlib, 100, 100, 3, 0)

    def same(a, b):
        return len(a) == len(b) and all((a[c].values == b[c].values).all() for c in ("d", "ek", "xk", "side")) and abs(a.pnl.values - b.pnl.values).max() < 1e-9 \
            and abs(a.mae.values - b.mae.values).max() < 1e-9 and abs(a.risk.values - b.risk.values).max() < 1e-9
    print("NOISE $250 == pass_faster/streams_noise_base.csv:", same(ref250, b250), len(b250), round(b250.pnl.sum(), 1), flush=True)
    print("NOISE $100 == pass_faster_100/streams_noise_stop100.csv:", same(ref100, b100), len(b100), round(b100.pnl.sum(), 1), flush=True)
    b250.to_csv(f"{CACHE}/{key(250, 100, 3, 0)}.csv", index=False); b100.to_csv(f"{CACHE}/{key(100, 100, 3, 0)}.csv", index=False)
    # ---- fade: all days; check against streams_fade_F0.csv on days where the session-19 baseline NOISE did not trade
    fall = fade_gen_xk(nlib, noise2)           # = fade2.gen(set()) with the exit bar `xk` recorded (needed for the one-position rule)
    ref_all = fade2.gen(set())
    assert len(ref_all) == len(fall) and all((ref_all[c].values == fall[c].values).all() for c in ("d", "ek", "pnl", "mae", "side")), "fade copy differs from fade2.gen"
    base19 = noise2.gen(); nd = set(base19.d)
    f0 = pd.read_csv(WT + "/docs/results/session19/refine/streams_fade_F0.csv"); f0 = f0[(f0.d >= "2021-10-21") & (f0.d <= "2026-10-30")]
    mine = fall[~fall.d.isin(nd)]
    ok = len(mine) == len(f0) and all((mine[c].values == f0[c].values).all() for c in ("d", "ek", "side")) and abs(mine.pnl.values - f0.pnl.values).max() < 1e-9
    print("FADE (all days, restricted to days without session-19 NOISE) == streams_fade_F0.csv (2021-10-21+):", ok, len(mine), len(f0), "all-days fade trades:", len(fall), flush=True)
    fall.to_csv(f"{CACHE}/fade_all_days.csv", index=False)
    if mode == "check":
        print("check done", round(time.time() - t0, 1), "s"); return
    # ---- every NOISE variant
    n = 0
    for stop, trig, mx, mon in itertools.product(STOPS, TRIGS, MAXES, MONS):
        fn = f"{CACHE}/{key(stop, trig, mx, mon)}.csv"
        if os.path.exists(fn): continue
        g = gen_noise(noise3, nlib, stop, trig, mx, mon); g.to_csv(fn, index=False); n += 1
        if n % 10 == 0: print("generated", n, key(stop, trig, mx, mon), len(g), round(g.pnl.sum(), 1), round(time.time() - t0, 1), "s", flush=True)
    print("all streams done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
