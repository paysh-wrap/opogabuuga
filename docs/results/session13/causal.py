"""Causal (no hindsight) NOISE + PM-fade generator. Fade at minute k is allowed only if NO NOISE entry signal has fired at a check <= k
(live rule 'no NOISE trade yet'); NOISE signals later the same day still trade unless the fade position is open. Reuses ob_ex (session-12 code + exit index)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session13")
import ob_ex as X
from study import days, F, DAYIDX, S, summ, line, HERE, oc
import study as ST

def gen_c(bn=None, bf=None, maxtr=3, band=2.0, k0=210, k1=359, hind=False):
    vN = (lambda d, k, s, p: bn(d, k, s)) if bn else None
    nt = X.noise_t(days, vN, None, maxtr=maxtr)          # (d, pnl, "NOISE", hm, ek, xk)
    nb = {}
    for t in nt: nb.setdefault(t[0], []).append(t)
    out = []
    for d, a in days:
        if d < S.START or d > S.END: continue
        o, h, l, c, vw = a["open"], a["high"], a["low"], a["close"], a["vwap"]
        trs = nb.get(d, []); fade = None
        for k in range(k0, k1):
            if hind and trs: break
            if (not hind) and any(t[4] - 1 <= k for t in trs): break     # a NOISE signal already fired -> no fade today
            if np.isnan(c[k]) or np.isnan(vw[k]): continue
            sd = np.nanstd(c[:k + 1] - vw[:k + 1])
            if sd <= 0: continue
            s = -1 if c[k] > vw[k] + band * sd else (1 if c[k] < vw[k] - band * sd else 0)
            if not s: continue
            e = o[k + 1] + s * X.TICK
            if (vw[k] - e) * s < 4 * X.TICK: break
            if bf and bf(d, k, s): break
            stop = e - s * X.PTS
            p, xk = X.walk(s, e, stop, vw[k], h, l, o, c, k + 1, 386)
            fade = (d, p, "FADE", X.hm(k + 1), k + 1, xk); break
        if fade:
            trs = [t for t in trs if not (fade[4] <= t[4] <= fade[5])]    # NOISE entry while the fade is open is skipped
            out.append(fade)
        out += trs
    return pd.DataFrame([x[:4] for x in out], columns=["date", "pnl", "strategy", "entry_time"])

if __name__ == "__main__":
    import json
    out = {}
    def run(name, **kw):
        t = gen_c(**kw); r = summ(t); out[name] = r; print(line(name, r), flush=True)
    run("A hindsight (as D55)", hind=True)
    run("A causal k0=210")
    for k0 in (30, 60, 90, 120, 150, 180): run(f"causal fade k0={k0}", k0=k0)
    for k0 in (150,):
        for bd in (1.5, 2.5): run(f"causal fade k0={k0} band={bd}", k0=k0, band=bd)
    json.dump(out, open(HERE + "/grid_causal.json", "w"), default=float)
