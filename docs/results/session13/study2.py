import json, itertools
from study import *
out = {}
def run(name, **kw):
    t = gen(nd=BASE_ND, **kw); r = summ(t); out[name] = r; print(line(name, r), flush=True); return r
base = run("A current")
for k0 in (30, 60, 90, 120, 150, 180):
    for bd in (2.0,):
        run(f"B fade k0={k0} band={bd}", k0=k0, band=bd)
for k0, bd in ((150, 1.5), (150, 2.5), (120, 2.5), (90, 2.5)): run(f"B fade k0={k0} band={bd}", k0=k0, band=bd)
json.dump(out, open(HERE + "/grid_B2.json", "w"), default=float)
