"""JJ F.P.T STRAT backtest on 5y MNQ RTH 1-min bars. Uses engine.jj_fpt.replay / contracts_for / trade_risk_usd unchanged.
Run:  cd backend && ../.venv/bin/python ../docs/results/jj_fpt/backtest_jj.py [days.pkl]
days.pkl = `git cat-file -p fabd3f3` (docs/results/session12/days.pkl); it needs numpy to unpickle, so it is converted
to a JSON cache with the system python3 when the venv has no numpy."""
import sys, os, json, csv, subprocess, statistics
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT + "/backend")
from app.config import JjFptCfg, load_rules
from app.engine.jj_fpt import JBar, SessionInput, replay, contracts_for, trade_risk_usd
from app.risk.checks import dll_remaining
from app.risk.lucid_scale import effective_dll
from app.risk.consistency import eval_limits

ET = ZoneInfo("America/New_York")
PKL = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "/tmp/claude-0/s/days.pkl"
CACHE = PKL + ".json"
SPLIT = "2025-11-01"
PV = D(2)

def load_days():
    if not os.path.exists(CACHE):
        subprocess.run(["python3", "-c", (
            "import pickle,json,sys;a,_=pickle.load(open(sys.argv[1],'rb'));"
            "json.dump([[d,{k:[None if x!=x else float(x) for x in v[k]] for k in ('open','high','low','close')}] for d,v in a],open(sys.argv[2],'w'))"),
            PKL, CACHE], check=True)
    return json.load(open(CACHE))

def build(days):
    """Per day: JBar list [synthetic 09:29 bar] + 390 bars. NaN minute -> flat bar at the previous close.
    The 09:29 bar is missing (RTH only): SYNTHETIC flat bar at the previous day's last close (first day: its own open)."""
    out, prev_close, nan_n = [], None, 0
    for ds, a in days:
        y, m, d = map(int, ds.split("-"))
        t0 = datetime(y, m, d, 9, 30, tzinfo=ET)
        first = next(x for x in a["open"] if x is not None)
        pc = prev_close if prev_close is not None else first
        bars = [JBar(t0, D(repr(pc)), D(repr(pc)), D(repr(pc)), D(repr(pc)))]  # closes at 09:30 = the 09:29 bar
        for k in range(390):
            o, h, l, c = (a[x][k] for x in ("open", "high", "low", "close"))
            if c is None:
                o = h = l = c = pc; nan_n += 1
            pc = c
            bars.append(JBar(t0 + timedelta(minutes=k + 1), D(repr(o)), D(repr(h)), D(repr(l)), D(repr(c))))
        prev_close = pc
        out.append((ds, bars, t0))
    return out, nan_n

def run_signals(built, cfg):
    """One replay per day; returns trade dicts (1 micro points, signals still OPEN closed at the 16:00 bar close)."""
    trades = []
    for ds, bars, t0 in built:
        r = replay(bars, 1, SessionInput("NY", t0, htf_bias=None), cfg)
        for s in r.signals:
            sign = 1 if s.direction.name == "LONG" else -1
            if s.outcome == "WIN": pts, res, ri = s.target_pts, "WIN", s.resolved_index
            elif s.outcome == "LOSS": pts, res, ri = -s.stop_pts, "LOSS", s.resolved_index
            else: pts, res, ri = (bars[-1].c - s.entry) * sign, "MTM", len(bars) - 1
            trades.append(dict(day=ds, idx=s.index, time=s.at.strftime("%H:%M"), kind=s.kind, tier=s.tier, dir=s.direction.name,
                               entry=float(s.entry), stop_pts=float(s.stop_pts), target_pts=float(s.target_pts), fair=float(s.fair),
                               room=None if s.room is None else float(s.room), outcome=res, exit_idx=ri, pts=float(pts), session="NY"))
    return trades

PM_WINDOW = 90   # minutes, 14:00-15:30
PM_START = 271   # bars[0] = synthetic 09:29 bar; bar k+1 = minute k after 09:30 -> 14:00 candle (k=270) is index 271

def run_signals_pm(built, cfg):
    """NY_PM session: open 14:00 ET, fair = the 09:30 session open of the same day, window 90 min, htf_bias None, continuation on.
    Bars run to 16:00 so signals still open at 15:30 keep being followed; open ones are marked to market at the 16:00 close."""
    trades = []
    for ds, bars, t0 in built:
        open_at = t0 + timedelta(minutes=270)
        assert bars[PM_START].close_time - timedelta(minutes=1) == open_at
        r = replay(bars, PM_START, SessionInput("NY_PM", open_at, fair=bars[1].o, htf_bias=None, window=PM_WINDOW), cfg)
        for s in r.signals:
            sign = 1 if s.direction.name == "LONG" else -1
            if s.outcome == "WIN": pts, res, ri = s.target_pts, "WIN", s.resolved_index
            elif s.outcome == "LOSS": pts, res, ri = -s.stop_pts, "LOSS", s.resolved_index
            else: pts, res, ri = (bars[-1].c - s.entry) * sign, "MTM", len(bars) - 1
            trades.append(dict(day=ds, idx=s.index, time=s.at.strftime("%H:%M"), kind=s.kind, tier=s.tier, dir=s.direction.name,
                               entry=float(s.entry), stop_pts=float(s.stop_pts), target_pts=float(s.target_pts), fair=float(s.fair),
                               room=None if s.room is None else float(s.room), outcome=res, exit_idx=ri, pts=float(pts), session="NY_PM"))
    return trades

def usd1(t, cost):  # $ at 1 micro incl. fee + slippage both ways
    return t["pts"] * float(PV) - cost

def stats(ts, cost):
    n = len(ts)
    if not n: return dict(n=0)
    u = [usd1(t, cost) for t in ts]
    w = sum(1 for t in ts if t["pts"] > 0)
    gw = sum(x for x in u if x > 0); gl = -sum(x for x in u if x < 0)
    return dict(n=n, win=100 * w / n, pf=(gw / gl if gl else float("inf")), avg_usd=sum(u) / n, avg_pts=sum(t["pts"] for t in ts) / n, total=sum(u))

def sequential(ts):
    """One position at a time: skip a signal that arrives while the previous TAKEN trade is still open."""
    out, free = [], -1
    for t in sorted(ts, key=lambda x: (x["day"], x["idx"])):
        if t["day"] != (out[-1]["day"] if out else None): free = -1
        if t["idx"] >= free:
            out.append(t); free = t["exit_idx"] if t["exit_idx"] > t["idx"] else t["idx"]
    return out

# ---------------- Lucid evaluation sim ----------------
def plan(k):
    r = load_rules(Path(ROOT) / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules
    m = r.instrument("MNQ"); i = r.internal
    return dict(k=k, r=r, S=D(r.account_size), target=r.eval.profit_target, mll=r.eval.max_loss_limit, dll=r.eval.daily_loss_limit,
                scale=r.eval.dll_scale_above_lock_pct, lt=r.eval.lock_trigger, ll=r.eval.lock_level, cons=r.eval.consistency_max_day_pct,
                mind=r.eval.min_profitable_days, jj=r.strategy.jj_fpt_cfg, cap_trade=r.strategy.max_trade_risk_usd, kill=i.kill_switch_mll_distance,
                maxmicros=min(r.max_contracts.micros, i.internal_max_micros), tick=m.tick, tv=m.tick_value, fee=m.fee_rt,
                slip=m.slippage_ticks or r.trade_plan.slippage_ticks,
                day_stop=eval_limits(r.eval.profit_target, r.eval.consistency_max_day_pct, i.consistency_day_stop_buffer_pct).day_stop)

def cost_per_micro(p): return float(p["fee"] + 2 * p["slip"] * p["tv"])

def eval_run(p, days_trades, start_i):
    """days_trades: list of (day, [trades sorted]) . Returns (status, days_used, final_profit)."""
    S = p["S"]; bal = S; peak = S; locked = False; mllv = S - p["mll"]
    day_pnls = []; last_tr = 0; cpm = D(str(cost_per_micro(p)))
    for n, (ds, tl) in enumerate(days_trades[start_i:], 1):
        pnl_day = D(0); peak_day = D(0); free = -1; stopped = False
        dll = effective_dll(p["dll"], p["scale"], locked, peak, S)
        for t in tl:
            if stopped: break
            if t["idx"] < free: continue          # max 1 position
            left = dll_remaining(dll, pnl_day, peak_day) if dll is not None else None
            if left is not None and left <= 0: stopped = True; break
            risk = trade_risk_usd(p["mll"], p["jj"].risk_pct_of_drawdown, p["jj"].stop_after_losses, left, p["jj"].dll_use_pct,
                                  (bal + pnl_day) - mllv - p["kill"], p["cap_trade"], p["day_stop"])
            c = min(contracts_for(risk, D(str(t["stop_pts"])), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"])
            if c < 1: continue                      # JJ_SIZE_BELOW_1
            free = max(t["exit_idx"], t["idx"]); last_tr = n
            pnl_day += c * (D(str(t["pts"])) * PV - cpm); peak_day = max(peak_day, pnl_day)
            if (bal + pnl_day) <= mllv: return ("BUST", n, bal + pnl_day - S, False)
            if pnl_day >= p["day_stop"]: stopped = True   # consistency day stop (N6)
        bal += pnl_day; day_pnls.append(pnl_day)
        if bal > peak: peak = bal
        if locked is False and peak >= p["lt"]: locked = True
        mllv = p["ll"] if locked else peak - p["mll"]
        prof = bal - S
        if prof >= p["target"]:
            big = max(day_pnls); pdays = sum(1 for x in day_pnls if x > 0)
            if big <= p["cons"] / 100 * prof and pdays >= p["mind"]: return ("PASS", n, prof, False)
    nn = len(days_trades) - start_i
    return ("RUNNING", nn, bal - S, nn - last_tr >= 20)  # stalled = no trade taken in the last 20 days (size < 1 micro / DLL)

def eval_stats(p, trades_by_day, daylist, lo):
    """Rolling start on each trading day >= lo."""
    dt = [(d, trades_by_day.get(d, [])) for d in daylist if d >= lo]
    res = [eval_run(p, dt, i) for i in range(len(dt))]
    n = len(res); P = [r[1] for r in res if r[0] == "PASS"]
    return dict(starts=n, pass_pct=100 * len(P) / n, bust_pct=100 * sum(r[0] == "BUST" for r in res) / n,
                run_pct=100 * sum(r[0] == "RUNNING" for r in res) / n, med_days=(statistics.median(P) if P else None),
                stalled_pct=100 * sum(1 for r in res if r[0] == 'RUNNING' and r[3]) / n,
                med_final=statistics.median([float(r[2]) for r in res if r[0] == 'RUNNING']) if any(r[0] == 'RUNNING' for r in res) else None)

def fmt(x, f="{:.1f}"): return "-" if x is None else f.format(x)

def table_rows(ts, key, cost, order):
    rows = []
    for v in order:
        s = stats([t for t in ts if t[key] == v], cost)
        rows.append(s | {"name": v})
    return rows

def md_stats(rows, ndays):
    o = "| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |\n|---|---|---|---|---|---|---|---|\n"
    for r in rows:
        if r["n"] == 0: o += f"| {r['name']} | 0 | | | | | | |\n"; continue
        o += f"| {r['name']} | {r['n']} | {r['n']/ndays:.2f} | {r['win']:.1f} | {r['pf']:.2f} | {r['avg_usd']:.2f} | {r['avg_pts']:.2f} | {r['total']:.0f} |\n"
    return o

def main():
    days = load_days(); built, nan_n = build(days)
    daylist = [b[0] for b in built]
    base = JjFptCfg(); plans = {k: plan(k) for k in (25, 50, 100, 150)}
    cost = cost_per_micro(plans[25])  # same MNQ fee/slippage in every plan yaml
    trades = run_signals(built, base)
    seq = sequential(trades)
    seqset = {(t["day"], t["idx"]) for t in seq}
    for t in trades: t["taken_sequential"] = int((t["day"], t["idx"]) in seqset); t["usd_1micro"] = round(usd1(t, cost), 2)
    with open(HERE + "/trades_jj.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)
    periods = {"Full (2021-10..2026-10)": (daylist[0], trades, seq), "Last 12 months (2025-11..2026-10)": (SPLIT, None, None)}
    md = []
    md.append(f"Data: {len(daylist)} RTH days {daylist[0]}..{daylist[-1]}; {nan_n} NaN minutes filled with a flat bar at the previous close. "
              f"Costs per micro round trip: fee ${plans[25]['fee']} + slippage {plans[25]['slip']} tick/side = ${cost:.2f} (MNQ in config/rules/lucid_pro_25k.yaml). $2/pt.\n")
    out = {}
    for pname, (lo, _, _) in periods.items():
        ts = [t for t in trades if t["day"] >= lo]; sq = [t for t in seq if t["day"] >= lo]; nd = sum(1 for d in daylist if d >= lo)
        md.append(f"\n### Trade statistics, 1 micro: {pname} ({nd} days)\n")
        md.append(md_stats([stats(ts, cost) | {"name": "ALL signals (engine, each followed to its own outcome)"},
                            stats(sq, cost) | {"name": "Sequential, max 1 open position"}], nd))
        md.append("\nBy entry kind (all signals):\n\n" + md_stats(table_rows(ts, "kind", cost, ["CONTINUATION", "BREAK_OF_STRUCTURE", "DISPLACEMENT"]), nd))
        md.append("\nBy tier (all signals):\n\n" + md_stats(table_rows(ts, "tier", cost, ["BASE", "BIG_OPEN", "SMALL_ROOM"]), nd))
        out[pname] = stats(ts, cost)
    md.append("\n### Per year (all signals, 1 micro)\n")
    yrs = sorted({d[:4] for d in daylist}); rows = []
    for y in yrs:
        rows.append(stats([t for t in trades if t["day"][:4] == y], cost) | {"name": y + (" (Oct-Dec)" if y == "2021" else " (Jan-Oct)" if y == "2026" else "")})
    md.append(md_stats(rows, 0 + 1).replace("/day", "/day*"))
    # per-year trades/day correct
    md[-1] = "| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |\n|---|---|---|---|---|---|---|---|\n" + "".join(
        f"| {r['name']} | {r['n']} | {r['n']/sum(1 for d in daylist if d[:4]==r['name'][:4]):.2f} | {r['win']:.1f} | {r['pf']:.2f} | {r['avg_usd']:.2f} | {r['avg_pts']:.2f} | {r['total']:.0f} |\n" for r in rows)
    # break-even
    ts = trades; wins = [t["pts"] for t in ts if t["pts"] > 0]; ls = [-t["pts"] for t in ts if t["pts"] <= 0]
    aw, al = sum(wins) / len(wins), sum(ls) / len(ls)
    be_gross = al / (aw + al) * 100; be_net = (al + cost / float(PV)) / (aw + al) * 100
    md.append(f"\nBreak-even win rate: 25/38 nominal = 39.7% before costs, 41.3% with the ${cost:.0f} round-trip cost (1 micro, 25 pt stop). "
              f"On the realised mix (avg win {aw:.1f} pt, avg loss {al:.1f} pt): {be_gross:.1f}% gross, {be_net:.1f}% after costs. Measured win rate full period: {out['Full (2021-10..2026-10)']['win']:.1f}%.\n")
    # eval sims
    byday = defaultdict(list)
    for t in seq_all_for_eval(trades): byday[t["day"]].append(t)
    md.append("\n### Lucid Pro evaluation simulation (rolling start every trading day, JJ sizing via trade_risk_usd + contracts_for, real plan yaml)\n")
    md.append("Rules: EOD trailing MLL (trails the EOD high balance, locks at lock_trigger -> lock_level), DLL from yaml (stop the day when none left; LucidScale after lock), "
              "consistency 40% (largest day <= 40% of profit at pass) + consistency day stop (38% of target) ends the day, min profitable days per yaml, kill distance $50, "
              "max 1 open position (signal arriving while a trade is open is skipped), contracts capped at min(firm micros, internal_max_micros=10), trade skipped if < 1 micro. "
              "Bust = closed P&L reaches the MLL (intraday excursions inside a trade are not modelled; a stopped trade loses exactly its stop). Trades after the 3-loss session stop are not taken (engine).\n")
    md.append("| Plan | period | starts | pass % | bust % | running at data end % | of which stalled (no trade in last 20 days) % | median P&L of running $ | median days to pass |\n|---|---|---|---|---|---|---|---|---|\n")
    evres = {}
    for k, p in plans.items():
        for pname, lo in (("Full", daylist[0]), ("Last 12m", SPLIT)):
            e = eval_stats(p, byday, daylist, lo); evres[(k, pname)] = e
            md.append(f"| Pro {k}K (target ${p['target']}, MLL ${p['mll']}, DLL ${p['dll']}) | {pname} | {e['starts']} | {e['pass_pct']:.1f} | {e['bust_pct']:.1f} | {e['run_pct']:.1f} | {e['stalled_pct']:.1f} | {fmt(e['med_final'], '{:.0f}')} | {fmt(e['med_days'], '{:.0f}')} |\n")
    # sensitivity
    md.append("\n### Sensitivity (changing only one setting; stats = all signals at 1 micro; eval = Pro 25K rolling starts)\n")
    md.append("| Variant | trades full | win % | PF | $/trade | trades L12 | win % | PF | $/trade | 25K eval pass/bust full | 25K eval pass/bust L12 |\n|---|---|---|---|---|---|---|---|---|---|---|\n")
    variants = [("baseline (defaults)", {}), ("small_room_tier False", {"small_room_tier": False}), ("adapt_fair_price False", {"adapt_fair_price": False}),
                ("wick_rejection_filter False", {"wick_rejection_filter": False}), ("stop_after_losses 99 (off)", {"stop_after_losses": 10})]
    for name, upd in variants:
        if name.startswith("stop_after"):
            c = base.model_copy(update={"stop_after_losses": 99})  # config bound is le=10; model_copy skips validation
        else: c = base.model_copy(update=upd)
        tv = run_signals(built, c)
        bd = defaultdict(list)
        for t in tv: bd[t["day"]].append(t)
        pv = dict(plans[25]); 
        if name.startswith("stop_after"): pv["jj"] = base  # sizing keeps JJ's 3-loss worst-case (sizing only)
        a = stats(tv, cost); b = stats([t for t in tv if t["day"] >= SPLIT], cost)
        ea = eval_stats(pv, bd, daylist, daylist[0]); eb = eval_stats(pv, bd, daylist, SPLIT)
        md.append(f"| {name} | {a['n']} | {a['win']:.1f} | {a['pf']:.2f} | {a['avg_usd']:.2f} | {b['n']} | {b['win']:.1f} | {b['pf']:.2f} | {b['avg_usd']:.2f} | {ea['pass_pct']:.1f}/{ea['bust_pct']:.1f} | {eb['pass_pct']:.1f}/{eb['bust_pct']:.1f} |\n")
    open(HERE + "/tables.md", "w").write("".join(md))
    print("".join(md))

def main_pm():
    """NY_PM alone, NY + NY_PM combined (max 1 open position across both), Lucid Pro evals for the combined case.
    Writes trades_jj.csv (both sessions, column `session`) and pm_tables.md.  Run: backtest_jj.py days.pkl --pm"""
    days = load_days(); built, nan_n = build(days); daylist = [b[0] for b in built]
    base = JjFptCfg(); plans = {k: plan(k) for k in (25, 50, 100, 150)}; cost = cost_per_micro(plans[25])
    ny = run_signals(built, base); pm = run_signals_pm(built, base)
    comb = sorted(ny + pm, key=lambda t: (t["day"], t["idx"]))
    seq = sequential(comb); seqset = {(t["day"], t["idx"]) for t in seq}
    pm_seq = sequential(pm)
    for t in comb: t["taken_sequential_combined"] = int((t["day"], t["idx"]) in seqset); t["usd_1micro"] = round(usd1(t, cost), 2)
    with open(HERE + "/trades_jj.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(comb[0].keys())); w.writeheader(); w.writerows(comb)
    md = []
    for pname, lo in (("Full (2021-10..2026-10)", daylist[0]), ("Last 12 months (2025-11..2026-10)", SPLIT)):
        nd = sum(1 for d in daylist if d >= lo)
        f_ = lambda L: [t for t in L if t["day"] >= lo]
        md.append(f"\n#### {pname} ({nd} days)\n\n(1) NY_PM alone, 1 micro, after costs\n\n")
        md.append(md_stats([stats(f_(pm), cost) | {"name": "NY_PM ALL signals"}, stats(f_(pm_seq), cost) | {"name": "NY_PM sequential (max 1 open)"}], nd))
        md.append("\nNY_PM by entry kind (all signals):\n\n" + md_stats(table_rows(f_(pm), "kind", cost, ["CONTINUATION", "BREAK_OF_STRUCTURE", "DISPLACEMENT"]), nd))
        md.append("\nNY_PM by tier (all signals):\n\n" + md_stats(table_rows(f_(pm), "tier", cost, ["BASE", "BIG_OPEN", "SMALL_ROOM"]), nd))
        md.append("\n(2) NY + NY_PM combined\n\n")
        md.append(md_stats([stats(f_(ny), cost) | {"name": "NY alone, ALL signals"}, stats(f_(pm), cost) | {"name": "NY_PM alone, ALL signals"},
                            stats(f_(comb), cost) | {"name": "Combined, ALL signals"},
                            stats(f_(seq), cost) | {"name": "Combined, sequential, max 1 open across both"},
                            stats([t for t in f_(seq) if t["session"] == "NY_PM"], cost) | {"name": "  of which NY_PM trades taken"}], nd))
    taken_pm = sum(1 for t in seq if t["session"] == "NY_PM")
    md.append(f"\nNY_PM signals total {len(pm)}; taken in the combined sequential run {taken_pm} (rest blocked by a still-open NY position at 14:00+). "
              f"NY signals still open at 16:00 are marked to market at the 16:00 close, i.e. they hold the single position through the PM window.\n")
    byday = defaultdict(list)
    for t in comb: byday[t["day"]].append(t)
    md.append("\n(3) Lucid Pro evaluation, NY + NY_PM combined (same sim and D143 sizing as above; max 1 open position across both sessions)\n\n")
    md.append("| Plan | period | starts | pass % | bust % | running at data end % | of which stalled % | median P&L of running $ | median days to pass | NY-only pass/bust for reference |\n|---|---|---|---|---|---|---|---|---|---|\n")
    byday_ny = defaultdict(list)
    for t in ny: byday_ny[t["day"]].append(t)
    for k, p in plans.items():
        for pname, lo in (("Full", daylist[0]), ("Last 12m", SPLIT)):
            e = eval_stats(p, byday, daylist, lo); r = eval_stats(p, byday_ny, daylist, lo)
            md.append(f"| Pro {k}K | {pname} | {e['starts']} | {e['pass_pct']:.1f} | {e['bust_pct']:.1f} | {e['run_pct']:.1f} | {e['stalled_pct']:.1f} | {fmt(e['med_final'], '{:.0f}')} | {fmt(e['med_days'], '{:.0f}')} | {r['pass_pct']:.1f}/{r['bust_pct']:.1f} |\n")
    open(HERE + "/pm_tables.md", "w").write("".join(md)); print("".join(md))

def seq_all_for_eval(trades):
    """Eval sim sees every engine signal (it applies the 1-position rule itself with the sizes it actually takes)."""
    return sorted(trades, key=lambda t: (t["day"], t["idx"]))

if __name__ == "__main__":
    main_pm() if "--pm" in sys.argv else main()
