"""Stage 1+2 of the NOISE sharpening study (all variants, IS + held-out, eval simulation). Writes study.json and streams/*.csv.
usage: python -I run_study.py"""
import os, sys, json, itertools, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from multiprocessing import Pool
import numpy as np, pandas as pd
import nz, sim

CHK = [29, 89, 149, 209, 269, 329]
HN = {29: "10:00", 89: "11:00", 149: "12:00", 209: "13:00", 269: "14:00", 329: "15:00"}
LOCKS = {"nolock": None, "lock": (100, 10)}


def _lv(f): return f["lowvol"]
def _mon(f): return f["dow"] == 0
def _fri(f): return f["dow"] == 4
def _lvmon(f): return f["lowvol"] or f["dow"] == 0
def _monfri(f): return f["dow"] in (0, 4)


def fam_variants(lockname):
    lk = LOCKS[lockname]; b = dict(lock=lk); tag = f" [{lockname}]"; V = {}
    V["BASE" + tag] = ("base", b)
    V["N10 skip low-vol tercile" + tag] = ("N10-12", dict(b, dayskip=_lv))
    V["N11 skip Monday" + tag] = ("N10-12", dict(b, dayskip=_mon))
    V["N12 skip Friday" + tag] = ("N10-12", dict(b, dayskip=_fri))
    V["N10+N11" + tag] = ("N10-12", dict(b, dayskip=_lvmon))
    V["N11+N12 (Tue-Thu only)" + tag] = ("N10-12", dict(b, dayskip=_monfri))
    V["VWAP side filter" + tag] = ("vwap", dict(b, vwapf="side"))
    V["VWAP side+slope filter" + tag] = ("vwap", dict(b, vwapf="slope"))
    for h in CHK: V[f"no entry {HN[h]}" + tag] = ("hours", dict(b, hours=set(CHK) - {h}))
    V["no reverse after stop-out" + tag] = ("norev", dict(b, norev="stop"))
    V["no flip after any exit" + tag] = ("norev", dict(b, norev="any"))
    V["extra check 15:30 (band entry)" + tag] = ("addon-1530", dict(b, extra_checks=(359,)))
    return V


def lock_variants():
    V = {}
    for tr in (50, 75, 100, 125, 150, 200):
        for lk in (0, 10, 25, 50):
            if lk < tr: V[f"lock {tr}->+{lk}"] = ("lock", dict(lock=(tr, lk)))
    for tr in (75, 100, 150):
        for g in (40, 60, 100):
            V[f"trail-lock +{tr} give back {g}"] = ("tlock", dict(tlock=(tr, g)))
    V["session-9 original (1% stop) [nolock]"] = ("stop", dict(stop_usd=None, stop_pct=0.01))
    return V


def job(a):
    name, fam, kw = a
    t = nz.gen(**kw)
    fn = "".join(ch if ch.isalnum() else "_" for ch in name)
    t.to_csv(f"{HERE}/streams/{fn}.csv", index=False)
    o = dict(name=name, fam=fam, file=fn, kw={k: (sorted(v) if isinstance(v, set) else (v.__name__ if callable(v) else v)) for k, v in kw.items()})
    for e in ("IS", "HO"):
        o[e] = nz.stats(t, e)
        o[e]["roll"] = sim.eval_roll(t, e)
    o["HO"]["roll_strict"] = sim.eval_roll(t, "HO", strict=True)
    o["HO"]["boot"] = sim.eval_boot(t, "HO"); o["IS"]["boot"] = sim.eval_boot(t, "IS")
    x = nz.era(t, "IS"); o["IS"]["ratio"] = float(2 * x.pnl.mean() / x.pnl.std() ** 2 * 1000)
    x = nz.era(t, "HO"); o["HO"]["ratio"] = float(2 * x.pnl.mean() / x.pnl.std() ** 2 * 1000)
    return o


if __name__ == "__main__":
    t0 = time.time(); os.makedirs(HERE + "/streams", exist_ok=True); nz.days()
    V = {}
    for ln in LOCKS: V.update(fam_variants(ln))
    V.update(lock_variants())
    # width filters from IS quantiles of the base trades (IS only)
    for ln in LOCKS:
        b = nz.gen(lock=LOCKS[ln]); bi = b[b.d <= nz.SPLIT]
        for q in (10, 20, 30, 40):
            w = float(bi.width.quantile(q / 100)); s = float(bi.sigk.quantile(q / 100))
            V[f"min band width >= IS p{q} ({w:.0f} pt) [{ln}]"] = ("width", dict(lock=LOCKS[ln], minw_pts=w))
            V[f"min sigma >= IS p{q} ({100*s:.2f}%) [{ln}]"] = ("width", dict(lock=LOCKS[ln], min_sig=s))
    with Pool(4) as p: res = p.map(job, [(n, f, k) for n, (f, k) in V.items()], chunksize=1)
    json.dump(dict(variants={r["name"]: r for r in res}), open(HERE + "/study.json", "w"), indent=1, default=float)
    print("done", round(time.time() - t0), "s", len(res), "variants")
