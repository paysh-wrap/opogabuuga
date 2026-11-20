"""GALA trade-more study (research only, engine unchanged; settings via GalaPaCfg).
Run: cd <worktree>/backend && NS_CACHE=<scratch>/days_vwap.json <venv>/python ../docs/results/new_strategies/gala_trade_more/gala_trade_more.py <days.pkl>
Pick on IS 2021-10-01..2023-12-31, judge on J 2024-01-01..2026-10-30. Writes RESULTS_tables.md + trades_*.csv + results.json here.
"""
import sys, os, csv, math, statistics, multiprocessing as mp, json
from collections import defaultdict
from decimal import Decimal as D
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PKL = next(a for a in sys.argv[1:] if a.endswith(".pkl"))
sys.argv = [sys.argv[0], PKL]
sys.path.insert(0, ROOT + "/backend"); sys.path.insert(0, os.path.join(HERE, ".."))
import backtest_new as bn
from app.config import GalaPaCfg
from app.engine import gala_pa as G
from app.engine.lucid_fit import contracts_for, trade_risk_usd
from app.risk.checks import dll_remaining
from app.risk.lucid_scale import effective_dll
TICK = D("0.25")
IS_END = "2023-12-31"; J_START = "2024-01-01"
HIST_N = 12
BUILT = None; DAYLIST = None; PLANS = None


def split_pts(s, last_close):
    sg = s.direction.sign
    x1 = s.exit_price if s.outcome != "OPEN" and s.exit_price is not None else last_close
    a = float((x1 - s.entry) * sg)
    if s.runner is not None:
        xr = s.runner.exit_price if s.runner.outcome != "OPEN" and s.runner.exit_price is not None else last_close
        b = float((xr - s.entry) * sg)
    else:
        b = a
    return a, b


def run_cfg(kw):
    cfg = GalaPaCfg(**kw)
    out = []
    for i, (ds, gb, mb) in enumerate(BUILT):
        hist = [b for x in BUILT[max(0, i - HIST_N):i] for b in x[1]]
        r = G.replay_day(hist, gb, cfg, TICK, False)
        for s in r.signals:
            a, b = split_pts(s, gb[-1].c)
            done = s.done_at
            xi = bn.mi(done, ds) if done is not None else 390
            out.append(dict(day=ds, idx=bn.mi(s.time, ds), exit_idx=max(xi, bn.mi(s.time, ds)), stop_pts=float(s.stop_pts), pts=a, ptsB=b,
                            setup=s.setup, dir=s.direction.name, outcome=s.outcome, runner=(s.runner.outcome if s.runner else ""), attempt=s.attempt))
    return out


def contracts_static(p, stop_pts):
    risk = trade_risk_usd(p["mll"], p["fit"]["GALA"][0], p["fit"]["GALA"][2], p["dll"], p["fit"]["GALA"][1], p["mll"] - p["kill"], p["cap_trade"], p["day_stop"])
    return min(contracts_for(risk, D(str(stop_pts)), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"])


def pnl_c(t, c, cost, trim):
    if trim and c >= 2:
        a = math.ceil(c / 2); b = c - a
        return 2.0 * (a * t["pts"] + b * t["ptsB"]) - c * cost
    return c * (t["pts"] * 2.0 - cost)


def window_stats(ts, lo, hi, months, cost, trim):
    sub = [t for t in ts if lo <= t["day"] <= hi]
    n = len(sub)
    r = dict(n=n, pm=n / months)
    if not n:
        return r
    u = [t["pts"] * 2.0 - cost for t in sub]
    gw = sum(x for x in u if x > 0); gl = -sum(x for x in u if x < 0)
    eq = pk = dd = 0.0
    for x in u:
        eq += x; pk = max(pk, eq); dd = max(dd, pk - eq)
    r.update(win=100 * sum(1 for x in u if x > 0) / n, pf=(gw / gl if gl else float("inf")), avg=sum(u) / n, tot=sum(u), dd=dd)
    for k in (25, 50):
        p = PLANS[k]; cc = bn.cost1(p); tot = 0.0
        for t in sub:
            c = contracts_static(p, t["stop_pts"])
            if c >= 1:
                tot += pnl_c(t, c, cc, trim)
        r[f"fit{k}"] = tot
    return r


def eval_run(p, days_trades, start_i, trim):
    rp, up, nfit = p["fit"]["GALA"]
    S = p["S"]; bal = S; peak = S; locked = False; mllv = S - p["mll"]; day_pnls = []; cpm = bn.cost1(p)
    for n, (ds, tl) in enumerate(days_trades[start_i:], 1):
        pnl_day = D(0); peak_day = D(0); free = -1; stopped = False
        dll = effective_dll(p["dll"], p["scale"], locked, peak, S)
        for t in tl:
            if stopped: break
            if t["idx"] <= free: continue
            left = dll_remaining(dll, pnl_day, peak_day) if dll is not None else None
            if left is not None and left <= 0: stopped = True; break
            risk = trade_risk_usd(p["mll"], rp, nfit, left, up, (bal + pnl_day) - mllv - p["kill"], p["cap_trade"], p["day_stop"])
            c = min(contracts_for(risk, D(str(t["stop_pts"])), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"])
            if c < 1: continue
            free = max(t["exit_idx"], t["idx"])
            pnl_day += D(repr(round(pnl_c(t, c, cpm, trim), 6)))
            peak_day = max(peak_day, pnl_day)
            if (bal + pnl_day) <= mllv: return "BUST"
            if pnl_day >= p["day_stop"]: stopped = True
        bal += pnl_day; day_pnls.append(pnl_day); peak = max(peak, bal)
        if not locked and peak >= p["lt"]: locked = True
        mllv = p["ll"] if locked else peak - p["mll"]; prof = bal - S
        if prof >= p["target"]:
            big = max(day_pnls); pdays = sum(1 for x in day_pnls if x > 0)
            if big <= p["cons"] / 100 * prof and pdays >= p["mind"]: return "PASS"
    return "RUNNING"


def eval_window(p, ts, lo, hi, trim):
    by = defaultdict(list)
    for t in ts: by[t["day"]].append(t)
    for v in by.values(): v.sort(key=lambda t: t["idx"])
    days = [d for d in DAYLIST if lo <= d <= hi]
    dt = [(d, by.get(d, [])) for d in days]
    res = [eval_run(p, dt, i, trim) for i in range(len(dt))]
    n = len(res)
    return dict(starts=n, pas=100 * res.count("PASS") / n, bust=100 * res.count("BUST") / n)


def work(job):
    name, kw, trim_flag = job
    ts = run_cfg(kw)
    months = {"IS": 27.0, "J": 34.0}
    out = dict(name=name, kw={k: str(v) for k, v in kw.items()}, ts=ts, stats={}, ev={})
    for lab, lo, hi in (("IS", "0000", IS_END), ("J", J_START, "9999")):
        out["stats"][lab] = window_stats(ts, lo, hi, months[lab], bn.cost1(PLANS[25]), trim_flag)
        for k in (25, 50, 100, 150):
            out["ev"][f"{lab}{k}"] = eval_window(PLANS[k], ts, lo, hi, trim_flag)
    return out


# ---------------- Part 1
def part1_day(i):
    ds, gb, mb = BUILT[i]
    cfg = GalaPaCfg()
    hist = [b for x in BUILT[max(0, i - HIST_N):i] for b in x[1]]
    r = G.replay_day(hist, gb, cfg, TICK, False)
    if r.setup is None:
        return None
    first = gb[0]
    plan = G.hourly_plan_candles(hist, first, cfg.history_sessions)
    k = cfg.pivot_lookback
    created = []
    for j in range(1, len(plan)):
        a, b = plan[j - 1], plan[j]
        if a.color == 0 or b.color == 0 or a.color == b.color: continue
        lo, hi = j - k, j + k
        if lo < 0 or hi >= len(plan): continue
        win = plan[lo:hi + 1]
        if b.color < 0 and b.o >= max(x.top for x in win): created.append((j, b.o))
        elif b.color > 0 and b.o <= min(x.bottom for x in win): created.append((j, b.o))
    n_del = n_gap = 0; surv = []
    for j, price in created:
        pier = next((x for x in plan[j + 1:] if x.bottom < price < x.top), None)
        if pier is None: surv.append(price)
        else:
            n_del += 1
            if pier.gap: n_gap += 1
    o = first.o
    up = min([float(s - o) for s in surv if s > o], default=None)
    dn = min([float(o - s) for s in surv if s < o], default=None)
    near = min([x for x in (up, dn) if x is not None], default=None)
    return dict(day=ds, ncand=len(plan), created=len(created), deleted=n_del, del_gap=n_gap, surv=len(surv), up=up, dn=dn, near=near,
                chosen=abs(float(r.level - o)))


def med(x): return statistics.median(x) if x else float("nan")


def main():
    global BUILT, DAYLIST, PLANS
    days = bn.load_days(); BUILT, info = bn.build(days); DAYLIST = [b[0] for b in BUILT]
    PLANS = {k: bn.plan(k) for k in (25, 50, 100, 150)}
    print("cost per micro RT", bn.cost1(PLANS[25]), flush=True)
    pool = mp.Pool(4)
    p1 = [x for x in pool.map(part1_day, range(len(BUILT)), chunksize=20) if x]
    md = ["## Part 1 raw counts\n"]
    for lab, f in (("all 1266 days", lambda d: True), ("IS", lambda d: d <= IS_END), ("J", lambda d: d >= J_START), ("2-year 2024-11-01+", lambda d: d >= "2024-11-01")):
        g = [x for x in p1 if f(x["day"])]
        n = len(g)
        ups = [x["up"] for x in g if x["up"] is not None]; dns = [x["dn"] for x in g if x["dn"] is not None]
        md.append(f"\n### {lab}: {n} setup days (trend day with a level)\n\n| measure | value |\n|---|---|\n")
        md.append(f"| hourly plan candles fed (5 sessions + gap candles), mean | {statistics.mean(x['ncand'] for x in g):.1f} |\n")
        md.append(f"| A4 levels created per day, mean / median | {statistics.mean(x['created'] for x in g):.2f} / {med([x['created'] for x in g]):.0f} |\n")
        md.append(f"| A6 deleted by a later body piercing, mean / median | {statistics.mean(x['deleted'] for x in g):.2f} / {med([x['deleted'] for x in g]):.0f} |\n")
        tot_c = sum(x['created'] for x in g); tot_d = sum(x['deleted'] for x in g); tot_g = sum(x['del_gap'] for x in g)
        md.append(f"| total created / deleted / of those first pierced by the A7 overnight gap candle | {tot_c} / {tot_d} ({100*tot_d/tot_c:.0f}%) / {tot_g} ({100*tot_g/max(tot_d,1):.0f}% of deletions) |\n")
        md.append(f"| deletions first made by a regular hourly candle | {tot_d - tot_g} ({100*(tot_d-tot_g)/max(tot_d,1):.0f}%) |\n")
        md.append(f"| surviving levels per day, mean / median | {statistics.mean(x['surv'] for x in g):.2f} / {med([x['surv'] for x in g]):.0f} |\n")
        md.append(f"| days with zero surviving levels | {sum(1 for x in g if x['surv']==0)} |\n")
        md.append(f"| nearest surviving level ABOVE open: median pt (days having one) | {med(ups):.0f} ({len(ups)} days) |\n")
        md.append(f"| nearest surviving level BELOW open: median pt (days having one) | {med(dns):.0f} ({len(dns)} days) |\n")
        nr = [x["near"] for x in g if x["near"] is not None]
        q = statistics.quantiles(nr, n=4)
        md.append(f"| nearest surviving level either side: median / Q1 / Q3 | {med(nr):.0f} / {q[0]:.0f} / {q[2]:.0f} |\n")
        md.append(f"| chosen level (A8) distance, median | {med([x['chosen'] for x in g]):.0f} |\n")
        for w in (50, 100, 150):
            c = sum(1 for x in nr if x <= w)
            md.append(f"| days with a surviving level within {w} pt of the open (either side) | {c} ({100*c/n:.0f}%) |\n")
    base = {}
    rows = [("baseline_trimON", base, True), ("baseline_trimOFF", dict(trim_at_target=False), False)]
    singles = [("window_end 11:00", dict(window_end="11:00")), ("window_end 11:30", dict(window_end="11:30")), ("window_end 12:30", dict(window_end="12:30")),
               ("window_end 14:00", dict(window_end="14:00")), ("window_end 15:00", dict(window_end="15:00")),
               ("pivot_lookback 2", dict(pivot_lookback=2)), ("history_sessions 8", dict(history_sessions=8)), ("history_sessions 10", dict(history_sessions=10)),
               ("trend_swing_lookback 3", dict(trend_swing_lookback=3)), ("hammer_wick_body_mult 3", dict(hammer_wick_body_mult=D("3"))),
               ("max_wick_through_pts 20", dict(max_wick_through_pts=D("20")))]
    rows += [(n, kw, True) for n, kw in singles]
    res = pool.map(work, rows, chunksize=1)
    R = {r["name"]: r for r in res}
    b = R["baseline_trimON"]

    def eligible(r):
        s, bs = r["stats"]["IS"], b["stats"]["IS"]
        return s["n"] > bs["n"] and s.get("pf", 0) >= 1.10 and s["tot"] >= bs["tot"] and s["fit25"] >= bs["fit25"]
    el = [n for n, _ in singles if eligible(R[n])]
    el.sort(key=lambda n: -R[n]["stats"]["IS"]["fit25"])
    kwmap = dict(singles)
    combos = []

    def merge(names):
        kw = {}; seen = set(); nm = []
        for n in names:
            key = list(kwmap[n])[0]
            if key in seen: continue
            seen.add(key); kw.update(kwmap[n]); nm.append(n)
        return " + ".join(nm), kw
    if len(el) >= 2:
        got = set()
        for c in (el[:2], el[:3], el):
            nm, kw = merge(c)
            if nm not in got and " + " in nm:
                got.add(nm); combos.append(("COMBO " + nm, kw, True))
        combos = combos[:3]
    if combos:
        for r in pool.map(work, combos, chunksize=1): R[r["name"]] = r
    names = [r[0] for r in rows] + [c[0] for c in combos]
    json.dump({n: dict(kw=R[n]["kw"], stats=R[n]["stats"], ev=R[n]["ev"]) for n in names}, open(HERE + "/results.json", "w"), indent=1, default=str)
    for n in names:
        ts = R[n]["ts"]
        if ts:
            with open(f"{HERE}/trades_{n.replace(' ','_').replace('+','and').replace(':','')}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(ts[0].keys())); w.writeheader(); w.writerows(ts)
    for lab in ("IS", "J"):
        md.append(f"\n## Part 2 {lab}: " + ("2021-10-01..2023-12-31 (27 months)" if lab == "IS" else "2024-01-01..2026-10-30 (34 months)") +
                  "\n\nTotals: 1 micro = single 2R bracket after $2.00/RT + $2/pt; fit25/fit50 = static Lucid-fit size per trade (full room), D152 trim when >= 2 contracts.\n\n"
                  "| row | trades | /month | win % | PF | avg $/trade | total $ 1 micro | fit 25K $ | fit 50K $ | max DD $ (1 micro) |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for n in names:
            s = R[n]["stats"][lab]
            if not s["n"]:
                md.append(f"| {n} | 0 | | | | | | | | |\n"); continue
            flag = " (<30: too few)" if s["n"] < 30 else ""
            md.append(f"| {n} | {s['n']}{flag} | {s['pm']:.2f} | {s['win']:.1f} | {s['pf']:.2f} | {s['avg']:.2f} | {s['tot']:.0f} | {s['fit25']:.0f} | {s['fit50']:.0f} | {s['dd']:.0f} |\n")
    md.append("\n## Eval (Lucid Pro EOD, all rules on, rolling start every trading day inside the window; PASS% / BUST%)\n\n| row | window | Pro 25K | Pro 50K | Pro 100K | Pro 150K |\n|---|---|---|---|---|---|\n")
    for n in names:
        for lab in ("IS", "J"):
            e = R[n]["ev"]
            md.append(f"| {n} | {lab} | " + " | ".join(f"{e[f'{lab}{k}']['pas']:.1f} / {e[f'{lab}{k}']['bust']:.1f}" for k in (25, 50, 100, 150)) + " |\n")
    bj = b["stats"]["J"]; be = b["ev"]
    md.append(f"\n## Part 3 verdict\n\nCandidates tested: {len(singles)} singles + {len(combos)} combos = {len(singles)+len(combos)} (+ trim-off baseline). IS-eligible singles: {el if el else 'NONE'}.\n\n"
              "| row | IS eligible | IS 25K fit $ | J trades vs base | J 1-micro $ vs base | J 25K fit $ vs base | J PF | 25K pass/bust vs base | 50K pass/bust vs base | verdict |\n|---|---|---|---|---|---|---|---|---|---|\n")
    for n in names[2:]:
        r = R[n]; s = r["stats"]["IS"]; j = r["stats"]["J"]; e = r["ev"]
        isel = eligible(r) or n.startswith("COMBO")
        ok = (j["n"] > bj["n"] and j["tot"] >= bj["tot"] and j["fit25"] >= bj["fit25"] and j.get("pf", 0) > 1
              and all(e[f"J{k}"]["pas"] >= be[f"J{k}"]["pas"] - 2 and e[f"J{k}"]["bust"] <= be[f"J{k}"]["bust"] + 2 for k in (25, 50)))
        v = "ACCEPT" if ok else "REJECT"
        if j["n"] < 30: v += " (J<30 trades: too few to trust)"
        md.append(f"| {n} | {'yes' if isel else 'no'} | {s['fit25']:.0f} | {j['n']} vs {bj['n']} | {j['tot']:.0f} vs {bj['tot']:.0f} | {j['fit25']:.0f} vs {bj['fit25']:.0f} | {j.get('pf',0):.2f} | {e['J25']['pas']:.1f}/{e['J25']['bust']:.1f} vs {be['J25']['pas']:.1f}/{be['J25']['bust']:.1f} | {e['J50']['pas']:.1f}/{e['J50']['bust']:.1f} vs {be['J50']['pas']:.1f}/{be['J50']['bust']:.1f} | {v} |\n")
    open(HERE + "/RESULTS_tables.md", "w").write("".join(md)); print("".join(md))


if __name__ == "__main__":
    main()
