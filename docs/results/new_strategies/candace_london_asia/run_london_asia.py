"""London / Asia / overnight simulation, last ~30 days of MNQ=F 1-minute bars from OpenBB (yfinance provider, keyless).
Engines UNCHANGED, default configs (no tuning): candace_ict.replay_day (NY + LONDON on) and jj_fpt.replay (NY, 6PM, ASIA).
Run: cd backend && ../.venv/bin/python ../docs/results/new_strategies/candace_london_asia/run_london_asia.py
Raw bars are cached in bars_mnq_1m.csv (real bars only, nothing interpolated)."""
import os, sys, csv, math
from datetime import datetime, timedelta, date, time
from decimal import Decimal as D
from zoneinfo import ZoneInfo
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
TICK, TV, PV, FEE = D("0.25"), D("0.5"), D("2"), D("2")   # MNQ: $2/pt, $2 round trip per micro, no extra slippage (user spec)
RISK = D("158.33")                                        # Lucid fit 25K (docs: BRUNI/CANDACE table; = D143 JJ min())
RAW = os.path.join(HERE, "bars_mnq_1m.csv")

def download():
    """OpenBB's yfinance provider hard-codes period=5d for 1m (only ~5 days) and 58d for 2m+, so for 30 days of REAL 1-minute
    bars we call the same keyless library OpenBB wraps (yfinance) directly, in 7-day requests (Yahoo: max 8 days per 1m request,
    ~30 days of history). No keys, no interpolation."""
    import yfinance as yf
    parts = []; s = datetime(2026, 10, 19); end = datetime(2026, 11, 17)
    while s < end:
        e = min(s + timedelta(days=7), end)
        df = yf.download("MNQ=F", start=s.date().isoformat(), end=e.date().isoformat(), interval="1m", prepost=True, progress=False, auto_adjust=False)
        df.columns = [c[0].lower() for c in df.columns]
        print("chunk", s.date(), e.date(), len(df)); parts.append(df.tz_convert(ET).tz_localize(None)); s = e
    df = pd.concat(parts); df = df[~df.index.duplicated()].sort_index()
    df = df[["open", "high", "low", "close", "volume"]]; df.to_csv(RAW, index_label="et_open_naive")
    return df

def load():
    if not os.path.exists(RAW): download()
    df = pd.read_csv(RAW, parse_dates=["et_open_naive"], index_col="et_open_naive")
    idx = df.index.tz_localize(ET, ambiguous="infer", nonexistent="shift_forward")   # naive ET wall clock -> aware
    df.index = idx
    return df

from app.engine import candace_ict, jj_fpt as JJ
from app.engine.candace_ict import MBar
from app.config import CandaceIctCfg, JjFptCfg
from app.engine.lucid_fit import contracts_for, grade_contracts

def mbars(df): return [MBar(t + timedelta(minutes=1), D(str(r.open)), D(str(r.high)), D(str(r.low)), D(str(r.close)), D(str(r.volume))) for t, r in df.iterrows()]
def jbars(df): return [JJ.JBar(t + timedelta(minutes=1), D(str(r.open)), D(str(r.high)), D(str(r.low)), D(str(r.close))) for t, r in df.iterrows()]
def at(d, hh, mm=0): return datetime.combine(d, time(hh, mm), tzinfo=ET)

def money(pts, n): return float(n * (D(str(pts)) * PV - FEE))

def main():
    df = load(); days = sorted({t.date() for t in df.index}); rows = []; cov = []
    ccfg = CandaceIctCfg(london=True)
    jcfg = JjFptCfg()
    for d in days:
        if d.weekday() >= 5: continue
        day = df[(df.index >= at(d, 0)) & (df.index < at(d, 17))]
        n_l = int(((day.index >= at(d, 2)) & (day.index < at(d, 5))).sum()); n_n = int(((day.index >= at(d, 9)) & (day.index < at(d, 10))).sum())
        cov.append((d, len(day), n_l, n_n, int(((df.index >= at(d - timedelta(days=1), 18)) & (df.index < at(d, 0))).sum())))
        if n_l == 0 and n_n == 0: continue
        # ---- CANDACE: history = up to 3 prior days' bars until 17:00 ET, today = 00:00-17:00 ET (overnight included)
        hist = df[(df.index >= at(d - timedelta(days=4), 0)) & (df.index < at(d, 0))]
        hist = hist[[t.time() < time(17) for t in hist.index]]
        sigs = candace_ict.replay_day(mbars(hist), mbars(day), ccfg, TICK).signals
        for s in sigs:
            oc, xp, xt = s.outcome, s.exit_price, s.exit_time
            if oc == "OPEN" or xp is None: oc, xp, xt = "MTM", day.iloc[-1].close, None; xp = D(str(xp))
            sg = s.direction.sign; pts = (xp - s.entry) * sg; sp = abs(s.entry - s.stop)
            c = contracts_for(RISK, sp, TICK, TV, FEE, 0); c2 = grade_contracts(c, s.size_mult)
            rows.append(dict(strategy="CANDACE", session=s.session, day=d, time=s.time.astimezone(ET).strftime("%H:%M"), dir=s.direction.name, kind=s.swept.kind + "/" + s.grade,
                             entry=float(s.entry), stop_pts=float(sp), exit=oc, pts=float(pts), micros_1=1, usd_1micro=money(pts, 1), micros_fit=c2, usd_fit=money(pts, c2), conf="+".join(s.confluences)))
        # ---- JJ F.P.T: NY (no news calendar -> news_fair None), 6PM and ASIA of this evening
        for name, hh, end_dt in (("NY", 9, at(d, 16, 44)), ("6PM", 18, at(d + timedelta(days=1), 16, 44)), ("ASIA", 20, at(d + timedelta(days=1), 16, 44))):
            op = at(d, hh, 30 if name == "NY" else 0)
            seg = df[(df.index >= op - timedelta(minutes=30)) & (df.index < end_dt)]
            if (seg.index == op).sum() == 0: cov.append((d, f"{name} open bar MISSING")); continue
            jb = jbars(seg); start = [i for i, t in enumerate(seg.index) if t == op][0]
            def last_close_before(t):
                x = df[df.index < t]; return None if x.empty else D(str(x.iloc[-1].close))
            first = jb[start]
            ref = last_close_before(op - timedelta(hours=jcfg.htf_hours)); htf = JJ.htf_bias(first.o, ref)
            if name == "NY": si = JJ.SessionInput("NY", op, htf_bias=htf)
            elif name == "6PM": si = JJ.SessionInput("6PM", op, htf_bias=htf, gap_prior_close=last_close_before(at(d, 17)))
            else:
                six = df[df.index == at(d, 18)]; si = JJ.SessionInput("ASIA", op, htf_bias=htf, alt_fair=None if six.empty else D(str(six.iloc[0].open)))
            rp = JJ.replay(jb, start, si, jcfg)
            for s in rp.signals:
                if s.outcome == "WIN": pts, oc = s.target_pts, "TP"
                elif s.outcome == "LOSS": pts, oc = -s.stop_pts, "STOP"
                else: pts, oc = (jb[-1].c - s.entry) * s.direction.sign, "MTM"
                c = contracts_for(RISK, s.stop_pts, TICK, TV, FEE, 0)
                rows.append(dict(strategy="JJ_FPT", session=name, day=d, time=s.at.astimezone(ET).strftime("%H:%M"), dir=s.direction.name, kind=s.kind + "/" + s.tier, entry=float(s.entry),
                                 stop_pts=float(s.stop_pts), exit=oc, pts=float(pts), micros_1=1, usd_1micro=money(pts, 1), micros_fit=c, usd_fit=money(pts, c), conf=""))
    cols = list(rows[0].keys()) if rows else []
    with open(os.path.join(HERE, "trades_all.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); [w.writerow(r) for r in rows]
    with open(os.path.join(HERE, "coverage.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["day", "bars_00-17", "bars_london_02-05", "bars_ny_09-10", "bars_evening_18-24_prev"]); [w.writerow(c) for c in cov]
    out = pd.DataFrame(rows); lines = ["| strategy | session | trades | win % | PF | pts | $ (1 micro, $2 RT cost) | $ (Lucid-fit size) | MTM/unresolved |", "|---|---|---|---|---|---|---|---|---|"]
    for (st, se), g in out.groupby(["strategy", "session"]):
        w = g[g.usd_1micro > 0]; l = g[g.usd_1micro <= 0]
        pf = w.usd_1micro.sum() / abs(l.usd_1micro.sum()) if abs(l.usd_1micro.sum()) > 0 else float("inf")
        lines.append(f"| {st} | {se} | {len(g)} | {100*len(w)/len(g):.0f} | {pf:.2f} | {g.pts.sum():+.1f} | {g.usd_1micro.sum():+.0f} | {g.usd_fit.sum():+.0f} | {(g.exit=='MTM').sum()} |")
    open(os.path.join(HERE, "summary_table.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines)); print("days:", len(cov), "first", days[0], "last", days[-1], "bars", len(df))

if __name__ == "__main__": main()
