"""Step 0 of the pass-fastest 50K study: REPRODUCE the earlier numbers and validate the new simulator against the old ones (stop and report if anything is off).
 1. BASE / NOISE-2@$100 / row A / row B (Pro 50K, 5y + pick + judge) from pass_faster_100/results.json, recomputed with the OLD code (pf_sim / run_fixed) AND with lib50.
 2. per-start equality (outcome + sessions on all 1,252 starts) of lib50.sim_a / sim_b with the old simulators.
 3. lib50 sizing (grow / taper / brake) == the app's pure `risk.strategy_sizing.auto_contracts` on a dense grid.
 4. the NOISE generator at $250 / $100 = the stored shipped streams (done in gen_streams.py check).
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest_50k/repro.py
"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/../pass_faster_100"); sys.path.insert(0, HERE + "/../pass_faster_fixed"); sys.path.insert(0, HERE + "/../pass_faster_c125")
import numpy as np
import lib50 as L
import run_100 as R100           # old study code: tables for the $100 stream (+ CANDACE capped at $100), account loop run_fixed.simulate
RF = R100.RF; F = L.F

ref = json.load(open(HERE + "/../pass_faster_100/results.json"))
ok_all = True


def cmp(name, mine, old, tol=1e-9):
    global ok_all
    keys = ("pass_", "stuck", "run", "p60", "med", "p75", "npass")
    good = all(abs((mine[k] or 0) - (old[k] or 0)) <= tol for k in keys)
    ok_all &= good
    print(f"  {name:34s} pass {mine['pass_']:.2f}/{old['pass_']:.2f}  stuck {mine['stuck']:.2f}/{old['stuck']:.2f}  <=60d {mine['p60']:.2f}/{old['p60']:.2f}  med {mine['med']}/{old['med']}  -> {'MATCH' if good else 'DIFF'}")


t0 = time.time()
print("GMIN lib50", L.gmin(), "old", RF.GMIN)
assert abs(L.gmin() - RF.GMIN) < 1e-12

# ---- 1+4: summaries vs stored results.json (stored = old code); also old code re-run now
print("1) BASE / NOISE-2@$100 / A / B vs pass_faster_100/results.json (mine / stored)")
cfgs = {"BASE": L.BASE, "N100": L.NOISE2_100, "A": L.ROW_A, "B": dict(L.ROW_A, both=1)}
# the $100 rows use CANDACE capped at $100 per micro in the old study; lib50 caps at $125. Check the cap changes nothing on the base CANDACE stream:
print("  CANDACE signals kept at $125 cap:", L.cand_tuples(1000)[1:], "; at $100 cap:", len(R100.cst_cap), "of", len(R100.cst))
for nm, c in cfgs.items():
    days = L.build_days(c)
    for w in ("ALL", "PICK", "JUDGE"):
        o, n, cp, cb = L.roll(days, c, w, both=bool(c["both"]))
        cmp(f"{nm} {w}", L.summ(o, n), ref[f"{nm}|50|roll|{w}"])

# ---- 2: per-start equality with the old simulators
print("2) per-start equality (all 1,252 starts)")
# BASE: F.simulate via run_roll detail
det = F.run_roll(RF.BASE_T, "ALL", RF.P[50], RF.GMIN, RF.dates)["detail"]
days = L.build_days(L.BASE); o, n, _, _ = L.roll(days, L.BASE, "ALL")
inv = {0: "pass", 1: "stuck", 2: "bust", 3: "open"}
diff = sum(1 for (d, oo, ss), a, b in zip(det, o, n) if oo != inv[int(a)] or ss != int(b))
print("  BASE vs pf_sim.simulate: starts differing =", diff); ok_all &= diff == 0
for nm, bys, both in (("N100", R100.T_N, False), ("A", R100.T_NC, False), ("B", R100.T_NC, True)):
    c = cfgs[nm]; days = L.build_days(c)
    # old tables carry the same tuples (m_in, m_out, kind, a, b, c, d, dir) -> compare day lists too
    old_days = F.day_lists(bys, L.ALL_D); same_days = all(sorted(map(tuple, ol)) == sorted(map(tuple, nl)) for ol, nl in zip(old_days, days))
    print(f"  {nm}: table identical to old study table: {same_days}")
    cfg_old = {"nn": 2, "nc": 1 if nm != "N100" else 0, "both": both}
    o, n, _, _ = L.roll(days, c, "ALL", both=both)
    bad = 0
    for s in range(len(o)):
        r = RF.simulate(old_days, range(s, len(old_days)), RF.P[50], RF.GMIN, cfg_old)
        if r[0] != inv[int(o[s])] or r[1] != int(n[s]): bad += 1
    print(f"  {nm} vs run_fixed.simulate: starts differing = {bad}"); ok_all &= bad == 0 and same_days

# ---- 3: sizing function vs app
print("3) lib50 sizing vs app.risk.strategy_sizing.auto_contracts")
from decimal import Decimal as D
from app.risk.strategy_sizing import SizeTier, auto_contracts
mism = 0; tot = 0
rows = []
for nn in (1, 2, 3, 4):
    for grow, gmax in ((0, 0), (600, 3), (600, 4), (1000, 3), (1000, 4)):
        if grow and gmax < nn: continue
        for bb in (0, 0.35, 0.5):
            for tb in (0, 0.25, 0.5):
                rows.append((nn, grow, gmax, bb, tb))
for nn, grow, gmax, bb, tb in rows:
    tier = SizeTier(D(50000), D(2000), nn, D(str(bb)) if bb else None, 1 if bb else None, D(grow) if grow else None, gmax if grow else None, D(str(tb)) if tb else None, 1 if tb else None)
    for cush in range(0, 2601, 25):
        for remf in (1.0, 0.9, 0.7, 0.51, 0.5, 0.49, 0.3, 0.25, 0.24, 0.1, 0.0):
            ref_q = auto_contracts(D(50000), D(cush), [tier], D(str(remf))).contracts
            # lib50 inline logic
            q = nn
            if grow:
                e = int(cush // grow) - 1
                if e > 0: q = nn + e
                if q > gmax: q = gmax
            tgt = 3000.0; bal0_minus_size = tgt * (1 - remf)
            if tb and (tgt - bal0_minus_size) < tb * tgt:
                if 1 < q: q = 1
            if bb and cush < bb * 2000:
                if 1 < q: q = 1
            tot += 1; mism += q != ref_q
print(f"  grid points {tot}, mismatches {mism}"); ok_all &= mism == 0
print("ALL CHECKS", "PASSED" if ok_all else "FAILED", round(time.time() - t0, 1), "s")
