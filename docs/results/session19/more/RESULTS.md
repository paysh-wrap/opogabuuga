# Session 19 more NOISE refinements (baseline = preset C + Mondays off). Pass share of finished evals (pass+bust=100), sizes 25/50/100/150K = 1/2/2/3 micros, 300 boot paths. Pick IS, judge J.

| item | IS n | win | PF | $/tr | J n | win | PF | $/tr | J net | pass% IS 25/50/100/150 | pass% J 25/50/100/150 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B  baseline: preset C + Mondays off | 814 | 48.6 | 1.44 | 21.1 | 121 | 59.5 | 1.72 | 50.3 | 6087 | 76/74/87/87 | 66/64/82/82 |
| 1a first check 10:30 | 790 | 50.4 | 1.28 | 13.1 | 118 | 52.5 | 1.20 | 17.0 | 2006 | 67/63/67/67 | 47/43/40/40 |
| 1b first check 11:00 | 681 | 49.6 | 1.46 | 20.4 | 106 | 58.5 | 1.58 | 41.6 | 4411 | 77/76/83/83 | 59/57/63/63 |
| 2  last entry 14:00 | 729 | 45.8 | 1.34 | 17.5 | 109 | 57.8 | 1.72 | 53.3 | 5814 | 70/68/76/76 | 66/65/81/81 |
| 3a band x0.9 | 880 | 47.7 | 1.37 | 18.8 | 136 | 52.2 | 1.40 | 31.7 | 4316 | 71/69/83/83 | 51/45/56/57 |
| 3b band x1.1 | 736 | 49.5 | 1.43 | 20.3 | 108 | 58.3 | 1.76 | 55.5 | 5998 | 78/75/83/83 | 69/66/78/79 |
| 4a lookback 10d | 805 | 47.7 | 1.42 | 21.1 | 130 | 58.5 | 1.53 | 38.3 | 4982 | 75/74/86/86 | 60/56/68/68 |
| 4b lookback 20d | 787 | 49.2 | 1.39 | 19.9 | 124 | 55.6 | 1.48 | 37.3 | 4622 | 76/74/83/83 | 54/47/60/60 |
| 5a stop $200 | 824 | 47.9 | 1.41 | 19.8 | 126 | 55.6 | 1.61 | 42.0 | 5296 | 75/72/83/83 | 64/63/73/73 |
| 5b stop $300 | 812 | 48.8 | 1.42 | 20.5 | 121 | 59.5 | 1.64 | 46.9 | 5679 | 73/72/85/85 | 61/58/74/74 |
| 6a lock trigger 80pt | 806 | 50.7 | 1.44 | 20.4 | 118 | 64.4 | 1.89 | 55.5 | 6544 | 77/75/87/87 | 76/76/90/90 |
| 6b lock trigger 120pt | 819 | 48.0 | 1.41 | 20.2 | 123 | 57.7 | 1.71 | 52.2 | 6424 | 76/73/87/87 | 68/65/76/76 |
| 7  skip FOMC days | 782 | 49.0 | 1.44 | 21.0 | 117 | 59.8 | 1.73 | 51.6 | 6040 | 79/78/90/90 | 68/66/82/82 |
| 8a skip day after >2% gap | 781 | 48.1 | 1.43 | 20.2 | 115 | 60.9 | 1.82 | 54.2 | 6236 | 76/73/84/84 | 73/70/86/86 |
| 8b skip day after >1% gap | 672 | 48.7 | 1.58 | 25.5 | 87 | 65.5 | 1.92 | 56.4 | 4909 | 84/83/92/92 | 80/81/94/94 |
| 11a skip month-end day | 775 | 48.5 | 1.43 | 20.7 | 113 | 59.3 | 1.63 | 43.2 | 4886 | 78/76/88/88 | 67/62/75/75 |
| 11b skip opex Friday | 762 | 48.4 | 1.42 | 20.3 | 113 | 60.2 | 1.74 | 49.2 | 5565 | 77/75/86/87 | 68/65/84/84 |
| 10 50K size 1 micro (vs baseline 2) | 814 | 48.6 | 1.44 | 21.1 | 121 | 59.5 | 1.72 | 50.3 | 6087 | 76/95/87/87 | 66/90/82/82 |
| 10b 50K size 3 micros | 814 | 48.6 | 1.44 | 21.1 | 121 | 59.5 | 1.72 | 50.3 | 6087 | 76/64/87/87 | 66/56/82/82 |

Notes: item 9 (max 2/day) already tested (refine R8). Item 7 = FOMC decision days only (from memory, 63 dates; CPI not built - no verified list). Item 8 gap = prior day's open-gap >2% / >1% (the existing 1.5% roll guard covers same-day gaps). Item 11 month-end = last RTH day; opex = 3rd Friday. 10 is sizing only (50K 1 micro: 95/90 pass share IS/J vs 74/64 at 2 micros, but target takes ~2x longer and profit halves).
 ~19 tests on shared data: expect ~1 false positive by chance.