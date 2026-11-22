# Pro 150K "fast pass" structure on the smaller Lucid Pro plans (25K / 50K / 100K EVAL), research only, 2026-11-22

## In plain words
- **25K: yes, worth building.** NOISE 1 micro at a $75 stop plus CANDACE 2 micros, with CANDACE cut to 1 micro once the cushion is below $333,
  passes faster than today (median 56 days instead of 74 under C40, 52 instead of 69 under C50). It passes more often (61.8 % vs 58.6 % and 64.4 % vs 60.9 %),
  holds up much better on the held-out years (judge 54.6 % vs 38.6 %), and profit is about the same ($19,328 vs $19,293, +$35).
  It is the only config that qualifies under both C40 and C50.
- **50K: no.** No config is faster, robust and at least as profitable all at once. The 150K-style point (NOISE 2 @ $100 + CANDACE 1, both 1 micro below $667)
  is 18 days faster and robust under C50. But profit is $204 lower, and under C40 it is not robust (5-yr pass 65.9 % < 66.8 %). Keep BASE.
- **100K: yes, but not the scaled point.** Keep NOISE at today's 2 micros @ $250, add CANDACE 3 micros, and cut to NOISE 1 + CANDACE 2 below a $1,000 cushion.
  Median falls from 152 to 127 days (C40) and from 147 to 126 (C50), pass stays the same (78.0 / 78.2 %), and profit rises from $38,586 to $44,850.
  Caveat: "within 60 days" does not improve (5.2 % vs 5.8 %). The near-identical variant with CANDACE cut to 1 micro is the safer pick:
  pass 79.9 / 80.1 %, judge 64.3 / 64.7 %, median 130 / 128 days, same profit.
- Scaling the 150K point straight down by MLL (NOISE 3 + CANDACE 2 on 100K, 2 + 1 on 50K) is too aggressive below 150K. It fails ROBUST on 100K and 50K.
  More micros make passing faster but bust far more accounts.
- User addition: the $50 and $75 NOISE stops (25K, 50K). $50 is worse everywhere: less profit, fewer passes. $75 helps on 25K (it is part of the winner).
  On 50K it gives high pass rates (NOISE 1 @ $75 + CANDACE 1: 79 % C40 / 82 % C50), but it is slower than BASE (median 156 days) and has less than half the profit, so it fails the rule.

Decision rule (user): QUALIFIES = beats BASE median days to pass AND ROBUST AND profit ≥ BASE profit.
ROBUST = 5-yr pass ≥ BASE − 2 pts (50K also ≥ 59 %), judge pass ≥ BASE judge − 3, pick pass ≥ BASE pick − 5. "Best" = the qualifying config with the lowest median days.

## Verdict per plan (exact settings)
Brake = cushion (equity − MLL floor) **< MLL/3** (25K $333, 50K $667, 100K $1,000), strict `<` as in brake150 U1. CANDACE = D154 engine, fixed micros, $125 per-micro cap, one position at a time.

| plan | C40 | C50 |
|---|---|---|
| 25K | **N1@100+C1, no brake**: NOISE 1 micro, $100 stop; CANDACE 1 micro; median 52 d (BASE 74). Pass 56.8 % is only 1.8 pts above the ROBUST floor. Runner-up = the C50 pick, which also qualifies under C40: pass 61.8, median 56 | **N1@75+C2, brake CANDACE→1**: NOISE 1 micro, $75 stop, no NOISE brake; CANDACE 2 micros, 1 below $333; median 52 d (BASE 69), pass 64.4 %, profit $19,328 |
| 50K | none | none |
| 100K | **N2@250+C3, brake→1/2**: NOISE 2 micros, $250 stop, 1 below $1,000; CANDACE 3 micros, 2 below $1,000. Median 127 d (BASE 152), profit $44,850 | same config: median 126 d (BASE 147) |

Recommendation if one config per plan is wanted: **25K = N1@75+C2 brake→1/1** (it qualifies in both C40 and C50, and it is the most robust).
**100K = N2@250+C3 brake→1/1** (1-3 days slower median than the fastest, but higher pass and judge in both C40 and C50). 50K = keep BASE.
Needs code (same as the 150K study): CANDACE fixed micros and the CANDACE brake band. The NOISE size and stop come from the size table and stop config.

## Reproduction (stop rule)
BASE recomputed with this simulator = pass_faster_100/results.json to the last digit (all windows: pass, stuck, <=60d, median, profit):
25K 58.6 / 23.0 / 74, 50K 68.8 / 19.7 / 92, 100K 77.7 / 5.8 / 152. Plan constants are asserted equal to the old loader (`run_small.py check`).

## Tables (top 5 by median days, C40 and C50)
Columns: pass 5y / stuck (incl. bust) / passed within 60 days / median days to pass (passers) / expected days to the first pass with resets (renewal chain; censored share) /
pick 2021-10..2023-12 pass / judge 2024-01..2026-10 pass / plan-sized static profit over 5 years.

### 25K C40 (ROBUST: 5y ≥ 56.6, judge ≥ 35.6, pick ≥ 53.9) - 50 configs, 6 ROBUST, 2 qualify
| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick | judge | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE (N1@250) | 58.6 | 35.9 | 23.0 | 74 | 117 (12 %) | 58.9 | 38.6 | 19,293 | - | - |
| N1@100+C1 nobrake | 56.8 | 34.6 | 33.1 | 52 | 103 (9 %) | 63.1 | 48.9 | 20,115 | YES | YES |
| N1@75+C2 brake->1/1 | 61.8 | 29.6 | 33.7 | 56 | 95 (9 %) | 62.5 | 54.6 | 19,328 | YES | YES |
| fastest any: N2@250+C3 brake->1/1 | 24.6 | 74.6 | 24.5 | 18 | 73 (11 %) | 31.8 | 19.0 | 44,850 | no | no |

### 25K C50 (ROBUST: 5y ≥ 58.9, judge ≥ 37.6, pick ≥ 56.6) - 1 qualifies
| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick | judge | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 60.9 | 34.3 | 26.0 | 69 | 112 (6 %) | 61.6 | 40.6 | 19,293 | - | - |
| N1@75+C2 brake->1/1 | 64.4 | 29.6 | 39.0 | 52 | 91 (6 %) | 62.5 | 59.1 | 19,328 | YES | YES |
| N1@100+C1 nobrake | 58.8 | 34.3 | 35.5 | 50 | 100 (7 %) | 63.1 | 52.5 | 20,115 | no (−0.1) | no |

### 50K (C40 ROBUST: 5y ≥ 66.8, judge ≥ 52.3, pick ≥ 68.1; C50: ≥ 68.0 / 54.4 / 68.1) - 90 configs each, 0 qualify
| config | cons | pass 5y | stuck | <=60d | median d | exp. days (cens) | pick | judge | profit $ | ROBUST |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE (N2@250, 1 below 50 %) | C40 | 68.8 | 21.4 | 19.7 | 92 | 133 (13 %) | 73.1 | 55.3 | 38,586 | - |
| BASE | C50 | 70.0 | 20.5 | 20.8 | 88 | 127 (12 %) | 73.1 | 57.4 | 38,586 | - |
| N2@100+C1 brake->1/1 (scaled) | C40 | 65.9 | 25.2 | 25.5 | 71 | 120 (9 %) | 69.5 | 52.8 | 38,382 | no |
| N2@100+C1 brake->1/1 (scaled) | C50 | 68.5 | 24.6 | 26.3 | 70 | 117 (7 %) | 69.5 | 57.4 | 38,382 | YES (profit −$204) |
| N2@100+C0 brake->1/0 | C50 | 73.0 | 19.6 | 21.6 | 80 | 129 (7 %) | 70.4 | 55.2 | 35,251 | YES (profit −$3,335) |
| N2@250+C1 brake->1/1 | C50 | 67.7 | 26.0 | 29.0 | 69 | 114 (8 %) | 72.4 | 53.6 | 41,154 | no (5y, judge) |
| N1@75+C1 nobrake | C50 | 82.4 | 9.4 | 3.4 | 156 | 194 (8 %) | 65.1 | 68.8 | 17,480 | no (pick); slower, half profit |
| fastest any: N3@250+C3 brake->2/2 | C50 | 50.2 | 48.0 | 39.1 | 35 | 75 (2 %) | 49.0 | 49.1 | 64,503 | no |

### 100K C40 (ROBUST: 5y ≥ 75.7, judge ≥ 57.4, pick ≥ 60.1) - 63 configs, 13 ROBUST, 8 qualify
| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick | judge | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE (N2@250, 1 below 30 %) | 77.7 | 11.3 | 5.8 | 152 | 185 (11 %) | 65.1 | 60.4 | 38,586 | - | - |
| N2@250+C3 brake->1/2 | 78.0 | 11.3 | 5.2 | 127 | 166 (11 %) | 64.0 | 60.9 | 44,850 | YES | YES |
| N2@250+C3 brake->1/1 | 79.9 | 9.3 | 5.2 | 130 | 169 (11 %) | 64.0 | 64.3 | 44,850 | YES | YES |
| N2@100+C3 brake->1/2 | 79.1 | 10.8 | 3.0 | 131 | 172 (10 %) | 64.5 | 62.8 | 42,078 | YES | YES |
| N2@100+C3 brake->1/1 | 79.1 | 10.8 | 3.0 | 132 | 172 (10 %) | 64.5 | 62.8 | 42,078 | YES | YES |
| N2@150+C2 brake->1/1 | 79.1 | 12.3 | 4.4 | 136 | 182 (9 %) | 61.2 | 65.0 | 39,635 | YES | YES |
| N3@100+C2 brake->2/1 (scaled) | 65.3 | 25.8 | 13.9 | 87 | 135 (9 %) | 71.3 | 51.3 | 58,498 | no | no |

### 100K C50 (ROBUST: 5y ≥ 76.9, judge ≥ 59.6, pick ≥ 60.1) - 8 qualify
| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick | judge | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 78.9 | 11.3 | 5.8 | 147 | 178 (10 %) | 65.1 | 62.6 | 38,586 | - | - |
| N2@250+C3 brake->1/2 | 78.2 | 11.3 | 5.4 | 126 | 163 (11 %) | 64.0 | 61.3 | 44,850 | YES | YES |
| N2@100+C3 brake->1/2 | 80.2 | 10.8 | 3.5 | 126 | 167 (9 %) | 64.5 | 64.8 | 42,078 | YES | YES |
| N2@250+C3 brake->1/1 | 80.1 | 9.3 | 5.4 | 128 | 165 (11 %) | 64.0 | 64.7 | 44,850 | YES | YES |
| N2@100+C3 brake->1/1 | 80.2 | 10.8 | 3.5 | 129 | 169 (9 %) | 64.5 | 64.8 | 42,078 | YES | YES |
| N2@100+C2 brake->1/1 | 79.1 | 11.7 | 3.1 | 132 | 173 (9 %) | 64.7 | 63.1 | 40,230 | YES | YES |

Full tables (with the fastest-overall rows): `tables.md`. All numbers: `results.json` (key `plan|C40/C50|config`).

## Method
- Simulator: `../sim150.py` with the brake150 size bands (`../brake150/brake150.load_sim`). Only the plan constants are swapped per plan
  (size, target, MLL, lock trigger and level, DLL, per-trade cap). Everything else is unchanged: EOD MLL + lock, DLL + LucidScale, consistency + day stop (C40 38 %, C50 48 %),
  kill distance + room check, D57 shrink, one position at a time, no hedge, flat by close. 1,252 rolling starts over 5 years.
- Grid: NOISE micros {s−1, s, s+1} with s = round(4 × MLL / 4,500) (25K 1, 50K 2, 100K 3); NOISE stop per micro {$100, $150, $250}, plus $50 and $75 on 25K and 50K (user addition;
  the $50 stream was generated with the same `gen_lib.noise_stream` generator; the $75 stream was already cached); CANDACE {0, 1, 2, 3}; brake below MLL/3 to {half = ceil(n/2), 1 micro} for NOISE and CANDACE together.
  25K has 50 configs, 50K 90 and 100K 63, each run under C40 and C50.
- Profit = plan-sized static replay (brake-independent), same as brake150.
- Name format: `N<noise micros>@<stop $>+C<candace micros> brake-><noise>/<candace>` = the micros used below the brake line.

Run: `cd backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/smaller_plans/run_small.py` (about 10 s on 4 processes), then `python3 report.py > tables.md`.
