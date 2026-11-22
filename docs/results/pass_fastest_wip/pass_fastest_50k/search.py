"""Pass-fastest 50K study: search driver. Results accumulate in one store (pickle in the scratch dir, exported to results.json by finalize.py).
Run: cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest_50k/search.py stage1|stage2|stage3 ...
Every evaluated config = rolling starts on 5y (ALL) / pick / judge + renewal chain + static replay (lib50.evaluate); the store is keyed by the normalised config.
"""
import sys, os, json, time, pickle, itertools, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib50 as L

STORE_FN = os.environ.get("PF50_STORE", "/tmp/claude-0/-home-user-opogabuuga/a242e4b9-b41b-5028-bba9-c21e825f6a98/scratchpad/pf50/store.pkl")

STOPS = (75, 100, 125, 150, 175, 200, 225, 250, 300)
GROWS = ((0, 0), (600, 3), (600, 4), (1000, 3), (1000, 4))      # (grow_per $, max_contracts); (0, 0) = none
BRAKES = ((0.0, 1), (0.5, 1), (0.35, 1))                          # (brake_below, brake_contracts)
TAPERS = ((0.0, 1), (0.25, 1), (0.5, 1))                          # (taper_below_remaining, taper_contracts)
DLS = (0.0, 0.25, 0.33, 0.5)
CANDS = ((0, 1000), (1, 1000), (2, 1000), (1, 1030), (2, 1030))   # (CANDACE micros, window end HHMM)

# factor tags for the report: config-only (existing setting) or needs code
TAGS = {
    "stop": "config-only: strategy.size_table_eval row stop_usd (EVAL only) [or noise_cfg.emergency_stop_usd, all stages]",
    "nn": "config-only: size_table_eval row contracts",
    "grow": "config-only: size_table_eval row grow_per + max_contracts",
    "brake": "config-only: size_table_eval row brake_below + brake_contracts",
    "taper": "config-only: size_table_eval row taper_below_remaining + taper_contracts (needs contracts >= 2)",
    "dl": "config-only: size_table_eval row day_lock_pct",
    "mx": "config-only: noise_cfg.max_entries_per_day (global: also funded/live)",
    "trig": "config-only: noise_cfg.profit_lock_trigger_pts (global: also funded/live; lock distance stays entry+10)",
    "mon": "config-only: noise_cfg.skip_weekdays (global: also funded/live; also governs the fade)",
    "fade": "config-only: strategy.pm_fade_cfg.eval_off = false (fade uses the NOISE size row)",
    "cand": "needs code for a FIXED micro count (today CANDACE = Lucid fit x grade rule); window = config-only strategy.candace_ict_cfg.ny_window",
    "gala": "needs code for a FIXED 1-micro GALA (today Lucid fit); strategy.gala_pa on is config-only",
    "both": "needs a RULE change (non-negotiable 7: max 1 open position per account)",
}


def norm(c):
    c = dict(c)
    if not c["grow"]: c["gmax"] = 0
    if c["nn"] < 2: c["bb"] = 0.0; c["tb"] = 0.0
    if not c["bb"]: c["bc"] = 1
    if not c["tb"]: c["tc"] = 1
    if not c["nc"]: c["cwin"] = 1000; c["both"] = 0 if not c["gala"] else c["both"]
    if not c["gala"]: c["ng"] = 1
    if not c["nc"] and not c["gala"]: c["both"] = 0
    if not c["fade"]: c["fsh"] = 0
    return c


def valid(c):
    if c["grow"] and c["gmax"] < c["nn"]: return False
    if c["bb"] and not (1 <= c["bc"] < c["nn"]): return False
    if c["tb"] and not (1 <= c["tc"] < c["nn"]): return False
    return True


def mk(**kw):
    return norm(L.cfg_of(**kw))


class Store:
    def __init__(self, fn=STORE_FN):
        self.fn = fn; self.d = {}
        if os.path.exists(fn): self.d = pickle.load(open(fn, "rb"))

    def save(self):
        tmp = self.fn + ".tmp"; pickle.dump(self.d, open(tmp, "wb")); os.replace(tmp, self.fn)

    def eval(self, cfgs, label="", procs=2):
        todo = {}
        for c in cfgs:
            c = norm(c)
            if not valid(c): continue
            k = L.cfg_key(c)
            if k not in self.d and k not in todo: todo[k] = c
        if todo:
            t0 = time.time()
            res = L.run_many(list(todo.values()), procs=procs, label=label)
            for k, r in res.items(): self.d[k] = dict(cfg=todo[k], m=r)
            self.save()
            print(f"[{label}] evaluated {len(todo)} new configs in {time.time() - t0:.0f}s; store {len(self.d)}", flush=True)
        return [self.d[L.cfg_key(norm(c))] for c in cfgs if valid(norm(c))]


def one_factor(anchor):
    """all single-factor variations of an anchor config (the anchor itself included)"""
    out = [anchor]
    for stop in STOPS: out.append(dict(anchor, stop=stop))
    for nn in (1, 2, 3, 4): out.append(dict(anchor, nn=nn))
    for g, gm in GROWS: out.append(dict(anchor, grow=g, gmax=gm))
    for bb, bc in BRAKES: out.append(dict(anchor, bb=bb, bc=bc))
    for tb, tc in TAPERS: out.append(dict(anchor, tb=tb, tc=tc))
    for dl in DLS: out.append(dict(anchor, dl=dl))
    for mx in (2, 3): out.append(dict(anchor, mx=mx))
    for trig in (80, 100, 120): out.append(dict(anchor, trig=trig))
    for mon in (0, 1): out.append(dict(anchor, mon=mon))
    for fade in (0, 1): out.append(dict(anchor, fade=fade))
    for nc, cw in CANDS: out.append(dict(anchor, nc=nc, cwin=cw))
    for gala in (0, 1): out.append(dict(anchor, gala=gala))
    return [norm(c) for c in out]


ANCHORS = {"BASE": L.BASE, "ROW_A": L.ROW_A, "NOISE2_100": L.NOISE2_100}


def stage1(st):
    cfgs = []
    for nm, a in ANCHORS.items(): cfgs += one_factor(norm(a))
    st.eval(cfgs, "stage1")


def stage2(st):
    """full factorial over the factors that moved the objectives in stage 1: NOISE stop x micros x grow x brake x taper x fixed CANDACE micros (window 10:00);
    every other factor at the shipped value (lock 100, max 3 a day, Mondays off, fade off, GALA off, no day lock)."""
    cfgs = []
    for stop, nn, (g, gm), (bb, bc), (tb, tc), nc in itertools.product(STOPS, (2, 3, 4), GROWS, BRAKES, TAPERS, (0, 1, 2)):
        cfgs.append(mk(stop=stop, nn=nn, grow=g, gmax=gm, bb=bb, bc=bc, tb=tb, tc=tc, nc=nc))
    # nn = 1 only makes sense with growth (no brake / taper possible at 1 micro)
    for stop, (g, gm), nc in itertools.product(STOPS, GROWS[1:], (0, 1, 2)):
        cfgs.append(mk(stop=stop, nn=1, grow=g, gmax=gm, nc=nc))
    st.eval(cfgs, "stage2")


if __name__ == "__main__":
    st = Store()
    what = sys.argv[1] if len(sys.argv) > 1 else "stage1"
    if what == "stage1": stage1(st)
    elif what == "stage2": stage2(st)
