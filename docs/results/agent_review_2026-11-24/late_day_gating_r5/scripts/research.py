"""Grid screen of 6 RTH-only ideas on MNQ. Pick on 2021-10..2023-12 (top PICK PF), judge 2024-01..2026-10.  Run: python3 -I research.py (from this dir)."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ne import *
from lib_ne import _ds
rng = np.random.default_rng(7)


def gen(strategy, p, rand=False):
    rows = []
    for d in DAYS:
        a = BARS[d]; c, o = a["close"], a["open"]; pc = PREV[d]; at = ATR[d]
        sig = None
        if strategy == "lastmom":        # first-30-min return (+ RTH gap) predicts the last 30 min (Gao/Han/Li/Zhou, RTH-only variant)
            r30 = c[29] - o[0]
            if abs(r30) < p["minr"] * at: continue
            s = np.sign(r30 + p["gapw"] * (o[0] - pc))
            if s == 0: continue
            sig = (int(s), 389 - p["hold"], 389, p["stop"], 0)
        elif strategy == "lastmom_day":  # trend so far today predicts the last 30 min
            r = c[p["ref"]] - o[0]
            if abs(r) < p["minr"] * at or r == 0 or p["ref"] >= 389 - p["hold"]: continue   # no lookahead: signal bar must precede entry
            sig = (int(np.sign(r)), 389 - p["hold"], 389, p["stop"], 0)
        elif strategy == "gapfade":
            gap = o[0] - pc
            if not (abs(gap) >= p["mingap"] * at): continue
            side = -int(np.sign(gap)) if p["mode"] == "fade" else int(np.sign(gap))
            tgt = abs(gap) * p["fill"] if p["mode"] == "fade" else 0
            sig = (side, p["e"], p["xend"], p["stop"] * at, tgt)
        elif strategy == "vwapmr":       # afternoon deviation from session VWAP -> revert
            v = a["vwap"]; found = None
            for k in range(p["t0"], p["t1"]):
                dev = c[k] - v[k]
                if abs(dev) >= p["dev"] * at: found = (k + 1, -int(np.sign(dev)), abs(dev)); break
            if not found: continue
            e, side, dv = found
            sig = (side, e, min(389, e + p["maxhold"]), p["stop"], dv * p["tgtfrac"])
        elif strategy == "lunchbrk":     # narrow lunch range breakout
            hi = a["high"][p["a"]:p["b"]].max(); lo = a["low"][p["a"]:p["b"]].min()
            if hi - lo > p["maxw"] * at: continue
            found = None
            for k in range(p["b"], p["b"] + p["win"]):
                if c[k] > hi: found = (k + 1, 1, hi - lo); break
                if c[k] < lo: found = (k + 1, -1, hi - lo); break
            if not found: continue
            e, side, w = found
            sig = (side, e, min(389, e + p["hold"]), min(p["stopcap"], max(8, w)), w * p["tgtw"])
        elif strategy == "tom":          # turn of month, long open->close
            i = _ds.index(d); mo = d[:7]
            nxt = _ds[i + 1][:7] if i + 1 < len(_ds) else mo; prv = _ds[i - 1][:7]
            if not ((nxt != mo and p["last"]) or (prv != mo and p["first"])): continue
            sig = (1, 0, 389, p["stop"], 0)
        if sig is None: continue
        side, e, xe, st, tg = sig
        if e >= xe: continue
        if rand: side = int(rng.choice([-1, 1]))
        pts, k = run_trade(a, e, side, st, tg, xe)
        rows.append(dict(day=d, idx=e, exit_idx=k, side=side, pts=pts, stop_pts=st))
    return pd.DataFrame(rows)


def judge_pf(t):
    j = t[t.day >= JUDGE0]; net = j.pts - COST_PTS
    w, l = net[net > 0].sum(), -net[net < 0].sum()
    return w / l if l > 0 else 9


def evaluate(strategy, p, nrand=15):
    tr = gen(strategy, p)
    if len(tr) < 30: return None
    s = stats(tr)
    pf = [judge_pf(gen(strategy, p, rand=True)) for _ in range(nrand)]
    s["rand_judge_pf_mean"] = round(float(np.mean(pf)), 3); s["rand_judge_pf_p95"] = round(float(np.percentile(pf, 95)), 3)
    return tr, s


GRIDS = {
    "lastmom": [dict(gapw=g, minr=m, hold=h, stop=st) for g in (0, 1) for m in (0, 0.1) for h in (29, 44, 59) for st in (30, 60)],
    "lastmom_day": [dict(ref=r, minr=m, hold=h, stop=st) for r in (239, 299, 329, 359) for m in (0, 0.1, 0.2) for h in (29, 44, 59) for st in (30, 60)],
    "gapfade": [dict(mode=md, mingap=mg, e=e, xend=xe, stop=st, fill=f) for md in ("fade", "cont") for mg in (0.3, 0.5, 0.8) for e in (5, 30) for xe in (120, 389) for st in (0.2, 0.35) for f in (0.5, 1.0)],
    "vwapmr": [dict(t0=t0, t1=330, dev=dv, maxhold=mh, stop=st, tgtfrac=tf) for t0 in (210, 270) for dv in (0.25, 0.4, 0.6) for mh in (60, 120) for st in (25, 40) for tf in (0.7, 1.0)],
    "lunchbrk": [dict(a=a, b=b, maxw=mw, win=w, hold=h, stopcap=sc, tgtw=tw) for (a, b) in ((120, 240), (150, 270)) for mw in (0.3, 0.5) for w in (60, 120) for h in (60, 120) for sc in (25, 40) for tw in (1.0, 2.0)],
    "tom": [dict(last=l, first=f, stop=st) for l, f in ((1, 0), (1, 1), (0, 1)) for st in (80, 150)],
}
if __name__ == "__main__":
    out = {}
    for st, grid in GRIDS.items():
        res = []
        for p in grid:
            ev = evaluate(st, p)
            if ev: res.append((p, ev[1]))
        res = [r for r in res if r[1]["pick"]["n"] >= 40 and r[1]["pick"]["pf"]]
        res.sort(key=lambda r: -r[1]["pick"]["pf"])
        out[st] = dict(ncfg=len(grid), top=[dict(p=p, **s) for p, s in res[:5]])
        print("==", st, len(res), "cfgs", flush=True)
        for p, s in res[:5]:
            print(json.dumps(p), "PICK", s["pick"]["n"], s["pick"]["pf"], "| JUDGE", s["judge"]["n"], s["judge"]["pf"], s["judge"]["wr"], "| rnd", s["rand_judge_pf_mean"], s["rand_judge_pf_p95"], flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "grid_out.json"), "w"), indent=1, default=float)
