"""Pre-registered funded sizing study. Candidates per plan: a eval fast-pass sizes (eval day stop 38% of eval target), b lowest brake step (no grow),
c regular size_table profile (NOISE $250 stop, table N, CANDACE floor(MLL/1000)), d30/d33 = a with funded day stop 30%/33% of eval target (cycle-target proxy).
Scenarios: base (payout cap 35%, news filter, $2/micro), cap40, cost (+$2/micro RT both legs), nonews. Horizons 60/120 sessions (rolling start on every day).
ADOPT rule (fixed before running): beats every other candidate on pick AND judge expected net payout $ at 120 d, breach % not higher on pick and judge, and still best in the +$2 and cap40 scenarios."""
import sys, json, multiprocessing as mp
import fsim, harness as H
B = H.BUILT
def cfgs(k):
    m = H.MLL[k]
    a = dict(B[k]); out = {"a": a}
    if k == 25: out["b"] = dict(stop=75, N=1, nc=1); out["c"] = dict(stop=250, N=1, nc=1)
    if k == 50: out["b"] = dict(stop=75, N=1, nc=3, lock=80); out["c"] = dict(stop=250, N=2, nc=2, nb=((1000, 1),))
    if k == 100: out["b"] = dict(stop=100, N=2, nc=2); out["c"] = dict(stop=250, N=2, nc=3, nb=((900, 1),))
    if k == 150:
        out["b"] = dict(stop=100, N=1, nc=1); out["b2"] = dict(stop=100, N=2, nc=4, nb=((1500, 1),), cb=((1500, 1),))
        out["c"] = dict(stop=250, N=3, nc=4, nb=((2250, 2),))
    out["d30"] = dict(a); out["d33"] = dict(a)
    return out
DS = {"a": .38, "b": .38, "b2": .38, "c": .38, "d30": .30, "d33": .33}
SCEN = {"base": dict(cap=.35, news=True, cost=False), "cap40": dict(cap=.40, news=True, cost=False), "cost": dict(cap=.35, news=True, cost=True), "nonews": dict(cap=.35, news=False, cost=False)}
def job(args):
    k, cand, scen = args
    c = H.cfg(k, **cfgs(k)[cand]); S, res, st = fsim.run(k, c, ds_frac=DS[cand], **SCEN[scen])
    r = fsim.summarize(S, res); r["news"] = st
    r["status"] = {s: sum(1 for x in res if x["status"] == s) for s in ("OPEN", "BUST", "STUCK", "MAXPAY")}
    r["maxday"] = max(x["maxday"] for x in res); r["big6k"] = sum(x["big6k"] for x in res)
    return (k, cand, scen), r
if __name__ == "__main__":
    jobs = [(k, cand, s) for k in (25, 50, 100, 150) for cand in cfgs(k) for s in SCEN]
    print(len(jobs), flush=True)
    with mp.Pool(4) as p: out = dict(p.map(job, jobs, chunksize=1))
    json.dump({"|".join(map(str, k)): v for k, v in out.items()}, open("results6.json", "w"), indent=1)
