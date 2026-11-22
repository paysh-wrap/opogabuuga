# NOISE + CANDACE with a $125 risk cap and more trades (C125 study, Pro 25K and 50K, EOD, all Lucid rules on)

Research only. No app code, config or frontend changed; nothing committed. Builds on `../pass_faster/` (simulator `pf_sim.py`, NOISE stream, rules and verdict rule unchanged). Full tables: `tables.md`; raw numbers: `results.json`.

## Interpretation of the ask (as instructed)
Today on Pro 25K CANDACE's Lucid-fit risk is $158.33 and its grade rule (C = a quarter) sizes 209 of 304 signals to 0 micros. Here "lower stop loss $125 + more trades" = each CANDACE trade's dollar risk (stop $ + fee + slippage) is capped at min(Lucid fit, $125), and no signal is shrunk to 0 by the grade rule (grade multiplier is tighten-only but floored at 1 micro). The CANDACE stop placement (beyond the sweep) is unchanged; only size changes. A signal is still skipped if even 1 micro does not fit inside min(Lucid fit, $125) (Lucid fit stays on; this never happened on the stream: 0 signals sized to 0). NOISE is exactly BASE.

Variants: **C125** (cap $125, min 1 micro, grade multiplier floored at 1), **C125_1** (always exactly 1 micro), **C125_W1030** (C125 + CANDACE `ny_window` 09:00-10:30; engine stream regenerated: 798 signals vs 310; 786 from 2021-10-21).

## Reproduction first (passed)
`run_c125.py check` re-ran BASE and NOISE+CANDACE with this study's code: all 12 compared numbers (pass %, bust+stuck %, running %, median, 75th pct days, static 1-micro / plan-sized profit, drawdown; 25K and 50K; ALL and JUDGE) are identical to `pass_faster/results.json` / RESULTS.md. The regenerated CANDACE base stream is byte-identical to `pass_faster/streams_candace.csv`.

## Headline (rolling starts; P / bust+stuck / running %; days = sessions)

| plan | variant | 5y P / B / R | 5y median / p75 d | 5y <=60 d % | judge P / B / R | judge median / p75 d | judge <=60 d % | pick P / B / R | pick median d | 5y plan-sized $ | judge plan-sized $ | CANDACE taken / signals (5y) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | BASE | 59 / 36 / 6 | 74 / 122 | 23 | 39 / 52 / 10 | 50 / 73 | 24 | 59 / 16 / 26 | 74 | 19,293 | 10,826 | - |
| 25K | N+CANDACE (earlier) | 50 / 46 / 4 | 59 / 92 | 25 | 39 / 54 / 8 | 52 / 72 | 23 | 60 / 15 / 25 | 62 | 19,546 | 10,429 | 94 / 304 (209 to 0) |
| 25K | C125 | 50 / 45 / 5 | 48 / 71 | 32 | 41 / 50 / 9 | 47 / 71 | 26 | 57 / 31 / 12 | 47 | 21,526 | 11,804 | 303 / 304 |
| 25K | C125_1 | 50 / 45 / 5 | 48 / 72 | 32 | 41 / 50 / 9 | 47 / 71 | 26 | 57 / 30 / 12 | 47 | 21,501 | 11,788 | 303 / 304 |
| 25K | C125_W1030 | 45 / 51 / 4 | 42 / 62 | 33 | 43 / 50 / 7 | 45 / 64 | 30 | 46 / 42 / 13 | 37 | 21,177 | 12,252 | 683 / 786 |
| 50K | BASE | 69 / 21 / 10 | 92 / 132 | 20 | 55 / 27 / 17 | 83 / 123 | 19 | 73 / 0 / 27 | 86 | 38,586 | 21,651 | - |
| 50K | N+CANDACE (earlier) | 63 / 27 / 10 | 78 / 114 | 25 | 42 / 40 / 17 | 67 / 94 | 20 | 72 / 1 / 27 | 68 | 40,430 | 21,988 | 303 / 304 |
| 50K | C125 | 61 / 29 / 10 | 74 / 109 | 24 | 43 / 40 / 17 | 67 / 92 | 20 | 73 / 0 / 27 | 71 | 41,167 | 22,778 | 303 / 304 |
| 50K | C125_1 | 61 / 29 / 10 | 75 / 109 | 24 | 43 / 40 / 17 | 67 / 92 | 20 | 73 / 0 / 27 | 73 | 41,154 | 22,762 | 303 / 304 |
| 50K | C125_W1030 | 62 / 30 / 8 | 71 / 114 | 26 | 44 / 41 / 14 | 63 / 94 | 21 | 73 / 0 / 27 | 68 | 40,752 | 23,194 | 683 / 786 |

Trades per week (static): 25K BASE 2.6 -> N+CANDACE 3.0 -> C125 3.8 -> C125_W1030 5.3 (judge: 2.5 / 2.8 / 3.5 / 4.8). CANDACE skipped: 1 signal because a NOISE position was open (W1030: 103 of 786), 0 sized to 0 in all three new variants. NOISE signals skipped because CANDACE held the account: 16 over 5 years (5 earlier).

## What the numbers say
- The cap and the min-1-micro rule do what was asked: CANDACE trades go from 94 to 303 of 304 signals on 25K, total profit rises on both plans and every window (5y plan-sized 25K +$2,234 vs BASE; judge +$978; 50K +$2,581 / +$1,126), and worst static drawdown is lower (25K $1,967 vs $2,096).
- Because CANDACE now trades on every signal, passing is faster when it happens: 25K 5y median 48 d vs 74 (earlier N+CANDACE 59), judge 47 vs 50; share of ALL starts passing within 60 sessions 32% vs 23% (25K 5y), 26% vs 24% (judge); 50K 24% vs 20%, 20% vs 19%.
- But the pass rate over 5 years is lower and bust+stuck higher: 25K 50% vs 59% pass (+9.4 pts bust+stuck), 50K 61% vs 69% (+7.6). 50K judge window is worse too (43% vs 55% pass, +12.3 pts bust+stuck). Only 25K judge window looks good (41% vs 39%, bust -1.4 pts). On the 25K pick window rolling bust+stuck is 31% vs 16% (pass 57% vs 59%), so the improvement is not consistent across windows. The session-21 bootstrap cross-check is mixed, closer to neutral: 25K pass 58-59% vs 57% (5y), judge 47 vs 47; 50K 68-69 vs 65 (5y), judge 58 vs 56, but L12 is lower (25K 36 vs 40, 50K 48 vs 52).
- Lowering the stop does not fix the drop: C125 and C125_1 are nearly identical (the $125 cap rarely binds beyond 1 micro for typical 20-40 pt stops), so the extra trades, not the size, drive the results. The accounts lost vs BASE are the same long-running ones near the floor noted in the earlier study (5y rolling starts overlap heavily; about 20 independent evaluation lengths), so treat the 5-year gap as fragile but not as supportive.
- C125_W1030 (window to 10:30) is the fastest (25K 5y median 42 d, 60-day pass 33%; judge 45 d, 30%) and has the highest judge profit (25K $12,252, 50K $23,194) but it has the lowest 25K 5-year pass rate (45% vs 59%, bust+stuck 51%) and the 25K pick window is clearly worse (46% pass, 42% bust+stuck). In the pick window its static profit is still above BASE (25K plan-sized $8,924 vs $8,468), so the loss is in survival, not profit.

## Verdict (rule: judge window AND 5 years, on BOTH plans: median days lower OR pass higher; bust+stuck not higher by more than 2 pts; total profit not lower than BASE)

| variant | 25K judge | 25K 5y | 50K judge | 50K 5y | cells passed |
|---|---|---|---|---|---|
| C125 | PASS | FAIL (bust +9.4) | FAIL (bust +12.3) | FAIL (bust +7.6) | 1 of 4 |
| C125_1 | PASS | FAIL (bust +9.4) | FAIL (bust +12.3) | FAIL (bust +7.6) | 1 of 4 |
| C125_W1030 | PASS | FAIL (bust +14.9) | FAIL (bust +14.0) | FAIL (bust +8.5) | 1 of 4 |

**None of the three meets the rule, so none is recommended for building.** Profit is never below BASE in any cell (so the "no profit cut" rule is satisfied), but the bust/stuck criterion fails in 3 of 4 cells for every variant. One caution on the literal rule: "median days lower OR pass higher" reads "yes" in all cells because the median is taken only over accounts that pass (survivorship), even where the pass rate is lower; I applied it literally and the verdict does not depend on it, because the bust criterion fails. Compared with the earlier NOISE+CANDACE (which failed 0 of 4 cells in the judge/5y rolling check on profit and bust), C125 is better on profit and speed but not on bust.

**Multiple testing:** three variants on top of the earlier three tests, one 5-year MNQ sample, judge window already seen by many sessions; rolling starts overlap heavily, so 2-4 point differences are within noise. The one cell that passes (25K judge) is the same pattern as LOCK80 in the earlier study: good in the last 33 months only. The conclusion is "no demonstrated gain in pass rate", not "proven harmful"; the clear, repeatable effects are more trades (+1 to +2.7 per week), higher profit, faster passes when they happen, and more accounts stuck.

## Method and files
- `gen_w1030.py`: regenerates CANDACE streams (`streams_candace_base.csv` = D154 defaults, identical to the earlier file; `streams_candace_w1030.csv` = `ny_window` "09:00-10:30"), engine `candace_ict.replay_day` through the same harness.
- `run_c125.py`: swaps only the CANDACE sizing function inside `pf_sim` (risk = min(Lucid fit, $125); contracts = floor(risk / per-micro cost), max micros cap; C125 then grade multiplier floored at 1; C125_1 = 1). Everything else (NOISE sizing, room/shrink/brake, DLL incl. LucidScale, 40% consistency, 38% day stop, kill distance, STUCK = NOISE cannot be sized, one position at a time, same-minute rule) is the earlier simulator. `python3 run_c125.py check` = reproduction; no argument = full run to `results.json`.
- `report.py`: builds `tables.md` (rolling and bootstrap tables, static profit and CANDACE taken/skipped, verdict cells).
- Not run: the stuck-mix sensitivity (account not stuck while CANDACE could still size); it only moves accounts from bust to running in the earlier study.
- Caveat: window 10:30 signals use the same engine with a longer `ny_window` and the same Lucid fit, not tested beyond this harness; the 10:00-10:30 signals overlap NOISE's 10:00 check, handled by one position at a time (103 CANDACE signals skipped for an open NOISE position).
