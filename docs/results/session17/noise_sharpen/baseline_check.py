import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import sharpen as S
t0 = time.time()
t = S.gen()
ref = pd.read_csv("/home/user/opogabuuga/docs/results/session15/out/streams/N1_MNQ.csv", dtype={"d": str})
print("gen secs", round(time.time() - t0, 1))
out = {}
for era in ("IS", "HO"):
    out[era] = S.stats(t, era); print(era, "mine", out[era]); print(era, "s15 csv", S.stats(ref, era))
same = len(t) == len(ref) and np.allclose(t.pnl.values, ref.pnl.values, atol=0.01) and (t.d.values == ref.d.values).all()
print("identical to session-15 N1 stream:", same, len(t), len(ref))
json.dump(dict(mine=out, identical=bool(same), n_mine=len(t), n_ref=len(ref)), open(os.path.dirname(os.path.abspath(__file__)) + "/baseline_check.json", "w"), indent=1)
