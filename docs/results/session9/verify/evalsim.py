"""Rolling-start Lucid eval simulation on REAL trade sequences (no resampling): start on every trading day of the
period, apply trades in order. MLL trails the peak END-OF-DAY balance (EOD drawdown), checked after every trade
(intraday breach), locks at start+100 once peak EOD >= lock_trigger. Pass = balance >= start+target AND (consistency:
best day <= pct * total profit). Open-trade excursions and the DLL are NOT modeled (optimistic)."""
import sys, os, pandas as pd, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PLANS = {"Pro25K": (25000, 1250, 1000, None), "Flex25K": (25000, 1250, 1000, .40), "Pro50K": (50000, 3000, 2000, None),
         "Flex50K": (50000, 3000, 2000, .40), "Pro100K": (100000, 6000, 3000, None), "Pro150K": (150000, 9000, 4500, None),
         "Flex150K": (150000, 9000, 4500, .40)}
def sim(trades, days_all, start_i, plan, q, horizon=120):
    bal0, tgt, mll, cons = PLANS[plan]; bal = bal0; peak = bal0; floor = bal0 - mll; lock = bal0 + mll + 100
    daypnl = {}
    for j, d in enumerate(days_all[start_i:start_i + horizon]):
        for p in trades.get(d, []):
            bal += p * q
            if bal <= floor: return "bust", j + 1
        daypnl[d] = bal - (bal0 + sum(v for k, v in daypnl.items() if k != d))
        prof = bal - bal0
        if prof >= tgt and (cons is None or max(daypnl.values()) <= cons * prof): return "pass", j + 1
        peak = max(peak, bal); floor = bal0 + 100 if peak >= lock else max(floor, peak - mll)
    return "open", horizon
def run(csv, period, plans, qs):
    t = pd.read_csv(csv); t["dt"] = pd.to_datetime(t.d)
    t = t[(t.dt >= period[0]) & (t.dt < period[1])]
    alld = pd.bdate_range(period[0], period[1]).date.astype(str).tolist()
    tr = {}
    for d, p in zip(t.d.astype(str), t.pnl): tr.setdefault(d, []).append(p)
    starts = range(0, len(alld) - 60, 3)
    for plan in plans:
        for q in qs:
            r = [sim(tr, alld, i, plan, q) for i in starts]
            n = len(r); ps = [x for x in r if x[0] == "pass"]; bs = [x for x in r if x[0] == "bust"]
            print(f"  {plan:8s} {q} micro: pass {len(ps)/n:5.1%}  bust {len(bs)/n:5.1%}  open {1-(len(ps)+len(bs))/n:5.1%}"
                  f"  median days to pass {np.median([x[1] for x in ps]) if ps else float('nan'):.0f}")
if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(name, "HELD-OUT 2024-01..2026-11")
        run(f"{HERE}/noise_{name}.csv", ("2024-01-01", "2026-11-07"), ["Pro25K", "Flex50K", "Pro50K", "Pro150K"], [1, 2])
