"""Step 0b: the NEW simulator (sim150.py) must reproduce the old pass_faster_100 150K rows (BASE, NOISE-4@$100, A) in ALL / PICK / JUDGE (pass, stuck, running,
<=60 d, median, p75) to the last digit, plus the plan constants must equal the old loader's.
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_fastest/validate150.py"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/../pass_faster_100")
import sim150 as S
import run_100 as R

p = R.P[150]
assert (p["size"], p["target"], p["mll"], p["lock_trig"], p["lock_lvl"], p["dll"], p["cons"], p["mpd"], p["kill"], p["margin"], p["day_stop"], p["cap_trade"], p["cost"]) == \
    (S.SIZE, S.TARGET, S.MLL, S.LOCK_TRIG, S.LOCK_LVL, S.DLL0, S.CONS, S.MPD, S.KILL, S.MARGIN, S.DSTOP, S.CAP_TRADE, S.COST1), "plan constants differ"
assert p["scale"] is True and R.RF.GMIN == S.GMIN and R.RF.F.SHRINK == S.SHRINK and R.RF.F.MINPCT == S.MINPCT
print("plan constants: identical to the old loader")
old = json.load(open(HERE + "/../pass_faster_100/results.json"))
rows = {"BASE": S.mk(), "N100": S.mk(stop=100, N=4, brake=None), "A": S.mk(stop=100, N=4, brake=None, nc=2, cwin=1000)}
allok = True
for nm, c in rows.items():
    t0 = time.time(); r = S.evaluate(c); dt = time.time() - t0
    for w in ("ALL", "PICK", "JUDGE"):
        o = old[f"{nm}|150|roll|{w}"]; n = r[w]
        diffs = []
        for k_old, k_new in (("pass_", "pass"), ("stuck", "stuck"), ("run", "run"), ("p60", "p60"), ("med", "med"), ("p75", "p75")):
            a, b = o[k_old], n[k_new]
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9): diffs.append((k_old, a, b))
        ok = not diffs; allok &= ok
        print(f"{nm:5s} {w:6s}", "MATCH" if ok else f"DIFF {diffs}", f"pass {n['pass']:.1f} stuck {n['stuck']:.1f} run {n['run']:.1f} <=60d {n['p60']:.1f} med {n['med']} p75 {n['p75']}", f"({dt:.1f}s)" if w == "ALL" else "")
    # static (profit / drawdown / trades per week) vs the old static rows
    for w in ("ALL",):
        o = old.get(f"{nm}|150|static|{w}")
        if o:
            if nm == "BASE": print("   static old:", {k: round(v, 1) for k, v in o.items() if isinstance(v, (int, float))})
            else: print("   static old:", {k: (round(v, 1) if isinstance(v, (int, float)) else v) for k, v in o.items() if k in ("profit", "dd", "tpw")})
            print("   static new:", {k: round(v, 1) for k, v in r["static"].items()})
# bootstrap protocol vs config/eval_odds.yaml (Pro 150K regular, EOD, all: pass 78 / stuck 14 / open 7, median 170 d)
c = S.mk()
bs = S.boot_summary(S.build_days(c, S.BD), c, S.boot_paths())
print("bootstrap BASE (600 x 400, seed 7): pass %.1f stuck %.1f open %.1f median %s   [eval_odds.yaml: 78 / 14 / 7 / 170]" % (bs["pass"], bs["stuck"], bs["run"], bs["med"]))
print("ALL VALIDATED" if allok else "MISMATCH")
