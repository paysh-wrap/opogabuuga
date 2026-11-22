# Pass-rate floor study: fastest setups that keep the new-best pass rate (25K / 100K / 150K), 2026-11-22

## In plain words
- The BUILT setups reproduce their reported numbers exactly (25K 61.8 / 33.7 within 60 d / median 56; 100K 78.0 / 5.2 / 127; 150K 74.3 / 20.4 / 86; BASE rows too). No mismatch.
- **None of the three BUILT yaml setups meets the pass floor.** 25K misses by 0.4 pt (61.8 vs 62.2), 100K by 1.9 pt (78.0 vs 79.9), 150K by 4.8 pt (74.3 vs 79.1) and its stuck % is 17.0 vs 9.8.
- Floors are reachable on all three plans with equal or faster median days (except 150K, see below). Replacements are below.
- **150K:** floor 79.1 % is met at median 93 days (BUILT: 86, REF: 111), 26 % within 60 days (REF 9.3 %), stuck 4.2 %, profit $100K. You give up 7 median days vs BUILT to gain +6 pt pass and 13 pts less stuck. Faster than 92 days at pass >= 79.1 was not found.
- **100K:** better than REF on every speed measure and on pass: pass 80.4, median 121 (REF 130, BUILT 127), profit $46,697.
- **25K:** only the REF setup qualifies (62.2, median 56). It is essentially BUILT with the CANDACE brake at $500 and NOISE lock 80.
- Rules in all runs: C40 (day stop 38 %), DLL ON, EOD MLL + lock, LucidScale, kill distance + room check, D57 shrink, plan trade cap, one position, flat by close. Same streams and simulator as brake150 / within60 (reuse of `../within60/lib.py`).
- Constraints applied to every candidate: 5-yr pass >= floor; stuck <= the floor setup's stuck; profit >= BASE; judge >= BASE judge - 3; pick >= BASE pick - 5.
  Floors/refs: 25K 62.2 (stuck 29.4), 100K 79.9 (9.3), 150K 79.1 (9.8). 20K+ runs (stage 1 grid 18.8K, band moves 1.9K, extras cross 7.7K).
- Search space: stop {50..250}, NOISE micros, CANDACE micros (0-5), one- and two-step brakes for NOISE and CANDACE separately (cushion steps $/MLL 0.15 to 0.6), lock 80/100/120, day lock 50/70 %, taper, grow, CANDACE window 10:30.
  Limits: 25K grid had NOISE 1-2 and CANDACE 0-3 only; 150K NOISE 2-5; 100K NOISE 1-3. Extras were crossed on the best ~25-40 seeds per plan, not on the full grid.

## Verdict and exact numbers
Brake bands are `cushion (equity incl. open P&L minus current MLL) < $X`, strict. Tags: code = needs app code (CANDACE fixed micros and CANDACE brake bands, a second brake step), config = existing plan-file fields (NOISE lock, EVAL_DAY_LOCK, grow, stop, micros).

| plan | BUILT meets floor? | replacement (fastest feasible) | pass | stuck | <=60d | median d | days w/ resets | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|---|---|---|
| 25K | no (61.8 vs 62.2) | N1@75 + C2; NOISE no brake; CANDACE 1 micro below $500 (was $333); NOISE lock 80 pt | 62.2 | 29.4 | 35.2 | 56 | 100 | 55.7 | 61.4 | 19,540 |
| 100K | no (78.0 vs 79.9) | N2@250 + C4; NOISE 1 below $750; CANDACE 1 below $1,500 | 80.4 | 9.1 | 6.0 | 121 | 159 | 65.7 | 64.0 | 46,697 |
| 150K | no (74.3 vs 79.1) | N5@100 + C5; NOISE 3 below $2,250 then 1 below $1,800; CANDACE 2 below $1,500 then 1 below $900; NOISE lock 80; day lock 70 %; grow 500/6 | 80.4 | 4.2 | 26.1 | 93 | 144 | 65.2 | 72.0 | 100,392 |

Reference rows: 25K BUILT 61.8 / 29.6 / 33.7 / 56 / 95; 100K BUILT 78.0 / 11.3 / 5.2 / 127 / 166 (REF N2+C3 brake 1/1: 79.9 / 9.3 / 5.2 / 130 / 169); 150K BUILT 74.3 / 17.0 / 20.4 / 86 / 130 (REF N4@100+C3: 79.1 / 9.8 / 9.3 / 111 / 155).

Tags:
- **25K**: CANDACE brake at $500 instead of $333 = config of the CANDACE brake (code needed anyway, as BUILT already assumes). NOISE lock 80 = config if it is a plan-file value (else code). Median 56 is the same as BUILT; the gain is +0.4 pt pass, +1.5 pt within 60 d, +$212.
- **100K**: CANDACE 4 micros + CANDACE brake 1 below $1,500 and NOISE brake 1 below $750 = same code as BUILT (fixed micros + brake band), only different numbers. Config-only on top of the built code.
- **150K**: two-step brakes for NOISE and CANDACE need code (BUILT has one step). Lock 80, day lock and grow are config. N5 stays above the D133 cap of 3 = D159 lift for fast-pass only; C5 is one more fixed micro than built.
- Simpler 150K alternative with no grow or lock change (needs the two-step brake only): N5@100+C4; NOISE 2 below $2,250 then 1 below $1,500; CANDACE 2 below $2,250 then 1 below $900; day lock 50 %: pass 79.3, stuck 0.4, within 60 d 20.0, median 95, days w/ resets 134, judge 63.3, pick 72.0, profit $98,728.
- Fastest median at the floor (150K): N5@100+C5 with NOISE 2 below $2,250 / 1 below $1,500, CANDACE 3 below $1,800 / 1 below $1,500, lock 120, day lock 50 %, CANDACE window 10:30: median 92, pass 79.3, stuck 5.8, within 60 d 21.2. One day faster, not worth the complexity.

## Pareto, pass % vs median days (all constraints except the pass floor; "floor met" marks pass >= floor)
Full tables with top lists by median, by within-60 and by expected days with resets: `tables.md`. Compact view:

25K (only 3 points; floor 62.2): 61.7 @ 53 d | 61.9 @ 54 | **62.2 @ 56** (floor met). 53-54 d versions use day lock 50 % but miss the floor by 0.3-0.5 pt.

100K (floor 79.9): **80.4 @ 121 d** | 81.0 @ 122 | 81.6 @ 123 (within 60 d 7.9 %, lock 80) | 85.2 @ 130 | 86.2 @ 137 | 88.5 @ 141 (stuck 0 %, profit $42K) | 89.9 @ 145.
150K (floor 79.1): 76.4 @ 82 | 78.0 @ 87 | 79.1 @ 90 (just on the floor) | 79.3 @ 92 | **80.4 @ 93** | 81.2 @ 95 | 83.3 @ 98 | 86.8 @ 101 (profit $97K) | 88.4 @ 119 | 89.9 @ 142 (stuck 0 %, within 60 d 3 %).
Trade-off: each +1 pt pass costs roughly 1-3 median days in the 80-88 % range on 150K, and about 1-5 on 100K; below 79 % the 150K median improves to 82-87 days.
Note the 150K BUILT point (86 d, 74.3 %) sits on this curve: it is speed-first, below the floor.

## Files
`repro.py` (+ `repro.json`, `repro.log`): BUILT / REF / BASE reproduction. `search.py` (stage1 / stage2 / stage3, resumes `results.json`, ~21K runs, ~17 min on 4 cores). `report.py` -> `tables.md`.
Nothing in backend/app, config/ or frontend/ was touched. No commit.
