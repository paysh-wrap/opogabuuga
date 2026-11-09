import sys, pandas as pd
sys.path.insert(0, "/home/user/opogabuuga/docs/results/tools")
import noise_area as NA, sim25k as SM
S = "/tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad"
days = NA.load_days(f"{S}/data/mnq_1m.csv")
held_days = sum(1 for d, _ in days if d >= "2024-01-01")
for step in (60, 30):
    for maxtr in (3, 5):
        t = NA.run(days, 14, step, 0.01, maxtr); p = f"{S}/verify/freq_{step}_{maxtr}.csv"; t.to_csv(p, index=False)
        dt = pd.to_datetime(t.d); h = t[dt >= "2024"]; i = t[dt < "2024"]
        r = SM.run("Pro", p, dll_funded=600); n = len(r)
        ps = sum(x[0] == "pass" for x in r) / n; bs = sum(x[0] == "bust" for x in r) / n
        print(f"checks {step}m max {maxtr}/day: HELD {len(h)/held_days:.2f}/day = {5*len(h)/held_days:.1f}/week, win {(h.pnl>0).mean():.1%}, "
              f"$/tr {h.pnl.mean():.2f}, PF {h.pnl[h.pnl>0].sum()/-h.pnl[h.pnl<=0].sum():.2f}, total ${h.pnl.sum():.0f} | IN PF "
              f"{i.pnl[i.pnl>0].sum()/-i.pnl[i.pnl<=0].sum():.2f} | Pro25K pass {ps:.0%} bust {bs:.0%}", flush=True)
