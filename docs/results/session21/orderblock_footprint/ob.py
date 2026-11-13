"""Order-block + simulated-footprint backtest engine (research only). Run via run.py."""
import pickle, numpy as np
TICK = 0.25
NB = 390
DATA = "/tmp/claude-0/-home-user-opogabuuga/50bc3d78-c0a4-5955-9229-af69d0b1b2e9/scratchpad/data/days12.pkl"

# ------------------------------------------------------------------ volume recovery from VWAP
def recover_volume(a):
    h, l, c, vw = a["high"], a["low"], a["close"], a["vwap"]
    tp = (h + l + c) / 3.0
    n = len(c)
    bad = np.zeros(n, bool)
    u = np.zeros(n)  # v_k / V_{k-1}
    for k in range(1, n):
        den = tp[k] - vw[k - 1]
        if abs(den) < 0.05: bad[k] = True; continue
        r = (vw[k] - vw[k - 1]) / den
        if not (0 < r < 1): bad[k] = True; continue
        u[k] = r / (1 - r)
    def chain(vimp):
        v = np.zeros(n); V = 1.0; v[0] = 1.0
        for k in range(1, n):
            vk = vimp[k] if bad[k] else u[k] * V
            v[k] = vk; V += vk
        return v
    # pass 1: impute from past good values (median of last 5 good); pass 2: centred window median
    v = chain(np.full(n, 1.0))
    for it in range(2):
        vimp = np.zeros(n)
        for k in range(1, n):
            if bad[k]:
                lo, hi = max(1, k - 5), min(n, k + 6)
                g = [v[j] for j in range(lo, hi) if not bad[j]]
                vimp[k] = float(np.median(g)) if g else (float(np.median(v[1:])) if n > 1 else 1.0)
        v = chain(vimp)
    return v, bad

def deltas(a, vol, prev_close):
    h, l, c = a["high"], a["low"], a["close"]
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        bs = np.where(rng > 0, (c - l) / rng, np.nan)
    pc = np.concatenate([[prev_close], c[:-1]])
    tick = np.where(c > pc, 1.0, np.where(c < pc, 0.0, 0.5))
    bs = np.where(np.isnan(bs), tick, bs)
    return vol * (2 * bs - 1)

class Market:
    def __init__(self, days, pv, fee=1.0, vol_modes=("rec", "range", "one")):
        self.days = days            # list of (date, dict)
        self.pv, self.fee = pv, fee
        self.dates = [d for d, _ in days]
        self.nd = len(days)
        self.delta = {m: [] for m in vol_modes}; self.cvd = {m: [] for m in vol_modes}
        self.imputed = 0; self.total = 0
        prev = days[0][1]["open"][0]
        for d, a in days:
            vr, bad = recover_volume(a); self.imputed += int(bad.sum()); self.total += len(bad)
            vols = {"rec": vr, "range": a["high"] - a["low"], "one": np.ones(len(a["close"]))}
            for m in vol_modes:
                dl = deltas(a, vols[m], prev)
                self.delta[m].append(dl); self.cvd[m].append(np.cumsum(dl))
            prev = a["close"][-1]
        self.cat = {k: np.concatenate([a[k] for _, a in days]) for k in ("open", "high", "low", "close")}
        self.obs = {}

    # ---- order blocks (app definition) on tf-minute bars
    def build_obs(self, tf):
        if tf in self.obs: return self.obs[tf]
        nb = NB // tf
        o = self.cat["open"].reshape(-1, nb, tf)[:, :, 0].ravel()
        h = self.cat["high"].reshape(-1, nb, tf).max(2).ravel()
        l = self.cat["low"].reshape(-1, nb, tf).min(2).ravel()
        c = self.cat["close"].reshape(-1, nb, tf)[:, :, -1].ravel()
        n = len(c)
        atr = np.full(n, np.nan); trs = []; val = None; pc = None
        a_prev = np.full(n, np.nan)
        for i in range(n):
            a_prev[i] = np.nan if val is None else val
            tr = h[i] - l[i] if pc is None else max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc))
            pc = c[i]
            if val is None:
                trs.append(tr)
                if len(trs) == 14: val = sum(trs) / 14
            else: val = (val * 13 + tr) / 14
        body = np.abs(c - o)
        res = []
        for i in range(11, n):
            ap = a_prev[i]
            if np.isnan(ap) or ap <= 0 or body[i] < 1.0 * ap: continue
            w = slice(i - 10, i)
            up = c[i] > o[i] and c[i] > h[w].max()
            dn = c[i] < o[i] and c[i] < l[w].min()
            if not (up or dn): continue
            for j in range(i - 1, max(i - 11, -1), -1):
                if (up and c[j] < o[j]) or (dn and c[j] > o[j]):
                    lo, hi = l[j], h[j]
                    end = min(n, i + 121)           # alive after bars up to i+120
                    seg = c[i + 1:end]
                    hit = np.where((seg < lo) if up else (seg > hi))[0]
                    dead_i = (i + 1 + hit[0] + 1) if len(hit) else end   # bar index after the killing bar (killed at its close)
                    if len(hit) == 0: dead_i = i + 121
                    res.append((up, lo, hi, (i + 1) * tf, dead_i * tf, i))
                    break
        # tuple: bull, lo, hi, g_conf, g_end (exclusive), bar index
        arr = res
        perday = {}
        for idx, (bull, lo, hi, gc, ge, _) in enumerate(arr):
            for di in range(gc // NB, min(self.nd - 1, (ge - 1) // NB) + 1):
                perday.setdefault(di, []).append(idx)
        self.obs[tf] = (arr, perday)
        return self.obs[tf]

    # ---- candidates
    def candidates(self, tf, variant, vm):
        arr, perday = self.build_obs(tf)
        consumed = set(); out = {}
        for di in range(self.nd):
            a = self.days[di][1]
            o, h, l, c = a["open"], a["high"], a["low"], a["close"]
            dl = self.delta[vm][di]; cv = self.cvd[vm][di]
            cands = []
            for idx in perday.get(di, ()):
                if idx in consumed: continue
                bull, lo, hi, gc, ge, _ = arr[idx]
                k0 = max(0, gc - di * NB, 15); k1 = min(NB, ge - di * NB, 331)
                if k1 <= k0: continue
                s = 1 if bull else -1
                touch = (l[k0:k1] <= hi) if bull else (h[k0:k1] >= lo)
                if not touch.any(): continue
                kt = k0 + int(np.argmax(touch))
                consumed.add(idx)
                ek = None; base = None
                if variant == "V0":
                    ek = kt
                    base = min(o[kt], hi) if bull else max(o[kt], lo)
                elif variant in ("V1", "V3"):
                    if kt <= 329:
                        ok = (dl[kt] > 0 and c[kt] >= lo) if bull else (dl[kt] < 0 and c[kt] <= hi)
                        if ok and variant == "V3": ok = (cv[kt] > 0) if bull else (cv[kt] < 0)
                        if ok: ek = kt + 1; base = o[ek]
                elif variant == "V2":
                    cum = 0.0
                    for j in range(kt, min(k1, 330)):
                        if bull:
                            if c[j] < lo: break
                            if c[j] <= hi:
                                if l[j] <= hi: cum += dl[j]
                            else:
                                if cum < 0 and dl[j] > 0: ek = j + 1; base = o[ek]; break
                                cum = 0.0
                        else:
                            if c[j] > hi: break
                            if c[j] >= lo:
                                if h[j] >= lo: cum += dl[j]
                            else:
                                if cum > 0 and dl[j] < 0: ek = j + 1; base = o[ek]; break
                                cum = 0.0
                if ek is None or ek > 330: continue
                e = base + s * TICK
                stop = (lo - TICK) if bull else (hi + TICK)
                pts = (e - stop) * s
                if pts * self.pv > 250 or pts < 8 * TICK: continue
                cands.append((ek, -gc, s, base, e, stop, pts, variant == "V0"))
            cands.sort(key=lambda x: (x[0], x[1]))
            out[di] = cands
        return out

    # ---- walk
    def walk(self, di, s, ek, e, stop, tgt_pts, no_tgt_entry_bar):
        a = self.days[di][1]; o, h, l, c = a["open"], a["high"], a["low"], a["close"]
        xend = 385
        tgt = e + s * tgt_pts
        tgt = np.floor(tgt / TICK) * TICK if s > 0 else np.ceil(tgt / TICK) * TICK
        L, H = l[ek:xend], h[ek:xend]
        sh = np.where(L <= stop)[0] if s > 0 else np.where(H >= stop)[0]
        th = np.where(H >= tgt + TICK)[0] if s > 0 else np.where(L <= tgt - TICK)[0]
        if no_tgt_entry_bar: th = th[th > 0]
        si = sh[0] if len(sh) else 10**9; ti = th[0] if len(th) else 10**9
        if si == 10**9 and ti == 10**9:
            j = xend - 1; px = c[j] - s * TICK
        elif si <= ti:
            j = ek + si; oj = o[j]
            px = (min(stop, oj) if s > 0 else max(stop, oj)) - s * TICK
        else:
            j = ek + ti; px = tgt
        seg = slice(ek, j + 1)
        mae = ((e - l[seg].min()) if s > 0 else (h[seg].max() - e)) * self.pv + TICK * self.pv
        pnl = (px - e) * s * self.pv - self.fee
        return pnl, j, max(mae, 0.0)

    def run(self, cands, R, tf=None):
        rows = []
        for di in range(self.nd):
            t_free = 0; n = 0
            for (ek, ngc, s, base, e, stop, pts, v0) in cands[di]:
                if n >= 3: break
                if ek < t_free: continue
                pnl, xk, mae = self.walk(di, s, ek, e, stop, R * pts, v0)
                n += 1; t_free = xk + 1
                rows.append(dict(d=self.dates[di], di=di, ek=ek, xk=xk, pnl=pnl, mae=mae,
                                 risk=pts * self.pv + self.fee + TICK * self.pv, side=s, base=base, pts=pts, v0=v0))
        return rows

    def random_side(self, rows, R, seed):
        rng = np.random.default_rng(seed); out = []
        for r in rows:
            s = 1 if rng.random() < 0.5 else -1
            e = r["base"] + s * TICK; stop = e - s * r["pts"]
            pnl, xk, mae = self.walk(r["di"], s, r["ek"], e, stop, R * r["pts"], r["v0"])
            out.append(pnl)
        return np.array(out)

def stats(rows, lo=None, hi=None):
    r = [x for x in rows if (lo is None or x["d"] >= lo) and (hi is None or x["d"] <= hi)]
    if not r: return dict(n=0, win=float("nan"), pf=float("nan"), per=0.0, net=0.0, dd=0.0)
    p = np.array([x["pnl"] for x in r]); w = p > 0; gl = -p[~w].sum()
    cum = np.concatenate([[0], np.cumsum(p)])
    return dict(n=len(p), win=100 * w.mean(), pf=(p[w].sum() / gl) if gl > 0 else float("inf"),
                per=float(p.mean()), net=float(p.sum()), dd=float((np.maximum.accumulate(cum) - cum).max()))

def load():
    D, E = pickle.load(open(DATA, "rb"))
    return D, E
