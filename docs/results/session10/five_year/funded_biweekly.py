"""Take-home from FUNDED Lucid Pro 25K accounts with a payout request every 2 weeks (10 trading days), 5 years of real
trade days (rolling starts), 1 micro per account. Rules: config/rules/lucid_pro_25k.yaml funded + payout:
  EOD trailing MLL $1,000 (locks at 25,100 once the EOD peak >= 26,100), DLL $600 soft, payout only if the cycle profit
  >= $250, balance after the payout stays >= $26,100 buffer, request >= $500, largest day <= 40% of the cycle profit,
  cap $1,000 first / $1,500 next, max 5 payouts (then the live/review pool — not modeled), split 90% to you.
All 5 accounts take the SAME trades (same signals) → they win and bust together; 5 accounts = 5 × one account.
usage: funded_biweekly.py TRADES.csv [START END]   (TRADES.csv columns d, pnl per 1 micro)"""
import sys

import numpy as np
import pandas as pd

B0, MLL, BUF, DLL = 25000.0, 1000.0, 26100.0, 600.0
csv = sys.argv[1]
start, end = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("2021-11-01", "2026-10-30")
t = pd.read_csv(csv)
t = t[(t.d >= start) & (t.d <= end)]
days = pd.bdate_range(start, end).date.astype(str).tolist()
tr: dict[str, list[float]] = {}
for d, p in zip(t.d.astype(str), t.pnl):
    tr.setdefault(d, []).append(p)


def funded(i0: int, horizon: int = 260):
    bal, peak, floor = B0, B0, B0 - MLL
    cyc: list[float] = []
    paid, npay, pays = 0.0, 0, []
    for n, i in enumerate(range(i0, min(i0 + horizon, len(days)))):
        cum = 0.0
        for p in tr.get(days[i], []):
            if cum + p <= -DLL:
                p = -DLL - cum
            bal += p
            cum += p
            if bal <= floor:
                return paid, npay, pays, "bust", n + 1
            if cum <= -DLL:
                break
        if tr.get(days[i]):
            cyc.append(cum)
        peak = max(peak, bal)
        floor = B0 + 100 if peak >= B0 + MLL + 100 else max(floor, peak - MLL)
        if (n + 1) % 10 == 0 and npay < 5:  # every 2 weeks: request a payout if the rules allow
            cp = sum(cyc)
            amt = min(bal - BUF, 1000 if npay == 0 else 1500)
            if cp >= 250 and amt >= 500 and max(cyc) <= 0.40 * cp:
                bal -= amt
                paid += 0.9 * amt
                npay += 1
                pays.append((n + 1, 0.9 * amt))
                cyc = []
        if npay >= 5:
            return paid, npay, pays, "5 payouts (→ live review)", n + 1
    return paid, npay, pays, "open", min(horizon, len(days) - i0)


res = [funded(i) for i in range(0, len(days) - 260, 2)]  # starts with a full year of data after them
n = len(res)
paid = np.array([r[0] for r in res])
first = [r[2][0][0] for r in res if r[2]]
print(f"{csv}: {n} funded starts {start}..{end}, first 12 months of each account")
for k, lab in ((0, "bust"), (1, "5 payouts"), (2, "still open")):
    m = {0: "bust", 1: "5 payouts (→ live review)", 2: "open"}[k]
    print(f"  {lab:11s} {sum(r[3] == m for r in res) / n:5.1%}")
print(f"  ≥1 payout {np.mean(paid > 0):.1%} · median days to 1st payout {np.median(first):.0f}")
print(f"  take-home per account in its first year: mean ${paid.mean():,.0f} · median ${np.median(paid):,.0f} · "
      f"25%-75% ${np.percentile(paid, 25):,.0f}–${np.percentile(paid, 75):,.0f}")
per2w = paid / 26
print(f"  ≈ per 2 weeks per account (over 52 weeks): mean ${per2w.mean():,.0f}")
print(f"  5 accounts (same trades): first-year take-home mean ${5 * paid.mean():,.0f} · median ${5 * np.median(paid):,.0f} "
      f"· per 2 weeks ≈ ${5 * per2w.mean():,.0f} · worst 25% of starts ≤ ${5 * np.percentile(paid, 25):,.0f}")
dist = pd.Series([len(r[2]) for r in res]).value_counts(normalize=True).sort_index()
print("  payouts in first year:", " · ".join(f"{k}: {v:.0%}" for k, v in dist.items()))
