"""Session 13: gate study on NOISE + PM fade (MNQ, 1 micro). Variants are VETO hooks (a gate can only block; a vetoed NOISE entry consumes
that check's entry, a vetoed fade ends the day's fade) on top of the session-12 trade generators. Pick on 2021-11..2023-12, judge 2024-01..2026-10."""
import sys, pickle, json, itertools, random
import numpy as np, pandas as pd
ROOT = "/home/user/opogabuuga"; HERE = ROOT + "/docs/results/session13"
sys.path[:0] = [ROOT + "/docs/results/session12"]
import ob_study as S
days, mes = S.load()
F = {j: pickle.load(open(f"{HERE}/feat_{j}.pkl", "rb")) for j in ("mso1", "mso5", "fr15", "fr60")}
DAYIDX = {d: i for i, (d, _) in enumerate(days)}
oc = {d: (a["close"][~np.isnan(a["close"])][-1] > a["open"][0]) for d, a in days}   # session open->close direction (the ledger's outcome)

def gen(bn=None, bf=None, maxtr=3, band=2.0, k0=210, k1=359, nd=None):
    vN = (lambda d, k, s, p: bn(d, k, s)) if bn else None
    vF = (lambda d, k, s, p: bf(d, k, s)) if bf else None
    nt = S.noise_t(days, vN, None, maxtr=maxtr)
    if nd is None: nd = set(d for d, *_ in S.noise_t(days, None, None, maxtr=3))
    ft = S.pm_fade(days, nd, vF, None, band=band, k0=k0, k1=k1)
    return pd.DataFrame(nt + ft, columns=["date", "pnl", "strategy", "entry_time"])
BASE_ND = set(d for d, *_ in S.noise_t(days, None, None))

# ---- Lucid Pro 25K eval, rolling starts: EOD trailing $1,000 MLL (locks at +$1,100 -> floor start+100), target +$1,250, 1 micro.
def eval_sim(t, horizon=400):
    ds = sorted(t.date.unique()); alld = [d for d, _ in days if S.START <= d <= S.END]
    by = {d: g.sort_values("entry_time").pnl.values for d, g in t.groupby("date")}
    res = []
    for i, d0 in enumerate(alld):
        bal = peak = 0.0; mll = -1000.0; out = None
        for j, d in enumerate(alld[i:i + horizon]):
            for p in by.get(d, []):
                bal += p
                if bal <= mll: out = "bust"; break
            if out: break
            peak = max(peak, bal); mll = max(mll, min(peak - 1000, 100)) if peak < 1100 else 100.0
            if bal >= 1250: out = "pass"; break
        if out is None and i + horizon > len(alld) - 0: continue   # unresolved at end of data
        res.append((d0, out or "open", j + 1))
    r = pd.DataFrame(res, columns=["d0", "out", "days"])
    def f(x): return dict(n=len(x), bust=100 * (x.out == "bust").mean(), pas=100 * (x.out == "pass").mean(), medp=float(x[x.out == "pass"].days.median()) if (x.out == "pass").any() else 0.0)
    return f(r[r.d0 <= S.SPLIT]), f(r[r.d0 > S.SPLIT])

def summ(t):
    a, b = S.halves(t)
    ea, eb = eval_sim(t)
    nd_is = len([d for d, _ in days if S.START <= d <= S.SPLIT]); nd_ho = len([d for d, _ in days if d > S.SPLIT and d <= S.END])
    return dict(IS=dict(a, tpd=a["n"] / nd_is, **{"bust": ea["bust"], "pass": ea["pas"], "medp": ea["medp"]}),
                HO=dict(b, tpd=b["n"] / nd_ho, **{"bust": eb["bust"], "pass": eb["pas"], "medp": eb["medp"]}))

def line(name, r):
    a, b = r["IS"], r["HO"]
    return f"{name:44s} IS n{a['n']:4.0f} {a['tpd']:.2f}/d win{a['win']:5.1f} PF{a['pf']:.2f} ${a['usd']:7.0f} dd{a['dd']:5.0f} bust{a['bust']:5.1f} pass{a['pass']:5.1f} | HO n{b['n']:4.0f} {b['tpd']:.2f}/d win{b['win']:5.1f} PF{b['pf']:.2f} ${b['usd']:7.0f} dd{b['dd']:5.0f} bust{b['bust']:5.1f} pass{b['pass']:5.1f}"

# ---- gate hooks
def hour_block(bad):  # block NOISE checks at these k
    return lambda d, k, s: k in bad
def mso(j, mode, wd=None):
    def g(d, k, s):
        tr, ab, ae = F[j][d]
        if mode == "agree": return tr[k] != s
        if mode == "noopp": return tr[k] == -s
        if mode == "nodiv":   # no opposing divergence in the last wd minutes (opposing a long = bearish div)
            return (ae[k] if s > 0 else ab[k]) <= wd
        if mode == "needdiv": return (ab[k] if s > 0 else ae[k]) > wd
    return g
def frac(j, mode):
    def g(d, k, s):
        st, dr = F[j][d]; on = st[k] >= 1
        if mode == "agree": return not (on and dr[k] == s)
        return on and dr[k] == -s
    return g
def both(*fs): return lambda d, k, s: any(f(d, k, s) for f in fs)
def bias_gate(acc, cov, seed):
    rng = random.Random(seed); call = {}
    for d, _ in days:
        if rng.random() < cov:
            up = oc[d]; call[d] = (1 if up else -1) if rng.random() < acc else (-1 if up else 1)
    return lambda d, k, s: d in call and call[d] != s

if __name__ == "__main__":
    out = {}
    def run(name, **kw):
        t = gen(nd=BASE_ND, **kw); r = summ(t); out[name] = r; print(line(name, r), flush=True); return r
    run("A  current (maxtr3, fade 13:00-15:29, 2sd)")
    # B: config-tunable gate knobs
    for mt in (1, 2): run(f"B maxtr={mt}", maxtr=mt)
    for bd in (1.5, 2.5): run(f"B fade band={bd}", band=bd)
    for k0 in (150, 270): run(f"B fade start k0={k0}", k0=k0)
    run("B fade end k1=330", k1=330)
    for kk, nm in ((29, "10:30"), (89, "11:30"), (149, "12:30"), (209, "13:30"), (269, "14:30"), (329, "15:30")):
        run(f"B drop NOISE check {nm}", bn=hour_block({kk}))
    run("B drop NOISE 10:30+11:30", bn=hour_block({29, 89}))
    run("B only NOISE <=13:30", bn=hour_block({269, 329}))
    json.dump(out, open(HERE + "/grid_B.json", "w"), default=float)
