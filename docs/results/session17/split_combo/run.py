"""Runs the whole study. usage: python3 run.py <cache dir> [seeds=20] [scenario names comma list]  -> results_<scenario>.json (this folder)
Scenarios: main = Duo on MNQ+MGC (as built), hedge lock;  mnq = Duo on MNQ only;  strict = main with 'max 1 open position per account' (any overlap skipped).
Sizing: APP (config size_table) is primary; S15 = session-15 recommended sizes (main scenario only)."""
import sys, os, pickle, json, time, random
import numpy as np
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from multiprocessing import Pool
import sim

CD = sys.argv[1]; SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
ACCS = [0.50, 0.55, 0.60, 0.65, 0.70]; ACCTS = ["25K", "50K", "100K", "150K"]
NT = pickle.load(open(f"{CD}/noise_mnq.pkl", "rb")); DUO = pickle.load(open(f"{CD}/duo.pkl", "rb"))
DATES = sim.bdays(DUO["MNQ"]["dates"][0], DUO["MNQ"]["dates"][-1])
NTAB = sim.noise_tab(NT, DATES)
I_SPLIT = next(i for i, d in enumerate(DATES) if d > sim.SPLIT)
ERA = {"IS": (0, I_SPLIT), "HO": (I_SPLIT, len(DATES))}
SCEN = {"main": dict(markets=tuple(m for m in ("MNQ", "MGC") if m in DUO), mode="hedge", sizing="APP"),
        "mnq": dict(markets=("MNQ",), mode="hedge", sizing="APP"),
        "strict": dict(markets=tuple(m for m in ("MNQ", "MGC") if m in DUO), mode="strict1", sizing="APP"),
        "mnq_strict": dict(markets=("MNQ",), mode="strict1", sizing="APP"),
        "mnq_s15": dict(markets=("MNQ",), mode="hedge", sizing="S15"),
        "main_s15": dict(markets=tuple(m for m in ("MNQ", "MGC") if m in DUO), mode="hedge", sizing="S15")}
NPATH, BLOCK, CAP = 600, 10, 750


def boot_idx(era, seed=7):
    lo, hi = ERA[era]; rnd = random.Random(seed); out = []
    for _ in range(NPATH):
        p = []
        while len(p) < CAP:
            i = lo + rnd.randrange(hi - lo); p.extend(range(i, min(i + BLOCK, hi)))
        out.append(p[:CAP])
    return out
BOOT = {e: boot_idx(e) for e in ERA}


def evals(tab, R, qf, budgets, mode):
    o = {}
    for era in ERA:
        o[era] = dict(roll=sim.eval_stats(tab, DATES, R, qf, budgets, mode, era, horizon=250, step=2))
        res = [sim.eval_run([tab[i] for i in p], R, qf, budgets, mode, CAP) for p in BOOT[era]]
        ps = [s for r, s in res if r == "PASS"]; n = len(res)
        o[era]["boot"] = dict(n=n, pas=100 * sum(r == "PASS" for r, _ in res) / n, bust=100 * sum(r == "BUST" for r, _ in res) / n,
                              open=100 * sum(r == "OPEN" for r, _ in res) / n, med_days=float(np.median(ps)) if ps else float("nan"))
        o[era]["stream"] = sim.stream_stats(tab, DATES, R, qf, budgets, mode, era)
    return o


def cell(a):
    scen, acct, seed = a
    sc = SCEN[scen]; R = sim.plan_rules(acct); B = R.budget
    qs = sim.make_qfun(sim.SIZES[sc["sizing"]], acct, R.e.mll, True)
    out = {}
    for acc in ACCS:
        tab = sim.combine(NTAB, sim.ai_calls(DUO, DATES, seed, acc, markets=sc["markets"]))
        out[acc] = evals(tab, R, qs, (B / 2, B / 2), sc["mode"])
    return (scen, acct, seed), out


def base(a):
    sizing, acct = a
    R = sim.plan_rules(acct); B = R.budget
    full = sim.make_qfun(sim.SIZES[sizing], acct, R.e.mll, False); half = sim.make_qfun(sim.SIZES[sizing], acct, R.e.mll, True)
    return (sizing, acct), dict(noise_full=evals(NTAB, R, full, (B, None), "hedge"), noise_half=evals(NTAB, R, half, (B / 2, None), "hedge"))


def agg(vals):
    v = np.array([x for x in vals if x == x], float)
    return dict(mean=float(v.mean()), min=float(v.min()), max=float(v.max()), sd=float(v.std()), vals=[round(float(x), 2) for x in v]) if len(v) else dict(mean=float("nan"), min=float("nan"), max=float("nan"), sd=float("nan"), vals=[])


def flat(d, pre=""):
    for k, v in d.items():
        if isinstance(v, dict): yield from flat(v, f"{pre}{k}.")
        else: yield f"{pre}{k}", v


if __name__ == "__main__":
    t0 = time.time()
    names = sys.argv[3].split(",") if len(sys.argv) > 3 else list(SCEN)
    with Pool(4) as p:
        b = dict(p.map(base, [(s, a) for s in ("APP", "S15") for a in ACCTS]))
        json.dump({f"{k[0]}|{k[1]}": v for k, v in b.items()}, open(f"{HERE}/results_baselines.json", "w"), indent=1, default=float)
        print("baselines", round(time.time() - t0), "s", flush=True)
        for scen in names:
            res = dict(p.map(cell, [(scen, a, s) for a in ACCTS for s in range(SEEDS)], chunksize=1))
            out = {}
            for acct in ACCTS:
                out[acct] = {}
                for acc in ACCS:
                    seeds = [dict(flat(res[(scen, acct, s)][acc])) for s in range(SEEDS)]
                    out[acct][str(acc)] = {k: agg([x[k] for x in seeds]) for k in seeds[0]}
            json.dump(dict(scenario=scen, cfg={k: list(v) if isinstance(v, tuple) else v for k, v in SCEN[scen].items()}, seeds=SEEDS, res=out), open(f"{HERE}/results_{scen}.json", "w"), indent=1, default=float)
            print(scen, "done", round(time.time() - t0), "s", flush=True)
