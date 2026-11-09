import json, itertools, pandas as pd
from sim import *
keys = ["main","s30","m5","s30m5","od","s30m5od","t125","t150","t125_s30m5","t125_od"]
data = {k: as_days(pd.read_csv(f"trades_{k}.csv")) for k in keys}
cf = {}
for q, X, L in itertools.product((3,4), (0.3,0.5), (None,0.33,0.5)):
    cf[f"B {q}mic sprint<{int(X*100)}%->1 lock {L or 'none'} [main]"] = ("main", dict(q=q, sprint=(X,1), lock=L))
for ds in ("t125","t150"):
    for q in (2,3,4):
        for X in (None,0.5):
            cf[f"C {ds} x{q} sprint {X or 'none'}"] = (ds, dict(q=q, sprint=(X,1) if X else None))
for ds in keys:
    for q, kw in ((1,{}),(2,dict(brake=(0.5,1))),(3,dict(sprint=(0.5,1),lock=0.33)),(4,dict(sprint=(0.5,1))),(4,dict(sprint=(0.5,1),lock=0.5))):
        cf[f"DE {ds} x{q} {kw}"] = (ds, dict(q=q, **kw))
cf = {k:(d,{a:b for a,b in c.items() if b is not None}) for k,(d,c) in cf.items()}
out = {}
for n,(ds,c) in cf.items():
    names, dd = data[ds]; r = evaluate(names, dd, c); out[n]=dict(ds=ds,cfg=c,**r)
json.dump(out, open("results_full.json","w"), indent=1, default=str)
L=["| variant | pass | bust | med | p75 | chain | evals/funded | value/eval | era1 pass/bust/med/chain | era2 |","|"+"---|"*10]
for n,v in out.items():
    a,e1,e2=v["all"],v["e1"],v["e2"]
    L.append(f"| {n} | {a['pass_']:.1%} | {a['bust']:.1%} | {a['med']:.0f} | {a['p75']:.0f} | {a['chain_med']:.0f} | {1/a['pass_']:.2f} | ${a['pass_']*1646.41:,.0f} | {e1['pass_']:.0%}/{e1['bust']:.0%}/{e1['med']:.0f}/{e1['chain_med']:.0f} | {e2['pass_']:.0%}/{e2['bust']:.0%}/{e2['med']:.0f}/{e2['chain_med']:.0f} |")
open("table_full.md","w").write("\n".join(L)+"\n"); print("\n".join(L))
