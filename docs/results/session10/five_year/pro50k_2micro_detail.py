"""Detail for 5 × Pro 50K at 2 micros (MAIN $250/$250): payouts per account in year 1, by start year, time to payouts."""
import sys
from collections import Counter, defaultdict
from decimal import Decimal as D
from pathlib import Path
from statistics import mean, median

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.backtest.income_projection import funded_path, research_days, rules_view  # noqa: E402
from app.config import load_rules  # noqa: E402

names, dd = research_days()
fv = rules_view(load_rules(REPO / "config" / "rules" / "lucid_pro_50k.yaml").rules)
res = [(names[i], funded_path(list(dd[i:i + 260]), fv, 2, 10)) for i in range(0, len(dd) - 260, 2)]
n = len(res)
cnt = Counter(len(p.payouts) for _, p in res)
print("payouts per account in year 1:", " · ".join(f"{k}: {cnt[k] / n:.0%}" for k in sorted(cnt)))
print("status:", {s: f"{sum(p.status == s for _, p in res) / n:.0%}" for s in ("BUST", "MAX_PAYOUTS", "OPEN")})
f1 = [p.payouts[0][0] for _, p in res if p.payouts]
print(f"days to 1st payout: median {median(f1):.0f}, payout amounts to you: first ${mean(float(p.payouts[0][1]) for _, p in res if p.payouts):,.0f}")
bust_days = [p.sessions for _, p in res if p.status == "BUST"]
print(f"busted accounts: median bust after {median(bust_days):.0f} trading days; paid before busting: "
      f"{sum(1 for _, p in res if p.status == 'BUST' and p.payouts) / max(1, len(bust_days)):.0%} got ≥1 payout first")
by = defaultdict(list)
for d, p in res: by[d[:4]].append(float(p.paid) * 5)
print("5-account first-year take-home by START year: " + " · ".join(f"{y}: avg ${mean(v):,.0f} / median ${median(v):,.0f} (n={len(v)})" for y, v in sorted(by.items())))
months = [0.0] * 12
for _, p in res:
    for day, amt in p.payouts: months[min(11, (day - 1) // 21)] += float(amt) * 5 / n
print("average 5-account income by month of the funded year: " + " · ".join(f"m{i + 1} ${m:,.0f}" for i, m in enumerate(months)))
