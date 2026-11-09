# Fleet 5 eval + 5 funded, cash per 10 sessions (steady state sessions 130-520)

Script: fleet.py. 157 rolling fleets (every 5 sessions), 520 sessions each, 39 steady blocks per fleet. Net per block = mean cash - fee x evals bought per block; break-even fee = mean cash / evals bought per block (= mean cash per eval bought).

| plan | variant | mean | median | p25 | p75 | %0 blocks | warm-up mean | funded occupied | evals/yr | busts/yr | BE fee |
|-|-|-|-|-|-|-|-|-|-|-|-|
| 25K | same-day | $464 | $0 | $0 | $0 | 91% | $192 | 4.4 | 6.1 | 2.9 | $1966 |
| 25K | staggered | $474 | $0 | $0 | $0 | 84% | $135 | 4.6 | 6.5 | 3.1 | $1909 |
| 50K | same-day | $730 | $0 | $0 | $0 | 92% | $198 | 4.5 | 5.0 | 1.8 | $3818 |
| 50K | staggered | $702 | $0 | $0 | $0 | 83% | $117 | 4.5 | 7.2 | 1.9 | $2524 |
| 100K | same-day | $519 | $0 | $0 | $0 | 95% | $61 | 4.3 | 4.5 | 0.5 | $2973 |
| 100K | staggered | $500 | $0 | $0 | $0 | 87% | $29 | 4.2 | 8.3 | 0.6 | $1558 |
| 150K | same-day | $718 | $0 | $0 | $0 | 94% | $107 | 4.2 | 4.9 | 0.3 | $3771 |
| 150K | staggered | $697 | $0 | $0 | $0 | 86% | $39 | 4.1 | 9.0 | 0.4 | $2024 |
| 150K-HR | same-day | $729 | $0 | $0 | $0 | 94% | $162 | 4.0 | 5.1 | 0.4 | $3735 |
| 150K-HR | staggered | $718 | $0 | $0 | $0 | 87% | $73 | 3.9 | 9.2 | 0.5 | $2036 |

| plan | variant | era 2021-11..2023-12 mean / %0 / evals-yr | era 2024..2026 mean / %0 / evals-yr |
|-|-|-|-|
| 25K | same-day | $544 / 90% / 7.1 (n=113) | $258 / 96% / 3.8 (n=44) |
| 25K | staggered | $558 / 82% / 7.2 (n=113) | $258 / 91% / 4.5 (n=44) |
| 50K | same-day | $873 / 90% / 5.8 (n=113) | $360 / 96% / 2.8 (n=44) |
| 50K | staggered | $829 / 81% / 7.7 (n=113) | $376 / 90% / 6.0 (n=44) |
| 100K | same-day | $607 / 94% / 5.0 (n=113) | $295 / 97% / 3.3 (n=44) |
| 100K | staggered | $583 / 86% / 8.8 (n=113) | $289 / 92% / 7.1 (n=44) |
| 150K | same-day | $845 / 93% / 5.6 (n=113) | $391 / 97% / 3.3 (n=44) |
| 150K | staggered | $813 / 84% / 9.7 (n=113) | $398 / 91% / 6.9 (n=44) |
| 150K-HR | same-day | $855 / 93% / 5.8 (n=113) | $405 / 97% / 3.3 (n=44) |
| 150K-HR | staggered | $835 / 84% / 10.0 (n=113) | $418 / 92% / 7.1 (n=44) |
