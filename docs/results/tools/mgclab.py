"""Offline Lab run on MGC (Intraday, Pro 25K) using the app's own Lab functions + backtest engine."""
import json, logging, sys
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal as D
from pathlib import Path
logging.disable(logging.CRITICAL)
PLAN = Path("/home/user/paytience/config/rules/lucid_pro_25k.yaml")
CSV = Path("/home/user/paytience/data/futures/mgc_yahoo_1m.csv")
OUT = Path(sys.argv[1])

def job(args):
    logging.disable(logging.CRITICAL)
    name, path, part = args
    from app.backtest.data import load_csv
    from app.backtest.runner import BacktestConfig, run_backtest
    from app.lab.cycle import split_sessions
    bars = load_csv(CSV.read_text())
    tr, te = split_sessions(bars)
    b = tr if part == "train" else te
    t = run_backtest(b, BacktestConfig(symbol="MGC", bias="NEUTRAL"), Path(path)).trades
    return name, part, t

if __name__ == "__main__":
    from app.config import load_rules, load_yaml_decimal
    from app.lab.challenger import Candidate, best_on_train, passes_oos, perf, explain
    from app.lab.cycle import write_rules
    from app.lab.tunables import current_values, neighbours
    lr = load_rules(PLAN); cfg = lr.rules; raw = load_yaml_decimal(lr.source_text)
    cur = current_values(cfg); nb = neighbours(cur, cfg.self_improvement.max_param_step_pct)
    paths = {"champ": write_rules(raw, {}, OUT, "champ")}
    from app.lab.cycle import valid_rules_file
    nb = [d for d in nb if valid_rules_file(write_rules(raw, d, OUT, "probe"))]
    print("CANDIDATES", len(nb), [{k: str(v) for k, v in d.items()} for d in nb], flush=True)
    for i, d in enumerate(nb): paths[f"c{i}"] = write_rules(raw, d, OUT, f"c{i}")
    jobs = [("champ", str(paths["champ"]), "train"), ("champ", str(paths["champ"]), "test")] + [(f"c{i}", str(paths[f"c{i}"]), "train") for i in range(len(nb))]
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for name, part, t in ex.map(job, jobs):
            res[(name, part)] = perf(t); p = res[(name, part)]
            print(name, part, p.trades, f"{p.win_rate:.2f}", f"{p.e:.3f}", flush=True)
    champ_tr, champ_te = res[("champ", "train")], res[("champ", "test")]
    cands = [Candidate(nb[i], res[(f"c{i}", "train")]) for i in range(len(nb))]
    best = best_on_train(champ_tr, cands)
    print("BEST_TRAIN", best.diff if best else None, flush=True)
    if best:
        i = nb.index(best.diff)
        _, _, t = job((f"c{i}", str(paths[f"c{i}"]), "test"))
        best = Candidate(best.diff, best.train, perf(t))
        ok, why = passes_oos(champ_te, best, cfg.self_improvement.min_improvement_r, 1)
        print("OOS", ok, why, explain(best.diff, champ_tr, best, champ_te), flush=True)
    print("CURRENT", {k: str(v) for k, v in cur.items()})
