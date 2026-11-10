"""kelly_run.py - runs tasks A/B/C of the Kelly sizing study -> kelly_results.json.  usage: python3 kelly_run.py"""
import sys, json
sys.dont_write_bytecode = True
from multiprocessing import Pool
import kelly_engine as K
P = K.P
EK = {"25K": "25K Regular (1x$250)", "50K": "50K", "100K": "100K", "150K": "150K"}
FK = {"25K": "25K x1, pay/10", "50K": "50K x2 brake<50%->1, pay/10", "100K": "100K x2 brake<30%->1, pay/5", "150K": "150K x3 brake<50%->2, pay/5"}
ECAP = {"25K": 1, "50K": 2, "100K": 4, "150K": 4}      # largest size of the live Eval-Mode row
FCAP = {"25K": 1, "50K": 2, "100K": 2, "150K": 3}      # live funded Regular size
KS = (0.4, 0.6, 0.8, 1.0, 1.3)
def work(job):
    kind, plan, stream, kelly = job
    V = K.G["V"]
    cfg = dict((P.eval_configs(V, "code")[EK[plan]] if kind == "E" else P.funded_configs(V, "code")[FK[plan]]))
    if stream == "lock": cfg["lock"] = K.LOCK
    if kelly: cfg["kelly"] = tuple(kelly)
    r = K.ev_eval(cfg, K.G["names"], K.G["objs"], P.HZ[EK[plan]]) if kind == "E" else K.ev_funded(cfg, K.G["names"], K.G["objs"])
    return dict(kind=kind, plan=plan, stream=stream, kelly=kelly, **r)
if __name__ == "__main__":
    jobs = []
    for kind in "EF":
        for plan in EK:
            for stream in ("base", "lock"):
                jobs.append((kind, plan, stream, None)); jobs.append((kind, plan, stream, (0, 1)))     # live table; fixed 1 micro
                if plan == "25K": continue
                cap0 = (ECAP if kind == "E" else FCAP)[plan]
                for k in KS:
                    for dc in (0, 1, 2): jobs.append((kind, plan, stream, (k, cap0 + dc)))
    with Pool(4, initializer=K.init) as p: res = p.map(work, jobs, chunksize=1)
    json.dump(res, open("kelly_results.json", "w"), indent=0)
    print(len(res), "jobs done")
