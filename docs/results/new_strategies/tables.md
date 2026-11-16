Data: 1266 RTH days 2021-10-01..2026-10-30 cached; backtest window 2024-11-01..2026-10-30 (495 days), last 12 months from 2025-11-01 (248 days). Costs per micro round trip: fee $1.00 + 1 tick slippage/side = $2.00; $2/pt. VWAP volume recovered from the stored VWAP: 5 of 493740 bars imputed (0.00%), max |recovered VWAP - stored VWAP| = 0.0000 pt. 0 NaN minutes filled flat.
In-sample / out-of-sample split (Conti A5): first 80% of the 495 days = 2024-11-01..2026-06-10 (IS), last 20% = 2026-06-11..2026-10-30 (OOS). Rules frozen, default configs, no tuning.

## GALA PRICE ACTION (defaults)

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 6 (<100: too small) | 0.01 | 66.7 | 2.10 | 46.2% | 32.58 | 196 | 157 |
| kind = BREAK_RETEST | 4 (<100: too small) | 0.01 | 75.0 | 6.93 | 82.4% | 30.38 | 122 | 20 |
| kind = BOUNCE | 1 (<100: too small) | 0.00 | 100.0 | inf | 194.9% | 231.00 | 231 | 0 |
| kind = REJECTION | 1 (<100: too small) | 0.00 | 0.0 | 0.00 | -100.0% | -157.00 | -157 | 157 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 2 (<100: too small) | 0.01 | 50.0 | 2.88 | 72.6% | 19.25 | 38 | 20 |
| kind = BREAK_RETEST | 2 (<100: too small) | 0.01 | 50.0 | 2.88 | 72.6% | 19.25 | 38 | 20 |

**Per quarter (1 micro)**

| quarter | trades | win % | PF | total $ |
|---|---|---|---|---|
| 2024-Q4 | 0 | | | |
| 2025-Q1 | 0 | | | |
| 2025-Q2 | 2 | 50.0 | 1.47 | 74 |
| 2025-Q3 | 1 | 100.0 | inf | 53 |
| 2025-Q4 | 3 | 66.7 | 4.34 | 68 |
| 2026-Q1 | 0 | | | |
| 2026-Q2 | 0 | | | |
| 2026-Q3 | 0 | | | |
| 2026-Q4 | 0 | | | |

**Lucid Pro EOD evaluation, Lucid-fit sizing (lucid_fit.trade_risk_usd + contracts_for, divisor 3), rolling start every trading day; trades in the window only**

| Plan | starts from | starts | pass % | bust % | running at end % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | 92 | - |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | 0 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | 300 | - |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | 0 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | 411 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | 0 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 0.0 | 0.0 | 100.0 | 96.2 | 616 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.0 | 0.0 | 100.0 | 92.3 | 0 | - |

## CONTI ORB rr 1 (default)

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 330 | 0.67 | 58.2 | 1.22 | 6.2% | 20.87 | 6888 | 4637 |
| exit_kind = TP | 86 (<100: too small) | 0.17 | 100.0 | inf | 98.7% | 293.67 | 25256 | 0 |
| exit_kind = STOP | 78 (<100: too small) | 0.16 | 0.0 | 0.00 | -100.0% | -318.42 | -24836 | 24836 |
| exit_kind = TIME | 166 | 0.34 | 63.9 | 2.01 | 10.8% | 38.97 | 6469 | 1182 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 162 | 0.65 | 53.1 | 1.01 | 0.1% | 0.59 | 96 | 4637 |
| exit_kind = TP | 34 (<100: too small) | 0.14 | 100.0 | inf | 98.8% | 341.03 | 11595 | 0 |
| exit_kind = STOP | 36 (<100: too small) | 0.15 | 0.0 | 0.00 | -100.0% | -390.44 | -14056 | 14056 |
| exit_kind = TIME | 92 (<100: too small) | 0.37 | 56.5 | 1.51 | 6.6% | 27.79 | 2556 | 1182 |

**In-sample (80%) vs out-of-sample (20%), 1 micro**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 264 | 0.67 | 61.4 | 1.37 | 10.0% | 31.06 | 8200 | 2274 |
| OUT-OF-SAMPLE | 66 (<100: too small) | 0.67 | 45.5 | 0.85 | -4.6% | -19.88 | -1312 | 3524 |

**Monte Carlo, 5,000 runs on the 330 2-year trades, 1 micro** (final P&L $, max drawdown $, longest losing streak = consecutive losing trades)

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th pct |
|---|---|---|---|---|---|---|
| reshuffle | 6888 | 6888 | 100 | 3316 | 5352 | 6 / 9 |
| resample | 6887 | -1074 | 92 | 3338 | 6520 | 6 / 9 |

**Lucid Pro EOD evaluation, Lucid-fit sizing (lucid_fit.trade_risk_usd + contracts_for, divisor 1), rolling start every trading day; trades in the window only**

| Plan | starts from | starts | pass % | bust % | running at end % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 54.9 | 0.0 | 45.1 | 0.0 | -30 | 126 |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 10.1 | 0.0 | 89.9 | 0.0 | -30 | 104 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 42.6 | 0.0 | 57.4 | 40.0 | -226 | 93 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 8.5 | 0.0 | 91.5 | 56.9 | -172 | 228 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 33.1 | 0.0 | 66.9 | 45.9 | 26 | 114 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.0 | 0.0 | 100.0 | 58.1 | 70 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 32.7 | 0.0 | 67.3 | 49.9 | 120 | 78 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.0 | 0.0 | 100.0 | 65.3 | -109 | - |

## CONTI ORB rr 2

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 330 | 0.67 | 54.8 | 1.09 | 2.7% | 9.11 | 3008 | 4637 |
| exit_kind = TP | 8 (<100: too small) | 0.02 | 100.0 | inf | 197.8% | 548.88 | 4391 | 0 |
| exit_kind = STOP | 83 (<100: too small) | 0.17 | 0.0 | 0.00 | -100.0% | -311.95 | -25892 | 25892 |
| exit_kind = TIME | 239 | 0.48 | 72.4 | 4.73 | 29.7% | 102.54 | 24508 | 572 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 162 | 0.65 | 50.6 | 0.92 | -2.3% | -9.18 | -1488 | 4637 |
| exit_kind = TP | 2 (<100: too small) | 0.01 | 100.0 | inf | 197.1% | 402.00 | 804 | 0 |
| exit_kind = STOP | 38 (<100: too small) | 0.15 | 0.0 | 0.00 | -100.0% | -381.59 | -14500 | 14500 |
| exit_kind = TIME | 122 | 0.49 | 65.6 | 3.42 | 24.6% | 100.07 | 12209 | 572 |

**In-sample (80%) vs out-of-sample (20%), 1 micro**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 264 | 0.67 | 58.0 | 1.23 | 6.5% | 20.40 | 5386 | 1841 |
| OUT-OF-SAMPLE | 66 (<100: too small) | 0.67 | 42.4 | 0.74 | -8.4% | -36.03 | -2378 | 3524 |

**Monte Carlo, 5,000 runs on the 330 2-year trades, 1 micro** (final P&L $, max drawdown $, longest losing streak = consecutive losing trades)

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th pct |
|---|---|---|---|---|---|---|
| reshuffle | 3008 | 3008 | 100 | 4188 | 6526 | 7 / 10 |
| resample | 3014 | -5146 | 73 | 4206 | 8628 | 7 / 10 |

**Lucid Pro EOD evaluation, Lucid-fit sizing (lucid_fit.trade_risk_usd + contracts_for, divisor 1), rolling start every trading day; trades in the window only**

| Plan | starts from | starts | pass % | bust % | running at end % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 49.5 | 0.0 | 50.5 | 25.9 | -348 | 131 |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 8.5 | 0.0 | 91.5 | 42.3 | -348 | 105 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 21.0 | 0.0 | 79.0 | 67.3 | -978 | 88 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 0.0 | 0.0 | 100.0 | 76.6 | -1082 | - |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 25.5 | 0.0 | 74.5 | 63.6 | -1472 | 154 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 0.0 | 0.0 | 100.0 | 78.2 | -1741 | - |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 22.2 | 0.0 | 77.8 | 67.1 | -2148 | 184 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 0.0 | 0.0 | 100.0 | 78.6 | -2488 | - |

## CONTI VWAP (defaults)

**2-year window (495 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 1855 | 3.75 | 23.0 | 1.06 | 3.2% | 1.67 | 3092 | 3126 |
| kind = LONG | 936 | 1.89 | 22.4 | 1.03 | 1.7% | 0.87 | 814 | 2062 |
| kind = SHORT | 919 | 1.86 | 23.6 | 1.09 | 4.8% | 2.48 | 2278 | 2034 |

**Last 12 months (248 days), 1 micro after costs**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL | 913 | 3.68 | 21.8 | 1.06 | 3.5% | 1.83 | 1674 | 3126 |
| kind = LONG | 462 | 1.86 | 20.3 | 0.93 | -4.3% | -2.25 | -1038 | 2062 |
| kind = SHORT | 451 | 1.82 | 23.3 | 1.20 | 11.6% | 6.01 | 2712 | 2034 |

**VWAP by exit kind (2-year)**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| exit = CROSS | 1127 | 2.28 | 29.4 | 1.05 | 1.4% | 0.73 | 824 | 1864 |
| exit = STOP | 632 | 1.28 | 0.0 | 0.00 | -100.0% | -52.00 | -32864 | 32864 |
| exit = TIME | 16 (<100: too small) | 0.03 | 100.0 | inf | 395.8% | 205.81 | 3293 | 0 |
| exit = TP | 80 (<100: too small) | 0.16 | 100.0 | inf | 765.4% | 398.00 | 31840 | 0 |

**D139-strict (a reversal on the exit bar is skipped, 2-year)**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| ALL strict | 1130 | 2.28 | 23.4 | 1.06 | 3.2% | 1.66 | 1880 | 3202 |
| skipped same-bar reversals | 725 | 1.46 | 22.5 | 1.06 | 3.2% | 1.67 | 1212 | 2920 |

**In-sample (80%) vs out-of-sample (20%), 1 micro**

| | trades | /day | win % | PF | expectancy per $ risked | avg $/trade | total $ | max DD $ |
|---|---|---|---|---|---|---|---|---|
| IN-SAMPLE | 1488 | 3.76 | 23.3 | 1.04 | 2.1% | 1.08 | 1604 | 2252 |
| OUT-OF-SAMPLE | 367 | 3.71 | 22.1 | 1.13 | 7.8% | 4.06 | 1488 | 1758 |

**Monte Carlo, 5,000 runs on the 1855 2-year trades, 1 micro** (final P&L $, max drawdown $, longest losing streak = consecutive losing trades)

| method | median final $ | 5th-pct final $ | % runs > 0 | median max DD $ | 95th-pct max DD $ | longest losing streak median / 95th pct |
|---|---|---|---|---|---|---|
| reshuffle | 3092 | 3092 | 100 | 3447 | 5428 | 24 / 33 |
| resample | 2962 | -3336 | 77 | 3554 | 6854 | 24 / 33 |

**Lucid Pro EOD evaluation, Lucid-fit sizing (lucid_fit.trade_risk_usd + contracts_for, divisor 3), rolling start every trading day; trades in the window only**

| Plan | starts from | starts | pass % | bust % | running at end % | of which stalled % | median P&L of running $ | median days to pass |
|---|---|---|---|---|---|---|---|---|
| Pro 25K (target $1250, MLL $1000, DLL $600) | 2y | 495 | 10.5 | 0.0 | 89.5 | 82.4 | -474 | 14 |
| Pro 25K (target $1250, MLL $1000, DLL $600) | L12m | 248 | 14.9 | 0.0 | 85.1 | 71.0 | -528 | 16 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | 2y | 495 | 10.7 | 0.0 | 89.3 | 81.8 | -932 | 15 |
| Pro 50K (target $3000, MLL $2000, DLL $1200) | L12m | 248 | 15.3 | 0.0 | 84.7 | 69.8 | -971 | 17 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | 2y | 495 | 9.3 | 0.0 | 90.7 | 83.2 | -1526 | 19 |
| Pro 100K (target $6000, MLL $3000, DLL $1800) | L12m | 248 | 14.1 | 0.0 | 85.9 | 71.0 | -1808 | 21 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | 2y | 495 | 9.1 | 0.0 | 90.9 | 82.8 | -2187 | 19 |
| Pro 150K (target $9000, MLL $4500, DLL $2700) | L12m | 248 | 14.1 | 0.0 | 85.9 | 69.8 | -2421 | 21 |
