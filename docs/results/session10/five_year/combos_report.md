# Agent B: MNQ 5y combination study (1 micro, 2021-11-01 to 2026-10-30, 1245 sessions)

Verification: my time-recording copies of NOISE, OPEN_DRIVE, PM_FADE reproduce the originals exactly (NOISE 810 trades all-period / total $18951; OPEN_DRIVE 178 / $1641; PM_FADE(START 2021-11-01) 488 / $6225); trade-by-trade pnl identical.

Overlap rule: sorted by entry bar per day; a trade is dropped if it enters before the previous kept trade exits (greedy, earlier entry wins). OVERNIGHT never overlaps. PM_FADE is generated only on days NOISE-alone did not trade (original definition). Sim: sim25k Pro, eval no DLL, funded DLL $600, rolling starts every 2 days; Halves sims run on the half's dates only.

## Headline (whole period)

| Set | trades | /day | win% | $/trade | total $ | PF | maxDD $ | worst day $ | dropped (overlap) |
|---|---|---|---|---|---|---|---|---|---|
| NOISE | 793 | 0.64 | 45.3% | 23.44 | 18588 | 1.35 | -2214 | -774 | 0 |
| OPEN_DRIVE | 173 | 0.14 | 57.2% | 8.38 | 1449 | 1.16 | -1104 | -281 | 0 |
| PM_FADE | 488 | 0.39 | 53.3% | 12.76 | 6225 | 1.26 | -1862 | -617 | 0 |
| OVERNIGHT | 1016 | 0.82 | 43.6% | -5.44 | -5532 | 0.88 | -5912 | -330 | 0 |
| NOISE+OPEN_DRIVE | 846 | 0.68 | 46.3% | 23.11 | 19553 | 1.35 | -2411 | -774 | 120 |
| NOISE+PM_FADE | 1281 | 1.03 | 48.3% | 19.37 | 24813 | 1.32 | -2914 | -774 | 0 |
| NOISE+OD+PM | 1334 | 1.07 | 48.9% | 19.32 | 25778 | 1.32 | -3141 | -774 | 120 |
| NOISE+OD+PM+OVN | 2350 | 1.89 | 46.6% | 8.62 | 20246 | 1.16 | -3341 | -755 | 120 |

## Per-year total $ (PF)  [2021 = Nov-Dec only, 2026 = Jan-Oct]

| Set | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| NOISE | 10 (1.01) | 4988 (1.46) | 3308 (1.44) | 2956 (1.29) | 5300 (1.50) | 2026 (1.16) |
| OPEN_DRIVE | -66 (0.81) LOSS | -82 (0.95) LOSS | 142 (1.13) | 653 (1.49) | 386 (1.18) | 415 (1.16) |
| PM_FADE | 69 (1.12) | -287 (0.96) LOSS | 1042 (1.33) | 1984 (1.60) | 165 (1.02) | 3252 (1.89) |
| OVERNIGHT | -524 (0.62) LOSS | -2435 (0.70) LOSS | -2514 (0.61) LOSS | 928 (1.16) | 682 (1.08) | -1669 (0.88) LOSS |
| NOISE+OPEN_DRIVE | 17 (1.01) | 5219 (1.47) | 3529 (1.45) | 3394 (1.32) | 5825 (1.53) | 1570 (1.11) |
| NOISE+PM_FADE | 79 (1.04) | 4701 (1.27) | 4350 (1.41) | 4940 (1.36) | 5465 (1.31) | 5278 (1.32) |
| NOISE+OD+PM | 86 (1.04) | 4932 (1.28) | 4570 (1.41) | 5378 (1.39) | 5990 (1.33) | 4822 (1.27) |
| NOISE+OD+PM+OVN | -438 (0.87) LOSS | 2497 (1.10) | 2056 (1.12) | 6306 (1.32) | 6672 (1.25) | 3153 (1.10) |

## Halves

| Set | H1 trades | H1 win% | H1 $/tr | H1 total $ | H1 PF | H1 maxDD | H2 trades | H2 win% | H2 $/tr | H2 total $ | H2 PF | H2 maxDD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE | 357 | 45.4% | 23.27 | 8306 | 1.42 | -1267 | 436 | 45.2% | 23.58 | 10282 | 1.31 | -2214 |
| OPEN_DRIVE | 66 | 54.5% | -0.08 | -5 | 1.00 | -817 | 107 | 58.9% | 13.60 | 1455 | 1.24 | -1104 |
| PM_FADE | 207 | 48.8% | 3.98 | 824 | 1.08 | -1862 | 281 | 56.6% | 19.22 | 5401 | 1.39 | -1850 |
| OVERNIGHT | 448 | 37.3% | -12.22 | -5473 | 0.66 | -5907 | 568 | 48.6% | -0.10 | -59 | 1.00 | -3751 |
| NOISE+OPEN_DRIVE | 377 | 46.4% | 23.25 | 8764 | 1.43 | -1260 | 469 | 46.3% | 23.00 | 10789 | 1.30 | -2411 |
| NOISE+PM_FADE | 564 | 46.6% | 16.19 | 9130 | 1.30 | -1467 | 717 | 49.7% | 21.87 | 15683 | 1.33 | -2914 |
| NOISE+OD+PM | 584 | 47.3% | 16.42 | 9588 | 1.31 | -1460 | 750 | 50.1% | 21.59 | 16190 | 1.33 | -3141 |
| NOISE+OD+PM+OVN | 1032 | 42.9% | 3.99 | 4115 | 1.09 | -2195 | 1318 | 49.5% | 12.24 | 16131 | 1.21 | -3341 |

## Pro 25K sim

| Set | period | eval pass | bust | median eval days | >=1 payout | avg paid $ | value/eval $ | funded n |
|---|---|---|---|---|---|---|---|---|
| NOISE | 5y | 57.0% | 35.7% | 44 | 63.0% | 880 | 502 | 357 |
| NOISE | H1 | 63.9% | 15.6% | 51 | 75.2% | 1240 | 792 | 101 |
| NOISE | H2 | 55.1% | 42.6% | 38 | 52.4% | 726 | 400 | 189 |
| OPEN_DRIVE | 5y | 0.3% | 8.2% | 83 | 0.0% | 0 | 0 | 2 |
| OPEN_DRIVE | H1 | 0.0% | 0.0% | nan | 0.0% | 0 | 0 | 0 |
| OPEN_DRIVE | H2 | 0.3% | 14.6% | 45 | 0.0% | 0 | 0 | 1 |
| PM_FADE | 5y | 24.8% | 16.7% | 63 | 1.4% | 8 | 2 | 74 |
| PM_FADE | H1 | 3.8% | 17.9% | 116 | 0.0% | 0 | 0 | 0 |
| PM_FADE | H2 | 42.0% | 17.1% | 59 | 3.1% | 31 | 13 | 65 |
| OVERNIGHT | 5y | 13.6% | 51.5% | 66 | 1.2% | 6 | 1 | 86 |
| OVERNIGHT | H1 | 0.0% | 73.8% | nan | 0.0% | 0 | 0 | 0 |
| OVERNIGHT | H2 | 23.4% | 37.4% | 62 | 1.2% | 6 | 1 | 82 |
| NOISE+OPEN_DRIVE | 5y | 58.1% | 35.9% | 42 | 64.4% | 1007 | 585 | 365 |
| NOISE+OPEN_DRIVE | H1 | 64.6% | 16.0% | 49 | 75.9% | 1584 | 1024 | 108 |
| NOISE+OPEN_DRIVE | H2 | 57.7% | 41.7% | 36 | 48.7% | 727 | 419 | 199 |
| NOISE+PM_FADE | 5y | 62.1% | 37.3% | 35 | 64.8% | 1745 | 1083 | 366 |
| NOISE+PM_FADE | H1 | 73.8% | 20.9% | 42 | 59.5% | 1756 | 1295 | 148 |
| NOISE+PM_FADE | H2 | 56.6% | 42.0% | 28 | 61.0% | 1788 | 1011 | 172 |
| NOISE+OD+PM | 5y | 62.7% | 36.7% | 33 | 64.8% | 1802 | 1130 | 372 |
| NOISE+OD+PM | H1 | 74.5% | 20.2% | 41 | 53.8% | 1515 | 1129 | 132 |
| NOISE+OD+PM | H2 | 57.1% | 42.0% | 27 | 61.5% | 1922 | 1098 | 174 |
| NOISE+OD+PM+OVN | 5y | 55.8% | 44.2% | 33 | 42.5% | 518 | 289 | 351 |
| NOISE+OD+PM+OVN | H1 | 61.6% | 37.3% | 56 | 47.3% | 415 | 255 | 150 |
| NOISE+OD+PM+OVN | H2 | 51.7% | 48.3% | 22 | 38.1% | 655 | 339 | 181 |

## 'Helps' test vs NOISE alone (pass rate AND total profit higher in BOTH halves)

| Set | H1 pass vs N | H2 pass vs N | H1 $ vs N | H2 $ vs N | helps? |
|---|---|---|---|---|---|
| OPEN_DRIVE | 0.0% / 63.9% | 0.3% / 55.1% | -5 / 8306 | 1455 / 10282 | no |
| PM_FADE | 3.8% / 63.9% | 42.0% / 55.1% | 824 / 8306 | 5401 / 10282 | no |
| OVERNIGHT | 0.0% / 63.9% | 23.4% / 55.1% | -5473 / 8306 | -59 / 10282 | no |
| NOISE+OPEN_DRIVE | 64.6% / 63.9% | 57.7% / 55.1% | 8764 / 8306 | 10789 / 10282 | YES |
| NOISE+PM_FADE | 73.8% / 63.9% | 56.6% / 55.1% | 9130 / 8306 | 15683 / 10282 | YES |
| NOISE+OD+PM | 74.5% / 63.9% | 57.1% / 55.1% | 9588 / 8306 | 16190 / 10282 | YES |
| NOISE+OD+PM+OVN | 61.6% / 63.9% | 51.7% / 55.1% | 4115 / 8306 | 16131 / 10282 | no |
