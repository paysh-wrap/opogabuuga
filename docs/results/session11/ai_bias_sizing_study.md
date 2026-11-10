# AI bias for SIZING only - accuracy study (session 11)

Script: `ai_bias_sizing_study.py` (engine = `pm_fade_d57_study.py`: NOISE + PM fade, D57 live rule, kill distance $50, D66 eval size tables, D68 payout cadence; 1-min MNQ 2021-11 .. 2026-10).
Daily call = coin with accuracy a vs the real RTH direction (open->close); agree +1 micro, disagree -1 (min 1), neutral not modelled (no neutral days; the call is always up/down). Never blocks a trade.
Plans: Pro 25K / 50K / 100K / 150K with the study's live sizing. Windows start every 10 trading days (overlapping); eval horizon 120 days (25K/50K) or 250 (100K/150K); funded = 260 days, income = paid-to-trader / 26 two-week periods.

**Seeds: 70 per (mode, accuracy) cell, not 200** - the run process was killed at job 700/2001 (the partial JSON in `out/ai_bias_sizing.json` is intact). Re-run `ai_bias_sizing_study.py run 200` for the full count; seed-to-seed noise is small relative to the gaps below, but treat differences < ~3 $ / 1 pp as noise.

Two cap interpretations:
- **A** = "never above the day's size-table size": agree can only restore a braked/tapered size, so it is effectively "-1 on disagree" (25K x1 is unchanged).
- **B** = agree may go 1 above the table (cap = base size + 1; DLL, D57 stop-tightening and worst-case checks still apply).

Cell format: EVAL pass % / EVAL bust % / FUNDED yr-1 bust % / income $ per 2 weeks. Bust is 0.0 in every cell, baseline included (D57 + kill $50 prevent it) - so bust/safety does NOT change; only pass rate and income do.

### ALL 2021-2026
per cell: EVAL pass% / EVAL bust% / FUNDED yr-1 bust% / mean income per 2 weeks $ (paid to trader)

| plan | baseline | 52% B | 55% B | 60% B | 65% B | 70% B | 52% A | 55% A | 60% A | 65% A | 70% A |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | 54.6 / 0.0 / 0.0 / 56 | 37.3 / 0.0 / 0.0 / 26 | 37.8 / 0.0 / 0.0 / 27 | 38.6 / 0.0 / 0.0 / 31 | 39.7 / 0.0 / 0.0 / 33 | 40.8 / 0.0 / 0.0 / 37 | 54.6 / 0.0 / 0.0 / 56 | 54.6 / 0.0 / 0.0 / 56 | 54.6 / 0.0 / 0.0 / 56 | 54.6 / 0.0 / 0.0 / 56 | 54.6 / 0.0 / 0.0 / 56 |
| 50K | 50.4 / 0.0 / 0.0 / 91 | 46.7 / 0.0 / 0.0 / 75 | 47.3 / 0.0 / 0.0 / 80 | 49.5 / 0.0 / 0.0 / 92 | 50.9 / 0.0 / 0.0 / 103 | 52.7 / 0.0 / 0.0 / 114 | 49.9 / 0.0 / 0.0 / 89 | 50.7 / 0.0 / 0.0 / 94 | 53.7 / 0.0 / 0.0 / 103 | 55.6 / 0.0 / 0.0 / 113 | 57.8 / 0.0 / 0.0 / 123 |
| 100K | 58.5 / 0.0 / 0.0 / 126 | 57.0 / 0.0 / 0.0 / 116 | 59.0 / 0.0 / 0.0 / 127 | 62.3 / 0.0 / 0.0 / 146 | 64.8 / 0.0 / 0.0 / 164 | 67.7 / 0.0 / 0.0 / 184 | 62.1 / 0.0 / 0.0 / 97 | 63.8 / 0.0 / 0.0 / 103 | 66.8 / 0.0 / 0.0 / 116 | 68.7 / 0.0 / 0.0 / 128 | 70.8 / 0.0 / 0.0 / 140 |
| 150K | 51.9 / 0.0 / 0.0 / 183 | 57.7 / 0.0 / 0.0 / 167 | 59.6 / 0.0 / 0.0 / 179 | 62.3 / 0.0 / 0.0 / 196 | 64.9 / 0.0 / 0.0 / 214 | 67.6 / 0.0 / 0.0 / 229 | 60.0 / 0.0 / 0.0 / 152 | 61.6 / 0.0 / 0.0 / 158 | 64.8 / 0.0 / 0.0 / 170 | 66.3 / 0.0 / 0.0 / 180 | 68.0 / 0.0 / 0.0 / 190 |

### 2021-2023 starts
per cell: EVAL pass% / EVAL bust% / FUNDED yr-1 bust% / mean income per 2 weeks $ (paid to trader)

| plan | baseline | 52% B | 55% B | 60% B | 65% B | 70% B | 52% A | 55% A | 60% A | 65% A | 70% A |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | 63.2 / 0.0 / 0.0 / 64 | 36.6 / 0.0 / 0.0 / 32 | 37.8 / 0.0 / 0.0 / 34 | 39.2 / 0.0 / 0.0 / 39 | 41.5 / 0.0 / 0.0 / 44 | 43.2 / 0.0 / 0.0 / 48 | 63.2 / 0.0 / 0.0 / 64 | 63.2 / 0.0 / 0.0 / 64 | 63.2 / 0.0 / 0.0 / 64 | 63.2 / 0.0 / 0.0 / 64 | 63.2 / 0.0 / 0.0 / 64 |
| 50K | 52.6 / 0.0 / 0.0 / 111 | 49.3 / 0.0 / 0.0 / 85 | 50.7 / 0.0 / 0.0 / 94 | 53.8 / 0.0 / 0.0 / 111 | 56.1 / 0.0 / 0.0 / 128 | 58.7 / 0.0 / 0.0 / 146 | 50.1 / 0.0 / 0.0 / 99 | 51.5 / 0.0 / 0.0 / 106 | 55.6 / 0.0 / 0.0 / 120 | 58.9 / 0.0 / 0.0 / 134 | 61.7 / 0.0 / 0.0 / 148 |
| 100K | 61.4 / 0.0 / 0.0 / 139 | 62.3 / 0.0 / 0.0 / 131 | 65.0 / 0.0 / 0.0 / 146 | 69.8 / 0.0 / 0.0 / 174 | 73.6 / 0.0 / 0.0 / 201 | 77.6 / 0.0 / 0.0 / 230 | 70.7 / 0.0 / 0.0 / 106 | 73.0 / 0.0 / 0.0 / 115 | 77.6 / 0.0 / 0.0 / 134 | 80.8 / 0.0 / 0.0 / 150 | 83.8 / 0.0 / 0.0 / 167 |
| 150K | 54.4 / 0.0 / 0.0 / 216 | 63.2 / 0.0 / 0.0 / 189 | 65.9 / 0.0 / 0.0 / 206 | 69.0 / 0.0 / 0.0 / 232 | 73.6 / 0.0 / 0.0 / 259 | 77.6 / 0.0 / 0.0 / 283 | 66.8 / 0.0 / 0.0 / 169 | 69.5 / 0.0 / 0.0 / 179 | 74.7 / 0.0 / 0.0 / 196 | 77.3 / 0.0 / 0.0 / 211 | 79.8 / 0.0 / 0.0 / 227 |

### 2024-2026 starts
per cell: EVAL pass% / EVAL bust% / FUNDED yr-1 bust% / mean income per 2 weeks $ (paid to trader)

| plan | baseline | 52% B | 55% B | 60% B | 65% B | 70% B | 52% A | 55% A | 60% A | 65% A | 70% A |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | 46.8 / 0.0 / 0.0 / 46 | 37.9 / 0.0 / 0.0 / 18 | 37.8 / 0.0 / 0.0 / 19 | 38.0 / 0.0 / 0.0 / 20 | 37.9 / 0.0 / 0.0 / 21 | 38.5 / 0.0 / 0.0 / 23 | 46.8 / 0.0 / 0.0 / 46 | 46.8 / 0.0 / 0.0 / 46 | 46.8 / 0.0 / 0.0 / 46 | 46.8 / 0.0 / 0.0 / 46 | 46.8 / 0.0 / 0.0 / 46 |
| 50K | 48.4 / 0.0 / 0.0 / 67 | 44.3 / 0.0 / 0.0 / 63 | 44.3 / 0.0 / 0.0 / 63 | 45.5 / 0.0 / 0.0 / 69 | 46.1 / 0.0 / 0.0 / 73 | 47.3 / 0.0 / 0.0 / 76 | 49.6 / 0.0 / 0.0 / 78 | 50.0 / 0.0 / 0.0 / 79 | 51.9 / 0.0 / 0.0 / 84 | 52.6 / 0.0 / 0.0 / 89 | 54.3 / 0.0 / 0.0 / 93 |
| 100K | 55.1 / 0.0 / 0.0 / 109 | 51.0 / 0.0 / 0.0 / 99 | 52.0 / 0.0 / 0.0 / 104 | 53.6 / 0.0 / 0.0 / 112 | 54.6 / 0.0 / 0.0 / 119 | 56.1 / 0.0 / 0.0 / 130 | 52.2 / 0.0 / 0.0 / 86 | 53.1 / 0.0 / 0.0 / 89 | 54.4 / 0.0 / 0.0 / 95 | 54.7 / 0.0 / 0.0 / 101 | 55.6 / 0.0 / 0.0 / 108 |
| 150K | 49.0 / 0.0 / 0.0 / 143 | 51.3 / 0.0 / 0.0 / 142 | 52.2 / 0.0 / 0.0 / 147 | 54.5 / 0.0 / 0.0 / 153 | 54.9 / 0.0 / 0.0 / 159 | 56.0 / 0.0 / 0.0 / 165 | 52.1 / 0.0 / 0.0 / 132 | 52.4 / 0.0 / 0.0 / 133 | 53.3 / 0.0 / 0.0 / 138 | 53.6 / 0.0 / 0.0 / 144 | 54.2 / 0.0 / 0.0 / 147 |

### Delta vs baseline (mode B, ALL): income $/2wk, funded bust pp, eval bust pp

| plan | 52% | 55% | 60% | 65% | 70% |
|---|---|---|---|---|---|
| 25K | -30 / +0.0 / +0.0 | -29 / +0.0 / +0.0 | -25 / +0.0 / +0.0 | -22 / +0.0 / +0.0 | -19 / +0.0 / +0.0 |
| 50K | -15 / +0.0 / +0.0 | -11 / +0.0 / +0.0 | +1 / +0.0 / +0.0 | +12 / +0.0 / +0.0 | +23 / +0.0 / +0.0 |
| 100K | -9 / +0.0 / +0.0 | +1 / +0.0 / +0.0 | +20 / +0.0 / +0.0 | +38 / +0.0 / +0.0 | +59 / +0.0 / +0.0 |
| 150K | -15 / +0.0 / +0.0 | -4 / +0.0 / +0.0 | +14 / +0.0 / +0.0 | +31 / +0.0 / +0.0 | +46 / +0.0 / +0.0 |

seeds per cell: 70
## Break-even accuracy (income per 2 weeks vs baseline, all years)
| plan | B (+1 above table) | A (cap at table) |
|---|---|---|
| 25K | never (even 70% is -19 $) | n/a (identical to baseline) |
| 50K | ~60% | ~53% |
| 100K | ~55% | ~66% |
| 150K | ~57% | ~68% |

Eval pass rate: A raises pass % even at 52% (100K 58.5 -> 62.1, 150K 51.9 -> 60.0) because it simply trades smaller about half the time (a size cut, not information), and it costs income at low accuracy. B on 100K/150K passes more at >=55%.

## Era split
2021-2023 gains are 2-3x bigger than 2024-2026 (100K B at 70%: +91 $ vs +21 $; 25K B loses in both). In 2024-2026 B only beats baseline income from ~60% (50K/100K) / ~52-55% (150K) and A stays below baseline income on 100K/150K up to 70%.

## Verdict
Not worth wiring below ~60% accuracy; a 52-55% AI call is worth nothing (B costs income on 25K/50K, A just shrinks size). It helps only at >=60-65% and only on 100K/150K (B at 65%: +38 / +31 $ per 2 weeks, pass +6 / +13 pp), consistent with D72's >=70% proof bar before the ledger gates anything. Never use it on 25K. Bust risk is unaffected either way. Recommendation: keep advisory until the ledger shows Wilson-lower >= 60%; then consider B on 100K/150K only.
