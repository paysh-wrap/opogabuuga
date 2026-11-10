"""Step 3: a small fixed list of higher-win-rate ideas (structure-based, parameters fixed BEFORE looking at results, no grid-mining).
All causal: a signal uses only bars closed at or before the signal bar; entry = next bar open + 1 tick; stop = market + 1 tick slippage;
limit targets need a 1-tick trade-through; same-bar stop+target -> stop first; fee per micro RT. IS = 2021-11..2023-12, HO = 2024-01..2026-10.
rr = designed reward:risk of the target (rr < 1.5 = VIOLATES the user's R:R >= 1.5 rule -> reported in a separate table).
usage: S15_RAW=<raw folder> python3 candidates.py   (writes out/candidates.json + out/streams/*.csv)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import lib
from lib import INST, walk, days, START, END

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT + "/streams", exist_ok=True)


def rec(out, d, ek, xk, p, mae, risk, side):
    out.append(dict(d=d, ek=ek, xk=xk, pnl=p, mae=mae, risk=risk, side=side))


# ---------------------------------------------------------------- C2: VWAP reversion with trend filter (RTH)
def vwap_rev(sym, rr, z=2.0, win=(60, 330), var=""):
    """Bar-close at minute k in [60,330] (10:30-15:00): sd = std(close - vwap) of the session so far (>= 30 bars). Price > vwap + z*sd AND day still below the prior
    close (so the stretch is against the day's direction)... NO: trend filter = trade WITH the day trend: long when price < vwap - z*sd and price > prior close
    (dip inside an up day); short when price > vwap + z*sd and price < prior close.  target = VWAP at signal time, stop = distance/rr beyond entry. One trade/day, flat 15:55."""
    I = INST[sym]; tk = I["tick"]
    D, nb = days(sym); out = []
    for i in range(14, len(D)):
        d, a = D[i]
        if d < START or d > END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        pc = D[i - 1][1]["close"][nb - 1]
        if np.isnan(pc): continue
        for k in range(win[0], win[1]):
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = 1 if (c[k] < vw[k] - z * sd and c[k] > pc) else (-1 if (c[k] > vw[k] + z * sd and c[k] < pc) else 0)
            if not s or np.isnan(o[k + 1]): continue
            e = o[k + 1] + s * tk
            dist = (vw[k] - e) * s
            if dist < 8 * tk: continue
            stop_pts = dist / rr
            p, xk, mae, risk = walk(a, s, k + 1, stop_pts, None, 386, sym, tgt_px=vw[k])
            rec(out, d, k + 1, xk, p, mae, risk, s); break
    return pd.DataFrame(out)


# ---------------------------------------------------------------- C3: opening-range failure fade
def or_fail(sym, mode, or_min=15, win_after=20, last=120):
    """OR = first or_min minutes. After the OR, a 1-min bar that closes beyond the OR extreme by >= 1 tick (break); if within win_after bars a later bar CLOSES back
    inside the OR -> fade (signal at that close, entry next open). stop = extreme of the failed break + 1 tick, target: mode 'rr15' = 1.5 x risk, 'mid' = OR midpoint.
    Skip if risk < 0.04% of price. One trade/day, signals until minute `last` (11:30), flat 15:55."""
    I = INST[sym]; tk = I["tick"]
    D, nb = days(sym); out = []
    for d, a in D:
        if d < START or d > END: continue
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        if np.isnan(c[:or_min]).any(): continue
        oh, ol = np.nanmax(h[:or_min]), np.nanmin(l[:or_min])
        brk = None; ext = None
        for k in range(or_min, last):
            if np.isnan(c[k]): continue
            if brk is None:
                if c[k] >= oh + tk: brk, ext, k0 = 1, h[k], k
                elif c[k] <= ol - tk: brk, ext, k0 = -1, l[k], k
                continue
            ext = max(ext, h[k]) if brk > 0 else min(ext, l[k])
            if k - k0 > win_after: break
            if (brk > 0 and c[k] < oh) or (brk < 0 and c[k] > ol):
                s = -brk
                if np.isnan(o[k + 1]): break
                e = o[k + 1] + s * tk
                stop_pts = abs(ext - e) + tk
                if stop_pts < 0.0004 * e: break
                if mode == "rr15":
                    p, xk, mae, risk = walk(a, s, k + 1, stop_pts, 1.5 * stop_pts, 386, sym)
                else:
                    mid = (oh + ol) / 2
                    if (mid - e) * s < 4 * tk: break
                    p, xk, mae, risk = walk(a, s, k + 1, stop_pts, None, 386, sym, tgt_px=mid)
                rec(out, d, k + 1, xk, p, mae, risk, s); break
    return pd.DataFrame(out)


# ---------------------------------------------------------------- C4: overnight gap fill
def gap_fill(sym, rr, gmin=0.0015, gmax=0.01, k0=5):
    """gap = RTH open (09:30) vs prior RTH close. Only gaps in [0.15%, 1.0%]. Signal at the close of minute k0-1 (09:34) -> entry 09:35 open, FADE toward the prior close
    (gap up -> short). target = prior close (limit), stop = remaining distance / rr beyond entry. Skip if the first 5 minutes already filled >= 50% of the gap. Flat 15:55."""
    I = INST[sym]; tk = I["tick"]
    D, nb = days(sym); out = []
    for i in range(1, len(D)):
        d, a = D[i]
        if d < START or d > END: continue
        o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        pc = D[i - 1][1]["close"][nb - 1]
        if np.isnan(pc) or np.isnan(o[0]) or np.isnan(c[k0 - 1]) or np.isnan(o[k0]): continue
        g = o[0] / pc - 1
        if not (gmin <= abs(g) <= gmax): continue
        s = -1 if g > 0 else 1
        if (c[k0 - 1] - pc) * (-s) < 0.5 * (o[0] - pc) * (-s): continue   # >= 50% filled already
        e = o[k0] + s * tk
        dist = (pc - e) * s
        if dist < 8 * tk: continue
        p, xk, mae, risk = walk(a, s, k0, dist / rr, None, 386, sym, tgt_px=pc)
        rec(out, d, k0, xk, p, mae, risk, s)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- C5: MGC overnight-VWAP reversion at the NY open
def mgc_session_rev(rr, dev_adr=0.5, adr_n=20):
    """MGC (gold) 1-min bars. Overnight session = 18:00 ET (prior day) .. 09:29 ET; its VWAP is known at 09:29. At 09:30 if price (09:29 close) is more than
    dev_adr x ADR(20 sessions of the 18:00-17:00 range) away from the overnight VWAP -> fade back toward it at the 09:30 open. target = overnight VWAP (limit),
    stop = distance/rr. Flat 15:55 ET (bar 09:30 + 385)."""
    I = INST["MGC"]; tk = I["tick"]
    df = pd.read_csv(f"{lib.RAW}/{I['csv']}", parse_dates=["timestamp"]).set_index("timestamp")
    df.index = df.index.tz_convert("America/New_York")
    df["sess"] = (df.index + pd.Timedelta(hours=6)).date          # 18:00 ET starts the next session date
    rng = df.groupby("sess").agg(hi=("high", "max"), lo=("low", "min"))
    adr = (rng.hi - rng.lo).rolling(adr_n).mean().shift(1)
    out = []
    for sess, g in df.groupby("sess"):
        if str(sess) < START or str(sess) > END or sess not in adr.index or np.isnan(adr[sess]): continue
        on = g.between_time("18:00", "09:29") if False else g[(g.index.hour >= 18) | (g.index.hour < 9) | ((g.index.hour == 9) & (g.index.minute < 30))]
        rth = g.between_time("09:30", "15:59")
        if len(on) < 200 or len(rth) < 300 or rth.index[0].strftime("%H:%M") != "09:30": continue
        tp = (on.high + on.low + on.close) / 3
        ovw = float((tp * on.volume).sum() / max(on.volume.sum(), 1))
        px = float(on.close.iloc[-1])
        dev = px - ovw
        if abs(dev) < dev_adr * adr[sess]: continue
        s = -1 if dev > 0 else 1
        a = dict(open=rth.open.values, high=rth.high.values, low=rth.low.values, close=rth.close.values)
        n = len(rth)
        e = a["open"][0] + s * tk
        dist = (ovw - e) * s
        if dist < 10 * tk: continue
        p, xk, mae, risk = walk(a, s, 0, dist / rr, None, min(n, 386), "MGC", tgt_px=ovw)
        rec(out, str(sess), 0, xk, p, mae, risk, s)
    return pd.DataFrame(out)


def main():
    C = []
    def add(name, sym, rr, note, t):
        C.append((name, sym, rr, note, t))
    nz = lib.noise_stream("MNQ")
    add("N0 NOISE baseline (MNQ, $250 stop, hourly band/VWAP exit)", "MNQ", None, "reference (no fixed target)", nz)
    add("N1 NOISE + profit lock (+100 pt -> stop entry+10 pt)", "MNQ", None, "D75-P1 (trail-type; no target <1.5R)", lib.noise_stream("MNQ", lock=(100, 10)))
    add("N2 NOISE + scale-out half at +1R then breakeven", "MNQ", 1.0, "partial target 1R < 1.5R", lib.noise_stream("MNQ", scale=(0.5, 1.0)))
    add("N3 NOISE + scale-out half at +0.5R then breakeven", "MNQ", 0.5, "partial target 0.5R < 1.5R", lib.noise_stream("MNQ", scale=(0.5, 0.5)))
    for sym in ("MNQ", "MES"):
        add(f"V1 VWAP-reversion +trend filter, R:R 1.5 ({sym})", sym, 1.5, "target = VWAP, stop = dist/1.5", vwap_rev(sym, 1.5))
        add(f"V2 VWAP-reversion +trend filter, R:R 0.67 ({sym})", sym, 0.67, "stop = 1.5 x dist", vwap_rev(sym, 0.67))
        add(f"O1 Opening-range failure fade, target 1.5R ({sym})", sym, 1.5, "OR 15 min, fade failed break", or_fail(sym, "rr15"))
        add(f"O2 Opening-range failure fade, target OR midpoint ({sym})", sym, None, "R:R depends on the trade (usually < 1.5)", or_fail(sym, "mid"))
        add(f"G1 Overnight gap fill, R:R 1.5 ({sym})", sym, 1.5, "fade gap toward prior close", gap_fill(sym, 1.5))
        add(f"G2 Overnight gap fill, R:R 0.67 ({sym})", sym, 0.67, "stop = 1.5 x remaining gap", gap_fill(sym, 0.67))
    if os.path.exists(f"{lib.RAW}/mgc_5y.csv"):
        add("M1 MGC overnight-VWAP reversion at NY open, R:R 1.5", "MGC", 1.5, "", mgc_session_rev(1.5))
        add("M2 MGC overnight-VWAP reversion at NY open, R:R 0.67", "MGC", 0.67, "", mgc_session_rev(0.67))
    rows = []
    for name, sym, rr, note, t in C:
        if len(t) == 0:
            print("EMPTY", name); continue
        key = name.split()[0] + "_" + sym
        t.to_csv(f"{OUT}/streams/{key}.csv", index=False)
        r = dict(name=name, sym=sym, rr=rr, note=note, key=key)
        for e in ("IS", "HO", "ALL"): r[e] = lib.stream_stats(t, e)
        rows.append(r)
        print(f"{name:62s} IS n={r['IS']['n']:4d} win={r['IS']['win']:5.1f} PF={r['IS']['pf']:.2f} ${r['IS']['profit']:8.0f} | HO n={r['HO']['n']:4d} win={r['HO']['win']:5.1f} PF={r['HO']['pf']:.2f} ${r['HO']['profit']:8.0f}", flush=True)
    json.dump(rows, open(f"{OUT}/candidates.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
