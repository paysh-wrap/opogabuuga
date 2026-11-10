"""eval_speed_run.py stage1|stage2 - runs variant grids, writes eval_speed_<stage>.json. Variants = overrides on the LIVE cfg."""
import os as _os; ROOT = _os.environ.get("PAYTIENCE_ROOT") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..", ".."))
import sys, json
sys.dont_write_bytecode = True
from multiprocessing import Pool
import eval_speed_engine as E
C30 = E.C30
COMMON = {
 "BASE (live)": {},
 "1a 30-min checks": dict(checks=C30), "1b 5 entries/day": dict(maxtr=5), "1c 30-min + 5 entries": dict(checks=C30, maxtr=5),
 "1d opening-drive": dict(od=True), "1e 30-min + 5 + open-drive": dict(checks=C30, maxtr=5, od=True),
 "2a frozen: $100 stop tier": dict(tier=100), "2b frozen: $125 stop tier": dict(tier=125), "2c frozen: $150 stop tier": dict(tier=150),
 "2d recover-mode fewer micros": dict(recover=True),
 "2e shrink 0.7": dict(shrink=0.7), "2f shrink 0.8": dict(shrink=0.8), "2g min-stop 0.15%": dict(min_pct=0.0015), "2h min-stop 0.10%": dict(min_pct=0.001),
 "2i shrink 0.8 + min-stop 0.10%": dict(shrink=0.8, min_pct=0.001), "2j fade under D57 (no pause floor)": dict(fade_tighten=True),
 "4a day cap 35% of target": dict(day_cap=0.35),
 "4b IF 40% rule applied: live": dict(consist=0.4), "4c IF 40% rule applied: day cap 35%": dict(consist=0.4, day_cap=0.35),
 "4d IF 40% rule applied: day cap 25%": dict(consist=0.4, day_cap=0.25),
}
F = lambda q, t: dict(sizer=("front", q, t))
PR = lambda u, lo, hi: dict(sizer=("prop", u, lo, hi))
SIZ = {
 "25K": {"3a front 2 @peak": F(2, 1.0), "3b front 2 >=90%": F(2, .9), "3c front 3 @peak": F(3, 1.0), "3d prop $500/micro max2": PR(500, 1, 2), "3e prop $400/micro max3": PR(400, 1, 3)},
 "25K-HR": {},
 "50K": {"3a front 3 @peak": F(3, 1.0), "3b front 3 >=90%": F(3, .9), "3c front 4 @peak": F(4, 1.0), "3d front 4 >=90%": F(4, .9),
         "3e prop $1000/micro max3": PR(1000, 1, 3), "3f prop $700/micro max4": PR(700, 1, 4), "3g prop $500/micro max4": PR(500, 1, 4)},
 "100K": {"3a front 3 @peak": F(3, 1.0), "3b front 4 @peak": F(4, 1.0), "3c front 4 >=90%": F(4, .9), "3d front 6 @peak": F(6, 1.0),
          "3e prop $1000/micro max4": PR(1000, 1, 4), "3f prop $750/micro max4": PR(750, 1, 4), "3g prop $600/micro max6": PR(600, 1, 6)},
 "150K": {"3a front 5 @peak": F(5, 1.0), "3b front 6 @peak": F(6, 1.0), "3c front 6 >=90%": F(6, .9), "3d front 8 @peak": F(8, 1.0),
          "3e prop $1125/micro max4": PR(1125, 1, 4), "3f prop $900/micro max6": PR(900, 1, 6), "3g prop $750/micro max6": PR(750, 1, 6), "3h prop $750/micro max8": PR(750, 1, 8)},
}
def stage1(): return {p: {**COMMON, **SIZ[p]} for p in SIZ}
def stage2():
    X = dict(checks=C30, maxtr=5); XO = dict(checks=C30, maxtr=5, od=True); OD = dict(od=True); R = dict(recover=True)
    g = {}
    for p in SIZ:
        v = {"BASE (live)": {}}
        for a in (0.1, 0.15, 0.2, 0.25, 0.3, 0.4): v[f"5 reset when cushion < {a:.0%} MLL"] = dict(abandon=a)
        v["OD + shrink .7"] = {**OD, "shrink": .7}; v["OD + reset<20%"] = {**OD, "abandon": .2}
        v["30m+5+OD + shrink .7"] = {**XO, "shrink": .7}; v["30m+5+OD + reset<20%"] = {**XO, "abandon": .2}
        v["OD + min .10%"] = {**OD, "min_pct": .001}; v["shrink .7 + reset<20%"] = dict(shrink=.7, abandon=.2)
        if p == "25K-HR":
            v["rec + min .10%"] = {**R, "min_pct": .001}; v["rec + shrink .8 + min .10%"] = {**R, "min_pct": .001, "shrink": .8}
            v["rec + shrink .8"] = {**R, "shrink": .8}; v["rec + OD"] = {**R, **OD}; v["rec + 30m"] = {**R, "checks": C30}
            v["rec + 30m + OD + min .10%"] = {**R, "checks": C30, **OD, "min_pct": .001}
            v["rec + reset<15%"] = {**R, "abandon": .15}; v["rec + min .10% + reset<15%"] = {**R, "min_pct": .001, "abandon": .15}
            v["rec, 4 micros"] = {**R, "q": 4}; v["rec, 2 micros x $250"] = {**R, "q": 2, "bp": E.P.BP}; v["rec, 3 micros no taper"] = {**R, "taper": None}
        g[p] = v
    return g
def stage3():
    X = dict(checks=C30, maxtr=5, od=True); OD = dict(od=True); R = dict(recover=True); g = {p: {"BASE (live)": {}} for p in SIZ}
    g["25K"].update({"reset<15%": dict(abandon=.15), "OD + reset<15%": {**OD, "abandon": .15}, "OD + shrink .7 + reset<15%": {**OD, "shrink": .7, "abandon": .15}})
    h = g["25K-HR"]
    for a in (.15, .2, .25, .3): h[f"rec + reset<{a:.0%}"] = {**R, "abandon": a}
    h["rec 2x$250 + reset<15%"] = {**R, "q": 2, "bp": E.P.BP, "abandon": .15}; h["rec 2x$250 + reset<25%"] = {**R, "q": 2, "bp": E.P.BP, "abandon": .25}
    h["rec + OD + reset<15%"] = {**R, **OD, "abandon": .15}; h["rec + OD + reset<25%"] = {**R, **OD, "abandon": .25}
    h["rec + 30m + reset<15%"] = {**R, "checks": C30, "abandon": .15}
    g["50K"].update({"reset<5%": dict(abandon=.05), "OD + shrink .7": {**OD, "shrink": .7}, "OD + shrink .7 + reset<5%": {**OD, "shrink": .7, "abandon": .05}})
    g["100K"].update({"reset<10%": dict(abandon=.1), "OD + reset<10%": {**OD, "abandon": .1}, "30m+5+OD + reset<10%": {**X, "abandon": .1}, "shrink .7 + reset<10%": dict(shrink=.7, abandon=.1)})
    g["150K"].update({"reset<5%": dict(abandon=.05), "OD + reset<5%": {**OD, "abandon": .05}, "30m+5+OD + reset<5%": {**X, "abandon": .05}, "30m+5+OD + reset<10%": {**X, "abandon": .1}, "30m+5+OD + reset<15%": {**X, "abandon": .15}})
    return g
G = {}
def init(): G["n"], G["o"] = E.prep_all(); G["c"] = E.base_cfgs()
def work(j):
    p, nm, o = j; return p, nm, E.evaluate({**G["c"][p], **o}, G["n"], G["o"], E.HZ[p])
if __name__ == "__main__":
    st = sys.argv[1]; grid = {"stage1": stage1, "stage2": stage2, "stage3": stage3}[st]()
    jobs = [(p, nm, o) for p, v in grid.items() for nm, o in v.items()]
    with Pool(4, initializer=init) as pool: res = pool.map(work, jobs, chunksize=2)
    out = {}
    for p, nm, r in res: out.setdefault(p, {})[nm] = r
    json.dump(out, open(f"eval_speed_{st}.json", "w"), indent=1)
    for p, v in out.items():
        b = v["BASE (live)"]; print(f"\n{p}  (IS n={b['IS']['n']}, OOS n={b['OOS']['n']})   pass/bust/frozen/open med spp")
        for nm, r in v.items():
            a, c = r["IS"], r["OOS"]
            f = lambda x: f"{x['pas']:5.1f}/{x['bust']:4.1f}/{x['frozen']:5.1f}/{x['open']:4.1f} {x['med']:5.1f} {x['spp']:6.1f}"
            ok = all(x["bust"] <= b[e]["bust"] for e, x in (("IS", a), ("OOS", c))) and (
                 all(x["pas"] >= b[e]["pas"] + 3 for e, x in (("IS", a), ("OOS", c))) or
                 (all(x["spp"] <= 0.9 * b[e]["spp"] for e, x in (("IS", a), ("OOS", c))) and all(x["pas"] >= b[e]["pas"] - 3 for e, x in (("IS", a), ("OOS", c)))))
            print(f"{nm:38s} | {f(a)} | {f(c)} | {'PASS' if ok else '-'}")
