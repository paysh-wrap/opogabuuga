"""(b) NOISE (engine/noise.py) and CANDACE (engine/candace_ict.py) on MGC and MNQ, 30 days of Yahoo 2-minute bars.
Engines are reused as is; only the bar size is 2 min instead of 1 min (noise: checks at 10:00,11:00.. exist on the 2-min grid;
candace: all bar-count parameters are in bars, so they now cover twice the time — flagged in RESULTS.md)."""
import itertools, json, sys
from datetime import timedelta, time
from decimal import Decimal as D
from types import SimpleNamespace
from lib import *
from app.engine import noise as N, candace_ict as CI
from app.engine.conti_orb import MBar
from app.engine.trade_plan import Direction


def sessions(df):
    out = {}
    for i, ts in enumerate(df.index):
        if not (time(9, 30) <= ts.time() < time(16, 0)): continue
        out.setdefault(ts.date(), []).append(i)
    return out


def noise_run(sym, stop_usd, lock, skip_mon, min_hist, lookback=14, check=60):
    df = load(sym); tick, tv, fee, slip = INST[sym]; pu, cu = pt_usd(sym), cost_usd(sym)
    ses = sessions(df); days = sorted(ses)
    O, H, L, C, V = (df[x].values for x in "ohlcv")
    sess_objs = {}
    for d in days:
        ix = ses[d]
        cl = {N.minute_index((df.index[i] + timedelta(minutes=2)).to_pydatetime()): D(str(C[i])) for i in ix}
        cl[0] = D(str(C[ix[0]]))  # k=0 (09:31 close) does not exist on a 2-min grid; only Session.complete() checks for it
        sess_objs[d] = N.Session(str(d), D(str(O[ix[0]])), cl)
    stop_pts = float(N.stop_pts_for_usd(D(stop_usd), D(str(tick)), D(str(tv)), D(str(fee)), slip))
    trades = []
    prev_close = None
    for di, d in enumerate(days):
        ix = ses[d]; s = sess_objs[d]
        hist = [sess_objs[x] for x in days[:di]]
        pc = hist[-1].last_close if hist else None
        if pc is None or len(ix) < 150: continue
        if not N.roll_guard(s.open, pc, D("0.015")): continue
        pos, entry, stop, i_in, lock_on, entries, locked_exit = None, None, None, None, False, 0, False
        for j in ix:
            k = N.minute_index((df.index[j] + timedelta(minutes=2)).to_pydatetime())
            # manage open position on this bar's range (stop / lock) before decisions on its close
            if pos is not None and j > i_in:
                sg = pos.sign
                if (L[j] <= stop) if sg > 0 else (H[j] >= stop):
                    trades.append(dict(day=str(d), sign=sg, i0=i_in, i1=j, entry=entry, stop_pts=stop_pts, why="STOP_LOCK" if lock_on else "STOP",
                                       usd=(stop - entry) * sg * pu - cu)); locked_exit = lock_on; pos = None
                elif lock and not lock_on and ((H[j] - entry) * sg >= lock[0] if sg > 0 else (entry - L[j]) >= lock[0]):
                    lock_on = True; stop = entry + sg * lock[1]
            check_bar = N.is_check(k, check, "10:00", "15:30")
            flat = k == N.hhmm_to_k("16:00")
            if not (check_bar or flat): continue
            sig = N.sigma(hist, k, lookback, min_hist, 150)
            if sig is None: continue
            b = N.bands(s.open, pc, sig)
            vw = N.vwap([(D(str(H[x])), D(str(L[x])), D(str(C[x])), D(str(V[x]))) for x in ix if x <= j])
            acts = N.decide(k=k, close=D(str(C[j])), b=b, vw=vw, position=pos, entries_today=entries, max_entries=3,
                            allow_entry=check_bar and not locked_exit and not (skip_mon and d.weekday() == 0))
            nxt = j + 1 if j + 1 <= ix[-1] else None
            for a in acts:
                if a.kind == "EXIT" and pos is not None:
                    px = float(O[nxt]) if (nxt and not flat) else float(C[j])
                    trades.append(dict(day=str(d), sign=pos.sign, i0=i_in, i1=(nxt - 1 if nxt and not flat else j), entry=entry,
                                       stop_pts=stop_pts, why=a.reason, usd=(px - entry) * pos.sign * pu - cu)); pos = None
                elif a.kind == "ENTER" and nxt:
                    pos = a.direction; entry = float(O[nxt]); i_in = nxt; entries += 1; lock_on = False
                    stop = entry - pos.sign * stop_pts
    # trades closed by stop need i1 = stop bar; baseline walks to i1 with stop only (lock ignored)
    return trades, df


def candace_run(sym, cfg_over, ):
    df = load(sym); tick, tv, fee, slip = INST[sym]; pu, cu = pt_usd(sym), cost_usd(sym)
    cfg = SimpleNamespace(ny_window="09:00-10:00", london_window="02:00-05:00", london=False, ny_max_stop_pts=D("40"),
        london_max_stop_pts=D("25"), ny_max_hold_minutes=15, london_max_hold_minutes=30, eq_tol_ticks=2, swing_lookback=2,
        displacement_mult=D("1.5"), displacement_bars=10, fvg_lookback=10, ifvg_max_bars=10, premium_pct=D("0.5"), range_bars=60,
        stop_buffer_ticks=2, min_rr=D("2"), gap_level_tol_pts=D("5"), grade_a_min=4, grade_b_min=3, max_losses_per_day=3, keep_all_sweeps=True)
    for k, v in cfg_over.items(): setattr(cfg, k, D(str(v)) if isinstance(v, float) else v)
    mb = [MBar((ts + timedelta(minutes=2)).to_pydatetime(), D(str(r.o)), D(str(r.h)), D(str(r.l)), D(str(r.c)), D(str(r.v))) for ts, r in df.iterrows()]
    pos_of = {m.close_time: i for i, m in enumerate(mb)}
    days = sorted({m.close_time.astimezone(CI.ET).date() for m in mb})
    trades = []
    for d in days:
        today = [m for m in mb if m.close_time.astimezone(CI.ET).date() == d]
        hist = [m for m in mb if m.close_time.astimezone(CI.ET).date() < d]
        for sgn in CI.replay_day(hist[-60 * 24:], today, cfg, D(str(tick))).signals:
            if sgn.outcome == "OPEN" or sgn.exit_price is None: continue
            sg = sgn.direction.sign; e = float(sgn.entry)
            i0 = pos_of[sgn.time] + 1; i1 = pos_of[sgn.exit_time]
            trades.append(dict(day=str(d), sign=sg, i0=i0, i1=max(i0, i1), entry=e, stop_pts=abs(e - float(sgn.stop)), tp_pts=abs(float(sgn.take_profit) - e),
                               why=sgn.outcome, grade=sgn.grade, usd=(float(sgn.exit_price) - e) * sg * pu - cu))
    return trades, df


def report(label, trades, df, sym):
    s = stats([t["usd"] for t in trades]); sh = sum(1 for t in trades if t["sign"] < 0)
    rb = random_baseline(trades, sym, df, draws=1000) if trades else {}
    return dict(label=label, **s, shorts=sh, **rb)


if __name__ == "__main__":
    OUT = {"noise": [], "candace": []}
    for sym in ("MGC", "MNQ"):
        px = float(load(sym).c.iloc[-1])
        lock_scaled = (round(100 * px / 26751, 1), round(10 * px / 26751, 1))
        stops = (250, 124) if sym == "MNQ" else (250, 100)
        for stop_usd, lock, mon, mh in itertools.product((stops[0], stops[1]), (None, (100, 10) if sym == "MNQ" else lock_scaled), (True, False), (10, 5)):
            tr, df = noise_run(sym, stop_usd, lock, mon, mh)
            r = report(f"{sym} NOISE stop${stop_usd} lock={lock} skipMon={mon} minhist={mh}", tr, df, sym); r.update(sym=sym, stop_usd=stop_usd, lock=lock, skip_mon=mon, min_hist=mh)
            OUT["noise"].append(r); print(r["label"], {k: r[k] for k in ("n", "win", "pf", "net", "shorts", "p_net") if k in r}, flush=True)
        # CANDACE variants (stop caps scaled by price vs the MNQ 40-pt cap = 0.15%)
        cap = 40 if sym == "MNQ" else 6
        for capm, hold, win in itertools.product((1, 2.5), (15, 30), ("09:00-10:00", "08:20-11:00")):
            over = dict(ny_max_stop_pts=cap * capm, ny_max_hold_minutes=hold, ny_window=win, gap_level_tol_pts=5 if sym == "MNQ" else 0.7)
            tr, df = candace_run(sym, over)
            r = report(f"{sym} CANDACE cap={cap*capm} hold={hold} win={win}", tr, df, sym); r.update(sym=sym, cap=cap * capm, hold=hold, window=win)
            OUT["candace"].append(r); print(r["label"], {k: r[k] for k in ("n", "win", "pf", "net", "shorts", "p_net") if k in r}, flush=True)
    json.dump(OUT, open(Path(__file__).resolve().parent.parent / "noise_candace_results.json", "w"), indent=1, default=str)
