# GALA: why it rarely trades, and what adds trades (research only, nothing implemented)

Script `gala_trade_more.py` (engine `gala_pa.replay_day` called unchanged; all settings inside GalaPaCfg validators, no model_copy needed). Data: 5-year MNQ 1-minute RTH, 1266 days. Pick window IS = 2021-10-01..2023-12-31 (27 months), judge window J = 2024-01-01..2026-10-30 (34 months). Costs $2.00 per micro round trip + $2/pt. Lucid sim = backtest_new.py's eval (EOD trailing MLL with lock, DLL + LucidScale, 40% consistency + 38% day stop, profitable-days minimum, kill-switch distance, one trade at a time, size shrinks with MLL room), rolling start every trading day inside each window; D152 trim applied when the fit size is 2+ micros. "fit 25K/50K $" in the tables = every trade sized by the Lucid-fit rule at full account room (static, not the path-dependent sim), trim applied.

## Plain summary

**Why it does not trade.** GALA needs a price level, and the level it picks is far away. Per setup day (trend day with a level; 740 of 1266 days) the engine builds a median of 4 hourly body-pivot levels (A4, mean 4.3), then A6 deletes about half of them (1527 of 3211, 48%) because a later hourly body closed through them. Of those deletions 35% were first made by the single overnight gap candle (A7) and 65% by regular hourly candles (in the 2-year window 41% / 59%). What survives is a median of 2 levels per day, and the nearest one to the 09:30 open is a median 233 pt away (262 pt in the 2-year window, quartiles about 100 and 450). A surviving level sits within 50 pt on only 13% of setup days, within 100 pt on 26%, within 150 pt on 37%. So the distance comes from the transcript rules (A4 level definition at hourly body pivots + A6 delete-when-pierced + A8 pick the nearest surviving one), not from one open setting: any level close to price has by construction already been pierced by a body, so only old extremes survive. The only open settings that touch this (pivot_lookback, history_sessions) move it only a little. The open setting that blocks the most otherwise-valid entries is `window_end` (10:35): the earlier funnel found 21 of 27 valid entries in 2 years come after 10:35.

**What adds trades.** In J only the later `window_end` values add a meaningful number of trades: 10 baseline trades in J (0.29/month) go to 18 (11:00), 26 (11:30), 31 (12:30), 41 (14:00), 45 (15:00, 1.3/month). The other single settings add 0 to 4 trades. Later windows add trades with a lower win rate (J 44-50% vs 60%) but PF stays above 1.4.

**Verdict (per your rule: no profit cut, Lucid rules on).** Seven singles passed the IS filter (window_end 11:00, 11:30, 12:30; history_sessions 8 and 10; hammer_wick_body_mult 3; max_wick_through_pts 20). The IS pick (highest IS 25K-fit total) is **window_end 11:00** (IS 14 trades vs 10, PF 3.04, 25K fit $1354 vs $980; 11:30 has identical IS trades). On J it is a **REJECT**: more trades (18 vs 10) and more 1-micro profit ($492 vs $212) but the 25K-fit total falls ($658 vs $976) and the Pro 25K pass rate falls from 3.4% to 0.0% (50K 8.9% to 4.0%). That is a profit cut at the Lucid size, so by your rule it is not to be implemented. The only IS-eligible row that passes every J test is **history_sessions 10** (J 14 trades vs 10, $478 vs $212 1-micro, $1204 vs $976 25K fit, PF 2.30, 25K pass 7.8% vs 3.4%, 50K 41.7% vs 8.9%, bust 0 everywhere), but it is only 14 trades in J (4 more than baseline): **too few to trust**, and its 50K pass jump rests on a handful of trades, not evidence. It was not the IS pick. Window_end 15:00 also passes the J test but was NOT IS-eligible (IS total $192 < baseline $288, IS 25K fit $172 < $980), so it may not be picked, and it was seen on J.

Honest caveats: 13 candidates tested (11 singles + 2 combos) plus the trim-off baseline, so some J "passes" are expected by chance; earlier sessions have already looked at J. Baseline has only 10 trades per window and every IS row has under 30 trades (too few to trust); J rows with 30+ trades are only window_end 12:30, 14:00 and 15:00 (31, 41, 45), and 12:30 and 14:00 fail the J test. Pass/bust percentages are lumpy at this trade count (one trade moves them by several points) and rolling starts near the end of each window cannot finish, which depresses pass %. There is no bust in any row (Lucid-fit sizing and the day stop keep bust at 0%).

**D152 trim, baseline ON vs OFF.** IS: 25K-fit total $980 ON vs $1332 OFF (trim cut IS profit by 26%), Pro 25K IS pass 0.0% vs 7.8%. J: $976 ON vs $712 OFF (trim added 37%), Pro 25K J pass 3.4% vs 0.0%, 50K 8.9% vs 0.0%. Over both windows ON and OFF are about equal ($1956 vs $2044 at 25K). 1-micro rows are identical (trim only matters at 2+ micros).

Combos (built only from IS-eligible settings): `window_end 11:00 + history_sessions 8` and `window_end 11:00 + history_sessions 8 + hammer 3 + wick 20`. Both REJECT on J (25K fit $418 and $371 vs $976, pass 0.0%).

The verdict table lists every row including those that were not IS-eligible (column "IS eligible"); only IS-eligible rows count toward a pick.

## Part 1 raw counts

### all 1266 days: 740 setup days (trend day with a level)

| measure | value |
|---|---|
| hourly plan candles fed (5 sessions + gap candles), mean | 40.0 |
| A4 levels created per day, mean / median | 4.34 / 4 |
| A6 deleted by a later body piercing, mean / median | 2.06 / 2 |
| total created / deleted / of those first pierced by the A7 overnight gap candle | 3211 / 1527 (48%) / 529 (35% of deletions) |
| deletions first made by a regular hourly candle | 998 (65%) |
| surviving levels per day, mean / median | 2.28 / 2 |
| days with zero surviving levels | 0 |
| nearest surviving level ABOVE open: median pt (days having one) | 214 (475 days) |
| nearest surviving level BELOW open: median pt (days having one) | 280 (540 days) |
| nearest surviving level either side: median / Q1 / Q3 | 233 / 96 / 436 |
| chosen level (A8) distance, median | 233 |
| days with a surviving level within 50 pt of the open (either side) | 98 (13%) |
| days with a surviving level within 100 pt of the open (either side) | 189 (26%) |
| days with a surviving level within 150 pt of the open (either side) | 272 (37%) |

### IS: 321 setup days (trend day with a level)

| measure | value |
|---|---|
| hourly plan candles fed (5 sessions + gap candles), mean | 40.0 |
| A4 levels created per day, mean / median | 4.11 / 4 |
| A6 deleted by a later body piercing, mean / median | 1.90 / 2 |
| total created / deleted / of those first pierced by the A7 overnight gap candle | 1318 / 609 (46%) / 165 (27% of deletions) |
| deletions first made by a regular hourly candle | 444 (73%) |
| surviving levels per day, mean / median | 2.21 / 2 |
| days with zero surviving levels | 0 |
| nearest surviving level ABOVE open: median pt (days having one) | 222 (212 days) |
| nearest surviving level BELOW open: median pt (days having one) | 249 (221 days) |
| nearest surviving level either side: median / Q1 / Q3 | 233 / 95 / 417 |
| chosen level (A8) distance, median | 233 |
| days with a surviving level within 50 pt of the open (either side) | 40 (12%) |
| days with a surviving level within 100 pt of the open (either side) | 85 (26%) |
| days with a surviving level within 150 pt of the open (either side) | 119 (37%) |

### J: 419 setup days (trend day with a level)

| measure | value |
|---|---|
| hourly plan candles fed (5 sessions + gap candles), mean | 40.0 |
| A4 levels created per day, mean / median | 4.52 / 5 |
| A6 deleted by a later body piercing, mean / median | 2.19 / 2 |
| total created / deleted / of those first pierced by the A7 overnight gap candle | 1893 / 918 (48%) / 364 (40% of deletions) |
| deletions first made by a regular hourly candle | 554 (60%) |
| surviving levels per day, mean / median | 2.33 / 2 |
| days with zero surviving levels | 0 |
| nearest surviving level ABOVE open: median pt (days having one) | 209 (263 days) |
| nearest surviving level BELOW open: median pt (days having one) | 308 (319 days) |
| nearest surviving level either side: median / Q1 / Q3 | 230 / 101 / 463 |
| chosen level (A8) distance, median | 230 |
| days with a surviving level within 50 pt of the open (either side) | 58 (14%) |
| days with a surviving level within 100 pt of the open (either side) | 104 (25%) |
| days with a surviving level within 150 pt of the open (either side) | 153 (37%) |

### 2-year 2024-11-01+: 296 setup days (trend day with a level)

| measure | value |
|---|---|
| hourly plan candles fed (5 sessions + gap candles), mean | 40.0 |
| A4 levels created per day, mean / median | 4.52 / 5 |
| A6 deleted by a later body piercing, mean / median | 2.22 / 2 |
| total created / deleted / of those first pierced by the A7 overnight gap candle | 1339 / 656 (49%) / 270 (41% of deletions) |
| deletions first made by a regular hourly candle | 386 (59%) |
| surviving levels per day, mean / median | 2.31 / 2 |
| days with zero surviving levels | 0 |
| nearest surviving level ABOVE open: median pt (days having one) | 238 (181 days) |
| nearest surviving level BELOW open: median pt (days having one) | 333 (232 days) |
| nearest surviving level either side: median / Q1 / Q3 | 262 / 118 / 521 |
| chosen level (A8) distance, median | 262 |
| days with a surviving level within 50 pt of the open (either side) | 39 (13%) |
| days with a surviving level within 100 pt of the open (either side) | 67 (23%) |
| days with a surviving level within 150 pt of the open (either side) | 96 (32%) |

## Part 2 IS: 2021-10-01..2023-12-31 (27 months)

Totals: 1 micro = single 2R bracket after $2.00/RT + $2/pt; fit25/fit50 = static Lucid-fit size per trade (full room), D152 trim when >= 2 contracts.

| row | trades | /month | win % | PF | avg $/trade | total $ 1 micro | fit 25K $ | fit 50K $ | max DD $ (1 micro) |
|---|---|---|---|---|---|---|---|---|---|
| baseline_trimON | 10 (<30: too few) | 0.37 | 70.0 | 2.36 | 28.80 | 288 | 980 | 2746 | 124 |
| baseline_trimOFF | 10 (<30: too few) | 0.37 | 70.0 | 2.36 | 28.80 | 288 | 1332 | 3280 | 124 |
| window_end 11:00 | 14 (<30: too few) | 0.52 | 71.4 | 3.04 | 34.43 | 482 | 1354 | 3486 | 148 |
| window_end 11:30 | 14 (<30: too few) | 0.52 | 71.4 | 3.04 | 34.43 | 482 | 1354 | 3486 | 148 |
| window_end 12:30 | 16 (<30: too few) | 0.59 | 62.5 | 2.26 | 25.03 | 400 | 1093 | 2802 | 173 |
| window_end 14:00 | 21 (<30: too few) | 0.78 | 52.4 | 1.75 | 15.43 | 324 | 721 | 1926 | 218 |
| window_end 15:00 | 25 (<30: too few) | 0.93 | 44.0 | 1.34 | 7.66 | 192 | 172 | 563 | 319 |
| pivot_lookback 2 | 12 (<30: too few) | 0.44 | 58.3 | 2.11 | 22.83 | 274 | 763 | 2276 | 124 |
| history_sessions 8 | 14 (<30: too few) | 0.52 | 64.3 | 2.28 | 26.43 | 370 | 1142 | 2992 | 112 |
| history_sessions 10 | 17 (<30: too few) | 0.63 | 58.8 | 2.17 | 24.59 | 418 | 1114 | 2916 | 152 |
| trend_swing_lookback 3 | 13 (<30: too few) | 0.48 | 53.8 | 1.98 | 20.50 | 266 | 646 | 2143 | 179 |
| hammer_wick_body_mult 3 | 11 (<30: too few) | 0.41 | 72.7 | 2.58 | 30.45 | 335 | 1134 | 3117 | 112 |
| max_wick_through_pts 20 | 12 (<30: too few) | 0.44 | 66.7 | 2.49 | 33.62 | 404 | 1036 | 3163 | 112 |
| COMBO window_end 11:00 + history_sessions 8 | 18 (<30: too few) | 0.67 | 66.7 | 2.58 | 27.53 | 496 | 1423 | 3626 | 120 |
| COMBO window_end 11:00 + history_sessions 8 + hammer_wick_body_mult 3 + max_wick_through_pts 20 | 23 (<30: too few) | 0.85 | 60.9 | 1.85 | 20.57 | 473 | 1391 | 3808 | 238 |

## Part 2 J: 2024-01-01..2026-10-30 (34 months)

Totals: 1 micro = single 2R bracket after $2.00/RT + $2/pt; fit25/fit50 = static Lucid-fit size per trade (full room), D152 trim when >= 2 contracts.

| row | trades | /month | win % | PF | avg $/trade | total $ 1 micro | fit 25K $ | fit 50K $ | max DD $ (1 micro) |
|---|---|---|---|---|---|---|---|---|---|
| baseline_trimON | 10 (<30: too few) | 0.29 | 60.0 | 1.62 | 21.25 | 212 | 976 | 2662 | 157 |
| baseline_trimOFF | 10 (<30: too few) | 0.29 | 60.0 | 1.62 | 21.25 | 212 | 712 | 2084 | 157 |
| window_end 11:00 | 18 (<30: too few) | 0.53 | 50.0 | 2.11 | 27.36 | 492 | 658 | 2590 | 189 |
| window_end 11:30 | 26 (<30: too few) | 0.76 | 46.2 | 1.65 | 16.08 | 418 | 596 | 2576 | 250 |
| window_end 12:30 | 31 | 0.91 | 48.4 | 1.94 | 21.66 | 672 | 1146 | 3701 | 321 |
| window_end 14:00 | 41 | 1.21 | 43.9 | 1.64 | 14.28 | 586 | 827 | 3075 | 301 |
| window_end 15:00 | 45 | 1.32 | 44.4 | 1.44 | 10.64 | 479 | 1018 | 3470 | 382 |
| pivot_lookback 2 | 10 (<30: too few) | 0.29 | 50.0 | 2.35 | 41.25 | 412 | 808 | 2133 | 194 |
| history_sessions 8 | 13 (<30: too few) | 0.38 | 53.8 | 1.75 | 21.23 | 276 | 1002 | 2724 | 176 |
| history_sessions 10 | 14 (<30: too few) | 0.41 | 57.1 | 2.30 | 34.14 | 478 | 1204 | 3534 | 176 |
| trend_swing_lookback 3 | 11 (<30: too few) | 0.32 | 54.5 | 1.35 | 13.50 | 148 | 931 | 2336 | 242 |
| hammer_wick_body_mult 3 | 11 (<30: too few) | 0.32 | 54.5 | 1.34 | 12.86 | 142 | 834 | 2306 | 157 |
| max_wick_through_pts 20 | 11 (<30: too few) | 0.32 | 54.5 | 1.23 | 9.59 | 106 | 869 | 2340 | 157 |
| COMBO window_end 11:00 + history_sessions 8 | 23 (<30: too few) | 0.68 | 43.5 | 1.91 | 21.13 | 486 | 418 | 1980 | 250 |
| COMBO window_end 11:00 + history_sessions 8 + hammer_wick_body_mult 3 + max_wick_through_pts 20 | 28 (<30: too few) | 0.82 | 42.9 | 1.59 | 16.89 | 473 | 371 | 2328 | 334 |

## Eval (Lucid Pro EOD, all rules on, rolling start every trading day inside the window; PASS% / BUST%)

| row | window | Pro 25K | Pro 50K | Pro 100K | Pro 150K |
|---|---|---|---|---|---|
| baseline_trimON | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| baseline_trimON | J | 3.4 / 0.0 | 8.9 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| baseline_trimOFF | IS | 7.8 / 0.0 | 7.8 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| baseline_trimOFF | J | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 11:00 | IS | 3.6 / 0.0 | 7.8 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 11:00 | J | 0.0 / 0.0 | 4.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 11:30 | IS | 3.6 / 0.0 | 7.8 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 11:30 | J | 0.0 / 0.0 | 3.3 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 12:30 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 12:30 | J | 1.6 / 0.0 | 6.5 / 0.0 | 0.0 / 0.0 | 1.6 / 0.0 |
| window_end 14:00 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 14:00 | J | 1.6 / 0.0 | 5.0 / 0.0 | 3.3 / 0.0 | 3.3 / 0.0 |
| window_end 15:00 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| window_end 15:00 | J | 4.1 / 0.0 | 16.0 / 0.0 | 7.4 / 0.0 | 9.1 / 0.0 |
| pivot_lookback 2 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| pivot_lookback 2 | J | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| history_sessions 8 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| history_sessions 8 | J | 0.0 / 0.0 | 0.1 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| history_sessions 10 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| history_sessions 10 | J | 7.8 / 0.0 | 41.7 / 0.0 | 5.8 / 0.0 | 3.5 / 0.0 |
| trend_swing_lookback 3 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| trend_swing_lookback 3 | J | 3.4 / 0.0 | 34.3 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| hammer_wick_body_mult 3 | IS | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| hammer_wick_body_mult 3 | J | 3.4 / 0.0 | 8.9 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| max_wick_through_pts 20 | IS | 0.0 / 0.0 | 7.8 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| max_wick_through_pts 20 | J | 3.4 / 0.0 | 8.9 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| COMBO window_end 11:00 + history_sessions 8 | IS | 3.6 / 0.0 | 7.8 / 0.0 | 3.6 / 0.0 | 3.6 / 0.0 |
| COMBO window_end 11:00 + history_sessions 8 | J | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| COMBO window_end 11:00 + history_sessions 8 + hammer_wick_body_mult 3 + max_wick_through_pts 20 | IS | 3.6 / 0.0 | 7.8 / 0.0 | 7.8 / 0.0 | 7.8 / 0.0 |
| COMBO window_end 11:00 + history_sessions 8 + hammer_wick_body_mult 3 + max_wick_through_pts 20 | J | 0.0 / 0.0 | 2.3 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |

## Part 3 verdict

Candidates tested: 11 singles + 2 combos = 13 (+ trim-off baseline). IS-eligible singles: ['window_end 11:00', 'window_end 11:30', 'history_sessions 8', 'hammer_wick_body_mult 3', 'history_sessions 10', 'window_end 12:30', 'max_wick_through_pts 20'].

| row | IS eligible | IS 25K fit $ | J trades vs base | J 1-micro $ vs base | J 25K fit $ vs base | J PF | 25K pass/bust vs base | 50K pass/bust vs base | verdict |
|---|---|---|---|---|---|---|---|---|---|
| window_end 11:00 | yes | 1354 | 18 vs 10 | 492 vs 212 | 658 vs 976 | 2.11 | 0.0/0.0 vs 3.4/0.0 | 4.0/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| window_end 11:30 | yes | 1354 | 26 vs 10 | 418 vs 212 | 596 vs 976 | 1.65 | 0.0/0.0 vs 3.4/0.0 | 3.3/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| window_end 12:30 | yes | 1093 | 31 vs 10 | 672 vs 212 | 1146 vs 976 | 1.94 | 1.6/0.0 vs 3.4/0.0 | 6.5/0.0 vs 8.9/0.0 | REJECT |
| window_end 14:00 | no | 721 | 41 vs 10 | 586 vs 212 | 827 vs 976 | 1.64 | 1.6/0.0 vs 3.4/0.0 | 5.0/0.0 vs 8.9/0.0 | REJECT |
| window_end 15:00 | no | 172 | 45 vs 10 | 479 vs 212 | 1018 vs 976 | 1.44 | 4.1/0.0 vs 3.4/0.0 | 16.0/0.0 vs 8.9/0.0 | ACCEPT |
| pivot_lookback 2 | no | 763 | 10 vs 10 | 412 vs 212 | 808 vs 976 | 2.35 | 0.0/0.0 vs 3.4/0.0 | 0.0/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| history_sessions 8 | yes | 1142 | 13 vs 10 | 276 vs 212 | 1002 vs 976 | 1.75 | 0.0/0.0 vs 3.4/0.0 | 0.1/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| history_sessions 10 | yes | 1114 | 14 vs 10 | 478 vs 212 | 1204 vs 976 | 2.30 | 7.8/0.0 vs 3.4/0.0 | 41.7/0.0 vs 8.9/0.0 | ACCEPT (J<30 trades: too few to trust) |
| trend_swing_lookback 3 | no | 646 | 11 vs 10 | 148 vs 212 | 931 vs 976 | 1.35 | 3.4/0.0 vs 3.4/0.0 | 34.3/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| hammer_wick_body_mult 3 | yes | 1134 | 11 vs 10 | 142 vs 212 | 834 vs 976 | 1.34 | 3.4/0.0 vs 3.4/0.0 | 8.9/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| max_wick_through_pts 20 | yes | 1036 | 11 vs 10 | 106 vs 212 | 869 vs 976 | 1.23 | 3.4/0.0 vs 3.4/0.0 | 8.9/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| COMBO window_end 11:00 + history_sessions 8 | yes | 1423 | 23 vs 10 | 486 vs 212 | 418 vs 976 | 1.91 | 0.0/0.0 vs 3.4/0.0 | 0.0/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
| COMBO window_end 11:00 + history_sessions 8 + hammer_wick_body_mult 3 + max_wick_through_pts 20 | yes | 1391 | 28 vs 10 | 473 vs 212 | 371 vs 976 | 1.59 | 0.0/0.0 vs 3.4/0.0 | 2.3/0.0 vs 8.9/0.0 | REJECT (J<30 trades: too few to trust) |
