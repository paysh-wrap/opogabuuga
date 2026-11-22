# Pass >= 70 % speed search (research only, 2026-11-22)

## Update: smaller plans at floor 62 % (user refinement; 100K/150K stay at 70 %)
Same robust rules (profit >= BASE, judge >= BASE-3, pick >= BASE-5), pass >= 62.
- 25K: fastest = median 56 d (pass 62.2-62.5, within-60 34-35 %, resets 95-100 d). Built is 61.8 % / 56.5 d: no real speed gain. KEEP BUILT. Best row: N1@$75 + C2, CANDACE brake to 1 at cushion $600, day lock 0.5 (62.5 %, 56 d, w60 34.4, resets 95, judge 56.0, pick 62.5, profit $19.3K; needs code).
- 50K: big gain at 62 %: N2@$75, NOISE 2 -> 1 at cushion $667, CANDACE 4 -> 3 at 50 % cushion, day lock 0.5, NOISE lock 80: pass 66.3 %, median 62 d (BASE 92), within-60 32.2 %, resets 114 d, judge 56.5, pick 68.2, profit $39.1K (BASE $38.6K), stuck 26.2 %. Alt: CANDACE 4 -> 2: 65.7 %, 62 d, resets 108 d. Needs code (CANDACE). ADOPT if pass 66 vs 69 for 30 fewer median days is acceptable.

## Plain answer
- Floor used: 5-year pass >= 70.0 %. Also: profit >= BASE profit, judge pass >= BASE judge - 3, pick pass >= BASE pick - 5. All Lucid rules on (C40, day stop 38 %, DLL ON, EOD MLL).
- 150K: YES, a faster setup exists. Fastest found: median 78 d vs built 86 d, but it only just clears 70 (70.4 %) and loses pass (built 74.3 %) and judge. The better trade is a 5-micro setup with a bigger CANDACE: median 81 d, pass 70.7 %.
  Setups with pass 76-79 % reach median 82-90 d; none beats the built 86 d AND keeps the built 74.3 % pass by much (76.4 % / 82 d is the cleanest win).
- 100K: YES, big gain. Built is median 121 d (pass 80.4). Pass-70 setups reach 87 d (3 micros). Mid-way: 78.4 % pass at 94.5 d, 82.2 % at 106 d.
- 50K: 70 % is reachable (best feasible 73.2 %), but only slightly faster than BASE (median 90 vs 92). Config-only.
- 25K: 70 % is NOT reachable. Max pass found 63.5 % (median 73 d, N1 @ $75, no CANDACE, day lock 0.5). Best robust: 62.5 % / median 56 d. Built (61.8 %, median 56.5) is already the speed optimum. Keep built.

## Verdicts
- 150K: adopt ONLY if you accept ~70-76 % pass. Recommended: row "76.4 % / 82 d" (N5@$100, NOISE brake 2250>2 then 1500>1, CANDACE 5 with 2700>4 then 1500>1, grow 500 to 6, dl 0.7): beats built speed (86 d), pass 76.4 vs 74.3, profit $100.6K vs $98.7K, judge 58.0 (floor 56.3). Needs code (CANDACE size / two-step brake) and the existing D159 micro cap lift. A fast 78 d row exists at only 70.4 % pass - not recommended (judge close to floor, more stuck 18.8 %).
- 100K: ADOPT. e.g. N3 @ $100, NOISE 3 micros (1000>2), CANDACE 3 micros (600>2), day lock 0.5: pass 71.4 %, median 87 d (built 121), within-60 14.9 % (built 6.0), with-resets 131 d (built 159), profit $60.3K (built $46.7K), judge 65.8, pick 68.9. Safer middle: N3[1500>2,1000>1] C3 same, 78.4 % / 94.5 d. Needs code (CANDACE) and N3 above the 100K eval cap (D159-style fast-pass lift).
- 50K: ADOPT only the config-only tweak (N2@$250, brake to 1 at cushion 1000, NOISE lock 80, taper): pass 73.2 %, median 94 (BASE 68.8 %, 92 d) = more pass, same speed; or day lock + lock 80: 72.0 % / 90 d. Marginal speed gain (2 d); the real gain is +3-4 pts pass. Optional.
- 25K: KEEP BUILT.

## Tables (compact; full output in tables.md)
Top-5 by median days (feasible):
| plan | pass | med d | w60 % | resets d | judge | pick | profit |
|---|---|---|---|---|---|---|---|
| 150K built N5@100+C4 | 74.3 | 86 | 20.4 | 130 | 64.5 | 66.7 | 98.7K |
| 150K #1 N5 grow dl0.7 lock80 C2 | 70.4 | 78 | 23.2 | 150 | 61.1 | 68.7 | 94.9K |
| 150K #4 N5[1500>4,900>2] C5[2250>3,1500>1] | 70.7 | 81 | 22.4 | 127 | 62.1 | 69.3 | 100.6K |
| 150K Pareto 76.4 N5 C5 grow | 76.4 | 82 | 25.9 | 145 | 58.0 | 72.8 | 100.6K |
| 100K built N2@250+C4 | 80.4 | 121 | 6.0 | 159 | 65.7 | 64.0 | 46.7K |
| 100K #4 N3[1000>2] C3[600>2] dl0.5 | 71.4 | 87 | 14.9 | 131 | 65.8 | 68.9 | 60.3K |
| 100K N3[1500>1] C4[1500>2,600>1] dl0.5 | 77.4 | 94 | 18.1 | 136 | 59.9 | 70.9 | 62.2K |
| 50K BASE | 68.8 | 92 | - | - | 55.3 | 73.1 | 38.6K |
| 50K best | 72.0 | 90 | 21.5 | 131 | 62.3 | 72.0 | 39.3K |
| 25K built N1@75+C2 | 61.8 | 56.5 | 33.7 | - | - | - | 19.3K |
| 25K best robust | 62.5 | 56 | 34.4 | 95 | 56.0 | 62.5 | 19.3K |
| 25K max pass | 63.5 | 73 | - | - | 51.1 | 68.0 | 15.3K |

Higher pass costs days: 150K 90 % pass = median 144 d; 100K 90 % = 138 d. Pareto lists in tables.md.

## Tags
Config-only: all 50K winners (CANDACE 0, size_table_eval brake + lock/taper/dlock existing fields), 25K max-pass row.
Needs code: every row with CANDACE micros / CANDACE brake (150K, 100K, 25K best robust). Also N above plan eval cap (150K N5+, 100K N3) = D159 fast-pass lift.

## Method
Reused ~37K evaluated configs (passfloor/, within60/) + 19,290 new grid + 4,445 extras. Grid: 150K stops 50-125, NOISE 5-10, CANDACE 3-8, brake cushions $1,000/1,500/2,500; 100K stops 75-250, NOISE 2-6, CANDACE 2-6, cushions $750/1,500/2,000; 50K and 25K small grids (N 1-4, CANDACE 0-4, stops 50-250). Single-step brakes in stage 1; extras (NOISE lock 80/100/120, day lock 0.5/0.7, taper, grow +1/$500 or $1,000) on top-25 feasible + top-15 by pass. Not searched: two-step brakes in stage 1 beyond those found in old stores, NOISE 10 with CANDACE 8 combos at stops < $100 on 100K, CANDACE grow. Built 150K/100K reproduced exactly (74.3 / 86; 80.4 / 121).
Files: pass70.py (search), report.py (tables), results.json, tables.md. Run from backend/ with PYTHONPATH=.
Note: the "BASE" used for floors is the earlier-study BASE (150K pass 77.1 med 159, profit $57,879; 100K 77.7 / 152; 50K 68.8 / 92; 25K 58.6 / 74).
