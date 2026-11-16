"""Backtest GALA PRICE ACTION, CONTI ORB (rr 1 and 2), CONTI VWAP on the last 2 years of 5y MNQ 1-min RTH data.
Engines called unchanged (engine/gala_pa.replay_day, conti_orb.replay_day, conti_vwap.replay_day), default configs.
Run: cd backend && ../.venv/bin/python ../docs/results/new_strategies/backtest_new.py [days.pkl]
days.pkl = `git cat-file -p fabd3f3` (docs/results/session12/days.pkl; has open/high/low/close/vwap, no volume).
Volume for CONTI VWAP is recovered from the stored session VWAP exactly as session 21 did:
v_k/V_k = (vwap_k - vwap_{k-1}) / (tp_k - vwap_{k-1}); ill-conditioned bars imputed by the median of the last valid ones."""
import sys, os, json, csv, subprocess, statistics, random
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT + "/backend")
from app.config import GalaPaCfg, ContiOrbCfg, ContiVwapCfg, load_rules
from app.engine import gala_pa, conti_orb, conti_vwap
from app.engine.lucid_fit import contracts_for, trade_risk_usd
from app.risk.checks import dll_remaining
from app.risk.lucid_scale import effective_dll
from app.risk.consistency import eval_limits
ET = ZoneInfo("America/New_York")
PKL = next((a for a in sys.argv[1:] if not a.startswith("--")), "/tmp/claude-0/s/days.pkl")
CACHE = os.environ.get("NS_CACHE", "/tmp/claude-0/s/days_vwap.json")
START2Y, START12M = "2024-11-01", "2025-11-01"
TICK = D("0.25"); PV = 2.0

def load_days():
    if not os.path.exists(CACHE):
        subprocess.run(["python3", "-c", (
            "import pickle,json,sys;a,_=pickle.load(open(sys.argv[1],'rb'));"
            "json.dump([[d,{k:[None if x!=x else float(x) for x in v[k]] for k in ('open','high','low','close','vwap')}] for d,v in a],open(sys.argv[2],'w'))"),
            PKL, CACHE], check=True)
    return json.load(open(CACHE))

def build(days):
    """Per day (ds, [GBar], [MBar with recovered volume], stats). NaN minute = flat bar at previous close, volume 0.
    RTH only: first bar closes 09:31 (the 09:30 minute), last 16:00."""
    out, prev_close, nan_n, imp_n, tot_n, maxdev = [], None, 0, 0, 0, 0.0
    for ds, a in days:
        y, m, d = map(int, ds.split("-")); t0 = datetime(y, m, d, 9, 30, tzinfo=ET)
        first = next(x for x in a["open"] if x is not None); pc = prev_close if prev_close is not None else first
        o_, h_, l_, c_ = [], [], [], []
        for k in range(390):
            o, h, l, c = (a[x][k] for x in ("open", "high", "low", "close"))
            if c is None: o = h = l = c = pc; nan_n += 1
            pc = c; o_.append(o); h_.append(h); l_.append(l); c_.append(c)
        prev_close = pc
        # volume recovery (per-day scale, v0 = 1)
        vol = [0.0] * 390; V = 0.0; vw_prev = None; recent = []
        for k in range(390):
            vwk = a["vwap"][k]; tp = (h_[k] + l_[k] + c_[k]) / 3; tot_n += 1
            if a["close"][k] is None or vwk is None: vol[k] = 0.0; continue
            if vw_prev is None: v = 1.0
            else:
                den = tp - vw_prev; r = (vwk - vw_prev) / den if abs(den) > 1e-9 else None
                if r is None or not (0.0 < r < 0.999): v = None
                else: v = V * r / (1 - r)
            if v is None or v <= 0:
                v = statistics.median(recent[-5:]) if recent else 1.0; imp_n += 1
            else: recent.append(v)
            vol[k] = v; V += v; vw_prev = vwk
        gb = [gala_pa.GBar(t0 + timedelta(minutes=k + 1), D(repr(o_[k])), D(repr(h_[k])), D(repr(l_[k])), D(repr(c_[k]))) for k in range(390)]
        mb = [conti_orb.MBar(t0 + timedelta(minutes=k + 1), D(repr(o_[k])), D(repr(h_[k])), D(repr(l_[k])), D(repr(c_[k])), D(repr(vol[k]))) for k in range(390)]
        # check recovered VWAP vs stored
        pv = vv = 0.0
        for k in range(390):
            pv += (h_[k] + l_[k] + c_[k]) / 3 * vol[k]; vv += vol[k]
            if vv > 0 and a["vwap"][k] is not None: maxdev = max(maxdev, abs(pv / vv - a["vwap"][k]))
        out.append((ds, gb, mb))
    return out, dict(nan=nan_n, imputed=imp_n, total=tot_n, maxdev=maxdev)

def mi(t, ds):  # minute index from 09:30
    t = t.astimezone(ET); return (t.hour - 9) * 60 + t.minute - 30

# -------- run engines -> trade dicts (points) --------
def gala_trades(built, cfg):
    out = []; hist_n = 8
    for i, (ds, gb, mb) in enumerate(built):
        if ds < START2Y: continue
        hist = [b for x in built[max(0, i - hist_n):i] for b in x[1]]
        r = gala_pa.replay_day(hist, gb, cfg, TICK, False)
        for s in r.signals:
            out.append(sig_row(ds, "GALA", s.time, s.direction.name, s.setup, s.entry, s.stop_pts, s.outcome, s.exit_time, s.exit_price, gb[-1].c, s.direction.sign, extra=dict(attempt=s.attempt)))
    return out

def orb_trades(built, cfg):
    out = []
    for ds, gb, mb in built:
        if ds < START2Y: continue
        r = conti_orb.replay_day(mb, cfg, TICK)
        for s in r.signals:
            out.append(sig_row(ds, f"ORB_rr{cfg.rr}", s.time, "LONG", "BREAKOUT", s.entry, s.risk_pts, s.outcome, s.exit_time, s.exit_price, mb[-1].c, 1, extra=dict(range_pts=float(r.range_high - r.range_low))))
    return out

def vwap_trades(built, cfg):
    out = []
    for ds, gb, mb in built:
        if ds < START2Y: continue
        for s in conti_vwap.replay_day(mb, cfg, TICK):
            out.append(sig_row(ds, "VWAP", s.time, s.direction.name, s.direction.name, s.entry, abs(s.entry - s.stop), s.outcome, s.exit_time, s.exit_price, mb[-1].c, s.direction.sign))
    return out

def sig_row(ds, strat, t, dr, kind, entry, stop_pts, outcome, et, xp, last_close, sign, extra=None):
    if outcome == "OPEN" or xp is None:  # still open at the 16:00 bar: marked to market
        xp, et, outcome = last_close, None, "MTM"
    idx = mi(t, ds); xi = mi(et, ds) if et is not None else 390
    pts = float((xp - entry) * sign)
    return dict(day=ds, strat=strat, time=t.astimezone(ET).strftime("%H:%M"), idx=idx, exit_idx=xi, exit_time=(et.astimezone(ET).strftime("%H:%M") if et else "16:00"),
                dir=dr, kind=kind, entry=float(entry), stop_pts=float(stop_pts), exit_kind=outcome, pts=pts, **(extra or {}))

# -------- plans & costs --------
def plan(k):
    r = load_rules(Path(ROOT) / "config" / "rules" / f"lucid_pro_{k}k.yaml").rules
    m = r.instrument("MNQ"); i = r.internal; s = r.strategy
    return dict(k=k, S=D(r.account_size), target=r.eval.profit_target, mll=r.eval.max_loss_limit, dll=r.eval.daily_loss_limit, scale=r.eval.dll_scale_above_lock_pct,
                lt=r.eval.lock_trigger, ll=r.eval.lock_level, cons=r.eval.consistency_max_day_pct, mind=r.eval.min_profitable_days, cap_trade=s.max_trade_risk_usd,
                kill=i.kill_switch_mll_distance, maxmicros=min(r.max_contracts.micros, i.internal_max_micros), tick=m.tick, tv=m.tick_value, fee=m.fee_rt,
                slip=m.slippage_ticks or r.trade_plan.slippage_ticks,
                day_stop=eval_limits(r.eval.profit_target, r.eval.consistency_max_day_pct, i.consistency_day_stop_buffer_pct).day_stop,
                fit=dict(GALA=(s.gala_pa_cfg.risk_pct_of_drawdown, s.gala_pa_cfg.dll_use_pct, s.gala_pa_cfg.max_trades_per_day),
                         ORB=(s.conti_orb_cfg.risk_pct_of_drawdown, s.conti_orb_cfg.dll_use_pct, s.conti_orb_cfg.max_trades_per_day),
                         VWAP=(s.conti_vwap_cfg.risk_pct_of_drawdown, s.conti_vwap_cfg.dll_use_pct, s.conti_vwap_cfg.max_losses_per_day)))
def cost1(p): return float(p["fee"] + 2 * p["slip"] * p["tv"])

# -------- stats --------
def net(t, cost): return t["pts"] * PV - cost
def stats(ts, cost, ndays):
    n = len(ts)
    if not n: return dict(n=0)
    u = [net(t, cost) for t in ts]; risk = sum(t["stop_pts"] * PV + cost for t in ts)
    gw = sum(x for x in u if x > 0); gl = -sum(x for x in u if x < 0); eq = peak = dd = 0.0
    for x in u:
        eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
    return dict(n=n, per_day=n / ndays, win=100 * sum(1 for x in u if x > 0) / n, pf=(gw / gl if gl else float("inf")), exp=sum(u) / risk, avg=sum(u) / n, total=sum(u), mdd=dd)

def row(name, s):
    if s["n"] == 0: return f"| {name} | 0 | | | | | | | |\n"
    flag = " (<100: too small)" if s["n"] < 100 else ""
    return f"| {name} | {s['n']}{flag} | {s['per_day']:.2f} | {s['win']:.1f} | {s['pf']:.2f} | {s['exp']*100:.1f}% | {s['avg']:.2f} | {s['total']:.0f} | {s['mdd']:.0f} |\n"
HDR = "| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |\n|---|---|---|---|---|---|---|---|---|\n"

def quarter(d): y, m = int(d[:4]), int(d[5:7]); return f"{y}-Q{(m-1)//3+1}"

# -------- eval sim (same rules as jj_fpt backtest, strategy-specific fit) --------
def eval_run(p, strat, days_trades, start_i, strict):
    rp, up, nfit = p["fit"][strat]
    S = p["S"]; bal = S; peak = S; locked = False; mllv = S - p["mll"]; day_pnls = []; last_tr = 0; cpm = D(str(cost1(p)))
    for n, (ds, tl) in enumerate(days_trades[start_i:], 1):
        pnl_day = D(0); peak_day = D(0); free = -1; stopped = False
        dll = effective_dll(p["dll"], p["scale"], locked, peak, S)
        for t in tl:
            if stopped: break
            if (t["idx"] <= free) if strict else (t["idx"] < free): continue
            left = dll_remaining(dll, pnl_day, peak_day) if dll is not None else None
            if left is not None and left <= 0: stopped = True; break
            risk = trade_risk_usd(p["mll"], rp, nfit, left, up, (bal + pnl_day) - mllv - p["kill"], p["cap_trade"], p["day_stop"])
            c = min(contracts_for(risk, D(str(t["stop_pts"])), p["tick"], p["tv"], p["fee"], p["slip"]), p["maxmicros"])
            if c < 1: continue
            free = max(t["exit_idx"], t["idx"]); last_tr = n
            pnl_day += c * (D(str(t["pts"])) * D(2) - cpm); peak_day = max(peak_day, pnl_day)
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

def eval_stats(p, strat, trades, daylist, lo, strict=True):
    by = defaultdict(list)
    for t in trades: by[t["day"]].append(t)
    for v in by.values(): v.sort(key=lambda t: t["idx"])
    dt = [(d, by.get(d, [])) for d in daylist if d >= lo]
    res = [eval_run(p, strat, dt, i, strict) for i in range(len(dt))]; n = len(res)
    P = [r[1] for r in res if r[0] == "PASS"]; R = [r for r in res if r[0] == "RUNNING"]
    return dict(starts=n, pas=100 * len(P) / n, bust=100 * sum(r[0] == "BUST" for r in res) / n, run=100 * len(R) / n,
                stalled=100 * sum(1 for r in R if r[3]) / n, med_days=statistics.median(P) if P else None,
                med_final=statistics.median([float(r[2]) for r in R]) if R else None)

def fm(x, f="{:.0f}"): return "-" if x is None else f.format(x)

# -------- Monte Carlo --------
def mc(u, runs=5000, seed=7):
    rnd = random.Random(seed); n = len(u)
    def path(seq):
        eq = peak = dd = 0.0; ls = cur = 0
        for x in seq:
            eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
            if x < 0: cur += 1; ls = max(ls, cur)
            else: cur = 0
        return eq, dd, ls
    out = {}
    for name in ("reshuffle", "resample"):
        F, DDs, L = [], [], []
        for _ in range(runs):
            seq = rnd.sample(u, n) if name == "reshuffle" else rnd.choices(u, k=n)
            f, d, l = path(seq); F.append(f); DDs.append(d); L.append(l)
        F.sort(); DDs.sort(); L.sort()
        q = lambda a, p: a[min(len(a) - 1, int(p * len(a)))]
        out[name] = dict(med=q(F, .5), p5=q(F, .05), dd95=q(DDs, .95), ddmed=q(DDs, .5), ls_med=q(L, .5), ls95=q(L, .95), pos=100 * sum(1 for x in F if x > 0) / runs)
    return out

def main():
    days = load_days(); built, info = build(days); daylist = [b[0] for b in built]
    plans = {k: plan(k) for k in (25, 50, 100, 150)}; cost = cost1(plans[25])
    d2 = [d for d in daylist if d >= START2Y]; d12 = [d for d in daylist if d >= START12M]
    cut = d2[int(len(d2) * 0.8)]  # first OOS day
    md = [f"Data: {len(daylist)} RTH days {daylist[0]}..{daylist[-1]} cached; backtest window {d2[0]}..{d2[-1]} ({len(d2)} days), last 12 months from {START12M} ({len(d12)} days). "
          f"Costs per micro round trip: fee ${plans[25]['fee']} + {plans[25]['slip']} tick slippage/side = ${cost:.2f}; $2/pt. VWAP volume recovered from the stored VWAP: {info['imputed']} of {info['total']} bars imputed "
          f"({100*info['imputed']/info['total']:.2f}%), max |recovered VWAP - stored VWAP| = {info['maxdev']:.4f} pt. {info['nan']} NaN minutes filled flat.\n"
          f"In-sample / out-of-sample split (Conti A5): first 80% of the {len(d2)} days = {d2[0]}..{d2[int(len(d2)*0.8)-1]} (IS), last 20% = {cut}..{d2[-1]} (OOS). Rules frozen, default configs, no tuning.\n"]
    strategies = {"GALA": gala_trades(built, GalaPaCfg()), "ORB_rr1": orb_trades(built, ContiOrbCfg(rr=D(1))),
                  "ORB_rr2": orb_trades(built, ContiOrbCfg(rr=D(2))), "VWAP": vwap_trades(built, ContiVwapCfg())}
    for k, ts in strategies.items():
        ts.sort(key=lambda t: (t["day"], t["idx"]))
        for t in ts: t["usd_1micro"] = round(net(t, cost), 2)
        if ts:
            with open(f"{HERE}/trades_{k.lower()}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(ts[0].keys())); w.writeheader(); w.writerows(ts)
    kinds = {"GALA": ("kind", ["BREAK_RETEST", "BOUNCE", "REJECTION"]), "ORB_rr1": ("exit_kind", ["TP", "STOP", "TIME", "MTM"]),
             "ORB_rr2": ("exit_kind", ["TP", "STOP", "TIME", "MTM"]), "VWAP": ("kind", ["LONG", "SHORT"])}
    names = {"GALA": "GALA PRICE ACTION (defaults)", "ORB_rr1": "CONTI ORB rr 1 (default)", "ORB_rr2": "CONTI ORB rr 2", "VWAP": "CONTI VWAP (defaults)"}
    for k, ts in strategies.items():
        md.append(f"\n## {names[k]}\n")
        for pname, lo, nd in (("2-year window", START2Y, len(d2)), ("Last 12 months", START12M, len(d12))):
            sub = [t for t in ts if t["day"] >= lo]
            md.append(f"\n**{pname} ({nd} days), 1 micro after costs**\n\n" + HDR + row("ALL", stats(sub, cost, nd)))
            key, vals = kinds[k]
            for v in vals:
                s = [t for t in sub if t[key] == v]
                if s: md.append(row(f"{key} = {v}", stats(s, cost, nd)))
        if k == "VWAP":
            md.append("\n**VWAP by exit kind (2-year)**\n\n" + HDR)
            for v in ("CROSS", "STOP", "TIME", "TP", "MTM"):
                s = [t for t in ts if t["exit_kind"] == v]
                if s: md.append(row(f"exit = {v}", stats(s, cost, len(d2))))
            strict = []; free = -1; cd = None
            for t in ts:
                if t["day"] != cd: cd = t["day"]; free = -1
                if t["idx"] > free: strict.append(t); free = t["exit_idx"]
            md.append("\n**D139-strict (a reversal on the exit bar is skipped, 2-year)**\n\n" + HDR + row("ALL strict", stats(strict, cost, len(d2))) + row("skipped same-bar reversals", stats([t for t in ts if t not in strict], cost, len(d2))))
        if k == "GALA":
            md.append("\n**Per quarter (1 micro)**\n\n| quarter | trades | win % | PF | total $ |\n|---|---|---|---|---|\n")
            qs = sorted({quarter(d) for d in d2})
            for q in qs:
                s = stats([t for t in ts if quarter(t["day"]) == q], cost, 1)
                md.append(f"| {q} | {s['n']} | {s.get('win',0):.1f} | {s.get('pf',0):.2f} | {s.get('total',0):.0f} |\n" if s["n"] else f"| {q} | 0 | | | |\n")
        if k.startswith("ORB") or k == "VWAP":
            IS = [t for t in ts if t["day"] < cut]; OOS = [t for t in ts if t["day"] >= cut]
            ndI = sum(1 for d in d2 if d < cut); ndO = len(d2) - ndI
            md.append("\n**In-sample (80%) vs out-of-sample (20%), 1 micro**\n\n" + HDR + row("IN-SAMPLE", stats(IS, cost, ndI)) + row("OUT-OF-SAMPLE", stats(OOS, cost, ndO)))
            u = [net(t, cost) for t in ts]
            if u:
                m = mc(u)
                md.append(f"\n**Monte Carlo, 5,000 runs on the {len(u)} 2-year trades, 1 micro** (final P&L $, max drawdown $, longest losing streak = consecutive losing trades)\n\n"
                          "| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th pct |\n|---|---|---|---|---|---|---|\n")
                for nme, r in m.items():
                    md.append(f"| {nme} | {r['med']:.0f} | {r['p5']:.0f} | {r['pos']:.0f} | {r['ddmed']:.0f} | {r['dd95']:.0f} | {r['ls_med']} / {r['ls95']} |\n")
        # eval sims
        strat = "GALA" if k == "GALA" else "ORB" if k.startswith("ORB") else "VWAP"
        md.append(f"\n**Lucid Pro EOD evaluation, Lucid-fit sizing (lucid_fit.trade_risk_usd + contracts_for, divisor {plans[25]['fit'][strat][2]}), rolling start every trading day; trades in the window only**\n\n"
                  "| Plan | starts from | starts | pass % | bust % | running at end % | of which stalled % | median P&L of running $ | median days to pass |\n|---|---|---|---|---|---|---|---|---|\n")
        for kk, p in plans.items():
            for lab, lo in (("2y", START2Y), ("L12m", START12M)):
                e = eval_stats(p, strat, ts, daylist, lo)
                md.append(f"| Pro {kk}K (target ${p['target']}, MLL ${p['mll']}, DLL ${p['dll']}) | {lab} | {e['starts']} | {e['pas']:.1f} | {e['bust']:.1f} | {e['run']:.1f} | {e['stalled']:.1f} | {fm(e['med_final'])} | {fm(e['med_days'])} |\n")
    open(HERE + "/tables.md", "w").write("".join(md)); print("".join(md))

if __name__ == "__main__": main()
