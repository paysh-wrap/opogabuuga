# GALA PRICE ACTION funnel: what blocks the setups (counting study, no tuning)

Script `gala_funnel.py` (engine `gala_pa.replay_day` called unchanged, default `GalaPaCfg()`, 8-10 prior days as history), per-day classification `days.csv`, all tables below also in `tables.md`. Data: 5-year MNQ 1-minute RTH bars, 1266 days 2021-10-01..2026-10-30; two windows: 2-year 2024-11-01..2026-10-30 (495 days) and all 1266 days. COUNTS ONLY: no win rate, no P&L, no recommendation. Any loosening must be chosen on 2021-10..2023-12 and judged on 2024-01..2026-10 in a separate study.

## What blocks GALA (plain English)
1. Reproduction OK: 2-year window = 6 trades, 189 days with no hourly trend (GALA_NO_TREND), 306 days with a trend. Note: the published "306 days have a setup" is really "306 trend days"; 10 of them have no level (GALA_NO_LEVEL), so 296 days have a real level + setup type.
2. The biggest blocker is distance, not a strict candle rule. The chosen level is a median 262 pt away from the 09:30 open (quartiles 119-519 pt; 2-year, 296 setup days). Price touches that level by 10:35 on only 73 of 296 days (25%), and on only 93 (31%) even by 16:00.
3. Break-and-retest (95 days): 61 days (64%) never close a 5-minute candle through the level all day. Bounce/rejection (201 days): 154 days (77%) never touch the level in 5-minute candles all day.
4. Only 27 of 296 setup days (9%) ever produce a valid entry candle at any time of day. Only 6 of those are inside 09:35-10:35 (= the 6 trades). 21 are after 10:35 (11 after 12:00): the OPEN setting `window_end` is the one that blocks the most valid entries.
5. The remaining candle-rule blocks are small: wick-through-too-big 5 days, hammer 3 days, touched-but-no-2-candle-bounce-run 29 days (the 2-candle count is a transcript rule), break cancelled by a close back through 6 days, no retest touch within 6 bars 11 days.
6. One-at-a-time relaxation (2-year, days with an entry / entries): window_end 15:00 6 -> 25 days (27 entries), 11:30 -> 16 days; hammer off 9; wick off 8; pivot_lookback 2 gives 7 (4 gives 3); trend_swing_lookback 3 gives 8; history_sessions 8 gives 7 (3 gives 3); max_retest_bars, stop_buffer_ticks and use_open_level change nothing. All four loose together (window 15:00, wick off, hammer off, retest 78): 36 days / 46 entries in 2 years (87 days / 109 entries in 5 years) out of 495 (1266) days. So even with the open settings loose, the level is mostly never reached.
7. Engine observations (not strict settings): see "Engine notes" at the bottom (`use_open_level` has no effect on the day-open setup choice).

## Settings legend
Open ([GAP], not from the video): pivot_lookback 3, trend_swing_lookback 2, history_sessions 5, use_open_level off, window 09:35-10:35, max_wick_through_pts 10, hammer_wick_body_mult 2, max_retest_bars 6, stop_buffer_ticks 1.
Transcript rule (from the video): skip_first_minutes 5, bounce_candles 2, target_r 2, max_hold 60, max_attempts_per_setup 2, max_trades_per_day 3, stop_after_win on. Fixed engine rules: perfect entry C2/C3, hammer C4, break must close beyond then retest, close back through cancels the break (C5).

Which setting/rule sits behind each stage (labels only):
| stage | rule behind it | open or transcript |
|---|---|---|
| BR a never_broke; B/R a level_never_touched | which level A8 picks (pivot_lookback, history_sessions, trend, A4 level definition) and where price goes; no setting can make price reach it | pivot_lookback / history_sessions open; A4/A8 transcript |
| BR b break_cancelled | C5 "a close back through cancels the break" | fixed rule |
| BR c no_retest_touch_in_time | max_retest_bars 6 (but see: relaxing it changed nothing) | open |
| BR d / B-R c wick_through_too_big | max_wick_through_pts 10 | open |
| BR e / B-R d body/close wrong side | C2/C3 | fixed rule |
| BR f / B-R e hammer | hammer_wick_body_mult 2 (C4) | open |
| BR g / B-R f valid_outside_window | window_end 10:35 | open |
| B-R b touched_no_bounce_run | bounce_candles 2 (a run of N candles with body on the right side and wick through) | transcript |
| first 5-min candle never traded | skip_first_minutes 5 | transcript |

## Definitions (exact)
- Day funnel: result of `replay_day` for the day (`skip` code, or a setup). GALA_NO_OPEN = first 1-min bar does not close 09:31 (0 days here).
- Stage table: for each setup day, the engine's `find_entry` is mirrored step by step on the day's 5-minute candles after the skip (assert: the mirror finds the same first entry candle as `find_entry` on every setup day). The day gets the DEEPEST stage any candidate reached during the whole day, deepest last: BREAK_RETEST a never_broke < b break_cancelled (every break ended by a close back through, none expired) < c break(s) expired with no retest touch / day ended < d touching candle with wick through > max_wick_through_pts < e touching candle whose body/close is on the wrong side (only checked if the wick test passed) < f hammer (passed wick and body tests) < g a valid entry exists but its candle closes after window_end. Bounce/rejection: a never touched < b touched but no run of `bounce_candles` holding candles < c run reached, wick through too big < d run reached, body/close fail < e hammer < f valid but after window_end. A valid entry inside the window shows as TRADE (all such days did trade; 0 mirror mismatches).
- "touch" for a level = candle low <= level (LONG) / high >= level (SHORT) for bounce/rejection; for break-and-retest it is the retest candle after the break. "Reached" in the distance table = a 1-minute bar's [low, high] contains the level.
- Entry-time distribution = close time of the FIRST valid entry candle of the day (any time of day, 5-minute chart), independent of the window.
- Relaxation rows: full engine rules still on (E1/E2/E3), so entries can exceed days. History fed = 10 prior days for all rows (the baseline equals the published 6 trades). Rows marked "outside validated bound" use `model_copy`, which skips the validators (max_retest_bars is limited to 24 in the config).
- Windows: all rows computed on all 1266 days; the 2-year rows count only days >= 2024-11-01 (history comes from before, as in backtest_new.py).

## Reproduction check
2-year: 6 trades (4 BREAK_RETEST, 1 BOUNCE, 1 REJECTION), GALA_NO_TREND 189, trend days 306 (= 10 NO_LEVEL + 296 SETUP). Matches `RESULTS_gala_conti.md` (the published "306 setup days" = trend days).

## Tables

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

## Engine notes (possible bug vs strict setting)
- `use_open_level=True` has no effect on the day-open setup choice (relaxation rows identical: 6 days 2-year, 19 days 5-year). Cause: `choose_setup` (gala_pa.py lines 282-283) takes `above` = price strictly greater than the reference price and `below` = strictly lower, and the A5 open level is appended at exactly `first.o` (line 399) while the setup is chosen from `first.o` (line 404), so that level is never above or below. It could only matter in the re-pick after a closed trade. This looks like an unintended dead switch, not a strict setting.
- `window_start` (09:35) never binds: `skip_first_minutes` 5 already drops the 09:30-09:35 candle, and every later 5-minute candle closes after 09:35.
- `max_retest_bars` changes nothing because the first valid entry must also close by 10:35 (about 12 candles).
- find_entry BREAK_RETEST (line 322 onward): a candle closing back through the level cancels the break even when it is itself the retest (touch with the close on the wrong side). That is the written C5 rule, shown as stage b, not a bug.
