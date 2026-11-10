import sys, json, itertools
sys.path.insert(0, "/home/user/opogabuuga/docs/results/session12")
import ob_study as S
days, mes = S.load()
dm = dict(days)
BD = {d: S.DayBars(a, mes.get(d)) for d, a in days if S.START <= d <= S.END}
base = S.build(days, set())   # placeholder to get noise days
nd = set(base[base.strategy == "NOISE"].date)
base = S.build(days, nd)
A0, B0 = S.halves(base)
print("BASE", {k: round(v, 2) for k, v in A0.items()}, {k: round(v, 2) for k, v in B0.items()}, flush=True)
rows = []
def run(name, spec, which):
    v, an = S.mk_hooks(BD, spec)
    kw = {}
    if spec.get("ob") or spec.get("smt"): kw.update(vN=v, vF=v)
    if spec.get("anchor"): kw.update(aN=an, aF=an)
    t = S.build(days, nd, **kw); a, b = S.halves(t)
    rows.append(dict(name=name, kind=which, spec=spec, A=a, B=b))
    print(name, {k: round(x, 2) for k, x in a.items()}, {k: round(x, 2) for k, x in b.items()}, flush=True)
for tf, body, swing, dist in itertools.product((1, 5), (1.0, 1.5), (10,), (10, 25, 60)):
    run(f"OBF tf{tf} body{body} sw{swing} d{dist}", dict(ob=(tf, body, swing, dist)), "filter")
for look, valid in itertools.product((10, 20, 40), (10, 30)):
    run(f"SMT l{look} v{valid}", dict(smt=(look, valid)), "filter")
for tf, body, swing, buf in itertools.product((1, 5), (1.0, 1.5), (10,), (2, 5)):
    run(f"ANCH tf{tf} body{body} sw{swing} buf{buf}", dict(anchor=(tf, body, swing, buf)), "anchor")
json.dump(dict(base=[A0, B0], rows=rows), open("/home/user/opogabuuga/docs/results/session12/nf_grid.json", "w"), default=float)
