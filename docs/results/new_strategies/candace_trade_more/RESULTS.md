# CANDACE ICT SCALP: why so few trades, and what adds trades (study only, nothing implemented)

## Plain English

**Why so few trades.** The strategy is not short of setups; it is short of setups that survive. In the 09:30-10:00 window the engine finds about 7.8 "sweeps" per day (9,814 in 1,266 days; every single day has at least one). Only 100 of them (1%) become a trade, about 1 trade every 12 days (53 in IS, 47 in J). Where they die (cumulative funnel, all 5 years):

| stage | episodes reaching it |
|---|---|
| sweeps of any pool | 9,814 |
| with an FVG on the run into the sweep | 5,984 |
| a candle body closed through that FVG | 1,164 |
| ...and displaced (body >= 1.5x the 10-bar average) = valid IFVG | 572 |
| ...and price retraced into it in time | 248 |
| ...and on the right premium/discount side | 145 |
| ...and stop <= 40 pt = TRADE | 100 |

1. The biggest loss, about 8,300 of the 9,714 non-trades, is that a pending setup is **overwritten by the next sweep** (the engine takes any new pool sweep, even a 2-bar swing, and drops the setup in progress; engine note 1 below). It is a design choice, not a transcript rule.
2. Next: no candle body closes through the FVG (C2, a transcript rule; 4,820 episodes ended there) and the displacement test (C5, size is a [GAP]; 592 ended there).
3. Retrace in time (C3, 10 bars, [GAP]): 324 ended. Premium/discount (A2, threshold [GAP]): 103. Stop wider than 40 pt (D2, transcript, skip): 45. D3 (1:2) never blocks anything.
4. **Sizing is a second wall.** 93 of the 100 trades are grade C (7 are B, none A+: it needs 4 confluences and the best seen is 3). Grade C gets 1/4 of the Lucid-fit size. On Pro 25K the fit is 3 micros at a 20 pt stop, so **63 of 100 trades size to 0 micros** (27 of 32 in the earlier 2-year run). 50K, 100K and 150K size every trade to at least 1. The Lucid fit itself never gives 0.
5. Time: after 10:00 the same engine finds as many setups per half hour as inside the window (signals per half hour: 100, 134, 128, 148 over 09:31-11:30), and 1,101 episodes that started in the last 10 minutes were cut off by the 10:00 window end. Only the 09:30-10:00 part of the NY window exists in the data (no pre-market, no London, no Asia range); nothing was faked.
6. Big caveat: the baseline is **negative in the in-sample period** (IS 2021-10..2023-12: 53 trades, PF 0.69, -$456 at 1 micro) and positive in J (47 trades, PF 2.05, +$1,211). The earlier "32 trades, PF 2.47" was the good part of the history. Targets are far (average 89 pt, because the target moves to the nearest pool beyond 2R): only 14 of 100 trades hit the target, 56 stop out, 30 time out after 15 minutes.

**What adds trades.** Later window ends (10:30 / 11:00 / 11:30) roughly 2.2x / 3.3x / 4.7x the trades; displacement 1.25 / 1.0 add 36% / 89%; displacement_bars 5 and swing_lookback 3 add 28% / 49%; ifvg_max_bars 20 and premium_pct 0.60 add a few. fvg_lookback 20, eq_tol 4, range_bars 120, stop buffer 1, swing_lookback 1 and displacement_bars 20 do not add IS trades (range_bars has no effect at all: only today's bars, at most 30 in the window, exist). C4 (aggressive entry) adds about 17x the trades (891 IS, 936 J) but loses money in both periods.

**Verdict under your rule ("do not cut profit, follow Lucid rules"): nothing is accepted.** None of the 22 candidates passed the IS filter (more trades, IS PF >= 1.10, IS profit not below baseline at 1 micro and 25K fit). The baseline itself has IS PF 0.69, so almost any change that adds trades adds more losing IS trades (IS PF 0.51-0.94). With no IS-eligible rows there is nothing to combine (0 combos built) and no IS pick. Nothing should be implemented on this evidence. Observations that are NOT a pick (they failed IS; J is shown in the tables for every row): window 10:30 had J 116 trades vs 47, J 1-micro +$1,280 vs +$1,211 and J 25K fit +$220 vs -$287, but IS says -$760 vs -$456 and PF 0.75. The grade floor makes the 25K plan trade every signal (J 25K fit +$1,192 vs -$287, J 25K eval 30.4% pass / 0% bust vs 0 / 0) but in IS it is -$494 vs -$226. Both look good only in the 2024-26 data, which earlier sessions already saw. "Too few to trust": every row except the window rows and C4 has under 100 J trades and the baseline has 47 (the eval pass/bust is 0 / 0 almost everywhere because 47 trades cannot reach the profit target).

Multiple-testing caveat: 22 candidates (+0 combos) on one 5-year sample; 2024-26 was seen by earlier sessions; the IS filter is a one-sided screen, not proof.

## Definitions used (offline simulations, app code untouched)
- Mirror: `run_day` in `ctm_lib.py` copies `candace_ict.replay_day` step by step and is asserted equal: **0 mismatching days of 1,266 on the baseline and on every engine-setting row** (the engine is called unchanged for those rows; all values passed the CandaceIctCfg validators, so no model_copy was needed).
- IS = 2021-10-01..2023-12-31 (561 days), J = 2024-01-01..2026-10-30 (705 days). Eval starts: every day inside each period; a run sees only its own period. History = 3 prior days (as the earlier harness; reproduces its 32 trades in 2024-11..2026-10).
- D4: half off (floor(c/2) micros; with 1 micro no partial) at the nearest minor 2-bar swing high/low or 1-minute FVG edge (long: FVG low above entry; short: FVG high below) strictly between entry and target, known at the entry bar; rest to the final target; stop unchanged. The "1 micro" figure for D4 is a per-contract 50/50 blend of the two legs.
- D5: once a bar's favourable extreme reaches 25% of entry-to-target, the stop moves to entry from the next bar. Stop-first bar ordering as the engine. A break-even exit still pays the $2 cost. Sizing risk uses the original stop.
- C4: for a sweep with an FVG on the run, entry at the first touch of the FVG near edge within ifvg_max_bars (fill at the edge, or the bar open if it opened inside), no body close or displacement needed, no DISPLACEMENT confluence (so grades are lower), same A2 / D2 / D3 / stop; the entry bar only checks the stop.
- Sizing variants: GFLOOR = grade_contracts result raised to at least 1 when the full fit >= 1 (never above the fit); GLOW = grade_b_min 2 / grade_a_min 3 (re-graded from confluence counts, signals identical). For sizing rows "more trades" means more trades executed at the 25K fit.
- Eval sim = the existing harness rules (EOD trailing MLL with lock, effective DLL, 40% consistency + day stop, kill distance, 1 position, size shrinks with MLL room), days without trades skipped (provably no state change). Each plan's own yaml fit values (all 0.25 / 0.9 / 3).

## Engine behaviour that looks like a bug or a trap (not changed)
1. `backend/app/engine/candace_ict.py` lines 237-243: the sweep loop runs on every bar and any new sweep replaces the pending `sweep, ifvg` state, so 8,289 of 9,814 episodes are discarded by a later sweep (a 1-minute swing or session high/low counts). Probably the main trade killer, and not from the transcript.
2. Line 269: the A2 dealing range is `bars[i-range_bars : i+1]` of TODAY's bars only, so range_bars 60/120 changes nothing inside the window and the "range" is just the session so far. One `premium_pct` also cannot loosen both sides.
3. Line 288: `conf = ["DISPLACEMENT"]` is always counted, so grade A+ (>= 4) is almost unreachable (0 of 100 trades) and the 2.0 multiplier never applies.
4. Line 216 and `hourly()` (line 142): on RTH-only history the 09:00 hourly candle holds only the 30 bars 09:30-10:00, so FVG1H pools (1,495 episodes, 7 trades) come from half-hour candles in the backtest; live bars would differ.
5. Line 259: the sweep time-out sits under the "FVG exists" branch (a sweep with no FVG never times out; harmless).

## Tables (days.csv has one row per day)

Data: 1266 RTH days 2021-10-01..2026-10-30; IS = 2021-10-01..2023-12-29 (561 days, 27 months), J = 2024-01-02..2026-10-30 (705 days, 34 months). Cost $2.00 per micro round trip, $2/pt. History = 3 prior days (as the existing harness).

## Part 1 check: mirror vs engine (baseline): days with different signals = 0 of 1266; signals 100 (IS 53, J 47)

### 1a. Day funnel (deepest stage reached by any sweep of the day), baseline defaults, NY 09:30-10:00

| deepest stage | rule label | all days | IS | J |
|---|---|---|---|---|
| no pool swept in the window (A3/A4) | A3 pools [GAP params] / A4 transcript / window [GAP] | 0 | 0 | 0 |
| swept, no FVG on the run into the sweep (C1, fvg_lookback) | C1 transcript, lookback [GAP] | 16 | 6 | 10 |
| FVG, but no candle body closed through it (C2) | transcript rule | 419 | 181 | 238 |
| body closed through, displacement too small (C5) | transcript rule, size [GAP] | 333 | 154 | 179 |
| valid IFVG, no retrace into it in time (C3, ifvg_max_bars / window end) | transcript rule, timing [GAP] | 264 | 115 | 149 |
| retrace, wrong premium/discount side (A2) | transcript rule, threshold [GAP] | 90 | 43 | 47 |
| stop wider than 40 pt (D2, transcript: skip) | transcript number | 44 | 9 | 35 |
| TRADE taken |  | 100 | 53 | 47 |
| total days | | 1266 | 561 | 705 |

Of the 0 no-sweep days, 0 had a bar that broke a pool and CLOSED beyond it (a breakout, not a sweep: the engine trades only reversals).

### 1b. Every sweep episode (9814 in 1266 days): the stage it died at, and HOW it ended

| stage reached | rule label | episodes | ended by window end | by timeout (10 bars) | replaced by a new sweep | taken as TRADE / A2 / D2 |
|---|---|---|---|---|---|---|
| swept, no FVG on the run into the sweep (C1, fvg_lookback) | C1 transcript, lookback [GAP] | 3830 | 291 | 0 | 3539 | 0 |
| FVG, but no candle body closed through it (C2) | transcript rule | 4820 | 708 | 76 | 4036 | 0 |
| body closed through, displacement too small (C5) | transcript rule, size [GAP] | 592 | 88 | 58 | 446 | 0 |
| valid IFVG, no retrace into it in time (C3, ifvg_max_bars / window end) | transcript rule, timing [GAP] | 324 | 55 | 1 | 268 | 0 |
| retrace, wrong premium/discount side (A2) | transcript rule, threshold [GAP] | 103 | 0 | 0 | 0 | 103 |
| stop wider than 40 pt (D2, transcript: skip) | transcript number | 45 | 0 | 0 | 0 | 45 |
| TRADE taken |  | 100 | 0 | 0 | 0 | 100 |

Cumulative funnel of the sweep episodes (how many reach each stage):

| stage | episodes reaching it |
|---|---|
| sweeps (A3/A4) | 9814 |
| ... with an FVG on the run (C1) | 5984 |
| ... a body closed through it (C2) | 1164 |
| ... displacement big enough = valid IFVG (C5) | 572 |
| ... retraced into it in time (C3) | 248 |
| ... right premium/discount side (A2) | 145 |
| ... stop <= 40 pt (D2) = TRADE | 100 |

By swept pool kind (episodes -> trades):

| pool kind | episodes | trades |
|---|---|---|
| EQUAL | 20 | 0 |
| FVG1H | 1495 | 7 |
| PDH | 286 | 2 |
| PDL | 216 | 1 |
| SESSION | 5693 | 69 |
| SWING | 2104 | 21 |

Sweep time inside the 30-bar window (episodes that started in each 10-minute slice, and how many of those died of the window end):

| slice | episodes | died by window end | trades |
|---|---|---|---|
| 09:31-09:40 | 4021 | 1 | 30 |
| 09:41-09:50 | 3042 | 40 | 49 |
| 09:51-10:00 | 2751 | 1101 | 21 |

D3 (reward >= 1:2): never blocks a setup by construction (the engine uses the nearest pool beyond 2R, else 2R itself): 88 of 100 trades got a pool target, 12 the plain 2R.
Other blockers counted: days where the 3-loss cap was reached: 0; trades per day max 1.

### 1c. SIZE stage (baseline trades, all 100; static Lucid fit at full DLL / MLL room, then the D149 grade rule)

Grades: {'C': 93, 'B': 7} (confluence count: {1: 48, 2: 45, 3: 7}). Grade size multiplier / 2.0: A+ 1.0, B 0.5, C 0.25 of the fit size.

| plan | fit micros at 20 pt (full) | signals | fit gives 0 (stop too wide for the $ budget) | sized 0 by the grade rule | sized >= 1 | sized >= 1 by grade A+/B/C |
|---|---|---|---|---|---|---|
| Pro 25K | 3 | 100 | 0 | 63 | 37 | 0/6/31 |
| Pro 50K | 8 | 100 | 0 | 0 | 100 | 0/7/93 |
| Pro 100K | 12 | 100 | 0 | 0 | 100 | 0/7/93 |
| Pro 150K | 19 | 100 | 0 | 0 | 100 | 0/7/93 |

By grade (all 100 trades): how many micros each grade gets per plan (median of full fit -> sized):

| plan | grade | trades | median full fit | median sized | sized 0 |
|---|---|---|---|---|---|
| Pro 25K | B | 7 | 2 | 1 | 1 |
| Pro 25K | C | 93 | 3 | 0 | 62 |
| Pro 50K | B | 7 | 6 | 3 | 0 |
| Pro 50K | C | 93 | 7 | 1 | 0 |
| Pro 100K | B | 7 | 9 | 4 | 0 |
| Pro 100K | C | 93 | 11 | 2 | 0 |
| Pro 150K | B | 7 | 14 | 7 | 0 |
| Pro 150K | C | 93 | 17 | 4 | 0 |

### 1d. What exists after 10:00 (mirror with ny_window 09:00-11:30; same engine rules; only 09:30+ bars exist, no pre-market)

| slice (bar close) | sweeps (episodes started) | days with a sweep | valid IFVG formed | signals (trades) |
|---|---|---|---|---|
| 09:31-10:00 (current window) | 9814 | 1266 | 637 | 100 |
| 10:01-10:30 | 8803 | 1266 | 686 | 134 |
| 10:31-11:00 | 8370 | 1265 | 618 | 128 |
| 11:01-11:30 | 8342 | 1264 | 560 | 148 |
| total | 35329 | 1266 | 2501 | 510 |

## Mirror-vs-engine assertion on every engine-setting row: mismatching days = 0

## Part 2 table A: 1 micro after costs, IS (2021-10..2023-12) and J (2024-01..2026-10). D4 rows: per-contract 50/50 blend of partial and runner

| id | row | IS trades | /month | win % | PF | avg $ | total $ | max DD $ | J trades | /month | win % | PF | avg $ | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline (engine defaults) | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 47 | 1.38 | 42.6 | 2.05 | 25.8 | 1,211 | 452 |
| W1030 | ny_window 09:00-10:30 | 118 | 4.37 | 32.2 | 0.75 | -6.4 | -760 | 922 | 116 | 3.41 | 43.1 | 1.42 | 11.0 | 1,280 | 648 |
| W1100 | ny_window 09:00-11:00 | 177 | 6.56 | 32.8 | 0.69 | -7.4 | -1,310 | 1,394 | 185 | 5.44 | 38.9 | 1.24 | 6.1 | 1,124 | 925 |
| W1130 | ny_window 09:00-11:30 | 249 | 9.22 | 36.1 | 0.73 | -5.8 | -1,452 | 1,534 | 261 | 7.68 | 39.1 | 1.20 | 4.7 | 1,238 | 1,092 |
| DM125 | displacement_mult 1.25 | 72 | 2.67 | 30.6 | 0.93 | -1.8 | -132 | 543 | 68 | 2.00 | 42.6 | 1.87 | 21.8 | 1,480 | 588 |
| DM100 | displacement_mult 1.0 | 100 | 3.70 | 29.0 | 0.89 | -2.8 | -282 | 624 | 91 | 2.68 | 37.4 | 1.43 | 12.3 | 1,117 | 466 |
| DB5 | displacement_bars 5 | 68 | 2.52 | 27.9 | 0.66 | -9.2 | -623 | 666 | 56 | 1.65 | 35.7 | 1.45 | 11.9 | 668 | 540 |
| DB20 | displacement_bars 20 | 47 | 1.74 | 31.9 | 0.94 | -1.3 | -62 | 248 | 43 | 1.26 | 41.9 | 2.30 | 31.2 | 1,342 | 270 |
| FL20 | fvg_lookback 20 | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 48 | 1.41 | 41.7 | 1.97 | 24.2 | 1,164 | 452 |
| IM20 | ifvg_max_bars 20 | 56 | 2.07 | 26.8 | 0.67 | -8.9 | -500 | 506 | 49 | 1.44 | 42.9 | 2.05 | 25.3 | 1,238 | 475 |
| EQ4 | eq_tol_ticks 4 | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 47 | 1.38 | 42.6 | 2.05 | 25.8 | 1,211 | 452 |
| SW1 | swing_lookback 1 | 32 | 1.19 | 34.4 | 0.70 | -7.2 | -231 | 374 | 27 | 0.79 | 40.7 | 1.67 | 19.4 | 524 | 284 |
| SW3 | swing_lookback 3 | 79 | 2.93 | 29.1 | 0.78 | -6.1 | -480 | 492 | 65 | 1.91 | 40.0 | 1.61 | 17.0 | 1,104 | 358 |
| RB120 | range_bars 120 | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 47 | 1.38 | 42.6 | 2.05 | 25.8 | 1,211 | 452 |
| PP40 | premium_pct 0.40 (shorts looser, longs tighter) | 51 | 1.89 | 23.5 | 0.54 | -14.4 | -735 | 735 | 46 | 1.35 | 39.1 | 1.67 | 17.9 | 824 | 512 |
| PP60 | premium_pct 0.60 (longs looser, shorts tighter) | 56 | 2.07 | 28.6 | 0.86 | -3.8 | -210 | 450 | 42 | 1.24 | 42.9 | 2.24 | 29.6 | 1,244 | 408 |
| SB1 | stop_buffer_ticks 1 | 53 | 1.96 | 26.4 | 0.70 | -8.3 | -440 | 448 | 47 | 1.38 | 44.7 | 2.13 | 27.1 | 1,272 | 448 |
| GFLOOR | sizing: grade floor (C/B get >= 1 micro if fit >= 1) | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 47 | 1.38 | 42.6 | 2.05 | 25.8 | 1,211 | 452 |
| GLOW | sizing: grade_b_min 2 / grade_a_min 3 | 53 | 1.96 | 26.4 | 0.69 | -8.6 | -456 | 462 | 47 | 1.38 | 42.6 | 2.05 | 25.8 | 1,211 | 452 |
| D4 | D4 partial at first internal liquidity (offline) | 53 | 1.96 | 30.2 | 0.55 | -9.4 | -499 | 512 | 47 | 1.38 | 51.1 | 1.99 | 16.3 | 766 | 192 |
| D5 | D5 break-even at 25% of the move (offline) | 53 | 1.96 | 15.1 | 0.68 | -7.1 | -374 | 444 | 47 | 1.38 | 31.9 | 2.68 | 29.0 | 1,362 | 313 |
| D45 | D4 + D5 (offline) | 53 | 1.96 | 37.7 | 0.51 | -9.1 | -483 | 516 | 47 | 1.38 | 53.2 | 2.42 | 18.1 | 850 | 140 |
| C4 | C4 aggressive entry inside the FVG (offline) | 891 | 33.00 | 29.9 | 0.92 | -2.0 | -1,790 | 3,848 | 936 | 27.53 | 29.5 | 0.92 | -2.4 | -2,220 | 4,612 |

## Part 2 table B: Lucid-fit sizing (static: full DLL/MLL room; grade rule per row). total $ / max DD $ / executed trades (sized >= 1 of signals)

| id | IS 25K total | IS 25K DD | IS 25K exec | IS 50K total | IS 50K exec | J 25K total | J 25K DD | J 25K exec | J 50K total | J 50K DD | J 50K exec | J 100K total | J 150K total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | -226 | 306 | 25/53 | -994 | 53/53 | -287 | 287 | 12/47 | 876 | 573 | 47/47 | 834 | 1,526 |
| W1030 | -18 | 324 | 66/118 | -1,451 | 118/118 | 220 | 269 | 37/116 | 1,734 | 933 | 116/116 | 2,284 | 3,544 |
| W1100 | -206 | 403 | 104/177 | -2,322 | 177/177 | 96 | 592 | 75/185 | 1,395 | 1,555 | 185/185 | 1,628 | 2,542 |
| W1130 | -301 | 568 | 151/249 | -2,462 | 249/249 | 172 | 604 | 120/261 | 1,592 | 1,971 | 261/261 | 1,726 | 2,564 |
| DM125 | -310 | 425 | 34/72 | -672 | 72/72 | -158 | 158 | 18/68 | 1,293 | 714 | 68/68 | 1,433 | 2,498 |
| DM100 | -384 | 550 | 45/100 | -892 | 100/100 | -242 | 242 | 22/91 | 774 | 820 | 91/91 | 915 | 1,660 |
| DB5 | -218 | 300 | 35/68 | -1,062 | 68/68 | -320 | 354 | 19/56 | -112 | 1,002 | 56/56 | -588 | -538 |
| DB20 | -145 | 270 | 21/47 | -502 | 47/47 | -251 | 251 | 11/43 | 1,042 | 382 | 43/43 | 1,160 | 2,147 |
| FL20 | -226 | 306 | 25/53 | -994 | 53/53 | -287 | 287 | 12/48 | 828 | 573 | 48/48 | 740 | 1,338 |
| IM20 | -246 | 326 | 26/56 | -1,099 | 56/56 | -310 | 310 | 13/49 | 857 | 642 | 49/49 | 820 | 1,494 |
| EQ4 | -226 | 306 | 25/53 | -994 | 53/53 | -287 | 287 | 12/47 | 876 | 573 | 47/47 | 834 | 1,526 |
| SW1 | 77 | 144 | 18/32 | -66 | 32/32 | -156 | 222 | 7/27 | 446 | 514 | 27/27 | 570 | 806 |
| SW3 | -316 | 413 | 35/79 | -1,286 | 79/79 | -384 | 384 | 14/65 | 278 | 535 | 65/65 | -466 | -82 |
| RB120 | -226 | 306 | 25/53 | -994 | 53/53 | -287 | 287 | 12/47 | 876 | 573 | 47/47 | 834 | 1,526 |
| PP40 | -301 | 319 | 22/51 | -1,352 | 51/51 | -287 | 287 | 12/46 | 448 | 674 | 46/46 | 473 | 824 |
| PP60 | -164 | 306 | 26/56 | -583 | 56/56 | -267 | 267 | 11/42 | 986 | 486 | 42/42 | 998 | 1,882 |
| SB1 | -252 | 316 | 25/53 | -960 | 53/53 | -199 | 260 | 12/47 | 1,078 | 568 | 47/47 | 1,309 | 2,254 |
| GFLOOR | -494 | 500 | 53/53 | -994 | 53/53 | 1,192 | 452 | 47/47 | 876 | 573 | 47/47 | 834 | 1,526 |
| GLOW | -648 | 750 | 38/53 | -1,942 | 53/53 | -160 | 325 | 26/47 | 1,115 | 884 | 47/47 | 1,141 | 1,951 |
| D4 | -226 | 306 | 25/53 | -734 | 53/53 | -242 | 244 | 12/47 | 866 | 452 | 47/47 | 722 | 706 |
| D5 | -233 | 348 | 25/53 | -936 | 53/53 | -256 | 256 | 12/47 | 1,118 | 434 | 47/47 | 1,118 | 1,976 |
| D45 | -233 | 348 | 25/53 | -768 | 53/53 | -228 | 250 | 12/47 | 1,060 | 382 | 47/47 | 940 | 936 |
| C4 | -1,118 | 2,010 | 488/891 | -4,908 | 891/891 | -1,581 | 1,870 | 379/936 | -4,577 | 6,469 | 936/936 | -8,448 | -12,960 |

## Part 2 table C: Lucid Pro eval (EOD trailing MLL + lock, DLL, 40% consistency + day stop, kill distance, 1 position, size shrinks with MLL room). pass % / bust % (rolling start every day inside the period; runs cannot see the other period)

| id | IS 25K | IS 50K | IS 100K | IS 150K | J 25K | J 50K | J 100K | J 150K |
|---|---|---|---|---|---|---|---|---|
| BASE | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| W1030 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| W1100 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| W1130 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| DM125 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| DM100 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| DB5 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| DB20 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| FL20 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| IM20 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| EQ4 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| SW1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| SW3 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| RB120 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| PP40 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| PP60 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| SB1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| GFLOOR | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 30.4 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| GLOW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| D4 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| D5 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| D45 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| C4 | 0.0 / 0.0 | 1.6 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |

Starts: IS 561, J 705.

### Management diagnostics (all 5 years)

| row | trades | outcomes | partials hit (D4) | avg stop pts | avg target pts |
|---|---|---|---|---|---|
| BASE | 100 | {'STOP': 56, 'TIME': 30, 'TP': 14} | 0 | 23.8 | 89.3 |
| D4 | 100 | {'STOP': 56, 'TIME': 30, 'TP': 14} | 64 | 23.8 | 89.3 |
| D5 | 100 | {'BE': 34, 'STOP': 42, 'TIME': 12, 'TP': 12} | 0 | 23.8 | 89.3 |
| D45 | 100 | {'BE': 34, 'STOP': 42, 'TIME': 12, 'TP': 12} | 60 | 23.8 | 89.3 |
| C4 | 1827 | {'STOP': 1242, 'TP': 319, 'TIME': 266} | 0 | 20.4 | 69.6 |

## Part 3: IS filter (22 candidates tested incl. 0 combos)

Rule: more IS trades than baseline (management rows D4/D5/D4+D5: not fewer; sizing rows: more executed trades at 25K fit) AND IS PF >= 1.10 AND IS total $ (1 micro and 25K fit) >= baseline IS.

| id | row | more trades | IS PF >= 1.10 | IS 1-micro $ >= base | IS 25K $ >= base | IS-eligible | IS 25K total |
|---|---|---|---|---|---|---|---|
| W1030 | ny_window 09:00-10:30 | yes | no | no | yes | no | -18 |
| W1100 | ny_window 09:00-11:00 | yes | no | no | yes | no | -206 |
| W1130 | ny_window 09:00-11:30 | yes | no | no | no | no | -301 |
| DM125 | displacement_mult 1.25 | yes | no | yes | no | no | -310 |
| DM100 | displacement_mult 1.0 | yes | no | yes | no | no | -384 |
| DB5 | displacement_bars 5 | yes | no | no | yes | no | -218 |
| DB20 | displacement_bars 20 | no | no | yes | yes | no | -145 |
| FL20 | fvg_lookback 20 | no | no | yes | yes | no | -226 |
| IM20 | ifvg_max_bars 20 | yes | no | no | no | no | -246 |
| EQ4 | eq_tol_ticks 4 | no | no | yes | yes | no | -226 |
| SW1 | swing_lookback 1 | no | no | yes | yes | no | 77 |
| SW3 | swing_lookback 3 | yes | no | no | no | no | -316 |
| RB120 | range_bars 120 | no | no | yes | yes | no | -226 |
| PP40 | premium_pct 0.40 (shorts looser, longs tighter) | no | no | no | no | no | -301 |
| PP60 | premium_pct 0.60 (longs looser, shorts tighter) | yes | no | yes | yes | no | -164 |
| SB1 | stop_buffer_ticks 1 | no | no | yes | no | no | -252 |
| GFLOOR | sizing: grade floor (C/B get >= 1 micro if fit >= 1) | yes | no | yes | no | no | -494 |
| GLOW | sizing: grade_b_min 2 / grade_a_min 3 | yes | no | yes | no | no | -648 |
| D4 | D4 partial at first internal liquidity (offline) | yes | no | no | yes | no | -226 |
| D5 | D5 break-even at 25% of the move (offline) | yes | no | yes | no | no | -233 |
| D45 | D4 + D5 (offline) | yes | no | no | no | no | -233 |
| C4 | C4 aggressive entry inside the FVG (offline) | yes | no | no | no | no | -1,118 |

IS pick (highest IS 25K-fit total among eligible): None

### J check for every IS-eligible row (J = 2024-01..2026-10; seen by earlier sessions)

| id | J 1-micro $ >= base | J 25K $ >= base | J PF > 1 | J trades >= base | J 25K pass/bust within 2 pts | J 50K pass/bust within 2 pts | J trades | VERDICT |
|---|---|---|---|---|---|---|---|---|
| (none IS-eligible) | | | | | | | | |

Baseline J: trades 47, 1-micro total 1,211, 25K-fit total -287; 25K eval pass/bust 0.0/0.0, 50K 0.0/0.0.

Combos built: 
