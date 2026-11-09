import sys, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/tools")
import noise_area as NA, sim25k as SM
S = "/tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad"
days = NA.load_days(f"{S}/data/mnq_1m.csv")
def one_loss(t):  # stop for the day after the first losing trade
    keep, seen = [], set()
    for r in t.itertuples():
        if r.d in seen: continue
        keep.append(r.Index)
        if r.pnl <= 0: seen.add(r.d)
    return t.loc[keep]
for name, kw, post in [("maxtr3 (base)", {"maxtr": 3}, None), ("maxtr2", {"maxtr": 2}, None), ("maxtr1", {"maxtr": 1}, None),
                       ("maxtr3 + stop after 1st loss", {"maxtr": 3}, one_loss)]:
    t = NA.run(days, 14, 60, 0.01, **kw)
    if post: t = post(t)
    p = f"{S}/verify/pro25_{name.split()[0]}{'_1loss' if post else ''}.csv"; t.to_csv(p, index=False)
    dt = pd.to_datetime(t.d)
    def ev(start, end):
        r = SM.run("Pro", p, dll_funded=600, start=start, end=end); n = len(r)
        return f"pass {sum(x[0]=='pass' for x in r)/n:4.0%} bust {sum(x[0]=='bust' for x in r)/n:4.0%}"
    print(f"{name:30s}", NA.stats(t[dt < "2024"], "IN")[15:], "| Pro25K-eval IN:", ev("2019-06-01", "2023-12-31"))
    print(f"{'':30s}", NA.stats(t[dt >= "2024"], "HELD")[15:], "| Pro25K-eval HELD:", ev("2024-01-01", "2026-11-06"), flush=True)
