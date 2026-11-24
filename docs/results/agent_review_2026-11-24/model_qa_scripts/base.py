from gen import *
t = noise3.gen()
print(st(t, "BASE all"))
t["y"] = t.d.str[:4]
print(st(t[t.d < "2024-01-01"], "2021-23"), "\n" + st(t[t.d >= "2024-01-01"], "2024-26"))
for y, g in t.groupby("y"): print(st(g, y))
t.to_csv("base.csv", index=False)
ref = pd.read_csv("/home/user/paytience/docs/results/session20/strategy_review/streams_BASE.csv")
print("ref", len(ref), round(ref.pnl.sum(),1), list(ref.columns))
