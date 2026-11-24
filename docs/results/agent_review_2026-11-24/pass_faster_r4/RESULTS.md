# Pass faster, round 4 (2026-11-24, research only: no app code changed, nothing pushed)
Sim: refine_round3/harness.py (pass_fastest/sim150.py + patches) on /home/user/days.pkl, extended to 25K/100K in `h4.py`. Lucid rules: 40 % consistency, 38 % day stop, DLL, EOD MLL with lock, NOISE profit lock, $2/micro RT in base. Pick = starts 2021-10..2023-12, judge = 2024-01..2026-10. Scripts: h4.py, repro4.py, grid4.py (pre-registration in its header), report4.py; data results4.json, table4.md.

## 1. Reproduced built rows (current yaml fast_pass_*_cfg)
| plan | config | all pass/med d | pick | judge | stuck+bust | 5-yr static profit |
|---|---|---|---|---|---|---|
| 25K | N1@$75 + C2 [333>1] | 61.8 / 56.5 | 62.5 / 42 | 54.6 / 67 | 29.6 | $19,328 |
| 50K | N2@$75 [667>1] + C4 [1000>3], dl0.4, lock80 | 66.3 / 61 | 68.2 / 50 | 56.5 / 64.5 | 26.2 | $39,080 |
| 100K | N3@$100 [1000>2] + C3 [600>2], dl0.5 | 71.4 / 87 | 68.9 / 79 | 65.8 / 88 | 20.0 | $60,345 |
| 150K | N5@$100 [2250>2,1500>1] grow500 max6 + C5 [2700>4,1500>1] grow1500 max6, dl0.7 | 74.4 / 80 | 72.8 / 66 | 57.3 / 70 | 4.4 | $100,575 |
50K and 150K match final_search / refine_round3 exactly. Late-day leg (D166, unverified) is NOT modelled (as in all prior studies). Static profit ignores grow/lock.

## 2. Pre-registration (fixed before judging; 31 variants)
ADOPT CANDIDATE iff strictly better than built on pick AND judge for pass % AND median days, profit not lower, all-window pass >= floor (62/62/70/70), all-window pass at +$2 extra cost >= built at +$2, and half-year min >= built. Families: (1) brake ladder thresholds x0.75 / x1.33 (4 plans = 8); grow rules (150K NOISE grow 300/750, CANDACE grow 1000/2250; 100K NOISE/CANDACE grow 1000 max 4; 50K CANDACE grow 700 max 5; 25K CANDACE grow 400 max 3 = 8); (3) day stop 30 % / 45 % of target and day lock 0.3 (4 plans = 12); (4) front-loading bigger start sizes with the same brakes (100K N4C4, 50K C5, 25K C3 = 3). Expected false wins at ~10 % each: ~3. Families (2) late leg and (6) multi-account could not be simulated (no late-day or household model in this sim); (5) pass-day stop is already in the sim (trading ends at target with consistency satisfied), so there is nothing to vary.

## 3. Results (full table)
| plan | variant | pick pass/med | judge pass/med | all pass/med | stuck+bust | profit | +$2 all/judge | HY min/med/max | candidate |
|---|---|---|---|---|---|---|---|---|---|
| 25K | BUILT | 62.5/42 | 54.6/67 | 61.8/56.5 | 29.6 | 19328 | 58.2/52.2 | 0/81/100 | - |
| 25K | brake_x0.75 | 62.5/42 | 54.6/67 | 61.7/56 | 29.7 | 19328 | 58.5/52.3 | 0/81/100 | no |
| 25K | brake_x1.33 | 62.5/42 | 54.5/67 | 61.6/56 | 29.7 | 19328 | 58.2/52.3 | 0/80/100 | no |
| 25K | dstop0.3 | 62.3/43 | 48.9/79 | 58.5/61 | 29.8 | 19328 | 53.7/44.5 | 0/50/100 | no |
| 25K | dstop0.45 | 62.5/42 | 57.6/69 | 63.5/58 | 29.8 | 19328 | 58.2/52.2 | 0/81/100 | no |
| 25K | dstop0.38_dl0.3 | 62.5/42 | 54.8/62 | 61.9/55 | 29.3 | 19328 | 58.4/52.5 | 0/80/100 | no |
| 50K | BUILT | 68.2/50 | 56.5/64.5 | 66.3/61 | 26.2 | 39080 | 58.8/52.2 | 2/73/100 | - |
| 50K | brake_x0.75 | 60.5/47 | 57.2/66 | 62.4/59 | 30.5 | 39080 | 57.3/52.5 | 0/73/100 | no |
| 50K | brake_x1.33 | 59.8/48 | 56.0/69 | 62.4/60 | 30.4 | 39080 | 59.3/51.9 | 0/69/100 | no |
| 50K | dstop0.3 | 68.2/52 | 48.7/77 | 61.9/70 | 26.7 | 39080 | 55.6/46.5 | 0/67/100 | no |
| 50K | dstop0.45 | 68.2/50 | 56.9/65 | 66.5/61 | 26.8 | 39080 | 60.6/55.5 | 2/73/100 | no |
| 50K | dstop0.38_dl0.3 | 68.2/51 | 58.0/63 | 67.2/60 | 25.3 | 39080 | 59.4/53.3 | 2/73/100 | no |
| 100K | BUILT | 68.9/79 | 65.8/88 | 71.4/87 | 20.0 | 60345 | 55.1/46.4 | 0/82/100 | - |
| 100K | brake_x0.75 | 61.2/75 | 48.9/73 | 56.5/75 | 34.8 | 60345 | 55.0/51.6 | 0/81/100 | no |
| 100K | brake_x1.33 | 69.3/79 | 49.9/74 | 62.9/80 | 27.6 | 60345 | 62.2/50.8 | 0/73/100 | no |
| 100K | dstop0.3 | 68.9/79 | 51.6/85 | 63.4/86 | 25.6 | 60345 | 52.5/41.7 | 0/65/100 | no |
| 100K | dstop0.45 | 68.9/79 | 67.2/92.5 | 72.2/89 | 19.6 | 60345 | 55.4/47.0 | 0/86/100 | no |
| 100K | dstop0.38_dl0.3 | 68.9/79 | 65.8/88 | 71.4/87 | 20.0 | 60345 | 55.1/46.4 | 0/82/100 | no |
| 150K | BUILT | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 63.7/40.1 | 0/84/100 | - |
| 150K | brake_x0.75 | 72.6/66 | 46.2/60.5 | 69.4/74 | 16.6 | 100575 | 62.8/43.3 | 0/94/100 | no |
| 150K | brake_x1.33 | 72.2/77 | 49.4/80.5 | 71.5/97 | 0.0 | 100575 | 65.2/39.3 | 0/100/100 | no |
| 150K | dstop0.3 | 72.8/68 | 53.5/73 | 70.9/82.5 | 5.9 | 100575 | 60.7/38.6 | 0/77/100 | no |
| 150K | dstop0.45 | 72.8/66 | 58.6/74 | 76.7/82 | 2.1 | 100575 | 67.5/42.8 | 0/100/100 | no |
| 150K | dstop0.38_dl0.3 | 72.8/67 | 57.9/70 | 74.7/80 | 4.1 | 100575 | 63.3/39.6 | 0/84/100 | no |
| 150K | ngrow300 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 63.7/40.1 | 0/84/100 | no |
| 150K | ngrow750 | 72.8/66 | 57.3/70 | 74.4/80 | 4.4 | 100575 | 63.7/40.1 | 0/84/100 | no |
| 150K | cgrow1000 | 72.8/66.5 | 58.0/71 | 75.6/82.5 | 3.4 | 100575 | 63.6/40.1 | 0/92/100 | no |
| 150K | cgrow2250 | 72.8/67 | 49.1/65.5 | 71.0/76 | 9.6 | 100575 | 65.1/39.4 | 0/97/100 | no |
| 100K | ngrow1000max4 | 62.2/63 | 48.4/65 | 56.9/66 | 32.3 | 60345 | 51.7/44.7 | 0/59/100 | no |
| 100K | cgrow1000max4 | 67.8/77 | 52.9/74 | 62.4/78 | 29.2 | 60345 | 58.5/53.3 | 0/81/100 | no |
| 50K | cgrow700max5 | 66.9/48.5 | 56.5/65 | 65.3/60 | 29.5 | 39080 | 56.7/49.9 | 0/67/100 | no |
| 25K | cgrow400max3 | 62.0/39 | 51.1/61 | 59.3/52 | 36.7 | 19328 | 53.5/49.1 | 0/61/100 | no |
| 100K | front_N4C4 | 54.5/53 | 48.1/61 | 52.2/58 | 40.5 | 80460 | 49.2/44.5 | 0/63/100 | no |
| 50K | front_C5 | 65.3/48 | 56.6/64 | 64.5/59 | 29.9 | 40928 | 56.9/50.4 | 0/69/100 | no |
| 25K | front_C3 | 55.6/34 | 51.1/67 | 55.1/47.5 | 41.0 | 21175 | 46.9/40.7 | 0/59/100 | no |
(+$2 column = all-window / judge pass with $2 more per micro RT on both legs. HY = pass % by start half-year; min is 0 for every row because the short 2026H2 bucket cannot pass in time, so the useful signal is the median: compare with refine_round3 where 2026H2 was excluded and built 150K had min 38 % (2025H2).)

## 4. Verdicts
- **0 of 31 variants are ADOPT CANDIDATES.** No multiplicity concern.
- Faster but worse: front-loading (100K N4C4: median 58 d vs 87, but pass 52 % vs 71 %, stuck+bust 41 %; 25K C3: 47.5 d but 55 %), tighter brakes (150K x0.75: 74 d but judge 46 %), faster NOISE grow on 100K (66 d, 57 %). Every route to fewer days here buys it with bust risk: speed and pass % trade off along one frontier, and built sits on it.
- Closest: day stop 45 % (150K 76.7 % / 82 d, judge 58.6 %; 100K 72.2 / 89; 25K 63.5 / 58). It raises pass a little but is slower on judge median for every plan, so it fails the rule. It also leaves less consistency room (a 45 % day breaks the 40 % rule unless more days follow), so it is not a pass-faster lever. 150K CANDACE grow 1000 is the refine_round3 "C6" tie again (+1.2 pts, +2.5 d slower).
- Inert: 150K NOISE grow 300/750 (identical to built), 25K brakes, 100K day lock 0.3.
- Cost +$2: every row loses 3-17 pts; built 150K 74.4 -> 63.7, 100K 71.4 -> 55.1. 100K brake x1.33 is the only row clearly more cost-robust (62.2 vs 55.1) but it is worse at base cost (62.9 %, judge 49.9 %): do not choose on the perturbed scenario.
- Fragility: pick-window pass barely moves for any knob; the judge window (2024-26) decides everything, and pass % is a regime on/off by start half-year (model_qa finding 1 still holds).

## 5. Funded / live accounts (not simulated; reasoning from the rules)
Fast Evaluation sizing is tuned to reach a target before MLL; funded payout rules reward the opposite. Payout consistency 40 %/35 % means a single big day (which the 9-12 micro 150K ladder makes likely: one CANDACE+NOISE winner can be $2-3K) must be diluted by more trading days before a payout; the 38 % day stop is above the 35 % payout cap, so on 35 % plans the day stop should be <= ~33 % of the payout-window profit. DLL ($2,700 on 150K) is hit by about 2.5 full $100-stop losses at 9+ micros, and a funded MLL that has locked at start+$100 leaves the cushion at just the locked buffer, so the brake ladder should key off the funded cushion (it does in fast_pass.py by design: cushion = equity - current MLL). Recommendation: on funded/live, start at the brake (reduced) step sizes, not the eval start sizes, until cushion exceeds the top step; this needs its own study with the payout rules before anyone trusts it.

## 6. Plain-language recommendation
Keep the built Fast Evaluation settings on all four plans. Nothing we tried passes faster without passing less often or failing the cost and out-of-sample checks; the knobs that cut days (bigger start size, tighter brakes, faster grow) do it by busting more accounts. The true limit is the edge itself (and costs), not the ladder. Worth doing next: model the late-day leg and multiple accounts, and run a funded-payout study before using eval sizes on funded/live accounts. Nothing adopted; the user decides.
