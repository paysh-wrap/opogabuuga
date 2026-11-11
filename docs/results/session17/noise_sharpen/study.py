"""Session 17 NOISE sharpening: stage 1 = trade-stream grids (every parameter chosen on IS only), writes stage1.json + streams/*.csv.
usage: S15_RAW=<folder with mnq_5y.csv> python3 study.py"""
import sys, os, json, itertools, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from multiprocessing import Pool
import numpy as np, pandas as pd
import sharpen as S

CHK = [29, 89, 149, 209, 269, 329]
HN = {29: "10:00", 89: "11:00", 149: "12:00", 209: "13:00", 269: "14:00", 329: "15:00"}


def variants(base_is=None):
    v = {"BASE (lock 100->+10)": {}}
    for tr in (75, 100, 125):
        for lk in (10, 25, 50):
            if (tr, lk) != (100, 10): v[f"lock {tr}->+{lk}"] = dict(lock=(tr, lk))
    for h in CHK: v[f"no entry {HN[h]}"] = dict(hours=set(CHK) - {h})
    for a, b in itertools.combinations(CHK, 2): v[f"no entry {HN[a]}+{HN[b]}"] = dict(hours=set(CHK) - {a, b})
    v["no reverse after stop-out"] = dict(norev="stop")
    v["no flip after any exit"] = dict(norev="any")
    v["VWAP side filter"] = dict(vwapf="side")
    v["VWAP side+slope filter"] = dict(vwapf="slope")
    return v


def job(a):
    name, kw = a
    t = S.gen(**kw)
    return name, kw, t


if __name__ == "__main__":
    t0 = time.time(); os.makedirs(HERE + "/streams", exist_ok=True)
    S.days("MNQ")
    v = variants()
    with Pool(4) as p: res = p.map(job, list(v.items()), chunksize=1)
    base = [t for n, k, t in res if n.startswith("BASE")][0]
    # width filter thresholds from IS quantiles of the base trades' band width / sigma (IS only)
    bi = base[base.d <= S.SPLIT]
    wq = {q: float(bi.width.quantile(q / 100)) for q in (10, 20, 30, 40)}
    sq = {q: float(bi.sigk.quantile(q / 100)) for q in (10, 20, 30, 40)}
    extra = {f"min band width >= IS p{q} ({wq[q]:.0f} pt)": dict(minw_pts=wq[q]) for q in wq}
    extra.update({f"min sigma >= IS p{q} ({100*sq[q]:.2f}%)": dict(min_sig=sq[q]) for q in sq})
    with Pool(4) as p: res += p.map(job, list(extra.items()), chunksize=1)
    out = {}
    for n, k, t in res:
        fn = "".join(ch if ch.isalnum() else "_" for ch in n)
        t.to_csv(f"{HERE}/streams/{fn}.csv", index=False)
        out[n] = dict(file=fn, kw={kk: (sorted(vv) if isinstance(vv, set) else vv) for kk, vv in k.items()},
                      **{era: S.stats(t, era) for era in ("IS", "HO", "L12")})
    # per-check-hour table of the base (IS and HO)
    hr = {}
    for h in CHK:
        x = base[base.sk == h]
        hr[HN[h]] = {era: S.stats(x, era) for era in ("IS", "HO")}
    json.dump(dict(variants=out, hours=hr, wq=wq, sq=sq), open(HERE + "/stage1.json", "w"), indent=1)
    print("done", round(time.time() - t0), "s;", len(out), "variants")
