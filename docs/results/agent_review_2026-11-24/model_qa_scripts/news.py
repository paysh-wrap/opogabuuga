from gen import *
import pickle
L, _ = pickle.load(open("/home/user/days.pkl", "rb")); M = dict(L); dates = [d for d, _ in L]
s = pd.Series(pd.to_datetime(dates)); ym = s.dt.strftime("%Y-%m")
ism = set()
for m, g in s.groupby(ym):
    g = sorted(g)
    ism.add(g[0].strftime("%Y-%m-%d"))
    if len(g) > 2: ism.add(g[2].strftime("%Y-%m-%d"))
fomc = set("""2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18 2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28""".split())
print("approx 10:00 ISM days", len(ism), "FOMC days in data", len(fomc & set(dates)))
def ef(d, k, side, a, f, sk):
    if k == 29 and d in ism: return False
    if k == 269 and d in fomc: return False
    return True
t = noise3.gen(efilt=ef)
# flatten FOMC positions at 13:58 (bar k=267 close)
pnl = []
for r in t.itertuples():
    p = r.pnl
    if r.d in fomc and r.ek <= 267 < r.xk:
        a = M[r.d]; e = a["open"][r.ek] + r.side * 0.25
        p = (a["close"][267] - r.side * 0.25 - e) * r.side * 2 - 1
    pnl.append(p)
t["pnl"] = pnl
b = pd.read_csv("base.csv")
print(st(b, "BASE")); print(st(t, "news-approx")); print(st(t[t.d >= "2024"], " judge news")); print(st(b[b.d >= "2024"], " judge base"))
c = pd.read_csv("cand_aug.csv"); keep = []; p2 = []
for r in c.itertuples():
    if r.day in ism:
        k0 = int(r.idx) - 1  # signal bar k
        if r.time >= "09:45": continue
        if int(r.exit_idx) - 1 > 27:  # still open at 09:58 → flatten at close of k=27
            a = M[r.day]; sg = 1 if r.dir == "LONG" else -1; keep.append(r.Index); p2.append(((a["close"][27] - r.entry) * sg) * 2 - 2); continue
    keep.append(r.Index); p2.append(r.usd)
p2 = np.array(p2); print("CANDACE base n=%d PF=%.2f net=%.0f | news-approx n=%d PF=%.2f net=%.0f" % (len(c), pf(c.usd), c.usd.sum(), len(p2), pf(p2), p2.sum()))
print("CANDACE trades on ISM days:", c.day.isin(ism).sum(), "net", round(c[c.day.isin(ism)].usd.sum()))
