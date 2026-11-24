import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import research as R
from lib_ne import *
tr = R.gen("lastmom_day", {"ref": 239, "minr": 0.1, "hold": 59, "stop": 60})
tr = tr[tr.stop_pts * 2 + 2 <= 125.0 + 1e-9].copy(); tr["ptsB"] = tr.pts
tr.to_csv(os.path.dirname(os.path.abspath(__file__)) + "/trades_late_rebuilt.csv", index=False)
print(stats(tr))
old = pd.read_csv("/home/user/paytience/docs/results/new_edge/scripts/trades_lastmom239.csv")
print("identical to published csv:", len(old) == len(tr) and np.allclose(old.pts.values, tr.pts.values) and (old.day.values == tr.day.values).all())
