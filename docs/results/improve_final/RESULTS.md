# improve_final (research only, 2026-11-23)
Sim = pass_fastest/final_search machinery (C40 day stop 38 %, DLL, EOD MLL, 1 position, no hedge). Baselines = D163 (150K cgrow 1500/6, 50K dl 0.4). Rule: floor 70/70/62/62, judge >= base-3, pick >= base-5, profit not cut, median strictly lower.

## A) Per-trade edge (streams pass_faster/streams_*.csv; pick 2021-23, judge 2024-26)
| change | pick PF / sum | judge PF / sum | 5y sum | verdict |
|---|---|---|---|---|
| NOISE base (lock80, Mon off) | 1.52 / +7,960 | 1.59 / +11,674 | +19,634 | - |
| NOISE drop late entries (150-270 min buckets) | 1.45 / +5,029 | 1.96 / +13,212 | +18,240 | REJECT: pick worse, cuts 5y profit |
| NOISE drop 210 bucket | 1.54 / +7,542 | 1.66 / +11,826 | +19,367 | REJECT: pick profit down |
| NOISE long-only / short-only | 1.75 vs 1.32 | 1.28 vs 1.89 | - | side edge flips by period, REJECT |
| NOISE skip Wednesday | 1.64 / +7,046 | 1.62 / +9,616 | +16,662 | REJECT (cuts profit) |
| CANDACE base | 1.37 / +675 | 1.26 / +557 | +1,232 | - |
| CANDACE skip Tuesday | 1.53 / +756 | 1.26 / +439 | +1,196 | REJECT |
| CANDACE nconf>=2 | 1.58 / +406 | 1.16 / +118 | +524 | REJECT (halves profit) |
| CANDACE grade != C / stop <= 30 | tiny n / PF 0.84 | | | REJECT |
CANDACE 10:0x entries: 15 trades, -68 pts only; not worth a rule. Result A: no change improves held-out profit without cutting 5y profit. Nothing adopted.

## B) Pass speed (134 new configs: day lock 0.1-0.8 incl. on CANDACE, NOISE lock 60-90, taper, brake bands x0.85-1.1, extra band steps)
| plan | base D163 (pass / med d / judge / pick) | feasible faster row | pass / med d / judge / pick / profit |
|---|---|---|---|
| 150K | 74.4 / 80 / 57.3 / 72.8 | none | - |
| 100K | 71.4 / 87 / 65.8 / 68.9 | none | - |
| 50K | 66.3 / 61 / 56.5 / 68.2 | day_lock_pct 0.3 | 67.2 / 60 / 58.0 / 68.2 / $39.1K (+0.9 pt, -1 d) |
| 25K | 61.8 / 56.5 / 54.6 / 62.5 | NOISE day_lock_pct 0.15 (0.10 gives 62.5/55) | 62.1 / 55 / 55.0 / 62.5 / $19.3K (-1.5 d) |
No A improvement exists to speed passing.

## Recommendation
Config-only: 50K day_lock_pct 0.4 -> 0.3; 25K add day_lock_pct 0.15. Both only stop NOISE earlier after a profit (shrink only). 100K/150K stay at D163. Gains are 1-1.5 days (small); static profit does not model the lock.
Scripts: scripts/improve.py, scripts/sweep_daylock.py (run from backend/ with PYTHONPATH=.), results.json.
