"""Session 18: Triple RSI / DMI / SuperTrend-15m / combos on MNQ (1 micro, RTH, flat 15:59). Reuses lib.py (= smc.py loader, run_trade/collect/stats/randbench)."""
import sys, json
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session18/rsi_dmi")
from lib import *
ENTRY_LO, ENTRY_HI = 575, 930
BARS = {tf: bars(tf) for tf in (1, 5, 15)}
ST15 = supertrend(BARS[15])[0]

def wilder(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().values

def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up = wilder(np.maximum(d, 0), n); dn = wilder(np.maximum(-d, 0), n)
    return 100 - 100 / (1 + up / np.where(dn == 0, 1e-9, dn))

def dmi(b, n=14):
    h, l, c = b.high.values, b.low.values, b.close.values
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = wilder(tr, n); pdi = 100 * wilder(pdm, n) / atr; mdi = 100 * wilder(mdm, n) / atr
    dx = 100 * abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-9)
    return pdi, mdi, wilder(dx, n), atr

class TF:
    def __init__(s, tf):
        b = BARS[tf]; s.b = b; s.tf = tf; s.c = b.close.values; s.nxt = b.nxt.values; s.mc = b.mod_close.values
        s.bd = b.index.strftime("%Y-%m-%d").values
        s.pdi, s.mdi, s.adx, s.atr = dmi(b)
        s.rsi = {n: rsi(s.c, n) for n in (2, 3, 7, 14)}
        # last closed 15m bar index for each tf bar
        sc = (BARS[15].index + pd.Timedelta(minutes=15)).values; bc = (b.index + pd.Timedelta(minutes=tf)).values
        s.k15 = np.searchsorted(sc, bc, side="right") - 1
TFS = {tf: TF(tf) for tf in (1, 5, 15)}
D15 = TF(15)

def rsi_state(T, ps, thr):
    a, bb, cc = (T.rsi[p] for p in ps)
    ob = (a > 100 - thr[0]) & (bb > 100 - thr[1]) & (cc > 100 - thr[2])
    os_ = (a < thr[0]) & (bb < thr[1]) & (cc < thr[2])
    return np.where(os_, 1, np.where(ob, -1, 0))

def dmi_state(T, thr):
    pdi, mdi, adx = T.pdi, T.mdi, T.adx
    rising = adx > np.r_[adx[0], adx[:-1]]
    return np.where((pdi > mdi) & (adx > thr) & rising, 1, np.where((mdi > pdi) & (adx > thr) & rising, -1, 0))

def dmi_dir(T):
    return np.where(T.pdi > T.mdi, 1, -1)

def to_sigs(T, state, exitm, mrp=2):
    """event = bar where state turns nonzero/changes; entry next 1m open."""
    out = []; n = len(state)
    ra = T.rsi[mrp]
    dd = dmi_dir(T)
    for j in range(1, n):
        s = int(state[j])
        if s == 0 or s == state[j - 1]: continue
        if not (ENTRY_LO <= T.mc[j] <= ENTRY_HI): continue
        i0 = T.nxt[j]
        if i0 >= N or DATE[i0] != T.bd[j]: continue
        dist = min(2 * T.atr[j], MAXPT)
        if exitm == "mr":
            if dist < MINPT: continue
            ex = None
            for k in range(j + 1, min(j + 400, n)):
                if T.bd[k] != T.bd[j]: break
                if (s == 1 and ra[k] > 50) or (s == -1 and ra[k] < 50) or T.mc[k] >= 955:
                    ex = T.nxt[k]; break
            if ex is not None and ex <= i0: continue
            out.append((i0, s, dist, None, ex, None))
        elif exitm == "flip":
            ex = None
            for k in range(j + 1, min(j + 400, n)):
                if T.bd[k] != T.bd[j]: break
                if dd[k] != s: ex = T.nxt[k]; break
            if ex is not None and ex <= i0: continue
            out.append((i0, s, MAXPT, None, ex, None))
        else:
            if dist < MINPT: continue
            out.append((i0, s, dist, exitm, None, None))
    return out

def sigs_ST15(exitm):
    b = BARS[15]; d = ST15; nxt = b.nxt.values; mc = b.mod_close.values; bd = b.index.strftime("%Y-%m-%d").values
    line = supertrend(b)[1]; flips = np.nonzero(d[1:] != d[:-1])[0] + 1; out = []
    for j, f in enumerate(flips):
        if not (ENTRY_LO <= mc[f] <= ENTRY_HI): continue
        i0 = nxt[f]
        if i0 >= N or DATE[i0] != bd[f]: continue
        side = int(d[f]); dist = abs(O[i0] - line[f])
        if exitm == "flip": out.append((i0, side, MAXPT, None, nxt[flips[j + 1]] if j + 1 < len(flips) else None, None))
        else:
            if dist < MINPT or dist > MAXPT: continue
            out.append((i0, side, dist, exitm, None, None))
    return out

res = {}; streams = {}; FAM = {}
def row(fam, name, sigs):
    t = collect(sigs); streams[name] = t; FAM[name] = fam
    r = dict(fam=fam, IS=stats(t, "IS"), HO=stats(t, "HO"), rand_HO=randbench(sigs, seeds=10) if len(t) > 30 else None)
    res[name] = r; print(name, json.dumps(r), flush=True)
    json.dump(res, open(OUT + "/results.json", "w"), indent=1)

base = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE__lock_.csv")
res["NOISE preset C"] = dict(fam="base", IS=stats(base, "IS"), HO=stats(base, "HO"))
THR = (10, 30, 40)
# A Triple RSI alone
for tf in (1, 5, 15):
    for ps in ((2, 7, 14), (3, 7, 14)):
        st = rsi_state(TFS[tf], ps, THR)
        for ex in ("mr", 1.5):
            row("A", f"A TriRSI{ps} {tf}m exit={ex}", to_sigs(TFS[tf], st, ex))
# B DMI alone
for tf in (5, 15):
    for thr in (20, 25):
        st = dmi_state(TFS[tf], thr)
        for ex in ("flip", 1.5, 2.0):
            row("B", f"B DMI adx>{thr} {tf}m exit={ex}", to_sigs(TFS[tf], st, ex))
# C SuperTrend 15m alone
for ex in ("flip", 1.5, 2.0): row("C", f"C ST15m exit={ex}", sigs_ST15(ex))
# D combos (entry TF 5m or 15m; ST/DMI = last closed 15m bar)
for tf in (5, 15):
    T = TFS[tf]; k = T.k15; kk = np.maximum(k, 0)
    stv = np.where(k >= 0, ST15[kk], 0)
    dmv = np.where(k >= 0, dmi_state(D15, 20)[kk], 0)
    rs = rsi_state(T, (2, 7, 14), THR)
    # RSI is counter-trend: oversold state = long vote
    votes_l = (rs == 1).astype(int) + (stv == 1) + (dmv == 1)
    votes_s = (rs == -1).astype(int) + (stv == -1) + (dmv == -1)
    vote2 = np.where(votes_l >= 2, 1, np.where(votes_s >= 2, -1, 0))
    all3 = np.where(votes_l == 3, 1, np.where(votes_s == 3, -1, 0))
    # ST/DMI trend agree (without RSI) vote: trend-only 2 of 2
    f_st = np.where(rs == stv, rs, 0)
    f_dm = np.where(rs == dmv, rs, 0)
    f_both = np.where((rs == stv) & (rs == dmv), rs, 0)
    for ex in ("mr", 1.5):
        row("Di", f"D(i) vote>=2 {tf}m exit={ex}", to_sigs(T, vote2, ex))
        row("Dii", f"D(ii) all-3 {tf}m exit={ex}", to_sigs(T, all3, ex))
        row("Diii", f"D(iii) RSI+ST15 {tf}m exit={ex}", to_sigs(T, f_st, ex))
        row("Diii", f"D(iii) RSI+DMI15 {tf}m exit={ex}", to_sigs(T, f_dm, ex))
        row("Diii", f"D(iii) RSI+ST15+DMI15 {tf}m exit={ex}", to_sigs(T, f_both, ex))
for k, t in streams.items(): t.to_csv(OUT + "/stream_" + k.replace(" ", "_").replace("=", "").replace("+", "p").replace(">", "g").replace("(", "").replace(")", "").replace(",", "") + ".csv.gz", index=False)
print("done")
