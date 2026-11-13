"""Session 22 (research only): the shipped ORDER FLOW strategy (D101 AR Model + D108 Casper) on 5 years of 1m RTH MNQ / MES
with a SIMULATED footprint (volume recovered from VWAP, buy share = close location). Gates and plan come from the app code
(app.engine.order_flow.check_ar / check_casper / build_plan / trail_stop); everything else is vectorised numpy here.
Run via run.py. Footprint is ESTIMATED, not aggressor flow."""
import sys, pickle, math
from decimal import Decimal as Dc
import numpy as np
sys.path[:0] = ["/home/user/opogabuuga/backend", "/home/user/opogabuuga/docs/results/session21/orderblock_footprint"]
import ob  # recover_volume / stats (session 21)
from app.engine.order_flow import (check_ar, ArFields, ArRules, build_plan, trail_stop, check_casper, CasperFields, CasperRules,
                                   OrderFlowSkip)
from app.engine.trade_plan import Direction
from app.engine import footprint as FP

DATA = "/tmp/claude-0/-home-user-opogabuuga/13cb35fb-f8d0-52e2-a7d8-3c5c31ee09a8/scratchpad/data/days12.pkl"
NB, NC = 390, 78
INST = {"MNQ": dict(pv=2.0, tick=0.25, fee=1.0, row=0.5), "MES": dict(pv=5.0, tick=0.25, fee=1.0, row=0.25)}
DIR = {1: Direction.LONG, -1: Direction.SHORT}
FIB_LO, FIB_HI = Dc("0.705"), Dc("0.886")


def load():
    D, E = pickle.load(open(DATA, "rb"))
    return D, E


def buy_share(a, prev_close):
    h, l, c = a["high"], a["low"], a["close"]
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        bs = np.where(rng > 0, (c - l) / rng, np.nan)
    pc = np.concatenate([[prev_close], c[:-1]])
    tk = np.where(c > pc, 1.0, np.where(c < pc, 0.0, 0.5))
    return np.where(np.isnan(bs), tk, bs)


def pivots(h, l, k=2):
    """confirmed swing pivots (ar.py logic) -> state known after each bar closes"""
    n = len(h)
    ph = np.full(n, np.nan); pl = np.full(n, np.nan); phi = np.full(n, -1); pli = np.full(n, -1)
    ph2 = np.full(n, np.nan); pl2 = np.full(n, np.nan)
    ch = cl = c2h = c2l = np.nan; chi = cli = -1
    for i in range(n):
        j = i - k
        if j >= k:
            if h[j] == h[j - k:j + k + 1].max(): c2h, ch, chi = ch, h[j], j
            if l[j] == l[j - k:j + k + 1].min(): c2l, cl, cli = cl, l[j], j
        ph[i], phi[i], pl[i], pli[i], ph2[i], pl2[i] = ch, chi, cl, cli, c2h, c2l
    with np.errstate(invalid="ignore"):
        tr = np.where((ph > ph2) & (pl > pl2), 1, np.where((ph < ph2) & (pl < pl2), -1, 0))
    return ph, phi, pl, pli, tr


def value_area(vols):
    """app footprint.volume_profile algorithm on a contiguous ascending row-volume vector -> (poc_i, val_i, vah_i)"""
    n = len(vols); total = vols.sum()
    pi = int(np.argmax(vols)); a = z = pi; acc = vols[pi]
    while acc < total * 0.70 and (a > 0 or z < n - 1):
        up = vols[z + 1] if z < n - 1 else -1.0
        dn = vols[a - 1] if a > 0 else -1.0
        if up >= dn: z += 1; acc += up
        else: a -= 1; acc += dn
    return pi, a, z


class Mkt:
    def __init__(self, days, inst, is_end):
        I = INST[inst]; self.inst = inst
        self.pv, self.tick, self.fee, self.row = I["pv"], I["tick"], I["fee"], I["row"]
        self.tickval = self.tick * self.pv
        self.days = days; self.dates = [d for d, _ in days]; self.nd = nd = len(days)
        self.is_end = is_end
        self.o, self.h, self.l, self.c = (np.array([a[k] for _, a in days]) for k in ("open", "high", "low", "close"))
        vol = np.zeros((nd, NB)); self.imputed = 0; prev = days[0][1]["open"][0]; bs = np.zeros((nd, NB))
        for i, (d, a) in enumerate(days):
            v, bad = ob.recover_volume(a); vol[i] = v; self.imputed += int(bad.sum())
            bs[i] = buy_share(a, prev); prev = a["close"][-1]
            assert np.allclose(v * (2 * bs[i] - 1), ob.deltas(a, v, days[i - 1][1]["close"][-1] if i else a["open"][0]))
        self.vol, self.bs = vol, bs
        self.dl = vol * (2 * bs - 1)
        self.cvd = np.cumsum(self.dl, axis=1)
        self.vnorm = vol / vol.mean(axis=1, keepdims=True)  # per-day scale equalisation (recovered volume has an arbitrary per-day unit)
        self._footprint5()
        self.GH, self.GL, self.GV = self.h.ravel(), self.l.ravel(), self.vnorm.ravel()
        self._pcache = {}; self._fcache = {}; self._plcache = {}; self.locdef = 'close'

    # ---------------------------------------------------------------- 5m footprint (vectorised app method)
    def _footprint5(self):
        nd, row = self.nd, self.row
        shp = (nd, NC, 5)
        self.O5 = self.o.reshape(shp)[:, :, 0]; self.C5 = self.c.reshape(shp)[:, :, -1]
        self.H5 = self.h.reshape(shp).max(2); self.L5 = self.l.reshape(shp).min(2)
        self.V5 = self.vol.reshape(shp).sum(2); self.D5 = self.dl.reshape(shp).sum(2)
        self.poc5 = np.zeros((nd, NC)); self.stk_buy = np.zeros((nd, NC), int); self.stk_sell = np.zeros((nd, NC), int)
        ci = np.arange(NB) // 5
        for i in range(nd):
            lo = np.floor(self.l[i] / row).astype(int); hi = np.floor(self.h[i] / row).astype(int)
            r0 = lo.min(); nr = hi.max() - r0 + 1
            per = self.vol[i] / (hi - lo + 1)
            A = np.zeros((NC, nr + 1)); B = np.zeros((NC, nr + 1))
            av = per * self.bs[i]; bv = per * (1 - self.bs[i])
            np.add.at(A, (ci, lo - r0), av); np.add.at(A, (ci, hi - r0 + 1), -av)
            np.add.at(B, (ci, lo - r0), bv); np.add.at(B, (ci, hi - r0 + 1), -bv)
            A = np.cumsum(A, 1)[:, :nr]; B = np.cumsum(B, 1)[:, :nr]
            eps = 1e-9 * self.vol[i].mean(); A[A < eps] = 0; B[B < eps] = 0
            pi = np.argmax(A + B, axis=1)
            self.poc5[i] = (r0 + pi) * row + row / 2
            buy = np.zeros((NC, nr), bool); sell = np.zeros((NC, nr), bool)   # diagonal 3:1 imbalances
            buy[:, 1:] = (A[:, 1:] > 0) & (A[:, 1:] >= 3 * B[:, :-1])          # ask here vs bid one row below
            sell[:, :-1] = (B[:, :-1] > 0) & (B[:, :-1] >= 3 * A[:, 1:])       # bid here vs ask one row above
            for M, out in ((buy, self.stk_buy), (sell, self.stk_sell)):
                run = np.zeros(NC, int); best = np.zeros(NC, int)
                for r in range(nr):
                    run = np.where(M[:, r], run + 1, 0); best = np.maximum(best, run)
                out[i] = best

    # ---------------------------------------------------------------- features (within-day windows, IS thresholds)
    def build(self, Z=None):
        nd = self.nd; H, L, C, Dd = self.H5, self.L5, self.C5, self.D5
        pc = np.concatenate([C[:, :1] * 0 + np.nan, C[:, :-1]], 1)
        tr5 = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
        tr5[:, 0] = (H - L)[:, 0]
        self.atr5 = np.full((nd, NC), np.nan); self.er = np.full((nd, NC), np.nan); self.dirn = np.zeros((nd, NC)); self.ov = np.full((nd, NC), np.nan)
        self.ad = np.full((nd, NC), np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            ovl = np.zeros((nd, NC)); rngc = H - L
            ovl[:, 1:] = np.clip(np.minimum(H[:, 1:], H[:, :-1]) - np.maximum(L[:, 1:], L[:, :-1]), 0, None) / np.where(rngc[:, 1:] > 0, rngc[:, 1:], np.nan)
            ovl = np.nan_to_num(ovl)
            for i in range(6, NC):
                w = min(12, i)
                self.atr5[:, i] = tr5[:, max(0, i - 11):i + 1].mean(1)
                den = np.abs(np.diff(C[:, i - w:i + 1], axis=1)).sum(1)
                self.er[:, i] = np.abs(C[:, i] - C[:, i - w]) / den
                self.dirn[:, i] = np.sign(C[:, i] - C[:, i - w])
                self.ov[:, i] = ovl[:, i - w + 1:i + 1].mean(1)
                self.ad[:, i] = np.abs(Dd[:, max(0, i - 20):i]).mean(1)
        dH, dL, dC = self.h.max(1), self.l.min(1), self.c[:, -1]
        dpc = np.concatenate([[np.nan], dC[:-1]])
        trd = np.maximum(dH - dL, np.maximum(np.abs(dH - dpc), np.abs(dL - dpc))); trd[0] = (dH - dL)[0]
        self.atrD = np.full(nd, np.nan)
        for i in range(20, nd): self.atrD[i] = trd[i - 20:i].mean()
        self.atrr = self.atr5 / self.atrD[:, None]
        isd = np.array([d <= self.is_end for d in self.dates])
        if Z is None:
            x = self.atrr[isd]; x = x[~np.isnan(x)]
            Z = dict(q30=float(np.quantile(x, 0.3)), q95=float(np.quantile(x, 0.95)), ov_med=float(np.nanmedian(self.ov[isd & ~np.isnan(self.atrD)])))
        self.Z = Z
        valid = ~np.isnan(self.atrr) & ~np.isnan(self.ov) & ~np.isnan(self.er)
        comp = ((self.atrr < Z["q30"]) & (self.ov > Z["ov_med"])) | (self.atrr > Z["q95"])
        expn = ~comp & (self.er >= 0.4)
        self.env = np.where(valid, np.where(comp, 0, np.where(expn, 1, 2)), -1)  # 0 compression 1 expansion 2 rotation -1 n/a
        self.mid5 = (H + L) / 2
        # swing structure: 15m and 1h RTH bars carried across days
        self.st = {}
        for tf in (15, 60):
            starts = np.arange(0, NB, tf)
            bh = np.maximum.reduceat(self.h, starts, axis=1); bl = np.minimum.reduceat(self.l, starts, axis=1)
            nb = len(starts)
            ph, phi, pl, pli, tr = pivots(bh.ravel(), bl.ravel())
            didx = np.repeat(np.arange(nd), nb); bidx = np.tile(np.arange(nb), nd)
            closeT = didx * NB + np.minimum(NB, (bidx + 1) * tf)
            self.st[tf] = dict(ph=ph, phi=phi, pl=pl, pli=pli, tr=tr, closeT=closeT, nb=nb)
        G = (np.arange(nd)[:, None] * NB + 5 * (np.arange(NC)[None, :] + 1)).ravel()
        for tf in (15, 60):
            s = self.st[tf]; ix = np.searchsorted(s["closeT"], G, side="right") - 1
            s["ix"] = ix.reshape(nd, NC)
        i15, i60 = self.st[15]["ix"], self.st[60]["ix"]
        t15 = np.where(i15 >= 0, self.st[15]["tr"][np.maximum(i15, 0)], 0); t60 = np.where(i60 >= 0, self.st[60]["tr"][np.maximum(i60, 0)], 0)
        self.bias = np.sign(t15 + t60)
        # prior-day RTH value (VAH / VAL / POC from the recovered-volume profile)
        self.prior = [None] * nd
        for i in range(1, nd):
            self.prior[i] = self._profile(( i - 1) * NB, i * NB, rtn=True)
        return Z

    def _profile(self, ws, we, rtn=False):
        key = (ws, we)
        if key in self._pcache: return self._pcache[key]
        row = self.row
        lo = np.floor(self.GL[ws:we] / row).astype(int); hi = np.floor(self.GH[ws:we] / row).astype(int)
        r0 = lo.min(); nr = hi.max() - r0 + 1
        per = self.GV[ws:we] / (hi - lo + 1)
        df = np.zeros(nr + 1); np.add.at(df, lo - r0, per); np.add.at(df, hi - r0 + 1, -per)
        v = np.cumsum(df)[:nr]; v[v < 1e-12] = 0
        pi, a, z = value_area(v)
        out = ((r0 + a) * row, (r0 + z) * row, (r0 + pi) * row + row / 2)  # VAL, VAH (row low edges as in the app), POC
        self._pcache[key] = out
        return out

    # ---------------------------------------------------------------- per-candle signals
    def conf(self, k):
        """(nd,NC) bool/kind arrays per side s: 1 absorption, 2 delta flip (0 none), valid decision candles only"""
        out = {}
        D, C, H, L, ad = self.D5, self.C5, self.H5, self.L5, self.ad
        ok = ~np.isnan(ad)
        for s in (1, -1):
            absb = ok & (np.abs(D) > k * ad) & (s * D < 0) & (s * (C - self.mid5) > 0)
            fl = np.zeros_like(absb)
            fl[:, 1:] = ok[:, 1:] & (s * D[:, :-1] < 0) & (s * D[:, 1:] > k * ad[:, 1:]) & (s * (C[:, 1:] - (H[:, :-1] if s > 0 else L[:, :-1])) > 0)
            out[s] = np.where(absb, 1, np.where(fl, 2, 0))
        return out

    def candidates(self, k):
        cf = self.conf(k); res = {}
        for s in (1, -1):
            m = (cf[s] > 0) & (self.env > 0)
            m &= ~((self.env == 1) & (self.dirn != s))     # expansion: continuation only
            m[:, 72:] = False                              # entry window ends 15:30 (bar 360 = candle 71 close + 0..2)
            for di, mi in zip(*np.nonzero(m)): res.setdefault(int(di), []).append((int(mi), s))
        for di in res: res[di].sort()
        return res, cf

    def fields(self, di, m, s):
        key = (di, m, s, self.locdef)
        if key in self._fcache: return self._fcache[key]
        envc = {0: "COMPRESSION", 1: "EXPANSION", 2: "ROTATION"}[int(self.env[di, m])]
        T = 5 * (m + 1)
        fib = vs = None; info = {}
        if self.bias[di, m] == s:
            s15 = self.st[15]; ix = s15["ix"][di, m]
            ph, pl, phi, pli = s15["ph"][ix], s15["pl"][ix], s15["phi"][ix], s15["pli"][ix]
            a = self.atrD[di]
            if ix >= 0 and phi >= 0 and pli >= 0 and not np.isnan(a) and ((pli < phi) if s > 0 else (phi < pli)):
                R = ph - pl
                if 0.2 * a <= R <= 2.5 * a:
                    cl = self.C5[di, m]                    # 'close' (pre-registered): candle close; 'extreme' (diagnostic): absorption extreme
                    if self.locdef == 'extreme': cl = self.L5[di, m] if s > 0 else self.H5[di, m]
                    depth = (ph - cl) / R if s > 0 else (cl - pl) / R
                    ws = min(phi, pli) * 15; we = (max(phi, pli) + 1) * 15
                    val, vah, _ = self._profile(ws, we)
                    fib = Dc(round(float(depth), 4))
                    vs = "BELOW_VAL" if cl < val else ("ABOVE_VAH" if cl > vah else "IN_VALUE")
                    info = dict(swing_hi=float(ph), swing_lo=float(pl), val=float(val), vah=float(vah), depth=float(depth))
        base = (di * 1440 + 570) * 60_000
        f = ArFields(env=envc, fib=fib, value_side=vs, path_zone=None, path_side=None, delta_source="est",
                     confirm_time_ms=base + (T - 1) * 60_000)
        self._fcache[key] = (f, info)
        return self._fcache[key]

    def plan(self, di, m, s, kind):
        key = (di, m, s, kind)
        if key in self._plcache: return self._plcache[key]
        ext = self.L5[di, m] if s > 0 else self.H5[di, m]
        r = build_plan(kind="ABSORPTION" if kind == 1 else "DELTA_DIVERGENCE", direction=DIR[s], entry=Dc(float(self.poc5[di, m])),
                       defended=Dc(float(ext)), tick=Dc("0.25"), buffer_ticks=1, rr=Dc("2.0"), rr_min=Dc("1.5"), min_risk_ticks=8,
                       max_risk_ticks=120, absorption=(Dc(float(self.L5[di, m])), Dc(float(self.H5[di, m]))))
        self._plcache[key] = r
        return r

    # ---------------------------------------------------------------- trade walk
    def walk(self, di, s, kk, fill, stop, tp, mode, risk_pts):
        """entry at bar kk with `fill` (+1 tick slippage); stop first inside a bar; target needs a 1-tick trade-through (no credit on the
        entry bar); exits: stop / bar open gap minus 1 tick slippage, target at its price, flat 16:00 at the last close minus 1 tick."""
        o, h, l, c = self.o[di], self.h[di], self.l[di], self.c[di]
        tk, pv = self.tick, self.pv
        e = fill + s * tk
        if mode == "2R":
            L, H = l[kk:], h[kk:]
            sh = np.where(L <= stop)[0] if s > 0 else np.where(H >= stop)[0]
            th = np.where(H >= tp + tk)[0] if s > 0 else np.where(L <= tp - tk)[0]
            th = th[th > 0]
            si = sh[0] if len(sh) else 10**9; ti = th[0] if len(th) else 10**9
            if si == 10**9 and ti == 10**9: j = NB - 1; px = c[j] - s * tk
            elif si <= ti:
                j = kk + si; oj = o[j]; px = (min(stop, oj) if s > 0 else max(stop, oj)) - s * tk
            else: j = kk + ti; px = tp
        else:  # AR trail: BE (+fee cover) after +1R, then behind each closed 5m candle (app trail_stop, ratchet only)
            fct = int(math.ceil(self.fee / self.tickval))
            st = stop; best = e; be_done = False; j = NB - 1; px = None
            risk = Dc(float(abs(e - stop))); De = Dc(float(e))
            for jj in range(kk, NB):
                hj, lj = h[jj], l[jj]
                if (s > 0 and lj <= st) or (s < 0 and hj >= st):
                    j = jj; oj = o[jj]; px = (min(st, oj) if s > 0 else max(st, oj)) - s * tk; break
                if jj > kk:
                    best = max(best, hj) if s > 0 else min(best, lj)
                    close5 = (jj + 1) % 5 == 0
                    crossed = (not be_done) and (best - e) * s >= risk_pts
                    if close5 or crossed:
                        cm = (jj + 1) // 5 - 1
                        lc = None
                        if cm >= 0 and (cm + 1) * 5 - 1 > kk:
                            lc = (Dc(float(self.H5[di, cm])), Dc(float(self.L5[di, cm])))
                        ns = float(trail_stop(DIR[s], De, risk, Dc(float(st)), Dc(float(best)), lc, Dc("1.0"), fct, Dc("0.25"), Dc(float(c[jj]))))
                        st = ns
                        if crossed: be_done = True
            if px is None: px = c[NB - 1] - s * tk
        seg = slice(kk, j + 1)
        mae = ((e - l[seg].min()) if s > 0 else (h[seg].max() - e)) * pv + tk * pv
        return (px - e) * s * pv - self.fee, j, max(mae, 0.0), e

    # ---------------------------------------------------------------- day simulation
    def simulate(self, k, loc, cas, mode, path=False, cand=None, count=None):
        cand = cand if cand is not None else self.candidates(k)
        cands, cf = cand
        rules = ArRules(required=True, allowed_envs=("EXPANSION", "ROTATION"), location_filter=loc, fib_min=FIB_LO, fib_max=FIB_HI,
                        value_side="OUTSIDE_VALUE", path_filter=path, path_block_zone="MAX", confirm_max_age_min=3, require_real_delta=False)
        crules = CasperRules(price_confirms=cas, stacked_definition=cas)
        rows = []
        for di, lst in cands.items():
            t_free = 0; n = 0
            for (m, s) in lst:
                if n >= 3: break
                T = 5 * (m + 1)
                if T < t_free: continue
                f, info = self.fields(di, m, s)
                if count is not None:   # report which layer stops the candidate at the first entry bar
                    sk = check_ar(DIR[s], (di * 1440 + 570 + T) * 60_000, f, rules)
                    count[sk.code if sk else "PASS"] = count.get(sk.code if sk else "PASS", 0) + 1
                    if sk: continue
                kind = int(cf[s][di, m])
                pl = self.plan(di, m, s, kind)
                if isinstance(pl, OrderFlowSkip): continue
                lim, stop, tp = float(pl.entry), float(pl.stop), float(pl.take_profit)
                for j in range(3):
                    kk = T + j
                    if kk > 360: break
                    oo, hh, ll = self.o[di, kk], self.h[di, kk], self.l[di, kk]
                    if (s > 0 and oo <= stop) or (s < 0 and oo >= stop): break          # stop traded first -> cancel
                    if not ((s > 0 and ll <= lim) or (s < 0 and hh >= lim)): continue
                    sk = check_ar(DIR[s], (di * 1440 + 570 + kk) * 60_000, f, rules)
                    if sk: break
                    pb = kk - 1; rg = self.h[di, pb] - self.l[di, pb]
                    cp = 0.5 if rg <= 0 else (self.c[di, pb] - self.l[di, pb]) / rg
                    cfd = CasperFields(close_pos=Dc(round(float(cp), 4)), stacked=int((self.stk_buy if s > 0 else self.stk_sell)[di, m]))
                    if check_casper(DIR[s], pl.kind, cfd, crules): break
                    fill = min(lim, oo) if s > 0 else max(lim, oo)
                    e = fill + s * self.tick; pts = (e - stop) * s
                    if pts <= 0: break
                    pnl, xk, mae, e = self.walk(di, s, kk, fill, stop, tp, mode, pts)
                    n += 1; t_free = xk + 1
                    rows.append(dict(d=self.dates[di], di=di, ek=kk, xk=xk, pnl=pnl, mae=mae, risk=pts * self.pv + self.fee + self.tick * self.pv,
                                     side=s, m=m, kind=kind, fill=fill, e=e, sd=pts, tpd=(tp - e) * s, stop=stop, tp=tp, lim=lim))
                    break
        return rows

    def random_side(self, rows, mode, seed):
        rng = np.random.default_rng(seed); out = []
        for r in rows:
            s = 1 if rng.random() < 0.5 else -1
            e = r["fill"] + s * self.tick; stop = e - s * r["sd"]; tp = e + s * r["tpd"]
            pnl, *_ = self.walk(r["di"], s, r["ek"], r["fill"], stop, tp, mode, r["sd"])
            out.append(pnl)
        return np.array(out)

    # ---------------------------------------------------------------- footprint ladder with the APP's own code (snapshots / validation)
    def app_ladder(self, di, m, scale=1000.0):
        bars = []
        prev = Dc(float(self.c[di, m * 5 - 1])) if m else None
        for kk in range(m * 5, m * 5 + 5):
            bars.append(FP.BarIn(kk, Dc(float(self.o[di, kk])), Dc(float(self.h[di, kk])), Dc(float(self.l[di, kk])), Dc(float(self.c[di, kk])), Dc(round(float(self.vol[di, kk]) * scale, 4))))
        fpb = FP.footprint(bars, Dc(str(self.row)))
        agg = {}
        for b in fpb:
            for x in b.levels:
                bid, ask = agg.get(x.price, (Dc(0), Dc(0))); agg[x.price] = (bid + x.bid, ask + x.ask)
        return agg
