Data: 1266 RTH days 2021-10-01..2026-10-30; IS = 2021-10-01..2023-12-29 (561 days, 27 months), J = 2024-01-02..2026-10-30 (705 days, 34 months). Cost $2.00 per micro RT, $2/pt. History = 3 prior days.
## Validation

- ctm_lib mirror vs engine replay_day (BASE): mismatching days = 0 of 1266; BASE signals 100 (IS 53, J 47).
- this study's generic multi-episode code in REPLACE mode vs engine: mismatching days = 0 of 1266.
- no-lookahead check (20 days with signals per variant; replay truncated at every signal time, signals up to t must be identical): V1 20 days / 22 cut points / 0 differences; V2 20 days / 21 cut points / 0 differences; V3 20 days / 21 cut points / 0 differences

## Table A: 1 micro after costs, IS (2021-10..2023-12) and J (2024-01..2026-10)

| row | IS trades | /month | win % | PF | avg $ | total $ | max DD $ | J trades | /month | win % | PF | avg $ | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE engine as is | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 47 | 1.38 | 42.6 | 2.05 | 25.8 | 1,211 | 452 |
| V1 KEEP_ALL | 160 | 5.93 | 40.6 | 1.27 | 6.4 | 1,030 | 478 | 150 | 4.41 | 37.3 | 1.18 | 5.4 | 814 | 504 |
| V2 SAME_SIDE | 90 | 3.33 | 34.4 | 1.00 | -0.0 | -3 | 556 | 79 | 2.32 | 36.7 | 1.28 | 7.9 | 626 | 734 |
| V3 PROTECT_FORMED | 78 | 2.89 | 30.8 | 0.89 | -2.9 | -224 | 518 | 82 | 2.41 | 35.4 | 1.21 | 6.0 | 490 | 514 |
| BASE@1030 engine as is window 10:30 | 118 | 4.37 | 32.2 | 0.75 | -6.4 | -760 | 922 | 116 | 3.41 | 43.1 | 1.42 | 11.0 | 1,280 | 648 |
| V1@1030 KEEP_ALL window 10:30 | 408 | 15.11 | 36.3 | 1.00 | 0.1 | 36 | 1,341 | 390 | 11.47 | 39.2 | 1.04 | 1.1 | 418 | 1,248 |

## Table B: Lucid-fit sizing incl. grade rule (static, full room): total $ / max DD $ / taken of signals (sized 0 = signals - taken)

| row | IS 25K total | DD | taken | IS 50K total | DD | taken | J 25K total | DD | taken | J 50K total | DD | taken | J 100K total | taken | J 150K total | taken |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE engine as is | -226 | 306 | 25/53 | -994 | 1,032 | 53/53 | -287 | 287 | 12/47 | 876 | 573 | 47/47 | 834 | 47/47 | 1,526 | 47/47 |
| V1 KEEP_ALL | 188 | 386 | 65/160 | 762 | 1,034 | 160/160 | -396 | 570 | 34/150 | 40 | 1,174 | 150/150 | -1,120 | 150/150 | -1,322 | 150/150 |
| V2 SAME_SIDE | -103 | 242 | 35/90 | -640 | 1,093 | 90/90 | -330 | 330 | 22/79 | 226 | 1,020 | 79/79 | -219 | 79/79 | -246 | 79/79 |
| V3 PROTECT_FORMED | -211 | 330 | 31/78 | -982 | 998 | 78/78 | -522 | 522 | 23/82 | -334 | 890 | 82/82 | -988 | 82/82 | -1,635 | 82/82 |
| BASE@1030 engine as is window 10:30 | -18 | 324 | 66/118 | -1,451 | 1,758 | 118/118 | 220 | 269 | 37/116 | 1,734 | 933 | 116/116 | 2,284 | 116/116 | 3,544 | 116/116 |
| V1@1030 KEEP_ALL window 10:30 | -580 | 836 | 179/408 | -1,908 | 2,974 | 408/408 | -192 | 616 | 114/390 | 96 | 1,630 | 390/390 | -1,362 | 390/390 | -1,750 | 390/390 |

## Table C: Lucid Pro eval, all rules (EOD trailing MLL + lock, DLL, 40% consistency + day stop, kill distance, 1 position, size shrinks with MLL room). pass % / bust % (rolling start every day in the period)

| row | IS 25K | IS 50K | IS 100K | IS 150K | J 25K | J 50K | J 100K | J 150K |
|---|---|---|---|---|---|---|---|---|
| BASE engine as is | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| V1 KEEP_ALL | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| V2 SAME_SIDE | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| V3 PROTECT_FORMED | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| BASE@1030 engine as is window 10:30 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| V1@1030 KEEP_ALL window 10:30 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |

## Table D: Pro 50K block (and 25K beside it), IS and J

| row | period | plan | taken | sized 0 | median contracts | total $ | max DD $ | eval pass % | bust % | still running % | median days to pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE engine as is | IS | 50K | 53 | 0 | 2 | -994 | 1,032 | 0.0 | 0.0 | 100.0 | - |
| BASE engine as is | IS | 25K | 25 | 28 | 1 | -226 | 306 | 0.0 | 0.0 | 100.0 | - |
| BASE engine as is | J | 50K | 47 | 0 | 1 | 876 | 573 | 0.0 | 0.0 | 100.0 | - |
| BASE engine as is | J | 25K | 12 | 35 | 1.0 | -287 | 287 | 0.0 | 0.0 | 100.0 | - |
| V1 KEEP_ALL | IS | 50K | 160 | 0 | 2.0 | 762 | 1,034 | 0.0 | 0.0 | 100.0 | - |
| V1 KEEP_ALL | IS | 25K | 65 | 95 | 1 | 188 | 386 | 0.0 | 0.0 | 100.0 | - |
| V1 KEEP_ALL | J | 50K | 150 | 0 | 1.0 | 40 | 1,174 | 0.0 | 0.0 | 100.0 | - |
| V1 KEEP_ALL | J | 25K | 34 | 116 | 1.0 | -396 | 570 | 0.0 | 0.0 | 100.0 | - |
| V2 SAME_SIDE | IS | 50K | 90 | 0 | 2.0 | -640 | 1,093 | 0.0 | 0.0 | 100.0 | - |
| V2 SAME_SIDE | IS | 25K | 35 | 55 | 1 | -103 | 242 | 0.0 | 0.0 | 100.0 | - |
| V2 SAME_SIDE | J | 50K | 79 | 0 | 1 | 226 | 1,020 | 0.0 | 0.0 | 100.0 | - |
| V2 SAME_SIDE | J | 25K | 22 | 57 | 1.0 | -330 | 330 | 0.0 | 0.0 | 100.0 | - |
| V3 PROTECT_FORMED | IS | 50K | 78 | 0 | 2.0 | -982 | 998 | 0.0 | 0.0 | 100.0 | - |
| V3 PROTECT_FORMED | IS | 25K | 31 | 47 | 1 | -211 | 330 | 0.0 | 0.0 | 100.0 | - |
| V3 PROTECT_FORMED | J | 50K | 82 | 0 | 1.0 | -334 | 890 | 0.0 | 0.0 | 100.0 | - |
| V3 PROTECT_FORMED | J | 25K | 23 | 59 | 1 | -522 | 522 | 0.0 | 0.0 | 100.0 | - |
| BASE@1030 engine as is window 10:30 | IS | 50K | 118 | 0 | 2.0 | -1,451 | 1,758 | 0.0 | 0.0 | 100.0 | - |
| BASE@1030 engine as is window 10:30 | IS | 25K | 66 | 52 | 1.0 | -18 | 324 | 0.0 | 0.0 | 100.0 | - |
| BASE@1030 engine as is window 10:30 | J | 50K | 116 | 0 | 1.0 | 1,734 | 933 | 0.0 | 0.0 | 100.0 | - |
| BASE@1030 engine as is window 10:30 | J | 25K | 37 | 79 | 1 | 220 | 269 | 0.0 | 0.0 | 100.0 | - |
| V1@1030 KEEP_ALL window 10:30 | IS | 50K | 408 | 0 | 2.0 | -1,908 | 2,974 | 0.0 | 0.0 | 100.0 | - |
| V1@1030 KEEP_ALL window 10:30 | IS | 25K | 179 | 229 | 1 | -580 | 836 | 0.0 | 0.0 | 100.0 | - |
| V1@1030 KEEP_ALL window 10:30 | J | 50K | 390 | 0 | 1.0 | 96 | 1,630 | 0.0 | 0.0 | 100.0 | - |
| V1@1030 KEEP_ALL window 10:30 | J | 25K | 114 | 276 | 1.0 | -192 | 616 | 0.0 | 0.0 | 100.0 | - |

## Table E: 10 equal chunks of the 5 years (126-127 days each): trades / 1-micro $ / PF / 25K-fit $ / 50K-fit $

| chunk | days | BASE | V1 | V2 | V3 | BASE@1030 | V1@1030 |
|---|---|---|---|---|---|---|---|
| 1 | 2021-10-01..2022-04-01 | 12 / -207 / 0.40 / 14 / -280 | 37 / -168 / 0.85 / -67 / -513 | 18 / -440 / 0.28 / -49 / -660 | 19 / -466 / 0.27 / -49 / -686 | 22 / -312 / 0.52 / -16 / -432 | 87 / -611 / 0.77 / -498 / -1,758 |
| 2 | 2022-04-04..2022-10-04 | 12 / 4 / 1.01 / -20 / -188 | 37 / 518 / 1.53 / 51 / 421 | 21 / 350 / 1.68 / -30 / 129 | 18 / 212 / 1.44 / -34 / -34 | 29 / -157 / 0.82 / -42 / -504 | 103 / -123 / 0.96 / -122 / -378 |
| 3 | 2022-10-05..2023-04-06 | 11 / 83 / 1.33 / 20 / 204 | 39 / 987 / 2.45 / 384 / 1,454 | 22 / 604 / 2.75 / 152 / 804 | 20 / 417 / 2.13 / 136 / 584 | 25 / 7 / 1.01 / 288 / 372 | 100 / 960 / 1.45 / 442 / 1,549 |
| 4 | 2023-04-10..2023-10-10 | 12 / -221 / 0.42 / -128 / -366 | 33 / -211 / 0.75 / -22 / -167 | 21 / -431 / 0.40 / -59 / -572 | 14 / -266 / 0.37 / -152 / -477 | 30 / -268 / 0.65 / -222 / -702 | 84 / -468 / 0.76 / -378 / -1,282 |
| 5 | 2023-10-11..2024-04-15 | 10 / -241 / 0.00 / -207 / -645 | 23 / 12 / 1.03 / -182 / -384 | 16 / -28 / 0.89 / -222 / -464 | 12 / -240 / 0.03 / -200 / -638 | 27 / 121 / 1.26 / 98 / 71 | 74 / 204 / 1.15 / 134 / 20 |
| 6 | 2024-04-16..2024-10-15 | 11 / 97 / 1.53 / 9 / 62 | 33 / -258 / 0.68 / 124 / -102 | 20 / 82 / 1.21 / 74 / 216 | 22 / -132 / 0.75 / -98 / -437 | 22 / 118 / 1.27 / 74 / 173 | 83 / -633 / 0.72 / 7 / -338 |
| 7 | 2024-10-16..2025-04-23 | 6 / 484 / 4.74 / -24 / 660 | 23 / 359 / 1.45 / -108 / 96 | 10 / 260 / 1.73 / -24 / 391 | 12 / 366 / 2.15 / -70 / 405 | 16 / 282 / 1.55 / 20 / 478 | 66 / -26 / 0.99 / 118 / -54 |
| 8 | 2025-04-24..2025-10-23 | 7 / -346 / 0.01 / -36 / -424 | 34 / -390 / 0.65 / -234 / -798 | 15 / -629 / 0.05 / -134 / -871 | 17 / -362 / 0.49 / -72 / -474 | 23 / -472 / 0.41 / -183 / -596 | 81 / -54 / 0.97 / -342 / -230 |
| 9 | 2025-10-24..2026-04-30 | 12 / 944 / 9.40 / 0 / 944 | 25 / 938 / 2.46 / -21 / 974 | 15 / 772 / 3.72 / 0 / 772 | 14 / 688 / 3.51 / -21 / 666 | 26 / 633 / 1.90 / 102 / 875 | 65 / 457 / 1.24 / -68 / 264 |
| 10 | 2026-05-01..2026-10-30 | 7 / 158 / 1.64 / -140 / -84 | 26 / 57 / 1.06 / -134 / -178 | 11 / 82 / 1.21 / -140 / -160 | 12 / 50 / 1.11 / -172 / -224 | 14 / 568 / 2.65 / 83 / 550 | 55 / 747 / 1.43 / -67 / 395 |

## Table F: win % (net of cost, 1 micro) by entry half-hour, all 5 years: wins / trades

| row | 09:30-10:00 | 10:00-10:30 |
|---|---|---|
| BASE engine as is | 34.0% (34/100) | - |
| V1 KEEP_ALL | 39.0% (121/310) | - |
| V2 SAME_SIDE | 35.5% (60/169) | - |
| V3 PROTECT_FORMED | 33.1% (53/160) | - |
| BASE@1030 engine as is window 10:30 | 34.0% (34/100) | 40.3% (54/134) |
| V1@1030 KEEP_ALL window 10:30 | 39.0% (121/310) | 36.9% (180/488) |

## Table G: episode bookkeeping (all 5 years)

| row | sweep episodes | valid IFVG | retraces | A2 fail | D2 fail | timeouts | replaced | sweeps ignored (V3) | signals skipped, position open | skipped, same bar | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE engine as is | - | - | - | - | - | - | - | - | - | - | 100 |
| V1 KEEP_ALL | 9911 | 1430 | 934 | 337 | 147 | 2818 | 0 | 0 | 18 | 122 | 310 |
| V2 SAME_SIDE | 9911 | 685 | 397 | 161 | 66 | 490 | 7062 | 0 | 1 | 0 | 169 |
| V3 PROTECT_FORMED | 9526 | 550 | 356 | 137 | 58 | 208 | 7816 | 574 | 1 | 0 | 160 |
| BASE@1030 engine as is window 10:30 | - | - | - | - | - | - | - | - | - | - | 234 |
| V1@1030 KEEP_ALL window 10:30 | 18810 | 3441 | 2344 | 782 | 357 | 7978 | 0 | 0 | 59 | 348 | 798 |

## IS filter (vs BASE 10:00): more IS trades, IS PF >= 1.10, IS 1-micro $ >= base, IS 25K-fit $ >= base, IS 50K-fit $ >= base

| row | more trades | PF >= 1.10 | 1-micro $ | 25K $ | 50K $ | ELIGIBLE | IS PF | IS 1-micro $ | IS 25K $ | IS 50K $ |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | | | | | | | 0.69 | -456 | -226 | -994 |
| V1 | yes | yes | yes | yes | yes | yes | 1.27 | 1,030 | 188 | 762 |
| V2 | yes | no | yes | yes | yes | no | 1.00 | -3 | -103 | -640 |
| V3 | yes | no | yes | yes | yes | no | 0.89 | -224 | -211 | -982 |

IS pick (highest IS 25K-fit total among eligible): V1

## J check (J = 2024-01..2026-10; seen by earlier sessions) for every IS-eligible row

| row | J 1-micro $ >= base | J 25K $ >= base | J 50K $ >= base | J PF > 1 | J trades >= base | 25K pass/bust within 2 pts | 50K pass/bust within 2 pts | J trades | VERDICT |
|---|---|---|---|---|---|---|---|---|---|
| V1 KEEP_ALL | no | no | no | yes | yes | yes | yes | 150 | REJECT |
| V1@1030 KEEP_ALL window 10:30 | no | yes | no | yes | yes | yes | yes | 390 | REJECT |

## Window 10:30 rows: IS filter vs BASE (10:00 engine as is) and vs BASE@1030

| row | vs BASE 10:00 eligible | vs BASE@1030 eligible |
|---|---|---|
| V1@1030 | no (more yes, PF no, 1m yes, 25K no, 50K no) | no (more yes, PF no, 1m yes, 25K no, 50K no) |

Variants tested: 3 at window 10:00 + 1 at window 10:30 = 4 (+ BASE refs).
