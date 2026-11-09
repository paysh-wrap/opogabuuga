# Agent D: filter study on MAIN (NOISE $250 stop + PM fade $250 stop), 1 micro MNQ, 2021-11-01..2026-10-30

Scripts: study.py (thin NOISE/fade copies + features), filters.py (21 filters -> results.csv), sims.py (Pro 25K sims -> sims.md). Copies reproduce baseline exactly: 1,291 trades (803 NOISE + 488 fade), $25,345.27, win 49.96%, PF 1.325. Fade runs only on days the (filtered) NOISE did not trade. Features use past data only. One a-priori cutoff per filter, no grid.

Pass rule: win% or PF improves in BOTH halves (H1 2021-11..2023-12, H2 2024-01..2026-10) and total >= 80% of baseline. strict = win AND PF improve in both halves.

| filter | n | win | $/tr | total $ | PF | maxDD | H1 win/PF/$ | H2 win/PF/$ | losing yrs | pass | strict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASELINE | 1291 | 50.0% | 19.6 | 25345 | 1.33 | -2591 | 48.6%/1.30/9363 | 51.0%/1.34/15982 | 2021 |  |  |
| N1 skip NOISE vs prior-day dir | 1152 | 49.6% | 5.9 | 6854 | 1.09 | -4988 | 49.0%/1.06/1897 | 50.0%/1.12/4958 | 2021,2025 | no | no |
| N2 skip NOISE vs overnight move | 1200 | 49.9% | 13.1 | 15769 | 1.21 | -5191 | 47.0%/1.15/4556 | 52.1%/1.25/11213 | 2021,2022,2025 | no | no |
| N3 NOISE only with open-to-now dir | 1291 | 50.0% | 19.6 | 25345 | 1.33 | -2591 | 48.6%/1.30/9363 | 51.0%/1.34/15982 | 2021 | no | no |
| N4 skip 15:00 NOISE entry | 1239 | 48.3% | 14.4 | 17809 | 1.22 | -2202 | 46.1%/1.14/4660 | 50.0%/1.28/13149 | 2021 | no | no |
| N5 max 1 NOISE entry/day | 1111 | 49.9% | 15.2 | 16916 | 1.25 | -2679 | 47.8%/1.19/5467 | 51.5%/1.29/11449 | - | no | no |
| N6 max 2 NOISE entries/day | 1268 | 49.8% | 19.0 | 24131 | 1.31 | -2342 | 48.1%/1.27/8213 | 51.2%/1.34/15918 | 2021 | no | no |
| N7 no NOISE entry after losing NOISE trade | 1150 | 49.5% | 14.4 | 16590 | 1.23 | -2928 | 47.5%/1.21/6085 | 51.0%/1.25/10505 | - | no | no |
| N8 skip |gap|>0.5% | 1210 | 49.9% | 13.2 | 16032 | 1.21 | -2662 | 47.7%/1.06/1908 | 51.7%/1.33/14124 | 2021 | no | no |
| N9 skip overnight range >1.5x 14d avg | 1265 | 50.1% | 17.5 | 22117 | 1.29 | -2582 | 48.4%/1.30/9104 | 51.5%/1.28/13013 | 2021 | no | no |
| N10 skip low-vol tercile (past 500d) | 1180 | 50.0% | 11.3 | 13282 | 1.18 | -2394 | 48.0%/1.10/3141 | 51.6%/1.23/10140 | 2021,2023 | no | no |
| N11 skip Monday | 1254 | 50.8% | 19.7 | 24690 | 1.33 | -3038 | 48.9%/1.28/8532 | 52.3%/1.36/16158 | 2021 | YES | no |
| N12 skip Friday | 1223 | 50.0% | 12.9 | 15812 | 1.22 | -4209 | 48.0%/1.11/3281 | 51.5%/1.29/12531 | 2021 | no | no |
| F1 skip fade if day range>1.5x avg | 1282 | 49.9% | 19.5 | 24954 | 1.32 | -2342 | 48.5%/1.30/9065 | 51.0%/1.34/15890 | 2021 | no | no |
| F2 fade only beyond prior-day H/L | 987 | 46.8% | 20.2 | 19953 | 1.32 | -2494 | 45.7%/1.34/8345 | 47.6%/1.30/11608 | - | no | no |
| F3 fade only NOT beyond prior-day H/L | 1107 | 49.0% | 22.0 | 24322 | 1.36 | -2326 | 48.8%/1.37/9760 | 49.1%/1.35/14562 | 2021 | YES | no |
| F4 fade only before 15:00 | 1268 | 49.8% | 19.7 | 24957 | 1.32 | -2591 | 48.3%/1.31/9387 | 50.9%/1.33/15570 | 2021 | no | no |
| F5 skip fade if |VWAP slope 30m|>0.1 avg-range | 1289 | 50.0% | 20.0 | 25844 | 1.33 | -2342 | 48.6%/1.30/9363 | 51.2%/1.35/16481 | 2021 | no | no |
| F6 fade target >= $100 | 1146 | 48.8% | 22.6 | 25843 | 1.36 | -2494 | 47.8%/1.37/10253 | 49.5%/1.35/15590 | - | YES | no |
| F7 fade target >= 1R ($250) | 873 | 45.7% | 25.6 | 22334 | 1.38 | -2728 | 46.3%/1.50/10099 | 45.2%/1.32/12235 | - | no | no |
| F8 fade BE after +$100 | 1291 | 46.6% | 18.1 | 23410 | 1.32 | -2392 | 45.9%/1.28/8166 | 47.0%/1.35/15244 | 2021 | no | no |
| F9 fade only against overnight move dir | 1009 | 47.1% | 19.8 | 19997 | 1.31 | -2355 | 46.5%/1.33/8172 | 47.6%/1.30/11824 | - | no | no |

N3 is a no-op (entries always agree with open-to-now direction). Passing: N11 (skip Monday), F3 (fade only when NOT beyond prior-day H/L), F6 (fade target >= $100). None passes strict (win AND PF both halves); N11 raises win in both halves but lowers H1 PF; F3/F6 raise PF in both halves but lower win%.

## Pro 25K eval sim (eval no DLL, funded DLL $600, rolling starts; pass/bust)

| set | n | win | total $ | PF | H1 win/PF/$ | H2 win/PF/$ | 5y pass/bust | H1 pass/bust | H2 pass/bust |
|---|---|---|---|---|---|---|---|---|---|
| BASELINE | 1291 | 50.0% | 25345 | 1.33 | 48.6%/1.30/9363 | 51.0%/1.34/15982 | 65.7%/32.2% | 71.1%/21.3% | 65.7%/32.9% |
| F6 | 1146 | 48.8% | 25843 | 1.36 | 47.8%/1.37/10253 | 49.5%/1.35/15590 | 66.5%/26.2% | 75.7%/11.4% | 63.7%/31.4% |
| F3 | 1107 | 49.0% | 24322 | 1.36 | 48.8%/1.37/9760 | 49.1%/1.35/14562 | 61.0%/37.8% | 77.9%/14.1% | 51.4%/48.6% |
| N11 | 1254 | 50.8% | 24690 | 1.33 | 48.9%/1.28/8532 | 52.3%/1.36/16158 | 59.7%/34.8% | 63.9%/17.1% | 61.7%/36.9% |
| F6+F3 | 1009 | 48.0% | 24692 | 1.39 | 47.5%/1.41/10014 | 48.3%/1.37/14677 | 61.0%/37.6% | 76.8%/17.1% | 53.1%/45.7% |
| F6+N11 | 1090 | 49.5% | 25376 | 1.37 | 48.1%/1.36/9625 | 50.6%/1.37/15751 | 65.4%/29.9% | 70.3%/16.7% | 67.1%/30.3% |
| F3+N11 | 1016 | 50.4% | 25339 | 1.41 | 50.0%/1.42/9896 | 50.7%/1.41/15443 | 61.6%/32.9% | 71.9%/14.4% | 57.7%/38.0% |
| F6+F3+N11 | 911 | 49.4% | 25979 | 1.46 | 48.6%/1.48/10268 | 50.0%/1.44/15711 | 64.5%/22.7% | 70.0%/12.9% | 66.0%/30.3% |


## Verdict
Effects are small (PF 1.33 -> 1.36-1.46, win within -2..+1 pt) and eval-sim results are inconsistent: F3 and F6+F3 get H1 better but H2 much worse (pass 51-53%, bust 46-49% vs 66/33). F6 alone: 5y 66.5/26.2 vs 65.7/32.2 but H2 pass 63.7 vs 65.7. The triple F6+F3+N11 looks best on PF (1.46, both halves ~1.44-1.48, total +$634) and 5y 64.5/22.7, yet H2 is 66.0/30.3 vs 65.7/32.9 (flat) and it stacks three weakly-motivated cuts (a day-of-week and two fade cuts) that were chosen after seeing 21 results; with ~1,000 trades and a trade-level SD near $270 the PF differences are within noise (multiple-testing: 3 of 21 passing is about what chance gives). Win rate is not raised by any filter.
Recommendation: none - keep MAIN as is. If anything is ever adopted, F6 (skip fades with target < $100) is the only one with a mechanical rationale (tiny targets cannot pay the $250 stop), it keeps profit (+$498) and cuts 5y bust 32% -> 26%, but it lowers win% and H2 pass rate, so it needs forward evidence first.
