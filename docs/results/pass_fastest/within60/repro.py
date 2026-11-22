import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
t = time.time()
c25 = mkcfg(75, 1, 2, cb=((T3, 1),))
c150 = mkcfg(100, 5, 4, nb=((T3, 2),), cb=((T3, 2),))
for k, c in ((25, c25), (150, c150)):
    n, r = ev((k, True, "cur", c))
    print(k, r["ALL"], "judge", r["JUDGE"]["pass"], "pick", r["PICK"]["pass"], "profit", r["profit"], round(time.time() - t), flush=True)
