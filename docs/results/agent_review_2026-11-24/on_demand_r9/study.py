"""r9 on-demand study (2026-11-24): weekly vs every-2-weeks vs daily-at-close (research) vs Lucid ON-DEMAND (intraday request, trading paused rest of day;
CONFIRMED help center user screenshot) vs on-demand WITHOUT the pause (counterfactual, NOT allowed by Lucid: isolates the effect of the pause).
Same engine/data as make_calc.py (fsim.life). Output: study.json + table (RESULTS.md numbers). Usage: python3 study.py [limit]"""
import sys, json, multiprocessing as mp
sys.path.insert(0, "/home/user/paytience/docs/results/agent_review_2026-11-24/calculator_r8")
import make_calc as M
MODES = {"weekly": (5, False, True), "2weeks": (10, False, True), "daily_close": (0, False, True), "on_demand": (0, True, True), "on_demand_nopause_counterfactual": (0, True, False), "on_demand_amount_not_session_limited_sensitivity": (0, "bal", True)}
SETUPS = [("fixed", 1), ("fixed", 2), ("fixed", 3), ("auto-high", 0), ("auto-regular", 0)]
def job(a):
    k, (mode, m) = a
    c = M.H.cfg(k, stop=100, N=m, nc=m, grow=None, cgrow=None) if mode == "fixed" else M.H.cfg(k, **(M.H.BUILT[k] if mode == "auto-high" else M.REG[k]))
    S, cc, days = M.prep(k, c)
    return k, mode, m, {name: M.cell(S, cc, days, k, cad, od, pa) for name, (cad, od, pa) in MODES.items()}
if __name__ == "__main__":
    jobs = [(k, s) for k in M.PLANS for s in SETUPS]
    jobs.sort(key=lambda a: (a[0], a[1][0], a[1][1]))
    if len(sys.argv) > 1: jobs = jobs[:int(sys.argv[1])]
    with mp.Pool(4) as p: out = p.map(job, jobs, chunksize=1)
    json.dump([dict(plan=k, setup=mode, micros=m, modes=r) for k, mode, m, r in out], open("study.json", "w"), indent=1)
    print("done", len(out))
