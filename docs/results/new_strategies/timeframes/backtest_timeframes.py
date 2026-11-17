"""TIMEFRAME SENSITIVITY of the seven new strategies, last 2 years (2024-11..2026-10) of cached MNQ 1-min RTH data.
Reuses backtest_new.py (loader, volume recovery, costs, stats, IS/OOS cut) and the signal->P&L conversion of
backtest_okala_bruni_candace_imre.py. Engines are called UNCHANGED, every other default unchanged, no tuning.
How a bar size N is applied (see RESULTS_timeframes.md "How each timeframe is applied"):
  GALA, CONTI ORB, CONTI VWAP, CANDACE, IMRE : the 1-minute bars are aggregated into N-minute bars (o first, h max, l min,
      c last, volume summed, close_time of the last minute) and passed as the engine's bar input (today + history).
  OKALA  : cfg.entry_minutes = N (engine's own field; bars stay 1-minute).   BRUNI : cfg.tf_minutes = N (engine's own field).
  Both fields are bounded by the config validator (okala 1..5, bruni 15..15); values outside are set with model_copy(update=)
  (no validation, engine code untouched) and flagged "outside validated bound".
Run: cd backend && ../.venv/bin/python ../docs/results/new_strategies/timeframes/backtest_timeframes.py [--sample]
Stage 1 (parallel, cached in NS_TF_CACHE pickle) replays the engines per (strategy, N); stage 2 writes tables + CSVs."""
import sys, os, csv, pickle, time
from decimal import Decimal as D
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
SAMPLE = "--sample" in sys.argv
sys.argv = [sys.argv[0]]
import backtest_new as B
from app.config import GalaPaCfg, ContiOrbCfg, ContiVwapCfg, Okala8020Cfg, BruniStructureCfg, CandaceIctCfg, AuctionImreCfg
from app.engine import gala_pa, conti_orb, conti_vwap, okala_8020, bruni_structure, candace_ict, auction_imre
TICK, PV, ET = B.TICK, B.PV, B.ET
CACHE = os.environ.get("NS_TF_CACHE", "/tmp/claude-0/s/tf_trades.pkl")
TFS = [1, 2, 3, 5, 10, 15, 30]
STRATS = ["GALA", "ORB", "VWAP", "OKALA", "BRUNI", "CANDACE", "IMRE"]
G = {}

def agg(bars, n, cls):
    if n == 1: return bars
    out = []
    for k in range(0, len(bars), n):
        g = bars[k:k + n]
        if cls is conti_orb.MBar:
            out.append(cls(g[-1].close_time, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c, sum((x.v for x in g), D(0))))
        else:
            out.append(cls(g[-1].close_time, g[0].o, max(x.h for x in g), min(x.l for x in g), g[-1].c))
    return out

def nb(i, n, kind):
    key = (i, n, kind)
    if key not in G["cache"]:
        ds, gb, mb = G["built"][i]
        G["cache"][key] = agg(gb, n, gala_pa.GBar) if kind == "g" else agg(mb, n, conti_orb.MBar)
    return G["cache"][key]

def r_(ds, t, entry, stop_pts, kind, pts, last_exit_t=None):
    return dict(day=ds, time=t.astimezone(ET).strftime("%H:%M"), idx=B.mi(t, ds), stop_pts=float(stop_pts), exit_kind=kind, pts=float(pts))

def day_rows(args):
    strat, n, i = args
    built = G["built"]; ds = built[i][0]; out = []; skip = None
    last = built[i][2][-1].c
    if strat == "GALA":
        hist = [b for x in range(max(0, i - 8), i) for b in nb(x, n, "g")]; today = nb(i, n, "g")
        r = gala_pa.replay_day(hist, today, GalaPaCfg(), TICK, False); skip = r.skip
        for s in r.signals:
            xp, oc = (s.exit_price, s.outcome) if (s.outcome != "OPEN" and s.exit_price is not None) else (today[-1].c, "MTM")
            out.append(r_(ds, s.time, s.entry, s.stop_pts, oc, (xp - s.entry) * s.direction.sign))
    elif strat == "ORB":
        today = nb(i, n, "m"); r = conti_orb.replay_day(today, ContiOrbCfg(), TICK); skip = r.skip
        for s in r.signals:
            xp, oc = (s.exit_price, s.outcome) if (s.outcome != "OPEN" and s.exit_price is not None) else (today[-1].c, "MTM")
            out.append(r_(ds, s.time, s.entry, s.risk_pts, oc, xp - s.entry))
    elif strat == "VWAP":
        today = nb(i, n, "m")
        for s in conti_vwap.replay_day(today, ContiVwapCfg(), TICK):
            xp, oc = (s.exit_price, s.outcome) if (s.outcome != "OPEN" and s.exit_price is not None) else (today[-1].c, "MTM")
            out.append(r_(ds, s.time, s.entry, abs(s.entry - s.stop), oc, (xp - s.entry) * s.direction.sign))
    elif strat == "OKALA":
        mb = built[i][2]; cfg = Okala8020Cfg().model_copy(update={"entry_minutes": n}) if n != 3 else Okala8020Cfg()
        close_at = {b.close_time: b.c for b in mb}
        for s in okala_8020.replay_day(mb, cfg, TICK).signals:
            if s.add_no != 0: continue  # base entries only (1 micro cannot add)
            sg = s.direction.sign; sp = abs(s.entry - s.stop); oc, et = s.outcome, s.exit_time
            if oc == "OPEN" or et is None: oc, xpx = "MTM", mb[-1].c
            else: xpx = close_at.get(et, mb[-1].c)
            mark = float((xpx - s.entry) * sg)
            if oc == "STOP": p1 = -float(sp)
            elif oc in ("BE", "RUNNER", "TIME", "MTM") and s.tp1_time is not None: p1 = float((s.tp1 - s.entry) * sg)
            else: p1 = mark
            out.append(r_(ds, s.time, s.entry, sp, oc, p1))
    elif strat == "BRUNI":
        mb = built[i][2]; hist = [b for x in built[max(0, i - 5):i] for b in x[2]]
        cfg = BruniStructureCfg().model_copy(update={"tf_minutes": n}) if n != 15 else BruniStructureCfg()
        for s in bruni_structure.replay_day(hist, mb, cfg, TICK).signals:
            xp, oc = (s.exit_price, s.outcome) if (s.outcome != "OPEN" and s.exit_price is not None) else (mb[-1].c, "MTM")
            out.append(r_(ds, s.time, s.entry, abs(s.entry - s.stop), oc, (xp - s.entry) * s.direction.sign))
    elif strat == "CANDACE":
        hist = [b for x in range(max(0, i - 3), i) for b in nb(x, n, "m")]; today = nb(i, n, "m")
        for s in candace_ict.replay_day(hist, today, CandaceIctCfg(), TICK).signals:
            xp, oc = (s.exit_price, s.outcome) if (s.outcome != "OPEN" and s.exit_price is not None) else (today[-1].c, "MTM")
            out.append(r_(ds, s.time, s.entry, abs(s.entry - s.stop), oc, (xp - s.entry) * s.direction.sign))
    elif strat == "IMRE":
        hist = [b for x in range(max(0, i - 10), i) for b in nb(x, n, "m")]; today = nb(i, n, "m")
        for s in auction_imre.replay_day(hist, today, AuctionImreCfg(), TICK).signals:
            if s.outcome == "TP": xp, oc = s.tp2, "TP"
            elif s.outcome == "STOP": xp, oc = s.stop, "STOP"
            else: xp, oc = today[-1].c, "MTM"
            out.append(r_(ds, s.time, s.entry, abs(s.entry - s.stop), oc, (xp - s.entry) * s.direction.sign))
    return (strat, n, i), out, skip

def init():
    G["cache"] = {}

def stage1():
    if os.path.exists(CACHE) and not SAMPLE: return pickle.load(open(CACHE, "rb"))
    days = B.load_days(); built, info = B.build(days); G["built"] = built; G["cache"] = {}
    idxs = [i for i, b in enumerate(built) if b[0] >= B.START2Y]
    if SAMPLE: idxs = idxs[:3]
    tasks = [(s, n, i) for s in STRATS for n in TFS for i in idxs]
    # slow engines first
    tasks.sort(key=lambda t: {"BRUNI": 0, "IMRE": 1}.get(t[0], 2))
    t0 = time.time(); res = {}; skips = {}
    with Pool(4, initializer=init) as pool:
        for k, (key, rows, skip) in enumerate(pool.imap_unordered(day_rows, tasks, chunksize=4)):
            res.setdefault(key[:2], []).extend(rows)
            if skip: skips.setdefault(key[:2], {}); skips[key[:2]][skip] = skips[key[:2]].get(skip, 0) + 1
            if k % 500 == 0: sys.stderr.write(f"{k}/{len(tasks)} {time.time()-t0:.0f}s\n")
    out = dict(res=res, skips=skips, ndays=len(idxs))
    if not SAMPLE: pickle.dump(out, open(CACHE, "wb"))
    return out

def pf(u):
    gw = sum(x for x in u if x > 0); gl = -sum(x for x in u if x < 0)
    return gw / gl if gl else (float("inf") if gw else 0.0)

def summarize(ts, cost, cut, d12lo):
    ts = sorted(ts, key=lambda t: (t["day"], t["idx"]))
    for t in ts: t["usd"] = t["pts"] * PV - cost
    def blk(sub):
        u = [t["usd"] for t in sub]
        if not u: return dict(n=0, win=0, pf=0, avg=0, total=0, mdd=0)
        eq = pk = dd = 0.0
        for x in u: eq += x; pk = max(pk, eq); dd = max(dd, pk - eq)
        return dict(n=len(u), win=100 * sum(1 for x in u if x > 0) / len(u), pf=pf(u), avg=sum(u) / len(u), total=sum(u), mdd=dd)
    return dict(all=blk(ts), l12=blk([t for t in ts if t["day"] >= d12lo]), IS=blk([t for t in ts if t["day"] < cut]), OOS=blk([t for t in ts if t["day"] >= cut]))

def f(x, p=2): return "inf" if x == float("inf") else f"{x:.{p}f}"

TITLE = {"GALA": "GALA PRICE ACTION", "ORB": "CONTI ORB (default rr 1)", "VWAP": "CONTI VWAP", "OKALA": "OKALA 8020 (base entries)",
         "BRUNI": "BRUNI STRUCTURE", "CANDACE": "CANDACE ICT SCALP", "IMRE": "AUCTION IMRE"}
HOW = {"GALA": "input bars aggregated to N min (engine builds its own 5-min entry candles from them; first bar must close 09:31)",
       "ORB": "input bars aggregated to N min (first bar must close 09:31)",
       "VWAP": "input bars aggregated to N min (volume summed)",
       "OKALA": "cfg.entry_minutes = N (validated 1..5; 10/15/30 set outside the bound; 10-min structure candles fixed)",
       "BRUNI": "cfg.tf_minutes = N (validated bound is 15..15, every other N set outside the bound; entry trigger stays a 1-minute bar)",
       "CANDACE": "input bars aggregated to N min (bar-count settings then span N times longer; the 09:31 gap-level feature needs a 1-minute first bar)",
       "IMRE": "input bars aggregated to N min (bar-count settings then span N times longer; estimated delta per N-min bar)"}

def main():
    data = stage1(); res = data["res"]; skips = data["skips"]
    days = B.load_days(); built, info = B.build(days); daylist = [b[0] for b in built]; p = B.plan(25); cost = B.cost1(p)
    d2 = [d for d in daylist if d >= B.START2Y]; cut = d2[int(len(d2) * 0.8)]
    md = [f"Window {d2[0]}..{d2[-1]} ({len(d2)} RTH days), last 12 months from {B.START12M}. 1 micro MNQ, $2/pt, cost ${cost:.2f} per round trip (fee + slippage both ways). "
          f"IS = first 80% of days ({d2[0]}..{d2[int(len(d2)*0.8)-1]}), OOS = last 20% ({cut}..{d2[-1]}). Default configs, nothing tuned. Samples under 100 trades are flagged **<100**. "
          f"Max DD is the 2-year peak-to-trough of the 1-micro equity curve in trade order.\n"]
    csvrows = []; verdicts = []
    for s in STRATS:
        md.append(f"\n## {TITLE[s]}\n\nHow N is applied: {HOW[s]}.\n\n")
        md.append("| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        ok = []
        for n in TFS:
            ts = res.get((s, n), []); sk = skips.get((s, n), {})
            nd = data["ndays"]
            status = "ran"
            if s in ("GALA", "ORB") and n > 1:
                code = "GALA_NO_OPEN" if s == "GALA" else "CORB_NO_RANGE"
                if sk.get(code, 0) >= 0.95 * nd and not ts:
                    md.append(f"| {n} min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |\n")
                    csvrows.append([s, n, "not runnable", f"engine returns {code} on {sk.get(code,0)}/{nd} days: it requires the first bar to close at 09:31 (1-minute bars)"] + [""] * 20)
                    continue
            flag = ""
            sm = summarize(ts, cost, cut, B.START12M); a, l, i_, o = sm["all"], sm["l12"], sm["IS"], sm["OOS"]
            if a["n"] == 0:
                md.append(f"| {n} min | ran, 0 trades | 0 | | | | | | | | | | | | |\n"); csvrows.append([s, n, "ran, 0 trades", ""] + [""] * 20); continue
            small = " **<100**" if a["n"] < 100 else ""
            ext = ""
            if (s == "OKALA" and n > 5) or (s == "BRUNI" and n != 15): ext = " (outside validated bound)"
            md.append(f"| {n} min{ext} | ran | {a['n']}{small} | {f(a['win'],1)} | {f(a['pf'])} | {f(a['avg'])} | {a['total']:.0f} | {a['mdd']:.0f} | {l['n']} | {f(l['pf'])} | {l['total']:.0f} | "
                      f"{i_['n']}{' **<100**' if i_['n']<100 else ''} | {f(i_['pf'])} | {o['n']}{' **<100**' if o['n']<100 else ''} | {f(o['pf'])} |\n")
            csvrows.append([s, n, "ran" + ext, "", a["n"], round(a["win"], 2), round(a["pf"], 3), round(a["avg"], 2), round(a["total"], 1), round(a["mdd"], 1),
                            l["n"], round(l["pf"], 3), round(l["total"], 1), i_["n"], round(i_["pf"], 3), round(i_["total"], 1), o["n"], round(o["pf"], 3), round(o["total"], 1)])
            ok.append((n, a, i_, o, ext))
        if s in ("GALA", "ORB"):
            md.append(f"\nSkip codes for N > 1 (days): " + ", ".join(f"{n}m: {skips.get((s,n),{})}" for n in TFS if n > 1) + "\n")
        winners = [(n, a, i_, o) for n, a, i_, o, e in ok if a["n"] >= 100 and i_["pf"] > 1 and o["pf"] > 1]
        if ok:
            best = max(ok, key=lambda x: x[2]["pf"]); bn, ba, bi, bo, be = best
            bestline = f"in-sample-best bar = {bn} min (IS PF {f(bi['pf'])} on {bi['n']} trades) -> OOS PF {f(bo['pf'])} on {bo['n']} trades, 2y total ${ba['total']:.0f}"
        else: bestline = "no runnable bar size produced trades"
        if winners: v = "YES, " + ", ".join(f"{n} min (n={a['n']}, IS PF {f(i_['pf'])}, OOS PF {f(o['pf'])}, 2y ${a['total']:.0f})" for n, a, i_, o in winners)
        else: v = "NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades"
        md.append(f"\n**Verdict {TITLE[s]}:** {v}. {bestline}. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)\n")
        verdicts.append((s, v, bestline))
    md.append("\n## One-line verdicts\n\n" + "".join(f"- {TITLE[s]}: {v}. {b}.\n" for s, v, b in verdicts))
    open(HERE + "/RESULTS_timeframes_body.md", "w").write("".join(md))
    with open(HERE + "/timeframes_summary.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["strategy", "bar_min", "status", "note", "trades", "win_pct", "pf", "avg_usd", "total_usd", "max_dd_usd", "l12_trades", "l12_pf", "l12_usd", "is_trades", "is_pf", "is_usd", "oos_trades", "oos_pf", "oos_usd"])
        for r in csvrows: w.writerow(r[:19])
    for (s, n), ts in res.items():
        if not ts: continue
        with open(HERE + f"/trades_{s.lower()}_{n}m.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(ts[0].keys())); w.writeheader(); w.writerows(sorted(ts, key=lambda t: (t["day"], t["idx"])))
    print("".join(md))

if __name__ == "__main__": main()
