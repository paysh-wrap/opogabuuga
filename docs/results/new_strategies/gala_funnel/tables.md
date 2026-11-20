
## 2-year (2024-11-01..2026-10-30): 495 days

### Day funnel (default config)

| outcome | days | % of days |
|---|---|---|
| GALA_NO_BARS | 0 | 0.0% |
| GALA_NO_OPEN | 0 | 0.0% |
| GALA_NO_TREND | 189 | 38.2% |
| GALA_NO_LEVEL | 10 | 2.0% |
| GALA_NEWS_FIRST_HOUR | 0 | 0.0% |
| SETUP | 296 | 59.8% |

Trend days (LONG/SHORT): 306.

| setup | LONG days | SHORT days | total |
|---|---|---|---|
| BREAK_RETEST | 52 | 43 | 95 |
| BOUNCE | 119 | 0 | 119 |
| REJECTION | 0 | 82 | 82 |
| all | 171 | 125 | 296 |

Setup days with >=1 trade: 6 (6 trades); setup days with no trade: 290.

### Blocking stage, BREAK_RETEST: 95 setup days

Each day gets the DEEPEST stage any candidate reached that day (valid entry outside the window is the deepest). TRADE = a trade happened. Sums to the setup days.

| stage | days | % of these days |
|---|---|---|
| TRADE | 4 | 4.2% |
| a_never_broke | 61 | 64.2% |
| b_break_cancelled | 6 | 6.3% |
| c_no_retest_touch_in_time | 11 | 11.6% |
| d_wick_through_too_big | 1 | 1.1% |
| g_valid_outside_window | 12 | 12.6% |

### Blocking stage, BOUNCE+REJECTION: 201 setup days

Each day gets the DEEPEST stage any candidate reached that day (valid entry outside the window is the deepest). TRADE = a trade happened. Sums to the setup days.

| stage | days | % of these days |
|---|---|---|
| TRADE | 2 | 1.0% |
| a_level_never_touched | 154 | 76.6% |
| b_touched_no_bounce_run | 29 | 14.4% |
| c_wick_through_too_big | 4 | 2.0% |
| e_hammer | 3 | 1.5% |
| f_valid_outside_window | 9 | 4.5% |

### Setup days where a valid entry candle exists at some time of day (first one per day): 27 of 296

| entry candle close | days |
|---|---|
| 09:30-10:00 | 3 |
| 10:00-10:30 | 2 |
| 10:30-11:00 | 8 |
| 11:00-11:30 | 3 |
| 12:00-12:30 | 1 |
| 12:30-13:00 | 2 |
| 13:00-13:30 | 3 |
| 14:00-14:30 | 2 |
| 14:30-15:00 | 1 |
| 15:00-15:30 | 1 |
| 16:00-16:30 | 1 |

First valid entry closes at/before 10:35: 6 days; after 10:35: 21 days (after 12:00: 11).

### Distance 09:30 open to chosen level (points), and whether price reached it

Reached = some 1-minute bar's [low, high] contains the level (bars closing 09:31..10:35, or the whole day to 16:00).

| setup | days | median | Q1 | Q3 | min | max | reached by 10:35 | reached by 16:00 |
|---|---|---|---|---|---|---|---|---|
| BREAK_RETEST | 95 | 133.8 | 59.9 | 324.6 | 1.0 | 1051.5 | 34 (36%) | 45 (47%) |
| BOUNCE | 119 | 374.0 | 190.1 | 616.4 | 4.8 | 1803.5 | 22 (18%) | 25 (21%) |
| REJECTION | 82 | 323.6 | 119.9 | 632.3 | 6.0 | 2042.2 | 17 (21%) | 23 (28%) |
| all | 296 | 262.1 | 118.7 | 519.4 | 1.0 | 2042.2 | 73 (25%) | 93 (31%) |

### One-at-a-time relaxation (everything else default). Counts only.

Full engine rules still apply (E1 2 attempts, E2 max 3/day, E3 stop after a win), so total entries can be above days.

| setting | days with >=1 entry | total entries | note |
|---|---|---|---|
| baseline (defaults) | 6 | 6 |  |
| window_end 11:30 | 16 | 17 |  |
| window_end 12:30 | 17 | 19 |  |
| window_end 15:00 | 25 | 27 |  |
| max_wick_through_pts 20 | 7 | 7 |  |
| max_wick_through_pts 40 | 8 | 8 |  |
| max_wick_through_pts 1000 (off) | 8 | 8 |  |
| hammer_wick_body_mult 3 | 7 | 7 |  |
| hammer_wick_body_mult 1000 (off) | 9 | 9 |  |
| max_retest_bars 12 | 6 | 6 |  |
| max_retest_bars 24 | 6 | 6 |  |
| max_retest_bars 78 (all day) | 6 | 6 | outside validated bound (max_retest_bars le=24) |
| pivot_lookback 2 | 7 | 7 |  |
| pivot_lookback 4 | 3 | 3 |  |
| trend_swing_lookback 1 | 6 | 6 |  |
| trend_swing_lookback 3 | 8 | 8 |  |
| history_sessions 3 | 3 | 3 |  |
| history_sessions 8 | 7 | 7 |  |
| use_open_level on | 6 | 6 |  |
| stop_buffer_ticks 0 | 6 | 6 |  |
| stop_buffer_ticks 4 | 6 | 6 |  |
| ALL LOOSE (window 15:00, wick off, hammer off, retest 78) | 36 | 46 | outside validated bound (max_retest_bars le=24) |

## 5-year (all days): 1266 days

### Day funnel (default config)

| outcome | days | % of days |
|---|---|---|
| GALA_NO_BARS | 0 | 0.0% |
| GALA_NO_OPEN | 0 | 0.0% |
| GALA_NO_TREND | 491 | 38.8% |
| GALA_NO_LEVEL | 35 | 2.8% |
| GALA_NEWS_FIRST_HOUR | 0 | 0.0% |
| SETUP | 740 | 58.5% |

Trend days (LONG/SHORT): 775.

| setup | LONG days | SHORT days | total |
|---|---|---|---|
| BREAK_RETEST | 141 | 110 | 251 |
| BOUNCE | 273 | 0 | 273 |
| REJECTION | 0 | 216 | 216 |
| all | 414 | 326 | 740 |

Setup days with >=1 trade: 19 (20 trades); setup days with no trade: 721.

### Blocking stage, BREAK_RETEST: 251 setup days

Each day gets the DEEPEST stage any candidate reached that day (valid entry outside the window is the deepest). TRADE = a trade happened. Sums to the setup days.

| stage | days | % of these days |
|---|---|---|
| TRADE | 14 | 5.6% |
| a_never_broke | 168 | 66.9% |
| b_break_cancelled | 11 | 4.4% |
| c_no_retest_touch_in_time | 21 | 8.4% |
| d_wick_through_too_big | 4 | 1.6% |
| f_hammer | 4 | 1.6% |
| g_valid_outside_window | 29 | 11.6% |

### Blocking stage, BOUNCE+REJECTION: 489 setup days

Each day gets the DEEPEST stage any candidate reached that day (valid entry outside the window is the deepest). TRADE = a trade happened. Sums to the setup days.

| stage | days | % of these days |
|---|---|---|
| TRADE | 5 | 1.0% |
| a_level_never_touched | 371 | 75.9% |
| b_touched_no_bounce_run | 78 | 16.0% |
| c_wick_through_too_big | 7 | 1.4% |
| e_hammer | 6 | 1.2% |
| f_valid_outside_window | 22 | 4.5% |

### Setup days where a valid entry candle exists at some time of day (first one per day): 70 of 740

| entry candle close | days |
|---|---|
| 09:30-10:00 | 4 |
| 10:00-10:30 | 12 |
| 10:30-11:00 | 13 |
| 11:00-11:30 | 8 |
| 11:30-12:00 | 2 |
| 12:00-12:30 | 3 |
| 12:30-13:00 | 6 |
| 13:00-13:30 | 4 |
| 13:30-14:00 | 4 |
| 14:00-14:30 | 4 |
| 14:30-15:00 | 2 |
| 15:00-15:30 | 3 |
| 15:30-16:00 | 1 |
| 16:00-16:30 | 4 |

First valid entry closes at/before 10:35: 19 days; after 10:35: 51 days (after 12:00: 30).

### Distance 09:30 open to chosen level (points), and whether price reached it

Reached = some 1-minute bar's [low, high] contains the level (bars closing 09:31..10:35, or the whole day to 16:00).

| setup | days | median | Q1 | Q3 | min | max | reached by 10:35 | reached by 16:00 |
|---|---|---|---|---|---|---|---|---|
| BREAK_RETEST | 251 | 131.2 | 59.5 | 279.0 | 1.0 | 1051.5 | 72 (29%) | 106 (42%) |
| BOUNCE | 273 | 321.2 | 172.5 | 499.5 | 4.8 | 1803.5 | 38 (14%) | 57 (21%) |
| REJECTION | 216 | 244.8 | 99.8 | 436.8 | 6.0 | 2042.2 | 38 (18%) | 62 (29%) |
| all | 740 | 232.9 | 97.0 | 435.2 | 1.0 | 2042.2 | 148 (20%) | 225 (30%) |

### One-at-a-time relaxation (everything else default). Counts only.

Full engine rules still apply (E1 2 attempts, E2 max 3/day, E3 stop after a win), so total entries can be above days.

| setting | days with >=1 entry | total entries | note |
|---|---|---|---|
| baseline (defaults) | 19 | 20 |  |
| window_end 11:30 | 37 | 40 |  |
| window_end 12:30 | 43 | 47 |  |
| window_end 15:00 | 62 | 70 |  |
| max_wick_through_pts 20 | 21 | 23 |  |
| max_wick_through_pts 40 | 22 | 24 |  |
| max_wick_through_pts 1000 (off) | 22 | 24 |  |
| hammer_wick_body_mult 3 | 21 | 22 |  |
| hammer_wick_body_mult 1000 (off) | 26 | 28 |  |
| max_retest_bars 12 | 19 | 20 |  |
| max_retest_bars 24 | 19 | 20 |  |
| max_retest_bars 78 (all day) | 19 | 20 | outside validated bound (max_retest_bars le=24) |
| pivot_lookback 2 | 21 | 22 |  |
| pivot_lookback 4 | 13 | 14 |  |
| trend_swing_lookback 1 | 18 | 19 |  |
| trend_swing_lookback 3 | 23 | 24 |  |
| history_sessions 3 | 13 | 14 |  |
| history_sessions 8 | 25 | 27 |  |
| use_open_level on | 19 | 20 |  |
| stop_buffer_ticks 0 | 19 | 20 |  |
| stop_buffer_ticks 4 | 19 | 20 |  |
| ALL LOOSE (window 15:00, wick off, hammer off, retest 78) | 87 | 109 | outside validated bound (max_retest_bars le=24) |
