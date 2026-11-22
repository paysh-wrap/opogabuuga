"""Step 0b: re-run the pass_faster_100 150K rows (BASE, NOISE-4@$100, A) with the OLD code and compare with its results.json.
Run: cd <worktree>/backend && PYTHONPATH=. python3 ../docs/results/pass_fastest_150k/repro_sim.py"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE + "/../pass_faster_100")
import run_100 as R

old = json.load(open(HERE + "/../pass_faster_100/results.json"))
for name in ("BASE", "N100", "A", "B"):
    for win in ("ALL", "PICK", "JUDGE"):
        _, r = R.job((name, 150, "roll", win)); o = old[f"{name}|150|roll|{win}"]
        keys = ("pass_", "stuck", "run", "p60", "med", "p75")
        ok = all(abs((r[k] or 0) - (o[k] or 0)) < 1e-9 for k in keys)
        print(name, win, "MATCH" if ok else "DIFF", " ".join(f"{k}={r[k]:.1f}" if r[k] is not None else f"{k}=None" for k in keys))
