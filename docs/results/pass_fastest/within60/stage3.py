"""stage 3: full extras cross (NOISE lock x day lock x CANDACE window x taper x grow) on (a) every acceptable config and (b) the 30 best-<=60d
near-acceptable configs (pass >= base-2, stuck <= base+2, profit >= 0.95 base) per plan x DLL.  Resumes results.json."""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import *

if __name__ == "__main__":
    store = json.load(open(FN)); pool = mp.Pool(4); jobs = []
    for k in (25, 150):
        for dll in (True, False):
            b = store[f"{k}|{int(dll)}|{name(BASE[k])}"]
            rs = [(nm, r) for nm, r in store.items() if nm.startswith(f"{k}|{int(dll)}|")]
            acc = [nm for nm, r in rs if ok_A(r, b)]
            near = sorted([(nm, r) for nm, r in rs if r["ALL"]["pass"] >= b["ALL"]["pass"] - 2 and r["ALL"]["stuck"] <= b["ALL"]["stuck"] + 2 and r["profit"] >= .95 * b["profit"]],
                          key=lambda x: -x[1]["ALL"]["p60"])[:30]
            seeds = {from_name(nm)["stop"] and nm for nm in acc} | {nm for nm, _ in near}
            for nm in seeds:
                d = from_name(nm)
                for lk, dl, cw, tp, gr in itertools.product((80, 100, 120), (None, .5, .7), (1000, 1030), (None, (0.25, 1)), (None, (500., 6))):
                    c = dict(d, lock=lk, dlock=dl, cwin=cw, taper=tp, grow=gr)
                    jobs.append((k, dll, name(c), c))
    print(len(jobs), flush=True)
    run(jobs, store, pool); print("done")
