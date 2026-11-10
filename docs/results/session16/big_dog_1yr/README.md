# Big Dog Small Trade Aggressive, last 12 months (session 16)

Research only. No backend/frontend code touched. **AI accuracy is SIMULATED (unproven; published LLM next-day accuracy is 50-56%). One year (about 257 sessions) is a SMALL sample. Every number is a bound ("if the AI were X% right"), not a forecast.**

## Verdict (plain language)
- At 50-55% accuracy (the only published range) Big Dog loses money on every plan: 50% = net -2,228 (Pro 25K) to -8,550 (Pro 150K); eval pass only 12-14%, eval bust 82-88%.
- It only turns clearly positive at 65-70% simulated accuracy (PF 1.07-1.14); even at 70% eval pass is only 35-50% (Pro 150K best 44%) and funded accounts bust 70-91% in year 1.
- Risk of ruin is the issue, not trade count: about 2 to 3 trades a day with 3 micros per $1,000 of loss limit and 12.5% per-trade risk means 8 full stop-outs reach the loss limit, and the edge per trade is small (PF 1.0-1.2).
- The extras (BE at +1R, trails, locks) cut average winners; at 2R target, a 50% win rate with scratches is roughly break-even after costs, so accuracy above about 65% is needed.
- Verdict: not proven and not safe to rely on; keep it paper/SEMI until the AI ledger shows real accuracy of 65%+ over many sessions, and do not size up on the strength of this one year.

## Method
- Data: Databento `MNQ.v.0` and `MGC.v.0` 1-minute (volume roll), cached CSVs, 2025-11-01 to 2026-10-31 (MNQ and MGC usable days after the same roll/bad-print guard as the AI Duo study). Loader, RTH-anchored VWAP (09:30) and 5-minute bars reused from `../ai_duo_window/ai_duo_window.py`; account engine (`eval_run`, `funded_run`, `plan_rules` reading `config/rules/*.yaml`) reused from `../../session15/lib.py`.
- AI side SIMULATED: correct with probability = accuracy versus the day's real RTH open-to-close direction, independent per market, 27% NEUTRAL days skipped at random. 200 seeds per cell for trade statistics (means).
- Window 09:36-11:30 ET (first 5m bar closing after 09:36, i.e. entry about 09:40; 09:30-09:35 bars excluded). Entry = first 5m bar that pulls back to VWAP and closes in the AI direction; fill at next 1m open + 1 tick; re-entry allowed on later pullbacks after the previous exit (one position per market at a time; MNQ and MGC may overlap; no hedging since they are in different hedge groups).
- Stop = pullback extreme (two 5m bars) +/- 1 tick, widened to at least $10 of risk per micro (assumption); signal skipped if 1 micro does not fit the per-trade budget. Target 2R (limit, needs 1-tick trade-through). Stop moves: BE (entry) at +1R; trail 1R behind best price from +1.5R; MNQ lock +100 pt then stop to entry+50 pt; MGC step trail 20 ticks per 60 ticks gained (my reading of "20 ticks per 60"). Same-bar stop and target counts as stop. Flat at 11:30.
- Costs: 1 tick slippage on entry, stop and flat exits; fee per micro round trip MNQ $1.00, MGC $1.60 (from the rule files).
- Plan sizing: per-trade max loss 12.5% of plan MLL distance (Pro 25K $125); max micros = 3 x MLL/$1,000 (25K 3, 50K 6, 100K 9, 150K 13) reduced to fit the budget; day loss limit 37.5% of MLL ($375 on 25K; also reduces size to fit what remains); max 5 trades a day across both markets; stop after 3 losses; day stop when session profit >= 39% of the plan's eval profit target. Pro / Flex / Daily of the same size share sizing; they differ only in account rules (target, DLL, consistency, minimum profitable days, payout rules) from `config/rules`.
- Account tests: the per-day trade table of each seed is block-bootstrapped (blocks of 10 sessions, 25 paths per seed over 200 seeds = 5,000 paths per cell). Eval runs up to 750 sessions: PASS = target reached with the plan's consistency and profitable-day rules, BUST = EOD loss limit touched (including intraday worst open loss per trade). Funded = first 260 sessions with payout rules of the plan (weekly-style cadence every 10 sessions); funded $/2wk = mean paid to trader per 2 weeks over the year including busted paths.
- `avg $/2wk` in the main columns = trading net divided by (sessions/10), no account rules. `win` counts trades with pnl > 0 (a BE scratch after costs is a loss). `max DD` is trade-by-trade on closed trades.
- Limitations: no 08:30 news flatten; MGC leg shares the MNQ-based AI truth (RTH open-to-close) which is a loose proxy for gold; bootstrap resamples one year of days so tail risk beyond that year is not captured; Flex DLL is not enforced (not stated in the rule file); Daily 25K funded rules as in the YAML (VERIFY items unconfirmed); one-year sample, so differences of a few points between cells are noise.

## Results (mean over seeds; trades and returns are for 12 months, 1 account)

| plan | AI acc | trades | /day | win | PF | net $ | max DD $ | avg $/2wk | eval pass | eval bust | median days to pass | funded bust (1st yr) | funded $/2wk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pro 25K | 50% | 460 | 1.79 | 47% | 0.89 | -2,228 | -3,970 | -87 | 14% | 86% | 46 | 98% | +4 |
| Pro 25K | 60% | 469 | 1.83 | 49% | 0.97 | -585 | -3,151 | -23 | 25% | 75% | 47 | 94% | +10 |
| Pro 25K | 65% | 472 | 1.84 | 49% | 0.99 | -231 | -3,126 | -9 | 28% | 72% | 47 | 93% | +12 |
| Pro 25K | 70% | 478 | 1.86 | 50% | 1.05 | +808 | -2,730 | +31 | 36% | 64% | 44 | 88% | +21 |
| Pro 50K | 50% | 642 | 2.50 | 52% | 0.96 | -2,313 | -7,676 | -90 | 18% | 82% | 44 | 96% | +20 |
| Pro 50K | 60% | 655 | 2.55 | 54% | 1.06 | +2,772 | -5,688 | +108 | 35% | 65% | 44 | 87% | +48 |
| Pro 50K | 65% | 660 | 2.57 | 55% | 1.08 | +4,049 | -5,444 | +158 | 38% | 62% | 43 | 85% | +61 |
| Pro 50K | 70% | 670 | 2.61 | 56% | 1.16 | +7,528 | -4,636 | +293 | 50% | 50% | 40 | 75% | +100 |
| Pro 100K | 50% | 669 | 2.60 | 53% | 0.94 | -5,281 | -12,894 | -205 | 12% | 88% | 62 | 96% | +22 |
| Pro 100K | 60% | 683 | 2.66 | 55% | 1.04 | +2,912 | -9,090 | +113 | 25% | 75% | 60 | 89% | +57 |
| Pro 100K | 65% | 688 | 2.68 | 56% | 1.07 | +5,179 | -8,408 | +202 | 31% | 69% | 60 | 85% | +72 |
| Pro 100K | 70% | 698 | 2.72 | 57% | 1.14 | +10,656 | -7,075 | +415 | 43% | 57% | 54 | 74% | +124 |
| Pro 150K | 50% | 675 | 2.63 | 54% | 0.94 | -8,550 | -20,375 | -333 | 12% | 88% | 55 | 96% | +27 |
| Pro 150K | 60% | 689 | 2.68 | 56% | 1.04 | +4,739 | -14,148 | +184 | 26% | 74% | 56 | 87% | +72 |
| Pro 150K | 65% | 694 | 2.70 | 56% | 1.07 | +8,179 | -13,119 | +318 | 31% | 69% | 54 | 83% | +90 |
| Pro 150K | 70% | 704 | 2.74 | 57% | 1.14 | +17,110 | -10,890 | +666 | 44% | 56% | 50 | 70% | +156 |
| Flex 25K | 50% | 460 | 1.79 | 47% | 0.89 | -2,228 | -3,970 | -87 | 14% | 86% | 47 | 98% | +5 |
| Flex 25K | 60% | 469 | 1.83 | 49% | 0.97 | -585 | -3,151 | -23 | 24% | 76% | 48 | 95% | +9 |
| Flex 25K | 65% | 472 | 1.84 | 49% | 0.99 | -231 | -3,126 | -9 | 27% | 73% | 48 | 94% | +10 |
| Flex 25K | 70% | 478 | 1.86 | 50% | 1.05 | +808 | -2,730 | +31 | 35% | 65% | 45 | 89% | +16 |
| Flex 50K | 50% | 642 | 2.50 | 52% | 0.96 | -2,313 | -7,676 | -90 | 18% | 82% | 45 | 97% | +18 |
| Flex 50K | 60% | 655 | 2.55 | 54% | 1.06 | +2,772 | -5,688 | +108 | 34% | 66% | 44 | 91% | +31 |
| Flex 50K | 65% | 660 | 2.57 | 55% | 1.08 | +4,049 | -5,444 | +158 | 38% | 62% | 43 | 89% | +37 |
| Flex 50K | 70% | 670 | 2.61 | 56% | 1.16 | +7,528 | -4,636 | +293 | 50% | 50% | 40 | 81% | +52 |
| Flex 100K | 50% | 669 | 2.60 | 53% | 0.94 | -5,281 | -12,894 | -205 | 12% | 88% | 62 | 98% | +23 |
| Flex 100K | 60% | 683 | 2.66 | 55% | 1.04 | +2,912 | -9,090 | +113 | 25% | 75% | 60 | 93% | +39 |
| Flex 100K | 65% | 688 | 2.68 | 56% | 1.07 | +5,179 | -8,408 | +202 | 31% | 69% | 60 | 91% | +46 |
| Flex 100K | 70% | 698 | 2.72 | 57% | 1.14 | +10,656 | -7,075 | +415 | 43% | 57% | 54 | 84% | +64 |
| Flex 150K | 50% | 675 | 2.63 | 54% | 0.94 | -8,550 | -20,375 | -333 | 12% | 88% | 55 | 98% | +34 |
| Flex 150K | 60% | 689 | 2.68 | 56% | 1.04 | +4,739 | -14,148 | +184 | 26% | 74% | 56 | 92% | +57 |
| Flex 150K | 65% | 694 | 2.70 | 56% | 1.07 | +8,179 | -13,119 | +318 | 31% | 69% | 54 | 90% | +65 |
| Flex 150K | 70% | 704 | 2.74 | 57% | 1.14 | +17,110 | -10,890 | +666 | 44% | 56% | 50 | 83% | +91 |
| Daily 25K | 50% | 460 | 1.79 | 47% | 0.89 | -2,228 | -3,970 | -87 | 14% | 86% | 47 | 98% | +5 |
| Daily 25K | 60% | 469 | 1.83 | 49% | 0.97 | -585 | -3,151 | -23 | 24% | 76% | 48 | 95% | +11 |
| Daily 25K | 65% | 472 | 1.84 | 49% | 0.99 | -231 | -3,126 | -9 | 27% | 73% | 48 | 95% | +13 |
| Daily 25K | 70% | 478 | 1.86 | 50% | 1.05 | +808 | -2,730 | +31 | 35% | 65% | 45 | 91% | +23 |

## Files
`big_dog_1yr.py` (simulation), `make_readme.py` (this table), `results.json` (every cell). Rerun: `python3 big_dog_1yr.py MNQ.csv MGC.csv 200 200 25` then `python3 make_readme.py`.
