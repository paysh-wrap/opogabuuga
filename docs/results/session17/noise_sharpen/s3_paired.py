"""Paired block-bootstrap of the Pro 25K evaluation outcome difference (variant minus its base) over HELD-OUT days.
Each resample draws 10-session blocks of the held-out days (same draw for variant and base), builds a history of the same length (~720 sessions), and
runs the same rolling-start eval simulation (every 2nd start, 120-session horizon, 'seq' breach rule). 400 resamples. This is the honest sampling
uncertainty of 'PASS % / BUST %' that the single rolling-start number hides (the ~330 overlapping starts are really ~6 independent windows).
usage: python -I s3_paired.py   -> paired.json"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from multiprocessing import Pool
import numpy as np, pandas as pd
import sim

S = json.load(open(HERE + "/study.json"))["variants"]; S2 = json.load(open(HERE + "/stage2.json")); LH = json.load(open(HERE + "/lhh.json"))
ALL = dict(S); ALL.update(S2["combos"])
N_RES, BLOCK = 400, 10


def stream(fn): return pd.read_csv(f"{HERE}/streams/{fn}.csv", dtype={"d": str})


def stats(tab):
    res = [sim.eval_run(tab[s0:], 120, False) for s0 in range(0, len(tab) - 40, 2)]
    n = len(res); return 100 * sum(o == "PASS" for o, _ in res) / n, 100 * sum(o == "BUST" for o, _ in res) / n


def job(a):
    name, f_var, f_base = a
    tv = sim.day_table(stream(f_var), "HO")[1]; tb = sim.day_table(stream(f_base), "HO")[1]
    L = len(tv); rnd = np.random.default_rng(11); nb = int(np.ceil(L / BLOCK)); dp = []; db = []; pv = []; bv = []
    for _ in range(N_RES):
        st = rnd.integers(0, L - BLOCK + 1, nb); idx = np.concatenate([np.arange(s, s + BLOCK) for s in st])[:L]
        a_p, a_b = stats([tv[i] for i in idx]); b_p, b_b = stats([tb[i] for i in idx])
        dp.append(a_p - b_p); db.append(a_b - b_b); pv.append(a_p); bv.append(b_p)
    dp, db = np.array(dp), np.array(db)
    return name, dict(dpass=float(dp.mean()), dpass_lo=float(np.percentile(dp, 2.5)), dpass_hi=float(np.percentile(dp, 97.5)), p_pass_better=float((dp > 0).mean()),
                      dbust=float(db.mean()), dbust_lo=float(np.percentile(db, 2.5)), dbust_hi=float(np.percentile(db, 97.5)), p_bust_lower=float((db < 0).mean()),
                      pass_var=float(np.mean(pv)), pass_base=float(np.mean(bv)))


if __name__ == "__main__":
    cands = ["BASE [lock]", "N11 skip Monday [lock]", "VWAP side filter [lock]", "no entry 11:00 [lock]", "N10 skip low-vol tercile [lock]", "N10+N11 [lock]",
             "min sigma >= IS p10 (0.24%) [lock]", "min sigma >= IS p20 (0.29%) [lock]", "min sigma >= IS p30 (0.33%) [lock]", "min band width >= IS p30 (126 pt) [lock]",
             "min band width >= IS p40 (149 pt) [lock]", "no flip after any exit [lock]", "extra check 15:30 (band entry) [lock]", "N11 skip Monday [nolock]",
             "VWAP side filter [nolock]", "no flip after any exit [nolock]", "min sigma >= IS p20 (0.29%) [nolock]", "extra check 15:30 (band entry) [nolock]",
             "lock 200->+10", "lock 200->+50", "lock 75->+50", "lock 75->+10", "trail-lock +100 give back 100", "lock 100->+10", "session-9 original (1% stop) [nolock]"] + list(S2["combos"])
    base = lambda n: "BASE [lock]" if n.endswith("[lock]") or n.startswith("COMBO") else "BASE [nolock]"
    jobs = [(n, ALL[n]["file"], ALL[base(n)]["file"]) for n in cands if n != "BASE [lock]"]
    jobs.append(("BASE [lock] vs BASE [nolock]", ALL["BASE [lock]"]["file"], ALL["BASE [nolock]"]["file"]))
    # LHH add-ons (pick) vs NOISE alone
    for l in ("nolock", "lock"):
        pk = LH["pick"]; fn = "LHH_" + l + "_" + "".join(ch if ch.isalnum() else "_" for ch in pk)
        jobs.append((f"NOISE[{l}] + LHH pick ({pk})", fn, ALL[f"BASE [{l}]"]["file"]))
    with Pool(4) as p: res = dict(p.map(job, jobs, chunksize=1))
    json.dump(res, open(HERE + "/paired.json", "w"), indent=1)
    for n, r in res.items(): print(f"{n[:70]:70s} dPASS {r['dpass']:+5.1f} [{r['dpass_lo']:+5.1f},{r['dpass_hi']:+5.1f}] P>0 {r['p_pass_better']:.2f} | dBUST {r['dbust']:+5.1f} [{r['dbust_lo']:+5.1f},{r['dbust_hi']:+5.1f}] P<0 {r['p_bust_lower']:.2f}")
