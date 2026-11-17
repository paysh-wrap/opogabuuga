Window 2024-11-01..2026-10-30 (495 RTH days), last 12 months from 2025-11-01. 1 micro MNQ, $2/pt, cost $2.00 per round trip (fee + slippage both ways). IS = first 80% of days (2024-11-01..2026-06-10), OOS = last 20% (2026-06-11..2026-10-30). Default configs, nothing tuned. Samples under 100 trades are flagged **<100**. Max DD is the 2-year peak-to-trough of the 1-micro equity curve in trade order.

## GALA PRICE ACTION

How N is applied: input bars aggregated to N min (engine builds its own 5-min entry candles from them; first bar must close 09:31).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 2 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 3 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 5 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 10 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 15 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 30 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |

Skip codes for N > 1 (days): 2m: {'GALA_NO_OPEN': 3}, 3m: {'GALA_NO_OPEN': 3}, 5m: {'GALA_NO_OPEN': 3}, 10m: {'GALA_NO_OPEN': 3}, 15m: {'GALA_NO_OPEN': 3}, 30m: {'GALA_NO_OPEN': 3}

**Verdict GALA PRICE ACTION:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. no runnable bar size produced trades. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## CONTI ORB (default rr 1)

How N is applied: input bars aggregated to N min (first bar must close 09:31).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 3 **<100** | 33.3 | 0.50 | -17.83 | -54 | 107 | 0 | 0.00 | 0 | 3 **<100** | 0.50 | 0 **<100** | 0.00 |
| 2 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 3 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 5 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 10 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 15 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 30 min | NOT RUNNABLE | - | - | - | - | - | - | - | - | - | - | - | - | - |

Skip codes for N > 1 (days): 2m: {'CORB_NO_RANGE': 3}, 3m: {'CORB_NO_RANGE': 3}, 5m: {'CORB_NO_RANGE': 3}, 10m: {'CORB_NO_RANGE': 3}, 15m: {'CORB_NO_RANGE': 3}, 30m: {'CORB_NO_RANGE': 3}

**Verdict CONTI ORB (default rr 1):** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 0.50 on 3 trades) -> OOS PF 0.00 on 0 trades, 2y total $-54. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## CONTI VWAP

How N is applied: input bars aggregated to N min (volume summed).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 14 **<100** | 35.7 | 2.28 | 15.50 | 217 | 73 | 0 | 0.00 | 0 | 14 **<100** | 2.28 | 0 **<100** | 0.00 |
| 2 min | ran | 14 **<100** | 35.7 | 1.29 | 5.64 | 79 | 188 | 0 | 0.00 | 0 | 14 **<100** | 1.29 | 0 **<100** | 0.00 |
| 3 min | ran | 14 **<100** | 35.7 | 2.81 | 20.50 | 287 | 73 | 0 | 0.00 | 0 | 14 **<100** | 2.81 | 0 **<100** | 0.00 |
| 5 min | ran | 10 **<100** | 30.0 | 0.83 | -5.30 | -53 | 267 | 0 | 0.00 | 0 | 10 **<100** | 0.83 | 0 **<100** | 0.00 |
| 10 min | ran | 10 **<100** | 20.0 | 0.48 | -20.50 | -205 | 398 | 0 | 0.00 | 0 | 10 **<100** | 0.48 | 0 **<100** | 0.00 |
| 15 min | ran | 8 **<100** | 25.0 | 1.19 | 6.44 | 52 | 268 | 0 | 0.00 | 0 | 8 **<100** | 1.19 | 0 **<100** | 0.00 |
| 30 min | ran | 9 **<100** | 11.1 | 0.15 | -39.28 | -354 | 416 | 0 | 0.00 | 0 | 9 **<100** | 0.15 | 0 **<100** | 0.00 |

**Verdict CONTI VWAP:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 3 min (IS PF 2.81 on 14 trades) -> OOS PF 0.00 on 0 trades, 2y total $287. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## OKALA 8020 (base entries)

How N is applied: cfg.entry_minutes = N (validated 1..5; 10/15/30 set outside the bound; 10-min structure candles fixed).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran | 15 **<100** | 40.0 | 0.85 | -2.00 | -30 | 66 | 0 | 0.00 | 0 | 15 **<100** | 0.85 | 0 **<100** | 0.00 |
| 2 min | ran | 16 **<100** | 56.2 | 1.64 | 6.12 | 98 | 22 | 0 | 0.00 | 0 | 16 **<100** | 1.64 | 0 **<100** | 0.00 |
| 3 min | ran | 14 **<100** | 35.7 | 0.71 | -4.14 | -58 | 114 | 0 | 0.00 | 0 | 14 **<100** | 0.71 | 0 **<100** | 0.00 |
| 5 min | ran | 15 **<100** | 60.0 | 1.91 | 8.00 | 120 | 66 | 0 | 0.00 | 0 | 15 **<100** | 1.91 | 0 **<100** | 0.00 |
| 10 min (outside validated bound) | ran | 10 **<100** | 40.0 | 0.85 | -2.00 | -20 | 66 | 0 | 0.00 | 0 | 10 **<100** | 0.85 | 0 **<100** | 0.00 |
| 15 min (outside validated bound) | ran | 6 **<100** | 33.3 | 0.64 | -5.33 | -32 | 66 | 0 | 0.00 | 0 | 6 **<100** | 0.64 | 0 **<100** | 0.00 |
| 30 min (outside validated bound) | ran | 1 **<100** | 0.0 | 0.00 | -22.00 | -22 | 22 | 0 | 0.00 | 0 | 1 **<100** | 0.00 | 0 **<100** | 0.00 |

**Verdict OKALA 8020 (base entries):** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 5 min (IS PF 1.91 on 15 trades) -> OOS PF 0.00 on 0 trades, 2y total $120. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## BRUNI STRUCTURE

How N is applied: cfg.tf_minutes = N (validated bound is 15..15, every other N set outside the bound; entry trigger stays a 1-minute bar).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min (outside validated bound) | ran | 8 **<100** | 12.5 | 0.00 | -55.44 | -444 | 444 | 0 | 0.00 | 0 | 8 **<100** | 0.00 | 0 **<100** | 0.00 |
| 2 min (outside validated bound) | ran | 8 **<100** | 25.0 | 0.28 | -42.25 | -338 | 405 | 0 | 0.00 | 0 | 8 **<100** | 0.28 | 0 **<100** | 0.00 |
| 3 min (outside validated bound) | ran | 7 **<100** | 0.0 | 0.00 | -45.07 | -316 | 316 | 0 | 0.00 | 0 | 7 **<100** | 0.00 | 0 **<100** | 0.00 |
| 5 min (outside validated bound) | ran | 6 **<100** | 33.3 | 0.62 | -37.33 | -224 | 562 | 0 | 0.00 | 0 | 6 **<100** | 0.62 | 0 **<100** | 0.00 |
| 10 min (outside validated bound) | ran | 3 **<100** | 33.3 | 0.48 | -51.83 | -156 | 296 | 0 | 0.00 | 0 | 3 **<100** | 0.48 | 0 **<100** | 0.00 |
| 15 min | ran | 3 **<100** | 66.7 | 1.36 | 4.67 | 14 | 38 | 0 | 0.00 | 0 | 3 **<100** | 1.36 | 0 **<100** | 0.00 |
| 30 min | ran, 0 trades | 0 | | | | | | | | | | | | |

**Verdict BRUNI STRUCTURE:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 15 min (IS PF 1.36 on 3 trades) -> OOS PF 0.00 on 0 trades, 2y total $14. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## CANDACE ICT SCALP

How N is applied: input bars aggregated to N min (bar-count settings then span N times longer; the 09:31 gap-level feature needs a 1-minute first bar).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 2 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 3 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 5 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 10 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 15 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 30 min | ran, 0 trades | 0 | | | | | | | | | | | | |

**Verdict CANDACE ICT SCALP:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. no runnable bar size produced trades. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## AUCTION IMRE

How N is applied: input bars aggregated to N min (bar-count settings then span N times longer; estimated delta per N-min bar).

| bar | status | trades | win % | PF | avg $/trade | total $ | max DD $ | 12m trades | 12m PF | 12m $ | IS trades | IS PF | OOS trades | OOS PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 2 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 3 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 5 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 10 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 15 min | ran, 0 trades | 0 | | | | | | | | | | | | |
| 30 min | ran, 0 trades | 0 | | | | | | | | | | | | |

**Verdict AUCTION IMRE:** NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. no runnable bar size produced trades. (Choosing a timeframe after seeing these results is over-fitting; the in-sample-best line is the only honest pick.)

## One-line verdicts

- GALA PRICE ACTION: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. no runnable bar size produced trades.
- CONTI ORB (default rr 1): NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 1 min (IS PF 0.50 on 3 trades) -> OOS PF 0.00 on 0 trades, 2y total $-54.
- CONTI VWAP: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 3 min (IS PF 2.81 on 14 trades) -> OOS PF 0.00 on 0 trades, 2y total $287.
- OKALA 8020 (base entries): NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 5 min (IS PF 1.91 on 15 trades) -> OOS PF 0.00 on 0 trades, 2y total $120.
- BRUNI STRUCTURE: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. in-sample-best bar = 15 min (IS PF 1.36 on 3 trades) -> OOS PF 0.00 on 0 trades, 2y total $14.
- CANDACE ICT SCALP: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. no runnable bar size produced trades.
- AUCTION IMRE: NO timeframe is profitable (PF > 1) on both IS and OOS with >= 100 trades. no runnable bar size produced trades.
