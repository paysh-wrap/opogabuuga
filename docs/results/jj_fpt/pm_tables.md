
#### Full (2021-10..2026-10) (1266 days)

(1) NY_PM alone, 1 micro, after costs

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| NY_PM ALL signals | 4788 | 3.78 | 38.1 | 0.84 | -4.18 | -1.09 | -20028 |
| NY_PM sequential (max 1 open) | 2711 | 2.14 | 38.2 | 0.86 | -3.53 | -0.76 | -9561 |

NY_PM by entry kind (all signals):

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| CONTINUATION | 924 | 0.73 | 37.9 | 0.84 | -5.32 | -1.66 | -4918 |
| BREAK_OF_STRUCTURE | 1904 | 1.50 | 37.2 | 0.83 | -4.72 | -1.36 | -8988 |
| DISPLACEMENT | 1960 | 1.55 | 38.9 | 0.87 | -3.12 | -0.56 | -6122 |

NY_PM by tier (all signals):

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| BASE | 3063 | 2.42 | 38.5 | 0.86 | -4.38 | -1.19 | -13408 |
| BIG_OPEN | 62 | 0.05 | 38.7 | 0.83 | -10.48 | -4.24 | -650 |
| SMALL_ROOM | 1663 | 1.31 | 37.2 | 0.79 | -3.59 | -0.79 | -5970 |

(2) NY + NY_PM combined

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| NY alone, ALL signals | 4770 | 3.77 | 37.7 | 0.86 | -3.81 | -0.91 | -18188 |
| NY_PM alone, ALL signals | 4788 | 3.78 | 38.1 | 0.84 | -4.18 | -1.09 | -20028 |
| Combined, ALL signals | 9558 | 7.55 | 37.9 | 0.85 | -4.00 | -1.00 | -38216 |
| Combined, sequential, max 1 open across both | 6514 | 5.15 | 37.8 | 0.85 | -3.87 | -0.93 | -25191 |
|   of which NY_PM trades taken | 2710 | 2.14 | 38.2 | 0.87 | -3.51 | -0.75 | -9509 |

#### Last 12 months (2025-11..2026-10) (248 days)

(1) NY_PM alone, 1 micro, after costs

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| NY_PM ALL signals | 1028 | 4.15 | 39.3 | 0.89 | -3.07 | -0.53 | -3156 |
| NY_PM sequential (max 1 open) | 628 | 2.53 | 39.8 | 0.93 | -1.75 | 0.13 | -1098 |

NY_PM by entry kind (all signals):

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| CONTINUATION | 185 | 0.75 | 41.6 | 0.92 | -2.42 | -0.21 | -447 |
| BREAK_OF_STRUCTURE | 421 | 1.70 | 36.6 | 0.81 | -5.51 | -1.75 | -2320 |
| DISPLACEMENT | 422 | 1.70 | 41.0 | 0.96 | -0.92 | 0.54 | -389 |

NY_PM by tier (all signals):

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| BASE | 704 | 2.84 | 39.1 | 0.90 | -3.12 | -0.56 | -2193 |
| BIG_OPEN | 11 | 0.04 | 36.4 | 0.46 | -35.14 | -16.57 | -386 |
| SMALL_ROOM | 313 | 1.26 | 39.9 | 0.89 | -1.84 | 0.08 | -576 |

(2) NY + NY_PM combined

| | trades | /day | win % | PF | avg $/trade | avg pts | total $ |
|---|---|---|---|---|---|---|---|
| NY alone, ALL signals | 1120 | 4.52 | 38.1 | 0.88 | -3.37 | -0.69 | -3778 |
| NY_PM alone, ALL signals | 1028 | 4.15 | 39.3 | 0.89 | -3.07 | -0.53 | -3156 |
| Combined, ALL signals | 2148 | 8.66 | 38.7 | 0.89 | -3.23 | -0.61 | -6934 |
| Combined, sequential, max 1 open across both | 1590 | 6.41 | 38.6 | 0.90 | -2.90 | -0.45 | -4612 |
|   of which NY_PM trades taken | 628 | 2.53 | 39.8 | 0.93 | -1.75 | 0.13 | -1098 |

NY_PM signals total 4788; taken in the combined sequential run 2710 (rest blocked by a still-open NY position at 14:00+). NY signals still open at 16:00 are marked to market at the 16:00 close, i.e. they hold the single position through the PM window.

(3) Lucid Pro evaluation, NY + NY_PM combined (same sim and D143 sizing as above; max 1 open position across both sessions)

| Plan | period | starts | pass % | bust % | running at data end % | of which stalled % | median P&L of running $ | median days to pass | NY-only pass/bust for reference |
|---|---|---|---|---|---|---|---|---|---|
| Pro 25K | Full | 1266 | 2.8 | 0.0 | 97.2 | 95.3 | -759 | 12 | 5.2/0.0 |
| Pro 25K | Last 12m | 248 | 0.8 | 0.0 | 99.2 | 89.5 | -682 | 13 | 0.0/0.0 |
| Pro 50K | Full | 1266 | 3.2 | 0.0 | 96.8 | 94.2 | -1610 | 11 | 4.8/0.0 |
| Pro 50K | Last 12m | 248 | 0.8 | 0.0 | 99.2 | 85.5 | -1440 | 13 | 0.0/0.0 |
| Pro 100K | Full | 1266 | 1.7 | 0.0 | 98.3 | 95.6 | -2526 | 14 | 2.9/0.0 |
| Pro 100K | Last 12m | 248 | 0.0 | 0.0 | 100.0 | 86.3 | -2377 | - | 0.0/0.0 |
| Pro 150K | Full | 1266 | 1.7 | 0.0 | 98.3 | 95.6 | -3781 | 12 | 3.0/0.0 |
| Pro 150K | Last 12m | 248 | 0.0 | 0.0 | 100.0 | 86.3 | -3682 | - | 0.0/0.0 |
