# Session 18 - "New ICT strategy" study (Silver Bullet: sweep -> MSS -> FVG retrace), MNQ 1-minute, 1 micro

Research only. Files only under docs/results/session18/new_ict/. No app code, no git, no download (cached Databento MNQ.v.0 1-minute file from session 17; Databento is locked).
Reproduce: `PYTHONPATH=. python3 run_grid.py; python3 grid2.py; python3 final.py; python3 extra.py` (needs numpy + pandas; `lib.py` holds all logic; `sim.py`/streams are reused read-only from session17/noise_sharpen).

## 1. What was tested
- **Windows (ET)**: AM Silver Bullet 10:00-11:00, PM 14:00-15:00, London 03:00-04:00 (note: Lucid trades RTH mostly; the London trades are flat by 05:00 ET, so they would be an overnight-session extra, not RTH), each alone and combined (AM+PM, ALL3). Setups only form inside the window; time exit 60 min after the window end (sensitivity 0/30/60/120 below).
- **Sequence** (closed bars only, no look-ahead): (1) sweep = bar trades beyond a liquidity level and closes back inside (prior-day RTH high/low, overnight/session high/low since 18:00, and - "all" level set - unexceeded 5-bar swings of the last 2 h); a bar that CLOSES beyond the level counts as acceptance and consumes the level; (2) MSS = within 25 bars a close beyond the last opposing 3-bar swing that formed before the sweep, with displacement (a body in the last 3 bars >= 1.0 x ATR14 of 1m; variant 0.5); (3) most recent 3-candle FVG in the displacement direction (1m or 5m candles) -> limit order at the FVG midpoint ("mid") or the near edge ("near"), valid 30 bars, dead if the stop level trades first.
- **Stop** = sweep extreme +- 1 tick. **Targets** 1.5R, 2R, or "liq" = nearest opposing liquidity (prior-day/session/5-bar swing) at >= 1.5R (cap 4R; no such level = skip). Skip if risk > $250 per micro (the NOISE emergency-stop size) or stop < 6 pts.
- **Variants**: FVG size (gap/ATR14 >= 0 / 0.5 / 1 / 2), HTF bias (prior-day direction, 15m EMA20 side, 1H EMA20 side, combinations), max 1 or 2 trades/day, FVG on 1m or 5m, two level sets, two displacement thresholds, mid/near entry. Full grid = 11,520 rows (`grid.csv`), 5 window sets.
- **Costs**: $1.00 RT fee; 1 tick slippage on stop and time exits; a limit entry and a TP both need 1 tick of penetration to fill (conservative); stop first within a bar; no TP check on the fill bar.
- **Eval simulation** = the exact session-17 `sim.py` (Pro 25K: +$1,250 target, $1,000 EOD-trailing MLL locking at 25,100, bust = dead account, 120-session rolling starts / 10-day-block bootstrap / strict MAE variant). Days with no trade count as sessions, so low-frequency strategies (about 0.3-0.5 trades/day here vs about 0.6 for NOISE) often end the 120 sessions "open" - the **boot** column (500-session cap) is the fairer PASS/BUST read for them.
- **Not tested**: order-flow confirmation (delta, footprint, absorption, DOM) - needs tick/L2 data and the Databento account is locked. Everything here is price-only ICT.
- **Protocol**: pick in-sample 2019-05..2023-12, judge only held-out 2024-01..2026-11. Rows marked DEF = canonical untuned configuration fixed before looking at results; PICK = best IS (rule: IS n>=100, IS PF>=1.15, max 2*mean/sd^2) per window set; EXP = post-hoc, shown for information only.

## 2. Verdict in one paragraph (details below)
Nothing here is proven. The untuned strategy is roughly break-even over the whole 7.5 years (AM+PM: IS -$5.1/trade PF 0.84, held-out +$9.2/trade PF 1.23, all-years t-stat 0.04) and its sign flips between years (2023 deeply negative, 2025 positive) - that is a coin-flip signature, not an edge. London (03:00-04:00) is clearly negative held-out (t = -2.6). Every IS-picked "best" combination LOST on held-out data (only 9.5% of the 84 IS-eligible grid rows had HO PF > 1; median HO PF 0.84). The random-entry benchmark with identical stops/targets/windows loses about $5-10 per trade, so the ICT entry is better than random timing and direction held-out  (random benchmark was run held-out only), but "better than random" is not "profitable" and NOISE preset C (+$27/trade, PF 1.43, 60% eval PASS) is far ahead of everything here.

## 3. Main table (held-out 2024-01..2026-11, 1 micro)
Columns eval: roll = rolling 120-session starts, boot = block bootstrap (500 sessions), strict = rolling with MAE-based bust; PASS/BUST in %; remainder is "open". Days to pass = median business days of the rolling passes.

| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | eval roll PASS/BUST % | days to pass (med) | boot PASS/BUST % | strict PASS/BUST % | IS trades / $/tr / PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (baseline, 427 HO trades) | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60 / 39 | 46 | 62 / 38 | 51 / 48 | 722 / 16.8 / 1.38 |
| [DEF] AM 1m-FVG mid 2R (untuned) | 112 | 42.0 | 4.2 | 476 | 1,755 | 1.09 | 2 / 14 | 113 | 28 / 50 | 2 / 16 | 201 / -8.0 / 0.78 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 112.0 | 36.2 | -5.9 | -664 | 1,670 | 0.90 | 2 / 9 | - | - | - | - |
| [DEF] PM 1m-FVG mid 2R (untuned) | 143 | 42.7 | 7.4 | 1,064 | 1,047 | 1.22 | 0 / 0 | - | 43 / 15 | 0 / 2 | 227 / -3.1 / 0.89 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 143.0 | 32.0 | -5.0 | -710 | 1,770 | 0.90 | 1 / 4 | - | - | - | - |
| [DEF] LON 1m-FVG mid 2R (untuned) | 162 | 31.5 | -11.1 | -1,801 | 2,059 | 0.61 | 0 / 0 | - | 0 / 80 | 0 / 0 | 213 / 1.4 / 1.08 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 162.0 | 34.0 | -3.9 | -636 | 1,148 | 0.85 | 0 / 0 | - | - | - | - |
| [DEF] AM+PM 1m-FVG mid 2R (untuned) | 230 | 43.9 | 9.2 | 2,116 | 1,802 | 1.23 | 24 / 25 | 90 | 59 / 36 | 24 / 26 | 396 / -5.1 / 0.84 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 230.0 | 33.4 | -9.8 | -2,244 | 3,057 | 0.80 | 1 / 29 | - | - | - | - |
| [DEF] ALL3 1m-FVG mid 2R (untuned) | 339 | 38.6 | 1.4 | 481 | 2,411 | 1.04 | 9 / 32 | 77 | 36 / 61 | 9 / 35 | 532 / -1.9 / 0.93 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 339.0 | 33.5 | -6.4 | -2,178 | 3,054 | 0.84 | 3 / 34 | - | - | - | - |
| [DEF] PM 1m-FVG mid 1.5R (untuned) | 143 | 46.9 | 4.4 | 622 | 1,114 | 1.13 | 0 / 3 | - | 26 / 17 | 0 / 3 | 227 / -2.8 / 0.90 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 143.0 | 37.8 | -4.0 | -572 | 1,602 | 0.92 | 0 / 3 | - | - | - | - |
| [DEF] AM+PM 1m-FVG mid 1.5R (untuned) | 230 | 47.0 | 4.3 | 984 | 1,883 | 1.11 | 20 / 29 | 98 | 44 / 50 | 20 / 35 | 396 / -3.5 / 0.89 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 230.0 | 38.6 | -8.1 | -1,863 | 2,714 | 0.83 | 1 / 24 | - | - | - | - |
| [DEF] ALL3 1m-FVG mid 1.5R (untuned) | 339 | 43.1 | 0.3 | 118 | 2,228 | 1.01 | 3 / 27 | 104 | 31 / 62 | 3 / 32 | 532 / -0.2 / 0.99 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 339.0 | 38.9 | -5.0 | -1,708 | 2,742 | 0.87 | 3 / 26 | - | - | - | - |
| [DEF] ALL3 5m-FVG mid 2R (untuned) | 126 | 43.7 | 6.4 | 810 | 834 | 1.18 | 5 / 0 | 108 | 32 / 20 | 5 / 0 | 182 / 0.6 / 1.02 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 126.0 | 35.9 | -6.0 | -759 | 1,581 | 0.86 | 1 / 4 | - | - | - | - |
| [DEF] ALL3 1m-FVG mid liq-target (untuned) | 298 | 34.6 | -2.9 | -856 | 2,009 | 0.92 | 5 / 44 | 81 | 19 / 76 | 5 / 48 | 467 / -3.7 / 0.86 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 298.0 | 32.9 | -6.2 | -1,861 | 2,693 | 0.83 | 1 / 22 | - | - | - | - |
| [DEF] PM 1m mid 2R, max 2/day (untuned) | 153 | 43.1 | 7.9 | 1,206 | 882 | 1.23 | 1 / 0 | 104 | 46 / 14 | 1 / 0 | 246 / -4.0 / 0.87 |
| [PICK] IS-pick ALL3: 5m all d0.5 near liqR md1 bias 1h gap>=0.0 | 80 | 38.8 | -7.1 | -566 | 844 | 0.82 | 0 / 0 | - | 2 / 36 | 0 / 0 | 115 / 12.3 / 1.53 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 80.0 | 34.6 | -5.8 | -466 | 1,132 | 0.88 | 1 / 0 | - | - | - | - |
| [PICK] IS-pick AM+PM: 5m all d1.0 near liqR md1 bias - gap>=0.0 | 74 | 37.8 | -8.1 | -602 | 1,338 | 0.83 | 0 / 0 | - | 5 / 48 | 0 / 0 | 101 / 5.8 / 1.19 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 74.0 | 37.5 | 0.9 | 65 | 1,028 | 1.04 | 0 / 1 | - | - | - | - |
| [PICK] IS-pick LON: 1m all d1.0 mid 1.5R md1 bias 1h gap>=0.0 | 84 | 36.9 | -5.8 | -483 | 546 | 0.77 | 0 / 0 | - | 0 / 7 | 0 / 0 | 118 / 8.6 / 1.57 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 84.0 | 39.5 | -3.1 | -259 | 645 | 0.89 | 0 / 0 | - | - | - | - |
| [PICK] IS-pick PM: 1m all d1.0 mid 1.5R md2 bias pd gap>=0.0 | 70 | 48.6 | 12.2 | 857 | 512 | 1.40 | 0 / 0 | - | 24 / 4 | 0 / 0 | 116 / 4.0 / 1.17 |
| &nbsp;&nbsp;random-entry, same exits (20 seeds mean) | 70.0 | 39.2 | -3.2 | -227 | 1,022 | 0.96 | 0 / 1 | - | - | - | - |
| [EXP] EXP ALL3 1m mid 1.5R + 1H bias + gap>=0.5ATR (2nd IS rank) | 86 | 48.8 | 16.2 | 1,391 | 891 | 1.57 | 0 / 0 | - | 38 / 2 | 0 / 0 | 118 / 8.2 / 1.35 |
| [EXP] EXP PM 1m mid 2R + prior-day bias | 69 | 43.5 | 15.5 | 1,071 | 410 | 1.48 | 0 / 0 | - | 32 / 3 | 0 / 0 | 113 / 3.0 / 1.11 |
| [EXP] EXP AM+PM 1m mid 2R + 1H bias | 121 | 43.8 | 9.7 | 1,171 | 1,894 | 1.24 | 12 / 14 | 100 | 49 / 27 | 12 / 14 | 202 / -7.6 / 0.78 |

(random-entry rows: random direction, random minute in the same window, market entry +1 tick, the real trade's stop distance and day, same TP multiple (2R for liq rows), same time exit, 20 seeds averaged.)

## 4. Reading the table
- Over the full 7.5 years the untuned sets are at best break-even (see t-stats in section 5). The held-out profits of PM / AM+PM (+$1.1k / +$2.1k over 2.8 y) come with IS losses of about the same size; both eras together are about $0.
- Random entry with the same exits loses -$4 to -$10 per trade, so the sweep+MSS+FVG filter does add something relative to arbitrary timing, but the lift (about +$10-20/trade) is the same size as the noise: IS and HO disagree in sign on every untuned set (London flips the other way: IS +, HO -).
- Eval-sim: the best untuned sets (AM+PM boot PASS 59% / BUST 36% at 2R, 5m-FVG ALL3 boot 32% / 20% at only 126 trades) never beat NOISE preset C (boot 62% / 38%, 427 trades, +$27/trade) and rest on 20-30 HO passes of an under-sampled path (only ~230 HO trades in 2.8 years: ~1 trade per 3 days).
- Selection failed: IS-picks (IS PF 1.17-1.57) went to HO PF 0.77-0.83 in 3 of 4 window sets; the one that held (PM, bias prior-day, 1.5R, max 2/day: IS PF 1.17 / HO 1.40, 70 trades) is a single row out of 84 eligible and its IS edge is marginal. The post-hoc 'EXP ALL3 1H-bias + gap>=0.5 ATR, 1.5R' (HO PF 1.57, 86 trades, boot 38/2) is the 2nd IS rank - chosen after seeing HO, so it is a hypothesis only.
- Order-flow confirmation (the usual ICT add-on) could not be tested - no tick data. It could in principle improve the FVG-entry quality, but nothing here shows what it would add.

## 5. Extra tables (post-hoc, all untuned-config slices; IS vs HO shown so the flips are visible)
### per-year, untuned 2R, 1m-FVG, all levels (n / $/trade / PF)
| year | AM | PM | LON | AM+PM | ALL3 |
|---|---|---|---|---|---|
| 2019 | 25 / 4.6 / 1.37 | 19 / 3.3 / 1.23 | 12 / -3.7 / 0.63 | 43 / 4.9 / 1.38 | 49 / 5.0 / 1.44 |
| 2020 | 39 / 6.2 / 1.26 | 48 / -0.3 / 0.99 | 43 / 10.5 / 1.61 | 84 / 1.7 / 1.07 | 113 / 4.5 / 1.20 |
| 2021 | 48 / 3.1 / 1.10 | 51 / -1.0 / 0.96 | 37 / 6.1 / 1.42 | 89 / 5.2 / 1.20 | 111 / 7.0 / 1.34 |
| 2022 | 42 / -20.7 / 0.64 | 50 / 12.1 / 1.34 | 65 / -1.4 / 0.94 | 82 / -7.1 / 0.85 | 126 / -5.0 / 0.86 |
| 2023 | 47 / -26.5 / 0.45 | 59 / -21.9 / 0.37 | 56 / -4.2 / 0.75 | 98 / -23.1 / 0.43 | 133 / -14.5 / 0.54 |
| 2024 | 38 / -12.0 / 0.75 | 46 / 4.3 / 1.15 | 61 / -11.8 / 0.45 | 75 / -3.3 / 0.92 | 118 / -11.6 / 0.64 |
| 2025 | 39 / 25.6 / 1.60 | 55 / 13.3 / 1.41 | 45 / -1.0 / 0.96 | 84 / 21.8 / 1.60 | 113 / 18.2 / 1.61 |
| 2026 | 35 / -1.9 / 0.97 | 42 / 3.2 / 1.07 | 56 / -18.5 / 0.50 | 71 / 7.4 / 1.16 | 108 / -1.9 / 0.95 |

### mean $/trade t-statistic (untuned 2R)
| set | IS t | HO t | ALL t |
|---|---|---|---|
| AM | -1.44 | 0.36 | -0.65 |
| PM | -0.62 | 0.90 | 0.23 |
| LON | 0.42 | -2.57 | -1.47 |
| AM+PM | -1.33 | 1.22 | 0.04 |
| ALL3 | -0.68 | 0.28 | -0.24 |

### time-exit sensitivity (untuned AM+PM 1m mid 2R; hold = minutes after window end)
| hold | IS n/$tr/PF | HO n/$tr/PF/net |
|---|---|---|
| 0 | 351/-5.1/0.79 | 202/6.4/1.22/1,292 |
| 30 | 396/-4.6/0.84 | 230/5.9/1.17/1,368 |
| 60 | 396/-5.1/0.84 | 230/9.2/1.23/2,116 |
| 120 | 396/-6.6/0.81 | 230/6.1/1.14/1,398 |

### FVG size filter (gap / ATR14) and HTF bias on AM+PM untuned 2R (IS | HO: n, $/trade, PF)
| filter | IS | HO |
|---|---|---|
| none | 396, -5.1, 0.84 | 230, 9.2, 1.23 |
| gap>=0.5 | 167, -5.8, 0.83 | 92, 25.4, 1.76 |
| gap>=1 | 47, -0.6, 0.98 | 19, 51.2, 2.42 |
| gap>=2 | 3, -30.5, 0.31 | 3, 13.0, 1.22 |
| bias prior-day | 198, -7.5, 0.78 | 123, 12.1, 1.30 |
| bias 15m | 211, -13.0, 0.64 | 122, 11.1, 1.27 |
| bias 1H | 202, -7.6, 0.78 | 121, 9.7, 1.24 |
| bias pd+1H | 111, -12.0, 0.66 | 64, 8.1, 1.19 |
| max 2/day | 446, -7.2, 0.79 | 268, 10.1, 1.26 |

## 6. Plain-language verdict
ICT Silver Bullet as specified (sweep -> structure shift -> FVG retrace, price-only) does **not** have a demonstrated edge on MNQ. Untuned it is near zero; it only looks good in some years/windows (2025, PM) and bad in others (2023, London). Held-out profits of the NY windows are offset by in-sample losses, tuning on 2019-2023 did not carry over to 2024-2026, the London window is outright negative held-out, and 5m FVGs or liquidity targets do not rescue it. It is also low-frequency (~0.3-0.5 trades/day), so a 25K eval would take many months and the variance is large. It should NOT be built into the app as a live strategy on this evidence. If wanted at all: SHADOW/paper only, NY PM (14:00-15:00) first, never London for a Lucid RTH account.

## 7. Combinations that could work (hypotheses to paper-test, not proven)
1. **PM window only (14:00-15:00), 1m FVG, mid entry, 1.5-2R, prior-day-direction bias, max 1-2 trades/day**: HO PF 1.2-1.5 (n 69-153), IS PF 0.9-1.17 - weak but never clearly negative; the only family positive in both eras at PF >= 1.1 when the prior-day bias is added.
2. **Larger FVGs only (gap >= 0.5 x ATR14) in the NY windows**: IS PF 0.83, HO PF 1.76 (n 92) - direction of the filter is plausible (displacement quality) but the IS edge is absent, so it needs a fresh out-of-sample period.
3. **1H-trend bias + gap >= 0.5 ATR, 1.5R, all windows**: IS PF 1.35 -> HO PF 1.57 (n 118 / 86), the only IS-ranked row that held; it was 2nd by the IS rule, so treat as one lucky survivor of ~84.
4. **As a NOISE add-on / filter** (not a separate strategy): use sweep+MSS context only to veto NOISE entries - untested, would need its own study.
Anything above should first run in SHADOW for >= 60 sessions; with ~0.3 trades/day that is only ~20 trades - too few to prove anything, so the honest expectation is "not provable within a Lucid eval timeline".
