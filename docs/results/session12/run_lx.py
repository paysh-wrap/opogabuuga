import sys, itertools, json
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session12")
from lunq_eval import *
ctx = Ctx(load_bars(RAW + "/mnq_5y.csv"), load_bars(RAW + "/mes_5y.csv"))
C = cands(sys.argv[1]); print("candidates", len(C), flush=True)
rows = []
def go(name, spec):
    t = run(ctx, C, spec); a, b = halves(t); rows.append(dict(name=name, spec=spec, A=a, B=b)); print(name, a, b, flush=True)
go("BASE", {})
for tf, body, dist in itertools.product((1, 5), (1.0, 1.5), (10, 25, 60)): go(f"OBF tf{tf} body{body} d{dist}", dict(ob=(tf, body, 10, dist)))
for look, valid in itertools.product((10, 20, 40), (10, 30)): go(f"SMT l{look} v{valid}", dict(smt=(look, valid)))
for tf, body, buf in itertools.product((1, 5), (1.0, 1.5), (2, 5)): go(f"ANCH tf{tf} body{body} buf{buf}", dict(anchor=(tf, body, 10, buf)))
json.dump(rows, open("/home/user/opogabuuga/docs/results/session12/lx_grid.json", "w"), default=float)
# variant 2 = in-sample-best filter + OB stop anchor (only if tighter and R:R stays 1.75-3.0)
for buf in (2, 5): go(f"OBF+ANCH tf5 body1.0 d60 buf{buf}", dict(ob=(5, 1.0, 10, 60), anchor=(5, 1.0, 10, buf)))
json.dump(rows, open("/home/user/opogabuuga/docs/results/session12/lx_grid.json", "w"), default=float)
