# Session 18 - "S.M.C" (SuperTrend + Smart Money Concepts) on MNQ, 1 micro, flat daily

Research only (no app code, no git). Script: `smc.py` (`python3 -I smc.py`, ~4 min). Data: the session-17 cached Databento `MNQ.v.0` 1-minute file
(2019-05..2026-11, no new download). Eval sim + baseline: `docs/results/session17/noise_sharpen/sim.py` and its preset-C stream.

## Method
- Pick on IS 2019-05..2023-12, judge on held-out (HO) 2024-01..2026-11 only. IS-pick rule (fixed before looking at HO): highest IS PF with >= 100 IS trades, one per family.
- Signals on CLOSED bars (1m/5m/15m, resampled from 1m, full ETH history for indicator warm-up); entry at the next 1m open (market) or a limit fill; signal bar close 09:35-15:30 ET; flat 15:59 close; one position at a time; no repainting (swing pivots are used only after their 2 right bars closed; SuperTrend of the last closed higher-TF bar).
- Costs: $1.00 fee RT + 1 tick slippage on every fill (entry, stop, target, exit, also limit fills); stop-first inside a bar; gaps fill at the open. Skip if stop < 4 pt or > 124 pt ($250 cap, same as NOISE).
- (A) SuperTrend(10, 3) Wilder ATR. Entry on a flip. Exit = opposite flip (+$250 emergency stop), or stop = SuperTrend line at the signal bar with 1.5R / 2R target. 3 params (tf, exit, R).
- (B) Liquidity sweep: bar wicks through prior-day RTH high/low, overnight high/low, or last confirmed swing (2/2 fractal) and closes back inside. Within 6 bars an FVG in the reversal direction (3-bar gap, formed after the sweep) -> limit at the gap midpoint (CE), valid 6 bars; stop = sweep extreme +- 1 tick; 1.5R / 2R target. Params: tf, R, window 6.
- (C) = (B) only when SuperTrend(10,3) of the last closed 5m or 15m bar agrees; optional extra filter EMA200 side or RSI(14) vs 50 on the entry TF.
- Random benchmark: same entry times/stop distance/R/exits, random direction, 30 seeds (mean shown). Eval: Lucid Pro 25K (target +1,250, $1,000 EOD trailing MLL, lock 25,100), rolling 120-session starts + block bootstrap; med days = median days-to-pass.

## Results (HO = 2024-01..2026-11)
| strategy | IS tr | IS win% | IS PF | HO tr | HO win% | HO PF | HO $/tr | HO net $ | HO maxDD $ | PASS/BUST % roll | boot PASS/BUST % | med days | random-dir HO $/tr, PF, PASS/BUST |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C | 722 | 46.3 | 1.38 | 427 | 52.2 | 1.43 | 27.19 | 11,609 | 2,028 | 60.3/39.4 | 66.2/33.8 | 46.0 | (beats 99.5% of seeds, s17) |
| A ST1m exit=flip | 10467 | 35.0 | 0.91 | 6130 | 36.0 | 0.94 | -2.81 | -17,240 | 20,670 | 19.8/80.2 | 24.5/75.5 | 8.0 | -2.19, 0.95, 25.3/74.7 |
| A ST1m exit=1.5 | 4787 | 39.6 | 0.9 | 2760 | 39.7 | 0.9 | -6.55 | -18,089 | 22,727 | 12.2/87.8 | 13.0/87.0 | 15.0 | -1.44, 0.98, 25.1/74.9 |
| A ST1m exit=2.0 | 4031 | 34.8 | 0.91 | 2358 | 35.7 | 0.91 | -6.38 | -15,040 | 16,025 | 17.8/82.2 | 21.0/79.0 | 10.0 | -1.24, 0.98, 27.4/72.6 |
| A ST5m exit=flip | 2264 | 43.2 | 1.09 | 1364 | 42.3 | 1.03 | 2.32 | 3,166 | 5,512 | 37.7/62.3 | 37.0/63.0 | 13.0 | -3.98, 0.95, 28.1/71.9 |
| A ST5m exit=1.5 | 1426 | 47.9 | 1.12 | 688 | 45.9 | 0.98 | -1.32 | -909 | 5,838 | 31.7/68.3 | 30.5/69.5 | 31.0 | -0.28, 1.0, 30.4/66.8 |
| **IS-pick** A ST5m exit=2.0 | 1367 | 45.8 | 1.14 | 664 | 43.8 | 0.98 | -1.46 | -967 | 5,433 | 36.5/63.5 | 28.2/71.8 | 30.0 | 0.57, 1.01, 33.1/65.0 |
| A ST15m exit=flip | 1075 | 48.5 | 1.04 | 602 | 42.5 | 0.94 | -6.17 | -3,717 | 10,688 | 30.0/70.0 | 27.2/72.8 | 21.0 | -14.02, 0.87, 24.2/75.8 |
| A ST15m exit=1.5 | 605 | 50.9 | 1.09 | 187 | 52.9 | 1.46 | 27.11 | 5,070 | 1,657 | 30.6/13.9 | 72.2/27.0 | 61.5 | 2.25, 1.04, 13.1/30.2 |
| A ST15m exit=2.0 | 603 | 50.6 | 1.1 | 187 | 50.8 | 1.42 | 25.12 | 4,697 | 1,804 | 35.4/19.0 | 64.8/35.0 | 56.0 | -0.11, 1.01, 13.8/30.6 |
| B sweep+FVG 1m R=1.5 | 7560 | 40.2 | 0.89 | 5193 | 40.3 | 0.93 | -1.48 | -7,681 | 13,260 | 12.2/87.8 | 11.8/88.2 | 20.0 | -4.84, 0.78, 1.3/98.7 |
| B sweep+FVG 1m R=2.0 | 7279 | 33.5 | 0.88 | 4995 | 33.7 | 0.93 | -1.55 | -7,766 | 12,836 | 15.3/84.7 | 11.0/89.0 | 32.5 | -4.8, 0.8, 2.9/96.9 |
| B sweep+FVG 5m R=1.5 | 2020 | 42.1 | 0.93 | 1158 | 41.2 | 0.98 | -0.8 | -926 | 4,158 | 18.1/68.8 | 20.0/80.0 | 71.5 | -3.79, 0.91, 14.8/74.7 |
| **IS-pick** B sweep+FVG 5m R=2.0 | 1959 | 36.9 | 0.96 | 1114 | 35.0 | 0.98 | -1.08 | -1,205 | 3,942 | 16.7/72.2 | 20.2/79.8 | 59.0 | -4.56, 0.9, 16.0/78.5 |
| C 1m +ST5m R=1.5 | 3592 | 39.9 | 0.9 | 2510 | 40.4 | 0.93 | -1.35 | -3,389 | 5,067 | 7.9/68.8 | 11.5/88.5 | 96.0 | -4.62, 0.79, 1.6/93.6 |
| C 1m +ST5m R=2.0 | 3518 | 33.1 | 0.88 | 2454 | 33.9 | 0.97 | -0.74 | -1,804 | 3,903 | 25.8/60.9 | 20.0/80.0 | 82.0 | -4.37, 0.82, 3.3/92.1 |
| C 1m +ST15m R=1.5 | 3508 | 40.3 | 0.89 | 2405 | 40.6 | 0.97 | -0.52 | -1,244 | 4,196 | 23.2/64.6 | 19.2/80.8 | 54.5 | -4.68, 0.79, 3.4/93.6 |
| C 1m +ST15m R=2.0 | 3443 | 33.7 | 0.89 | 2343 | 34.0 | 0.99 | -0.21 | -495 | 3,941 | 39.9/58.4 | 26.2/73.8 | 57.0 | -4.62, 0.81, 3.3/92.8 |
| C 1m +ST15m+EMA200 R=1.5 | 2731 | 39.9 | 0.86 | 1864 | 41.1 | 1.04 | 0.77 | 1,441 | 2,246 | 30.0/51.8 | 37.5/62.5 | 54.5 | -3.55, 0.85, 2.9/80.6 |
| C 1m +ST15m+RSI50 R=1.5 | 2595 | 39.5 | 0.86 | 1766 | 41.7 | 1.05 | 1.0 | 1,771 | 1,858 | 24.9/42.8 | 42.5/57.2 | 68.5 | -3.54, 0.85, 4.8/78.3 |
| C 1m +ST15m+EMA200 R=2.0 | 2684 | 33.6 | 0.86 | 1813 | 34.5 | 1.06 | 1.44 | 2,613 | 2,374 | 45.3/45.3 | 42.8/57.2 | 51.0 | -3.71, 0.85, 6.4/82.8 |
| C 1m +ST15m+RSI50 R=2.0 | 2545 | 33.5 | 0.88 | 1718 | 34.5 | 1.05 | 1.25 | 2,154 | 1,870 | 40.5/52.4 | 37.5/62.5 | 68.0 | -3.94, 0.85, 4.9/85.6 |
| **IS-pick** C 5m +ST15m R=1.5 | 846 | 43.6 | 0.99 | 496 | 42.5 | 1.03 | 1.39 | 691 | 2,052 | 10.2/34.8 | 30.8/69.0 | 98.5 | -5.28, 0.89, 7.8/57.3 |
| C 5m +ST15m R=2.0 | 838 | 37.6 | 0.95 | 488 | 38.1 | 1.05 | 2.13 | 1,041 | 1,922 | 16.1/39.7 | 32.8/67.0 | 86.0 | -6.57, 0.87, 5.9/64.6 |
| C 5m +ST15m+EMA200 R=1.5 | 709 | 43.3 | 0.96 | 426 | 43.0 | 1.08 | 3.61 | 1,540 | 1,656 | 9.1/16.7 | 41.2/58.8 | 106.0 | -5.87, 0.88, 6.1/52.0 |
| C 5m +ST15m+RSI50 R=1.5 | 740 | 43.5 | 0.97 | 434 | 42.6 | 1.02 | 1.03 | 448 | 2,084 | 9.1/35.4 | 31.2/68.2 | 89.5 | -6.02, 0.88, 8.1/55.0 |
| C 5m +ST15m+EMA200 R=2.0 | 703 | 37.1 | 0.91 | 421 | 38.2 | 1.08 | 3.98 | 1,675 | 1,578 | 20.4/24.9 | 36.2/63.8 | 89.0 | -4.75, 0.91, 9.1/57.2 |
| C 5m +ST15m+RSI50 R=2.0 | 735 | 37.3 | 0.93 | 429 | 38.0 | 1.01 | 0.26 | 113 | 2,362 | 11.3/40.5 | 28.8/71.0 | 95.0 | -7.61, 0.86, 8.0/61.7 |

## Reading the numbers
- **Source claim (SuperTrend 68% win / PF 2.4 / 12% DD on ES/NQ 2020-26): not reproduced.** Our best SuperTrend rows reach 43-53% win and PF 0.9-1.1 after costs; no variant comes near 68% / 2.4.
- **(A) SuperTrend alone:** 1m is a cost machine (PF 0.90-0.94, -$15-18k HO). The IS-pick (5m, 2R, IS PF 1.14) fell to PF 0.98 held-out. 5m flip-exit was the only 5m row positive in both periods (PF 1.09 -> 1.03, +$2.3/tr HO) but it busts 62% of evals. 15m 1.5R/2R looks good held-out (PF 1.42-1.46) but was weak in-sample (PF 1.09-1.10), and its HO trade count collapses (605 -> 187) because the higher NQ price makes most 15m stops wider than the $250 cap - a small, era-dependent sample, not an edge to trust.
- **(B) sweep + FVG:** loses in every row and both periods (PF 0.88-0.98). It does beat random direction (random PF 0.78-0.91), so the reversal direction has some information, but not enough to pay costs at 1.5-2R.
- **(C) S.M.C combined:** the SuperTrend filter roughly halves trades and lifts PF by ~0.04-0.1, but IS PF stays < 1 everywhere (IS-pick 5m+ST15m 1.5R: IS 0.99 -> HO 1.03, +$1.4/tr, roll PASS 10% / BUST 35%, mostly OPEN = too few trades). The best HO rows (+EMA200 / RSI, PF 1.04-1.08) were all losers in-sample - selecting them would be fitting the held-out window.
- **vs NOISE preset C** (HO 427 tr, 52.2% win, PF 1.43, +$27/tr, PASS 60% / BUST 39%, median 46 days): nothing here is close on an IS-honest basis.

## Verdict (plain language)
S.M.C as described does not work on MNQ after realistic costs. SuperTrend alone is roughly break-even at best on 5m and a loser on 1m; the
liquidity-sweep + FVG idea loses money; adding the SuperTrend filter makes it lose less but never turns it reliably positive in the period we used to choose it.
The article's 68% / PF 2.4 claim is not supported by our test. Do NOT add any of these as a strategy button; NOISE preset C stays the main strategy.

## Combinations that could work (untested hypotheses for a later helper - judge on HO only after an IS pick)
1. **SuperTrend 15m as a regime filter for NOISE**, not as an entry: skip NOISE entries against the 15m SuperTrend direction (series in `out/supertrend_15m_rth.csv.gz`, `out/supertrend_daily.csv`). Low parameter count (0 new params with 10/3).
2. **SuperTrend + Triple RSI + DMI agreement** as a day/hour direction vote, used as G2-style bias or a NOISE side filter - the sweep/FVG part adds little and should be dropped.
3. SuperTrend 5m flip with a flip exit was the only stand-alone row positive in both eras; might merit a test with a time-of-day restriction (one pre-registered window) - expect small edge.
4. Sweep+FVG beats random direction; maybe useful only as an entry-timing refinement inside an existing edge (e.g. NOISE breakout day), not alone.

## Files (`out/`)
- `results.json` all numbers; `run.log`; `stream_*.csv.gz` per-trade streams (d, entry/exit 1m index, side, pnl, mae, risk).
- `supertrend_15m_rth.csv.gz`, `supertrend_5m_rth.csv.gz`: per RTH bar (bar start ET, close, st_dir +1/-1, st_line), SuperTrend(10,3) computed on full ETH history, value known at that bar's close.
- `supertrend_daily.csv`: date, st15 direction at 09:30 (last ETH bar before open, usable pre-market), at 16:00, number of 15m flips between RTH 15m bar closes 09:45..16:00 (a flip on the first bar, 09:30->09:45, is not counted).
