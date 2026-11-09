# Consistency 50% vs 40% study (MNQ MAIN strategy trades, 2021-11..2026-10, rolling starts every 2 sessions, 260-session horizon, 5 accounts)

## Part 1a. Pro funded, as-soon-as-eligible (check every session, >=2 sessions after prior payout)

| plan | cons | pay/acct/yr | 5-acct $/2wk | year mean / median | >=1 payout | med sess to 1st | bust | checks failing only on consistency | cycles blocked by big day | wait med/mean sess |
|---|---|---|---|---|---|---|---|---|---|---|
| 25k | 40 | 1.96 | 334 | 8686 / 4500 | 60% | 56 | 62.7% | 94% | 63% | 14/17.5
| 25k | 50 | 2.27 | 334 | 8690 / 5841 | 60% | 54 | 61.8% | 86% | 56% | 8/13.8
| 50k | 40 | 2.04 | 599 | 15582 / 14294 | 68% | 52.5 | 48.0% | 95% | 76% | 15/21.5
| 50k | 50 | 2.47 | 631 | 16408 / 15157 | 69% | 49.0 | 49.9% | 91% | 64% | 14/18.1
| 100k | 40 | 2.25 | 695 | 18060 / 16673 | 74% | 72.0 | 25.8% | 95% | 66% | 14/20.7
| 100k | 50 | 2.64 | 686 | 17825 / 16932 | 74% | 71.0 | 28.3% | 92% | 54% | 9/16.7
| 150k | 40 | 2.37 | 973 | 25308 / 20280 | 76% | 69.0 | 24.5% | 95% | 71% | 14/19.7
| 150k | 50 | 2.78 | 1001 | 26024 / 26156 | 77% | 68 | 25.2% | 92% | 53% | 13/19.0

## Part 1b. Pro funded, wait for payout >= 50% of cap

| plan | cons | pay/acct/yr | 5-acct $/2wk | year mean / median | >=1 payout | med sess to 1st | bust | checks failing only on consistency | cycles blocked by big day | wait med/mean sess |
|---|---|---|---|---|---|---|---|---|---|---|
| 25k | 40 | 1.88 | 336 | 8724 / 4500 | 60% | 56 | 61.0% | 92% | 72% | 11/17.0
| 25k | 50 | 2.17 | 348 | 9046 / 3230 | 60% | 54 | 59.7% | 80% | 66% | 7/14.2
| 50k | 40 | 1.92 | 625 | 16262 / 15752 | 66% | 59 | 47.8% | 91% | 76% | 18/24.8
| 50k | 50 | 2.25 | 670 | 17426 / 15954 | 67% | 59.0 | 53.0% | 79% | 70% | 15/18.3
| 100k | 40 | 1.93 | 709 | 18434 / 18985 | 71% | 85.0 | 25.8% | 88% | 66% | 16/24.6
| 100k | 50 | 2.23 | 743 | 19307 / 17846 | 71% | 85 | 25.2% | 78% | 66% | 11/18.5
| 150k | 40 | 2.10 | 1003 | 26090 / 23879 | 74% | 82 | 23.5% | 89% | 69% | 16/24.3
| 150k | 50 | 2.49 | 1077 | 28009 / 25411 | 74% | 82.0 | 24.3% | 81% | 57% | 13/18.7

## Part 2a. Daily P&L distribution at 1 micro (days with trades)
n days 1111 (of 1305 sessions); mean 22.8; median 8.0; p5 -250 p25 -103 p75 112 p95 349 p99 612; max 3228 min -748; win days 52%

## Part 2b. Share of rolling windows (of N trading days, profit>0) whose best day exceeds X% of window profit
| window | profitable windows | >30% | >40% | >50% | median best-day share |
|---|---|---|---|---|---|
| 3 | 609 | 100% | 98% | 93% | 1.02 |
| 5 | 655 | 99% | 96% | 89% | 0.98 |
| 10 | 726 | 98% | 92% | 81% | 0.88 |

## Part 2c. Consistency day-stop (stop for the day once today's realized profit >= X% of cycle-so-far+today; floor = denominator min). as-soon policy
| plan | cons | day-stop | floor | 5-acct $/2wk | mean yr | median yr | pay/acct/yr | bust | cons-fail checks | 1st payout med |
|---|---|---|---|---|---|---|---|---|---|---|
| 25k | 40 | - none | 0 | 334 | 8686 | 4500 | 1.96 | 62.7% | 94% | 56 |
| 25k | 40 | 0.35 literal | 0 | 365 | 9485 | 7678 | 2.06 | 53.9% | 94% | 57.0 |
| 25k | 40 | 0.35 floor=min cycle x2 | 500 | 334 | 8686 | 4500 | 1.96 | 62.7% | 94% | 56 |
| 25k | 40 | 0.35 floor=1st cap | 1000 | 334 | 8686 | 4500 | 1.96 | 62.7% | 94% | 56 |
| 25k | 50 | - none | 0 | 334 | 8690 | 5841 | 2.27 | 61.8% | 86% | 54 |
| 25k | 50 | 0.45 literal | 0 | 349 | 9082 | 6923 | 2.38 | 57.0% | 87% | 56.0 |
| 25k | 50 | 0.45 floor=min cycle x2 | 500 | 334 | 8690 | 5841 | 2.27 | 61.8% | 86% | 54 |
| 25k | 50 | 0.45 floor=1st cap | 1000 | 334 | 8690 | 5841 | 2.27 | 61.8% | 86% | 54 |
| 50k | 40 | - none | 0 | 599 | 15582 | 14294 | 2.04 | 48.0% | 95% | 52.5 |
| 50k | 40 | 0.35 literal | 0 | 599 | 15584 | 14344 | 2.02 | 45.7% | 95% | 53.0 |
| 50k | 40 | 0.35 floor=min cycle x2 | 1000 | 599 | 15581 | 14294 | 2.04 | 48.0% | 95% | 52.5 |
| 50k | 40 | 0.35 floor=1st cap | 2000 | 599 | 15581 | 14294 | 2.04 | 48.0% | 95% | 52.5 |
| 50k | 50 | - none | 0 | 631 | 16408 | 15157 | 2.47 | 49.9% | 91% | 49.0 |
| 50k | 50 | 0.45 literal | 0 | 609 | 15843 | 14308 | 2.42 | 42.3% | 92% | 49 |
| 50k | 50 | 0.45 floor=min cycle x2 | 1000 | 631 | 16407 | 15157 | 2.47 | 49.9% | 91% | 49.0 |
| 50k | 50 | 0.45 floor=1st cap | 2000 | 631 | 16408 | 15157 | 2.47 | 49.9% | 91% | 49.0 |
| 100k | 40 | - none | 0 | 695 | 18060 | 16673 | 2.25 | 25.8% | 95% | 72.0 |
| 100k | 40 | 0.35 literal | 0 | 692 | 17982 | 16642 | 2.24 | 24.9% | 96% | 74 |
| 100k | 40 | 0.35 floor=min cycle x2 | 1500 | 695 | 18060 | 16673 | 2.25 | 25.8% | 95% | 72.0 |
| 100k | 40 | 0.35 floor=1st cap | 2500 | 695 | 18060 | 16673 | 2.25 | 25.8% | 95% | 72.0 |
| 100k | 50 | - none | 0 | 686 | 17825 | 16932 | 2.64 | 28.3% | 92% | 71.0 |
| 100k | 50 | 0.45 literal | 0 | 686 | 17839 | 17125 | 2.66 | 26.4% | 92% | 73 |
| 100k | 50 | 0.45 floor=min cycle x2 | 1500 | 686 | 17825 | 16932 | 2.64 | 28.3% | 92% | 71.0 |
| 100k | 50 | 0.45 floor=1st cap | 2500 | 686 | 17825 | 16932 | 2.64 | 28.3% | 92% | 71.0 |
| 150k | 40 | - none | 0 | 973 | 25308 | 20280 | 2.37 | 24.5% | 95% | 69.0 |
| 150k | 40 | 0.35 literal | 0 | 971 | 25248 | 20280 | 2.37 | 19.9% | 96% | 71.0 |
| 150k | 40 | 0.35 floor=min cycle x2 | 2000 | 973 | 25308 | 20280 | 2.37 | 24.5% | 95% | 69.0 |
| 150k | 40 | 0.35 floor=1st cap | 3000 | 973 | 25308 | 20280 | 2.37 | 24.5% | 95% | 69.0 |
| 150k | 50 | - none | 0 | 1001 | 26024 | 26156 | 2.78 | 25.2% | 92% | 68 |
| 150k | 50 | 0.45 literal | 0 | 989 | 25726 | 25256 | 2.77 | 19.9% | 92% | 70 |
| 150k | 50 | 0.45 floor=min cycle x2 | 2000 | 1001 | 26024 | 26156 | 2.78 | 25.2% | 92% | 68 |
| 150k | 50 | 0.45 floor=1st cap | 3000 | 1001 | 26024 | 26156 | 2.78 | 25.2% | 92% | 68 |

## Part 3. Flex eval (3 profitable days, DLL none), target per plan
| plan | cons | starts | PASS | BUST | OPEN | median days to pass | mean days |
|---|---|---|---|---|---|---|---|
| 25k | 40 | 593 | 59% | 38% | 4% | 47.0 | 51 |
| 25k | 50 | 593 | 61% | 36% | 3% | 40.0 | 45 |
| 50k | 40 | 593 | 54% | 30% | 16% | 50.0 | 53 |
| 50k | 50 | 593 | 55% | 29% | 16% | 47.5 | 51 |
| 100k | 40 | 528 | 62% | 24% | 14% | 104 | 120 |
| 100k | 50 | 528 | 62% | 24% | 14% | 104.0 | 120 |
| 150k | 40 | 528 | 64% | 23% | 13% | 103.5 | 121 |
| 150k | 50 | 528 | 64% | 23% | 13% | 104 | 122 |

## Notes / verdict
- Check-fail % = share of payout checks where cycle profit >= min and balance-buffer >= min request, but largest day > X% of cycle profit. Cycles blocked = payout cycles that failed at least once before paying.
- Best-day share can exceed 100% in rolling windows because other days are net losses.
- Floor variants of the day-stop never trigger (identical to no stop) because denominators of 2x min-cycle or first cap exceed typical cycle profit; only the literal rule bites.
- Script: study.py (own funded_path, parametrised consistency; did not edit app code). Strategy is MNQ 1-micro trade list scaled by plan size; same-trades accounts bust together.
