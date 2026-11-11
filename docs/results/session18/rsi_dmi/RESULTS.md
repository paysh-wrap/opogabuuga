# Session 18 - Triple RSI / DMI / SuperTrend-15m and combinations (MNQ + MGC, last 12 months only)

Research only. Scripts: `lib.py` (loader/sim from smc.py, parametrised per market), `rsi_dmi.py` (`MKT=MNQ|MGC python3 -I rsi_dmi.py`), `report.py` (tables, combined). Per-trade streams + json in `out/`.
Source claims (lunefi.com, UNVERIFIED): Triple RSI 90% win; DMI Toolbox 64% win / PF 3.34 / 4% DD; SuperTrend 68% win.

## Method
- Data: cached Databento 1m only (no download): MNQ.v.0 and MGC.v.0, last 12 months 2025-11-06..2026-11-05 (indicators warmed up from 2025-09-01). **Pick on the first ~8 months (2025-11-06..2026-06-30), judge only on the last ~4 months (2026-07-01..2026-11-05) = walk-forward.** ONE YEAR IS A SMALL SAMPLE: judge windows hold 13-2,000 trades and ~85 sessions; the rolling eval estimate has only ~24 overlapping start dates, so PASS/BUST % are very noisy (steps of ~3.7%). Most "good" HO rows below are < 120 trades = noise-level evidence.
- MNQ: 1 micro, RTH 09:30-16:00, signal bar close 09:35-15:30 ET, flat 15:59, $1.00 fee RT + 1 tick slippage per fill, $250 risk cap (stop 4-124 pt). MGC: 1 micro gold, tick 0.10 = $1, 10 oz, fee $1.60 RT (plan yaml, VERIFY), 1 tick slippage, session 03:00-16:00 ET, flat 15:59, stop 1.6-25 pt ($250 cap). Same sim, closed bars, entry at next 1m open, stop-first in a bar, one position at a time.
- Eval: Lucid Pro 25K (target +1,250, $1,000 EOD trailing MLL, lock 25,100), rolling starts every 2nd day over the HO window ("roll PASS/BUST %", remainder = still OPEN at window end; "med days" = median days to pass). Combined = both markets' trades in one account (concatenated; order within a day not time-sorted).
- Variants. Entry on the bar a state turns on. Triple RSI = three Wilder RSIs (2,7,14) or (3,7,14): long when all < (10,30,40), short when all > (90,70,60). Exit "mr" = RSI(2) crosses 50 (or 15:55) with a 2xATR(14) stop; "1.5" = fixed 1.5R target with the 2xATR stop. DMI(14): long when +DI>-DI, ADX > 20 or 25 and rising (short mirrored); exit = DI flip (MAXPT stop) or 1.5R/2R. SuperTrend(10,3) 15m: flip entry; flip exit or stop=ST line with 1.5R/2R. D(i) vote: >=2 of {RSI state (oversold=long), ST15 dir, DMI15 dir} agree; D(ii) all 3 agree; D(iii) Triple-RSI signal only when ST15 and/or DMI15 direction agrees (pullback-in-trend). ST/DMI are the last closed 15m bar.
- IS-pick rule (fixed in advance): per family, highest IS PF with >= 30 IS trades, marked **PICK**. Random benchmark = same entries/stops/exits with random direction, 10 seeds (HO PF shown). NOISE preset C (same 12 months) from the session-17 stream.
- Claim check: Triple RSI with the mean-reversion exit does show a high win rate (MNQ 54-63%, MGC 57-67%) but HO PF is 0.76-1.02 - many small wins, few big losses, net loss after costs. Nothing reproduces 90% win; DMI wins 31-41% and loses; SuperTrend 15m flip wins 28-33% (the 68% claim is not seen).

## Key reading (details in tables below)

IS-picked variant per family, judged on the last ~4 months (full list of every variant incl. IS columns below):

| market / pick | HO trades | win% | PF | $/tr | net $ | maxDD $ | roll PASS/BUST % |
|---|---|---|---|---|---|---|---|
| MNQ NOISE preset C (baseline, 12 mo) | 51 | 51.0 | 1.76 | 57.38 | 2,926 | 977 | 100/0 (only ~24 starts; trades few) |
| MNQ A Triple RSI 5m mr | 364 | 56.9 | 0.76 | -11.13 | -4,051 | 5,105 | 0/100 |
| MNQ B DMI adx>20 15m flip | 99 | 39.4 | 0.85 | -17.94 | -1,776 | 4,904 | 3.7/96.3 |
| MNQ C SuperTrend 15m flip | 65 | 27.7 | 0.52 | -71.94 | -4,676 | 6,250 | 3.7/96.3 |
| MNQ D(i) vote>=2 15m mr | 132 | 48.5 | 0.78 | -8.83 | -1,165 | 2,056 | 0/100 |
| MNQ D(iii) RSI+ST15 5m 1.5R | 109 | 49.5 | 1.28 | 21.56 | 2,350 | 1,855 | 55.6/25.9 |
| MGC A Triple RSI(3,7,14) 15m mr | 190 | 66.8 | 1.02 | 0.95 | 181 | 1,275 | 22.2/66.7 |
| MGC B DMI adx>25 15m 1.5R | 142 | 38.7 | 0.80 | -19.19 | -2,724 | 3,266 | 63.0/37.0 (OPEN-heavy) |
| MGC C SuperTrend 15m flip | 110 | 32.7 | 0.59 | -48.75 | -5,362 | 6,148 | 0/100 |
| MGC D(i) vote>=2 5m 1.5R | 419 | 38.4 | 0.85 | -8.88 | -3,722 | 4,401 | 11.1/88.9 |
| MGC D(iii) RSI+DMI15 5m 1.5R | 14 | 28.6 | 0.37 | -59.04 | -827 | 1,136 | 0/25.9 |
| COMB A Triple RSI 15m mr | 272 | 62.9 | 0.90 | -5.76 | -1,566 | 4,162 | 3.7/96.3 |
| COMB D(i) vote>=2 15m mr | 410 | 53.2 | 0.94 | -1.91 | -783 | 2,056 | 37.0/63.0 |
| COMB D(ii)/(iii) all-3 5m 1.5R | 26 | 42.3 | 0.86 | -11.46 | -298 | 900 | 0/25.9 |

## Verdict (plain language)
- **None of the three indicators works alone**, on either market, after costs, on the held-out 4 months. Triple RSI gives a high win rate (57-67% with the mean-reversion exit) but the average loss is bigger than the average win: PF 0.75-1.02, i.e. at best break-even; with a fixed 1.5R target the win rate falls to 40-52% and results are a coin flip (MNQ 1.0-1.06, MGC 0.9-1.28, and the random-direction benchmark gives about the same PF - no proven edge). DMI and SuperTrend lose clearly (PF 0.5-0.9), and SuperTrend 15m with an ST-line stop is mostly filtered out by the $250 cap.
- **Combinations:** vote (>=2) and "all 3" do not rescue it (PF 0.77-1.05); all-3 on 5m produces only 13-26 trades in 4 months (too few to judge). The only strictly positive held-out rows are D(iii) "Triple RSI only when the 15m SuperTrend agrees" with a 1.5R exit: MNQ 5m (109 trades, PF 1.28, 49.5% win, but the IS PF was 0.95, so it was the least-bad IS row, not an IS winner), and MGC/combined 15m (18-22 trades, 72% win, PF 3-4, MGC IS PF 1.31 on 45 trades). Those are 4-22 months-worth-of-noise samples, not evidence.
- None of this approaches NOISE preset C (HO PF 1.76, 51 trades; session-17 full history PF 1.4) on an honest-pick basis, and the article numbers (90% / 64% PF 3.34 / 68%) are not reproduced. Do NOT add any of these as a strategy button. MGC is OFF in the plans anyway (information only).

## Combinations that could work (untested hypotheses; need >= 2-3 years of data, so only after Databento is unlocked)
1. **Triple RSI pullback inside a 15m SuperTrend trend, 1.5R target** (D(iii) RSI+ST15): the only family positive in HO on both markets; re-test on 2019-2026 MNQ with IS-pick/HO-judge before believing it. Use as a NOISE entry filter / pullback add-on, not stand-alone.
2. SuperTrend 15m direction (or DMI direction) as a **side filter for NOISE** (0-2 new params) - the smc study's hypothesis 1, still untested.
3. Triple RSI (mean reversion) only as an **exit/timing aid** or a "do not chase" guard inside NOISE, since its high win rate comes with PF ~1.
4. If gold is ever turned on: Triple RSI(3,7,14) 15m looked best on MGC (IS PF 1.21 -> HO 1.02, 67% win) but is basically break-even.

## Full tables (all variants; IS = first 8 months, HO = last ~4 months)

### MNQ (1 micro)
| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net $ | HO maxDD $ | roll PASS/BUST % | med days | random-dir HO PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A TriRSI(2, 7, 14) 1m exit=mr | 3438 | 0.89 | 1931 | 60.4 | 0.84 | -2.59 | -5,008 | 5,928 | 0.0/100.0 | - | 0.88 |
| A TriRSI(2, 7, 14) 1m exit=1.5 | 2092 | 0.93 | 1138 | 40.4 | 1.03 | 1.55 | 1,764 | 2,699 | 44.4/55.6 | 12 | 1.03 |
| A TriRSI(3, 7, 14) 1m exit=mr | 2321 | 0.88 | 1274 | 59.6 | 0.81 | -3.18 | -4,055 | 4,336 | 0.0/100.0 | - | 0.91 |
| A TriRSI(3, 7, 14) 1m exit=1.5 | 1723 | 0.93 | 943 | 40.5 | 1.01 | 0.52 | 493 | 2,340 | 44.4/55.6 | 20 | 1.0 |
| **PICK** A TriRSI(2, 7, 14) 5m exit=mr | 723 | 1.1 | 364 | 56.9 | 0.76 | -11.13 | -4,051 | 5,105 | 0.0/100.0 | - | 0.84 |
| A TriRSI(2, 7, 14) 5m exit=1.5 | 506 | 1.03 | 275 | 45.1 | 1.05 | 4.74 | 1,305 | 3,042 | 55.6/44.4 | 11 | 0.94 |
| A TriRSI(3, 7, 14) 5m exit=mr | 454 | 0.9 | 250 | 57.2 | 0.81 | -8.74 | -2,184 | 2,790 | 0.0/100.0 | - | 0.9 |
| A TriRSI(3, 7, 14) 5m exit=1.5 | 374 | 0.83 | 216 | 45.8 | 1.06 | 5.58 | 1,205 | 2,413 | 44.4/55.6 | 8 | 1.03 |
| A TriRSI(2, 7, 14) 15m exit=mr | 278 | 0.86 | 135 | 58.5 | 0.81 | -14.06 | -1,899 | 2,735 | 7.4/92.6 | 12 | 1.05 |
| A TriRSI(2, 7, 14) 15m exit=1.5 | 246 | 0.91 | 122 | 49.2 | 1.06 | 6.76 | 825 | 1,526 | 51.9/48.1 | 14 | 0.97 |
| A TriRSI(3, 7, 14) 15m exit=mr | 181 | 0.87 | 82 | 53.7 | 0.76 | -21.3 | -1,747 | 3,098 | 14.8/85.2 | 14 | 0.93 |
| A TriRSI(3, 7, 14) 15m exit=1.5 | 171 | 0.81 | 81 | 45.7 | 0.93 | -8.46 | -685 | 3,141 | 25.9/74.1 | 10 | 1.0 |
| B DMI adx>20 5m exit=flip | 360 | 1.12 | 194 | 35.1 | 0.9 | -9.19 | -1,783 | 3,988 | 37.0/63.0 | 10 | 0.97 |
| B DMI adx>20 5m exit=1.5 | 389 | 0.96 | 209 | 38.3 | 0.83 | -16.24 | -3,395 | 4,575 | 29.6/70.4 | 29 | 1.02 |
| B DMI adx>20 5m exit=2.0 | 367 | 0.97 | 197 | 34.0 | 0.81 | -19.43 | -3,828 | 5,180 | 11.1/88.9 | 8 | 1.02 |
| B DMI adx>25 5m exit=flip | 254 | 1.25 | 142 | 32.4 | 0.83 | -15.83 | -2,248 | 3,578 | 14.8/85.2 | 29 | 0.89 |
| B DMI adx>25 5m exit=1.5 | 310 | 0.89 | 163 | 37.4 | 0.73 | -28.28 | -4,609 | 5,410 | 0.0/100.0 | - | 0.88 |
| B DMI adx>25 5m exit=2.0 | 293 | 0.95 | 154 | 32.5 | 0.71 | -32.57 | -5,016 | 5,806 | 0.0/100.0 | - | 0.99 |
| **PICK** B DMI adx>20 15m exit=flip | 180 | 1.43 | 99 | 39.4 | 0.85 | -17.94 | -1,776 | 4,904 | 3.7/96.3 | 10 | 0.84 |
| B DMI adx>20 15m exit=1.5 | 210 | 1.19 | 106 | 38.7 | 0.75 | -29.82 | -3,161 | 4,120 | 0.0/100.0 | - | 0.92 |
| B DMI adx>20 15m exit=2.0 | 205 | 1.25 | 103 | 38.8 | 0.74 | -32.59 | -3,357 | 4,812 | 0.0/100.0 | - | 0.8 |
| B DMI adx>25 15m exit=flip | 146 | 1.41 | 79 | 32.9 | 0.8 | -25.85 | -2,042 | 4,972 | 0.0/100.0 | - | 0.9 |
| B DMI adx>25 15m exit=1.5 | 165 | 1.16 | 84 | 33.3 | 0.69 | -40.56 | -3,407 | 4,456 | 0.0/100.0 | - | 0.92 |
| B DMI adx>25 15m exit=2.0 | 160 | 1.19 | 82 | 31.7 | 0.62 | -50.44 | -4,136 | 5,579 | 0.0/100.0 | - | 0.82 |
| **PICK** C ST15m exit=flip | 128 | 0.88 | 65 | 27.7 | 0.52 | -71.94 | -4,676 | 6,250 | 3.7/96.3 | 11 | 0.79 |
| C ST15m exit=1.5 | 11 | 2.81 | 5 | 40.0 | 0.4 | -57.71 | -289 | 317 | 0.0/0.0 | - | - |
| C ST15m exit=2.0 | 11 | 2.49 | 5 | 40.0 | 0.4 | -57.71 | -289 | 317 | 0.0/0.0 | - | - |
| D(i) vote>=2 5m exit=mr | 430 | 1.07 | 235 | 55.3 | 0.77 | -8.18 | -1,921 | 2,770 | 0.0/100.0 | - | 1.02 |
| D(ii) all-3 5m exit=mr | 21 | 0.83 | 13 | 53.8 | 1.08 | 3.77 | 49 | 288 | 0.0/0.0 | - | 0.95 |
| D(iii) RSI+ST15 5m exit=mr | 221 | 0.89 | 128 | 57.8 | 0.87 | -5.29 | -677 | 1,203 | 0.0/37.0 | - | 0.93 |
| D(iii) RSI+DMI15 5m exit=mr | 23 | 0.92 | 13 | 53.8 | 1.08 | 3.77 | 49 | 288 | 0.0/0.0 | - | 1.15 |
| D(iii) RSI+ST15+DMI15 5m exit=mr | 21 | 0.83 | 13 | 53.8 | 1.08 | 3.77 | 49 | 288 | 0.0/0.0 | - | 0.95 |
| D(i) vote>=2 5m exit=1.5 | 348 | 1.07 | 180 | 42.8 | 0.98 | -1.43 | -257 | 2,807 | 40.7/59.3 | 18 | 1.04 |
| D(ii) all-3 5m exit=1.5 | 21 | 1.67 | 13 | 53.8 | 1.27 | 22.52 | 293 | 599 | 0.0/0.0 | - | 1.0 |
| **PICK** D(iii) RSI+ST15 5m exit=1.5 | 185 | 0.95 | 109 | 49.5 | 1.28 | 21.56 | 2,350 | 1,855 | 55.6/25.9 | 14 | 0.92 |
| D(iii) RSI+DMI15 5m exit=1.5 | 23 | 1.65 | 13 | 53.8 | 1.27 | 22.52 | 293 | 599 | 0.0/0.0 | - | 1.3 |
| D(iii) RSI+ST15+DMI15 5m exit=1.5 | 21 | 1.67 | 13 | 53.8 | 1.27 | 22.52 | 293 | 599 | 0.0/0.0 | - | 1.0 |
| **PICK** D(i) vote>=2 15m exit=mr | 265 | 1.18 | 132 | 48.5 | 0.78 | -8.83 | -1,165 | 2,056 | 0.0/100.0 | - | 1.11 |
| D(ii) all-3 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15 15m exit=mr | 18 | 0.69 | 4 | 100.0 | 99 | 33.0 | 132 | 0 | 0.0/0.0 | - | - |
| D(iii) RSI+DMI15 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15+DMI15 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(i) vote>=2 15m exit=1.5 | 213 | 1.08 | 98 | 39.8 | 0.78 | -25.91 | -2,539 | 3,499 | 0.0/100.0 | - | 0.88 |
| D(ii) all-3 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15 15m exit=1.5 | 18 | 0.82 | 4 | 75.0 | 1.33 | 20.88 | 84 | 250 | 0.0/0.0 | - | - |
| D(iii) RSI+DMI15 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15+DMI15 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| NOISE preset C (same 12 mo) | 98 | 1.41 | 51 | 51.0 | 1.76 | 57.38 | 2,926 | 977 | 100.0/0.0 | 48 | - |

### MGC (1 micro gold, info only - OFF in app plans)
| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net $ | HO maxDD $ | roll PASS/BUST % | med days | random-dir HO PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A TriRSI(2, 7, 14) 1m exit=mr | 7220 | 0.88 | 4173 | 56.9 | 0.75 | -2.94 | -12,258 | 12,409 | 0.0/100.0 | - | 0.7 |
| A TriRSI(2, 7, 14) 1m exit=1.5 | 4756 | 0.93 | 2763 | 40.4 | 0.9 | -2.87 | -7,938 | 9,019 | 3.7/96.3 | 5 | 0.89 |
| A TriRSI(3, 7, 14) 1m exit=mr | 4681 | 0.87 | 2769 | 57.5 | 0.79 | -2.47 | -6,839 | 6,977 | 0.0/100.0 | - | 0.74 |
| A TriRSI(3, 7, 14) 1m exit=1.5 | 3808 | 0.91 | 2223 | 40.4 | 0.88 | -3.42 | -7,599 | 8,625 | 0.0/100.0 | - | 0.86 |
| A TriRSI(2, 7, 14) 5m exit=mr | 1455 | 0.97 | 852 | 62.3 | 0.9 | -2.55 | -2,177 | 3,882 | 0.0/96.3 | - | 0.85 |
| A TriRSI(2, 7, 14) 5m exit=1.5 | 1012 | 0.99 | 566 | 41.2 | 0.92 | -4.68 | -2,650 | 5,462 | 3.7/96.3 | 16 | 0.94 |
| A TriRSI(3, 7, 14) 5m exit=mr | 978 | 1.03 | 574 | 65.2 | 1.01 | 0.32 | 183 | 1,943 | 7.4/85.2 | 42 | 0.84 |
| A TriRSI(3, 7, 14) 5m exit=1.5 | 804 | 1.09 | 448 | 45.5 | 1.11 | 6.13 | 2,747 | 3,066 | 44.4/55.6 | 18 | 0.99 |
| A TriRSI(2, 7, 14) 15m exit=mr | 482 | 1.16 | 273 | 63.4 | 0.96 | -1.46 | -399 | 1,556 | 3.7/81.5 | 6 | 0.94 |
| A TriRSI(2, 7, 14) 15m exit=1.5 | 409 | 1.1 | 222 | 49.5 | 1.18 | 14.69 | 3,260 | 2,660 | 22.2/77.8 | 12 | 0.94 |
| **PICK** A TriRSI(3, 7, 14) 15m exit=mr | 311 | 1.21 | 190 | 66.8 | 1.02 | 0.95 | 181 | 1,275 | 22.2/66.7 | 34 | 0.94 |
| A TriRSI(3, 7, 14) 15m exit=1.5 | 289 | 1.16 | 177 | 52.0 | 1.28 | 22.05 | 3,902 | 2,671 | 7.4/92.6 | 10 | 1.0 |
| B DMI adx>20 5m exit=flip | 683 | 0.73 | 402 | 35.3 | 1.04 | 1.79 | 721 | 4,648 | 74.1/25.9 | 14 | 0.97 |
| B DMI adx>20 5m exit=1.5 | 767 | 0.92 | 460 | 40.9 | 0.91 | -5.42 | -2,494 | 4,267 | 40.7/59.3 | 13 | 0.91 |
| B DMI adx>20 5m exit=2.0 | 716 | 0.95 | 411 | 36.0 | 0.91 | -6.15 | -2,527 | 5,380 | 18.5/81.5 | 6 | 0.95 |
| B DMI adx>25 5m exit=flip | 463 | 0.74 | 281 | 36.3 | 0.9 | -5.69 | -1,599 | 3,498 | 3.7/96.3 | 4 | 0.99 |
| B DMI adx>25 5m exit=1.5 | 561 | 0.88 | 337 | 40.9 | 0.89 | -7.1 | -2,393 | 4,302 | 0.0/100.0 | - | 1.01 |
| B DMI adx>25 5m exit=2.0 | 517 | 0.86 | 304 | 37.5 | 0.96 | -2.84 | -865 | 3,384 | 22.2/77.8 | 8 | 0.92 |
| B DMI adx>20 15m exit=flip | 302 | 0.81 | 165 | 30.9 | 0.91 | -8.32 | -1,372 | 4,912 | 63.0/37.0 | 9 | 0.98 |
| B DMI adx>20 15m exit=1.5 | 346 | 0.86 | 192 | 37.0 | 0.81 | -17.8 | -3,418 | 4,368 | 29.6/70.4 | 9 | 0.89 |
| B DMI adx>20 15m exit=2.0 | 324 | 0.87 | 181 | 34.3 | 0.85 | -14.22 | -2,574 | 4,739 | 66.7/33.3 | 16 | 0.84 |
| B DMI adx>25 15m exit=flip | 223 | 0.89 | 116 | 33.6 | 0.89 | -10.95 | -1,271 | 3,116 | 63.0/37.0 | 10 | 1.03 |
| **PICK** B DMI adx>25 15m exit=1.5 | 258 | 0.98 | 142 | 38.7 | 0.8 | -19.19 | -2,724 | 3,266 | 63.0/37.0 | 23 | 0.86 |
| B DMI adx>25 15m exit=2.0 | 250 | 0.98 | 134 | 37.3 | 0.88 | -11.8 | -1,581 | 3,057 | 66.7/33.3 | 17 | 1.03 |
| **PICK** C ST15m exit=flip | 192 | 0.84 | 110 | 32.7 | 0.59 | -48.75 | -5,362 | 6,148 | 0.0/100.0 | - | 0.93 |
| C ST15m exit=1.5 | 26 | 1.01 | 34 | 38.2 | 1.03 | 2.99 | 102 | 1,092 | 0.0/55.6 | - | 1.12 |
| C ST15m exit=2.0 | 26 | 0.88 | 32 | 31.2 | 0.64 | -42.6 | -1,363 | 1,978 | 0.0/59.3 | - | 0.85 |
| D(i) vote>=2 5m exit=mr | 965 | 0.85 | 590 | 60.2 | 0.99 | -0.18 | -104 | 995 | 0.0/0.0 | - | 0.77 |
| D(ii) all-3 5m exit=mr | 29 | 1.39 | 13 | 30.8 | 0.28 | -33.78 | -439 | 556 | 0.0/0.0 | - | 1.69 |
| D(iii) RSI+ST15 5m exit=mr | 571 | 0.94 | 356 | 63.8 | 0.91 | -1.87 | -665 | 1,495 | 0.0/29.6 | - | 0.79 |
| D(iii) RSI+DMI15 5m exit=mr | 32 | 1.49 | 14 | 28.6 | 0.2 | -48.22 | -675 | 792 | 0.0/0.0 | - | 0.86 |
| D(iii) RSI+ST15+DMI15 5m exit=mr | 29 | 1.39 | 13 | 30.8 | 0.28 | -33.78 | -439 | 556 | 0.0/0.0 | - | 1.69 |
| **PICK** D(i) vote>=2 5m exit=1.5 | 736 | 1.02 | 419 | 38.4 | 0.85 | -8.88 | -3,722 | 4,401 | 11.1/88.9 | 17 | 0.92 |
| D(ii) all-3 5m exit=1.5 | 29 | 1.53 | 13 | 30.8 | 0.45 | -45.44 | -591 | 900 | 0.0/0.0 | - | 1.05 |
| D(iii) RSI+ST15 5m exit=1.5 | 453 | 1.09 | 255 | 36.9 | 0.79 | -12.5 | -3,188 | 4,104 | 0.0/100.0 | - | 0.9 |
| **PICK** D(iii) RSI+DMI15 5m exit=1.5 | 32 | 1.51 | 14 | 28.6 | 0.37 | -59.04 | -827 | 1,136 | 0.0/25.9 | - | 1.03 |
| D(iii) RSI+ST15+DMI15 5m exit=1.5 | 29 | 1.53 | 13 | 30.8 | 0.45 | -45.44 | -591 | 900 | 0.0/0.0 | - | 1.05 |
| D(i) vote>=2 15m exit=mr | 484 | 0.98 | 278 | 55.4 | 1.05 | 1.38 | 382 | 1,707 | 66.7/33.3 | 30 | 0.97 |
| D(ii) all-3 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15 15m exit=mr | 46 | 1.29 | 19 | 57.9 | 1.77 | 14.22 | 270 | 161 | 0.0/0.0 | - | 1.25 |
| D(iii) RSI+DMI15 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15+DMI15 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(i) vote>=2 15m exit=1.5 | 355 | 0.93 | 196 | 39.8 | 0.9 | -9.02 | -1,768 | 2,955 | 37.0/63.0 | 10 | 0.91 |
| D(ii) all-3 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15 15m exit=1.5 | 45 | 1.31 | 18 | 72.2 | 4.16 | 104.53 | 1,881 | 162 | 63.0/0.0 | 40 | 0.81 |
| D(iii) RSI+DMI15 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15+DMI15 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |

### MNQ + MGC combined (one account trades both, concatenated streams)
| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net $ | HO maxDD $ | roll PASS/BUST % | med days | random-dir HO PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A TriRSI(2, 7, 14) 1m exit=mr | 10658 | 0.88 | 6104 | 58.0 | 0.79 | -2.83 | -17,265 | 17,994 | 0.0/100.0 | - | - |
| A TriRSI(2, 7, 14) 1m exit=1.5 | 6848 | 0.93 | 3901 | 40.4 | 0.95 | -1.58 | -6,173 | 10,318 | 18.5/81.5 | 3 | - |
| A TriRSI(3, 7, 14) 1m exit=mr | 7002 | 0.88 | 4043 | 58.2 | 0.8 | -2.69 | -10,894 | 11,230 | 0.0/100.0 | - | - |
| A TriRSI(3, 7, 14) 1m exit=1.5 | 5531 | 0.92 | 3166 | 40.5 | 0.93 | -2.24 | -7,106 | 10,093 | 3.7/96.3 | 4 | - |
| A TriRSI(2, 7, 14) 5m exit=mr | 2178 | 1.02 | 1216 | 60.7 | 0.83 | -5.12 | -6,228 | 7,635 | 0.0/100.0 | - | - |
| A TriRSI(2, 7, 14) 5m exit=1.5 | 1518 | 1.0 | 841 | 42.4 | 0.98 | -1.6 | -1,346 | 7,164 | 14.8/85.2 | 7 | - |
| A TriRSI(3, 7, 14) 5m exit=mr | 1432 | 0.98 | 824 | 62.7 | 0.92 | -2.43 | -2,001 | 3,916 | 0.0/100.0 | - | - |
| A TriRSI(3, 7, 14) 5m exit=1.5 | 1178 | 1.0 | 664 | 45.6 | 1.09 | 5.95 | 3,952 | 3,066 | 25.9/74.1 | 7 | - |
| A TriRSI(2, 7, 14) 15m exit=mr | 760 | 1.04 | 408 | 61.8 | 0.89 | -5.63 | -2,297 | 4,121 | 14.8/85.2 | 11 | - |
| A TriRSI(2, 7, 14) 15m exit=1.5 | 655 | 1.03 | 344 | 49.4 | 1.13 | 11.88 | 4,085 | 2,660 | 40.7/59.3 | 6 | - |
| **PICK** A TriRSI(3, 7, 14) 15m exit=mr | 492 | 1.08 | 272 | 62.9 | 0.9 | -5.76 | -1,566 | 4,162 | 3.7/96.3 | 10 | - |
| A TriRSI(3, 7, 14) 15m exit=1.5 | 460 | 1.02 | 258 | 50.0 | 1.14 | 12.47 | 3,217 | 4,486 | 25.9/74.1 | 8 | - |
| B DMI adx>20 5m exit=flip | 1043 | 0.86 | 596 | 35.2 | 0.97 | -1.78 | -1,062 | 4,648 | 25.9/74.1 | 3 | - |
| B DMI adx>20 5m exit=1.5 | 1156 | 0.94 | 669 | 40.1 | 0.88 | -8.8 | -5,889 | 7,957 | 11.1/88.9 | 5 | - |
| B DMI adx>20 5m exit=2.0 | 1083 | 0.96 | 608 | 35.4 | 0.87 | -10.45 | -6,356 | 9,158 | 14.8/85.2 | 3 | - |
| B DMI adx>25 5m exit=flip | 717 | 0.91 | 423 | 35.0 | 0.87 | -9.09 | -3,847 | 5,107 | 7.4/92.6 | 6 | - |
| B DMI adx>25 5m exit=1.5 | 871 | 0.89 | 500 | 39.8 | 0.82 | -14.01 | -7,003 | 8,745 | 3.7/96.3 | 6 | - |
| B DMI adx>25 5m exit=2.0 | 810 | 0.89 | 458 | 35.8 | 0.85 | -12.84 | -5,880 | 7,135 | 14.8/85.2 | 4 | - |
| B DMI adx>20 15m exit=flip | 482 | 1.02 | 264 | 34.1 | 0.89 | -11.93 | -3,149 | 4,912 | 44.4/55.6 | 7 | - |
| B DMI adx>20 15m exit=1.5 | 556 | 0.97 | 298 | 37.6 | 0.78 | -22.08 | -6,579 | 7,241 | 18.5/81.5 | 6 | - |
| B DMI adx>20 15m exit=2.0 | 529 | 0.99 | 284 | 35.9 | 0.8 | -20.88 | -5,931 | 6,896 | 14.8/85.2 | 5 | - |
| **PICK** B DMI adx>25 15m exit=flip | 369 | 1.07 | 195 | 33.3 | 0.85 | -16.99 | -3,313 | 5,354 | 37.0/63.0 | 6 | - |
| B DMI adx>25 15m exit=1.5 | 423 | 1.04 | 226 | 36.7 | 0.75 | -27.13 | -6,131 | 6,619 | 11.1/88.9 | 4 | - |
| B DMI adx>25 15m exit=2.0 | 410 | 1.05 | 216 | 35.2 | 0.76 | -26.47 | -5,717 | 6,878 | 14.8/85.2 | 4 | - |
| C ST15m exit=flip | 320 | 0.85 | 175 | 30.9 | 0.56 | -57.36 | -10,038 | 10,951 | 0.0/100.0 | - | - |
| **PICK** C ST15m exit=1.5 | 37 | 1.34 | 39 | 38.5 | 0.95 | -4.8 | -187 | 1,092 | 0.0/59.3 | - | - |
| C ST15m exit=2.0 | 37 | 1.15 | 37 | 32.4 | 0.61 | -44.64 | -1,652 | 2,294 | 0.0/59.3 | - | - |
| D(i) vote>=2 5m exit=mr | 1395 | 0.92 | 825 | 58.8 | 0.9 | -2.45 | -2,025 | 2,770 | 0.0/100.0 | - | - |
| D(ii) all-3 5m exit=mr | 50 | 1.04 | 26 | 42.3 | 0.69 | -15.01 | -390 | 714 | 0.0/0.0 | - | - |
| D(iii) RSI+ST15 5m exit=mr | 792 | 0.92 | 484 | 62.2 | 0.9 | -2.77 | -1,342 | 1,751 | 0.0/100.0 | - | - |
| D(iii) RSI+DMI15 5m exit=mr | 55 | 1.15 | 27 | 40.7 | 0.58 | -23.19 | -626 | 950 | 0.0/0.0 | - | - |
| D(iii) RSI+ST15+DMI15 5m exit=mr | 50 | 1.04 | 26 | 42.3 | 0.69 | -15.01 | -390 | 714 | 0.0/0.0 | - | - |
| D(i) vote>=2 5m exit=1.5 | 1084 | 1.04 | 599 | 39.7 | 0.91 | -6.64 | -3,978 | 5,888 | 0.0/100.0 | - | - |
| **PICK** D(ii) all-3 5m exit=1.5 | 50 | 1.59 | 26 | 42.3 | 0.86 | -11.46 | -298 | 900 | 0.0/25.9 | - | - |
| D(iii) RSI+ST15 5m exit=1.5 | 638 | 1.04 | 364 | 40.7 | 0.96 | -2.3 | -837 | 4,271 | 11.1/88.9 | 9 | - |
| D(iii) RSI+DMI15 5m exit=1.5 | 55 | 1.57 | 27 | 40.7 | 0.78 | -19.77 | -534 | 1,136 | 0.0/25.9 | - | - |
| **PICK** D(iii) RSI+ST15+DMI15 5m exit=1.5 | 50 | 1.59 | 26 | 42.3 | 0.86 | -11.46 | -298 | 900 | 0.0/25.9 | - | - |
| **PICK** D(i) vote>=2 15m exit=mr | 749 | 1.05 | 410 | 53.2 | 0.94 | -1.91 | -783 | 2,056 | 37.0/63.0 | 25 | - |
| D(ii) all-3 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15 15m exit=mr | 64 | 1.08 | 23 | 65.2 | 2.15 | 17.49 | 402 | 161 | 0.0/0.0 | - | - |
| D(iii) RSI+DMI15 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15+DMI15 15m exit=mr | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(i) vote>=2 15m exit=1.5 | 568 | 0.98 | 294 | 39.8 | 0.85 | -14.65 | -4,307 | 5,029 | 33.3/66.7 | 13 | - |
| D(ii) all-3 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15 15m exit=1.5 | 63 | 1.18 | 22 | 72.7 | 3.33 | 89.32 | 1,965 | 250 | 70.4/0.0 | 30 | - |
| D(iii) RSI+DMI15 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |
| D(iii) RSI+ST15+DMI15 15m exit=1.5 | 0 | - | 0 | - | - | - | - | - | - | - | - |