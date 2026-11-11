"""Daily + intraday features for the two-books study. Everything is CAUSAL: bias[i] for day i uses data up to the 16:00 close of day i-1
(and, where stated, today's 09:30 open)."""
import numpy as np, pandas as pd
import core as C


def sma(x, n):
    return pd.Series(x).rolling(n).mean().values


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values


def rsi(x, n=2):
    """Wilder RSI (as in Connors & Alvarez)."""
    d = np.diff(x, prepend=x[0]); up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    au = pd.Series(up).ewm(alpha=1 / n, adjust=False).mean().values; ad = pd.Series(dn).ewm(alpha=1 / n, adjust=False).mean().values
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    r[ad == 0] = 100.0; r[(au == 0) & (ad == 0)] = 50.0
    return r


def machine(le, lx, se, sx):
    """position state after each close: +1 after a long entry until the long exit, -1 mirrored. returns state, first (entry bar flag)."""
    n = len(le); st = np.zeros(n, int); first = np.zeros(n, int); p = 0
    for i in range(n):
        if p > 0 and lx[i]: p = 0
        elif p < 0 and sx[i]: p = 0
        if p == 0:
            if le[i]: p = 1; first[i] = 1
            elif se[i]: p = -1; first[i] = -1
        st[i] = p
    return st, first


def daily(data):
    D = data["days"]; n = len(D)
    off = np.array([a["off"] for _, a in D])
    f = dict(d=np.array([d for d, _ in D]),
             o=np.array([a["open"][0] for _, a in D]) + off, c=np.array([a["close"][389] for _, a in D]) + off,
             h=np.array([np.nanmax(a["high"]) for _, a in D]) + off, l=np.array([np.nanmin(a["low"]) for _, a in D]) + off,
             o_raw=np.array([a["open"][0] for _, a in D]), c_raw=np.array([a["close"][389] for _, a in D]))
    pre = np.array([c for _, c in data["nq_pre"]]) + off[0]          # NQ daily closes before MNQ existed: only for the 200-day average warm-up
    ext = np.concatenate([pre, f["c"]])
    f["sma200"] = sma(ext, 200)[len(pre):]
    f["sma5"] = sma(ext, 5)[len(pre):]
    f["rsi2"] = rsi(ext, 2)[len(pre):]
    s = pd.Series(ext)
    f["lo7"] = (s <= s.rolling(7).min() + 1e-9).values[len(pre):]; f["hi7"] = (s >= s.rolling(7).max() - 1e-9).values[len(pre):]
    f["ret"] = np.concatenate([[np.nan], f["c"][1:] / f["c"][:-1] - 1])
    f["oc"] = f["c"] / f["o"] - 1
    f["gap"] = np.concatenate([[np.nan], f["o"][1:] / f["c"][:-1] - 1])
    f["rollskip"] = np.concatenate([[True], np.abs(f["o_raw"][1:] / f["c_raw"][:-1] - 1) > 0.015])
    return f


def shift(x):
    """value known after close i-1 -> usable on day i"""
    return np.concatenate([[0], x[:-1]])


def connors(f):
    """Published daily rules (Connors & Alvarez, 'Short Term Trading Strategies That Work', 2008) -> dict name -> bias array for the NEXT day."""
    c, m200, m5, r = f["c"], f["sma200"], f["sma5"], f["rsi2"]
    up, dn = c > m200, c < m200
    cum = r + np.concatenate([[50], r[:-1]])
    B = {}
    B["T200 (close vs 200-day average)"] = shift(np.where(up, 1, np.where(dn, -1, 0)))
    for thr in (5, 10):
        st, fi = machine(up & (r < thr), c > m5, dn & (r > 100 - thr), c < m5)
        B[f"RSI2<{thr} (hold until close > 5-day avg)"] = shift(st); B[f"RSI2<{thr} (entry day only)"] = shift(fi)
    st, fi = machine(up & (cum < 35), r > 65, dn & (cum > 165), r < 35)
    B["CumRSI(2x2)<35 (hold until RSI2 > 65)"] = shift(st); B["CumRSI(2x2)<35 (entry day only)"] = shift(fi)
    st, fi = machine(up & f["lo7"], f["hi7"], dn & f["hi7"], f["lo7"])
    B["Double 7's (hold until 7-day high)"] = shift(st); B["Double 7's (entry day only)"] = shift(fi)
    return B


def tfbars(D, tf):
    """per-day TF bars from the 1-minute RTH arrays, ADJUSTED prices. returns list of dict(o,h,l,c,vw) arrays (390/tf bars) + concatenated closes."""
    nbar = 390 // tf; out = []
    for d, a in D:
        off = a["off"]
        O = a["open"].reshape(nbar, tf); H = a["high"].reshape(nbar, tf); L = a["low"].reshape(nbar, tf); Cc = a["close"].reshape(nbar, tf)
        V = a["vwap"].reshape(nbar, tf)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                h = np.nanmax(H, axis=1); l = np.nanmin(L, axis=1)
        o = pd.DataFrame(O).bfill(axis=1).iloc[:, 0].values; c = pd.DataFrame(Cc).ffill(axis=1).iloc[:, -1].values
        vw = pd.DataFrame(V).ffill(axis=1).iloc[:, -1].values
        b = dict(o=o + off, h=h + off, l=l + off, c=c + off, vw=vw + off)
        for k in b:                                   # a TF bar with no trade at all = previous close
            x = b[k]
            if np.isnan(x).any(): b[k] = pd.Series(x).ffill().bfill().values
        out.append(b)
    return out
