# Pass fastest: Pro 50K and Pro 150K EVALUATION (research only, 2026-11-22)

## Plain answer

Goal: more evaluations passed within 60 trading days ("<=60d", as a share of all starts), while keeping the 5-year pass rate >= 59 % (50K) and >= 70 % (150K).
Every run has all Lucid rules on: EOD trailing MLL + lock, DLL incl. LucidScale, consistency at pass + day stop, kill distance + room check, D57 shrink,
one position at a time, no hedge, flat by close. C40 = the shipped 40 % (day stop 38 %). C50 = the 50 % option you can buy (D155, day stop 48 %).
ROBUST = meets the floor over 5 years AND judge pass >= BASE judge − 3 pts AND pick pass >= BASE pick − 5 pts (BASE under the same consistency).

**Pro 50K: keep the shipped setting.** No config in the grid is both faster than BASE and ROBUST. Faster configs do exist (CANDACE 2 micros:
<=60d up to 27.6 % C40 / 31.2 % C50), but every one of them loses 7–11 pts of judge-window pass rate (2024–2026), so I do not recommend them.
- C40: BASE = NOISE 2 micros @ $250 stop, brake to 1 micro below 50 % cushion: pass 68.8 %, <=60d 19.7 %, median 92 d, profit $38,586.
- C50: the same BASE: pass 70.0 %, <=60d 20.8 %, median 88 d. Buying the 50 % option on its own adds +1.2 pts pass and +1.1 pts <=60d.
- Optional, config-only: add a taper (1 micro once < 25 % of the target remains). Pass goes up +1.6 pts (C40 70.4 %) and judge +2.9 pts,
  but <=60d drops 0.9 pts (18.8 %). It makes passing **slower**, not faster. Profit is unchanged.

**Pro 150K: NOISE 4 micros @ $100 stop + CANDACE 3 micros + brake (2 micros below 50 % cushion).** It is the same config under C40 and C50:
- C40: pass 79.1 % (BASE 77.1), <=60d 9.3 % (BASE 5.8), median 111 d (159), expected days to the first pass with resets 155 (187),
  judge 63.7 (59.3), plan-sized profit $78,612 (BASE $57,879).
- C50: pass 79.9 % (77.3), <=60d 9.7 % (5.8), median 110 d (158), with resets 153 d (186), judge 65.1 (59.7).
- Strictly, the fastest ROBUST config under C40 is NOISE 4 @ $250 + CANDACE 3 + brake: <=60d 9.4 %, which is 0.1 pt better (about 1 start).
  Its pass rate is only 71.7 % and stuck is 18.8 %, so it is not worth taking. Under C50 the recommended config ranks #1 outright.
- Config-only alternative (no code needed): NOISE 4 @ $250 + brake, which is today's size_table_eval row with the D133 cap lifted.
  Pass 77.6 %, <=60d 8.1 %, median 132 d, profit $77,172. The figures are about the same under C40 and C50.
- None of the recommended changes cuts measured profit. 150K gains +$20.7K plan-sized over 5 years; 50K is unchanged.
- Caveat: even the best 150K config passes within 60 days in only about 1 start in 10. The $9,000 target is far for this strategy set.

Tags
- NOISE stop $100 (150K): **config-only:** `size_table_eval` 150K row `stop_usd: 100` (EVAL only).
- NOISE 4 micros on 150K: **config-only, but a D133 rule change:** `eval_size_caps` 150K `max_contracts: 4` (or `eval_size_s19: false`).
  The row already says `contracts: 4, brake_below: 0.5, brake_contracts: 2`.
- CANDACE 3 fixed micros per trade ($125 per-micro cap, D154): **needs code**. Today CANDACE is sized by its Lucid fit.
- Taper (50K option): **config-only:** `size_table_eval` 50K row `taper_below_remaining: 0.25, taper_contracts: 1`.
- C50: **config-only, after buying the option:** eval consistency 50 % in the plan yaml (the day stop then becomes 48 %). VERIFY with Lucid.

## Top-5 ROBUST per plan × consistency (5-year rolling starts, 1,252 per config)
"chain days" = expected trading days to the FIRST pass when every stuck or bust account is reset the next day (cens = share of chains cut off by the end of the data).
profit = plan-sized static replay over 5 years. pick = 2021-10..2023-12, judge = 2024-01..2026-10.

**Pro 50K · C40** (ROBUST: 5y pass >= 59 %, judge >= 52.3, pick >= 68.1; 2 robust configs out of 108)

| config | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ |
|---|---|---|---|---|---|---|---|---|---|
| BASE: NOISE 2@$250 +brake | 68.8 | 21.4 | **19.7** | 92 | 133 (13 %) | 73.1 | 55.3 | 19.0 | 38,586 |
| row A: NOISE 2@$100 + CAND 1 | 59.1 | 30.6 | **25.5** | 67 | 118 (10 %) | 62.3 | 48.9 | 22.4 | 38,382 |
| #1 NOISE 2@$250 +brake (=BASE) | 68.8 | 21.4 | **19.7** | 92 | 133 (13 %) | 73.1 | 55.3 | 19.0 | 38,586 |
| #2 NOISE 2@$250 +brake +taper | 70.4 | 20.9 | **18.8** | 92 | 132 (11 %) | 73.9 | 58.2 | 20.1 | 38,586 |

**Pro 50K · C50** (ROBUST: 5y pass >= 59 %, judge >= 54.4, pick >= 68.1; 2 robust configs)

| config | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ |
|---|---|---|---|---|---|---|---|---|---|
| BASE: NOISE 2@$250 +brake | 70.0 | 20.5 | **20.8** | 88 | 127 (12 %) | 73.1 | 57.4 | 20.4 | 38,586 |
| row A: NOISE 2@$100 + CAND 1 | 62.9 | 30.2 | **26.3** | 67 | 116 (7 %) | 62.3 | 55.7 | 23.8 | 38,382 |
| #1 NOISE 2@$250 +brake (=BASE) | 70.0 | 20.5 | **20.8** | 88 | 127 (12 %) | 73.1 | 57.4 | 20.4 | 38,586 |
| #2 NOISE 2@$250 +brake +taper | 71.5 | 20.3 | **20.1** | 89 | 126 (11 %) | 73.9 | 60.0 | 21.8 | 38,586 |

**Pro 150K · C40** (ROBUST: 5y pass >= 70 %, judge >= 56.3, pick >= 60.1; 38 robust configs out of 137)

| config | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ |
|---|---|---|---|---|---|---|---|---|---|
| BASE: NOISE 3@$250 +brake | 77.1 | 10.5 | **5.8** | 159 | 187 (12 %) | 65.1 | 59.3 | 3.8 | 57,879 |
| row A: NOISE 4@$100 + CAND 2 | 73.9 | 16.0 | **8.9** | 105 | 168 (10 %) | 69.5 | 64.3 | 6.7 | 76,765 |
| #1 NOISE 4@$250 + CAND 3 +brake | 71.7 | 18.8 | **9.4** | 108 | 149 (12 %) | 68.4 | 61.1 | 8.2 | 84,156 |
| #2 NOISE 4@$100 + CAND 3 +brake (recommended) | 79.1 | 9.8 | **9.3** | 111 | 155 (11 %) | 68.7 | 63.7 | 7.5 | 78,612 |
| #3 NOISE 4@$100 + CAND 3 | 74.2 | 16.9 | **9.3** | 103 | 144 (9 %) | 69.5 | 66.4 | 7.5 | 78,612 |
| #4 NOISE 4@$100 + CAND 2 +brake | 79.8 | 9.3 | **8.9** | 113 | 160 (11 %) | 69.8 | 64.1 | 6.7 | 76,765 |
| #5 NOISE 4@$100 + CAND 2 | 73.9 | 16.0 | **8.9** | 105 | 168 (10 %) | 69.5 | 64.3 | 6.7 | 76,765 |
| config-only: NOISE 4@$250 +brake | 77.6 | 1.8 | **8.1** | 132 | 145 (21 %) | 70.2 | 60.3 | 7.2 | 77,172 |

**Pro 150K · C50** (ROBUST: 5y pass >= 70 %, judge >= 56.7, pick >= 60.1; 38 robust configs)

| config | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ |
|---|---|---|---|---|---|---|---|---|---|
| BASE: NOISE 3@$250 +brake | 77.3 | 10.5 | **5.8** | 158 | 186 (12 %) | 65.1 | 59.7 | 3.8 | 57,879 |
| row A: NOISE 4@$100 + CAND 2 | 75.9 | 16.0 | **9.3** | 104 | 160 (8 %) | 69.5 | 67.8 | 7.4 | 76,765 |
| #1 NOISE 4@$100 + CAND 3 +brake (recommended) | 79.9 | 9.8 | **9.7** | 110 | 153 (10 %) | 68.7 | 65.1 | 8.1 | 78,612 |
| #2 NOISE 4@$100 + CAND 3 | 75.0 | 16.9 | **9.7** | 102 | 142 (8 %) | 69.5 | 67.8 | 8.1 | 78,612 |
| #3 NOISE 4@$250 + CAND 3 +brake | 71.7 | 18.8 | **9.7** | 108 | 148 (12 %) | 68.4 | 61.1 | 8.7 | 84,156 |
| #4 NOISE 4@$100 + CAND 2 +brake | 80.8 | 9.3 | **9.3** | 113 | 156 (10 %) | 69.8 | 65.8 | 7.4 | 76,765 |
| #5 NOISE 4@$100 + CAND 2 | 75.9 | 16.0 | **9.3** | 104 | 160 (8 %) | 69.5 | 67.8 | 7.4 | 76,765 |
| config-only: NOISE 4@$250 +brake | 77.6 | 1.8 | **8.1** | 129 | 145 (21 %) | 70.2 | 60.3 | 7.2 | 77,172 |

## Fastest configs that meet only the 5-year floor (NOT robust, for reference)
| plan · cons | config | pass 5y | <=60d | pick | judge | why not |
|---|---|---|---|---|---|---|
| 50K C40 | NOISE 2@$100 + CAND 2 +brake | 62.9 | 27.6 | 69.1 | 46.4 | judge −8.9 vs BASE |
| 50K C50 | NOISE 2@$200 + CAND 2 +brake | 60.1 | 31.2 | 62.3 | 47.9 | judge −9.5, pick −10.8 |
| 150K C50 | NOISE 5@$100 + CAND 1 +brake | 70.7 | 17.9 | 70.4 | 54.6 | judge −5.1; pass at the floor |

## Method
- Reproduction first, matching to the last digit: pass_faster_100/results.json gives 50K BASE 68.85 / 19.73, row A 59.11 / 25.48; 150K BASE 77.08 / 5.75, row A 73.88 / 8.87.
  repro50.log adds per-start equality with pf_sim/run_fixed, and the sizing equals the app's `auto_contracts` on 187k grid points.
  validate150.log adds the bootstrap, which equals eval_odds.yaml 78/14/7/170.
- Simulators reused unchanged from the stopped search (pass_fastest_wip): lib50.py (50K), sim150.py + gen_lib.py (150K). The consistency scenario is injected per run
  (50K: plan dict `cons`/`day_stop`; 150K: module `CONS`/`DSTOP`). NOISE streams come from the shared scratch cache (same session-20 generator, Mondays off, lock 100→+10, max 3).
- Grid: stop {100,150,200,250} × NOISE micros (50K 1–3, 150K 3–6) × CANDACE (50K 0–2, 150K 0–3) × brake {none, half below 50 % cushion} × taper {none, half below 25 % remaining}.
  50K: the full grid (108 distinct configs; one-factor slices around BASE and row A in slices.txt). 150K: stage 1 one-factor around BASE and row A,
  stage 2 factorial stop × micros × CANDACE × brake, stage 3 taper on the 8 fastest robust configs per consistency (137 configs). Every config was run under C40 and C50.
- One-factor findings (slices.txt):
  - 50K: the brake is what keeps judge pass up (without it judge falls to 38.9). CANDACE adds speed but costs judge pass. 3 NOISE micros bust.
  - 150K: more CANDACE micros help both speed and judge. 5–6 NOISE micros bust. With row A, $150–$250 stops lose about 13–20 pts of pass. Taper never helps speed.

Files: search.py (driver → results.json), report.py (tables), tables.md, slices.txt, lib50.py, sim150.py, gen_lib.py, repro50.py/.log, validate150.py/.log.
Run: `cd <worktree>/backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/search.py` (about 15 s, 4 workers).
