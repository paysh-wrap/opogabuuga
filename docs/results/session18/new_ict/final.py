"""Stage 2: eval sim, random benchmark, NOISE preset C baseline -> tables.md / tables.json. PYTHONPATH=. python3 final.py"""
import sys, pickle, json, itertools
import numpy as np, pandas as pd, lib
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session17/noise_sharpen")
import sim
out = pickle.load(open("sims.pkl", "rb")); S = {}
for (win, tf, lev, disp), n, res in out:
    for k, df in res.items(): S[(win, tf, lev, disp) + k] = df
WSN = {"AM": ["AM"], "PM": ["PM"], "LON": ["LON"], "AM+PM": ["AM", "PM"], "ALL3": ["AM", "PM", "LON"]}

def build(wn, tf, lev, disp, entry, tgt, md, bias, gm):
    df = pd.concat([S[(w, tf, lev, disp, entry, tgt)] for w in WSN[wn]], ignore_index=True)
    return lib.select(df, md, None, None if bias == "-" else bias, gm)

ROWS = [  # label, kind, params   kind: DEF = untuned canonical (pre-registered before looking), PICK = IS rule, EXP = post-hoc exploratory
 *[(f"{w} 1m-FVG mid 2R (untuned)", "DEF", (w, 1, "all", 1.0, "mid", 2.0, 1, "-", 0.0)) for w in WSN],
 *[(f"{w} 1m-FVG mid 1.5R (untuned)", "DEF", (w, 1, "all", 1.0, "mid", 1.5, 1, "-", 0.0)) for w in ("PM", "AM+PM", "ALL3")],
 ("ALL3 5m-FVG mid 2R (untuned)", "DEF", ("ALL3", 5, "all", 1.0, "mid", 2.0, 1, "-", 0.0)),
 ("ALL3 1m-FVG mid liq-target (untuned)", "DEF", ("ALL3", 1, "all", 1.0, "mid", "liq", 1, "-", 0.0)),
 ("PM 1m mid 2R, max 2/day (untuned)", "DEF", ("PM", 1, "all", 1.0, "mid", 2.0, 2, "-", 0.0)),
]
# IS-rule picks per window set (eligible: IS n>=100, IS PF>=1.15, best 2*mean/sd^2)
g = pd.read_csv("grid.csv"); g["ratio"] = 2 * g.IS_avg / g.IS_sd ** 2
e = g[(g.IS_n >= 100) & (g.IS_pf >= 1.15)]
for w, x in e.groupby("win"):
    r = x.sort_values("ratio", ascending=False).iloc[0]
    tgt = r.tgt if r.tgt == "liq" else float(r.tgt)
    ROWS.append((f"IS-pick {w}: {r.tf}m {r.lev} d{r.disp} {r.entry} {r.tgt}R md{r.maxday} bias {r.bias} gap>={r.gapmin}", "PICK", (w, int(r.tf), r.lev, float(r.disp), r.entry, tgt, int(r.maxday), r.bias, float(r.gapmin))))
r = e.sort_values("ratio", ascending=False).iloc[0]
ROWS += [("EXP ALL3 1m mid 1.5R + 1H bias + gap>=0.5ATR (2nd IS rank)", "EXP", ("ALL3", 1, "all", 1.0, "mid", 1.5, 1, "1h", 0.5)),
         ("EXP PM 1m mid 2R + prior-day bias", "EXP", ("PM", 1, "all", 1.0, "mid", 2.0, 1, "pd", 0.0)),
         ("EXP AM+PM 1m mid 2R + 1H bias", "EXP", ("AM+PM", 1, "all", 1.0, "mid", 2.0, 1, "1h", 0.0))]

def evals(t, e="HO", strict=True, boot=True):
    r = sim.eval_roll(t, e)
    d = dict(roll=f"{r['pass_']:.0f} / {r['bust']:.0f}", med=("-" if np.isnan(r["med"]) else f"{r['med']:.0f}"))
    if boot:
        b = sim.eval_boot(t, e); d["boot"] = f"{b['pass_']:.0f} / {b['bust']:.0f}"
        s = sim.eval_roll(t, e, strict=True); d["strict"] = f"{s['pass_']:.0f} / {s['bust']:.0f}"
    return d

def hoin(t, e): return t[t.d <= lib.SPLIT] if e == "IS" else t[t.d > lib.SPLIT]

def rand_bench(t, tgt, hold=60, seeds=20, boot=False):
    """random direction + random minute inside the same window, market entry (+1 tick), stop distance and day of each real trade, same TP multiple (2R for liq), same time exit"""
    D = lib.load(); o, h, l, c = D["o"], D["h"], D["l"], D["c"]; n = len(c); tm = 2.0 if tgt == "liq" else float(tgt)
    res = []
    for sd in range(seeds):
        rng = np.random.default_rng(sd); rows = []
        for r in t.itertuples():
            m0, m1 = lib.WINS[r.win]; i0 = np.searchsorted(D["t"], r.day * 1440 + m0); i1 = np.searchsorted(D["t"], r.day * 1440 + m1)
            k = int(rng.integers(i0, i1 - 1)); dr = 1 if rng.random() < .5 else -1
            R = r.rpts; E = o[k + 1] + dr * lib.TICK; stop = E - dr * R; tp = E + dr * tm * R
            tend = min(np.searchsorted(D["t"], r.day * 1440 + m1 + hold), n - 1); ex = None; mae = 0.0
            for b in range(k + 1, tend + 1):
                mae = max(mae, ((E - l[b]) if dr == 1 else (h[b] - E)) * lib.PV)
                if (dr == 1 and l[b] <= stop) or (dr == -1 and h[b] >= stop):
                    ex = (min(stop, o[b]) - lib.TICK) if dr == 1 else (max(stop, o[b]) + lib.TICK); break
                if b > k + 1 and ((dr == 1 and h[b] >= tp + lib.TICK) or (dr == -1 and l[b] <= tp - lib.TICK)): ex = tp; break
            if ex is None: ex = c[tend] - dr * lib.TICK
            rows.append(dict(d=r.d, day=r.day, pnl=(ex - E) * dr * lib.PV - lib.FEE, mae=mae + lib.TICK * lib.PV))
        res.append(pd.DataFrame(rows))
    return res

def fmt(s): return f"{s['n']} | {s['win']:.1f} | {s['avg']:.1f} | {s['net']:,.0f} | {s['dd']:,.0f} | {s['pf']:.2f}"

lines = []; J = []
hdr = "| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | eval roll PASS/BUST % | days to pass (med) | boot PASS/BUST % | strict PASS/BUST % | IS trades / $/tr / PF |\n|---|---|---|---|---|---|---|---|---|---|---|---|"
lines.append(hdr)
base = pd.read_csv("/home/user/opogabuuga/docs/results/session17/noise_sharpen/streams/BASE__lock_.csv")
def addrow(label, t):
    h_ = hoin(t, "HO"); i_ = hoin(t, "IS"); s = lib.stats(h_); si = lib.stats(i_)
    ev = evals(h_.assign(d=h_.d)) if len(h_) > 5 else dict(roll="-", med="-", boot="-", strict="-")
    lines.append(f"| {label} | {fmt(s)} | {ev['roll']} | {ev['med']} | {ev['boot']} | {ev['strict']} | {si['n']} / {si['avg']:.1f} / {si['pf']:.2f} |")
    J.append(dict(label=label, ho=s, ist=si, ev=ev))
    return ev
addrow("NOISE preset C (baseline, 427 HO trades)", base)
rb = {}
for label, kind, p in ROWS:
    t = build(*p); tg = p[5]
    addrow(f"[{kind}] {label}", t)
    if kind in ("DEF", "PICK") and len(hoin(t, "HO")) > 20 and not label.startswith("PM 1m mid 2R, max"):
        rr = rand_bench(hoin(t, "HO"), tg)
        st = [lib.stats(x) for x in rr]
        s = {k: float(np.mean([x[k] for x in st])) for k in ("n", "win", "avg", "net", "dd", "pf")}
        ev = [sim.eval_roll(x, "HO") for x in rr]
        lines.append(f"| &nbsp;&nbsp;random-entry, same exits ({len(rr)} seeds mean) | {fmt(s)} | {np.mean([x['pass_'] for x in ev]):.0f} / {np.mean([x['bust'] for x in ev]):.0f} | - | - | - | - |")
        rb[label] = dict(s=s, pass_=float(np.mean([x['pass_'] for x in ev])), bust=float(np.mean([x['bust'] for x in ev])))
open("tables.md", "w").write("\n".join(lines) + "\n")
json.dump(J, open("tables.json", "w"), indent=1, default=float)
print("\n".join(lines))
