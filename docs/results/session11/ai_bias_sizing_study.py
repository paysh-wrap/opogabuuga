"""AI-bias-for-SIZING-only study. Daily call = coin with accuracy a vs real RTH direction (open -> close of the 1-min session).
agree -> +1 micro, disagree -> -1 micro (min 1), never blocks. Engine = pm_fade_d57_study.py (NOISE + PM fade, D57 live rule, kill $50,
eval brake/grow tables, D68 payout cadence) with day_sim patched to size per trade.
Modes: A = cap at the day's table size (agree can only restore a braked/tapered size -> effectively "-1 on disagree");
       B = agree may exceed the table by 1 (cap = base q0 + 1; DLL/D57 stop-tightening/worst-case checks still apply).
usage: python3 ai_bias_sizing_study.py run [seeds=200] | python3 ai_bias_sizing_study.py report"""
import os as _os; ROOT = _os.environ.get("PAYTIENCE_ROOT") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))
import sys, re, inspect, json
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT + "/backend"); sys.path.insert(0, ROOT + "/docs/results/session11")
from multiprocessing import Pool
import numpy as np
import pm_fade_d57_study as P

OUT = (_os.environ.get("STUDY_OUT") or ROOT + "/docs/results/session11/out") + "/ai_bias_sizing.json"
ACCS = [0.52, 0.55, 0.60, 0.65, 0.70]
STEP = 10
EV = [("25K", "25K Regular (1x$250)"), ("50K", "50K"), ("100K", "100K"), ("150K", "150K")]
FU = [("25K", "25K x1, pay/10"), ("50K", "50K x2 brake<50%->1, pay/10"), ("100K", "100K x2 brake<30%->1, pay/5"), ("150K", "150K x3 brake<50%->2, pay/5")]
MODE = {"m": "base"}

def QS(q, side, D, cfg):
    m = MODE["m"]
    if m == "base": return q
    c = D.call
    if c == 0 or c == side: return min(q + 1, q if m == "A" else cfg["q"] + 1) if c == side else q
    return max(1, q - 1)

src = inspect.getsource(P.day_sim)
head, body = src.split("\n", 1)
body = re.sub(r"\bq\b", "qq", body)
body = body.replace("    rule = cfg[\"rule\"]", "    qq = q\n    rule = cfg[\"rule\"]", 1)
body = body.replace("            ntr += 1\n", "            ntr += 1\n            qq = QS(q, side, D, cfg)\n", 1)
body = body.replace("        k, s, e, tgt = D.fade\n", "        k, s, e, tgt = D.fade\n        qq = QS(q, s, D, cfg)\n", 1)
assert body.count("QS(") == 2
P.QS = QS
exec(head + "\n" + body, P.__dict__)

def set_calls(objs, acc, seed):
    rng = np.random.default_rng(seed)
    for D in objs:
        if D is None: continue
        v = np.flatnonzero(~np.isnan(D.c)); tr = np.sign(D.c[v[-1]] - D.o[0]) if len(v) else 0
        if tr == 0: tr = rng.choice([-1, 1])
        D.call = int(tr if rng.random() < acc else -tr)

G = {}
def init():
    P.init(); G.update(names=P.G["names"], objs=P.G["objs"], V=P.G["V"])
    G["ev"] = P.eval_configs(G["V"], "tighten"); G["fu"] = P.funded_configs(G["V"], "tighten")

def one(job):
    mode, acc, seed = job; MODE["m"] = mode
    names, objs = G["names"], G["objs"]
    if mode != "base": set_calls(objs, acc, seed)
    out = {}
    for tag, key in EV:
        cfg = G["ev"][key]; H = P.HZ[key]; starts = list(range(0, len(objs) - H, STEP)); r = []
        for i in starts:
            s, n = P.run_eval(objs, i, cfg, P.KILL, H, P.zeros()); r.append((s, names[i] <= P.ERA_SPLIT))
        for era, f in (("all", lambda e: True), ("e1", lambda e: e), ("e2", lambda e: not e)):
            x = [s for s, e in r if f(e)]; out[f"E{tag}_{era}"] = [len(x), x.count("PASS"), x.count("BUST")]
    for tag, key in FU:
        cfg = G["fu"][key]; starts = list(range(0, len(objs) - 260, STEP)); r = []
        for i in starts:
            d = P.run_funded(objs, i, cfg, P.KILL, P.zeros(), 260); r.append((d["status"] == "BUST", d["paid"], names[i] <= P.ERA_SPLIT))
        for era, f in (("all", lambda e: True), ("e1", lambda e: e), ("e2", lambda e: not e)):
            x = [(b, p) for b, p, e in r if f(e)]; out[f"F{tag}_{era}"] = [len(x), sum(b for b, _ in x), sum(p for _, p in x)]
    return job, out

def run(nseeds):
    jobs = [("base", 0, 0)] + [(m, a, s) for s in range(nseeds) for a in ACCS for m in ("B", "A")]
    res = {}
    with Pool(4, initializer=init) as p:
        for k, (j, o) in enumerate(p.imap_unordered(one, jobs, chunksize=1)):
            res["|".join(map(str, j))] = o
            if k % 50 == 0: print(k, len(jobs), flush=True); json.dump(res, open(OUT, "w"))
    json.dump(res, open(OUT, "w"))

def agg(res, mode, acc):
    ks = [k for k in res if k.startswith(f"{mode}|{acc}|")] if mode != "base" else ["base|0|0"]
    o = {}
    for key in res[ks[0]]:
        a = np.array([res[k][key] for k in ks], float); o[key] = a.sum(0)
    return o, len(ks)

def report():
    res = json.load(open(OUT)); L = []
    def row(o, tag, era):
        e = o[f"E{tag}_{era}"]; f = o[f"F{tag}_{era}"]
        return e[1] / e[0] * 100, e[2] / e[0] * 100, f[1] / f[0] * 100, f[2] / f[0] / 26
    for era, nm in (("all", "ALL 2021-2026"), ("e1", "2021-2023 starts"), ("e2", "2024-2026 starts")):
        L.append(f"\n### {nm}\nper cell: EVAL pass% / EVAL bust% / FUNDED yr-1 bust% / mean income per 2 weeks $ (paid to trader)\n")
        L.append("| plan | baseline | " + " | ".join(f"{int(a*100)}% B" for a in ACCS) + " | " + " | ".join(f"{int(a*100)}% A" for a in ACCS) + " |\n|" + "---|" * (2 + 2 * len(ACCS)))
        for tag, _ in EV:
            cells = []; b = row(agg(res, "base", 0)[0], tag, era)
            cells.append("{:.1f} / {:.1f} / {:.1f} / {:.0f}".format(*b))
            for mode in ("B", "A"):
                for a in ACCS:
                    cells.append("{:.1f} / {:.1f} / {:.1f} / {:.0f}".format(*row(agg(res, mode, a)[0], tag, era)))
            L.append(f"| {tag} | " + " | ".join(cells) + " |")
    L.append("\n### Delta vs baseline (mode B, ALL): income $/2wk, funded bust pp, eval bust pp\n\n| plan | " + " | ".join(f"{int(a*100)}%" for a in ACCS) + " |\n|---|" + "---|" * len(ACCS))
    for tag, _ in EV:
        b = row(agg(res, "base", 0)[0], tag, "all"); cells = []
        for a in ACCS:
            r = row(agg(res, "B", a)[0], tag, "all"); cells.append(f"{r[3]-b[3]:+.0f} / {r[2]-b[2]:+.1f} / {r[1]-b[1]:+.1f}")
        L.append(f"| {tag} | " + " | ".join(cells) + " |")
    n = agg(res, "B", 0.6)[1]; L.append(f"\nseeds per cell: {n}")
    open(OUT.replace("ai_bias_sizing.json", "ai_bias_tables.md"), "w").write("\n".join(L)); print("\n".join(L))

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["run"]: run(int(a[1]) if len(a) > 1 else 200)
    else: report()
