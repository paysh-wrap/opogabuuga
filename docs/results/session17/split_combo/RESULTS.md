# NOISE + AI Duo split 50/50 vs NOISE alone (session 17 study)

Research only. No app code, config or tests were touched. **The AI direction accuracy is SIMULATED; real accuracy is unproven, so every "AI x%" row is a bound ("if the AI were x% right"), not a forecast.** Held-out = 2024-01 .. 2026-11 (the judge); in-sample = 2019-05 .. 2023-12 (where a combination would be picked). Nothing was tuned: all rules were fixed before any run.

## Plain-language verdict

1. **At realistic AI accuracy (50-56%, the published range for LLM next-day calls, session 11) the split does NOT beat NOISE alone on any Pro account.** On the held-out years: 25K is clearly worse (bootstrap pass 41-45% vs 57%, bust 55-59% vs 43%); 50K is break-even at best (55%: +2 pp pass); 100K and 150K only become "safer but slower" (fewer busts, much longer evals, and $5-21k less profit than NOISE alone). At 50% accuracy the Duo half earns about +$1.7k in 2.8 years (about nothing after fees) while NOISE at half size gives up $10k (50K) to $23k (150K) of NOISE profit.
2. **Break-even accuracy, held-out, vs NOISE alone at the app's default full size:** about **60% on Pro 50K and 100K** (bootstrap PASS +11 / +17 pp, BUST -11 / -16 pp, split better in 95-100% of the 40 AI seeds), about **70% on Pro 25K and 150K**. Picked on in-sample years the bar is higher: **65% on 50K, 70% on 100K, never on 25K, "safer but slower" only on 150K**. Taking the two periods together, a split is only defensible at **AI accuracy of 65% or better**; nobody has measured the app's AI above ~56% (the app itself requires a proven 70% ledger before AI advises, D55).
3. **Combinations that could work (if the AI really reaches the accuracy):** **Pro 50K at 65%+** (works in-sample and held-out, with Duo on MNQ+MGC, MNQ only, and under the strict "1 open position" rule); **Pro 100K at 65-70%+** (held-out yes from 60%, in-sample only at 70%); **Pro 150K at 70%** (held-out only; otherwise it is the safe-but-slow option: median 216-390 sessions to pass vs 141); **Pro 25K: no** (the split puts 2 micros on a $1,000 loss limit; in-sample it loses at every accuracy, held-out it needs 70% and still busts 39%).
4. **Most of the split's gain on 50K-100K is not the AI.** The app's default full size puts NOISE at 2 micros on 50K/100K (3 on 150K), which busts 40% / 31% / 31% of bootstrap evals; any 1-micro NOISE already cuts that (the "half size" row: bust 22% / 9% / 2%, but very slow on 100K/150K). Against that 1-micro NOISE the AI half only helps at **70% (50K), 65-70% (25K, 150K)** and **never on 100K** (HO), and nothing helps in-sample except 65-70% on 100K/150K. Against the session-15 recommended NOISE sizes the picture is similar (sensitivity matrices below: 50K needs 65%, 100K never, 150K 65%, 25K 70%).
5. **Speed vs safety:** "round down, min 1" turns NOISE at 150K from 3 micros into 1 micro (1/3, not 1/2) and every split is 1 + 1 micro on 50K-150K. That is why the 100K/150K splits rarely bust once the AI is 60%+ right (bootstrap BUST 0-14%) but take 140-390 sessions; the rolling 250-session test therefore leaves 29-87% of 150K starts unfinished while the bootstrap (run to the end) shows 72-99% eventually pass. Whether a 10-18 month evaluation is allowed is still an open question to Lucid.

## Verdict matrix (split vs NOISE alone)

**Y** = split better: bootstrap PASS up and BUST not up, and the 250-session rolling run not worse. **s** = safer but slower (BUST clearly lower, fewer evals finish inside 250 sessions). **-** = no better.

Held-out 2024-2026 (the judge), main scenario (Duo on MNQ + MGC), vs NOISE alone at the app's full size:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | **Y** |
| Pro 50K | - | - | **Y** | **Y** | **Y** |
| Pro 100K | - | s | **Y** | **Y** | **Y** |
| Pro 150K | s | s | s | s | **Y** |

In-sample 2019-2023 (where the call is picked), same comparison:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | - |
| Pro 50K | - | - | - | **Y** | **Y** |
| Pro 100K | - | - | - | s | **Y** |
| Pro 150K | - | s | s | s | s |

Held-out, vs NOISE alone at half size (= 1 micro on every account here; isolates what the AI Duo half adds):

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | **Y** | **Y** |
| Pro 50K | - | - | - | - | **Y** |
| Pro 100K | - | - | - | - | - |
| Pro 150K | - | - | - | **Y** | **Y** |

### How to read the two estimators
- **roll** (rolling starts, the requested test): a start on every 2nd session; held-out starts run from 2024-01 to about 2025-11 (an eval needs 250 sessions of data after the start), so there are about 247 heavily overlapping starts = only 2-3 genuinely different eval episodes. Noisy by construction; the seed spread columns show it.
- **boot** (block bootstrap, 600 paths of 10-session blocks drawn from the held-out days, run until pass/bust, up to 750 sessions): no end-of-data censoring, so it is the better number for slow setups. It validates against session 15 (NOISE at the session-15 150K size: boot 79% pass / 18% bust / median 182 vs session-15 README 77 / 18 / 182) and my rolling engine (session-15 sizes, no strategy budgets) reproduces session-15's own rolling numbers (25K 51.8/48.2/48.5 vs 51.4/48.6/48; 50K 60.3/23.9/139 vs 60.0/24.1/139; 100K 41.3/0/128 vs 40.8/0/127; 150K 37.2/0/107.5 vs 36.3/0/105).

## Held-out tables, main scenario (Duo on MNQ + MGC, hedge lock)

HO = 2024-01 .. 2026-11. 'split' rows: mean over 40 seeds, [min..max] across seeds for net $ and PASS %. 'roll' = rolling-start eval, 250-session horizon, starts every 2nd session (a start whose eval is not finished = OPEN). 'boot' = 600 block-bootstrap paths (10-session blocks drawn from the held-out days), eval run to the end (up to 750 sessions). Trades / win % / net $ / max DD $ = a continuous account over the whole era (reset to the start balance after a bust), closed-trade drawdown. Median days = trading sessions.

**Pro 25K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 425 | 52.5 | 12,066 | 2,028 | 52 | 48 | 0 | 48 | 57 | 43 | 36 |
| NOISE alone, half size (diagnostic) | 372 | 51.9 | 9,148 | 1,502 | 46 | 54 | 0 | 55 | 52 | 48 | 40 |
| **split, AI 50%** | 1,302 | 42.8 | 10,927 [3,678..17,053] | 3,733 | 47 [28..67] | 53 | 0 | 26 | 41 [29..50] | 59 | 19 |
| **split, AI 55%** | 1,308 | 44.0 | 14,745 [6,339..22,160] | 3,311 | 53 [36..77] | 47 | 0 | 25 | 45 [32..56] | 55 | 19 |
| **split, AI 60%** | 1,313 | 45.1 | 18,746 [12,236..24,593] | 2,957 | 59 [43..78] | 41 | 0 | 25 | 51 [43..60] | 49 | 19 |
| **split, AI 65%** | 1,319 | 46.3 | 23,082 [13,803..30,900] | 2,579 | 65 [43..84] | 35 | 0 | 24 | 56 [43..67] | 44 | 19 |
| **split, AI 70%** | 1,325 | 47.5 | 27,424 [19,125..34,848] | 2,357 | 71 [58..86] | 29 | 0 | 24 | 61 [52..72] | 39 | 18 |

**Pro 50K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 426 | 52.3 | 22,199 | 4,056 | 70 | 29 | 0 | 92 | 60 | 40 | 56 |
| NOISE alone, half size (diagnostic) | 426 | 52.3 | 11,858 | 2,028 | 60 | 24 | 16 | 139 | 78 | 22 | 139 |
| **split, AI 50%** | 1,374 | 43.3 | 13,332 [5,138..19,418] | 3,975 | 59 [38..91] | 41 | 0 | 88 | 53 [32..71] | 47 | 75 |
| **split, AI 55%** | 1,380 | 44.4 | 17,437 [8,906..24,239] | 3,460 | 67 [41..98] | 32 | 0 | 81 | 62 [44..86] | 38 | 71 |
| **split, AI 60%** | 1,385 | 45.5 | 21,555 [14,794..28,086] | 3,028 | 78 [47..100] | 22 | 0 | 76 | 71 [58..89] | 29 | 68 |
| **split, AI 65%** | 1,391 | 46.6 | 26,077 [16,829..33,945] | 2,702 | 85 [68..100] | 15 | 0 | 70 | 79 [64..90] | 21 | 63 |
| **split, AI 70%** | 1,396 | 47.8 | 30,587 [22,835..39,049] | 2,370 | 93 [79..100] | 7 | 0 | 65 | 85 [72..96] | 15 | 59 |

**Pro 100K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 427 | 52.2 | 22,366 | 4,056 | 53 | 24 | 23 | 128 | 69 | 31 | 138 |
| NOISE alone, half size (diagnostic) | 427 | 52.2 | 11,609 | 2,028 | 5 | 0 | 95 | 243 | 86 | 9 | 332 |
| **split, AI 50%** | 1,376 | 43.3 | 13,009 [4,500..19,169] | 3,986 | 35 [5..84] | 35 | 29 | 185 | 64 [32..88] | 35 | 221 |
| **split, AI 55%** | 1,382 | 44.4 | 17,120 [8,449..23,587] | 3,484 | 52 [20..98] | 22 | 26 | 176 | 76 [51..97] | 23 | 199 |
| **split, AI 60%** | 1,387 | 45.5 | 21,248 [14,337..27,836] | 3,037 | 69 [36..99] | 12 | 19 | 163 | 86 [73..98] | 14 | 177 |
| **split, AI 65%** | 1,392 | 46.6 | 25,811 [16,372..33,695] | 2,734 | 84 [44..100] | 6 | 10 | 150 | 92 [79..99] | 8 | 156 |
| **split, AI 70%** | 1,398 | 47.7 | 30,305 [22,085..38,799] | 2,410 | 96 [75..100] | 1 | 3 | 139 | 96 [87..100] | 4 | 138 |

**Pro 150K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 427 | 52.2 | 34,328 | 6,084 | 56 | 24 | 20 | 132 | 69 | 31 | 141 |
| NOISE alone, half size (diagnostic) | 427 | 52.2 | 11,609 | 2,028 | 0 | 0 | 100 | - | 77 | 2 | 494 |
| **split, AI 50%** | 1,376 | 43.3 | 13,009 [4,500..19,169] | 3,986 | 5 [0..20] | 9 | 87 | 230 | 72 [28..95] | 19 | 389 |
| **split, AI 55%** | 1,382 | 44.4 | 17,120 [8,449..23,587] | 3,484 | 14 [0..43] | 3 | 83 | 223 | 86 [50..100] | 9 | 341 |
| **split, AI 60%** | 1,387 | 45.5 | 21,248 [14,337..27,836] | 3,037 | 28 [4..54] | 0 | 72 | 214 | 94 [85..100] | 4 | 292 |
| **split, AI 65%** | 1,392 | 46.6 | 25,811 [16,372..33,695] | 2,734 | 48 [13..85] | 0 | 52 | 201 | 98 [89..100] | 2 | 250 |
| **split, AI 70%** | 1,398 | 47.7 | 30,305 [22,085..38,799] | 2,410 | 71 [32..100] | 0 | 29 | 192 | 99 [96..100] | 1 | 216 |

### Split minus NOISE alone, held-out (percentage points, net $)

*seeds better = share of the 40 AI seeds in which the bootstrap PASS is higher AND the bootstrap BUST is lower than NOISE alone.

#### vs NOISE alone full size

| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |
|---|---|---|---|---|---|---|---|---|
| 25K | 50% | -5 | +5 | -17 | +17 | -1,140 | 0% | no |
| 25K | 55% | +1 | -1 | -12 | +12 | +2,678 | 0% | no |
| 25K | 60% | +7 | -7 | -6 | +6 | +6,680 | 8% | no |
| 25K | 65% | +13 | -13 | -1 | +1 | +11,015 | 45% | no |
| 25K | 70% | +19 | -19 | +4 | -4 | +15,357 | 85% | YES |
| 50K | 50% | -12 | +12 | -7 | +7 | -8,867 | 25% | no |
| 50K | 55% | -3 | +3 | +2 | -2 | -4,762 | 60% | no |
| 50K | 60% | +7 | -7 | +11 | -11 | -644 | 95% | YES |
| 50K | 65% | +14 | -14 | +18 | -18 | +3,878 | 100% | YES |
| 50K | 70% | +22 | -22 | +24 | -24 | +8,388 | 100% | YES |
| 100K | 50% | -18 | +12 | -5 | +4 | -9,356 | 32% | no |
| 100K | 55% | -2 | -2 | +7 | -7 | -5,246 | 82% | SAFER, SLOWER |
| 100K | 60% | +16 | -12 | +17 | -16 | -1,118 | 100% | YES |
| 100K | 65% | +31 | -18 | +23 | -22 | +3,445 | 100% | YES |
| 100K | 70% | +43 | -23 | +27 | -26 | +7,940 | 100% | YES |
| 150K | 50% | -51 | -15 | +3 | -12 | -21,318 | 60% | SAFER, SLOWER |
| 150K | 55% | -42 | -21 | +17 | -22 | -17,208 | 95% | SAFER, SLOWER |
| 150K | 60% | -28 | -24 | +25 | -27 | -13,080 | 100% | SAFER, SLOWER |
| 150K | 65% | -7 | -24 | +29 | -29 | -8,517 | 100% | SAFER, SLOWER |
| 150K | 70% | +15 | -24 | +30 | -30 | -4,022 | 100% | YES |

#### vs NOISE alone half size

| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |
|---|---|---|---|---|---|---|---|---|
| 25K | 50% | +1 | -1 | -12 | +12 | +1,779 | 0% | no |
| 25K | 55% | +7 | -7 | -7 | +7 | +5,597 | 12% | no |
| 25K | 60% | +13 | -13 | -1 | +1 | +9,598 | 35% | no |
| 25K | 65% | +19 | -19 | +4 | -4 | +13,934 | 78% | YES |
| 25K | 70% | +25 | -25 | +9 | -9 | +18,276 | 98% | YES |
| 50K | 50% | -2 | +17 | -25 | +25 | +1,473 | 0% | no |
| 50K | 55% | +7 | +9 | -16 | +16 | +5,579 | 5% | no |
| 50K | 60% | +17 | -1 | -7 | +7 | +9,696 | 15% | no |
| 50K | 65% | +24 | -9 | +1 | -1 | +14,219 | 58% | no |
| 50K | 70% | +32 | -17 | +7 | -7 | +18,728 | 92% | YES |
| 100K | 50% | +30 | +35 | -22 | +26 | +1,400 | 0% | no |
| 100K | 55% | +47 | +22 | -10 | +14 | +5,511 | 5% | no |
| 100K | 60% | +64 | +12 | -1 | +5 | +9,639 | 22% | no |
| 100K | 65% | +79 | +6 | +5 | -1 | +14,202 | 55% | no |
| 100K | 70% | +91 | +1 | +9 | -5 | +18,696 | 92% | no |
| 150K | 50% | +5 | +9 | -5 | +16 | +1,400 | 0% | no |
| 150K | 55% | +14 | +3 | +9 | +7 | +5,511 | 10% | no |
| 150K | 60% | +28 | +0 | +17 | +2 | +9,639 | 40% | no |
| 150K | 65% | +48 | +0 | +21 | -1 | +14,202 | 80% | YES |
| 150K | 70% | +71 | +0 | +22 | -2 | +18,696 | 100% | YES |

## In-sample (2019-2023) tables, main scenario

**Pro 25K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 718 | 46.2 | 11,649 | 1,308 | 54 | 31 | 15 | 84 | 71 | 29 | 83 |
| NOISE alone, half size (diagnostic) | 635 | 44.6 | 7,394 | 1,152 | 47 | 32 | 21 | 117 | 57 | 43 | 84 |
| **split, AI 50%** | 2,159 | 39.2 | 5,016 [-1,847..11,957] | 3,288 | 23 [8..45] | 77 | 0 | 38 | 34 [22..47] | 66 | 44 |
| **split, AI 55%** | 2,174 | 40.3 | 9,145 [3,507..16,032] | 2,735 | 32 [14..61] | 68 | 0 | 40 | 42 [29..53] | 58 | 43 |
| **split, AI 60%** | 2,188 | 41.5 | 13,546 [6,140..20,104] | 2,321 | 43 [20..75] | 57 | 0 | 43 | 50 [34..59] | 50 | 43 |
| **split, AI 65%** | 2,199 | 42.6 | 17,629 [9,840..23,073] | 2,049 | 52 [31..80] | 48 | 0 | 42 | 58 [43..68] | 42 | 42 |
| **split, AI 70%** | 2,212 | 43.8 | 22,077 [15,055..26,512] | 1,829 | 62 [37..91] | 38 | 0 | 42 | 66 [54..73] | 34 | 40 |

**Pro 50K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 718 | 46.2 | 21,489 | 2,616 | 52 | 11 | 37 | 112 | 77 | 23 | 118 |
| NOISE alone, half size (diagnostic) | 721 | 46.2 | 11,669 | 1,308 | 45 | 0 | 55 | 164 | 92 | 7 | 272 |
| **split, AI 50%** | 2,257 | 39.8 | 8,231 [1,195..15,052] | 3,108 | 36 [6..64] | 31 | 33 | 139 | 53 [26..78] | 47 | 192 |
| **split, AI 55%** | 2,268 | 40.9 | 12,534 [6,958..19,265] | 2,579 | 52 [28..82] | 21 | 28 | 145 | 67 [45..86] | 33 | 175 |
| **split, AI 60%** | 2,278 | 42.1 | 17,028 [10,026..23,227] | 2,148 | 63 [29..90] | 13 | 24 | 135 | 79 [58..92] | 21 | 157 |
| **split, AI 65%** | 2,288 | 43.2 | 21,294 [13,191..26,466] | 1,848 | 74 [34..99] | 6 | 21 | 125 | 87 [73..94] | 13 | 141 |
| **split, AI 70%** | 2,298 | 44.3 | 25,885 [18,969..30,443] | 1,681 | 82 [62..100] | 3 | 15 | 118 | 93 [84..97] | 7 | 125 |

**Pro 100K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 722 | 46.3 | 24,219 | 2,616 | 46 | 0 | 54 | 164 | 86 | 12 | 260 |
| NOISE alone, half size (diagnostic) | 722 | 46.3 | 12,110 | 1,308 | 6 | 0 | 94 | 240 | 75 | 0 | 510 |
| **split, AI 50%** | 2,259 | 39.8 | 8,565 [1,397..15,493] | 3,160 | 8 [0..29] | 8 | 84 | 201 | 50 [14..86] | 30 | 458 |
| **split, AI 55%** | 2,270 | 41.0 | 12,903 [6,916..19,706] | 2,627 | 18 [0..39] | 4 | 78 | 198 | 71 [37..92] | 15 | 417 |
| **split, AI 60%** | 2,280 | 42.1 | 17,424 [10,278..23,667] | 2,188 | 29 [3..57] | 1 | 70 | 192 | 87 [61..97] | 7 | 364 |
| **split, AI 65%** | 2,289 | 43.2 | 21,734 [13,631..26,907] | 1,848 | 40 [11..71] | 1 | 59 | 188 | 95 [79..99] | 3 | 312 |
| **split, AI 70%** | 2,299 | 44.4 | 26,322 [19,409..30,884] | 1,679 | 52 [14..76] | 0 | 47 | 179 | 98 [94..100] | 1 | 265 |

**Pro 150K**

| setup | trades | win % | net $ | max DD $ | roll PASS % | roll BUST % | roll OPEN % | roll med days | boot PASS % | boot BUST % | boot med days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone, full size | 722 | 46.3 | 35,325 | 3,924 | 46 | 0 | 54 | 164 | 88 | 10 | 264 |
| NOISE alone, half size (diagnostic) | 722 | 46.3 | 12,110 | 1,308 | 0 | 0 | 100 | - | 36 | 0 | 627 |
| **split, AI 50%** | 2,261 | 39.8 | 8,523 [1,241..15,493] | 3,213 | 0 [0..2] | 1 | 99 | 242 | 25 [3..64] | 10 | 580 |
| **split, AI 55%** | 2,271 | 41.0 | 12,897 [6,666..19,706] | 2,645 | 1 [0..16] | 0 | 99 | 233 | 47 [14..81] | 3 | 561 |
| **split, AI 60%** | 2,280 | 42.1 | 17,416 [10,278..23,667] | 2,196 | 5 [0..23] | 0 | 95 | 230 | 71 [31..93] | 1 | 514 |
| **split, AI 65%** | 2,289 | 43.2 | 21,734 [13,631..26,907] | 1,848 | 11 [0..26] | 0 | 89 | 222 | 88 [50..98] | 0 | 460 |
| **split, AI 70%** | 2,299 | 44.4 | 26,322 [19,409..30,884] | 1,679 | 20 [0..37] | 0 | 80 | 212 | 97 [86..100] | 0 | 401 |

#### In-sample delta vs NOISE alone full size

| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |
|---|---|---|---|---|---|---|---|---|
| 25K | 50% | -31 | +45 | -37 | +37 | -6,633 | 0% | no |
| 25K | 55% | -22 | +37 | -29 | +29 | -2,504 | 0% | no |
| 25K | 60% | -11 | +26 | -21 | +21 | +1,897 | 0% | no |
| 25K | 65% | -3 | +17 | -13 | +13 | +5,980 | 0% | no |
| 25K | 70% | +8 | +7 | -5 | +5 | +10,428 | 15% | no |
| 50K | 50% | -16 | +20 | -24 | +24 | -13,258 | 2% | no |
| 50K | 55% | -1 | +10 | -9 | +10 | -8,955 | 8% | no |
| 50K | 60% | +11 | +2 | +3 | -2 | -4,461 | 70% | no |
| 50K | 65% | +22 | -6 | +11 | -10 | -195 | 95% | YES |
| 50K | 70% | +30 | -8 | +16 | -16 | +4,396 | 100% | YES |
| 100K | 50% | -37 | +8 | -37 | +18 | -15,654 | 2% | no |
| 100K | 55% | -28 | +4 | -15 | +3 | -11,316 | 8% | no |
| 100K | 60% | -17 | +1 | +1 | -5 | -6,795 | 68% | no |
| 100K | 65% | -5 | +1 | +9 | -9 | -2,485 | 95% | SAFER, SLOWER |
| 100K | 70% | +7 | +0 | +12 | -11 | +2,103 | 100% | YES |
| 150K | 50% | -45 | +1 | -64 | +0 | -26,802 | 0% | no |
| 150K | 55% | -44 | +0 | -41 | -7 | -22,428 | 0% | SAFER, SLOWER |
| 150K | 60% | -41 | +0 | -17 | -9 | -17,909 | 12% | SAFER, SLOWER |
| 150K | 65% | -35 | +0 | -1 | -10 | -13,591 | 60% | SAFER, SLOWER |
| 150K | 70% | -26 | +0 | +8 | -10 | -9,003 | 92% | SAFER, SLOWER |

## Sensitivities (held-out, delta vs NOISE alone full size)


#### Duo on MNQ only (hedge lock vs NOISE is then the only interaction)

| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |
|---|---|---|---|---|---|---|---|---|
| 25K | 50% | -1 | +1 | -11 | +11 | -20 | 2% | no |
| 25K | 55% | +3 | -3 | -7 | +7 | +2,545 | 10% | no |
| 25K | 60% | +6 | -6 | -3 | +3 | +4,736 | 28% | no |
| 25K | 65% | +12 | -12 | +0 | -0 | +7,437 | 58% | no |
| 25K | 70% | +15 | -15 | +4 | -4 | +10,376 | 80% | YES |
| 50K | 50% | -5 | +5 | +2 | -2 | -7,883 | 62% | no |
| 50K | 55% | +3 | -3 | +8 | -8 | -5,246 | 80% | YES |
| 50K | 60% | +8 | -8 | +13 | -13 | -2,947 | 95% | YES |
| 50K | 65% | +14 | -13 | +19 | -19 | -164 | 100% | YES |
| 50K | 70% | +21 | -20 | +23 | -23 | +2,714 | 100% | YES |
| 100K | 50% | -15 | -7 | +6 | -7 | -8,329 | 75% | SAFER, SLOWER |
| 100K | 55% | -3 | -14 | +14 | -14 | -5,682 | 95% | SAFER, SLOWER |
| 100K | 60% | +7 | -18 | +18 | -18 | -3,367 | 100% | YES |
| 100K | 65% | +19 | -21 | +22 | -22 | -585 | 100% | YES |
| 100K | 70% | +29 | -22 | +25 | -25 | +2,302 | 100% | YES |
| 150K | 50% | -49 | -23 | +10 | -21 | -20,291 | 82% | SAFER, SLOWER |
| 150K | 55% | -43 | -24 | +19 | -25 | -17,644 | 95% | SAFER, SLOWER |
| 150K | 60% | -35 | -24 | +24 | -28 | -15,329 | 100% | SAFER, SLOWER |
| 150K | 65% | -24 | -24 | +28 | -29 | -12,547 | 100% | SAFER, SLOWER |
| 150K | 70% | -12 | -24 | +29 | -30 | -9,660 | 100% | SAFER, SLOWER |

Verdict matrix, held-out:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | **Y** |
| Pro 50K | - | **Y** | **Y** | **Y** | **Y** |
| Pro 100K | s | s | **Y** | **Y** | **Y** |
| Pro 150K | s | s | s | s | s |

In-sample:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | - |
| Pro 50K | - | - | **Y** | **Y** | **Y** |
| Pro 100K | - | - | s | s | **Y** |
| Pro 150K | s | s | s | s | s |

#### 'max 1 open position per account' (a Duo or NOISE entry that overlaps any open position is skipped; MNQ + MGC)

| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |
|---|---|---|---|---|---|---|---|---|
| 25K | 50% | -0 | +0 | -14 | +14 | -3,464 | - | no |
| 25K | 55% | +7 | -7 | -10 | +10 | -850 | - | no |
| 25K | 60% | +13 | -13 | -5 | +5 | +1,636 | - | no |
| 25K | 65% | +17 | -17 | +0 | -0 | +4,418 | - | no |
| 25K | 70% | +24 | -24 | +5 | -5 | +7,242 | - | YES |
| 50K | 50% | -7 | +5 | -5 | +5 | -12,108 | - | no |
| 50K | 55% | +5 | -8 | +4 | -4 | -9,193 | - | YES |
| 50K | 60% | +12 | -13 | +11 | -11 | -6,693 | - | YES |
| 50K | 65% | +19 | -19 | +18 | -18 | -3,874 | - | YES |
| 50K | 70% | +24 | -24 | +24 | -24 | -952 | - | YES |
| 100K | 50% | -29 | +0 | -6 | +4 | -12,495 | - | no |
| 100K | 55% | -16 | -10 | +6 | -7 | -9,605 | - | SAFER, SLOWER |
| 100K | 60% | -2 | -16 | +15 | -15 | -7,094 | - | SAFER, SLOWER |
| 100K | 65% | +13 | -19 | +21 | -21 | -4,271 | - | YES |
| 100K | 70% | +30 | -23 | +25 | -25 | -1,353 | - | YES |
| 150K | 50% | -54 | -19 | -10 | -12 | -24,462 | - | SAFER, SLOWER |
| 150K | 55% | -51 | -22 | +5 | -21 | -21,565 | - | SAFER, SLOWER |
| 150K | 60% | -47 | -23 | +16 | -26 | -19,056 | - | SAFER, SLOWER |
| 150K | 65% | -36 | -24 | +24 | -28 | -16,233 | - | SAFER, SLOWER |
| 150K | 70% | -23 | -24 | +28 | -30 | -13,315 | - | SAFER, SLOWER |

Verdict matrix, held-out:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | **Y** |
| Pro 50K | - | **Y** | **Y** | **Y** | **Y** |
| Pro 100K | - | s | s | **Y** | **Y** |
| Pro 150K | s | s | s | s | s |

In-sample:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | - |
| Pro 50K | - | - | s | **Y** | **Y** |
| Pro 100K | - | - | - | s | s |
| Pro 150K | s | s | s | s | s |

#### NOISE alone at the session-15 recommended sizes instead of the app default (25K 1, 50K 1, 100K 2 / 1, 150K 3 / 1 micros)

| account | AI acc | roll PASS d | roll BUST d | boot PASS d | boot BUST d | net $ d | seeds better* | beats? |
|---|---|---|---|---|---|---|---|---|
| 25K | 50% | -5 | +5 | -17 | +17 | -1,140 | - | no |
| 25K | 55% | +1 | -1 | -12 | +12 | +2,678 | - | no |
| 25K | 60% | +7 | -7 | -6 | +6 | +6,680 | - | no |
| 25K | 65% | +13 | -13 | -1 | +1 | +11,015 | - | no |
| 25K | 70% | +19 | -19 | +4 | -4 | +15,357 | - | YES |
| 50K | 50% | -2 | +17 | -24 | +24 | +1,723 | - | no |
| 50K | 55% | +7 | +9 | -15 | +15 | +5,828 | - | no |
| 50K | 60% | +17 | -1 | -6 | +6 | +9,946 | - | no |
| 50K | 65% | +24 | -9 | +1 | -1 | +14,468 | - | YES |
| 50K | 70% | +32 | -17 | +7 | -7 | +18,978 | - | YES |
| 100K | 50% | -6 | +35 | -15 | +16 | -8,824 | - | no |
| 100K | 55% | +11 | +22 | -3 | +4 | -4,714 | - | no |
| 100K | 60% | +28 | +12 | +6 | -5 | -586 | - | no |
| 100K | 65% | +43 | +6 | +12 | -11 | +3,977 | - | no |
| 100K | 70% | +55 | +1 | +16 | -15 | +8,472 | - | no |
| 150K | 50% | -33 | +9 | -7 | +0 | -16,964 | - | no |
| 150K | 55% | -23 | +3 | +7 | -9 | -12,853 | - | no |
| 150K | 60% | -9 | +0 | +15 | -14 | -8,725 | - | SAFER, SLOWER |
| 150K | 65% | +11 | +0 | +19 | -17 | -4,162 | - | YES |
| 150K | 70% | +34 | +0 | +20 | -18 | +332 | - | YES |

Verdict matrix, held-out:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | **Y** |
| Pro 50K | - | - | - | **Y** | **Y** |
| Pro 100K | - | - | - | - | - |
| Pro 150K | - | - | s | **Y** | **Y** |

In-sample:

| account | AI 50% | AI 55% | AI 60% | AI 65% | AI 70% |
|---|---|---|---|---|---|
| Pro 25K | - | - | - | - | - |
| Pro 50K | - | - | - | - | - |
| Pro 100K | - | - | - | **Y** | **Y** |
| Pro 150K | - | - | - | s | s |

## Method, assumptions and doubts

**Data.** Databento GLBX.MDP3 1-minute bars, `MNQ.v.0` and `MGC.v.0` (volume roll, never `.c.0`), 2019-04/05 to 2026-11. RTH 09:30-16:00 ET day arrays (MNQ 1,867 usable days from 2019-05-06; MGC 1,920 days; 71 MNQ / 45 MGC days skipped as short/thin days, and for MGC also any day with a 1-minute jump over 2% (roll/bad print); no jump filter on MNQ). The MNQ yearly CSVs came from the shared scratchpad cache (another helper downloaded them); I verified them by reproducing the session-15 NOISE trade stream exactly (778 trades 2021-11..2026-10, identical P&L, HO 424 trades 52.1% win $10,259). MGC was downloaded here; its Duo candidates reproduce session 16 (MGC 70% HO +$6,007 PF 1.30 vs +$6,000 PF 1.30). Raw data is NOT in git (scratchpad only). `noise_mnq_stream.csv` here is the 1,149-row NOISE trade list.

**Strategies (per 1 micro, costs as sessions 10-16: MNQ $1.00 / MGC $1.50 round trip, 1 tick slippage on every market entry/exit and stop fill, limit targets need a 1-tick trade-through).**
- NOISE: 14-day noise band, hourly checks 10:00-15:00, band/VWAP trail exits, flat 16:00, $250 emergency stop, max 3 entries a day, **profit lock +100 pt -> entry +10 pt** (preset C / D75-P1, the held-out-proven form), MNQ only. Same code path as session 15/17 `sharpen.gen`.
- AI Duo: the session-16 `ai_duo_window.py` model, window 09:36-11:30 (D86), first 5-minute VWAP pullback close in the AI direction, stop beyond the pullback swing (a setup whose stop exceeds the $250 NOISE-stop distance is skipped), 2.0R target, flat 11:30, one trade per market per day, MNQ and MGC (the real button runs both). **Differences from the built app (my simplification, same as session 16):** no D85 trade management (BE at +1R, trail, lock), skip instead of cap for a too-wide stop, no news flatten, stop widened to >= $10.
- AI side: simulated. The call equals the day's true RTH open-to-close direction with probability = accuracy (50/55/60/65/70%), 27% of market-days NEUTRAL (no trade; user brief). 40 seeds; the same random numbers are reused across accuracies (common random numbers). Spread = min..max over the 40 seeds.

**Account engine (one account runs both halves; Lucid Pro numbers read from `config/rules/lucid_pro_{25,50,100,150}k.yaml`, none invented).** Eval: target 1,250 / 3,000 / 6,000 / 9,000, EOD trailing loss limit 1,000 / 2,000 / 3,000 / 4,500 locking at start+100 once the peak reaches the lock trigger, no consistency rule, 1 profitable day, firm DLL per plan file (25K none), intraday breach of the floor = bust (checked on each trade's worst adverse excursion, conservatively adding the worst excursion of every other open position). Funded stage is not simulated.
- **Full size (NOISE alone) = the app default `size_table`**: 25K 1 micro; 50K 2 (1 below 50% cushion); 100K 2 (1 below 30%); 150K 3 (2 below 50%).
- **Split:** each strategy at half of the current full size, rounded down, min 1 micro (so 1+1 on every account here, including 25K where it doubles exposure; the 'NOISE alone, half size' diagnostic row at 25K is therefore still 1 micro, only the budget is halved), each with **half of the daily loss budget**. ASSUMPTION: the daily loss budget = the plan's funded DLL (600 / 1,200 / 1,800 / 2,700) in every stage; NOISE alone gets the whole budget. A new entry is sized down / skipped if (that strategy's realised loss today + the trade's stop risk + $40 safety margin) would exceed its budget.
- **Hedge lock:** opposite directions may not be open at the same time in the same equity-index group (MNQ NOISE vs MNQ Duo); the later arrival is skipped (tie: NOISE wins); MGC is a different group. Skipped NOISE trades are not re-simulated (their state machine is not re-run), a small approximation (hedge lock removed about 1% of NOISE trades). The "strict" sensitivity applies "max 1 open position per account" (any overlap skipped; removes about 12-14% of NOISE trades).
- Day stops, hold rule, consistency and news rules of the live risk engine are not modelled beyond the above; the Pro eval has no consistency rule.

**Doubts to keep in mind.**
1. The AI is an iid coin with a given bias, independent of regime and of NOISE. A real TradingAgents + Vibe-Trading call is correlated with trend days and news, and nobody has measured 60%+; the table is a what-if.
2. Held-out is 2.8 years of one mostly rising market; ~247 overlapping rolling starts are 2-3 real episodes; the bootstrap breaks dependence beyond 10 sessions.
3. The Duo model ignores the D85 trade management and the 08:30 news flatten; the built app's Duo could do better or worse. MGC "AI truth" is the RTH open-to-close sign (a loose proxy for gold).
4. Which strategy counts as "NOISE alone at full size" changes the answer (app default vs session-15 sizes, matrices above). The split is the same 1+1 micro engine on every account from 50K up.
5. The daily loss budget = funded DLL is my assumption; the Pro eval DLL is none/soft. A smaller budget would starve the Duo half on 25K.
6. The combined intraday MLL check is conservative (sums worst excursions of simultaneous positions); real correlation is below 1, so split busts are somewhat overstated.
7. AI Duo is paper-only (D83); a real NOISE + paper Duo split on one account is not possible today, so this is a research question about the combined idea only.
8. Pick/judge: no parameter was tuned; "picked on in-sample" here means reading the in-sample verdict matrix first and then confirming on 2024-2026.

**Files.** `data.py` (loader), `sim.py` (NOISE stream, Duo candidates, account engine), `build_streams.py`, `run.py` (all scenarios, 40 seeds), `make_tables.py`, `make_results.py`, `text_blocks.py`, `results_*.json` (aggregates incl. per-seed values for main/mnq), `tables_*.md` (all generated tables incl. IS), `noise_mnq_stream.csv`. Re-run: build the day caches with `data.py`, then `python3 build_streams.py <cache>` and `python3 run.py <cache> 40`.
