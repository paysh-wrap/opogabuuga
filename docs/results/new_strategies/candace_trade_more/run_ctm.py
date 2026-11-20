"""CANDACE ICT SCALP: why so few trades, what adds trades (MEASURE + REPORT only; no app code is changed).
Run: cd backend && NS_CACHE=<own scratch>/days_vwap.json PYTHONPATH=. ../../.venv/bin/python \
        ../docs/results/new_strategies/candace_trade_more/run_ctm.py <days.pkl> [outdir]
Protocol: pick on IS 2021-10-01..2023-12-31, judge on J 2024-01-01..2026-10-30. Writes tables.md and days.csv.
"""
import sys, os, csv, json, pickle, time
from collections import Counter, defaultdict
import multiprocessing as mp

HERE = os.path.dirname(os.path.abspath(__file__))
PKL = next(a for a in sys.argv[1:] if a.endswith(".pkl"))
OUT = next((a for a in sys.argv[1:] if os.path.isdir(a)), HERE)
sys.argv = [sys.argv[0], PKL]
sys.path.insert(0, HERE)
import ctm_lib as L
from ctm_lib import Variant, BASEV

PLANK = (25, 50, 100, 150)
BASE_CFG = L.CandaceIctCfg().model_dump()


def cfg_with(**kw):
    d = dict(BASE_CFG)
    d.update(kw)
    L.CandaceIctCfg(**d)  # validate (raises if outside the validators)
    return d


# ---------------------------------------------------------------- candidate rows
ROWS = []


def add(id_, label, kind, over=None, flags=(False, False, False), var=None, gap=""):
    ROWS.append(dict(id=id_, label=label, kind=kind, over=over or {}, flags=flags, var=var or BASEV, gap=gap))


add("BASE", "baseline (engine defaults)", "base")
for e in ("10:30", "11:00", "11:30"):
    add(f"W{e.replace(':', '')}", f"ny_window 09:00-{e}", "setting", dict(ny_window=f"09:00-{e}"), gap="B4 [GAP]")
add("DM125", "displacement_mult 1.25", "setting", dict(displacement_mult=L.D("1.25")), gap="C5 [GAP]")
add("DM100", "displacement_mult 1.0", "setting", dict(displacement_mult=L.D("1.0")), gap="C5 [GAP]")
add("DB5", "displacement_bars 5", "setting", dict(displacement_bars=5), gap="C5 [GAP]")
add("DB20", "displacement_bars 20", "setting", dict(displacement_bars=20), gap="C5 [GAP]")
add("FL20", "fvg_lookback 20", "setting", dict(fvg_lookback=20), gap="C1 [GAP]")
add("IM20", "ifvg_max_bars 20", "setting", dict(ifvg_max_bars=20), gap="C3 [GAP]")
add("EQ4", "eq_tol_ticks 4", "setting", dict(eq_tol_ticks=4), gap="A3 [GAP]")
add("SW1", "swing_lookback 1", "setting", dict(swing_lookback=1), gap="A3 [GAP]")
add("SW3", "swing_lookback 3", "setting", dict(swing_lookback=3), gap="A3 [GAP]")
add("RB120", "range_bars 120", "setting", dict(range_bars=120), gap="A2 [GAP]")
add("PP40", "premium_pct 0.40 (shorts looser, longs tighter)", "setting", dict(premium_pct=L.D("0.4")), gap="A2 [GAP]")
add("PP60", "premium_pct 0.60 (longs looser, shorts tighter)", "setting", dict(premium_pct=L.D("0.6")), gap="A2 [GAP]")
add("SB1", "stop_buffer_ticks 1", "setting", dict(stop_buffer_ticks=1), gap="D1 [GAP]")
add("GFLOOR", "sizing: grade floor (C/B get >= 1 micro if fit >= 1)", "sizing", var=Variant("floor", floor=True), gap="E3 [GAP]")
add("GLOW", "sizing: grade_b_min 2 / grade_a_min 3", "sizing", var=Variant("low", a_min=3, b_min=2), gap="E3 [GAP]")
add("D4", "D4 partial at first internal liquidity (offline)", "mgmt", flags=(True, False, False), gap="D4 transcript, not built")
add("D5", "D5 break-even at 25% of the move (offline)", "mgmt", flags=(False, True, False), gap="D5 transcript, not built")
add("D45", "D4 + D5 (offline)", "mgmt", flags=(True, True, False), gap="D4/D5 transcript, not built")
add("C4", "C4 aggressive entry inside the FVG (offline)", "mgmt", flags=(False, False, True), gap="C4 transcript 'experienced only'")


# ---------------------------------------------------------------- evaluation of one row
class Ctx:
    pass


X = Ctx()


def trades_for(row, pool):
    cfgd = cfg_with(**row["over"])
    flags = row["flags"]
    key = json.dumps([sorted((k, str(v)) for k, v in row["over"].items()), flags], sort_keys=True)
    if key in X.cache:
        return X.cache[key]
    if any(flags):
        res = L.run_all(cfgd, flags, "mirror", pool)
        tr = {ds: t for ds, t, _ in res}
        info = res
    else:
        eng = L.run_all(cfgd, flags, "engine", pool)
        mir = L.run_all(cfgd, flags, "mirror", pool)
        bad = [d1 for (d1, a, _), (d2, b, _) in zip(eng, mir) if not L.same(a, b)]
        X.mismatch[row["id"]] = len(bad)
        tr = {ds: t for ds, t, _ in eng}
        info = mir
    out = (tr, info)
    X.cache[key] = out
    return out


def period(trs, lo, hi):
    return [t for ds in sorted(trs) if lo <= ds <= hi for t in trs[ds]]


def evaluate(row, pool):
    tr, _ = trades_for(row, pool)
    var = row["var"]
    out = {}
    for pn, (lo, hi) in (("IS", (L.IS_START, L.IS_END)), ("J", (L.J_START, "2099-01-01"))):
        ts = period(tr, lo, hi)
        months = X.months[pn]
        m = dict(s1=L.stats1(ts, X.cost, months), n=len(ts))
        for k in PLANK:
            f = L.fit_static(k, ts, var, X.cost)
            m[f"fit{k}"] = f
            m[f"ev{k}"] = L.eval_stats(k, ts, var, X.daylist, lo, hi if pn == "IS" else X.daylist[-1], X.cost)
        out[pn] = m
    out["grades"] = Counter(t["grade"] for t in period(tr, L.IS_START, "2099"))
    return out


def merge_rows(rs, cid, label):
    over, flags, a, b, fl = {}, [False] * 3, 4, 3, False
    for r in rs:  # rs ordered by IS rank: the better row wins a key conflict
        for k, v in r["over"].items():
            over.setdefault(k, v)
        flags = [x or y for x, y in zip(flags, r["flags"])]
        a, b, fl = min(a, r["var"].a_min), min(b, r["var"].b_min), fl or r["var"].floor
    return dict(id=cid, label=label, kind="combo", over=over, flags=tuple(flags), var=Variant(cid, a, b, fl), gap="combo of IS-eligible rows")


# ---------------------------------------------------------------- formatting
def f0(x): return f"{x:,.0f}"
def fpf(x): return "inf" if x == float("inf") else f"{x:.2f}"


def main():
    t0 = time.time()
    days = L.B.load_days()
    built, info = L.B.build(days)
    L.BUILT = built
    L.load_plans()
    X.daylist = [b[0] for b in built]
    X.cost = L.B.cost1(L.PLANS[25])
    X.cache, X.mismatch = {}, {}
    isd = [d for d in X.daylist if d <= L.IS_END]
    jd = [d for d in X.daylist if d >= L.J_START]
    X.months = {"IS": L.months_between(isd[0], isd[-1]), "J": L.months_between(jd[0], jd[-1])}
    md = []
    md.append(f"Data: {len(X.daylist)} RTH days {X.daylist[0]}..{X.daylist[-1]}; IS = {isd[0]}..{isd[-1]} ({len(isd)} days, {X.months['IS']} months), "
              f"J = {jd[0]}..{jd[-1]} ({len(jd)} days, {X.months['J']} months). Cost ${X.cost:.2f} per micro round trip, $2/pt. History = 3 prior days (as the existing harness).\n")
    pool = mp.Pool(4)

    # ------------------------------------------------------------ PART 1
    base_row = ROWS[0]
    btr, bmir = trades_for(base_row, pool)
    assert X.mismatch["BASE"] == 0, "mirror != engine on baseline"
    md.append(f"\n## Part 1 check: mirror vs engine (baseline): days with different signals = {X.mismatch['BASE']} of {len(X.daylist)}; "
              f"signals {sum(len(v) for v in btr.values())} (IS {len(period(btr, L.IS_START, L.IS_END))}, J {len(period(btr, L.J_START, '2099'))})\n")
    # day classification, baseline window (30 bars)
    cls = {}
    for ds, _, r in bmir:
        eps = r["episodes"]
        if r["signals"]:
            st = "TRADE"
        elif not eps:
            st = "NO_SWEEP"
        else:
            st = max((e["stage"] for e in eps), key=lambda s: L.STAGES.index(s))
        cls[ds] = (st, len(eps), len(r["signals"]), r["had_break"])
    names = {"NO_SWEEP": "no pool swept in the window (A3/A4)", "C1": "swept, no FVG on the run into the sweep (C1, fvg_lookback)",
             "C2": "FVG, but no candle body closed through it (C2)", "C5": "body closed through, displacement too small (C5)",
             "C3": "valid IFVG, no retrace into it in time (C3, ifvg_max_bars / window end)", "A2": "retrace, wrong premium/discount side (A2)",
             "D2": "stop wider than 40 pt (D2, transcript: skip)", "TRADE": "TRADE taken"}
    gapl = {"NO_SWEEP": "A3 pools [GAP params] / A4 transcript / window [GAP]", "C1": "C1 transcript, lookback [GAP]", "C2": "transcript rule",
            "C5": "transcript rule, size [GAP]", "C3": "transcript rule, timing [GAP]", "A2": "transcript rule, threshold [GAP]",
            "D2": "transcript number", "TRADE": ""}
    order = ["NO_SWEEP", "C1", "C2", "C5", "C3", "A2", "D2", "TRADE"]
    md.append("\n### 1a. Day funnel (deepest stage reached by any sweep of the day), baseline defaults, NY 09:30-10:00\n\n| deepest stage | rule label | all days | IS | J |\n|---|---|---|---|---|\n")
    for s in order:
        a = sum(1 for d, v in cls.items() if v[0] == s)
        i_ = sum(1 for d, v in cls.items() if v[0] == s and d <= L.IS_END)
        j_ = sum(1 for d, v in cls.items() if v[0] == s and d >= L.J_START)
        md.append(f"| {names[s]} | {gapl[s]} | {a} | {i_} | {j_} |\n")
    md.append(f"| total days | | {len(cls)} | {len(isd)} | {len(jd)} |\n")
    nb = sum(1 for d, v in cls.items() if v[0] == "NO_SWEEP" and v[3])
    md.append(f"\nOf the {sum(1 for v in cls.values() if v[0]=='NO_SWEEP')} no-sweep days, {nb} had a bar that broke a pool and CLOSED beyond it (a breakout, not a sweep: the engine trades only reversals).\n")
    # episode funnel
    eps_all = [e for ds, _, r in bmir for e in r["episodes"]]
    md.append(f"\n### 1b. Every sweep episode ({len(eps_all)} in {len(X.daylist)} days): the stage it died at, and HOW it ended\n\n| stage reached | rule label | episodes | ended by window end | by timeout (10 bars) | replaced by a new sweep | taken as TRADE / A2 / D2 |\n|---|---|---|---|---|---|---|\n")
    for s in order[1:]:
        es = [e for e in eps_all if e["stage"] == s]
        c = Counter(e["end"] for e in es)
        md.append(f"| {names[s]} | {gapl[s]} | {len(es)} | {c['WINDOW']} | {c['TIMEOUT']} | {c['REPLACED']} | {c['TRADE']+c['A2']+c['D2']} |\n")
    n_ = len(eps_all)
    cum = [("sweeps (A3/A4)", n_), ("... with an FVG on the run (C1)", sum(e["fvg"] for e in eps_all)),
           ("... a body closed through it (C2)", sum(e["through"] or e["ifvg"] for e in eps_all)),
           ("... displacement big enough = valid IFVG (C5)", sum(e["ifvg"] for e in eps_all)),
           ("... retraced into it in time (C3)", sum(e["trade"] or e["a2fail"] or e["d2fail"] for e in eps_all)),
           ("... right premium/discount side (A2)", sum(e["trade"] or e["d2fail"] for e in eps_all)),
           ("... stop <= 40 pt (D2) = TRADE", sum(e["trade"] for e in eps_all))]
    md.append("\nCumulative funnel of the sweep episodes (how many reach each stage):\n\n| stage | episodes reaching it |\n|---|---|\n" + "".join(f"| {a} | {b} |\n" for a, b in cum))
    md.append("\nBy swept pool kind (episodes -> trades):\n\n| pool kind | episodes | trades |\n|---|---|---|\n")
    for k in sorted({e["kind"] for e in eps_all}):
        es = [e for e in eps_all if e["kind"] == k]
        md.append(f"| {k} | {len(es)} | {sum(1 for e in es if e['trade'])} |\n")
    # sweep bar index distribution (when in the window sweeps happen)
    md.append("\nSweep time inside the 30-bar window (episodes that started in each 10-minute slice, and how many of those died of the window end):\n\n| slice | episodes | died by window end | trades |\n|---|---|---|---|\n")
    for a, b_ in ((0, 10), (10, 20), (20, 30)):
        es = [e for e in eps_all if a <= e["idx"] < b_]
        md.append(f"| 09:{31+a:02d}-{'09:'+str(30+b_) if b_<30 else '10:00'} | {len(es)} | {sum(1 for e in es if e['end']=='WINDOW')} | {sum(1 for e in es if e['trade'])} |\n")
    tr_all = [t for ds, _, r in bmir for t in r["signals"]]  # mirror trades (carry the D3 flag)
    ext = sum(1 for t in tr_all if t["extended"])
    md.append(f"\nD3 (reward >= 1:2): never blocks a setup by construction (the engine uses the nearest pool beyond 2R, else 2R itself): {ext} of {len(tr_all)} trades got a pool target, {len(tr_all)-ext} the plain 2R.\n")
    md.append("Other blockers counted: days where the 3-loss cap was reached: "
              f"{sum(1 for ds,_,r in bmir if r['loss_cap'])}; trades per day max {max(len(v) for v in btr.values())}.\n")

    # size stage
    md.append("\n### 1c. SIZE stage (baseline trades, all 100; static Lucid fit at full DLL / MLL room, then the D149 grade rule)\n\n")
    gc = Counter(t["grade"] for t in tr_all)
    md.append(f"Grades: {dict(gc)} (confluence count: {dict(sorted(Counter(t['nconf'] for t in tr_all).items()))}). Grade size multiplier / 2.0: A+ 1.0, B 0.5, C 0.25 of the fit size.\n\n")
    md.append("| plan | fit micros at 20 pt (full) | signals | fit gives 0 (stop too wide for the $ budget) | sized 0 by the grade rule | sized >= 1 | sized >= 1 by grade A+/B/C |\n|---|---|---|---|---|---|---|\n")
    for k in PLANK:
        p, rc = L.PLANS[k], L.RISKCFG[k]
        full0 = grade0 = ok = 0
        byg = Counter()
        for t in tr_all:
            cf = L.full_fit(p, rc, t, L.D(p["dll"]) if p["dll"] is not None else None, p["mll"])
            c = BASEV.size(t, cf)
            if cf < 1: full0 += 1
            elif c < 1: grade0 += 1
            else:
                ok += 1; byg[t["grade"]] += 1
        cf20 = L.full_fit(p, rc, {"stop_pts": 20.0}, L.D(p["dll"]) if p["dll"] is not None else None, p["mll"])
        md.append(f"| Pro {k}K | {cf20} | {len(tr_all)} | {full0} | {grade0} | {ok} | {byg['A+']}/{byg['B']}/{byg['C']} |\n")
    md.append("\nBy grade (all 100 trades): how many micros each grade gets per plan (median of full fit -> sized):\n\n| plan | grade | trades | median full fit | median sized | sized 0 |\n|---|---|---|---|---|---|\n")
    import statistics
    for k in PLANK:
        p, rc = L.PLANS[k], L.RISKCFG[k]
        for g in ("A+", "B", "C"):
            ts = [t for t in tr_all if t["grade"] == g]
            if not ts: continue
            cfs = [L.full_fit(p, rc, t, L.D(p["dll"]) if p["dll"] is not None else None, p["mll"]) for t in ts]
            szs = [BASEV.size(t, c) for t, c in zip(ts, cfs)]
            md.append(f"| Pro {k}K | {g} | {len(ts)} | {statistics.median(cfs)} | {statistics.median(szs)} | {sum(1 for s in szs if s < 1)} |\n")

    # window extension (mirror at 11:30)
    row1130 = [r for r in ROWS if r["id"] == "W1130"][0]
    _, mir1130 = trades_for(row1130, pool)
    assert X.mismatch["W1130"] == 0
    md.append("\n### 1d. What exists after 10:00 (mirror with ny_window 09:00-11:30; same engine rules; only 09:30+ bars exist, no pre-market)\n\n| slice (bar close) | sweeps (episodes started) | days with a sweep | valid IFVG formed | signals (trades) |\n|---|---|---|---|---|\n")
    ep30 = [(ds, e) for ds, _, r in mir1130 for e in r["episodes"]]
    sg30 = [(ds, t) for ds, _, r in mir1130 for t in r["signals"]]
    for a, b_, lab in ((0, 30, "09:31-10:00 (current window)"), (30, 60, "10:01-10:30"), (60, 90, "10:31-11:00"), (90, 120, "11:01-11:30")):
        es = [(d, e) for d, e in ep30 if a <= e["idx"] < b_]
        ss = [(d, t) for d, t in sg30 if a <= t["sess_idx"] < b_]
        md.append(f"| {lab} | {len(es)} | {len({d for d,_ in es})} | {sum(1 for _,e in es if e['ifvg'])} | {len(ss)} |\n")
    md.append(f"| total | {len(ep30)} | {len({d for d,_ in ep30})} | {sum(1 for _,e in ep30 if e['ifvg'])} | {len(sg30)} |\n")

    # days.csv
    with open(os.path.join(OUT, "days.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["day", "period", "stage_0930_1000", "sweeps_0930_1000", "trades_0930_1000", "breakout_no_sweep",
                    "stage_to_1130", "sweeps_to_1130", "trades_to_1130", "sweeps_after_1000", "ifvg_after_1000", "trades_after_1000"])
        m1130 = {ds: r for ds, _, r in mir1130}
        for ds in X.daylist:
            st, ne, nt, hb = cls[ds]
            r = m1130[ds]
            eps = r["episodes"]
            st2 = "TRADE" if r["signals"] else ("NO_SWEEP" if not eps else max((e["stage"] for e in eps), key=lambda s: L.STAGES.index(s)))
            late = [e for e in eps if e["idx"] >= 30]
            w.writerow([ds, "IS" if ds <= L.IS_END else "J", st, ne, nt, int(hb), st2, len(eps), len(r["signals"]), len(late),
                        sum(1 for e in late if e["ifvg"]), sum(1 for t in r["signals"] if t["sess_idx"] >= 30)])

    # ------------------------------------------------------------ PART 2: evaluate rows
    results = {}
    for r in ROWS:
        results[r["id"]] = evaluate(r, pool)
        print(f"{r['id']:7s} done {time.time()-t0:.0f}s IS n={results[r['id']]['IS']['n']} J n={results[r['id']]['J']['n']}", flush=True)
    bad = {k: v for k, v in X.mismatch.items() if v}
    md.append(f"\n## Mirror-vs-engine assertion on every engine-setting row: mismatching days = {bad if bad else 0}\n")

    # ------------------------------------------------------------ PART 3: IS filter, combos, J check
    def is_ok(r, res):
        b = results["BASE"]
        I, bI = res["IS"], b["IS"]
        if r["kind"] in ("setting",) or r["id"] == "C4" or r["kind"] == "combo":
            more = I["n"] > bI["n"]
        elif r["kind"] == "mgmt":
            more = I["n"] >= bI["n"]
        else:  # sizing: same signals, but more executed trades at the 25K fit
            more = I["fit25"]["n"] > bI["fit25"]["n"]
        pf = I["s1"]["pf"] >= 1.10
        t1 = I["s1"]["total"] >= bI["s1"]["total"] - 1e-9
        t25 = I["fit25"]["total"] >= bI["fit25"]["total"] - 1e-9
        return dict(more=more, pf=pf, t1=t1, t25=t25, ok=more and pf and t1 and t25)

    elig = {}
    for r in ROWS[1:]:
        c = is_ok(r, results[r["id"]])
        elig[r["id"]] = c
    ranked = sorted([r for r in ROWS[1:] if elig[r["id"]]["ok"]], key=lambda r: -results[r["id"]]["IS"]["fit25"]["total"])
    combos = []
    if len(ranked) >= 2:
        combos.append(merge_rows(ranked[:2], "COMBO1", "top-2 IS-eligible: " + " + ".join(r["id"] for r in ranked[:2])))
    if len(ranked) >= 3:
        combos.append(merge_rows(ranked[:3], "COMBO2", "top-3 IS-eligible: " + " + ".join(r["id"] for r in ranked[:3])))
    if len(ranked) > 3:
        combos.append(merge_rows(ranked, "COMBO3", "all IS-eligible: " + " + ".join(r["id"] for r in ranked)))
    for c in combos:
        ROWS.append(c)
        results[c["id"]] = evaluate(c, pool)
        elig[c["id"]] = is_ok(c, results[c["id"]])
        print(c["id"], "done", c["label"], flush=True)
    ranked2 = sorted([r for r in ROWS[1:] if elig[r["id"]]["ok"]], key=lambda r: -results[r["id"]]["IS"]["fit25"]["total"])
    pick = ranked2[0]["id"] if ranked2 else None

    def jcheck(r):
        b, x = results["BASE"]["J"], results[r["id"]]["J"]
        c = dict(t1=x["s1"]["total"] >= b["s1"]["total"] - 1e-9, t25=x["fit25"]["total"] >= b["fit25"]["total"] - 1e-9,
                 pf=x["s1"]["pf"] > 1, n=x["n"] >= b["n"],
                 p25=x["ev25"]["pas"] >= b["ev25"]["pas"] - 2 and x["ev25"]["bust"] <= b["ev25"]["bust"] + 2,
                 p50=x["ev50"]["pas"] >= b["ev50"]["pas"] - 2 and x["ev50"]["bust"] <= b["ev50"]["bust"] + 2)
        c["ACCEPT"] = all(c.values())
        return c

    # ---- tables
    def row1(r):
        res = results[r["id"]]
        out = []
        for pn in ("IS", "J"):
            s = res[pn]["s1"]
            out.append(f"{s['n']} | {s['pm']:.2f} | {s['win']:.1f} | {fpf(s['pf'])} | {s['avg']:.1f} | {f0(s['total'])} | {f0(s['mdd'])}")
        return f"| {r['id']} | {r['label']} | " + " | ".join(out) + " |\n"

    hdr1 = "| id | row | IS trades | /month | win % | PF | avg $ | total $ | max DD $ | J trades | /month | win % | PF | avg $ | total $ | max DD $ |\n|" + "---|" * 16 + "\n"
    md.append("\n## Part 2 table A: 1 micro after costs, IS (2021-10..2023-12) and J (2024-01..2026-10). D4 rows: per-contract 50/50 blend of partial and runner\n\n" + hdr1)
    for r in ROWS:
        md.append(row1(r))
    md.append("\n## Part 2 table B: Lucid-fit sizing (static: full DLL/MLL room; grade rule per row). total $ / max DD $ / executed trades (sized >= 1 of signals)\n\n| id | IS 25K total | IS 25K DD | IS 25K exec | IS 50K total | IS 50K exec | J 25K total | J 25K DD | J 25K exec | J 50K total | J 50K DD | J 50K exec | J 100K total | J 150K total |\n|" + "---|" * 14 + "\n")
    for r in ROWS:
        a, b = results[r["id"]]["IS"], results[r["id"]]["J"]
        md.append(f"| {r['id']} | {f0(a['fit25']['total'])} | {f0(a['fit25']['mdd'])} | {a['fit25']['n']}/{a['n']} | {f0(a['fit50']['total'])} | {a['fit50']['n']}/{a['n']} | "
                  f"{f0(b['fit25']['total'])} | {f0(b['fit25']['mdd'])} | {b['fit25']['n']}/{b['n']} | {f0(b['fit50']['total'])} | {f0(b['fit50']['mdd'])} | {b['fit50']['n']}/{b['n']} | {f0(b['fit100']['total'])} | {f0(b['fit150']['total'])} |\n")
    md.append("\n## Part 2 table C: Lucid Pro eval (EOD trailing MLL + lock, DLL, 40% consistency + day stop, kill distance, 1 position, size shrinks with MLL room). pass % / bust % (rolling start every day inside the period; runs cannot see the other period)\n\n| id | IS 25K | IS 50K | IS 100K | IS 150K | J 25K | J 50K | J 100K | J 150K |\n|" + "---|" * 9 + "\n")
    for r in ROWS:
        res = results[r["id"]]
        cells = [f"{res[pn]['ev'+str(k)]['pas']:.1f} / {res[pn]['ev'+str(k)]['bust']:.1f}" for pn in ("IS", "J") for k in PLANK]
        md.append(f"| {r['id']} | " + " | ".join(cells) + " |\n")
    md.append(f"\nStarts: IS {len(isd)}, J {len(jd)}.\n")

    md.append("\n### Management diagnostics (all 5 years)\n\n| row | trades | outcomes | partials hit (D4) | avg stop pts | avg target pts |\n|---|---|---|---|---|---|\n")
    for rid in ("BASE", "D4", "D5", "D45", "C4"):
        rr = [r for r in ROWS if r["id"] == rid][0]
        tt = [t for v in trades_for(rr, pool)[0].values() for t in v]
        oc = dict(Counter(t["outcome"] for t in tt))
        md.append(f"| {rid} | {len(tt)} | {oc} | {sum(t['partial'] for t in tt)} | {sum(t['stop_pts'] for t in tt)/len(tt):.1f} | {sum(t['tp_pts'] for t in tt)/len(tt):.1f} |\n")
    ncand = len(ROWS) - 1
    md.append(f"\n## Part 3: IS filter ({ncand} candidates tested incl. {len(combos)} combos)\n\nRule: more IS trades than baseline (management rows D4/D5/D4+D5: not fewer; sizing rows: more executed trades at 25K fit) AND IS PF >= 1.10 AND IS total $ (1 micro and 25K fit) >= baseline IS.\n\n| id | row | more trades | IS PF >= 1.10 | IS 1-micro $ >= base | IS 25K $ >= base | IS-eligible | IS 25K total |\n|---|---|---|---|---|---|---|---|\n")
    yn = lambda x: "yes" if x else "no"
    for r in ROWS[1:]:
        c = elig[r["id"]]
        md.append(f"| {r['id']} | {r['label']} | {yn(c['more'])} | {yn(c['pf'])} | {yn(c['t1'])} | {yn(c['t25'])} | {yn(c['ok'])} | {f0(results[r['id']]['IS']['fit25']['total'])} |\n")
    md.append(f"\nIS pick (highest IS 25K-fit total among eligible): {pick}\n")
    md.append("\n### J check for every IS-eligible row (J = 2024-01..2026-10; seen by earlier sessions)\n\n| id | J 1-micro $ >= base | J 25K $ >= base | J PF > 1 | J trades >= base | J 25K pass/bust within 2 pts | J 50K pass/bust within 2 pts | J trades | VERDICT |\n|---|---|---|---|---|---|---|---|---|\n")
    verdicts = {}
    for r in ROWS[1:]:
        if not elig[r["id"]]["ok"]:
            continue
        c = jcheck(r)
        n = results[r["id"]]["J"]["n"]
        verdicts[r["id"]] = c["ACCEPT"]
        md.append(f"| {r['id']} | {yn(c['t1'])} | {yn(c['t25'])} | {yn(c['pf'])} | {yn(c['n'])} | {yn(c['p25'])} | {yn(c['p50'])} | {n}{' (too few to trust)' if n < 30 else ''} | {'ACCEPT' if c['ACCEPT'] else 'REJECT'} |\n")
    if not verdicts:
        md.append("| (none IS-eligible) | | | | | | | | |\n")
    md.append(f"\nBaseline J: trades {results['BASE']['J']['n']}, 1-micro total {f0(results['BASE']['J']['s1']['total'])}, 25K-fit total {f0(results['BASE']['J']['fit25']['total'])}; "
              f"25K eval pass/bust {results['BASE']['J']['ev25']['pas']:.1f}/{results['BASE']['J']['ev25']['bust']:.1f}, 50K {results['BASE']['J']['ev50']['pas']:.1f}/{results['BASE']['J']['ev50']['bust']:.1f}.\n")
    md.append("\nCombos built: " + "; ".join(f"{c['id']} = {c['label']} (cfg {c['over']}, flags d4/d5/c4 {c['flags']}, sizing floor={c['var'].floor} a_min={c['var'].a_min} b_min={c['var'].b_min})" for c in combos) + "\n")
    open(os.path.join(OUT, "tables.md"), "w").write("".join(md))
    pickle.dump(dict(results=results, elig=elig, verdicts=verdicts, pick=pick), open(os.path.join(os.environ.get("NS_CACHE", "/tmp") + ".results.pkl"), "wb"))
    print("".join(md))
    print(f"total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
