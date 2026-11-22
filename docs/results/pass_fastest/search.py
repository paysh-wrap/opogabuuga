"""Pass-fastest study (Pro 50K + Pro 150K EVALUATION), search driver. Research only: nothing in backend/app, config/ or frontend/ is touched.
Simulators (validated, see repro50.py / validate150.py): lib50.py (50K, = pass_faster/pf_sim + pass_faster_fixed/run_fixed) and sim150.py (150K).
Consistency scenarios: C40 = best day <= 40 % of profit to pass + day stop 38 % of target (shipped); C50 = 50 % option (D155) + day stop 48 %.
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/search.py   -> results.json
"""
import sys, os, json, time, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import multiprocessing as mp

CONS = {"C40": (40.0, 0.38), "C50": (50.0, 0.48)}
FLOOR = {50: 59.0, 150: 70.0}
STOPS = (100, 150, 200, 250)
NNS = {50: (1, 2, 3), 150: (3, 4, 5, 6)}
NCS = {50: (0, 1, 2), 150: (0, 1, 2, 3)}
BASE = {50: dict(stop=250, nn=2, nc=0, brake=1, taper=0), 150: dict(stop=250, nn=3, nc=0, brake=1, taper=0)}
ROWA = {50: dict(stop=100, nn=2, nc=1, brake=0, taper=0), 150: dict(stop=100, nn=4, nc=2, brake=0, taper=0)}


def half(n): return -(-n // 2)


def norm(g):
    """brake / taper to 'half size' are no-ops at 1 micro (half of 1 = 1)"""
    g = dict(g)
    if half(g["nn"]) >= g["nn"]: g["brake"] = 0; g["taper"] = 0
    return g


def gkey(k, g, cn): return f"{k}K|s{g['stop']}|n{g['nn']}|c{g['nc']}|b{g['brake']}|t{g['taper']}|{cn}"


def ev(job):
    k, g, cn = job
    cons, ds = CONS[cn]
    if k == 50:
        import lib50 as L
        p = dict(L.P, cons=cons, day_stop=ds * L.P["target"])
        h = half(g["nn"])
        c = L.cfg_of(stop=g["stop"], nn=g["nn"], nc=g["nc"], bb=0.5 if g["brake"] else 0.0, bc=h if g["brake"] else 1,
                     tb=0.25 if g["taper"] else 0.0, tc=h if g["taper"] else 1)
        days = L.table_for(c); r = {}
        for w in ("ALL", "PICK", "JUDGE"):
            o, n, _, _ = L.roll(days, c, w, p=p)
            s = L.summ(o, n); s["stuck"] = s["stuck"] + s["bust"]; r[w] = s
            if w == "ALL":
                ch = L.chain(o, n); r["chain"] = dict(mean=ch["ch_days"], med=ch["ch_med"], cens=ch["ch_cens"], att=ch["ch_att"])
        st = L.static(days, c, "ALL"); r["profit"] = st["profit"]; r["dd"] = st["dd"]; r["tpw"] = st["tpw"]
    else:
        import sim150 as S
        S.CONS = cons; S.DSTOP = ds * S.TARGET
        h = half(g["nn"])
        c = S.mk(stop=g["stop"], N=g["nn"], nc=g["nc"], brake=(0.5, h) if g["brake"] else None, taper=(0.25, h) if g["taper"] else None)
        e = S.evaluate(c); r = {}
        for w in ("ALL", "PICK", "JUDGE"):
            s = dict(e[w]); r[w] = s
        ch = e["ch"]; r["chain"] = dict(mean=ch["mean"], med=ch["med"], cens=ch["cens"], att=ch["att"])
        r["profit"] = e["static"]["profit"]; r["dd"] = e["static"]["dd"]; r["tpw"] = e["static"]["tpw"]
    keep = ("pass", "pass_", "stuck", "run", "p60", "med", "p75")
    for w in ("ALL", "PICK", "JUDGE"):
        s = r[w]; s["pass"] = s.get("pass", s.get("pass_")); r[w] = {x: s.get(x) for x in keep if x != "pass_"}
    return gkey(k, g, cn), dict(plan=k, cons=cn, g=g, **r)


def run(jobs, store):
    jobs = [j for j in jobs if gkey(*j) not in store]
    if not jobs: return
    with mp.Pool(4) as pool:
        for key, r in pool.imap_unordered(ev, jobs, chunksize=2): store[key] = r


def robust(r, base):
    return r["ALL"]["pass"] >= FLOOR[r["plan"]] and r["JUDGE"]["pass"] >= base["JUDGE"]["pass"] - 3 and r["PICK"]["pass"] >= base["PICK"]["pass"] - 5


def stage1(k):
    out = []
    for a in (BASE[k], ROWA[k]):
        out.append(a)
        for f, vals in (("stop", STOPS), ("nn", NNS[k]), ("nc", NCS[k]), ("brake", (0, 1)), ("taper", (0, 1))):
            for v in vals: out.append(dict(a, **{f: v}))
    return out


def factorial(k, fix=None):
    out = []
    for s, n, c, b, t in itertools.product(STOPS, NNS[k], NCS[k], (0, 1), (0, 1)):
        g = dict(stop=s, nn=n, nc=c, brake=b, taper=t)
        if fix and any(g[f] != v for f, v in fix.items()): continue
        out.append(g)
    return out


def uniq(gs):
    seen = {}; [seen.setdefault(json.dumps(norm(g), sort_keys=True), norm(g)) for g in gs]; return list(seen.values())


if __name__ == "__main__":
    t0 = time.time(); store = {}
    fn = HERE + "/results.json"
    if os.path.exists(fn): store = json.load(open(fn)).get("runs", {})
    plan_cfgs = {}
    for k in (50, 150):
        s1 = uniq(stage1(k))
        if k == 50:
            s2 = uniq(factorial(50))                                   # 108 distinct configs: the whole grid fits the budget
        else:                                                          # 150K: factorial over stop x micros x CANDACE x brake; taper only where stage 1 says it helps (see RESULTS.md)
            s2 = uniq(factorial(150, fix={"taper": 0}))
        plan_cfgs[k] = dict(stage1=s1, stage2=[g for g in s2 if g not in s1])
        jobs = [(k, g, cn) for g in s1 + plan_cfgs[k]["stage2"] for cn in CONS]
        run(jobs, store)
        print(k, "K configs", len(uniq(s1 + s2)), "runs", len(jobs), f"{time.time() - t0:.0f}s", flush=True)
    # 150K stage 3: taper ON on the 8 fastest ROBUST stage-2 configs per consistency
    s3 = []
    for cn in CONS:
        base = store[gkey(150, norm(BASE[150]), cn)]
        rs = sorted([r for r in store.values() if r["plan"] == 150 and r["cons"] == cn and not r["g"]["taper"] and robust(r, base)], key=lambda r: (-r["ALL"]["p60"], -r["ALL"]["pass"]))[:8]
        s3 += [norm(dict(r["g"], taper=1)) for r in rs]
    s3 = uniq(s3); plan_cfgs[150]["stage3"] = s3
    run([(150, g, cn) for g in s3 for cn in CONS], store)
    meta = dict(cons=CONS, floor=FLOOR, n_configs={k: len(uniq(sum(v.values(), []))) for k, v in plan_cfgs.items()}, secs=round(time.time() - t0))
    json.dump(dict(meta=meta, runs=store), open(fn, "w"), indent=0, default=float)
    print("done", meta)
