"""Step 1 (NOISE-alone causal baseline per Pro plan) + step 2 (sizing / brake / kill-distance / profit-lock search for funded year-1 bust < 30% and eval bust < 30%).
usage: S15_RAW=<folder with mnq_5y.csv> python3 run_step12.py [base|grid]   (outputs in out/)"""
import sys, json, itertools, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
import lib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BASE = {"25K": dict(q=1), "50K": dict(q=2, brake=(0.5, 1)), "100K": dict(q=2, brake=(0.3, 1)), "150K": dict(q=3, brake=(0.5, 2))}
EVALB = {"25K": dict(q=1), "50K": dict(q=2, brake=(0.5, 1)), "100K": dict(q=2, brake=(0.3, 1)), "150K": dict(q=4, brake=(0.5, 2))}
QS = {"25K": [1], "50K": [1, 2], "100K": [1, 2, 3], "150K": [1, 2, 3, 4]}
_T = {}


def tab(stop, lock):
    k = (stop, lock)
    if k not in _T:
        t = lib.noise_stream("MNQ", stop_usd=stop, lock=(100, 10) if lock else None)
        _T[k] = lib.day_table(t)
    return _T[k]


def both(plan, stop, lock, cfg):
    R = lib.plan_rules(plan); T = tab(stop, lock)
    out = {}
    for era in ("IS", "HO", "ALL"):
        out["f_" + era] = lib.funded_stats(T, R, cfg, era)
        out["e_" + era] = lib.eval_stats(T, R, cfg, era)
    return out


def job(a):
    plan, stop, lock, cfg = a
    return dict(plan=plan, stop=stop, lock=lock, cfg={k: v for k, v in cfg.items()}, **both(plan, stop, lock, cfg))


def grid(plan):
    mll = lib.plan_rules(plan).f.mll
    for q, stop, lock, br, fit, kill, dl in itertools.product(QS[plan], (150, 200, 250), (False, True), (None, (0.5, 1), (0.7, 1)), (None, 0.5, 0.35),
                                                           (None, 100, 200), (None, 0.15 * mll, 0.3 * mll)):
        if q == 1 and br: continue
        cfg = dict(q=q)
        if br: cfg["brake"] = br
        if fit: cfg["fit"] = fit
        if kill: cfg["kill"] = kill
        if dl: cfg["dlock"] = dl
        yield (plan, stop, lock, cfg)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "base":
        rows = []
        t = lib.noise_stream("MNQ")
        st = {e: lib.stream_stats(t, e) for e in ("IS", "HO", "ALL")}
        for plan in BASE:
            R = lib.plan_rules(plan); T = tab(250, False)
            fb, eb = BASE[plan], EVALB[plan]
            r = dict(plan=plan, funded_cfg=fb, eval_cfg=eb)
            for era in ("IS", "HO", "ALL"):
                r["f_" + era] = lib.funded_stats(T, R, fb, era); r["e_" + era] = lib.eval_stats(T, R, eb, era)
            rows.append(r)
        json.dump(dict(stream=st, rows=rows), open(f"{OUT}/base.json", "w"), indent=1, default=float)
        print(json.dumps(st, indent=1))
        for r in rows:
            print(r["plan"], {k: (round(v["bust"], 1), round(v["per2w"], 1)) for k, v in r.items() if k.startswith("f_")},
                  {k: (round(v["pass_"], 1), round(v["bust"], 1)) for k, v in r.items() if k.startswith("e_")})
    else:
        for plan in QS:
            jobs = list(grid(plan))
            print(plan, len(jobs), flush=True)
            with Pool(4) as p:
                res = p.map(job, jobs, chunksize=8)
            json.dump(res, open(f"{OUT}/grid_{plan}.json", "w"), default=float)
