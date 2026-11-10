import json
r=json.load(open('results.json'));R=r['res']
WN=["A 09:36-11:30","L 03:00-11:30","B 03:00-11:00","C 03:00-09:30"]; PS=["2019-2023","2024-2026","last12m"]
def f(x): return f"{x['n']:.0f} | {x['win']:.0f}% | {x['pf']:.2f} | {x['net']:+,.0f} | {x['dd']:,.0f} | {x['avg']:+.1f}"
out=[]
for m,title in (("MNQ","MNQ (1 micro)"),("MGC","MGC (1 micro)"),("BOTH","MNQ + MGC combined (independent AI call per market)")):
  for p in PS:
    out.append(f"\n#### {title}, {p} (NEUTRAL skip 27%, mean of 200 seeds)\n\n| window | AI acc | trades | win | PF | net $ | max DD $ | avg $/trade |"+(" overlap w/ NOISE |" if m!="BOTH" else "")+"\n|---|---|---|---|---|---|---|---|"+("---|" if m!="BOTH" else ""))
    for w in WN:
      for a in (0.5,0.55,0.6,0.65,0.7):
        if w[0] in "BC" and a not in (0.6,0.7): continue
        x=R[f"{m}|{w}|0.27|{a}|{p}"]; out.append(f"| {w} | {int(a*100)}% | {f(x)} |"+(f" {x['ov_time_pct']:.0f}% |" if m!="BOTH" else ""))
out.append("\n#### Oracle / blind diagnostics (2024-2026, no NEUTRAL skips): AI 100% right, 0% right, always long, always short\n\n| market | window | case | trades | win | PF | net $ |\n|---|---|---|---|---|---|---|")
for m in ("MNQ","MGC"):
  for w in WN:
    for lab in ("oracle100","anti0","always_long","always_short"):
      x=r['diag'][f"{m}|{w}|{lab}|2024-2026"]; out.append(f"| {m} | {w} | {lab} | {x['n']:.0f} | {x['win']:.0f}% | {x['pf']:.2f} | {x['net']:+,.0f} |")
out.append("\n#### Sensitivity: agree-strong only (NEUTRAL skip 73%, ~0.27 trades/day), 70% accuracy, 2024-2026\n\n| market | window | trades | win | PF | net $ | max DD $ |\n|---|---|---|---|---|---|---|")
for m in ("MNQ","MGC","BOTH"):
  for w in WN[:2]:
    x=R[f"{m}|{w}|0.73|0.7|2024-2026"]; out.append(f"| {m} | {w} | {x['n']:.0f} | {x['win']:.0f}% | {x['pf']:.2f} | {x['net']:+,.0f} | {x['dd']:,.0f} |")
open('tables.md','w').write("\n".join(out)); print(len("\n".join(out)))
