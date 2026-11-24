import sys; sys.path.insert(0, sys.path[0])
import sim150 as S, numpy as np, pandas as pd
c = S.mk(stop=100, N=4, nc=3, brake=(0.5, 2)); r = S.evaluate(c, with_static=False)["_roll"]
y = pd.Series([d[:4] + ("H1" if d[5:7] <= "06" else "H2") for d in S.DATES])
o = r["out"]; n = r["ses"]
df = pd.DataFrame(dict(h=y, p=(o == 0), p60=(o == 0) & (n <= 60), open=(o == 2)))
print(df.groupby("h").agg(starts=("p", "size"), pass_pct=("p", "mean"), p60=("p60", "mean"), still_open=("open", "mean")).round(2).to_string())
# effective independent windows
pn = n[o == 0]; print("median sessions to pass", np.median(pn), "-> independent windows ~", round(len(S.DATES) / np.median(pn), 1))
