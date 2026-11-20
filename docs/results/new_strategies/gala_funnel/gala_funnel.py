"""GALA PRICE ACTION funnel: COUNTING study (no tuning, no P&L). Engine called unchanged.
Run: cd backend && NS_CACHE=<scratch>/days_vwap.json ../../.venv/bin/python ../docs/results/new_strategies/gala_funnel/gala_funnel.py <days.pkl> [outdir]
Writes days.csv and tables.md (outdir default = this folder). RESULTS.md is written from these tables.
Per-day stage analysis mirrors gala_pa.find_entry step by step (asserted equal to find_entry's result on every setup day).
"""
import sys, os, csv, statistics, multiprocessing as mp
from collections import Counter
from datetime import timedelta
from decimal import Decimal as D
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PKL = next((a for a in sys.argv[1:] if not a.startswith("--") and a.endswith(".pkl")), None)
OUT = next((a for a in sys.argv[1:] if os.path.isdir(a)), HERE)
sys.argv = [sys.argv[0], PKL]
sys.path.insert(0, ROOT + "/backend"); sys.path.insert(0, os.path.join(HERE, ".."))
import backtest_new as bn
from app.config import GalaPaCfg
from app.engine import gala_pa as G
TICK = D("0.25")
START2Y = "2024-11-01"
BASE = GalaPaCfg()
HIST_N = 10
BUILT = None  # set before the Pool forks


def reason(c, level, sign, cfg):
    """why a candle that touches the level is not an entry: first failing check (wick distance, body/close, hammer)"""
    touch = c.l <= level if sign > 0 else c.h >= level
    body_ok = (c.bottom >= level and c.c > level) if sign > 0 else (c.top <= level and c.c < level)
    wick = (level - c.l) if sign > 0 else (c.h - level)
    if not touch: return "notouch"
    if wick > cfg.max_wick_through_pts: return "wick"
    if not body_ok: return "body"
    if G.hammer(c, sign, cfg.hammer_wick_body_mult, TICK): return "hammer"
    return "valid"


def trace_break(candles, level, sign, cfg):
    """same loop as find_entry BREAK_RETEST, with counters"""
    t = dict(breaks=0, cancelled=0, expired=0, events=Counter(), first=None, episodes=[])
    brk = None; ep = None
    for i, c in enumerate(candles):
        prev_c = candles[i - 1].c if i > 0 else c.o
        isbrk = (c.c > level >= prev_c) if sign > 0 else (c.c < level <= prev_c)
        if brk is None:
            if isbrk: brk = i; t["breaks"] += 1; ep = {}
            continue
        if (c.c < level) if sign > 0 else (c.c > level):
            t["cancelled"] += 1; t["episodes"].append("cancel"); brk = None; ep = None
            if isbrk: brk = i; t["breaks"] += 1; ep = {}
            continue
        if i - brk > cfg.max_retest_bars:
            t["expired"] += 1; t["episodes"].append("expire"); brk = None; ep = None
            continue
        r = reason(c, level, sign, cfg)
        if r != "notouch": t["events"][r] += 1
        if r == "valid":
            grp = [x for x in candles[brk + 1: i + 1] if (x.l <= level if sign > 0 else x.h >= level)]
            ext = min(x.l for x in grp) if sign > 0 else max(x.h for x in grp)
            t["first"] = (i, ext); return t
    if ep is not None: t["episodes"].append("eod")
    return t


def trace_bounce(candles, level, sign, cfg):
    t = dict(reached=False, runs=0, events=Counter(), first=None)
    run = 0
    for i, c in enumerate(candles):
        if (c.l <= level) if sign > 0 else (c.h >= level): t["reached"] = True
        hold = (c.bottom >= level and c.l < level) if sign > 0 else (c.top <= level and c.h > level)
        run = run + 1 if hold else 0
        if run >= cfg.bounce_candles:
            t["runs"] += 1
            r = reason(c, level, sign, cfg)
            t["events"][r] += 1
            if r == "valid":
                grp = candles[i - run + 1: i + 1]
                t["first"] = (i, min(x.l for x in grp) if sign > 0 else max(x.h for x in grp)); return t
    return t


def stage_of(setup, tr, first_end, w1):
    """deepest stage reached; None if a valid entry exists inside the window"""
    ev = tr["events"]
    if setup == "BREAK_RETEST":
        if tr["first"] is not None:
            return None if first_end <= w1 else "g_valid_outside_window"
        if ev["hammer"]: return "f_hammer"
        if ev["body"]: return "e_body_close_wrong_side"
        if ev["wick"]: return "d_wick_through_too_big"
        if tr["breaks"] == 0: return "a_never_broke"
        if any(e in ("eod", "expire") for e in tr["episodes"]): return "c_no_retest_touch_in_time"
        return "b_break_cancelled"
    if tr["first"] is not None:
        return None if first_end <= w1 else "f_valid_outside_window"
    if ev["hammer"]: return "e_hammer"
    if ev["body"]: return "d_body_close"
    if ev["wick"]: return "c_wick_through_too_big"
    if tr["reached"]: return "b_touched_no_bounce_run"
    return "a_level_never_touched"


def classify(i):
    ds, gb, _ = BUILT[i]
    hist = [b for x in BUILT[max(0, i - HIST_N):i] for b in x[1]]
    cfg = BASE
    r = G.replay_day(hist, gb, cfg, TICK, False)
    row = dict(day=ds, trend=r.trend, skip=r.skip or "", setup=r.setup or "", side=("LONG" if r.trend > 0 else "SHORT" if r.trend < 0 else ""),
               level="", dist_open="", reached_1035="", reached_1600="", n_trades=len(r.signals), stage="", first_valid_end="", breaks="", note="")
    if r.setup is None:
        return row
    sign = r.trend; level = r.level; o = gb[0].o
    row["level"] = float(level); row["dist_open"] = float(abs(level - o))
    def reach(b): return b.l <= level <= b.h
    row["reached_1035"] = int(any(reach(b) for b in gb if G._et(b.close_time).time() <= G.time(10, 35)))
    row["reached_1600"] = int(any(reach(b) for b in gb))
    day = G._et(gb[0].close_time).date()
    skip_until = G._at(day, "09:30") + timedelta(minutes=cfg.skip_first_minutes)
    five = [c for c in G.aggregate(gb, 5, gb[-1].close_time) if c.end > skip_until]
    w1 = G._at(day, cfg.window_end)
    if r.setup == "BREAK_RETEST":
        tr = trace_break(five, level, sign, cfg); row["breaks"] = tr["breaks"]
    else:
        tr = trace_bounce(five, level, sign, cfg)
    ref = G.find_entry(five, r.setup, level, sign, cfg, TICK)
    assert (ref is None) == (tr["first"] is None) and (ref is None or ref[0] == tr["first"][0]), (ds, "mirror differs from find_entry")
    fe = five[tr["first"][0]].end if tr["first"] else None
    if fe: row["first_valid_end"] = fe.strftime("%H:%M")
    st = stage_of(r.setup, tr, fe, w1)
    if r.signals:
        row["stage"] = "TRADE"
        if st is not None: row["note"] = f"mirror={st}"
    else:
        row["stage"] = st or "MIRROR_VALID_BUT_NO_TRADE"
    return row


def run_cfg(k):
    name, upd = RELAX[k]
    cfg = BASE.model_copy(update=upd)
    pd = {}
    for i, (ds, gb, _) in enumerate(BUILT):
        hist = [b for x in BUILT[max(0, i - HIST_N):i] for b in x[1]]
        n = len(G.replay_day(hist, gb, cfg, TICK, False).signals)
        if n: pd[ds] = n
    return name, pd


RELAX = [("baseline (defaults)", {}),
 ("window_end 11:30", dict(window_end="11:30")), ("window_end 12:30", dict(window_end="12:30")), ("window_end 15:00", dict(window_end="15:00")),
 ("max_wick_through_pts 20", dict(max_wick_through_pts=D(20))), ("max_wick_through_pts 40", dict(max_wick_through_pts=D(40))), ("max_wick_through_pts 1000 (off)", dict(max_wick_through_pts=D(1000))),
 ("hammer_wick_body_mult 3", dict(hammer_wick_body_mult=D(3))), ("hammer_wick_body_mult 1000 (off)", dict(hammer_wick_body_mult=D(1000))),
 ("max_retest_bars 12", dict(max_retest_bars=12)), ("max_retest_bars 24", dict(max_retest_bars=24)), ("max_retest_bars 78 (all day)", dict(max_retest_bars=78)),
 ("pivot_lookback 2", dict(pivot_lookback=2)), ("pivot_lookback 4", dict(pivot_lookback=4)),
 ("trend_swing_lookback 1", dict(trend_swing_lookback=1)), ("trend_swing_lookback 3", dict(trend_swing_lookback=3)),
 ("history_sessions 3", dict(history_sessions=3)), ("history_sessions 8", dict(history_sessions=8)),
 ("use_open_level on", dict(use_open_level=True)),
 ("stop_buffer_ticks 0", dict(stop_buffer_ticks=0)), ("stop_buffer_ticks 4", dict(stop_buffer_ticks=4)),
 ("ALL LOOSE (window 15:00, wick off, hammer off, retest 78)", dict(window_end="15:00", max_wick_through_pts=D(1000), hammer_wick_body_mult=D(1000), max_retest_bars=78)),
]
VALIDATED = {"max_retest_bars 78 (all day)": "outside validated bound (max_retest_bars le=24)",
             "ALL LOOSE (window 15:00, wick off, hammer off, retest 78)": "outside validated bound (max_retest_bars le=24)"}


def pct(xs, q):
    s = sorted(xs); k = (len(s) - 1) * q; f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main():
    global BUILT
    BUILT, _ = bn.build(bn.load_days())
    print("days", len(BUILT), BUILT[0][0], BUILT[-1][0], flush=True)
    with mp.get_context("fork").Pool(min(8, mp.cpu_count())) as p:
        rows = p.map(classify, range(len(BUILT)), chunksize=8)
        rel = dict(p.map(run_cfg, range(len(RELAX)), chunksize=1))
    with open(os.path.join(OUT, "days.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    md = []
    W = {"2-year (2024-11-01..2026-10-30)": [r for r in rows if r["day"] >= START2Y], "5-year (all days)": rows}
    for wn, rs in W.items():
        n = len(rs); days = {r["day"] for r in rs}
        md.append(f"\n## {wn}: {n} days\n")
        c = Counter()
        for r in rs: c[r["skip"] if r["skip"] else "SETUP"] += 1
        md.append("\n### Day funnel (default config)\n\n| outcome | days | % of days |\n|---|---|---|\n")
        for k in ("GALA_NO_BARS", "GALA_NO_OPEN", "GALA_NO_TREND", "GALA_NO_LEVEL", "GALA_NEWS_FIRST_HOUR", "SETUP"):
            md.append(f"| {k} | {c[k]} | {100*c[k]/n:.1f}% |\n")
        sd = [r for r in rs if r["setup"]]
        md.append(f"\nTrend days (LONG/SHORT): {sum(1 for r in rs if r['trend'])}.\n\n| setup | LONG days | SHORT days | total |\n|---|---|---|---|\n")
        for s in ("BREAK_RETEST", "BOUNCE", "REJECTION"):
            l = sum(1 for r in sd if r["setup"] == s and r["side"] == "LONG"); sh = sum(1 for r in sd if r["setup"] == s and r["side"] == "SHORT")
            md.append(f"| {s} | {l} | {sh} | {l+sh} |\n")
        md.append(f"| all | {sum(1 for r in sd if r['side']=='LONG')} | {sum(1 for r in sd if r['side']=='SHORT')} | {len(sd)} |\n")
        tr_days = [r for r in sd if r["n_trades"]]
        md.append(f"\nSetup days with >=1 trade: {len(tr_days)} ({sum(r['n_trades'] for r in tr_days)} trades); setup days with no trade: {len(sd)-len(tr_days)}.\n")
        for s in ("BREAK_RETEST", "BOUNCE+REJECTION"):
            grp = [r for r in sd if (r["setup"] == "BREAK_RETEST") == (s == "BREAK_RETEST")]
            cc = Counter(r["stage"] for r in grp)
            md.append(f"\n### Blocking stage, {s}: {len(grp)} setup days\n\nEach day gets the DEEPEST stage any candidate reached that day (valid entry outside the window is the deepest). TRADE = a trade happened. Sums to the setup days.\n\n| stage | days | % of these days |\n|---|---|---|\n")
            for k in sorted(cc): md.append(f"| {k} | {cc[k]} | {100*cc[k]/len(grp):.1f}% |\n")
        fv = [r for r in sd if r["first_valid_end"]]
        md.append(f"\n### Setup days where a valid entry candle exists at some time of day (first one per day): {len(fv)} of {len(sd)}\n\n| entry candle close | days |\n|---|---|\n")
        bk = Counter()
        for r in fv:
            h, m = map(int, r["first_valid_end"].split(":")); t = h * 60 + m; b = t - t % 30
            bk[f"{b//60:02d}:{b%60:02d}-{(b+30)//60:02d}:{(b+30)%60:02d}"] += 1
        for k in sorted(bk): md.append(f"| {k} | {bk[k]} |\n")
        inw = sum(1 for r in fv if r["first_valid_end"] <= "10:35")
        md.append(f"\nFirst valid entry closes at/before 10:35: {inw} days; after 10:35: {len(fv)-inw} days (after 12:00: {sum(1 for r in fv if r['first_valid_end']>'12:00')}).\n")
        md.append("\n### Distance 09:30 open to chosen level (points), and whether price reached it\n\nReached = some 1-minute bar's [low, high] contains the level (bars closing 09:31..10:35, or the whole day to 16:00).\n\n| setup | days | median | Q1 | Q3 | min | max | reached by 10:35 | reached by 16:00 |\n|---|---|---|---|---|---|---|---|---|\n")
        for s in ("BREAK_RETEST", "BOUNCE", "REJECTION", "all"):
            g = [r for r in sd if s == "all" or r["setup"] == s]
            if not g: continue
            d_ = [r["dist_open"] for r in g]
            a = sum(r["reached_1035"] for r in g); b = sum(r["reached_1600"] for r in g)
            md.append(f"| {s} | {len(g)} | {statistics.median(d_):.1f} | {pct(d_,.25):.1f} | {pct(d_,.75):.1f} | {min(d_):.1f} | {max(d_):.1f} | {a} ({100*a/len(g):.0f}%) | {b} ({100*b/len(g):.0f}%) |\n")
        md.append("\n### One-at-a-time relaxation (everything else default). Counts only.\n\nFull engine rules still apply (E1 2 attempts, E2 max 3/day, E3 stop after a win), so total entries can be above days.\n\n| setting | days with >=1 entry | total entries | note |\n|---|---|---|---|\n")
        for nme, _ in RELAX:
            pd = {d: k for d, k in rel[nme].items() if d in days}
            md.append(f"| {nme} | {len(pd)} | {sum(pd.values())} | {VALIDATED.get(nme,'')} |\n")
    open(os.path.join(OUT, "tables.md"), "w").write("".join(md))
    print("".join(md))


if __name__ == "__main__": main()
