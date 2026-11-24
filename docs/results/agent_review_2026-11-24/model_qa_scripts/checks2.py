from gen import *
base = pd.read_csv("base.csv")
H = lambda t: (st(t[t.d < "2024-01-01"], " 21-23"), st(t[t.d >= "2024-01-01"], " 24-26"))
print("== roll/gap guard sensitivity")
for r in (0.015, 0.02, 0.03, 1.0):
    t = noise3.gen(roll=r); print(st(t, f"roll={r}"), *H(t), sep="\n")
print("== cost sensitivity (fee = RT $ incl. commission; slippage 1 tick/side kept in addition)")
for f in (1.0, 2.0, 3.0, 4.0):
    t = noise3.gen(fee=f); print(st(t, f"fee={f}"), *H(t), sep="\n")
print("== entry hour breakdown (BASE)")
base["hr"] = (base.ek - 1 + 30) // 60 + 9
base["hrlab"] = base.ek.map(lambda k: f"{(570 + k - 1)//60:02d}:{(570 + k - 1)%60:02d}")
for h, g in base.groupby("hrlab"): print(st(g, "entry " + h))
