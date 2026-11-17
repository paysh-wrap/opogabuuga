"""Backtest OKALA 8020, BRUNI STRUCTURE, CANDACE ICT, AUCTION (IMRE) on the last 2 years of cached 5y MNQ 1-min RTH data.
Reuses backtest_new.py (loader, volume recovery, costs, stats, MC, Lucid plans, eval rules). Engines unchanged, default configs.
Run: cd backend && ../.venv/bin/python ../docs/results/new_strategies/backtest_okala_bruni_candace_imre.py
Stage 1 (parallel, cached in NS_TRADES pickle): replay the engines. Stage 2: tables."""
import sys, os, csv, math, pickle, statistics, time
from collections import defaultdict
from decimal import Decimal as D
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]
import backtest_new as B
from app.config import Okala8020Cfg, BruniStructureCfg, CandaceIctCfg, AuctionImreCfg
from app.engine import okala_8020, bruni_structure, candace_ict, auction_imre
from app.engine.lucid_fit import contracts_for, trade_risk_usd, grade_contracts
from app.risk.checks import dll_remaining
from app.risk.lucid_scale import effective_dll
TICK, PV, ET = B.TICK, B.PV, B.ET
CACHE = os.environ.get("NS_TRADES", "/tmp/claude-0/s/trades_4.pkl")
NAMES = ["OKALA", "BRUNI", "CANDACE", "IMRE"]
G = {}

def init():
    days = B.load_days(); built, info = B.build(days)
    G["built"] = built; G["info"] = info

def row(ds, strat, t, dr, kind, entry, stop_pts, exit_kind, et, pts, pts1=None, ptsA=None, ptsB=None, ex1=None, **ex):
    idx = B.mi(t, ds); xi = B.mi(et, ds) if et is not None else 390
    pts1 = pts if pts1 is None else pts1
    return dict(day=ds, strat=strat, time=t.astimezone(ET).strftime("%H:%M"), idx=idx, exit_idx=xi, exit_idx1=(xi if ex1 is None else ex1),
                dir=dr, kind=kind, entry=float(entry), stop_pts=float(stop_pts), exit_kind=exit_kind, pts=float(pts), pts1=float(pts1),
                ptsA=float(pts if ptsA is None else ptsA), ptsB=float(pts if ptsB is None else ptsB), **ex)

def run(name):
    init(); built = G["built"]; out = []
    t0 = time.time()
    for i, (ds, gb, mb) in enumerate(built):
        if ds < B.START2Y: continue
        close_at = {b.close_time: b.c for b in mb}
        last = mb[-1].c
        def px(t): return close_at.get(t, last)
        if name == "OKALA":
            r = okala_8020.replay_day(mb, Okala8020Cfg(), TICK)
            for s in r.signals:
                sg = s.direction.sign; sp = abs(s.entry - s.stop); tp1p = (s.tp1 - s.entry) * sg
                oc, et = s.outcome, s.exit_time
                if oc == "OPEN" or et is None: oc, et, xpx = "MTM", None, last
                else: xpx = px(et)
                mark = float((xpx - s.entry) * sg)
                be = float(D("1"))
                if oc == "STOP": a = b = -float(sp); p1 = -float(sp)
                elif oc in ("BE", "RUNNER", "TIME", "MTM") and s.tp1_time is not None:
                    a = float(tp1p); p1 = float(tp1p)
                    b = be if oc == "BE" else float((s.runner_target - s.entry) * sg) if oc == "RUNNER" else mark
                else: a = b = p1 = mark
                ex1 = B.mi(s.tp1_time, ds) if (s.tp1_time is not None) else None
                xi = B.mi(et, ds) if et is not None else 390
                out.append(row(ds, "OKALA", s.time, s.direction.name, s.setup, s.entry, sp, oc, et, p1, pts1=p1, ptsA=a, ptsB=b, ex1=ex1,
                               add_no=s.add_no, conf="+".join(s.confluences), tp1_hit=int(s.tp1_time is not None)))
        elif name in ("BRUNI", "CANDACE", "IMRE"):
            nh = {"BRUNI": 5, "CANDACE": 3, "IMRE": 10}[name]
            hist = [b for x in built[max(0, i - nh):i] for b in x[2]]
            if name == "BRUNI": sigs = bruni_structure.replay_day(hist, mb, BruniStructureCfg(), TICK).signals
            elif name == "CANDACE": sigs = candace_ict.replay_day(hist, mb, CandaceIctCfg(), TICK).signals
            else: sigs = auction_imre.replay_day(hist, mb, AuctionImreCfg(), TICK).signals
            for s in sigs:
                sg = s.direction.sign
                if name == "IMRE":
                    oc, et = s.outcome, s.exit_time
                    if oc == "TP": xp = s.tp2
                    elif oc == "STOP": xp = s.stop
                    else: oc, et, xp = "MTM", None, last
                    out.append(row(ds, name, s.time, s.direction.name, s.setup, s.entry, abs(s.entry - s.stop), oc, et, (xp - s.entry) * sg,
                                   share=float(s.risk_share), tp1_pts=float((s.tp1 - s.entry) * sg), tp2_pts=float((s.tp2 - s.entry) * sg)))
                else:
                    oc, et, xp = s.outcome, s.exit_time, s.exit_price
                    if oc == "OPEN" or xp is None: oc, et, xp = "MTM", None, last
                    if name == "BRUNI":
                        out.append(row(ds, name, s.time, s.direction.name, s.context, s.entry, abs(s.entry - s.stop), oc, et, (xp - s.entry) * sg,
                                       regime=s.regime, flipped=int(s.flipped)))
                    else:
                        out.append(row(ds, name, s.time, s.direction.name, s.grade, s.entry, abs(s.entry - s.stop), oc, et, (xp - s.entry) * sg,
                                       swept=s.swept.kind, session=s.session, mult=float(s.size_mult), conf="+".join(s.confluences)))
    sys.stderr.write(f"{name}: {len(out)} signals in {time.time()-t0:.0f}s\n")
    return name, out

# ---------- eval sim with per-trade sizing ----------
def size(name, t, c):
    if name == "CANDACE": c = grade_contracts(c, D(str(t["mult"])))
    return c

def pnl_usd(name, t, c, cost):
    if name == "OKALA":
        if c == 1: return t["pts1"] * PV - cost
        a = math.ceil(c / 2); b = c - a
        return (a * t["ptsA"] + b * t["ptsB"]) * PV - c * cost
    return c * (t["pts"] * PV - cost)

def risk_for(name, p, left, room, t, cfgs):
    rp, up, n = cfgs
    r = trade_risk_usd(p["mll"], rp, n, left, up, room, p["cap_trade"], p["day_stop"])
    if name == "IMRE": r = r * D(str(t["share"]))
    return r

def eval_run(name, p, days_trades, start_i, cfgs):
    S = p["S"]; bal = S; peak = S; locked = False; mllv = S - p["mll"]; day_pnls = []; last_tr = 0; cost = B.cost1(p)
    for n, (ds, tl) in enumerate(days_trades[start_i:], 1):
        pnl_day = D(0); peak_day = D(0); free = -1; stopped = False
        dll = effective_dll(p["dll"], p["scale"], locked, peak, S)
        for t in tl:
            if stopped: break
            if t["idx"] <= free: continue
            left = dll_remaining(dll, pnl_day, peak_day) if dll is not None else None
            if left is not None and left <= 0: stopped = True; break
            risk = risk_for(name, p, left, (bal + pnl_day) - mllv - p["kill"], t, cfgs)
            c = min(contracts_for(risk, D(str(t["stop_pts"])), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"])
            c = size(name, t, c)
            if c < 1: continue
            x = t["exit_idx1"] if (name == "OKALA" and c == 1 and t["exit_idx1"] is not None) else t["exit_idx"]
            free = max(x, t["idx"]); last_tr = n
            pnl_day += D(str(round(pnl_usd(name, t, c, cost), 2))); peak_day = max(peak_day, pnl_day)
            if (bal + pnl_day) <= mllv: return ("BUST", n, bal + pnl_day - S, False)
            if pnl_day >= p["day_stop"]: stopped = True
        bal += pnl_day; day_pnls.append(pnl_day); peak = max(peak, bal)
        if not locked and peak >= p["lt"]: locked = True
        mllv = p["ll"] if locked else peak - p["mll"]; prof = bal - S
        if prof >= p["target"]:
            big = max(day_pnls); pdays = sum(1 for x in day_pnls if x > 0)
            if big <= p["cons"] / 100 * prof and pdays >= p["mind"]: return ("PASS", n, prof, False)
    nn = len(days_trades) - start_i
    return ("RUNNING", nn, bal - S, nn - last_tr >= 20)

def eval_stats(name, p, trades, daylist, lo, cfgs):
    by = defaultdict(list)
    for t in trades: by[t["day"]].append(t)
    for v in by.values(): v.sort(key=lambda t: t["idx"])
    dt = [(d, by.get(d, [])) for d in daylist if d >= lo]
    res = [eval_run(name, p, dt, i, cfgs) for i in range(len(dt))]; n = len(res)
    P = [r[1] for r in res if r[0] == "PASS"]; R = [r for r in res if r[0] == "RUNNING"]
    return dict(starts=n, pas=100 * len(P) / n, bust=100 * sum(r[0] == "BUST" for r in res) / n, run=100 * len(R) / n,
                stalled=100 * sum(1 for r in R if r[3]) / n, med_days=statistics.median(P) if P else None,
                med_final=statistics.median([float(r[2]) for r in R]) if R else None)

def fit_curve(name, p, trades, cost):
    """Static Lucid-fit sizing (full DLL and MLL room, no day stop): contracts per trade, equity, max DD."""
    cfgs = FIT[name]; eq = peak = dd = 0.0; cs = []
    for t in trades:
        risk = risk_for(name, p, p["dll"] if False else D(p["dll"]) if p["dll"] is not None else None, p["mll"], t, cfgs)
        c = min(contracts_for(risk, D(str(t["stop_pts"])), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"]); c = size(name, t, c)
        if c < 1: continue
        cs.append(c); eq += pnl_usd(name, t, c, cost); peak = max(peak, eq); dd = max(dd, peak - eq)
    return dict(n=len(cs), skipped=len(trades) - len(cs), medc=statistics.median(cs) if cs else 0, total=eq, mdd=dd)

FIT = {}

def chunks10(u):
    n = len(u); out = []
    for k in range(10):
        s = u[k * n // 10:(k + 1) * n // 10]
        if not s: continue
        gw = sum(x for x in s if x > 0); gl = -sum(x for x in s if x < 0)
        out.append((len(s), 100 * sum(1 for x in s if x > 0) / len(s), gw / gl if gl else float("inf"), sum(s)))
    return out

def main():
    if os.path.exists(CACHE): res = pickle.load(open(CACHE, "rb"))
    else:
        with Pool(4) as pool: res = dict(pool.map(run, NAMES))
        pickle.dump(res, open(CACHE, "wb"))
    days = B.load_days(); built, info = B.build(days); daylist = [b[0] for b in built]
    plans = {k: B.plan(k) for k in (25, 50, 100, 150)}; cost = B.cost1(plans[25])
    from app.config import load_rules
    from pathlib import Path
    st = load_rules(Path(B.ROOT) / "config" / "rules" / "lucid_pro_25k.yaml").rules.strategy
    FIT.update(OKALA=(st.okala_8020_cfg.risk_pct_of_drawdown, st.okala_8020_cfg.dll_use_pct, st.okala_8020_cfg.max_losses_per_day),
               BRUNI=(st.bruni_structure_cfg.risk_pct_of_drawdown, st.bruni_structure_cfg.dll_use_pct, st.bruni_structure_cfg.max_losses_per_day),
               CANDACE=(st.candace_ict_cfg.risk_pct_of_drawdown, st.candace_ict_cfg.dll_use_pct, st.candace_ict_cfg.max_losses_per_day),
               IMRE=(st.order_flow_cfg.auction.risk_pct_of_drawdown, st.order_flow_cfg.auction.dll_use_pct, st.order_flow_cfg.auction.max_trades_per_day))
    d2 = [d for d in daylist if d >= B.START2Y]; d12 = [d for d in daylist if d >= B.START12M]; cut = d2[int(len(d2) * 0.8)]
    md = [f"Data: {len(daylist)} cached RTH days; backtest window {d2[0]}..{d2[-1]} ({len(d2)} days), last 12 months from {B.START12M} ({len(d12)} days). "
          f"Costs per micro round trip ${cost:.2f} (fee + slippage both ways), $2/pt. IS/OOS: first 80% of days = {d2[0]}..{d2[int(len(d2)*0.8)-1]}, OOS = {cut}..{d2[-1]}. "
          f"Fit divisors/risk % read from the plan yaml: {', '.join(f'{k}: {v[0]}/{v[1]}/{v[2]}' for k, v in FIT.items())} (risk % of MLL / DLL use / divisor).\n"]
    title = {"OKALA": "OKALA 8020 (defaults)", "BRUNI": "BRUNI STRUCTURE (defaults, overlays OFF)", "CANDACE": "CANDACE ICT SCALP (defaults, New York window only)", "IMRE": "AUCTION IMRE / Order Flow (defaults, ESTIMATED delta)"}
    for name in NAMES:
        ts = sorted(res[name], key=lambda t: (t["day"], t["idx"]))
        for t in ts: t["usd_1micro"] = round(t["pts"] * PV - cost, 2)
        if ts:
            with open(f"{HERE}/trades_{name.lower()}.csv", "w", newline="") as f:
                keys = sorted({k for t in ts for k in t}, key=lambda k: list(ts[0]).index(k) if k in ts[0] else 99)
                w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(ts)
        base = [t for t in ts if t.get("add_no", 0) == 0]
        md.append(f"\n## {title[name]}\n")
        if name == "OKALA":
            md.append(f"Signals: {len(ts)} = {len(base)} base entries + {len(ts)-len(base)} adds (add-to-winners, engine exposes it via `add_no`). 1-micro P&L is the single bracket at TP1 15 pt "
                      f"(stop -10 pt); Lucid-fit with 2+ micros uses the two-leg bracket (leg A ceil(n/2) at TP1, leg B break-even+1 / runner / time). Eval sims use base entries only (adds need the controller's cap logic, not simulated).\n")
        if name == "IMRE":
            md.append("1-micro and Lucid-fit P&L follow the engine outcome (stop or full second target TP2; the live two-leg partial / stop-to-entry is not replayed by the engine). Fit risk is multiplied by each signal's `risk_share` (as D150 builds it).\n")
        if name == "CANDACE":
            md.append("Only the New York window 09:30-10:00 can trade (data is RTH only); London cannot be tested. Fit size = grade-tightened (`grade_contracts`).\n")
        sets = [("ALL signals", ts)] if name != "OKALA" else [("ALL signals (base + adds)", ts), ("base entries only", base), ("adds only", [t for t in ts if t["add_no"] > 0])]
        keyf = {"OKALA": "kind", "BRUNI": "kind", "CANDACE": "kind", "IMRE": "kind"}[name]
        for pname, lo, nd in (("2-year window", B.START2Y, len(d2)), ("Last 12 months", B.START12M, len(d12))):
            md.append(f"\n**{pname} ({nd} days), 1 micro after costs**\n\n" + B.HDR)
            for lab, sset in sets:
                sub = [t for t in sset if t["day"] >= lo]; md.append(B.row(lab, B.stats(sub, cost, nd)))
            sub = [t for t in (base if name == "OKALA" else ts) if t["day"] >= lo]
            for v in sorted({t[keyf] for t in sub}):
                md.append(B.row(f"{keyf} = {v}" + (" (base)" if name == "OKALA" else ""), B.stats([t for t in sub if t[keyf] == v], cost, nd)))
            if name == "CANDACE":
                for v in sorted({t["swept"] for t in sub}): md.append(B.row(f"swept = {v}", B.stats([t for t in sub if t["swept"] == v], cost, nd)))
            if name == "BRUNI":
                for v in sorted({str(t["regime"]) for t in sub}): md.append(B.row(f"regime = {v}", B.stats([t for t in sub if str(t["regime"]) == v], cost, nd)))
            ek = "exit_kind"
            for v in sorted({t[ek] for t in sub}): md.append(B.row(f"exit = {v}", B.stats([t for t in sub if t[ek] == v], cost, nd)))
        ev = base if name == "OKALA" else ts
        for t in ev: t["_"] = 0
        md.append("\n**Max drawdown at Lucid-fit sizing (static: full DLL and MLL room, one fit per trade, no day stop; skipped = fit gives < 1 contract), 2-year**\n\n| Plan | trades sized | skipped | median contracts | total $ | max DD $ |\n|---|---|---|---|---|---|\n")
        for k, p in plans.items():
            f = fit_curve(name, p, ev, cost)
            md.append(f"| Pro {k}K | {f['n']} | {f['skipped']} | {f['medc']} | {f['total']:.0f} | {f['mdd']:.0f} |\n")
        u = [B.net(t, cost) for t in ev]
        IS = [t for t in ev if t["day"] < cut]; OOS = [t for t in ev if t["day"] >= cut]; ndI = sum(1 for d in d2 if d < cut)
        md.append("\n**In-sample (80%) vs out-of-sample (20%), 1 micro" + (", base entries" if name == "OKALA" else "") + "**\n\n" + B.HDR + B.row("IN-SAMPLE", B.stats(IS, cost, ndI)) + B.row("OUT-OF-SAMPLE", B.stats(OOS, cost, len(d2) - ndI)))
        if u:
            ch = chunks10(u); ow = 100 * sum(1 for x in u if x > 0) / len(u)
            md.append(f"\n**10-chunk stability (chronological, {len(u)} trades, ~{len(u)//10} per chunk; overall win {ow:.1f}%)**\n\n| chunk | trades | win % | PF | P&L $ |\n|---|---|---|---|---|\n")
            for i, (n, w, pf, s) in enumerate(ch, 1): md.append(f"| {i} | {n} | {w:.1f} | {pf:.2f} | {s:.0f} |\n")
            ws = [c[1] for c in ch]; dev = sum(1 for w in ws if abs(w - ow) > 20)
            md.append(f"\nWin-rate swing (max - min) = {max(ws)-min(ws):.1f} pts; chunks > 20 pts from the overall win rate: {dev} of {len(ws)}; profitable chunks: {sum(1 for c in ch if c[3] > 0)} of {len(ch)}.\n")
            # autocorrelation + PF without best trade
            aft = [u[i] for i in range(1, len(u)) if u[i - 1] < 0]; cw = 100 * sum(1 for x in aft if x > 0) / len(aft) if aft else float("nan")
            ub = sorted(u)[:-1]; gw = sum(x for x in ub if x > 0); gl = -sum(x for x in ub if x < 0)
            md.append(f"Autocorrelation (G/F2): win after a loss {cw:.1f}% ({len(aft)} trades) vs overall {ow:.1f}% (gap {ow-cw:+.1f} pts). Profit factor without the single best trade: {gw/gl if gl else float('inf'):.2f}.\n")
            m = B.mc(u)
            md.append(f"\n**Monte Carlo, 5,000 runs on {len(u)} trades, 1 micro**\n\n| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th |\n|---|---|---|---|---|---|---|\n")
            for nme, r in m.items(): md.append(f"| {nme} | {r['med']:.0f} | {r['p5']:.0f} | {r['pos']:.0f} | {r['ddmed']:.0f} | {r['dd95']:.0f} | {r['ls_med']} / {r['ls95']} |\n")
        md.append("\n**Lucid Pro EOD evaluation (Lucid-fit sizing, rolling start every trading day; window trades only" + ("; base entries" if name == "OKALA" else "") + ")**\n\n| Plan | starts from | starts | pass % | bust % | running % | of which stalled % | median P&L of running $ | median days to pass |\n|---|---|---|---|---|---|---|---|---|\n")
        for k, p in plans.items():
            for lab, lo in (("2y", B.START2Y), ("L12m", B.START12M)):
                e = eval_stats(name, p, ev, daylist, lo, FIT[name])
                md.append(f"| Pro {k}K (target ${p['target']}, MLL ${p['mll']}, DLL ${p['dll']}) | {lab} | {e['starts']} | {e['pas']:.1f} | {e['bust']:.1f} | {e['run']:.1f} | {e['stalled']:.1f} | {B.fm(e['med_final'])} | {B.fm(e['med_days'])} |\n")
    open(HERE + "/tables_okala_bruni_candace_imre.md", "w").write("".join(md)); print("".join(md))

if __name__ == "__main__": main()
