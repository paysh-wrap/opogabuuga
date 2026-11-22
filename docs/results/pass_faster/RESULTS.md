# Pass faster: three offline tests vs the shipped NOISE eval config (Pro 25K and 50K, EOD, all Lucid rules on)

Research only. No app code, config or frontend changed; nothing committed. Scripts and raw numbers are in this folder.

## Plain-English summary

**Baseline reproduced first.** The session-21 realistic account simulator, run unchanged on the same stream, gives Pro 25K 57/43 (56 days) over 5 years and 40/60 (40 days) over the last 12 months, and Pro 50K 65/34 (78 days) and 52/48 (55 days): an exact match to `config/eval_odds.yaml` (see section 1). The simulator I used for the tests gives the identical numbers when only NOISE is on.

**Answer: none of the three is worth building.**

- **LOCK80 (lock trigger 80 pt instead of 100): fails the rule, but narrowly and mostly by noise.** On the held-out window it looks good on both sizes (25K pass 41% vs 39%, 50K 62% vs 55%, bust lower, profit higher), and 50K also over 5 years. But it is NOT faster (median days to pass 2-4 days longer on the judge window), it does not help in the pick window (2021-10..2023-12: pass 25K 66% vs 67%, 50K 76% vs 78%; static profit lower on 25K), and on Pro 25K over 5 years with rolling starts it is worse (pass 54% vs 59%, bust+stuck 40% vs 36%, a +4.6 pt bust rise, over the 2-pt limit). The paired by-quarter comparison is inside the noise (25K -3.8 +/- 5.0 pts, 50K +2.8 +/- 2.0). It is the same pattern session 19 saw (good in the last 12 months only). Verdict: FAIL on the stated rule (1 of 4 required cells fails) and not a speed-up.
- **NOISE + CANDACE: fails.** It does make passing faster when it passes (median days 59 vs 74 over 5 years on 25K, 78 vs 92 on 50K, 67 vs 83 on the judge 50K), but fewer accounts pass (5-year rolling: 25K 50% vs 59%, 50K 63% vs 69%; judge 50K 42% vs 55%) and more accounts end stuck (bust +2 to +13 pts), and on Pro 25K the plan-sized profit in the judge window is lower (-$397). On 25K CANDACE is sized to 0 micros for about 70% of its signals, so it adds almost nothing there. (For the accounts that do pass, CANDACE is slightly quicker: share of starts passing within 60 days 25% vs 23% on 25K and 25% vs 20% on 50K over 5 years, but that is within noise and does not offset the lost passes.) The 25K 5-year drop comes from one cluster (accounts started mid-2023 that were still running in Jan 2024), so treat it as fragile, but nothing in the numbers supports building it.
- **NOISE + CONTI VWAP: fails badly.** CONTI VWAP fires about 3.7 signals a day with an essentially flat edge (+$254 per micro over 5 years on 4,745 trades), 25 pt stops and heavy cost. On the same account it grinds the MLL room away: pass 9% (25K) and 9% (50K) over 5 years vs 59% / 69%, about 90% of accounts end stuck, and plan-sized profit falls by $6,900 (25K) and $13,700 (50K). The shorter median days (13-15) is survivorship: only the 9% that pass quickly are counted.

In the table below `pass / bust / running` are % of rolling starts; bust includes accounts stuck below the trading room (same definition as `eval_odds.yaml`; there are 0 outright kill-switch busts in any row). Days are trading sessions. `pass within 60 d` is the share of ALL starts that pass inside 60 sessions: it avoids the survivorship effect of a median taken only over the accounts that pass.

### Headline table (rolling starts, plan sizing: 25K = 1 micro, 50K = 2 micros with the brake)

| plan | test | 5y: pass / bust / running % | 5y median days | judge 2024-26: pass / bust / running % | judge median days | 5y plan-sized profit $ | judge plan-sized profit $ | rule met in (judge, 5y) windows |
|---|---|---|---|---|---|---|---|---|
| Pro 25K | BASE (NOISE shipped) | 59 / 36 / 6 | 74 | 39 / 52 / 10 | 50 | 19,293 | 10,826 | baseline |
| Pro 25K | LOCK80 (lock trigger 80 pt) | 54 / 40 / 5 | 67 | 41 / 50 / 9 | 53 | 19,634 | 11,674 | 1 of 2 |
| Pro 25K | NOISE + CANDACE | 50 / 46 / 4 | 59 | 39 / 54 / 8 | 52 | 19,546 | 10,429 | 0 of 2 |
| Pro 25K | NOISE + CONTI VWAP | 9 / 91 / 1 | 15 | 9 / 90 / 1 | 13 | 12,433 | 9,596 | 0 of 2 |
| Pro 50K | BASE (NOISE shipped) | 69 / 21 / 10 | 92 | 55 / 27 / 17 | 83 | 38,586 | 21,651 | baseline |
| Pro 50K | LOCK80 (lock trigger 80 pt) | 72 / 17 / 11 | 90 | 62 / 19 / 19 | 87 | 39,267 | 23,347 | 2 of 2 |
| Pro 50K | NOISE + CANDACE | 63 / 27 / 10 | 78 | 42 / 40 / 17 | 67 | 40,430 | 21,988 | 0 of 2 |
| Pro 50K | NOISE + CONTI VWAP | 9 / 90 / 1 | 15 | 10 / 88 / 2 | 13 | 24,866 | 19,193 | 0 of 2 |

**Verdict rule (all four cells must pass: 25K and 50K, judge window and 5 years):** median days lower OR pass % higher; bust+stuck not higher by more than 2 pts; total profit (plan-sized and 1-micro) not lower. Overall verdict: no test passes (the 'rule met' column must read 2 of 2 on BOTH plans; LOCK80 reads 1 of 2 on 25K and 2 of 2 on 50K, i.e. 3 of 4 cells). See section 3 for each cell. Caveat on the rule itself: the median is taken only over accounts that pass, so a test that makes many accounts fail can show a lower median by survivorship (CONTI VWAP, partly CANDACE); I mark the rule as met only literally in those cases.

**Multiple testing and reuse of data.** Three tests plus two sub-views, on one 5-year MNQ sample; 2024-26 was seen by many earlier sessions (including the LOCK80 idea itself, session 19 item 6a, which was found on the last 12 months). The rolling starts overlap heavily (about 20 independent evaluation lengths in 5 years), so a 2-4 point difference is not distinguishable from noise. Nothing here justifies building anything; LOCK80 is the only one that could be re-checked on genuinely new data.


---

## 1. Baseline reproduction (stop condition: passed)

Stream: session-20 `streams_BASE.csv` (NOISE, preset C lock +100 pt -> stop entry+10, Mondays off, no fade, 654 trades 2021-10-22..2026-10-30). I regenerated it from the engine-mirror generator (`session20/noise3.gen()`) on the shared days.pkl: **654/654 identical** (net $19,293). Simulator: session-21 `sim2.py` unchanged (paths patched only), session-21 bootstrap protocol (10-day blocks, uniform start, 600 paths x 400 sessions, seed 7, plan size tables, D57 shrink, kill distance, room check, brake, STUCK test with gmin $112).

| row | `eval_odds.yaml` (pass/bust, median days) | reproduced |
|---|---|---|
| Pro 25K, 5 years | 57/43, 56d | 57.3/42.7, 56.5d |
| Pro 25K, last 12 months | 40/60, 40d | 39.8/60.2, 40.0d |
| Pro 50K, 5 years | 65/34, 78d | 65.3/34.2, 77.5d |
| Pro 50K, last 12 months | 52/48, 55d | 52.3/47.7, 55.0d |

Exact match (within 0.5 pt, well inside +/-2). The test simulator `pf_sim.py` (NOISE + extra strategies on one account) was also run in NOISE-only mode and matches sim2 to the last digit on all 6 era x plan rows (`validate.py`); the float re-implementation of the CANDACE / VWAP Lucid fit matches the app's Decimal `lucid_fit` functions on 20,000 random inputs (0 mismatches).

## 2. Method

- **Account (all tests, 25K and 50K, EOD):** balance, trailing EOD MLL with lock (25K lock at 26,100 -> 25,100), DLL incl. LucidScale (60% of peak EOD profit once locked), 40% consistency at pass + 38% day stop (a trade is capped at the day stop and the day ends), kill distance + room check before every trade, D57 shrink for NOISE, the plan's size table and brake for NOISE, STUCK = NOISE can no longer be sized (counts as bust, as in `eval_odds.yaml`), max one position per account, no hedging (all MNQ, one position), flat by close (streams are flat by 16:00).
- **Streams:** NOISE base and LOCK80 from `noise3.gen()` (LOCK80 = `lock=(80, 10)`: trigger 80 pt, stop to entry+10; 647 trades, net $19,634 vs 654 / $19,293). CANDACE = engine `candace_ict.replay_day` with D154 defaults (keep_all_sweeps ON, 09:30-10:00), 310 signals (304 from 2021-10-21), through the existing study harness (`ctm_lib.engine_trades`, 3 prior days of history). CONTI VWAP = engine `conti_vwap.replay_day`, defaults, volume recovered from the stored VWAP as in session 21: 4,745 signals.
- **Sharing one account:** all signals of both strategies are merged by entry minute. A signal is skipped if its entry minute is at or before the exit minute of the position the account holds (NOISE's own same-bar flip is allowed as it is its own rule). A signal that sizes to 0 contracts does not block anything. NOISE exits are intrabar or at the open of the exit bar, so NOISE exit minute = exit bar + 0.5 (slightly conservative).
- **Sizing:** NOISE by its plan size table (25K: 1, 50K: 2 with brake) and the room/shrink logic of session 21. CANDACE and VWAP by the controller's Lucid fit: `trade_risk_usd` (risk % of drawdown, DLL left x use %, MLL room less kill distance, per-trade cap, day stop, divided by losses/session) then `contracts_for` (stop $ + fee + slippage), capped at max micros; CANDACE then the grade rule (A+ full, B and C halved or less, `grade_contracts`). DLL room for fit strategies is the D18 reading (`dll_remaining`, drop from the day's best P&L); NOISE keeps the session-21 reading.
- **Rolling starts:** a start on every trading day of the window; each run follows the real days from that start to the end of the window (5 years: 2021-10-21..2026-10-30; pick: ..2023-12-31; judge: 2024-01-01..2026-10-30) and ends at pass, stuck/bust, or the window end (= still running). Starts late in a window are censored (more `running`), the same for every test. Pick-window rolling rows use only pick-window days. Days to pass = trading sessions from the start day (no-trade days count).
- **Bootstrap:** the session-21 protocol on the same windows (cross-check; includes `L12` = last 12 months to compare with `eval_odds.yaml`).
- **Static (profit, trades/week, drawdown, skips):** a fresh-account replay with no balance dependence: NOISE at its table size (no brake or shrink), CANDACE/VWAP at the full-room Lucid fit, one position at a time. 1-micro = every signal at 1 micro, one position at a time. `worst DD` = largest peak-to-trough of the cumulative P&L of the merged stream.
- **Stuck rule for mixes:** primary = the baseline definition (account stuck as soon as NOISE cannot be sized). Sensitivity = not stuck while CANDACE/VWAP could still size 1 micro (section 6): it moves accounts from `bust` to `running`, it creates no passes of note.

## 3. Verdict cell by cell (rolling starts, then bootstrap in the same format)

Differences are test minus BASE. Profit = static plan-sized / static 1-micro total over the window.

| test | plan | window | d pass (pts) | d median days | d bust+stuck (pts) | d profit $ (plan / 1-micro) | faster or more pass | bust ok (<= +2) | profit not lower | cell |
|---|---|---|---|---|---|---|---|---|---|---|
| LOCK80 (lock trigger 80 pt) | Pro 25K | JUDGE rolling | +2.0 | +2 | -1.3 | +848 / +848 | yes | yes | yes | **PASS** |
| LOCK80 (lock trigger 80 pt) | Pro 25K | JUDGE bootstrap | +5.7 | +3 | -5.7 | +848 / +848 | yes | yes | yes | **PASS** |
| LOCK80 (lock trigger 80 pt) | Pro 25K | ALL rolling | -4.2 | -7 | +4.6 | +340 / +340 | yes | NO | yes | **FAIL** |
| LOCK80 (lock trigger 80 pt) | Pro 25K | ALL bootstrap | +4.2 | +0 | -4.2 | +340 / +340 | yes | yes | yes | **PASS** |
| LOCK80 (lock trigger 80 pt) | Pro 50K | JUDGE rolling | +6.5 | +4 | -8.5 | +1,696 / +848 | yes | yes | yes | **PASS** |
| LOCK80 (lock trigger 80 pt) | Pro 50K | JUDGE bootstrap | +7.3 | +7 | -7.3 | +1,696 / +848 | yes | yes | yes | **PASS** |
| LOCK80 (lock trigger 80 pt) | Pro 50K | ALL rolling | +2.9 | -2 | -4.0 | +681 / +340 | yes | yes | yes | **PASS** |
| LOCK80 (lock trigger 80 pt) | Pro 50K | ALL bootstrap | +4.8 | +4 | -4.5 | +681 / +340 | yes | yes | yes | **PASS** |
| NOISE + CANDACE | Pro 25K | JUDGE rolling | +0.0 | +2 | +2.0 | -396 / +962 | NO | yes | NO | **FAIL** |
| NOISE + CANDACE | Pro 25K | JUDGE bootstrap | -2.5 | -1 | +2.5 | -396 / +962 | yes | NO | NO | **FAIL** |
| NOISE + CANDACE | Pro 25K | ALL rolling | -8.9 | -15 | +10.1 | +253 / +2,208 | yes | NO | yes | **FAIL** |
| NOISE + CANDACE | Pro 25K | ALL bootstrap | +0.5 | -0 | -0.5 | +253 / +2,208 | yes | yes | yes | **PASS** |
| NOISE + CANDACE | Pro 50K | JUDGE rolling | -12.9 | -16 | +12.9 | +337 / +962 | yes | NO | yes | **FAIL** |
| NOISE + CANDACE | Pro 50K | JUDGE bootstrap | -1.5 | +2 | +1.5 | +337 / +962 | NO | yes | yes | **FAIL** |
| NOISE + CANDACE | Pro 50K | ALL rolling | -5.5 | -14 | +5.5 | +1,844 / +2,208 | yes | NO | yes | **FAIL** |
| NOISE + CANDACE | Pro 50K | ALL bootstrap | +1.2 | -6 | -0.7 | +1,844 / +2,208 | yes | yes | yes | **PASS** |
| NOISE + CONTI VWAP | Pro 25K | JUDGE rolling | -29.5 | -38 | +38.2 | -1,229 / -1,386 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 25K | JUDGE bootstrap | -39.2 | -34 | +39.2 | -1,229 / -1,386 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 25K | ALL rolling | -49.8 | -59 | +54.7 | -6,860 / -4,035 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 25K | ALL bootstrap | -47.2 | -42 | +47.2 | -6,860 / -4,035 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 50K | JUDGE rolling | -45.5 | -70 | +60.6 | -2,458 / -1,386 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 50K | JUDGE bootstrap | -47.0 | -51 | +47.0 | -2,458 / -1,386 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 50K | ALL rolling | -60.2 | -77 | +68.7 | -13,720 / -4,035 | yes | NO | NO | **FAIL** |
| NOISE + CONTI VWAP | Pro 50K | ALL bootstrap | -54.7 | -62 | +55.2 | -13,720 / -4,035 | yes | NO | NO | **FAIL** |

The rolling rows are the verdict rows; the bootstrap rows are a cross-check. Where they disagree (LOCK80 Pro 25K 5 years: rolling bust +4.6, bootstrap bust -4.2) the result is within noise and it shows the LOCK80 25K conclusion is not robust either way.

**Paired by start quarter (5-year rolling, pass % of the test minus BASE, 21 quarters):**

| test | plan | mean diff (pts) | std error | quarters better / worse / equal (+/-0.5) |
|---|---|---|---|---|
| LOCK80 (lock trigger 80 pt) | Pro 25K | -3.8 | 5.0 | 5 / 3 / 13 |
| LOCK80 (lock trigger 80 pt) | Pro 50K | +2.8 | 2.0 | 5 / 2 / 14 |
| NOISE + CANDACE | Pro 25K | -8.6 | 5.5 | 1 / 3 / 17 |
| NOISE + CANDACE | Pro 50K | -5.3 | 7.5 | 4 / 6 / 11 |
| NOISE + CONTI VWAP | Pro 25K | -47.8 | 10.1 | 3 / 15 / 3 |
| NOISE + CONTI VWAP | Pro 50K | -58.7 | 10.0 | 3 / 16 / 2 |

CANDACE on Pro 25K: 114 of the 1,252 starts pass in BASE but are stuck with CANDACE, almost all starting 2023-06..2023-11; they are the long-running accounts (250+ sessions) that sit near the floor, and an ordinary CANDACE/NOISE difference around 2024-01 tips them. One cluster, not 114 independent events.


### 4. Full results, rolling starts (5 years / judge 2024-01..2026-10 / pick 2021-10..2023-12)

| plan | test | ALL: pass / bust / running % | median / 75th pct days | pass within 60 d % | JUDGE: pass / bust / running % | median / 75th pct days | pass within 60 d % | PICK: pass / bust / running % | median / 75th pct days | pass within 60 d % |
|---|---|---|---|---|---|---|---|---|---|---|
| Pro 25K | BASE (NOISE shipped) | 59 / 36 / 6 | 74 / 122 | 23 | 39 / 52 / 10 | 50 / 73 | 24 | 59 / 16 / 26 | 74 / 103 | 22 |
| Pro 25K | LOCK80 (lock trigger 80 pt) | 54 / 40 / 5 | 67 / 109 | 24 | 41 / 50 / 9 | 53 / 72 | 24 | 60 / 13 / 27 | 74 / 103 | 24 |
| Pro 25K | NOISE + CANDACE | 50 / 46 / 4 | 59 / 92 | 25 | 39 / 54 / 8 | 52 / 72 | 23 | 60 / 15 / 25 | 62 / 94 | 29 |
| Pro 25K | NOISE + CONTI VWAP | 9 / 91 / 1 | 15 / 31 | 9 | 9 / 90 / 1 | 13 / 24 | 9 | 8 / 88 / 3 | 27 / 38 | 8 |
| Pro 50K | BASE (NOISE shipped) | 69 / 21 / 10 | 92 / 132 | 20 | 55 / 27 / 17 | 83 / 123 | 19 | 73 / 0 / 27 | 86 / 118 | 21 |
| Pro 50K | LOCK80 (lock trigger 80 pt) | 72 / 17 / 11 | 90 / 132 | 21 | 62 / 19 / 19 | 87 / 120 | 21 | 72 / 0 / 28 | 87 / 119 | 22 |
| Pro 50K | NOISE + CANDACE | 63 / 27 / 10 | 78 / 114 | 25 | 42 / 40 / 17 | 67 / 94 | 20 | 72 / 1 / 27 | 68 / 102 | 33 |
| Pro 50K | NOISE + CONTI VWAP | 9 / 90 / 1 | 15 / 33 | 8 | 10 / 88 / 2 | 13 / 24 | 10 | 7 / 88 / 5 | 32 / 42 | 7 |

Pick-window rolling runs stop at 2023-12-31, so late starts are cut off and `running` is large; compare rows within the column only.


### 4b. Same, session-21 bootstrap protocol (cross-check; L12 = last 12 months, comparable with eval_odds.yaml)

| plan | test | ALL: pass / bust / running % | median / 75th pct days | pass within 60 d % | JUDGE: pass / bust / running % | median / 75th pct days | pass within 60 d % | PICK: pass / bust / running % | median / 75th pct days | pass within 60 d % | L12: pass / bust / running % | median / 75th pct days | pass within 60 d % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pro 25K | BASE (NOISE shipped) | 57 / 43 / 0 | 56 / 82 | 32 | 47 / 53 / 0 | 47 / 70 | 31 | 67 / 33 / 0 | 61 / 83 | 34 | 40 / 60 / 0 | 40 / 56 | 31 |
| Pro 25K | LOCK80 (lock trigger 80 pt) | 62 / 38 / 0 | 57 / 86 | 34 | 53 / 47 / 0 | 50 / 73 | 34 | 66 / 34 / 0 | 61 / 87 | 32 | 47 / 53 / 0 | 47 / 66 | 34 |
| Pro 25K | NOISE + CANDACE | 58 / 42 / 0 | 56 / 79 | 33 | 45 / 55 / 0 | 46 / 67 | 30 | 68 / 32 / 0 | 54 / 75 | 40 | 39 / 61 / 0 | 40 / 56 | 31 |
| Pro 25K | NOISE + CONTI VWAP | 10 / 90 / 0 | 14 / 20 | 10 | 8 / 92 / 0 | 14 / 18 | 8 | 9 / 91 / 0 | 20 / 31 | 9 | 8 / 92 / 0 | 11 / 13 | 8 |
| Pro 50K | BASE (NOISE shipped) | 65 / 34 / 0 | 78 / 109 | 24 | 56 / 44 / 0 | 64 / 102 | 25 | 78 / 22 / 0 | 77 / 123 | 27 | 52 / 48 / 0 | 55 / 86 | 29 |
| Pro 50K | LOCK80 (lock trigger 80 pt) | 70 / 30 / 0 | 81 / 118 | 25 | 63 / 37 / 0 | 71 / 116 | 26 | 76 / 23 / 1 | 82 / 124 | 25 | 65 / 35 / 0 | 66 / 102 | 28 |
| Pro 50K | NOISE + CANDACE | 66 / 34 / 0 | 72 / 108 | 26 | 54 / 46 / 0 | 66 / 96 | 25 | 77 / 23 / 0 | 68 / 112 | 33 | 46 / 54 / 0 | 50 / 80 | 28 |
| Pro 50K | NOISE + CONTI VWAP | 11 / 89 / 0 | 15 / 23 | 10 | 9 / 91 / 0 | 13 / 19 | 9 | 8 / 92 / 0 | 20 / 33 | 7 | 8 / 92 / 0 | 12 / 20 | 8 |

## 5. Profit, trades per week, worst drawdown, skipped signals (static replay)

`1-micro` = all signals at 1 micro; `plan-sized` = NOISE at its table size, CANDACE/VWAP at the Lucid fit. trades/week = trades taken per 5 trading days. Skips = signals not taken because the OTHER strategy held a sized position (CANDACE/VWAP signals that size to 0 contracts block nothing).

| plan | test | window | 1-micro $ | plan-sized $ | trades/week | worst DD 1-micro / plan-sized $ | NOISE taken / signals | other taken / signals | NOISE skipped (other open) | other skipped (NOISE open) | other skipped (own previous trade, VWAP same-bar rule) | other sized to 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pro 25K | BASE (NOISE shipped) | ALL | 19,293 | 19,293 | 2.6 | 2,096 / 2,096 | 654 / 654 | - | 0 | - | - | - |
| Pro 25K | LOCK80 (lock trigger 80 pt) | ALL | 19,634 | 19,634 | 2.6 | 1,896 / 1,896 | 647 / 647 | - | 0 | - | - | - |
| Pro 25K | NOISE + CANDACE | ALL | 21,501 | 19,546 | 3.0 | 1,967 / 2,174 | 649 / 654 | 94 / 304 | 5 | 1 | 0 | 209 |
| Pro 25K | NOISE + CONTI VWAP | ALL | 15,258 | 12,433 | 13.2 | 2,801 / 9,353 | 570 / 654 | 2738 / 4694 | 84 | 81 | 1875 | 0 |
| Pro 25K | BASE (NOISE shipped) | JUDGE | 10,826 | 10,826 | 2.5 | 2,096 / 2,096 | 356 / 356 | - | 0 | - | - | - |
| Pro 25K | LOCK80 (lock trigger 80 pt) | JUDGE | 11,674 | 11,674 | 2.5 | 1,896 / 1,896 | 350 / 350 | - | 0 | - | - | - |
| Pro 25K | NOISE + CANDACE | JUDGE | 11,788 | 10,429 | 2.8 | 1,967 / 2,174 | 356 / 356 | 34 / 150 | 0 | 0 | 0 | 116 |
| Pro 25K | NOISE + CONTI VWAP | JUDGE | 9,440 | 9,596 | 13.3 | 2,311 / 8,107 | 312 / 356 | 1562 / 2648 | 44 | 46 | 1040 | 0 |
| Pro 25K | BASE (NOISE shipped) | PICK | 8,468 | 8,468 | 2.7 | 944 / 944 | 298 / 298 | - | 0 | - | - | - |
| Pro 25K | LOCK80 (lock trigger 80 pt) | PICK | 7,960 | 7,960 | 2.7 | 1,100 / 1,100 | 297 / 297 | - | 0 | - | - | - |
| Pro 25K | NOISE + CANDACE | PICK | 9,714 | 9,117 | 3.2 | 980 / 917 | 293 / 298 | 60 / 154 | 5 | 1 | 0 | 93 |
| Pro 25K | NOISE + CONTI VWAP | PICK | 5,818 | 2,836 | 13.1 | 1,778 / 4,390 | 258 / 298 | 1176 / 2046 | 40 | 35 | 835 | 0 |
| Pro 50K | BASE (NOISE shipped) | ALL | 19,293 | 38,586 | 2.6 | 2,096 / 4,193 | 654 / 654 | - | 0 | - | - | - |
| Pro 50K | LOCK80 (lock trigger 80 pt) | ALL | 19,634 | 39,267 | 2.6 | 1,896 / 3,791 | 647 / 647 | - | 0 | - | - | - |
| Pro 50K | NOISE + CANDACE | ALL | 21,501 | 40,430 | 3.8 | 1,967 / 3,932 | 638 / 654 | 303 / 304 | 16 | 1 | 0 | 0 |
| Pro 50K | NOISE + CONTI VWAP | ALL | 15,258 | 24,866 | 13.2 | 2,801 / 18,706 | 570 / 654 | 2738 / 4694 | 84 | 81 | 1875 | 0 |
| Pro 50K | BASE (NOISE shipped) | JUDGE | 10,826 | 21,651 | 2.5 | 2,096 / 4,193 | 356 / 356 | - | 0 | - | - | - |
| Pro 50K | LOCK80 (lock trigger 80 pt) | JUDGE | 11,674 | 23,347 | 2.5 | 1,896 / 3,791 | 350 / 350 | - | 0 | - | - | - |
| Pro 50K | NOISE + CANDACE | JUDGE | 11,788 | 21,988 | 3.5 | 1,967 / 3,932 | 349 / 356 | 150 / 150 | 7 | 0 | 0 | 0 |
| Pro 50K | NOISE + CONTI VWAP | JUDGE | 9,440 | 19,193 | 13.3 | 2,311 / 16,214 | 312 / 356 | 1562 / 2648 | 44 | 46 | 1040 | 0 |
| Pro 50K | BASE (NOISE shipped) | PICK | 8,468 | 16,935 | 2.7 | 944 / 1,888 | 298 / 298 | - | 0 | - | - | - |
| Pro 50K | LOCK80 (lock trigger 80 pt) | PICK | 7,960 | 15,920 | 2.7 | 1,100 / 2,201 | 297 / 297 | - | 0 | - | - | - |
| Pro 50K | NOISE + CANDACE | PICK | 9,714 | 18,442 | 4.0 | 980 / 2,092 | 289 / 298 | 153 / 154 | 9 | 1 | 0 | 0 |
| Pro 50K | NOISE + CONTI VWAP | PICK | 5,818 | 5,673 | 13.1 | 1,778 / 8,779 | 258 / 298 | 1176 / 2046 | 40 | 35 | 835 | 0 |

Reading the skips: NOISE loses 5-16 of 654 signals to CANDACE over 5 years (<= 2.5%) and CANDACE loses 1; against CONTI VWAP NOISE loses 84 of 654 (13%) because VWAP is in a position almost all the time (VWAP: 2,738 trades taken on 25K; 1,956 of its 4,694 signals skipped, 1,875 of them its own same-bar reversals under the D139 rule and 81 because NOISE was open).

## 6. Sensitivity: STUCK rule that lets CANDACE / VWAP keep an account alive (rolling, pass / bust+stuck / running %, median days)

| plan | test | window | primary rule | sensitivity rule |
|---|---|---|---|---|
| Pro 25K | NOISE + CANDACE | ALL | 50 / 46 / 4, 59d | 50 / 30 / 20, 59d |
| Pro 25K | NOISE + CANDACE | JUDGE | 39 / 54 / 8, 52d | 39 / 26 / 35, 52d |
| Pro 25K | NOISE + CONTI VWAP | ALL | 9 / 91 / 1, 15d | 9 / 91 / 1, 15d |
| Pro 25K | NOISE + CONTI VWAP | JUDGE | 9 / 90 / 1, 13d | 9 / 90 / 1, 13d |
| Pro 50K | NOISE + CANDACE | ALL | 63 / 27 / 10, 78d | 63 / 19 / 17, 78d |
| Pro 50K | NOISE + CANDACE | JUDGE | 42 / 40 / 17, 67d | 42 / 27 / 31, 67d |
| Pro 50K | NOISE + CONTI VWAP | ALL | 9 / 90 / 1, 15d | 9 / 90 / 1, 15d |
| Pro 50K | NOISE + CONTI VWAP | JUDGE | 10 / 88 / 2, 13d | 10 / 88 / 2, 13d |

The sensitivity rule turns stuck accounts into zombie 'running' accounts that cannot realistically finish; pass % barely moves, so the verdict does not depend on it.

## 7. Caveats

- **Streams are independent runs of each engine, merged afterwards.** When a signal is skipped because the other strategy is in a position, the skipped strategy's own state machine (NOISE signal counter of 3 per day, CANDACE one-trade-per-setup, VWAP position flip) is not re-run. A faithful rerun would let NOISE re-enter at its next hourly check and CANDACE re-arm its setup; the effect is small (5-16 NOISE signals and 1 CANDACE signal over 5 years) but not zero. For VWAP it is large, but VWAP loses by a wide margin anyway.
- **Strategy-internal day limits** (CANDACE max losses per day, VWAP losses per day) count only that strategy's own trades.
- **Shared-day limits** (DLL, 38% consistency day stop, MLL room) are shared and are applied to every trade; a trade is capped at the day stop (flatten) as in session 21.
- **Pro 25K sizing makes CANDACE almost inert** (only 94 of 304 signals get >= 1 micro after the grade rule; static plan-sized +$253 over 5 years).
- **Median days to pass is conditional on passing** and differs by protocol (rolling real days vs 10-day-block bootstrap; rolling 5-year medians are longer than the bootstrap ones). Compare within a protocol.
- **No outright busts occur in any run**: every non-pass is STUCK (room too small to size NOISE) or still running, exactly as in `eval_odds.yaml`. The 2-pt bust rule therefore applies to stuck + bust.
- Rolling starts are overlapping and heavily clustered; no confidence interval beyond the by-quarter pairing in section 3 is given.

## 8. Files

- `repro_baseline.py` / `repro_baseline.json`: step 0 (session-21 sim2, unchanged, exact reproduction).
- `gen_streams.py`: builds `streams_noise_base.csv`, `streams_noise_lock80.csv`, `streams_candace.csv`, `streams_vwap.csv` (run from `backend/` with `PYTHONPATH=.`).
- `pf_sim.py`: account simulator for NOISE + CANDACE / VWAP; `validate.py`: sim2 equality + fit-sizing equality; `run_all.py`: runs everything -> `results.json`; `analyze.py` + `report.py`: verdict checks and this file; `show.py`: quick print.

