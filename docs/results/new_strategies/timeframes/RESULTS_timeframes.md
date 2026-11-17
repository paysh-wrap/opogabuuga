# Timeframe sensitivity of the seven new strategies (MNQ, 1 micro, last 2 years)

Reuses the cached 5-year MNQ 1-minute RTH data and the harness of `../backtest_new.py` / `../backtest_okala_bruni_candace_imre.py` (costs, 1-micro stats, 80/20 IS/OOS cut). Engines called unchanged, all other settings at their defaults, nothing tuned. Script: `backtest_timeframes.py`; per-row CSV: `timeframes_summary.csv`; trade lists: `trades_<strategy>_<N>m.csv`. The Lucid-fit eval simulation is not repeated here (this is a 1-micro sensitivity test).

## How each timeframe is applied, and what is not runnable

- GALA, CONTI ORB: hard-wired to 1-minute bars. Both engines require the session's first bar to close at 09:31 (`gala_pa.replay_day`: `GALA_NO_OPEN`; `conti_orb.replay_day`: `CORB_NO_RANGE`). Fed 2/3/5/10/15/30-minute bars they return no plan on 495 of 495 days, so those sizes are recorded as NOT RUNNABLE (nothing was faked, e.g. by relabelling bar times). GALA has no timeframe setting: its 5-minute entry candles (and 1-hour planning candles) are built inside the engine, so its only runnable point is the native 1-minute input. ORB has no timeframe setting either.
- CONTI VWAP: bar-level logic with no 1-minute assumption; N-minute bars with summed volume run for every N.
- OKALA 8020: the engine's own `entry_minutes` field is set to N (bars stay 1-minute). The validator allows 1..5 only; 10/15/30 are set with `model_copy(update=...)` (no validation, engine untouched) and flagged "outside validated bound". The 10-minute structure candles are fixed. Default is 3 min; the 3-minute row here counts base entries only (adds excluded), so it differs slightly from the earlier report that included adds. 1-micro P&L = single bracket (TP1 15 pt, stop 10 pt), as in the earlier report.
- BRUNI: the engine's own `tf_minutes` is set to N (structure candles); the entry trigger remains a 1-minute bar. The validator pins it to 15, so every other N is outside the bound (flagged). The 15-minute row reproduces the earlier report (404 trades).
- CANDACE, IMRE: N-minute bars passed as the bar input (today + history). Their bar-count settings (displacement bars, micro-range bars, bubble window...) then cover N times more time, and CANDACE loses its 09:31 gap-level feature for N > 1 (needs a 1-minute first bar). These are semantics changes, not pure resolution changes; with few or zero trades above 2 minutes the result mostly says the setups depend on 1-minute detail.
- Verdict rule: a timeframe counts only if total trades >= 100 and profit factor > 1 on BOTH the in-sample 80% and the out-of-sample 20%. OOS samples are small (20% of 495 days = 99 days), so even a pass is weak evidence; PF 1.00 in the tables can be marginally above or below 1 (see the CSV, 3 decimals).

## GALA PRICE ACTION

How N is applied: input bars aggregated to N min (engine builds its own 5-min entry candles from them; first bar must close 09:31).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 6 **<100** | 66.7 | 2.10 | 32.58 | 196 | 157 | 2 | 2.88 | 38 | 6 **<100** | 2.10 | 0 **<100** | 0.00 |
| 2 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 3 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 5 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 10 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 15 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 30 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |

Skip codes for N > 1 (days): 2m: {'GALA_NO_OPEN': 495}, 3m: {'GALA_NO_OPEN': 495}, 5m: {'GALA_NO_OPEN': 495}, 10m: {'GALA_NO_OPEN': 495}, 15m: {'GALA_NO_OPEN': 495}, 30m: {'GALA_NO_OPEN': 495}

**Verdict GALA PRICE ACTION:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 2.10 on 6 trades) -> OOS PF 0.00 on 0 trades, 2y total $196. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## CONTI ORB (default rr 1)

How N is applied: input bars aggregated to N min (first bar must close 09:31).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 330 | 58.2 | 1.22 | 20.87 | 6888 | 4637 | 162 | 1.01 | 96 | 264 | 1.37 | 66 **<100** | 0.85 |
| 2 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 3 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 5 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 10 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 15 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 30 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |

Skip codes for N > 1 (days): 2m: {'CORB_NO_RANGE': 495}, 3m: {'CORB_NO_RANGE': 495}, 5m: {'CORB_NO_RANGE': 495}, 10m: {'CORB_NO_RANGE': 495}, 15m: {'CORB_NO_RANGE': 495}, 30m: {'CORB_NO_RANGE': 495}

**Verdict CONTI ORB (default rr 1):** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 1.37 on 264 trades) -> OOS PF 0.85 on 66 trades, 2y total $6888. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## CONTI VWAP

How N is applied: input bars aggregated to N min (volume summed).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 1855 | 23.0 | 1.06 | 1.67 | 3092 | 3126 | 913 | 1.06 | 1674 | 1488 | 1.04 | 367 | 1.13 |
| 2 min | ran | 1779 | 22.9 | 1.02 | 0.65 | 1153 | 3054 | 892 | 1.02 | 700 | 1422 | 1.03 | 357 | 1.00 |
| 3 min | ran | 1711 | 22.0 | 1.06 | 2.04 | 3484 | 3174 | 850 | 0.97 | -819 | 1373 | 1.10 | 338 | 0.94 |
| 5 min | ran | 1612 | 19.9 | 0.98 | -0.62 | -1001 | 7158 | 796 | 0.86 | -4143 | 1292 | 1.06 | 320 | 0.70 |
| 10 min | ran | 1475 | 20.0 | 0.99 | -0.24 | -356 | 4372 | 730 | 0.97 | -775 | 1183 | 1.03 | 292 | 0.86 |
| 15 min | ran | 1385 | 19.4 | 1.01 | 0.47 | 651 | 3228 | 695 | 1.00 | 103 | 1100 | 1.06 | 285 | 0.85 |
| 30 min | ran | 1182 | 18.2 | 0.92 | -3.41 | -4034 | 4512 | 590 | 0.90 | -2428 | 932 | 0.95 | 250 | 0.80 |

**Verdict CONTI VWAP:** YES, 1 min (n=1855, IS PF 1.04, OOS PF 1.13, 2y $3092), 2 min (n=1779, IS PF 1.03, OOS PF 1.00, 2y $1153). in-sample-best bar = 3 min (IS PF 1.10 on 1373 trades) -> OOS PF 0.94 on 338 trades, 2y total $3484. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## OKALA 8020 (base entries)

How N is applied: cfg.entry_minutes = N (validated 1..5; 10/15/30 set outside the bound; 10-min structure candles fixed).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 2209 | 34.2 | 0.66 | -4.89 | -10798 | 10962 | 1097 | 0.61 | -6284 | 1786 | 0.69 | 423 | 0.55 |
| 2 min | ran | 2169 | 35.2 | 0.69 | -4.39 | -9518 | 9684 | 1089 | 0.65 | -5608 | 1747 | 0.72 | 422 | 0.57 |
| 3 min | ran | 2135 | 36.2 | 0.72 | -3.92 | -8370 | 8426 | 1099 | 0.70 | -4678 | 1715 | 0.76 | 420 | 0.58 |
| 5 min | ran | 1927 | 35.9 | 0.71 | -4.04 | -7794 | 7960 | 1015 | 0.70 | -4380 | 1535 | 0.74 | 392 | 0.61 |
| 10 min (outside validated bound) | ran | 1251 | 36.2 | 0.72 | -3.89 | -4872 | 5068 | 645 | 0.74 | -2290 | 993 | 0.74 | 258 | 0.66 |
| 15 min (outside validated bound) | ran | 754 | 35.5 | 0.70 | -4.23 | -3188 | 3264 | 370 | 0.74 | -1340 | 601 | 0.71 | 153 | 0.67 |
| 30 min (outside validated bound) | ran | 321 | 33.6 | 0.65 | -5.18 | -1662 | 1964 | 174 | 0.64 | -928 | 245 | 0.66 | 76 **<100** | 0.59 |

**Verdict OKALA 8020 (base entries):** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 3 min (IS PF 0.76 on 1715 trades) -> OOS PF 0.58 on 420 trades, 2y total $-8370. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## BRUNI STRUCTURE

How N is applied: cfg.tf_minutes = N (validated bound is 15..15, every other N set outside the bound; entry trigger stays a 1-minute bar).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min (outside validated bound) | ran | 1717 | 32.1 | 0.88 | -7.99 | -13718 | 20381 | 843 | 0.76 | -15378 | 1392 | 0.88 | 325 | 0.86 |
| 2 min (outside validated bound) | ran | 1293 | 36.9 | 0.95 | -3.63 | -4692 | 10519 | 636 | 0.89 | -5830 | 1030 | 1.04 | 263 | 0.70 |
| 3 min (outside validated bound) | ran | 1096 | 37.7 | 1.00 | -0.15 | -164 | 4500 | 543 | 1.02 | 849 | 883 | 1.05 | 213 | 0.84 |
| 5 min (outside validated bound) | ran | 821 | 40.8 | 1.03 | 2.18 | 1791 | 7542 | 417 | 1.17 | 5514 | 656 | 1.07 | 165 | 0.91 |
| 10 min (outside validated bound) | ran | 514 | 38.9 | 1.04 | 2.79 | 1434 | 4024 | 255 | 1.07 | 1420 | 423 | 0.98 | 91 **<100** | 1.31 |
| 15 min | ran | 404 | 39.1 | 0.89 | -9.54 | -3854 | 7222 | 195 | 0.98 | -430 | 336 | 0.89 | 68 **<100** | 0.91 |
| 30 min (outside validated bound) | ran | 281 | 38.8 | 0.72 | -32.96 | -9262 | 12050 | 119 | 0.81 | -3086 | 238 | 0.70 | 43 **<100** | 0.86 |

**Verdict BRUNI STRUCTURE:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 5 min (IS PF 1.07 on 656 trades) -> OOS PF 0.91 on 165 trades, 2y total $1791. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## CANDACE ICT SCALP

How N is applied: input bars aggregated to N min (bar-count settings then span N times longer; the 09:31 gap-level feature needs a 1-minute first bar).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 32 **<100** | 46.9 | 2.47 | 38.75 | 1240 | 452 | 19 | 4.06 | 1102 | 26 **<100** | 2.54 | 6 **<100** | 2.24 |
| 2 min | ran | 11 **<100** | 54.5 | 2.10 | 30.41 | 334 | 174 | 5 | 3.51 | 374 | 9 **<100** | 1.75 | 2 **<100** | 3.34 |
| 3 min | ran | 1 **<100** | 0.0 | 0.00 | -52.00 | -52 | 52 | 1 | 0.00 | -52 | 1 **<100** | 0.00 | 0 **<100** | 0.00 |
| 5 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 10 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 15 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 30 min | ran, 0 trades | 0 | | | | | | | | | | | | |

**Verdict CANDACE ICT SCALP:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 2.54 on 26 trades) -> OOS PF 2.24 on 6 trades, 2y total $1240. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## AUCTION IMRE

How N is applied: input bars aggregated to N min (bar-count settings then span N times longer; estimated delta per N-min bar).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 43 **<100** | 18.6 | 0.30 | -20.03 | -862 | 862 | 9 | 0.10 | -316 | 42 **<100** | 0.31 | 1 **<100** | 0.00 |
| 2 min | ran | 4 **<100** | 25.0 | 0.16 | -52.38 | -210 | 210 | 0 | 0.00 | 0 | 4 **<100** | 0.16 | 0 **<100** | 0.00 |
| 3 min | ran | 1 **<100** | 0.0 | 0.00 | -146.50 | -146 | 146 | 0 | 0.00 | 0 | 1 **<100** | 0.00 | 0 **<100** | 0.00 |
| 5 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 10 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 15 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 30 min | ran, 0 trades | 0 | | | | | | | | | | | | |

**Verdict AUCTION IMRE:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 0.31 on 42 trades) -> OOS PF 0.00 on 1 trades, 2y total $-862. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## One-line verdicts

- GALA PRICE ACTION: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 2.10 on 6 trades) -> OOS PF 0.00 on 0 trades, 2y total $196.
- CONTI ORB (default rr 1): NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 1.37 on 264 trades) -> OOS PF 0.85 on 66 trades, 2y total $6888.
- CONTI VWAP: YES, 1 min (n=1855, IS PF 1.04, OOS PF 1.13, 2y $3092), 2 min (n=1779, IS PF 1.03, OOS PF 1.00, 2y $1153). in-sample-best bar = 3 min (IS PF 1.10 on 1373 trades) -> OOS PF 0.94 on 338 trades, 2y total $3484.
- OKALA 8020 (base entries): NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 3 min (IS PF 0.76 on 1715 trades) -> OOS PF 0.58 on 420 trades, 2y total $-8370.
- BRUNI STRUCTURE: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 5 min (IS PF 1.07 on 656 trades) -> OOS PF 0.91 on 165 trades, 2y total $1791.
- CANDACE ICT SCALP: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 2.54 on 26 trades) -> OOS PF 2.24 on 6 trades, 2y total $1240.
- AUCTION IMRE: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 0.31 on 42 trades) -> OOS PF 0.00 on 1 trades, 2y total $-862.
