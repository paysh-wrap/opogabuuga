# OKALA 8020, BRUNI STRUCTURE, CANDACE ICT, AUCTION (IMRE): 2-year MNQ backtest

Window 2024-11-01..2026-10-30 (495 RTH days), last 12 months from 2025-11-01 (248 days). Cached 5-year MNQ 1-minute RTH data, harness reused from `backtest_new.py`. Engines called unchanged with their default configs (`Okala8020Cfg()`, `BruniStructureCfg()`, `CandaceIctCfg()`, `AuctionImreCfg()`), nothing tuned. Script: `backtest_okala_bruni_candace_imre.py`; per-trade CSVs: `trades_okala.csv`, `trades_bruni.csv`, `trades_candace.csv`, `trades_imre.csv`. Costs $2.00 per micro round trip plus $2/pt.

## Summary (1 micro after costs, 2-year window; trade counts in brackets)

| Strategy | trades | /day | win % | PF | exp. per $ risked | total $ | max DD $ (1 micro) | Lucid Pro EOD result |
|---|---|---|---|---|---|---|---|---|
| OKALA 8020 (base entries) | 2,135 | 4.31 | 36.2 | 0.72 | -17.8% | -8,370 | 8,426 | LOSES MONEY. 25K: 2.0% pass / 0% bust / 98% running (92% stalled, median -852); 50K-150K pass 0.4-1.4% |
| BRUNI STRUCTURE | 404 | 0.82 | 39.1 | 0.89 | -3.7% | -3,854 | 7,222 | LOSES MONEY. 25K 13.3% pass (2y starts), 0% in last 12m; 50K-150K 0.2-1.2% pass; 0% bust |
| CANDACE ICT (NY 09:30-10:00) | 32 (too small) | 0.06 | 46.9 | 2.47 | +63.3% | +1,240 | 452 | 0% pass on all plans (too few trades to reach any target) |
| AUCTION IMRE (est. delta) | 43 (too small) | 0.09 | 18.6 | 0.30 | -57.1% | -862 | 862 | LOSES MONEY. 0% pass on all plans |

Last 12 months (1 micro): OKALA 1,099 base trades, win 35.5%, PF 0.70, -4,678 $; BRUNI 195 trades, win 38.5%, PF 0.98, -430 $; CANDACE 19 trades (too small), win 57.9%, PF 4.06, +1,102 $; IMRE 9 trades (too small), win 11.1%, PF 0.10, -316 $.

Plain reading:
- OKALA loses money at every cut: every setup kind, in-sample (PF 0.76) and out-of-sample (PF 0.58, 420 trades), 0 of 10 chunks profitable. With a 10 pt stop and 15 pt TP1 (1.5R, partly runner) the break-even win rate is about 40%; the engine delivers 36%. Add-to-winners: the engine exposes it (`add_no`); only 46 adds fired (17 in the last 12 months), 39% win, PF 0.82, too small to judge.
- BRUNI is slightly negative overall (PF 0.89, 404 trades). The 2-year sample is BELOW its own 1,000-trade minimum (G1), so the numbers cannot confirm or reject an edge. Context split (all below 100 trades except AGREE): AGREE 223 trades PF 0.82; FOLLOW_A 95 PF 0.57; FOLLOW_P 86 PF 2.21 (too small, one subset out of three, not a basis for tuning). Chunk check: win-rate swing 21.3 pts across 10 chunks of about 40 trades (no chunk more than 20 pts from the overall 39.1%; 4 of 10 chunks profitable). The edge is not shown. Monte Carlo (5,000 runs): 0% of reshuffled runs positive (a reshuffle keeps the total), resample 22% positive, median max DD 7.1-7.2k, 95th pct 9.9-13.6k, longest losing streak 10 median / 15 at the 95th pct. All overlays (autocorrelation, regime flip, shield) are OFF by default and were not tested; measured autocorrelation gap is -0.2 pts (none).
- CANDACE: only 32 trades in two years (about one every 15 days), so no conclusion; positive on the small sample (PF 2.47, 8 of 10 chunks profitable) but only about 3 trades per chunk and 6 trades out-of-sample. At Lucid-fit size on the 25K plan only 5 of 32 trades are sized (grade-tightened size rounds to 0 contracts for C-grade trades; 27 skipped); it cannot pass an eval at this frequency.
- IMRE: 43 signals (BREAKOUT_B 37, FAILED_AUCTION_V 6), 18.6% win, loses money. Delta is estimated from 1-minute bars, so this does not test the real order-flow strategy.

## What could not be tested or is modelled loosely
- Data is RTH only: CANDACE London, Asia range, midnight price and 15/30 s speed cannot be tested; only the New York 09:30-10:00 part of the 09:00-10:00 window exists. OKALA entries use 3-minute bars (200 s is impossible from 1-minute data, a flagged gap in the engine).
- Volume is recovered from the stored VWAP (see `backtest_new.py`); the scale is per day, so the BRUNI and IMRE volume profiles (one day each) are fine but any cross-day volume comparison is not.
- OKALA P&L model (the engine returns outcomes, not prices): 1 micro = single bracket at TP1 (+15 pt) or stop (-10 pt); 2+ micros = leg A ceil(n/2) at TP1, leg B at break-even +1 / runner target / time exit price. Same-bar TP1 and stop touch counts as a stop (engine order). The 4-contract "1 at 30, last at 60" ladder is not built in the engine. Eval sims use base entries only; adds need the controller's cap logic and are not simulated.
- IMRE follows the engine outcome (stop or full TP2); the live two-leg partial with stop-to-entry is not replayed by the engine. Fit risk is multiplied by each signal's `risk_share` (as D150 builds it).
- "Lucid-fit max drawdown" is static sizing (full DLL and MLL room, no day stop), so it overstates what a live account would be allowed to lose; the eval table is the realistic Lucid view (day stop, DLL, trailing EOD MLL, 40% consistency, kill switch distance, sizing shrinks with MLL room). An eval shown as "running" with a negative median P&L is effectively failed or frozen, not alive: the sizing shrinks toward 0 near the MLL, so busts are 0% while pass is near 0%.
- Rolling-start evals are heavily overlapping (495 starts from about 2 years); read them as one sample, not 495 independent ones.

# Detail tables
Data: 1266 cached RTH days; backtest window 2024-11-01..2026-10-30 (495 days), last 12 months from 2025-11-01 (248 days). Costs per micro round trip $2.00 (fee + slippage both ways), $2/pt. IS/OOS: first 80% of days = 2024-11-01..2026-06-10, OOS = 2026-06-11..2026-10-30. Fit divisors/risk % read from the plan yaml: OKALA: 0.25/0.9/3, BRUNI: 0.25/0.9/3, CANDACE: 0.25/0.9/3, IMRE: 0.25/0.9/3 (risk % of MLL / DLL use / divisor).

## OKALA 8020 (defaults)
Signals: 2181 = 2135 base entries + 46 adds (add-to-winners, engine exposes it via `add_no`). 1-micro P&L is the single bracket at TP1 15 pt (stop -10 pt); Lucid-fit with 2+ micros uses the two-leg bracket (leg A ceil(n/2) at TP1, leg B break-even+1 / runner / time). Eval sims use base entries only (adds need the controller's cap logic, not simulated).

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals (base + adds) | 2181 | 4.41 | 36.2 | 0.72 | -17.7% | -3.89 | -8482 | 8538 |
| base entries only | 2135 | 4.31 | 36.2 | 0.72 | -17.8% | -3.92 | -8370 | 8426 |
| adds only | 46 (<100: too small) | 0.09 | 39.1 | 0.82 | -11.1% | -2.43 | -112 | 222 |
| kind = CROSS (base) | 999 | 2.02 | 35.4 | 0.70 | -19.5% | -4.28 | -4278 | 4364 |
| kind = FORK (base) | 99 (<100: too small) | 0.20 | 33.3 | 0.64 | -24.2% | -5.33 | -528 | 540 |
| kind = LEVEL (base) | 952 | 1.92 | 37.2 | 0.75 | -15.5% | -3.41 | -3244 | 3272 |
| kind = REVERSE_FORK (base) | 85 (<100: too small) | 0.17 | 36.5 | 0.73 | -17.1% | -3.76 | -320 | 516 |
| exit = BE | 353 | 0.71 | 100.0 | inf | 127.3% | 28.00 | 9884 | 0 |
| exit = RUNNER | 418 | 0.84 | 100.0 | inf | 127.3% | 28.00 | 11704 | 0 |
| exit = STOP | 1363 | 2.75 | 0.0 | 0.00 | -100.0% | -22.00 | -29986 | 29986 |
| exit = TIME | 1 (<100: too small) | 0.00 | 100.0 | inf | 127.3% | 28.00 | 28 | 0 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals (base + adds) | 1116 | 4.50 | 35.5 | 0.70 | -19.4% | -4.26 | -4752 | 4906 |
| base entries only | 1099 | 4.43 | 35.5 | 0.70 | -19.3% | -4.26 | -4678 | 4876 |
| adds only | 17 (<100: too small) | 0.07 | 35.3 | 0.69 | -19.8% | -4.35 | -74 | 104 |
| kind = CROSS (base) | 543 | 2.19 | 33.5 | 0.64 | -23.8% | -5.24 | -2846 | 3078 |
| kind = FORK (base) | 51 (<100: too small) | 0.21 | 29.4 | 0.53 | -33.2% | -7.29 | -372 | 378 |
| kind = LEVEL (base) | 455 | 1.83 | 38.7 | 0.80 | -12.1% | -2.66 | -1210 | 1244 |
| kind = REVERSE_FORK (base) | 50 (<100: too small) | 0.20 | 34.0 | 0.66 | -22.7% | -5.00 | -250 | 516 |
| exit = BE | 161 | 0.65 | 100.0 | inf | 127.3% | 28.00 | 4508 | 0 |
| exit = RUNNER | 229 | 0.92 | 100.0 | inf | 127.3% | 28.00 | 6412 | 0 |
| exit = STOP | 709 | 2.86 | 0.0 | 0.00 | -100.0% | -22.00 | -15598 | 15598 |

**Max drawdown at Lucid-fit sizing (static: full DLL and MLL room, one fit per trade, no day stop; skipped = fit gives < 1 contract), 2-year**

| Plan | trades sized | skipped | median contracts | total $ | max DD $ |
|---|---|---|---|---|---|
| Pro 25K | 2135 | 0 | 7 | -49893 | 50291 |
| Pro 50K | 2135 | 0 | 16 | -110728 | 111640 |
| Pro 100K | 2135 | 0 | 24 | -166092 | 167460 |
| Pro 150K | 2135 | 0 | 36 | -249138 | 251190 |

**In-sample (80%) vs out-of-sample (20%), 1 micro, base entries**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 1715 | 4.33 | 37.3 | 0.76 | -15.2% | -3.34 | -5730 | 5828 |
| OUT-OF-SAMPLE | 420 | 4.24 | 31.4 | 0.58 | -28.6% | -6.29 | -2640 | 2662 |

**10-chunk stability (chronological, 2135 trades, ~213 per chunk; overall win 36.2%)**

| chunk | trades | win % | PF | P&L $ |
|---|---|---|---|---|
| 1 | 213 | 36.6 | 0.74 | -786 |
| 2 | 214 | 36.4 | 0.73 | -808 |
| 3 | 213 | 34.7 | 0.68 | -986 |
| 4 | 214 | 36.9 | 0.74 | -758 |
| 5 | 213 | 41.8 | 0.91 | -236 |
| 6 | 214 | 37.9 | 0.78 | -658 |
| 7 | 213 | 35.7 | 0.71 | -886 |
| 8 | 214 | 38.8 | 0.81 | -558 |
| 9 | 213 | 26.8 | 0.47 | -1836 |
| 10 | 214 | 36.0 | 0.72 | -858 |

Win-rate swing (max - min) = 15.0 pts; chunks > 20 pts from the overall win rate: 0 of 10; profitable chunks: 0 of 10.
Autocorrelation (G/F2): win after a loss 36.7% (1362 trades) vs overall 36.2% (gap -0.6 pts). Profit factor without the single best trade: 0.72.

**Monte Carlo, 5,000 runs on 2135 trades, 1 micro**

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th |
|---|---|---|---|---|---|---|
| reshuffle | -8370 | -8370 | 0 | 8474 | 8698 | 15 / 21 |
| resample | -8370 | -10170 | 0 | 8488 | 10298 | 15 / 21 |

**Lucid Pro EOD evaluation (Lucid-fit sizing, rolling start every trading day; window trades only; base entries)**

| Plan | starts from | starts | pass % | bust % | running % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 2.0 | 0.0 | 98.0 | 91.9 | -852 | 7 |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 4.0 | 0.0 | 96.0 | 83.9 | -871 | 7 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 1.4 | 0.0 | 98.6 | 92.5 | -1850 | 9 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 2.4 | 0.0 | 97.6 | 85.5 | -1886 | 10 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 0.4 | 0.0 | 99.6 | 93.3 | -2886 | 10 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.8 | 0.0 | 99.2 | 86.7 | -2886 | 10 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 0.4 | 0.0 | 99.6 | 93.3 | -4386 | 10 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.8 | 0.0 | 99.2 | 86.7 | -4386 | 10 |

## BRUNI STRUCTURE (defaults, overlays OFF)

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals | 404 | 0.82 | 39.1 | 0.89 | -3.7% | -9.54 | -3854 | 7222 |
| kind = AGREE | 223 | 0.45 | 41.3 | 0.82 | -6.8% | -18.59 | -4146 | 6289 |
| kind = FOLLOW_A | 95 (<100: too small) | 0.19 | 32.6 | 0.57 | -14.8% | -42.39 | -4027 | 4548 |
| kind = FOLLOW_P | 86 (<100: too small) | 0.17 | 40.7 | 2.21 | 29.7% | 50.21 | 4318 | 1080 |
| regime = None | 404 | 0.82 | 39.1 | 0.89 | -3.7% | -9.54 | -3854 | 7222 |
| exit = STOP | 168 | 0.34 | 0.0 | 0.00 | -100.0% | -157.54 | -26466 | 26466 |
| exit = TIME | 184 | 0.37 | 57.6 | 2.08 | 13.9% | 52.98 | 9748 | 1098 |
| exit = TP | 52 (<100: too small) | 0.11 | 100.0 | inf | 195.3% | 247.38 | 12864 | 0 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals | 195 | 0.79 | 38.5 | 0.98 | -0.7% | -2.20 | -430 | 3592 |
| kind = AGREE | 116 | 0.47 | 43.1 | 1.06 | 1.8% | 5.53 | 642 | 2027 |
| kind = FOLLOW_A | 48 (<100: too small) | 0.19 | 29.2 | 0.55 | -14.5% | -47.72 | -2290 | 2737 |
| kind = FOLLOW_P | 31 (<100: too small) | 0.12 | 35.5 | 1.66 | 18.1% | 39.34 | 1220 | 740 |
| regime = None | 195 | 0.79 | 38.5 | 0.98 | -0.7% | -2.20 | -430 | 3592 |
| exit = STOP | 76 (<100: too small) | 0.31 | 0.0 | 0.00 | -100.0% | -157.94 | -12004 | 12004 |
| exit = TIME | 98 (<100: too small) | 0.40 | 55.1 | 1.84 | 11.3% | 48.97 | 4799 | 1098 |
| exit = TP | 21 (<100: too small) | 0.08 | 100.0 | inf | 196.3% | 322.62 | 6775 | 0 |

**Max drawdown at Lucid-fit sizing (static: full DLL and MLL room, one fit per trade, no day stop; skipped = fit gives < 1 contract), 2-year**

| Plan | trades sized | skipped | median contracts | total $ | max DD $ |
|---|---|---|---|---|---|
| Pro 25K | 166 | 238 | 2.0 | -3616 | 3947 |
| Pro 50K | 314 | 90 | 2.0 | -8526 | 9840 |
| Pro 100K | 372 | 32 | 3.0 | -15116 | 17086 |
| Pro 150K | 387 | 17 | 4 | -19129 | 22334 |

**In-sample (80%) vs out-of-sample (20%), 1 micro**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 336 | 0.85 | 39.6 | 0.89 | -4.0% | -9.56 | -3211 | 7222 |
| OUT-OF-SAMPLE | 68 (<100: too small) | 0.69 | 36.8 | 0.91 | -2.7% | -9.46 | -644 | 2904 |

**10-chunk stability (chronological, 404 trades, ~40 per chunk; overall win 39.1%)**

| chunk | trades | win % | PF | P&L $ |
|---|---|---|---|---|
| 1 | 40 | 32.5 | 0.78 | -540 |
| 2 | 40 | 45.0 | 1.00 | -6 |
| 3 | 41 | 34.1 | 0.58 | -2800 |
| 4 | 40 | 45.0 | 1.32 | 507 |
| 5 | 41 | 46.3 | 0.83 | -478 |
| 6 | 40 | 25.0 | 0.52 | -1600 |
| 7 | 40 | 40.0 | 1.23 | 759 |
| 8 | 41 | 46.3 | 1.50 | 1256 |
| 9 | 40 | 45.0 | 1.00 | 10 |
| 10 | 41 | 31.7 | 0.67 | -960 |

Win-rate swing (max - min) = 21.3 pts; chunks > 20 pts from the overall win rate: 0 of 10; profitable chunks: 4 of 10.
Autocorrelation (G/F2): win after a loss 39.3% (244 trades) vs overall 39.1% (gap -0.2 pts). Profit factor without the single best trade: 0.87.

**Monte Carlo, 5,000 runs on 404 trades, 1 micro**

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th |
|---|---|---|---|---|---|---|
| reshuffle | -3854 | -3854 | 0 | 7064 | 9858 | 10 / 15 |
| resample | -3860 | -11896 | 22 | 7240 | 13594 | 10 / 15 |

**Lucid Pro EOD evaluation (Lucid-fit sizing, rolling start every trading day; window trades only)**

| Plan | starts from | starts | pass % | bust % | running % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 13.3 | 0.0 | 86.7 | 56.8 | -748 | 50 |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 0.0 | 0.0 | 100.0 | 40.3 | -748 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 1.2 | 0.0 | 98.8 | 69.5 | -1426 | 36 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 0.0 | 0.0 | 100.0 | 41.5 | -1426 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 0.2 | 0.0 | 99.8 | 68.9 | -2129 | 40 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.0 | 0.0 | 100.0 | 38.3 | -2200 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 0.2 | 0.0 | 99.8 | 67.5 | -3005 | 41 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.0 | 0.0 | 100.0 | 35.5 | -3022 | - |

## CANDACE ICT SCALP (defaults, New York window only)
Only the New York window 09:30-10:00 can trade (data is RTH only); London cannot be tested. Fit size = grade-tightened (`grade_contracts`).

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals | 32 (<100: too small) | 0.06 | 46.9 | 2.47 | 63.3% | 38.75 | 1240 | 452 |
| kind = B | 2 (<100: too small) | 0.00 | 0.0 | 0.00 | -100.0% | -50.75 | -102 | 102 |
| kind = C | 30 (<100: too small) | 0.06 | 50.0 | 2.81 | 72.3% | 44.72 | 1342 | 452 |
| swept = FVG1H | 2 (<100: too small) | 0.00 | 0.0 | 0.00 | -100.0% | -55.00 | -110 | 110 |
| swept = PDH | 1 (<100: too small) | 0.00 | 100.0 | inf | 226.5% | 132.50 | 132 | 0 |
| swept = SESSION | 22 (<100: too small) | 0.04 | 54.5 | 3.05 | 73.7% | 49.80 | 1096 | 367 |
| swept = SWING | 7 (<100: too small) | 0.01 | 28.6 | 1.62 | 40.3% | 17.43 | 122 | 134 |
| exit = STOP | 15 (<100: too small) | 0.03 | 0.0 | 0.00 | -100.0% | -53.37 | -800 | 800 |
| exit = TIME | 10 (<100: too small) | 0.02 | 80.0 | 17.07 | 97.3% | 65.10 | 651 | 40 |
| exit = TP | 7 (<100: too small) | 0.01 | 100.0 | inf | 284.7% | 198.50 | 1390 | 0 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals | 19 (<100: too small) | 0.08 | 57.9 | 4.06 | 89.0% | 58.00 | 1102 | 140 |
| kind = B | 2 (<100: too small) | 0.01 | 0.0 | 0.00 | -100.0% | -50.75 | -102 | 102 |
| kind = C | 17 (<100: too small) | 0.07 | 64.7 | 5.66 | 105.9% | 70.79 | 1204 | 107 |
| swept = FVG1H | 2 (<100: too small) | 0.01 | 0.0 | 0.00 | -100.0% | -55.00 | -110 | 110 |
| swept = PDH | 1 (<100: too small) | 0.00 | 100.0 | inf | 226.5% | 132.50 | 132 | 0 |
| swept = SESSION | 13 (<100: too small) | 0.05 | 69.2 | 7.91 | 121.2% | 85.81 | 1116 | 107 |
| swept = SWING | 3 (<100: too small) | 0.01 | 33.3 | 0.59 | -24.1% | -12.00 | -36 | 50 |
| exit = STOP | 6 (<100: too small) | 0.02 | 0.0 | 0.00 | -100.0% | -53.25 | -320 | 320 |
| exit = TIME | 9 (<100: too small) | 0.04 | 77.8 | 16.95 | 105.3% | 71.78 | 646 | 40 |
| exit = TP | 4 (<100: too small) | 0.02 | 100.0 | inf | 254.3% | 193.88 | 776 | 0 |

**Max drawdown at Lucid-fit sizing (static: full DLL and MLL room, one fit per trade, no day stop; skipped = fit gives < 1 contract), 2-year**

| Plan | trades sized | skipped | median contracts | total $ | max DD $ |
|---|---|---|---|---|---|
| Pro 25K | 5 | 27 | 1 | -200 | 200 |
| Pro 50K | 32 | 0 | 1.0 | 1096 | 573 |
| Pro 100K | 32 | 0 | 2.0 | 1087 | 875 |
| Pro 150K | 32 | 0 | 3.0 | 2008 | 1363 |

**In-sample (80%) vs out-of-sample (20%), 1 micro**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 26 (<100: too small) | 0.07 | 50.0 | 2.54 | 64.2% | 39.08 | 1016 | 452 |
| OUT-OF-SAMPLE | 6 (<100: too small) | 0.06 | 33.3 | 2.24 | 59.7% | 37.33 | 224 | 140 |

**10-chunk stability (chronological, 32 trades, ~3 per chunk; overall win 46.9%)**

| chunk | trades | win % | PF | P&L $ |
|---|---|---|---|---|
| 1 | 3 | 66.7 | 14.46 | 323 |
| 2 | 3 | 33.3 | 2.53 | 162 |
| 3 | 3 | 0.0 | 0.00 | -212 |
| 4 | 3 | 33.3 | 0.06 | -72 |
| 5 | 4 | 50.0 | 4.48 | 218 |
| 6 | 3 | 66.7 | 3.37 | 150 |
| 7 | 3 | 66.7 | 2.65 | 82 |
| 8 | 3 | 100.0 | inf | 434 |
| 9 | 3 | 33.3 | 1.78 | 83 |
| 10 | 4 | 25.0 | 1.53 | 74 |

Win-rate swing (max - min) = 100.0 pts; chunks > 20 pts from the overall win rate: 3 of 10; profitable chunks: 8 of 10.
Autocorrelation (G/F2): win after a loss 43.8% (16 trades) vs overall 46.9% (gap +3.1 pts). Profit factor without the single best trade: 2.16.

**Monte Carlo, 5,000 runs on 32 trades, 1 micro**

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th |
|---|---|---|---|---|---|---|
| reshuffle | 1240 | 1240 | 100 | 246 | 406 | 4 / 7 |
| resample | 1236 | 218 | 98 | 248 | 500 | 4 / 8 |

**Lucid Pro EOD evaluation (Lucid-fit sizing, rolling start every trading day; window trades only)**

| Plan | starts from | starts | pass % | bust % | running % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 0.0 | 0.0 | 100.0 | 0.0 | -140 | - |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 0.0 | 0.0 | 100.0 | 0.0 | -140 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 0.0 | 0.0 | 100.0 | 0.0 | 580 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 0.0 | 0.0 | 100.0 | 0.0 | 137 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 0.0 | 0.0 | 100.0 | 0.0 | 411 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.0 | 0.0 | 100.0 | 0.0 | 98 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 0.0 | 0.0 | 100.0 | 0.0 | 899 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.0 | 0.0 | 100.0 | 0.0 | 235 | - |

## AUCTION IMRE / Order Flow (defaults, ESTIMATED delta)
1-micro and Lucid-fit P&L follow the engine outcome (stop or full second target TP2; the live two-leg partial / stop-to-entry is not replayed by the engine). Fit risk is multiplied by each signal's `risk_share` (as D150 builds it).

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals | 43 (<100: too small) | 0.09 | 18.6 | 0.30 | -57.1% | -20.03 | -862 | 862 |
| kind = BREAKOUT_B | 37 (<100: too small) | 0.07 | 18.9 | 0.41 | -47.3% | -11.00 | -407 | 424 |
| kind = FAILED_AUCTION_V | 6 (<100: too small) | 0.01 | 16.7 | 0.16 | -70.0% | -75.75 | -454 | 454 |
| exit = MTM | 1 (<100: too small) | 0.00 | 100.0 | inf | 76.5% | 84.50 | 84 | 0 |
| exit = STOP | 35 (<100: too small) | 0.07 | 0.0 | 0.00 | -100.0% | -35.26 | -1234 | 1234 |
| exit = TP | 7 (<100: too small) | 0.01 | 100.0 | inf | 174.5% | 41.14 | 288 | 0 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL signals | 9 (<100: too small) | 0.04 | 11.1 | 0.10 | -84.7% | -35.11 | -316 | 316 |
| kind = BREAKOUT_B | 7 (<100: too small) | 0.03 | 14.3 | 0.27 | -62.9% | -13.79 | -96 | 132 |
| kind = FAILED_AUCTION_V | 2 (<100: too small) | 0.01 | 0.0 | 0.00 | -100.0% | -109.75 | -220 | 220 |
| exit = STOP | 8 (<100: too small) | 0.03 | 0.0 | 0.00 | -100.0% | -44.00 | -352 | 352 |
| exit = TP | 1 (<100: too small) | 0.00 | 100.0 | inf | 171.4% | 36.00 | 36 | 0 |

**Max drawdown at Lucid-fit sizing (static: full DLL and MLL room, one fit per trade, no day stop; skipped = fit gives < 1 contract), 2-year**

| Plan | trades sized | skipped | median contracts | total $ | max DD $ |
|---|---|---|---|---|---|
| Pro 25K | 43 | 0 | 3 | -1848 | 1848 |
| Pro 50K | 43 | 0 | 7 | -4270 | 4270 |
| Pro 100K | 43 | 0 | 11 | -6724 | 6724 |
| Pro 150K | 43 | 0 | 17 | -10143 | 10143 |

**In-sample (80%) vs out-of-sample (20%), 1 micro**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 42 (<100: too small) | 0.11 | 19.0 | 0.31 | -56.4% | -19.98 | -839 | 839 |
| OUT-OF-SAMPLE | 1 (<100: too small) | 0.01 | 0.0 | 0.00 | -100.0% | -22.50 | -22 | 22 |

**10-chunk stability (chronological, 43 trades, ~4 per chunk; overall win 18.6%)**

| chunk | trades | win % | PF | P&L $ |
|---|---|---|---|---|
| 1 | 4 | 0.0 | 0.00 | -91 |
| 2 | 4 | 50.0 | 1.23 | 16 |
| 3 | 4 | 50.0 | 0.71 | -52 |
| 4 | 5 | 40.0 | 1.59 | 34 |
| 5 | 4 | 0.0 | 0.00 | -90 |
| 6 | 4 | 0.0 | 0.00 | -113 |
| 7 | 5 | 0.0 | 0.00 | -102 |
| 8 | 4 | 25.0 | 0.16 | -148 |
| 9 | 4 | 25.0 | 0.15 | -199 |
| 10 | 5 | 0.0 | 0.00 | -117 |

Win-rate swing (max - min) = 50.0 pts; chunks > 20 pts from the overall win rate: 3 of 10; profitable chunks: 2 of 10.
Autocorrelation (G/F2): win after a loss 17.6% (34 trades) vs overall 18.6% (gap +1.0 pts). Profit factor without the single best trade: 0.23.

**Monte Carlo, 5,000 runs on 43 trades, 1 micro**

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th |
|---|---|---|---|---|---|---|
| reshuffle | -862 | -862 | 0 | 896 | 995 | 11 / 18 |
| resample | -858 | -1347 | 0 | 901 | 1382 | 12 / 22 |

**Lucid Pro EOD evaluation (Lucid-fit sizing, rolling start every trading day; window trades only)**

| Plan | starts from | starts | pass % | bust % | running % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | -601 | - |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | -68 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | -1263 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | -180 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | -1958 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | -270 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | -3008 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | -405 | - |
