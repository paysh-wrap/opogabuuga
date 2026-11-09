"""ORB family backtest (agent orb). Usage: python orb.py [mnq|mgc|all]
Rules fixed a priori (see results/orb.md). 1-min bars, NY time, no lookahead.
"""
import sys, os, math
import numpy as np, pandas as pd

D = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(D, "..", "..", "data")
SPEC = {"mnq": dict(tick=0.25, pv=2.0, fee=1.00, min_ticks=8),
        "mgc": dict(tick=0.10, pv=10.0, fee=1.60, min_ticks=5)}


def load(sym):
    pq = os.path.join(D, f"{sym}.parquet")
    if os.path.exists(pq):
        return pd.read_parquet(pq)
    df = pd.read_csv(os.path.join(DATA, f"{sym}_1m.csv"))
    ts = pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
    df["date"] = ts.dt.date.astype(str)
    df["mins"] = ts.dt.hour * 60 + ts.dt.minute
    df = df.drop(columns=["timestamp", "volume"])
    df.to_parquet(pq)
    return df


def daily_features(df, open_min):
    """Per calendar day: session (open_min..16:00) features + overnight range, known before open."""
    rth = df[(df.mins >= open_min) & (df.mins < 960)]
    g = rth.groupby("date")
    d = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(), "c": g.close.last()})
    d["rng"] = d.h - d.l
    d["roll"] = (d.o / d.c.shift(1) - 1).abs() > 0.015
    d["atr14"] = d.rng.shift(1).rolling(14).mean()
    sma = d.c.shift(1).rolling(20).mean()
    rolled20 = d.roll.astype(int).rolling(21).sum() > 0
    d["trend"] = np.where(rolled20 | sma.isna(), 0, np.sign(d.c.shift(1) - sma))
    d.loc[d.roll, "atr14"] = np.nan
    # overnight: 18:00 prev day .. open_min today -> use bars with mins<open_min on day + mins>=1080 of prev day
    on = df[(df.mins < open_min) | (df.mins >= 1080)].copy()
    dates = sorted(d.index)
    nxt = dict(zip(dates[:-1], dates[1:]))
    on["sd"] = np.where(on.mins >= 1080, on.date.map(nxt), on.date)
    og = on.dropna(subset=["sd"]).groupby("sd")
    d["on_rng"] = (og.high.max() - og.low.min()).reindex(d.index)
    return d


def run(df, feats, sym, v, open_min=570, entry_end=720, flat=1000):
    s = SPEC[sym]; tk = s["tick"]; pv = s["pv"]
    out = []
    orm = v.get("or", 5)
    for date, day in df[(df.mins >= open_min) & (df.mins < flat)].groupby("date", sort=True):
        if date not in feats.index:
            continue
        f = feats.loc[date]
        m = day.mins.values; o = day.open.values; h = day.high.values; l = day.low.values; c = day.close.values
        orb = m < open_min + orm
        if orb.sum() < orm * 0.8 or (~orb).sum() < 10 or m[0] != open_min:
            continue
        ORH, ORL = h[orb].max(), l[orb].min(); R0 = ORH - ORL
        if R0 <= 0:
            continue
        atr = f.atr14
        filt = v.get("filt")
        if filt:
            if pd.isna(atr):
                continue
            if filt == "narrow" and R0 >= 0.2 * math.sqrt(orm / 5) * atr: continue
            if filt == "on" and (pd.isna(f.on_rng) or f.on_rng > 0.75 * atr): continue
        allowed = {1, -1}
        if filt == "trend":
            if f.trend == 0: continue
            allowed = {int(f.trend)}
        i0 = int(np.argmax(~orb))
        trades = 0; i = i0; side_used = set()
        maxt = 3 if v.get("reverse") else 1
        if v["kind"] == "zar":
            fc_o, fc_c = o[orb][0], c[orb][-1]
            if fc_c == fc_o: continue
            side = 1 if fc_c > fc_o else -1
            if side not in allowed: continue
            entry = o[i0] + side * tk  # market entry, 1 tick slip
            stop = ORL if side == 1 else ORH
            if v.get("atrstop"):
                if pd.isna(atr): continue
                stop = o[i0] - side * 0.1 * atr
            pending = [(side, i0, entry, stop, True)]
        else:
            pending = None
        while trades < maxt:
            if v["kind"] == "zar":
                if not pending: break
                side, ei, entry, stop, _ = pending.pop()
            else:
                # resting stop entries both sides (filtered), fill when price trades through by 1 tick
                ei = None
                for j in range(i, len(m)):
                    if m[j] >= entry_end: break
                    hit_l = 1 in allowed and 1 not in side_used and h[j] >= ORH + tk
                    hit_s = -1 in allowed and -1 not in side_used and l[j] <= ORL - tk
                    if hit_l and hit_s: break  # ambiguous bar: skip day
                    if hit_l or hit_s:
                        side = 1 if hit_l else -1; ei = j; break
                if ei is None: break
                lvl = ORH if side == 1 else ORL
                entry = max(lvl + tk, o[ei]) if side == 1 else min(lvl - tk, o[ei])
                entry += side * tk  # slippage
                if v.get("atrstop"):
                    if pd.isna(atr): break
                    stop = entry - side * 0.1 * atr
                elif v.get("stop") == "half":
                    stop = (ORH + ORL) / 2
                else:
                    stop = ORL if side == 1 else ORH
            stop = (math.floor(stop / tk) * tk) if side == 1 else (math.ceil(stop / tk) * tk)
            risk = (entry - stop) * side
            if risk < s["min_ticks"] * tk:
                break
            tR = v["tgt"]
            tgt = entry + side * tR * risk if tR else None
            if tgt is not None:
                tgt = math.ceil(tgt / tk) * tk if side == -1 else math.floor(tgt / tk) * tk
            # walk forward; entry bar: stop checked (conservative), target from next bar
            xi = None; xp = None; why = "EOD"
            for j in range(ei, len(m)):
                sh = l[j] <= stop if side == 1 else h[j] >= stop
                if sh:
                    xp = stop - side * tk; xi = j; why = "STOP"; break
                if tgt is not None and j > ei:
                    th = h[j] >= tgt + tk if side == 1 else l[j] <= tgt - tk
                    if th: xp = tgt; xi = j; why = "TGT"; break
            if xi is None:
                xi = len(m) - 1; xp = c[xi] - side * tk
            pnl = (xp - entry) * side * pv - s["fee"]
            out.append(dict(date=date, side=side, R=pnl / (risk * pv), usd=pnl, why=why, rr=tR or 0))
            trades += 1; side_used.add(side)
            if v["kind"] == "zar" or why != "STOP" or not v.get("reverse"):
                break
            i = xi + 1
            side_used = {side}  # only the opposite side may trigger after a stop
    return pd.DataFrame(out)


def stats(t, ndays):
    if len(t) == 0:
        return dict(trades=0)
    r = t.R.values; w = r > 0
    eq = np.cumsum(r); dd = (np.maximum.accumulate(np.maximum(eq, 0)) - eq).max()
    st = mx = 0
    for x in r:
        st = st + 1 if x <= 0 else 0; mx = max(mx, st)
    gw, gl = r[w].sum(), -r[~w].sum()
    return dict(trades=len(r), tpd=round(len(r) / ndays, 2), win=round(100 * w.mean(), 1),
                avgW=round(r[w].mean(), 2) if w.any() else 0, avgL=round(r[~w].mean(), 2) if (~w).any() else 0,
                expR=round(r.mean(), 3), usd=round(t.usd.mean(), 2), PF=round(gw / gl, 2) if gl else 99,
                ddR=round(dd, 1), streak=mx, totusd=round(t.usd.sum()))


VARIANTS = []
for tg in [10, 1.5, 2, 2.5]:
    VARIANTS.append((f"ZAR5_t{tg}{'/EOD' if tg == 10 else ''}", dict(kind="zar", or_=5, tgt=tg)))
for orm in [5, 15, 30]:
    for st in ["opp", "half"]:
        for tg in [1.5, 2, 2.5, None]:
            VARIANTS.append((f"BRK{orm}_{st}_{tg or 'EOD'}", dict(kind="brk", **{"or": orm}, stop=st, tgt=tg)))
for v in VARIANTS:
    if "or_" in v[1]: v[1]["or"] = v[1].pop("or_")


def split(t, days):
    t = t.copy(); t["y"] = t.date.str[:4]
    ins = t[t.date < "2024-01-01"]; ho = t[t.date >= "2024-01-01"]
    di = sum(1 for x in days if x < "2024-01-01"); dh = len(days) - di
    return ins, ho, di, dh


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "mnq"
    import json
    res = {}
    syms = [("mnq", 570)] if which == "mnq" else [("mgc", 500), ("mgc", 570)] if which == "mgc" else []
    extra = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    for sym, om in syms:
        df = load(sym); feats = daily_features(df, om)
        days = sorted(feats.index)
        vs = VARIANTS if extra is None else [(n, v) for n, v in extra]
        for name, v in vs:
            t = run(df, feats, sym, v, open_min=om)
            ins, ho, di, dh = split(t, days)
            key = f"{sym}@{om//60:02d}:{om%60:02d} {name}"
            res[key] = (stats(ins, di), stats(ho, dh))
            print(key, "IS", res[key][0], "| HO", res[key][1], flush=True)
            t.to_csv(os.path.join(D, "trades", key.replace(" ", "_").replace(":", "").replace("@", "_").replace("/", "") + ".csv"), index=False)
    return res


if __name__ == "__main__":
    os.makedirs(os.path.join(D, "trades"), exist_ok=True)
    main()
