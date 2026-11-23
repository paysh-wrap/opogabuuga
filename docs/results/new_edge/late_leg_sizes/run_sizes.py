"""late_leg_sizes: late-day momentum leg (lastmom239) as 3rd leg on the BUILT D163 fast-pass rows, sizes 1-4 micros + cushion-brake variants (research only).
Run from backend/: PYTHONPATH=. /usr/local/bin/python3 ../docs/results/new_edge/late_leg_sizes/run_sizes.py [k ...]
Same sim as pass_fastest/final_search (one account, one position, DLL, EOD MLL + lock, C40 day stop 38 %, kill switch); leg trades from new_edge/scripts/trades_lastmom239.csv."""
import sys, os, json, types, time
import pandas as pd
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
PF = "/home/user/opogabuuga/docs/results/pass_fastest"
sys.path.insert(0, PF + "/within60"); sys.path.insert(0, PF + "/brake150"); sys.path.insert(0, PF + "/final_search")
import final as FN
import brake150 as B
VARIANT = os.environ.get("LATE_VARIANT", "study")      # study = exit 16:00 close, no target; app = exit 15:59 + 3R target (what the app trades)
TR = pd.read_csv(HERE + ("/../scripts/trades_lastmom239.csv" if VARIANT == "study" else "/trades_app.csv"))
TR["ptsB"] = TR.pts


def load_sim():
    src = open(PF + "/sim150.py").read()
    reps = [
        ('fade=False, nc=0, cwin=1000, ng=0,', 'fade=False, nc=0, cwin=1000, ng=0, nbands=(), cbands=(), cgrow=None, dlall=False, ndow=(), cdow=(), gbands=(),'),
        ('                if bb is not None and cush / MLL < bb: q = min(q, bc)\n',
         '                if bb is not None and cush / MLL < bb: q = min(q, bc)\n'
         '                for fb_, fn_ in c["nbands"]:\n'
         '                    if cush / MLL < fb_: q = min(q, fn_)\n'),
        ('                q = nc if kind == KC else ng\n',
         '                q = nc if kind == KC else ng\n'
         '                if kind == KC and c["cgrow"]:\n'
         '                    ex_ = int((bal - floor) // c["cgrow"][0]) - 1\n'
         '                    if ex_ > 0: q = min(c["cgrow"][1], nc + ex_)\n'
         '                if kind == KC:\n'
         '                    for fb_, fn_ in c["cbands"]:\n'
         '                        if (bal - floor) / MLL < fb_: q = min(q, fn_)\n'
         '                if kind == KG:\n'
         '                    for fb_, fn_ in c["gbands"]:\n'
         '                        if (bal - floor) / MLL < fb_: q = min(q, fn_)\n'),
        ('                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0\n',
         '                if kind == KC and DOWL[di] in c["cdow"]: continue\n'
         '                if c["dlall"] and (lockday or (dlk and today > 0 and rem0 > 0 and today >= dlk * rem0)):\n'
         '                    if not lockday: lockday = True; dlkd += 1\n'
         '                    continue\n'
         '                per = b * 2.0 + 2.0 if kind == KC else b * 2.0 + 2.0\n'),
        ('            if kind <= KF:                                           # NOISE / fade: size table + checks\n',
         '            if kind <= KF and DOWL[di] in c["ndow"]: continue\n'
         '            if kind <= KF:                                           # NOISE / fade: size table + checks\n'),
    ]
    for a, b in reps:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    m = types.ModuleType("simlate"); m.__file__ = PF + "/sim150.py"
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    m.DOWL = [m.DOW[d] for d in m.DATES]
    g = TR
    m.gala_df = lambda: g[(g.day >= m.WIN["ALL"][0]) & (g.day <= m.WIN["ALL"][1])]
    return m


B.load_sim = load_sim
import lib as L
MLL = FN.MLL
BUILT = {k: dict(v) for k, v in FN.BUILT.items()}
BUILT[150]["cgrow"] = (1500., 6)          # D163
BUILT[50]["dlock"] = 0.4                  # D163
BRK = {25: 333, 50: 667, 100: 1000, 150: 2250}    # plan's first NOISE brake (25K: CANDACE brake) in $ cushion


def job_list():
    jobs = []
    for k in (25, 50, 100, 150):
        b = BUILT[k]
        jobs.append((k, "base", 0, b, ()))
        for n in (1, 2, 3, 4):
            jobs.append((k, f"flat{n}", n, b, ()))
            if n > 1:
                jobs.append((k, f"brake{n}", n, b, ((BRK[k], 1),)))
                jobs.append((k, f"brakeH{n}", n, b, ((MLL[k] * 0.5, 1),)))
    return jobs


def ev(job):
    k, name, ng, b, gb = job
    p = {x: v for x, v in b.items() if x not in ("cgrow",)}
    kw = dict(p); kw["cgrow"] = b.get("cgrow")
    if ng: kw["ng"] = ng
    kw["gbands"] = tuple((d / MLL[k], m) for d, m in gb)
    S = L.sim(k, True); c = FN.cfg(k, **{x: v for x, v in kw.items() if x not in ("cgrow", "gbands", "ng")}, cgrow=kw["cgrow"], gbands=kw["gbands"], **({"ng": ng} if ng else {}))
    e = S.evaluate(S.mk(**c))
    r = {w: {x: e[w][x] for x in ("pass", "stuck", "run", "p60", "med")} for w in ("ALL", "PICK", "JUDGE")}
    r["chain"] = {x: e["ch"][x] for x in ("mean", "med", "cens")}; r["profit"] = e["static"]["profit"]
    return f"{k}|{name}", r


if __name__ == "__main__":
    ks = [int(x) for x in sys.argv[1:]] or [25, 50, 100, 150]
    jobs = [j for j in job_list() if j[0] in ks]
    FNJ = HERE + ("/results_study.json" if VARIANT == "study" else "/results_app.json")
    store = json.load(open(FNJ)) if os.path.exists(FNJ) else {}
    jobs = [j for j in jobs if f"{j[0]}|{j[1]}" not in store]
    t0 = time.time(); print(len(jobs), "jobs", flush=True)
    with mp.Pool(4) as pool:
        for key, r in pool.imap_unordered(ev, jobs):
            store[key] = r
            print(key, "ALL %.1f med %s | pick %.1f judge %.1f | profit %.0f" % (r["ALL"]["pass"], r["ALL"]["med"], r["PICK"]["pass"], r["JUDGE"]["pass"], r["profit"]), round(time.time() - t0), "s", flush=True)
            json.dump(store, open(FNJ, "w"), indent=1, default=float)
