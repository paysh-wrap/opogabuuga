"""MGC session-structure research (agent 'gold'). Usage: python gold.py
Reads scratchpad/data/mgc_1m.csv (never modified), caches parquet here, prints tables, writes trades.csv.
Protocol: closed 1m bars, market entries at next bar open (+1 tick slip), stop-entries fill only when price
trades 1 tick THROUGH the level (+1 tick slip), limit targets fill only when traded through by 1 tick (no slip),
stop exits -1 tick slip, stop-first on same-bar touch, flat 16:40 ET, fee $1.60 RT, tick 0.10 = $1.00.
"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "data", "mgc_1m.csv")
PQ = os.path.join(HERE, "mgc_1m.parquet")
TICK, TV, FEE = 0.10, 1.0, 1.60  # $ per tick; MGC $10/pt
PT = TV / TICK


def load():
    if os.path.exists(PQ) and os.path.getmtime(PQ) > os.path.getmtime(DATA):
        return pd.read_parquet(PQ)
    df = pd.read_csv(DATA)
    ts = pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
    df["ts"] = ts.dt.tz_localize(None)
    df = df.drop(columns="timestamp").drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    # session day: bars at/after 18:00 ET belong to the next day
    df["sday"] = (df.ts + pd.Timedelta(hours=6)).dt.normalize()
    df["mins"] = df.ts.dt.hour * 60 + df.ts.dt.minute  # minutes since ET midnight
    df.to_parquet(PQ)
    return df


def m(h, mi=0):
    return h * 60 + mi


def daily_features(df):
    g = df.groupby("sday")
    d = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(), "c": g.close.last()})
    d["gap"] = (d.o / d.c.shift(1) - 1).abs()
    d["roll"] = d.gap > 0.015
    d["rng"] = d.h - d.l                       # H-L only: no gap, so no roll contamination
    d["atr"] = d.rng.rolling(14).mean().shift(1)  # prior 14 days, known at open
    # 20-day trend on prior closes using intraday returns (c/o) so roll gaps do not leak; unknown if roll inside
    r = np.log(d.c / d.o)
    d["tr20"] = r.rolling(20).sum().shift(1)
    d["roll20"] = d.roll.astype(int).rolling(20).sum().shift(1) > 0
    d["trend"] = np.sign(d.tr20)
    # plain close-to-close 20d (known only if no roll in window)
    d["trend_cc"] = np.where(d.roll20, np.nan, np.sign(d.c.shift(1) - d.c.shift(21)))
    return d


def sim(bars, i0, side, entry, stop, target, t_exit, entry_kind):
    """Simulate from bar index i0 (entry bar). entry_kind 'mkt' (fill=open of i0) or ('stop', level).
    bars: dict of numpy arrays for one day. Returns (exit_px, entry_px, reason) or None if no fill."""
    o, h, l, c, mins = bars["o"], bars["h"], bars["l"], bars["c"], bars["mins"]
    n = len(o)
    if entry_kind == "mkt":
        ep = o[i0] + side * TICK
    else:
        ep = entry + side * TICK  # entry here is already level+1tick fill; add slip
    i = i0
    first = True
    while i < n:
        if mins[i] >= t_exit:
            return c[i - 1] - side * TICK if i > i0 else o[i] - side * TICK, ep, "TIME"
        hi, lo = h[i], l[i]
        if side > 0:
            hs = lo <= stop
            ht = target is not None and hi >= target + TICK
        else:
            hs = hi >= stop
            ht = target is not None and lo <= target - TICK
        if first and entry_kind != "mkt":
            # on fill bar, can't know order of fill vs target; allow stop, disallow target unless close beyond
            ht = ht and ((c[i] > target) if side > 0 else (c[i] < target))
        if hs:
            px = stop if not (first and entry_kind == "mkt") else stop
            # gap through stop at open
            if side > 0 and o[i] < stop and not first: px = o[i]
            if side < 0 and o[i] > stop and not first: px = o[i]
            return px - side * TICK, ep, "STOP"
        if ht:
            return target, ep, "TP"
        first = False
        i += 1
    return c[n - 1] - side * TICK, ep, "EOD"


def run_strategy(df, d, gen, name, cap=3):
    out = []
    for sday, day in df.groupby("sday", sort=True):
        if sday not in d.index:
            continue
        f = d.loc[sday]
        bars = {k: day[v].to_numpy() for k, v in
                [("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("mins", "mins")]}
        bars["v"] = day.volume.to_numpy()
        bars["ts"] = day.ts.to_numpy()
        # normalize mins: evening bars (>=18:00) -> negative so time runs monotonic within session
        mm = bars["mins"].copy(); mm[mm >= m(18)] -= 1440; bars["mins"] = mm
        busy_until = -10**9; k = 0
        for sig in gen(bars, f):
            if k >= cap:
                break
            i0, side, entry, stop, target, t_exit, kind = sig
            if bars["mins"][i0] < busy_until:
                continue
            if side * (entry if kind != "mkt" else bars["o"][i0]) <= side * stop:
                continue
            r = sim(bars, i0, side, entry, stop, target, min(t_exit, m(16, 40)), kind)
            if r is None:
                continue
            xp, ep, why = r
            risk = abs(ep - stop) * PT
            if risk <= 0:
                continue
            pnl = side * (xp - ep) * PT - FEE
            out.append(dict(strat=name, sday=sday, side=side, ep=ep, stop=stop, xp=xp, why=why,
                            risk=risk, pnl=pnl, R=pnl / risk, trend=f.trend, roll=f.roll))
            k += 1
            busy_until = 10**9  # one position per day per strategy (all strategies here are 1/day)
    return pd.DataFrame(out)


def rng(bars, a, b):
    s = (bars["mins"] >= a) & (bars["mins"] < b)
    if s.sum() < (b - a) * 0.5:
        return None
    return bars["h"][s].max(), bars["l"][s].min(), np.nonzero(s)[0][-1]


def first_break(bars, hi, lo, a, b, i_from):
    """first bar in [a,b) after i_from trading 1 tick through hi/lo. returns (i, side)."""
    mins, h, l = bars["mins"], bars["h"], bars["l"]
    for i in range(i_from + 1, len(mins)):
        if mins[i] >= b:
            return None
        if mins[i] < a:
            continue
        up, dn = h[i] >= hi + TICK, l[i] <= lo - TICK
        if up and dn:
            return None
        if up: return i, 1
        if dn: return i, -1
    return None


def tgt(ep, stop, side, R):
    return None if R is None else round((ep + side * R * abs(ep - stop)) / TICK) * TICK


# ---------- generators ----------
def g_breakout(ra, rb, wa, wb, R, stopmode="opp", t_exit=m(11, 30), stopatr=None):
    def gen(bars, f):
        r = rng(bars, ra, rb)
        if r is None: return
        hi, lo, il = r
        b = first_break(bars, hi, lo, wa, wb, il)
        if b is None: return
        i, side = b
        lvl = hi + TICK if side > 0 else lo - TICK
        if stopatr is not None:
            if np.isnan(f.atr): return
            stop = lvl - side * stopatr * f.atr
        elif stopmode == "opp":
            stop = lo - TICK if side > 0 else hi + TICK
        else:
            stop = (hi + lo) / 2
        stop = round(stop / TICK) * TICK
        ep = lvl + side * TICK
        yield i, side, lvl, stop, tgt(ep, stop, side, R), t_exit, "stop"
    return gen


def g_sweep(ra, rb, wa, wb, R, t_exit=m(11, 30), tf=5):
    """price trades beyond Asian high/low, then a tf-min bar closes back inside -> reverse at next open."""
    def gen(bars, f):
        r = rng(bars, ra, rb)
        if r is None: return
        hi, lo, il = r
        mins, h, l, c = bars["mins"], bars["h"], bars["l"], bars["c"]
        ext_hi, ext_lo, swept = hi, lo, 0
        for i in range(il + 1, len(mins) - 1):
            if mins[i] >= wb: return
            if mins[i] < wa: continue
            if h[i] >= hi + TICK and swept >= 0: swept = 1; ext_hi = max(ext_hi, h[i])
            if l[i] <= lo - TICK and swept <= 0: swept = -1 if swept == 0 else swept; ext_lo = min(ext_lo, l[i])
            if swept == 1: ext_hi = max(ext_hi, h[i])
            if swept == -1: ext_lo = min(ext_lo, l[i])
            if (mins[i] + 1) % tf != 0: continue  # tf-bar close
            if swept == 1 and c[i] < hi:
                side, stop = -1, ext_hi + TICK
            elif swept == -1 and c[i] > lo:
                side, stop = 1, ext_lo - TICK
            else:
                continue
            ep = bars["o"][i + 1] + side * TICK
            if R == "opp":
                t = lo if side < 0 else hi
                t = min(abs(t - ep), 3 * abs(ep - stop))
                target = round((ep + side * t) / TICK) * TICK
            else:
                target = tgt(ep, stop, side, R)
            yield i + 1, side, None, stop, target, t_exit, "mkt"
            return
    return gen


def vwap_arr(bars, a):
    s = bars["mins"] >= a
    tp = (bars["h"] + bars["l"] + bars["c"]) / 3 * bars["v"] * s
    vv = np.cumsum(bars["v"] * s)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.cumsum(tp) / vv


def g_trend_pullback(k, R, t_exit=m(16, 40), stopk=0.25):
    """move 08:20 open -> 10:00 close > k*ATR: limit at 08:20-anchored VWAP (10:00-13:00), stop stopk*ATR."""
    def gen(bars, f):
        if np.isnan(f.atr): return
        mins = bars["mins"]
        i_open = np.nonzero(mins >= m(8, 20))[0]
        i_10 = np.nonzero(mins < m(10))[0]
        if len(i_open) == 0 or len(i_10) == 0: return
        a, b = i_open[0], i_10[-1]
        if b <= a: return
        mv = bars["c"][b] - bars["o"][a]
        if abs(mv) < k * f.atr: return
        side = int(np.sign(mv))
        vw = vwap_arr(bars, m(8, 20))
        for i in range(b + 1, len(mins)):
            if mins[i] >= m(13): return
            lvl = round(vw[i - 1] / TICK) * TICK  # VWAP known at prior close
            touched = bars["l"][i] <= lvl - TICK if side > 0 else bars["h"][i] >= lvl + TICK
            if touched:
                stop = round((lvl - side * stopk * f.atr) / TICK) * TICK
                # limit fill: no slip -> pass entry so sim adds 1 tick; compensate
                yield i, side, lvl - side * TICK, stop, tgt(lvl, stop, side, R), t_exit, "stop"
                return
    return gen


def g_fade(k, t_exit=m(11, 30), stopk=0.25):
    """10:00-11:30: 1m close deviates > k*ATR from session (08:20) VWAP -> fade at next open, target VWAP
    at signal time, stop stopk*ATR beyond entry."""
    def gen(bars, f):
        if np.isnan(f.atr): return
        mins, c = bars["mins"], bars["c"]
        vw = vwap_arr(bars, m(8, 20))
        for i in range(len(mins) - 1):
            if mins[i] < m(10): continue
            if mins[i] >= m(11, 30): return
            dev = c[i] - vw[i]
            if abs(dev) > k * f.atr:
                side = -int(np.sign(dev))
                ep = bars["o"][i + 1] + side * TICK
                stop = round((ep - side * stopk * f.atr) / TICK) * TICK
                target = round(vw[i] / TICK) * TICK
                if side * (target - ep) <= 0: return
                yield i + 1, side, None, stop, target, t_exit, "mkt"
                return
    return gen


def filt_trend(gen, col="trend"):
    def g(bars, f):
        for s in gen(bars, f):
            if not np.isnan(f[col]) and s[1] == f[col] and not f.roll:
                yield s
    return g


def variants():
    V = {}
    A0, A1, L0, L1 = m(-6), m(2), m(2), m(5)   # Asian 18:00-02:00 (prev evening = negative)
    for R in (1.5, 2, 3):
        V[f"A_asia_bo_opp_{R}R"] = g_breakout(A0, A1, L0, L1, R)
    V["A_asia_bo_mid_2R"] = g_breakout(A0, A1, L0, L1, 2, "mid")
    for R in (1.5, 2, "opp"):
        V[f"B_asia_sweep_rev_{R}"] = g_sweep(A0, A1, L0, L1, R)
    for R in (1.5, 2):
        V[f"C_ldn_orb_{R}R"] = g_breakout(m(3), m(3, 30), m(3, 30), m(6), R)
    for orm in (5, 15, 30):
        for R in (1.5, 2, 2.5, 3):
            V[f"D_comex_orb{orm}_{R}R"] = g_breakout(m(8, 20), m(8, 20 + orm), m(8, 20 + orm), m(11, 30), R)
        V[f"D_comex_orb{orm}_x1130"] = g_breakout(m(8, 20), m(8, 20 + orm), m(8, 20 + orm), m(11, 30), None)
        V[f"D_comex_orb{orm}_x1640"] = g_breakout(m(8, 20), m(8, 20 + orm), m(8, 20 + orm), m(11, 30), None,
                                                  t_exit=m(16, 40))
    V["D_comex_orb15_atr.25_2R"] = g_breakout(m(8, 20), m(8, 35), m(8, 35), m(11, 30), 2, stopatr=0.25)
    for k in (0.3, 0.5):
        V[f"E_trend_pb_k{k}_2R"] = g_trend_pullback(k, 2)
    for k in (0.3, 0.5):
        V[f"F_fade_k{k}_vwap"] = g_fade(k)
    return V


def stats(t):
    if len(t) == 0:
        return dict(trades=0)
    w = t[t.pnl > 0]; lo = t[t.pnl <= 0]
    eq = t.R.cumsum(); dd = (eq.cummax() - eq).max()
    s = (t.pnl <= 0).astype(int).to_numpy(); ws = cur = 0
    for x in s:
        cur = cur + 1 if x else 0; ws = max(ws, cur)
    days = t.sday.nunique()
    return dict(trades=len(t), tpd=round(len(t) / max(days, 1), 2), win=round(100 * len(w) / len(t), 1),
                avgW=round(w.R.mean(), 2) if len(w) else 0, avgL=round(lo.R.mean(), 2) if len(lo) else 0,
                expR=round(t.R.mean(), 3), usd=round(t.pnl.mean(), 2),
                PF=round(w.pnl.sum() / -lo.pnl.sum(), 2) if lo.pnl.sum() < 0 else np.inf,
                ddR=round(dd, 1), streak=ws, tot=round(t.pnl.sum()))


def main():
    df = load()
    d = daily_features(df)
    print("days", len(d), "roll days", int(d.roll.sum()), df.ts.min(), df.ts.max())
    V = variants()
    print("variants", len(V) + 4)
    allt = []
    for name, g in V.items():
        allt.append(run_strategy(df, d, g, name))
    T = pd.concat(allt)
    IS = T.sday < "2024-01-01"
    rows = []
    for name, t in T.groupby("strat"):
        rows.append(dict(strat=name, per="IS", **stats(t[t.sday < "2024-01-01"])))
    R = pd.DataFrame(rows).sort_values("expR", ascending=False)
    print(R.to_string(index=False))
    # pick top 3 by IS expectancy (with >=200 IS trades), plus trend-filter versions
    picks = R[R.trades >= 200].head(3).strat.tolist()
    print("PICKS (IS only):", picks)
    extra = []
    for p in picks:
        for col in ("trend",):
            nm = p + "+tr20"
            extra.append(run_strategy(df, d, filt_trend(V[p], col), nm))
    # also trend filter on the most basic ORB15 2R regardless
    extra.append(run_strategy(df, d, filt_trend(V["D_comex_orb15_2R"]), "D_comex_orb15_2R+tr20"))
    T = pd.concat([T] + extra)
    T.to_csv(os.path.join(HERE, "trades.csv"), index=False)
    rows = []
    for name, t in T.groupby("strat"):
        for per, s in (("IS", t[t.sday < "2024-01-01"]), ("OOS", t[t.sday >= "2024-01-01"])):
            rows.append(dict(strat=name, per=per, **stats(s)))
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(HERE, "summary.csv"), index=False)
    print(R.to_string(index=False))
    for p in sorted(set(picks + [x + "+tr20" for x in picks] + ["D_comex_orb15_2R+tr20"])):
        t = T[T.strat == p]
        print("\nPER YEAR", p)
        print(pd.DataFrame([dict(year=y, **stats(s)) for y, s in t.groupby(t.sday.dt.year)]).to_string(index=False))
    # trend-direction stability per year: win of long-with-trend vs against for ORB15 2R
    t = T[T.strat == "D_comex_orb15_2R"]
    t = t.assign(with_tr=(t.side == t.trend))
    print("\nORB15 2R expR by year x with-trend")
    print(t.groupby([t.sday.dt.year, "with_tr"]).R.mean().unstack().round(3))


if __name__ == "__main__":
    main()
