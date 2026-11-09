# Pro 25K high-risk evaluation study (MNQ 5y, 2021-11 to 2026-10)

Files: gen.py (trade generators; main verified identical to app/backtest/data/main_strategy_5y.csv, 1291 trades, $25,345), sim.py (eval engine; verified 0 mismatches vs app eval_path for 1 micro / 2 micros / 3 micros+brake), run2.py, funded.py, report.py, extra.json, results_all.json, table.md.
Method: Pro 25K eval (target $1,250, EOD trailing MLL $1,000 locks at 25,100 when peak >= 26,100, no DLL, no consistency, >=1 profitable day), 593 rolling starts every 2 sessions, 120-session horizon. Sizing is set at the start of each session (same as app); stops are checked trade by trade (bust if balance <= floor intraday). Restart chain: after each bust restart on the next session with a fresh eval until the first pass (no horizon; 0% censored). Era1 = starts to 2023-12-31, era2 = 2024-01 on. 25 configs tested (+ baseline), nothing tuned after seeing results; E1-E4 were picked from A-D.
Caveat: starts overlap heavily (about 10 independent 120-session windows), so differences of 2-3 pass-points are noise; the size effect (bust 34% to 47-59%) and the speed effect (median 36 to 4-14) are far outside noise.
Value per eval = pass % x funded year-1 take-home at 1 micro ($1,646.41, project(accounts=1,cadence=10), funded stream = MAIN). The eval price is not subtracted.

## Full results (all 25 configs + baseline)
| config | pass | bust | open | med sess to pass | p75 | restart-chain med sess to 1st pass | evals per funded | value per eval (funded 1 micro $1,646) | era1 21-23 pass/bust/med/chain | era2 24-26 pass/bust/med/chain |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE 1 micro | 63.4% | 34.4% | 2.2% | 36 | 56 | 47 | 1.58 | $1,044 | 66%/31%/41/56 | 61%/37%/32/40 |
| A1 fixed 2 | 45.5% | 54.5% | 0.0% | 12 | 18 | 19 | 2.20 | $750 | 44%/56%/13/20 | 47%/53%/11/18 |
| A2 fixed 3 | 45.9% | 54.1% | 0.0% | 6 | 9 | 11 | 2.18 | $755 | 45%/55%/6/11 | 46%/54%/6/11 |
| A3 fixed 4 | 47.4% | 52.6% | 0.0% | 4 | 7 | 8 | 2.11 | $780 | 47%/53%/4/9 | 47%/53%/4/8 |
| A4 2, brake<50%->1 | 52.8% | 47.2% | 0.0% | 14 | 25 | 23 | 1.89 | $869 | 52%/48%/15/26 | 54%/46%/13/21 |
| A5 3, brake<50%->1 | 41.0% | 59.0% | 0.0% | 6 | 11 | 16 | 2.44 | $675 | 43%/57%/6/15 | 39%/61%/6/18 |
| A6 3, brake<50%->2 | 44.7% | 55.3% | 0.0% | 6 | 11 | 13 | 2.24 | $736 | 45%/55%/6/13 | 45%/55%/6/14 |
| A7 4, brake<50%->2 | 41.7% | 58.3% | 0.0% | 4 | 7 | 9 | 2.40 | $686 | 43%/57%/4/10 | 41%/59%/4/9 |
| B1 4, sprint<30% left->1 | 49.4% | 50.6% | 0.0% | 5 | 9 | 9 | 2.02 | $813 | 51%/49%/6/10 | 48%/52%/5/9 |
| B2 4, sprint<50% left->1 | 52.4% | 47.6% | 0.0% | 7 | 14 | 11 | 1.91 | $863 | 56%/44%/7/11 | 49%/51%/6/11 |
| B3 3, sprint<50%->1, lock 33% | 49.9% | 50.1% | 0.0% | 11 | 17 | 16 | 2.00 | $822 | 50%/50%/12/17 | 50%/50%/9/15 |
| B4 4, sprint<50%->1, lock 50% | 52.4% | 47.6% | 0.0% | 7 | 14 | 11 | 1.91 | $863 | 56%/44%/8/11 | 49%/51%/7/11 |
| B5 3, brake<50%->1, lock 50% | 41.7% | 58.3% | 0.0% | 6 | 11 | 16 | 2.40 | $686 | 43%/57%/6/15 | 41%/59%/6/17 |
| C1 stop$125 x2 | 51.3% | 48.7% | 0.0% | 14 | 24 | 24 | 1.95 | $844 | 57%/43%/17/25 | 46%/54%/12/23 |
| C2 stop$125 x3 | 43.7% | 56.3% | 0.0% | 7 | 11 | 13 | 2.29 | $719 | 45%/55%/7/13 | 42%/58%/6/13 |
| C3 stop$150 x2 | 49.4% | 50.6% | 0.0% | 13 | 21 | 22 | 2.02 | $813 | 50%/50%/14/23 | 49%/51%/12/22 |
| C4 stop$150 x3 | 41.3% | 58.7% | 0.0% | 6 | 10 | 13 | 2.42 | $680 | 42%/58%/6/14 | 40%/60%/6/12 |
| D1 30-min checks, 1 micro | 51.8% | 43.7% | 4.6% | 32 | 46 | 48 | 1.93 | $852 | 58%/32%/33/57 | 46%/54%/31/45 |
| D2 max 5 entries, 1 micro | 64.6% | 33.2% | 2.2% | 36 | 56 | 47 | 1.55 | $1,063 | 66%/31%/41/56 | 63%/35%/30/38 |
| D3 30-min+5 entries, 1 micro | 51.1% | 44.5% | 4.4% | 31 | 46 | 50 | 1.96 | $841 | 58%/33%/33/57 | 45%/55%/29/47 |
| D4 +open-drive, 1 micro | 66.6% | 31.9% | 1.5% | 37 | 55 | 46 | 1.50 | $1,097 | 68%/31%/41/54 | 65%/33%/31/40 |
| D5 30-min+5+OD, 1 micro | 62.1% | 33.6% | 4.4% | 34 | 52 | 44 | 1.61 | $1,022 | 66%/25%/36/55 | 59%/41%/32/40 |
| E1 4, sprint<50%->1 + brake<50%->1, +OD | 47.2% | 52.8% | 0.0% | 7 | 15 | 15 | 2.12 | $777 | 49%/51%/8/15 | 45%/55%/7/14 |
| E2 2, brake<50%->1, +OD | 55.3% | 44.7% | 0.0% | 13 | 22 | 22 | 1.81 | $911 | 53%/47%/14/25 | 57%/43%/12/20 |
| E3 4, sprint<50%->1 + brake<50%->1 | 46.0% | 54.0% | 0.0% | 7 | 17 | 16 | 2.17 | $758 | 49%/51%/9/17 | 43%/57%/7/15 |
| E4 stop$125 x4, sprint<50%->1, +OD | 49.1% | 50.9% | 0.0% | 7 | 14 | 13 | 2.04 | $808 | 55%/45%/7/12 | 43%/57%/7/14 |

## Funded side (project(), 1 account, cadence 10, year 1, MAIN stream)
| funded rule | year-1 mean | median | p25-p75 | bust | any payout |
|---|---|---|---|---|---|
| 1 micro (baseline) | $1,646 | $900 | 0-3,375 | 56.6% | 58.3% |
| 2 micros no brake | $1,054 | $0 | 0-900 | 72.7% | 35.8% |
| 2 micros, brake cushion<60% -> 1 | $1,242 | $0 | 0-2,250 | 64.2% | 42.4% |
| 2 micros, brake <50% -> 1 | $1,206 | $0 | 0-2,250 | 65.2% | 43.2% |
| 3 micros, brake <60% -> 1 | $1,016 | $0 | 0-900 | 75.3% | 35.0% |
Higher funded risk loses money (the DLL, 40% largest-day and $26,100 buffer rules cap the upside; MLL busts cost the account). Keep funded at 1 micro.

## 1. Recommended HIGH-RISK profile (25K, Evaluation Mode, stage EVAL only)
Eval rule (B2): trade size 4 micros per signal (worst-case trade 4 x $250 = $1,000 = 100% of the MLL at the start, ~50% once there is $2,000 of cushion); as soon as remaining target < 50% of $1,250 (profit >= $625) drop to 1 micro for the rest of the eval; no day lock-in (B4 with a 50% lock-in gave identical results, B3 33% lock-in did not help); strategies and stops unchanged (MAIN: NOISE $250 + afternoon fade $250); size set at the session start; reverts automatically at PASSED / stage change (non-negotiable 10; eval-only).
Funded rule: 1 micro, no growth, no brake (baseline).

| | current 1 micro | B2 high-risk | moderate alternative E2/A4 (2 micros, brake<50% -> 1) |
|---|---|---|---|
| pass / bust | 63.4% / 34.4% (2.2% open) | 52.4% / 47.6% | 52.8-55.3% / 45-47% |
| median / p75 sessions to pass | 36 / 56 | 7 / 14 | 13-14 / 22-25 |
| restart-chain median sessions to first pass | 47 | 11 | 22-23 |
| evals per funded account | 1.58 | 1.91 | 1.81-1.89 |
| value per eval | $1,044 | $863 (-17%) | $869-911 |
| era1 / era2 pass, bust, med, chain | 66/31/41/56, 61/37/32/40 | 56/44/7/11, 49/51/6/11 | similar |
Price: 13 extra busts per 100 evals (+0.33 evals per funded account) and about $180 less funded value per eval bought (the funded stream is unchanged, you just pass less often); in exchange a funded-ready account in about 11 sessions (~2 weeks) instead of 47 (~2.5 months). Whether it pays depends on the eval fee (not modeled): speed costs ~0.33 extra evals per account and saves ~36 sessions. Worth noting E2 (2 micros + brake + OD) has the best value per eval of the fast set ($911) but is twice as slow as B2.
Era1 vs era2: the high-risk sprint passes less in 2024-26 (49% vs 56%) as does the baseline (61 vs 66).

## 2. Ranking of other ways to pass faster (vs baseline: median 36, chain 47, pass 63.4%, value $1,044)
| rank | way | median sess | chain | pass | bust | value | verdict |
|---|---|---|---|---|---|---|---|
| 1 | B2 4 micros then 1 micro under 50% of target left | 7 (-29) | 11 (-36) | 52.4% | 47.6% | $863 | best speed per lost pass |
| 2 | B1 4 micros then 1 micro under 30% left | 5 | 9 | 49.4% | 50.6% | $813 | faster, 3 pts fewer passes |
| 3 | A3 fixed 4 micros | 4 | 8 | 47.4% | 52.6% | $780 | fastest, no protect |
| 4 | A2 fixed 3 micros | 6 | 11 | 45.9% | 54.1% | $755 | dominated by B2 |
| 5 | A4 2 micros + brake<50% -> 1 | 14 | 23 | 52.8% | 47.2% | $869 | moderate; brake adds +7 pass pts vs fixed 2 |
| 6 | C1 stop $125 x2 (same $250 worst case) | 14 | 24 | 51.3% | 48.7% | $844 | no gain: lower pass than $250 stop at 1 micro, no better than A4 |
| 7 | A1 fixed 2 | 12 | 19 | 45.5% | 54.5% | $750 | fixed 2 is worse than A4 |
Not helpful: brakes at 3-4 micros (A5/A6/A7/B5/E3 pass 41-46%, lower than no brake: the brake leaves a bigger recovery gap so it stalls and then busts), C2/C4 tighter stop at 3x (42-44%), day lock-in (no effect at 50%, -3 pts at 33%), 30-min NOISE checks (D1/D3: pass 51-52% vs 63%, hurts, more trades but more whipsaw; era2 worse), max entries 5 (D2: +1 pt, no speed change, 7 extra trades in 5 years), OD pullback as extra (D4: +3 pts pass at 1 micro, median 37, +$53 value; era-consistent, tiny; D5 with 30-min loses it). Extra trades do not speed the pass; size is what speeds it. The only free improvement found is D4 (+3 pts pass, +$53 value/eval, no extra speed) and E2 = 2 micros + brake + OD (55.3% pass, chain 22).
Note OD is flagged PAPER-only by D55 in CLAUDE.md; it would need approval for EVAL accounts, and was run with its stop capped at $250.

## ADDENDUM (user asked: full B, C, D and all E combinations, no pruning). 76 further variants, same method; supersedes the pruned ranking above.
Datasets: main=NOISE$250+fade; s30=30-min checks; m5=5 entries; s30m5; od=+opening-drive pullback (stop capped $250); t125/t150=tight stops; DE rows = every dataset x 5 sizings. Sizing: xN = N micros; sprint<50%->1 = 1 micro when <50% of target left; lock = stop the day at that fraction of remaining target.

| variant | pass | bust | med | p75 | chain | evals/funded | value/eval | era1 pass/bust/med/chain | era2 |
|---|---|---|---|---|---|---|---|---|---|
| B 3mic sprint<30%->1 lock none [main] | 47.9% | 52.1% | 7 | 12 | 12 | 2.09 | $788 | 47%/53%/8/13 | 49%/51%/6/12 |
| B 3mic sprint<30%->1 lock 0.33 [main] | 47.6% | 52.4% | 7 | 12 | 13 | 2.10 | $783 | 46%/54%/8/14 | 49%/51%/7/12 |
| B 3mic sprint<30%->1 lock 0.5 [main] | 47.7% | 52.3% | 7 | 12 | 12 | 2.10 | $786 | 47%/53%/8/13 | 49%/51%/7/12 |
| B 3mic sprint<50%->1 lock none [main] | 50.1% | 49.9% | 10 | 17 | 16 | 2.00 | $825 | 51%/49%/12/16 | 50%/50%/9/15 |
| B 3mic sprint<50%->1 lock 0.33 [main] | 49.9% | 50.1% | 11 | 17 | 16 | 2.00 | $822 | 50%/50%/12/17 | 50%/50%/9/15 |
| B 3mic sprint<50%->1 lock 0.5 [main] | 50.1% | 49.9% | 10 | 17 | 16 | 2.00 | $825 | 51%/49%/12/16 | 50%/50%/9/15 |
| B 4mic sprint<30%->1 lock none [main] | 49.4% | 50.6% | 5 | 9 | 9 | 2.02 | $813 | 51%/49%/6/10 | 48%/52%/5/9 |
| B 4mic sprint<30%->1 lock 0.33 [main] | 49.4% | 50.6% | 5 | 9 | 9 | 2.02 | $813 | 51%/49%/6/10 | 48%/52%/5/9 |
| B 4mic sprint<30%->1 lock 0.5 [main] | 49.4% | 50.6% | 5 | 9 | 9 | 2.02 | $813 | 51%/49%/6/10 | 48%/52%/5/9 |
| B 4mic sprint<50%->1 lock none [main] | 52.4% | 47.6% | 7 | 14 | 11 | 1.91 | $863 | 56%/44%/7/11 | 49%/51%/6/11 |
| B 4mic sprint<50%->1 lock 0.33 [main] | 52.3% | 47.7% | 7 | 14 | 11 | 1.91 | $861 | 56%/44%/8/11 | 49%/51%/7/11 |
| B 4mic sprint<50%->1 lock 0.5 [main] | 52.4% | 47.6% | 7 | 14 | 11 | 1.91 | $863 | 56%/44%/8/11 | 49%/51%/7/11 |
| C t125 x2 sprint none | 51.3% | 48.7% | 14 | 24 | 24 | 1.95 | $844 | 57%/43%/17/25 | 46%/54%/12/23 |
| C t125 x2 sprint 0.5 | 52.1% | 47.9% | 19 | 29 | 28 | 1.92 | $858 | 57%/43%/22/29 | 48%/52%/16/28 |
| C t125 x3 sprint none | 43.7% | 56.3% | 7 | 11 | 13 | 2.29 | $719 | 45%/55%/7/13 | 42%/58%/6/13 |
| C t125 x3 sprint 0.5 | 50.4% | 49.6% | 12 | 21 | 18 | 1.98 | $830 | 56%/44%/13/17 | 45%/55%/11/19 |
| C t125 x4 sprint none | 41.1% | 58.9% | 4 | 7 | 9 | 2.43 | $677 | 44%/56%/4/9 | 38%/62%/4/10 |
| C t125 x4 sprint 0.5 | 46.5% | 53.5% | 7 | 15 | 13 | 2.15 | $766 | 53%/47%/7/12 | 41%/59%/7/13 |
| C t150 x2 sprint none | 49.4% | 50.6% | 13 | 21 | 22 | 2.02 | $813 | 50%/50%/14/23 | 49%/51%/12/22 |
| C t150 x2 sprint 0.5 | 51.9% | 48.1% | 18 | 29 | 27 | 1.93 | $855 | 53%/47%/20/28 | 51%/49%/16/26 |
| C t150 x3 sprint none | 41.3% | 58.7% | 6 | 10 | 13 | 2.42 | $680 | 42%/58%/6/14 | 40%/60%/6/12 |
| C t150 x3 sprint 0.5 | 48.7% | 51.3% | 10 | 18 | 16 | 2.05 | $802 | 54%/46%/12/17 | 44%/56%/8/16 |
| C t150 x4 sprint none | 41.3% | 58.7% | 4 | 6 | 9 | 2.42 | $680 | 42%/58%/4/9 | 41%/59%/4/9 |
| C t150 x4 sprint 0.5 | 48.1% | 51.9% | 7 | 14 | 12 | 2.08 | $791 | 51%/49%/7/12 | 46%/54%/7/12 |
| DE main x1 {} | 63.4% | 34.4% | 36 | 56 | 47 | 1.58 | $1,044 | 66%/31%/41/56 | 61%/37%/32/40 |
| DE main x2 {'brake': (0.5, 1)} | 52.8% | 47.2% | 14 | 25 | 23 | 1.89 | $869 | 52%/48%/15/26 | 54%/46%/13/21 |
| DE main x3 {'sprint': (0.5, 1), 'lock': 0.33} | 49.9% | 50.1% | 11 | 17 | 16 | 2.00 | $822 | 50%/50%/12/17 | 50%/50%/9/15 |
| DE main x4 {'sprint': (0.5, 1)} | 52.4% | 47.6% | 7 | 14 | 11 | 1.91 | $863 | 56%/44%/7/11 | 49%/51%/6/11 |
| DE main x4 {'sprint': (0.5, 1), 'lock': 0.5} | 52.4% | 47.6% | 7 | 14 | 11 | 1.91 | $863 | 56%/44%/8/11 | 49%/51%/7/11 |
| DE s30 x1 {} | 51.8% | 43.7% | 32 | 46 | 48 | 1.93 | $852 | 58%/32%/33/57 | 46%/54%/31/45 |
| DE s30 x2 {'brake': (0.5, 1)} | 53.6% | 46.4% | 14 | 24 | 23 | 1.86 | $883 | 55%/45%/16/27 | 53%/47%/13/21 |
| DE s30 x3 {'sprint': (0.5, 1), 'lock': 0.33} | 56.7% | 43.3% | 12 | 20 | 16 | 1.76 | $933 | 58%/42%/12/15 | 55%/45%/10/16 |
| DE s30 x4 {'sprint': (0.5, 1)} | 57.0% | 43.0% | 8 | 14 | 11 | 1.75 | $938 | 61%/39%/8/11 | 53%/47%/7/11 |
| DE s30 x4 {'sprint': (0.5, 1), 'lock': 0.5} | 57.0% | 43.0% | 8 | 14 | 11 | 1.75 | $938 | 61%/39%/8/11 | 53%/47%/7/11 |
| DE m5 x1 {} | 64.6% | 33.2% | 36 | 56 | 47 | 1.55 | $1,063 | 66%/31%/41/56 | 63%/35%/30/38 |
| DE m5 x2 {'brake': (0.5, 1)} | 50.1% | 49.9% | 13 | 22 | 23 | 2.00 | $825 | 52%/48%/15/26 | 49%/51%/11/21 |
| DE m5 x3 {'sprint': (0.5, 1), 'lock': 0.33} | 49.6% | 50.4% | 10 | 17 | 16 | 2.02 | $816 | 50%/50%/12/17 | 49%/51%/9/16 |
| DE m5 x4 {'sprint': (0.5, 1)} | 52.3% | 47.7% | 7 | 13 | 11 | 1.91 | $861 | 56%/44%/7/11 | 49%/51%/6/11 |
| DE m5 x4 {'sprint': (0.5, 1), 'lock': 0.5} | 52.3% | 47.7% | 7 | 13 | 11 | 1.91 | $861 | 56%/44%/8/11 | 49%/51%/7/11 |
| DE s30m5 x1 {} | 51.1% | 44.5% | 31 | 46 | 50 | 1.96 | $841 | 58%/33%/33/57 | 45%/55%/29/47 |
| DE s30m5 x2 {'brake': (0.5, 1)} | 52.6% | 47.4% | 14 | 24 | 24 | 1.90 | $866 | 55%/45%/16/25 | 51%/49%/13/22 |
| DE s30m5 x3 {'sprint': (0.5, 1), 'lock': 0.33} | 56.3% | 43.7% | 12 | 19 | 16 | 1.78 | $927 | 58%/42%/12/15 | 55%/45%/10/16 |
| DE s30m5 x4 {'sprint': (0.5, 1)} | 56.7% | 43.3% | 8 | 14 | 11 | 1.76 | $933 | 61%/39%/8/11 | 53%/47%/7/11 |
| DE s30m5 x4 {'sprint': (0.5, 1), 'lock': 0.5} | 56.7% | 43.3% | 7 | 14 | 11 | 1.76 | $933 | 61%/39%/8/11 | 53%/47%/7/11 |
| DE od x1 {} | 66.6% | 31.9% | 37 | 55 | 46 | 1.50 | $1,097 | 68%/31%/41/54 | 65%/33%/31/40 |
| DE od x2 {'brake': (0.5, 1)} | 55.3% | 44.7% | 13 | 22 | 22 | 1.81 | $911 | 53%/47%/14/25 | 57%/43%/12/20 |
| DE od x3 {'sprint': (0.5, 1), 'lock': 0.33} | 51.8% | 48.2% | 10 | 16 | 15 | 1.93 | $852 | 51%/49%/11/16 | 53%/47%/9/15 |
| DE od x4 {'sprint': (0.5, 1)} | 53.5% | 46.5% | 7 | 13 | 11 | 1.87 | $880 | 56%/44%/7/11 | 51%/49%/7/10 |
| DE od x4 {'sprint': (0.5, 1), 'lock': 0.5} | 53.3% | 46.7% | 7 | 12 | 10 | 1.88 | $877 | 55%/45%/8/11 | 52%/48%/7/10 |
| DE s30m5od x1 {} | 62.1% | 33.6% | 34 | 52 | 44 | 1.61 | $1,022 | 66%/25%/36/55 | 59%/41%/32/40 |
| DE s30m5od x2 {'brake': (0.5, 1)} | 53.5% | 46.5% | 13 | 23 | 22 | 1.87 | $880 | 55%/45%/14/25 | 52%/48%/12/19 |
| DE s30m5od x3 {'sprint': (0.5, 1), 'lock': 0.33} | 58.0% | 42.0% | 12 | 19 | 15 | 1.72 | $955 | 58%/42%/13/15 | 58%/42%/10/15 |
| DE s30m5od x4 {'sprint': (0.5, 1)} | 57.0% | 43.0% | 7 | 13 | 10 | 1.75 | $938 | 61%/39%/8/10 | 54%/46%/7/10 |
| DE s30m5od x4 {'sprint': (0.5, 1), 'lock': 0.5} | 57.7% | 42.3% | 7 | 13 | 10 | 1.73 | $950 | 61%/39%/8/10 | 54%/46%/6/10 |
| DE t125 x1 {} | 61.4% | 34.6% | 44 | 59 | 58 | 1.63 | $1,011 | 70%/25%/47/57 | 54%/43%/38/59 |
| DE t125 x2 {'brake': (0.5, 1)} | 51.4% | 48.6% | 15 | 31 | 29 | 1.94 | $847 | 57%/43%/18/30 | 46%/54%/13/29 |
| DE t125 x3 {'sprint': (0.5, 1), 'lock': 0.33} | 50.3% | 49.7% | 12 | 21 | 18 | 1.99 | $827 | 56%/44%/14/17 | 45%/55%/10/19 |
| DE t125 x4 {'sprint': (0.5, 1)} | 46.5% | 53.5% | 7 | 15 | 13 | 2.15 | $766 | 53%/47%/7/12 | 41%/59%/7/13 |
| DE t125 x4 {'sprint': (0.5, 1), 'lock': 0.5} | 46.4% | 53.6% | 7 | 14 | 13 | 2.16 | $764 | 53%/47%/8/12 | 40%/60%/7/13 |
| DE t150 x1 {} | 56.2% | 43.7% | 36 | 56 | 52 | 1.78 | $925 | 61%/39%/43/62 | 52%/48%/30/46 |
| DE t150 x2 {'brake': (0.5, 1)} | 53.1% | 46.9% | 15 | 30 | 28 | 1.88 | $875 | 53%/47%/16/30 | 53%/47%/14/27 |
| DE t150 x3 {'sprint': (0.5, 1), 'lock': 0.33} | 48.4% | 51.6% | 11 | 19 | 17 | 2.07 | $797 | 54%/46%/13/17 | 43%/57%/9/16 |
| DE t150 x4 {'sprint': (0.5, 1)} | 48.1% | 51.9% | 7 | 14 | 12 | 2.08 | $791 | 51%/49%/7/12 | 46%/54%/7/12 |
| DE t150 x4 {'sprint': (0.5, 1), 'lock': 0.5} | 47.7% | 52.3% | 7 | 14 | 12 | 2.10 | $786 | 51%/49%/7/12 | 45%/55%/7/12 |
| DE t125_s30m5 x1 {} | 61.6% | 37.1% | 35 | 52 | 48 | 1.62 | $1,013 | 63%/35%/37/56 | 61%/39%/34/45 |
| DE t125_s30m5 x2 {'brake': (0.5, 1)} | 53.8% | 46.2% | 14 | 26 | 24 | 1.86 | $886 | 58%/42%/16/22 | 50%/50%/12/24 |
| DE t125_s30m5 x3 {'sprint': (0.5, 1), 'lock': 0.33} | 56.3% | 43.7% | 12 | 21 | 16 | 1.78 | $927 | 65%/35%/14/15 | 48%/52%/9/16 |
| DE t125_s30m5 x4 {'sprint': (0.5, 1)} | 52.6% | 47.4% | 7 | 14 | 12 | 1.90 | $866 | 58%/42%/8/11 | 48%/52%/6/12 |
| DE t125_s30m5 x4 {'sprint': (0.5, 1), 'lock': 0.5} | 53.0% | 47.0% | 7 | 14 | 11 | 1.89 | $872 | 58%/42%/8/11 | 48%/52%/6/12 |
| DE t125_od x1 {} | 59.5% | 37.9% | 39 | 55 | 56 | 1.68 | $980 | 67%/30%/43/56 | 52%/45%/36/56 |
| DE t125_od x2 {'brake': (0.5, 1)} | 56.8% | 43.2% | 16 | 29 | 26 | 1.76 | $936 | 58%/42%/17/27 | 55%/45%/15/26 |
| DE t125_od x3 {'sprint': (0.5, 1), 'lock': 0.33} | 52.4% | 47.6% | 12 | 20 | 18 | 1.91 | $863 | 55%/45%/14/18 | 50%/50%/11/18 |
| DE t125_od x4 {'sprint': (0.5, 1)} | 49.1% | 50.9% | 7 | 14 | 13 | 2.04 | $808 | 55%/45%/7/12 | 43%/57%/7/14 |
| DE t125_od x4 {'sprint': (0.5, 1), 'lock': 0.5} | 49.2% | 50.8% | 7 | 14 | 13 | 2.03 | $811 | 55%/45%/7/12 | 44%/56%/7/14 |
