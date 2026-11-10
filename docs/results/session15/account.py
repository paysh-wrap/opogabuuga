"""Session 15 account tests: run a 1-micro trade stream through each Lucid Pro plan (lib.eval_run / lib.funded_run = the same rules as
backend/app/backtest/income_projection.py eval_path / funded_path, plus an intraday breach check on each trade's worst open loss).
Two estimates per era (IS = pick, HO = judge):
  hist  = every-2nd-session rolling starts inside the era (eval: 250-session horizon -> PASS / BUST / still OPEN; funded: first 260 sessions)
  boot  = block bootstrap of the era's days (blocks of 10 sessions, 600 paths): evals run to the end (max 750 sessions), funded = first 260 sessions.
"FAIL" always means the account is dead (balance touched the loss limit).  No kill-distance / freeze rule is used: a freeze is a dead account too."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import lib

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def load(key):
    return pd.read_csv(f"{OUT}/streams/{key}.csv", dtype={"d": str})


def merge(*streams):
    """several 1-micro streams -> one stream obeying 'one open position per account' (a trade whose entry falls while an earlier one is open is dropped)."""
    t = pd.concat(streams).sort_values(["d", "ek"]).reset_index(drop=True)
    keep = []; last_d = None; busy = -1
    for r in t.itertuples():
        if r.d != last_d: last_d, busy = r.d, -1
        if r.ek <= busy: keep.append(False); continue
        keep.append(True); busy = r.xk
    return t[keep].reset_index(drop=True)


def era_days(tab, era):
    if era == "IS": return [t for d, t in tab if d <= lib.SPLIT]
    if era == "HO": return [t for d, t in tab if d > lib.SPLIT]
    return [t for _, t in tab]


def boot_paths(days_, n_paths, length, block=10, seed=7):
    rnd = random.Random(seed); n = len(days_); out = []
    for _ in range(n_paths):
        p = []
        while len(p) < length:
            i = rnd.randrange(n)
            p.extend(days_[i:i + block])
        out.append(p[:length])
    return out


def eval_boot(tab, R, cfg, era, n_paths=1000, cap=750):
    res = [lib.eval_run(p, R, cfg, cap) for p in boot_paths(era_days(tab, era), n_paths, cap)]
    ps = [s for o, s in res if o == "PASS"]
    return dict(pass_=100 * sum(o == "PASS" for o, _ in res) / len(res), bust=100 * sum(o == "BUST" for o, _ in res) / len(res),
                open_=100 * sum(o == "OPEN" for o, _ in res) / len(res), med=float(np.median(ps)) if ps else float("nan"),
                p80=float(np.percentile(ps, 80)) if ps else float("nan"))


def funded_boot(tab, R, cfg, era, n_paths=1000, horizon=260, cadence=10):
    res = [lib.funded_run(p, R, cfg, cadence) for p in boot_paths(era_days(tab, era), n_paths, horizon, seed=11)]
    paid = [x["paid"] for x in res]
    return dict(bust=100 * sum(x["status"] == "BUST" for x in res) / len(res), any_pay=100 * sum(x["npay"] > 0 for x in res) / len(res),
                per2w=float(np.mean(paid)) / (horizon / 10), year=float(np.mean(paid)), year_median=float(np.median(paid)),
                maxed=100 * sum(x["status"] == "MAX" for x in res) / len(res))


def full(tab, R, ecfg, fcfg, eras=("IS", "HO")):
    o = {}
    for era in eras:
        o[era] = dict(eh=lib.eval_stats(tab, R, ecfg, era, horizon=250), eb=eval_boot(tab, R, ecfg, era),
                      fh=lib.funded_stats(tab, R, fcfg, era), fb=funded_boot(tab, R, fcfg, era))
    return o


def edge(t, era):
    """per-trade mean, sd and the drift ratio 2*mean/sd^2 (per $; higher = an account survives more easily at a given size)."""
    x = t[t.d <= lib.SPLIT] if era == "IS" else t[t.d > lib.SPLIT]
    m, s = x.pnl.mean(), x.pnl.std()
    return dict(mean=float(m), sd=float(s), ratio=float(2 * m / s ** 2 * 1000) if s > 0 else 0.0)
