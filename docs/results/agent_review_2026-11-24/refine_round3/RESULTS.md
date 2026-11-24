# Refine round 3: real fast-pass config (2026-11-24, research only; no app code changed, nothing pushed)
Sim: pass_fastest/sim150.py + brake150/final_search patches, loaded in memory on /home/user/days.pkl (`harness.py`; repo files untouched). Rules as built: C40 + 38 % day stop ($3,420), DLL on, EOD MLL, 1 position, +$2 RT/micro costs in base. Pick = starts/accounts 2021-10..2023-12, judge = starts 2024-01..2026-10 (the sim's PICK/JUDGE windows). Scripts: harness.py, repro.py, run_r3.py, extra_dl.py, report_r3.py; data results_r3.json, table.md.

## 1. Reproduction (exact)
| row | pass % | median d | judge / pick pass | stuck+bust | 5-yr profit (static) |
|---|---|---|---|---|---|
| 150K built: N5@$100 [2250>2,1500>1] grow500 max6, C5 [2700>4,1500>1] grow1500 max6, dl0.7, lock100/10 | 74.4 | 80 | 57.3 / 72.8 | 4.4 % | $100,575 (max closed-trade DD $8,192) |
| 50K built: N2@$75 [667>1], C4 [1000>3], dl0.4, NOISE lock 80 | 66.3 | 61 | 56.5 / 68.2 | 26.2 % | $39,080 (DD $3,703) |
Both match final_search/RESULTS.md (74.4/80 and 66.3/61). Late-day leg (optional, unverified) not modelled, as in those studies. Static profit does not model grow or day lock.
Sensitivity of the built 150K row: +$2/micro RT on NOISE and CANDACE: pass 63.7 %, judge 40.1 %, median 80 (-11 and -17 pts). Pass by start half-year (2021H2-2026H1, 2026H2 excluded: under 30 sessions): min 38 % (2025H2), median 100 %, max 100 %. 50K: 5 % (2025H2) / 91.9 % / 100 %. It is a regime on/off pattern, as model_qa finding 1 said.

## 2. Pre-registered re-test at the $100-stop 150K config (one change at a time off the built row)
Candidate rule (set before running): beats built on BOTH pick and judge for pass % AND median days (strictly), static profit not lower, 5-yr pass >= 70 %, stuck+bust not worse by > 2 pts. Variants tried: **23** (a) 11 lock trigger {80,100,120} x offset {0,10,20,30} minus shipped, (b) 3 stops $75/125/150, (c) 3 day locks 0.5/0.6/0.8, (d) 6 size balances (N,C) = 5/3, 5/4, 4/5, 4/4, 6/5, 5/6. Plus 5 diagnostic day-lock values (0.1-0.4, none; not counted as picks). At 23 tries about 2 false wins at 10 % are expected; **0 candidates, so no multiplicity problem arises**.
| variant | pick pass/med | judge pass/med | all pass/med | stuck+bust % | profit | maxDD | +$2 all pass/judge/med | HY min/med/max | candidate |
|---|---|---|---|---|---|---|---|---|---|
| BUILT | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 8192 | 63.7/40.1/80 | 38/100/100 | - |
| a_lock80/0 | 72.0/65 | 51.2/65 | 72.5/78 | 4.4 | 99308 | 7620 | 67.9/46.2/86 | 21/100/100 | no |
| a_lock80/10 | 72.0/67 | 61.1/71 | 78.1/88 | 4.2 | 100392 | 7855 | 70.1/47.0/88 | 30/100/100 | no |
| a_lock80/20 | 72.2/68 | 48.8/65 | 71.2/79 | 4.2 | 95225 | 7812 | 67.3/42.0/82 | 11/100/100 | no |
| a_lock80/30 | 72.8/82 | 42.3/69 | 67.5/94 | 0.3 | 85480 | 7212 | 65.3/38.3/104 | 0/100/100 | no |
| a_lock100/0 | 72.8/64 | 49.2/67 | 71.4/78 | 5.0 | 100982 | 8258 | 65.3/41.3/82 | 21/100/100 | no |
| a_lock100/20 | 72.9/67 | 67.9/93 | 81.9/94 | 0.3 | 96605 | 8192 | 60.9/44.0/76 | 57/100/100 | no |
| a_lock100/30 | 73.1/77 | 43.7/69 | 68.3/83 | 0.4 | 92270 | 8192 | 60.9/40.1/82 | 0/100/100 | no |
| a_lock120/0 | 73.1/64 | 47.8/66 | 70.6/74 | 11.6 | 98492 | 8258 | 62.6/41.1/78 | 9/100/100 | no |
| a_lock120/10 | 73.1/64 | 45.4/62 | 67.8/71 | 6.8 | 98540 | 8192 | 63.3/44.0/79 | 15/100/100 | no |
| a_lock120/20 | 73.1/65 | 50.1/64 | 71.9/73 | 4.2 | 99080 | 8192 | 69.6/48.5/78 | 22/100/100 | no |
| a_lock120/30 | 73.1/65 | 51.3/61 | 72.6/73 | 3.3 | 99938 | 8192 | 68.7/44.4/71 | 25/100/100 | no |
| b_stop75 | 72.8/70 | 39.7/87 | 59.7/83 | 21.2 | 87400 | 10038 | 53.1/36.3/84 | 0/93/100 | no |
| b_stop125 | 73.1/74 | 38.9/57 | 65.6/78 | 17.9 | 93480 | 9578 | 63.5/37.4/79 | 0/100/100 | no |
| b_stop150 | 72.8/68 | 42.8/62 | 67.8/74 | 18.5 | 99088 | 10258 | 65.7/40.9/80 | 0/100/100 | no |
| c_dl0.5 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 8192 | 63.7/40.1/80 | 38/100/100 | no |
| c_dl0.6 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 8192 | 63.7/40.1/80 | 38/100/100 | no |
| c_dl0.8 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 8192 | 63.7/40.1/80 | 38/100/100 | no |
| d_N5C3 | 72.9/67 | 51.9/68 | 72.8/79 | 6.2 | 96880 | 7952 | 66.1/40.0/78 | 25/100/100 | no |
| d_N5C4 | 72.8/67 | 48.9/65 | 71.2/76 | 9.1 | 98728 | 8072 | 64.7/39.4/82 | 9/100/100 | no |
| d_N4C5 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 82308 | 6674 | 63.7/40.1/80 | 38/100/100 | no |
| d_N4C4 | 72.8/67 | 48.9/65 | 71.2/76 | 9.1 | 80460 | 6554 | 64.7/39.4/82 | 9/100/100 | no |
| d_N6C5 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 118842 | 9711 | 63.7/40.1/80 | 38/100/100 | no |
| d_N5C6 | 72.8/66 | 58.0/71 | 75.6/82 | 3.4 | 102422 | 8312 | 63.6/40.1/80 | 38/100/100 | no |

(HY = pass % by start half-year, min/median/max. +$2 column = all-window pass / judge pass / median with +$2 RT per micro on both strategies. Medians are among passers; the pick median is cut at the window end, so compare it only with the built row's 66.)

## 3. Findings
- (a) Lock: no variant beats built on both windows. Pick is flat (72.0-73.1 %, differences of 0-2 starts), judge swings both ways non-monotonically (42-68 %): 100/20 shows judge 67.9 % and all 81.9 % but median 93 d (slower than 80) and profit -$4K; 80/10 shows judge 61.1 % / all 78.1 % but pick 72.0 % and median 88 d. Neighbours of each (100/30, 80/20, 80/0) are 10-25 pts worse: a noisy ridge, not a plateau. Keep 100/10. (lock 100/20 does win +$2 sensitivity? No: 60.9 vs built 63.7.)
- (b) Stop: $100 is clearly the best; $75/$125/$150 cut all-window pass to 59.7/65.6/67.8 % with stuck+bust rising to 18-21 %. Rejection holds, more strongly than round 2.
- (c) Day lock: INERT at 0.5-0.8 (results identical to 0.7 to the last digit). A day cannot reach 50 % of the $9,000 target ($4,500) because the 38 % day stop ($3,420) ends it first, so the lock only bites late when the remaining target is small. Values 0.2-0.4 move pass by under 0.5 pt (noise). Nothing to adopt; the setting is cosmetic on 150K.
- (d) Balance: NOISE start size is also inert for pass % (4, 5 or 6 give identical pass/median because grow lifts to the cap of 6 on a fresh $4,500 cushion; they differ only in static profit, which ignores grow, so ignore the profit column there). Smaller CANDACE (3, 4) is worse (judge 49-52 %, stuck 6-9 %). CANDACE 6: all 75.6 % / 82 d, judge 58.0 / 71 d, pick unchanged 72.8 / 66: not strictly better (median slower, pick tied) and rests on the weakest-evidenced leg (CANDACE PF 1.22, CI 0.92-1.59).
- Cost: every row falls 5-15 pts on the all-window and 10-20 on judge with +$2/micro. Built 74.4 to 63.7. No variant is robust to this; lock 80/10 at +$2 looks better (70.1) but it is worse at base cost on pick, and picking by a perturbed scenario is another fork.
- Overall pick-window pass is 72.0-73.1 % for all 24 rows: the pick period (2021-23) is insensitive to every knob; only the judge window (about 11 regimes of data in 5 years) moves, which makes any "win" a judge-window coin flip.

## 4. Round-2 rejections at the real fast-pass config
- Lock trigger/offset: HOLDS (REJECT). No ADOPT CANDIDATE among 11.
- Stop distance: HOLDS (REJECT). The built $100 beats $75/125/150 on every metric.
- Extra: day lock and NOISE size are no-ops here; CANDACE size is the only live lever and 6 is a tie-ish, not a candidate.
Nothing is adopted. Keep shipped settings. 50K was reproduced only (re-test was scoped to 150K).
