# Beat 109 days (Pro 150K EVAL, research only, 2026-11-22)

## Plain answer
YES. Median days to pass can go well below 109 and still meet the user's robust rule.
- Reproduced U1 first: C40 pass 78.8 %, median 109, within-60 9.3 %, profit $78,612 (C50 median 107).
- Best robust setting (C40 and C50): NOISE 5 micros @ $100 stop + CANDACE 4 micros, both cut to 2 micros when cushion <= $1,500
  (U1's brake, only +1 micro NOISE and +1 micro CANDACE). C40: pass 74.3 %, median 86 d (was 109), within-60 20.4 % (was 9.3),
  days to first pass with resets 130 (U1 150), judge 64.5, pick 66.7, plan-sized profit $98,728 (U1 $78,612, BASE $57,879).
  C50: pass 76.4 %, median 86 d, within-60 20.8 %, with resets 128 d.
- Fastest robust median: same, brake cushion $2,000 -> 2 micros: median 84 d (C40), but judge pass only 57.4 (floor 56.3). I prefer the $1,500 row (judge 64.5).
- Day lock (0.33 of remaining target) changes little (+/- 1 day).
- Faster exist (NOISE 8 micros: median 43-47 d) but pass only 40 %, so they fail ROBUST. Not recommended.
- 38 of 155 configs beat 109 and are robust under C40; 49 under C50.
- Cost: pass rate is lower than U1 (74 vs 79); more stuck/bust accounts. Judge window still above BASE (59.3).

## Tags
- NOISE 5 micros: config-only but a D133 rule change (`eval_size_caps` 150K max_contracts 5 or `eval_size_s19: false`; size_table_eval row contracts 5, brake_below 0.333, brake_contracts 2, stop_usd 100).
- NOISE grow / taper / day lock: config-only (existing SizeTierCfg fields).
- CANDACE fixed 4 micros + CANDACE brake to 2 micros at cushion <= $1,500: needs code (same as U1).

## Robust rule used
5-yr pass >= 70 %, judge (2024-01..2026-10) >= BASE judge - 3 (C40 56.3, C50 56.7), pick (2021-10..2023-12) >= BASE pick - 5 (60.1), plan-sized profit >= BASE ($57,879).
All Lucid checks on (EOD MLL + lock, DLL + LucidScale, kill distance, room check, D57 shrink, one position, consistency pass check + day stop 38 % C40 / 48 % C50).
155 configs x 2 consistency: stage 1 = stop {75,100,125,150} x NOISE {4,5,6,8} x CANDACE {2,3,4,5} (brake $1,500 -> 2);
stage 2 = brake cushion {1,000, 1,500, 2,000} x {2,3} micros on the best; stage 3 = taper / grow (+1 per $2,000 cushion, up to N+2) / day lock on the best.
Brake applies to NOISE and CANDACE together (as U1). CANDACE grow and separate brakes not searched.

## Tables (full output of report.py)
See tables.md in this folder. All runs: results.json. Search: beat109.py. Tables: report.py.
