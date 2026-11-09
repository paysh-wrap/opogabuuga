"""25K Lucid accounts: eval -> funded (with payouts) on REAL consecutive trade days, rolling starts.
Rules from config/rules/lucid_{pro,flex}_25k.yaml (VERIFY items as configured). MLL $1,000 trails the peak EOD balance,
breach checked after every trade (open-trade excursion not modeled), locks at 25,100 once peak EOD >= 26,100.
DLL (when ON) = $600 soft: the day's loss is capped at -600 (trade that crosses is cut there) and trading stops that day."""
import os, sys, numpy as np, pandas as pd
B0, TGT, MLL = 25000, 1250, 1000
def day_pnls(trs, q, dll):
    out, cum = [], 0.0
    for p in trs:
        p *= q
        if dll is not None and cum + p <= -dll: out.append(-dll - cum); break
        out.append(p); cum += p
    return out
class Acct:
    def __init__(s): s.bal = B0; s.peak = B0; s.floor = B0 - MLL
    def apply_day(s, pn):
        for p in pn:
            s.bal += p
            if s.bal <= s.floor: return False
        s.peak = max(s.peak, s.bal)
        s.floor = B0 + 100 if s.peak >= B0 + MLL + 100 else max(s.floor, s.peak - MLL)
        return True
def run(plan, csv, q=1, dll_eval=None, dll_funded=None, horizon_eval=120, horizon_funded=250, start="2024-01-01", end="2026-11-06"):
    t = pd.read_csv(csv); t = t[(pd.to_datetime(t.d) >= start) & (pd.to_datetime(t.d) <= end)]
    days = pd.bdate_range(start, end).date.astype(str).tolist()
    tr = {}
    for d, p in zip(t.d.astype(str), t.pnl): tr.setdefault(d, []).append(p)
    res = []
    for s0 in range(0, len(days) - 40, 2):
        a = Acct(); dp = []; i = s0; status = "open"
        while i < len(days) and i - s0 < horizon_eval:                      # ---------- eval
            pn = day_pnls(tr.get(days[i], []), q, dll_eval); i += 1
            if not a.apply_day(pn): status = "bust"; break
            if pn: dp.append(sum(pn))
            prof = a.bal - B0
            if prof >= TGT:
                if plan == "Pro" or (max(dp) <= .40 * prof and sum(x > 0 for x in dp) >= 3): status = "pass"; break
        if status != "pass": res.append((status, i - s0, 0.0, 0, False)); continue
        eval_days = i - s0; f = Acct(); paid = 0.0; npay = 0; cyc = []; f0 = i; fstat = "ok"; censored = False
        while i < len(days) and i - f0 < horizon_funded and npay < 5:     # ---------- funded
            pn = day_pnls(tr.get(days[i], []), q, dll_funded); i += 1
            if not f.apply_day(pn): fstat = "bust"; break
            if pn: cyc.append(sum(pn))
            cp = sum(cyc)
            if plan == "Pro":
                ok = cp >= 250 and f.bal - 26100 >= 500 and (max(cyc) <= .40 * cp)
                amt = min(f.bal - 26100, 1000 if npay == 0 else 1500)
            else:
                ok = sum(x >= 100 for x in cyc) >= 5 and f.bal - 25100 >= 500
                amt = min(.5 * (f.bal - B0), 1000, f.bal - 25100)
            if ok and amt >= 500:
                f.bal -= amt; paid += .9 * amt; npay += 1; cyc = []
                if plan == "Flex": f.floor = max(f.floor, 25100)
        if i >= len(days) and fstat == "ok" and npay < 5 and i - f0 < horizon_funded: censored = True
        res.append(("pass", eval_days, paid, npay, censored, fstat))
    return res
def summary(name, res):
    n = len(res); ps = [r for r in res if r[0] == "pass"]; bs = sum(r[0] == "bust" for r in res)
    full = [r for r in ps if not r[4]]
    pay1 = sum(r[3] >= 1 for r in full) / max(1, len(full)); ev = np.mean([r[2] for r in full]) if full else 0
    fb = sum(len(r) > 5 and r[5] == "bust" for r in full) / max(1, len(full))
    print(f"{name:38s} eval pass {len(ps)/n:5.1%} bust {bs/n:5.1%} | median eval days {np.median([r[1] for r in ps]):3.0f} | "
          f"funded (n={len(full)}): ≥1 payout {pay1:5.1%}, bust before 5 payouts {fb:5.1%}, avg paid to you ${ev:6.0f} "
          f"| per eval bought ≈ ${ev*len(ps)/n:5.0f}")
if __name__ == "__main__":
    # usage: sim25k.py TRADES.csv [TRADES2.csv ...]   (columns d=YYYY-MM-DD, pnl=$ net per 1 micro; e.g. noise_area.py output)
    for csv in sys.argv[1:]:
        print("==", csv, "(held-out 2024-01..2026-11, 1 micro unless noted)")
        summary("Pro 25K  (eval no DLL, funded DLL $600)", run("Pro", csv, dll_funded=600))
        summary("Pro 25K  if NO DLL anywhere", run("Pro", csv))
        summary("Flex 25K (no DLL, eval 40% consistency)", run("Flex", csv))
        summary("Flex 25K with DLL $600 ON", run("Flex", csv, dll_eval=600, dll_funded=600))
        summary("Pro 25K  2 micros (funded DLL $600)", run("Pro", csv, q=2, dll_funded=600))
        summary("Flex 25K 2 micros (no DLL)", run("Flex", csv, q=2))
