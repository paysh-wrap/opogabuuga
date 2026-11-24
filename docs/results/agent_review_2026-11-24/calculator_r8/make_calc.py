"""Generates config/income_calc.json for the Dashboard profit calculator (research projection, UNVERIFIED).
MAIN strategy = Fast Evaluation NOISE + CANDACE (fast-pass setups) replayed through the FUNDED rules of funded_payout_r6/fsim.py
(EOD MLL + lock, DLL + LucidScale, payout consistency 35%, kill $50, news hard breach, $2/micro RT) on /home/user/days.pkl (MNQ 1-min RTH).
Micros 1..9 = NOISE and CANDACE both at N micros (stop $100, profit lock 100/10), optional growth (+1 micro per $g of cushion, cap 9).
Auto = the plan's own fast_pass_*_cfg sizes+brakes (profile high = r6 candidate a) or the lowest brake step (profile regular = r6 candidate b / b2).
Payout cadence: 5 / 10 sessions = a payout is requested only on those days; 0 = on-demand (whenever eligible; UNVERIFIED model). Per account, first 250 sessions."""
import sys
sys.path[:0] = ["/home/user/paytience/docs/results/agent_review_2026-11-24/pass_faster_r4", "/home/user/paytience/docs/results/agent_review_2026-11-24/refine_round3"]
import json, types, multiprocessing as mp, numpy as np
R6 = "/home/user/paytience/docs/results/agent_review_2026-11-24/funded_payout_r6/"
src = open(R6 + "fsim.py").read()
src = src.replace("horizon=250, eval_mode=False):", "horizon=250, eval_mode=False, cad=0):")
a = "        if cp > 0 and cp >= mincyc"
assert src.count(a) == 1
src = src.replace(a, "        if (cad == 0 or s % cad == 0) and cp > 0 and cp >= mincyc")
fsim = types.ModuleType("fsim_r8"); fsim.__file__ = R6 + "fsim.py"; exec(compile(src, fsim.__file__, "exec"), fsim.__dict__)
import harness as H, h4
PLANS = {25: "lucid_pro_25k", 50: "lucid_pro_50k", 100: "lucid_pro_100k", 150: "lucid_pro_150k"}
GROWS = [0, 500, 1000, 1500, 2000, 3000]; CADS = [5, 10, 0]; HZ = 250; CAP = 0.35; MAXM = 9
REG = {25: dict(stop=75, N=1, nc=1), 50: dict(stop=75, N=1, nc=3, lock=80), 100: dict(stop=100, N=2, nc=2),
       150: dict(stop=100, N=2, nc=4, nb=((1500, 1),), cb=((1500, 1),))}
_cache = {}
def prep(k, c):
    key = (k, json.dumps(c, default=str, sort_keys=True))
    if key not in _cache:
        S = h4.sim(k, ds=0.38); cc = S.mk(**c); days, st = fsim.build_days(S, cc, True); _cache.clear(); _cache[key] = (S, cc, days)
    return _cache[key]
def cell(S, cc, days, k, cad):
    L = S.L; ix = range(0, L - HZ + 1); res = [fsim.life(S, k, days, i, cc, CAP, 0.38, HZ, False, cad) for i in ix]
    net = np.array([0.9 * sum(g for _, g in r["pays"]) for r in res]); npay = np.array([len(r["pays"]) for r in res])
    first = [r["pays"][0][0] for r in res if r["pays"]]
    return dict(year_mean=round(float(net.mean()), 2), year_median=round(float(np.median(net)), 2), year_p25=round(float(np.percentile(net, 25)), 2),
                year_p75=round(float(np.percentile(net, 75)), 2), week_mean=round(float(net.mean()) / (HZ / 5), 2),
                per_paycheck_mean=round(float(net.sum() / npay.sum()), 2) if npay.sum() else 0.0,
                any_payout_pct=round(100 * float((npay > 0).mean()), 1), max_payouts_pct=round(100 * float((npay >= 5).mean()), 1),
                bust_pct=round(100 * float(np.mean([r["status"] in ("BUST", "STUCK") for r in res])), 1),
                median_sessions_to_first=int(np.median(first)) if first else None, starts=len(res))
def job(a):
    k, mode, m, g = a
    if mode == "fixed": c = H.cfg(k, stop=100, N=m, nc=m, grow=(float(g), MAXM) if g else None, cgrow=(g, MAXM) if g else None)
    else: c = H.cfg(k, **(H.BUILT[k] if mode == "auto-high" else REG[k]))
    S, cc, days = prep(k, c)
    return a, {str(cad): cell(S, cc, days, k, cad) for cad in CADS}, c
if __name__ == "__main__":
    jobs = [(k, "fixed", m, g) for k in PLANS for m in range(1, MAXM + 1) for g in GROWS] + [(k, md, 0, 0) for k in PLANS for md in ("auto-high", "auto-regular")]
    jobs.sort(key=lambda a: (a[0], a[1], a[3], a[2]))
    if len(sys.argv) > 1: jobs = jobs[:int(sys.argv[1])]
    with mp.Pool(4) as p: out = p.map(job, jobs, chunksize=4)
    S0 = {k: h4.sim(k) for k in PLANS}
    data = dict(meta=dict(title="MAIN strategy = Fast Evaluation NOISE + CANDACE", status="UNVERIFIED research projection, not a promise",
        generator="docs/results/agent_review_2026-11-24/calculator_r8/make_calc.py", data="Databento MNQ 1-min RTH (/home/user/days.pkl)", horizon_sessions=HZ,
        payout_consistency_pct=int(CAP * 100), net_split=0.9, cost_per_micro_rt_usd=2, news="hard breach: flat 1 min before, no entry until 1 min after (VERIFY window)",
        setups="NOISE (profit lock +100 pt, stop moves to entry +10) + CANDACE ICT scalp, same trades on every account; micros = size of each strategy",
        fixed_stop_usd=100, max_micros=MAXM, grows=GROWS, cadences=CADS, caveat="Funded accounts are lost often: 20-43% lost within 120 days on 25K/50K/100K (funded_payout_r6/RESULTS.md); open-trade drawdown only through the stop, eval fees and resets not subtracted.",
        on_demand="Lucid help center (on_demand_payouts_r8/RESULTS.md) CONFIRMS LucidPro has no fixed payout window: a payout may be requested any day once eligible (min $500, min cycle profit, consistency 40%, buffer). Intraday timing, DLL-on requirement and trading pause after a request are third-party only, and the app's '3 profitable days' rule is not on the official page: all VERIFY. Modelled as a payout whenever eligible, same-evening, trading not blocked."), plans={})
    for k, n in PLANS.items():
        P = fsim.PAY[k]; data["plans"][n] = dict(account_size=k * 1000, max_possible_year=round(0.9 * (P[1] + 4 * P[2]), 2), cells={},
            auto={md: dict(setup=("fast-pass sizes + brakes (r6 candidate a)" if md == "auto-high" else "lowest brake step (r6 candidate b)"), cfg={x: (list(v) if isinstance(v, tuple) else v) for x, v in (H.BUILT[k] if md == "auto-high" else REG[k]).items()}) for md in ("high", "regular")} if False else {})
    for (k, mode, m, g), cads, c in out:
        n = PLANS[k]; cells = data["plans"][n]["cells"]
        key = (lambda cad: f"m{m}|g{g}|c{cad}") if mode == "fixed" else (lambda cad: f"{mode}|c{cad}")
        for cad, v in cads.items(): cells[key(cad)] = v
        if mode != "fixed": data["plans"][n].setdefault("auto", {})[mode[5:]] = dict(setup=("fast-pass sizes + brakes (r6 candidate a)" if mode == "auto-high" else "lowest brake step (r6 candidate b)"), stop_usd=c["stop"], noise=c["N"], candace=c["nc"], noise_brake=[[round(f * H.MLL[k]), q] for f, q in c["nbands"]], candace_brake=[[round(f * H.MLL[k]), q] for f, q in c["cbands"]], grow=list(c["grow"]) if c["grow"] else None)
    json.dump(data, open(sys.argv[2] if len(sys.argv) > 2 else "/home/user/paytience/config/income_calc.json", "w"), indent=1)
    print("cells", sum(len(v["cells"]) for v in data["plans"].values()))
