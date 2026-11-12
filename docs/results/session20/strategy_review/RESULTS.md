# Session 20 strategy review - NOISE baseline refinements (MNQ, 1 micro)

## 1. Verdict

| family | pick (IS only) | IS PF / $/tr / net / 25K pass | J PF / $/tr / net / 25K pass | verdict | reason |
|---|---|---|---|---|---|
| BASE | - | 1.50 / 27.16 / 14556 / 72% | 1.58 / 40.14 / 4737 / 68% | - | shipped config |
| F1 MES confirmation | F1 (MES close beyond MES band) | 1.63 / 33.13 / 13154 / 73% | 1.56 / 42.39 / 3561 / 64% (bust 36%) | REJECT | failed: J pf, J pass_, J bust, J net |
| F2 price-scaled lock | none eligible | - | - | REJECT | no variant met IS eligibility (PF>=base, net>=90%, n>=100) |
| F3 band-scaled lock | F3_1.25 (lock trigger 1.25 x sigma_k x price) | 1.52 / 27.49 / 14407 / 73% | 1.57 / 40.85 / 4942 / 69% (bust 31%) | REJECT | failed: J pf |
| F4 2nd ratchet | F4_150 (ratchet +150 -> +75) | 1.53 / 28.66 / 15676 / 76% | 1.50 / 35.59 / 4592 / 62% (bust 38%) | REJECT | failed: J pf, J avg, J pass_, J bust, J net |
| F5 exit cadence | none eligible | - | - | REJECT | no variant met IS eligibility (PF>=base, net>=90%, n>=100) |
| F6 exit rule | F6b (trail = band only) | 1.52 / 28.88 / 14640 / 73% | 1.57 / 40.95 / 4628 / 68% (bust 32%) | REJECT | failed: J pf, J pass_, J bust |

Adopted families: none. Combination test: not run (needs >= 2 adopted).

**Random-direction benchmark** (baseline timing/exits/lock, side random, 30 seeds): J 25K pass mean 45.6% (min 12, max 77, sd 18.1) vs baseline 68%; J PF mean 1.16 (range 0.75-1.58) vs 1.58; J net mean 1460 vs 4737. IS 25K pass mean 39.2%, IS PF mean 1.07 vs baseline IS 72% / 1.50.

## 2. Baseline reproduction (step 0)

Baseline stream (gen with Monday skip) vs `session19/refine/streams_noise_R6.csv` on 2021-10-21..2026-10-30: mine 654 trades, net $19,293; reference 654 trades, net $19,293; 654/654 (100%) identical on (d, ek, xk, side), identical P&L. Reproduction passes. (Reference 2019-2026 file apparently shares the same underlying bars/VWAP for this span.)

## 3. Full tables (p/b = bootstrap pass % / bust %; Lucid Pro, 600 paths x 400 sessions, 10-day blocks, seed 7)

### IS 2021-10-21..2025-11-05

| id | variant | trades | win% | PF | $/trade | net $ | maxDD $ | 25K p/b | 50K p/b | 100K p/b | 150K p/b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | 536 | 49.6 | 1.50 | 27.16 | 14556 | 2096 | 72/28 | 70/30 | 69/31 | 65/35 |
| F1 *PICK* | MES close beyond MES band | 397 | 54.4 | 1.63 | 33.13 | 13154 | 2284 | 73/27 | 72/28 | 70/29 | 66/34 |
| F1b (elig.) | MES close on side of MES VWAP | 509 | 49.9 | 1.52 | 28.16 | 14336 | 2456 | 69/31 | 67/33 | 66/34 | 63/37 |
| F2_0.30 | lock trigger 0.3% of price | 503 | 59.8 | 1.42 | 19.98 | 10049 | 1616 | 69/31 | 66/34 | 63/36 | 59/41 |
| F2_0.35 | lock trigger 0.35% of price | 516 | 56.6 | 1.42 | 20.99 | 10832 | 1738 | 70/30 | 67/33 | 64/36 | 60/39 |
| F2_0.40 | lock trigger 0.4% of price | 523 | 54.7 | 1.42 | 21.41 | 11200 | 2250 | 67/33 | 65/35 | 63/37 | 60/40 |
| F2_0.45 | lock trigger 0.45% of price | 525 | 52.6 | 1.43 | 22.80 | 11970 | 2096 | 67/33 | 66/34 | 64/36 | 60/40 |
| F2_0.50 | lock trigger 0.5% of price | 533 | 51.2 | 1.49 | 26.22 | 13976 | 2096 | 72/28 | 70/30 | 69/31 | 64/36 |
| F3_0.5 | lock trigger 0.5 x sigma_k x price | 473 | 67.0 | 1.72 | 27.39 | 12955 | 1016 | 84/16 | 83/17 | 81/17 | 80/19 |
| F3_0.75 | lock trigger 0.75 x sigma_k x price | 498 | 58.6 | 1.47 | 22.12 | 11016 | 1422 | 69/31 | 69/31 | 66/33 | 64/36 |
| F3_1.0 | lock trigger 1.0 x sigma_k x price | 514 | 55.4 | 1.46 | 23.47 | 12066 | 1468 | 69/31 | 68/32 | 66/34 | 63/37 |
| F3_1.25 *PICK* | lock trigger 1.25 x sigma_k x price | 524 | 53.1 | 1.52 | 27.49 | 14407 | 1536 | 73/27 | 71/29 | 70/30 | 66/34 |
| F3_1.5 | lock trigger 1.5 x sigma_k x price | 530 | 51.3 | 1.49 | 26.83 | 14222 | 2514 | 70/30 | 68/32 | 67/33 | 63/37 |
| F4_150 *PICK* | ratchet +150 -> +75 | 547 | 50.5 | 1.53 | 28.66 | 15676 | 2096 | 76/24 | 74/26 | 72/28 | 68/32 |
| F4_200 | ratchet +200 -> +100 | 541 | 49.7 | 1.47 | 25.70 | 13902 | 2096 | 72/28 | 71/29 | 69/31 | 65/35 |
| F4_250 (elig.) | ratchet +250 -> +125 | 538 | 49.8 | 1.52 | 28.09 | 15110 | 2096 | 74/26 | 72/28 | 71/29 | 66/34 |
| F4_300 (elig.) | ratchet +300 -> +150 | 538 | 49.8 | 1.51 | 27.74 | 14926 | 2096 | 73/27 | 71/29 | 70/30 | 65/35 |
| F5a | trail checked every 30 min | 576 | 47.9 | 1.46 | 23.14 | 13328 | 2325 | 68/32 | 67/33 | 66/34 | 63/37 |
| F5b | trail checked every 15 min | 608 | 44.6 | 1.46 | 21.03 | 12788 | 3094 | 70/30 | 68/32 | 66/33 | 62/37 |
| F6a | trail = VWAP only | 498 | 53.4 | 1.47 | 30.15 | 15012 | 1756 | 72/28 | 70/30 | 68/32 | 63/37 |
| F6b *PICK* | trail = band only | 507 | 50.7 | 1.52 | 28.88 | 14640 | 2048 | 73/27 | 71/29 | 70/30 | 66/34 |

### J 2025-11-06..2026-10-30

| id | variant | trades | win% | PF | $/trade | net $ | maxDD $ | 25K p/b | 50K p/b | 100K p/b | 150K p/b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | 118 | 59.3 | 1.58 | 40.14 | 4737 | 1024 | 68/32 | 65/35 | 62/38 | 57/43 |
| F1 *PICK* | MES close beyond MES band | 84 | 58.3 | 1.56 | 42.39 | 3561 | 974 | 64/36 | 63/37 | 60/40 | 58/42 |
| F1b (elig.) | MES close on side of MES VWAP | 111 | 59.5 | 1.57 | 40.70 | 4518 | 870 | 64/36 | 62/38 | 60/40 | 55/45 |
| F2_0.30 | lock trigger 0.3% of price | 115 | 63.5 | 1.67 | 42.83 | 4926 | 1040 | 74/26 | 72/28 | 70/30 | 65/35 |
| F2_0.35 | lock trigger 0.35% of price | 117 | 61.5 | 1.64 | 42.17 | 4934 | 1024 | 71/29 | 68/32 | 66/34 | 60/40 |
| F2_0.40 | lock trigger 0.4% of price | 119 | 58.8 | 1.57 | 39.93 | 4752 | 1048 | 66/34 | 64/36 | 61/39 | 56/44 |
| F2_0.45 | lock trigger 0.45% of price | 120 | 57.5 | 1.62 | 44.23 | 5308 | 1058 | 68/32 | 64/36 | 62/38 | 56/44 |
| F2_0.50 | lock trigger 0.5% of price | 123 | 55.3 | 1.54 | 40.40 | 4970 | 1304 | 63/37 | 60/40 | 57/43 | 51/49 |
| F3_0.5 | lock trigger 0.5 x sigma_k x price | 110 | 65.5 | 1.25 | 15.70 | 1727 | 1045 | 44/56 | 42/58 | 38/62 | 34/66 |
| F3_0.75 | lock trigger 0.75 x sigma_k x price | 116 | 61.2 | 1.57 | 37.85 | 4390 | 1058 | 67/33 | 65/35 | 62/38 | 57/43 |
| F3_1.0 | lock trigger 1.0 x sigma_k x price | 120 | 58.3 | 1.62 | 42.78 | 5134 | 1171 | 70/30 | 68/32 | 66/34 | 59/41 |
| F3_1.25 *PICK* | lock trigger 1.25 x sigma_k x price | 121 | 56.2 | 1.57 | 40.85 | 4942 | 1304 | 69/31 | 66/34 | 63/37 | 56/44 |
| F3_1.5 | lock trigger 1.5 x sigma_k x price | 123 | 53.7 | 1.45 | 35.39 | 4352 | 1553 | 62/38 | 59/41 | 56/44 | 52/48 |
| F4_150 *PICK* | ratchet +150 -> +75 | 129 | 58.1 | 1.50 | 35.59 | 4592 | 1304 | 62/38 | 60/40 | 57/43 | 54/46 |
| F4_200 | ratchet +200 -> +100 | 125 | 59.2 | 1.55 | 37.88 | 4735 | 1228 | 66/34 | 63/37 | 60/40 | 54/46 |
| F4_250 (elig.) | ratchet +250 -> +125 | 122 | 57.4 | 1.46 | 34.59 | 4220 | 1046 | 63/37 | 59/41 | 56/44 | 50/50 |
| F4_300 (elig.) | ratchet +300 -> +150 | 123 | 56.9 | 1.44 | 33.84 | 4162 | 1224 | 61/39 | 57/43 | 54/46 | 49/51 |
| F5a | trail checked every 30 min | 125 | 52.8 | 1.42 | 28.90 | 3612 | 1076 | 61/39 | 59/41 | 56/44 | 50/50 |
| F5b | trail checked every 15 min | 136 | 47.1 | 1.29 | 19.92 | 2709 | 1472 | 52/48 | 48/52 | 45/55 | 42/58 |
| F6a | trail = VWAP only | 114 | 57.9 | 1.38 | 31.86 | 3632 | 1188 | 54/46 | 50/50 | 46/54 | 44/56 |
| F6b *PICK* | trail = band only | 113 | 58.4 | 1.57 | 40.95 | 4628 | 1024 | 68/32 | 65/35 | 62/38 | 56/44 |

### ALL

| id | variant | trades | win% | PF | $/trade | net $ | maxDD $ | 25K p/b | 50K p/b | 100K p/b | 150K p/b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | baseline | 654 | 51.4 | 1.52 | 29.50 | 19293 | 2096 | 75/25 | 72/28 | 70/30 | 68/32 |
| F1 *PICK* | MES close beyond MES band | 481 | 55.1 | 1.61 | 34.75 | 16716 | 2284 | 76/24 | 74/26 | 72/27 | 70/30 |
| F1b (elig.) | MES close on side of MES VWAP | 620 | 51.6 | 1.53 | 30.41 | 18854 | 2456 | 73/27 | 70/30 | 69/31 | 66/34 |
| F2_0.30 | lock trigger 0.3% of price | 618 | 60.5 | 1.48 | 24.23 | 14974 | 1616 | 71/29 | 68/32 | 66/34 | 64/36 |
| F2_0.35 | lock trigger 0.35% of price | 633 | 57.5 | 1.47 | 24.91 | 15766 | 1738 | 70/30 | 67/33 | 65/35 | 64/36 |
| F2_0.40 | lock trigger 0.4% of price | 642 | 55.5 | 1.45 | 24.85 | 15952 | 2250 | 70/30 | 66/34 | 64/36 | 62/38 |
| F2_0.45 | lock trigger 0.45% of price | 645 | 53.5 | 1.48 | 26.79 | 17278 | 2096 | 71/29 | 68/32 | 66/34 | 64/36 |
| F2_0.50 | lock trigger 0.5% of price | 656 | 52.0 | 1.50 | 28.88 | 18946 | 2096 | 73/27 | 71/29 | 68/32 | 67/33 |
| F3_0.5 | lock trigger 0.5 x sigma_k x price | 583 | 66.7 | 1.59 | 25.18 | 14682 | 1045 | 77/23 | 76/24 | 73/25 | 71/29 |
| F3_0.75 | lock trigger 0.75 x sigma_k x price | 614 | 59.1 | 1.49 | 25.09 | 15406 | 1422 | 74/26 | 72/28 | 70/30 | 66/33 |
| F3_1.0 | lock trigger 1.0 x sigma_k x price | 634 | 56.0 | 1.50 | 27.13 | 17199 | 1468 | 74/26 | 71/29 | 70/30 | 66/34 |
| F3_1.25 *PICK* | lock trigger 1.25 x sigma_k x price | 645 | 53.6 | 1.53 | 30.00 | 19350 | 1536 | 75/25 | 73/27 | 71/29 | 68/32 |
| F3_1.5 | lock trigger 1.5 x sigma_k x price | 653 | 51.8 | 1.48 | 28.44 | 18574 | 2514 | 72/28 | 70/30 | 68/32 | 64/36 |
| F4_150 *PICK* | ratchet +150 -> +75 | 676 | 51.9 | 1.53 | 29.98 | 20267 | 2096 | 75/25 | 73/27 | 71/28 | 69/31 |
| F4_200 | ratchet +200 -> +100 | 666 | 51.5 | 1.49 | 27.98 | 18636 | 2096 | 73/27 | 70/30 | 69/31 | 67/33 |
| F4_250 (elig.) | ratchet +250 -> +125 | 660 | 51.2 | 1.50 | 29.29 | 19330 | 2096 | 73/27 | 71/29 | 69/31 | 66/34 |
| F4_300 (elig.) | ratchet +300 -> +150 | 661 | 51.1 | 1.49 | 28.88 | 19088 | 2096 | 73/27 | 70/30 | 68/31 | 66/34 |
| F5a | trail checked every 30 min | 701 | 48.8 | 1.45 | 24.17 | 16940 | 2325 | 72/28 | 71/29 | 68/32 | 65/35 |
| F5b | trail checked every 15 min | 744 | 45.0 | 1.42 | 20.83 | 15497 | 3094 | 71/29 | 68/32 | 67/33 | 64/36 |
| F6a | trail = VWAP only | 612 | 54.2 | 1.45 | 30.47 | 18645 | 1756 | 70/30 | 67/33 | 64/36 | 61/39 |
| F6b *PICK* | trail = band only | 620 | 52.1 | 1.53 | 31.08 | 19268 | 2048 | 75/25 | 73/27 | 72/28 | 70/30 |

(*PICK* = selected on IS; (elig.) = passed IS eligibility but not the best; unmarked rows were not picked, FYI only.)

### Paired block-bootstrap 95% CI of net difference vs base ($)

| id | J delta [lo, hi] | IS delta [lo, hi] |
|---|---|---|
| F1 | -1176 [-3436, 1412] | -1402 [-5947, 2015] |
| F1b | -219 [-1181, 866] | -220 [-1985, 1622] |
| F2_0.30 | 188 [-1210, 1572] | -4507 [-8605, -955] |
| F2_0.35 | 197 [-857, 1340] | -3724 [-7522, -685] |
| F2_0.40 | 14 [-480, 446] | -3356 [-6400, -514] |
| F2_0.45 | 570 [-597, 974] | -2586 [-4971, -456] |
| F2_0.50 | 232 [-1076, 860] | -580 [-1901, 694] |
| F3_0.5 | -3010 [-5554, -690] | -1601 [-6508, 3036] |
| F3_0.75 | -346 [-1520, 770] | -3540 [-7392, -18] |
| F3_1.0 | 396 [-615, 1436] | -2490 [-5524, 288] |
| F3_1.25 | 206 [-874, 1342] | -149 [-1932, 1543] |
| F3_1.5 | -384 [-1914, 878] | -334 [-2021, 1156] |
| F4_150 | -146 [-1178, 1021] | 1120 [-88, 2375] |
| F4_200 | -2 [-755, 808] | -654 [-2329, 544] |
| F4_250 | -516 [-1273, 12] | 554 [-36, 1369] |
| F4_300 | -574 [-1331, 0] | 370 [0, 1084] |
| F5a | -1125 [-2364, 343] | -1228 [-3608, 874] |
| F5b | -2028 [-3902, 333] | -1768 [-5013, 1669] |
| F6a | -1104 [-2384, 431] | 456 [-2266, 3239] |
| F6b | -110 [-350, 16] | 84 [-371, 612] |

### PF by calendar year (n trades)

| id | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| BASE | 1.61 (132) | 1.60 (142) | 1.88 (136) | 1.13 (113) | 1.56 (107) |
| F1 | 2.01 (100) | 1.40 (102) | 2.11 (99) | 1.12 (89) | 1.60 (74) |
| F1b | 1.60 (131) | 1.55 (131) | 2.01 (128) | 1.15 (106) | 1.56 (100) |
| F2_0.30 | 1.34 (121) | 1.51 (130) | 1.94 (129) | 1.19 (110) | 1.60 (104) |
| F2_0.35 | 1.36 (124) | 1.40 (137) | 2.04 (131) | 1.23 (111) | 1.57 (106) |
| F2_0.40 | 1.38 (125) | 1.56 (138) | 1.95 (134) | 1.12 (113) | 1.55 (108) |
| F2_0.45 | 1.48 (125) | 1.53 (140) | 1.92 (134) | 1.19 (114) | 1.55 (108) |
| F2_0.50 | 1.65 (130) | 1.53 (141) | 1.92 (136) | 1.11 (116) | 1.57 (109) |
| F3_0.5 | 1.87 (120) | 1.61 (123) | 1.70 (119) | 1.72 (99) | 1.28 (99) |
| F3_0.75 | 1.49 (126) | 1.57 (128) | 1.77 (125) | 1.24 (107) | 1.56 (105) |
| F3_1.0 | 1.55 (131) | 1.54 (131) | 1.84 (130) | 1.18 (109) | 1.66 (109) |
| F3_1.25 | 1.59 (132) | 1.50 (138) | 2.04 (131) | 1.14 (111) | 1.64 (109) |
| F3_1.5 | 1.60 (132) | 1.62 (139) | 2.01 (132) | 1.00 (115) | 1.55 (111) |
| F4_150 | 1.62 (133) | 1.59 (142) | 1.95 (141) | 1.18 (118) | 1.48 (118) |
| F4_200 | 1.60 (133) | 1.60 (142) | 1.86 (138) | 1.04 (115) | 1.53 (114) |
| F4_250 | 1.63 (132) | 1.60 (142) | 1.94 (138) | 1.13 (113) | 1.44 (111) |
| F4_300 | 1.61 (132) | 1.60 (142) | 1.92 (137) | 1.13 (114) | 1.42 (112) |
| F5a | 1.55 (141) | 1.60 (151) | 1.85 (146) | 1.02 (124) | 1.46 (113) |
| F5b | 1.61 (147) | 1.69 (158) | 1.91 (153) | 0.88 (133) | 1.34 (124) |
| F6a | 1.58 (124) | 1.42 (129) | 1.93 (126) | 1.11 (108) | 1.35 (103) |
| F6b | 1.61 (130) | 1.62 (133) | 1.94 (126) | 1.13 (105) | 1.55 (102) |

### Selection details

- F1: eligible = ['F1', 'F1b']; pick = F1
- F2: eligible = []; pick = None
- F3: eligible = ['F3_1.25']; pick = F3_1.25
- F4: eligible = ['F4_150', 'F4_250', 'F4_300']; pick = F4_150
- F5: eligible = []; pick = None
- F6: eligible = ['F6b']; pick = F6b

## 4. Caveats

- J is ~245 sessions (118 baseline trades): wide uncertainty; see paired CIs. J was seen in earlier sessions, so it is not a pristine holdout.
- Multiple testing: about 25 variant rows, so roughly one false positive is expected by chance.
- News blackouts / event days are not modelled. No volume, VWAP is the precomputed series. Fees $1 RT + 1 tick per fill, 1 micro.
- Interpretation choices: ratchet exits (F4) do not end NOISE for the day (only the +10 lock stop-out does); F5 extra exit checks at k=29+30n / 29+15n up to 15:00 (entries remain hourly); F3 sigma_k is the check-bar sigma at the entry decision; 'within 1 pt' = not worse by more than 1 pt.
- Eval bootstraps for IS/J draw from a bday calendar of that window (days without trades count as zero).

## 5. Review notes (main session, 2026-11-12)

- Data: Databento is still locked, so this study uses the MNQ + MES 1-minute RTH cache recovered from git history
  (`docs/results/session12/days.pkl`, blob fabd3f3, 2021-10-01..2026-10-30). The baseline matches session-19 R6 trade for trade on that span.
- **Nothing is adopted; the shipped NOISE eval config (preset C lock 100 → +10, Mondays off, fade off in evals) stays as it is.**
- Over-fit trap worth remembering: tighter locks look excellent in-sample and fail in J. F3 0.5σ: IS 25K pass 84/16, win 67 %, max DD $1,016 →
  J PF 1.25, 25K 44/56. F2 0.30 %: the opposite (IS net −31 %, significant; J slightly better). The 100 pt lock sits in a flat, stable region.
- F1 (MES must also break out) raises IS PF to 1.63 and win % to 54 but removes ~27 % of trades and does not hold in J → no market-wide
  confirmation benefit for NOISE on MNQ.
- Exits: the paper's max(band, VWAP) trail checked hourly is the best of the exit rules tried; checking it more often (30/15 min) is worse in
  both periods (consistent with session 15's 30-min entry+exit test).
- J resolution: random-direction NOISE scores J 25K pass 12–77 % across 30 seeds (sd 18). A J pass difference under ~10 pt cannot be told
  apart from luck; only changes that also hold in IS (and ideally year by year) are worth acting on.
