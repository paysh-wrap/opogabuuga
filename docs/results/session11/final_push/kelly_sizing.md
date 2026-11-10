# Kelly / cushion sizing + profit-lock validation (session 11 final push)

Engine: `kelly_engine.py` = `../pm_fade_d57_study.py` (live rules: D57 shrink 0.6 for NOISE, PM fade as coded, kill $50, soft DLL, D68 cadence,
live size tables) + two knobs (intraday profit lock, cushion sizing). Run: `kelly_run.py` (212 configs -> `kelly_results.json`), tables: `kelly_tables.py`.
Rolling starts every 2 sessions; EVAL window 120 sessions (25K, 50K) / 250 (100K, 150K); FUNDED 260 sessions; halves split by START date (<= 2023-12-31 vs later).

**Checks.** (1) Lock replayed intraday with no account rule at 1 micro reproduces `streams/noise_lock100_plus10_no_reentry.csv` exactly
(1,271 trades, 53.2% win, mean $20.51, sd $187.7, 0 of 1,111 days differ). So NO day-level approximation: D57 stop-tightening, kill and DLL act inside the day on the locked trade.
(2) With both knobs off the engine equals `pm_fade_d57_study.evaluate_funded` (50K: $2,534 yr-1, same as `out/tables.md`).

**Definition that matters.** In this engine an account almost never touches the MLL: the $50 kill switch stops it first and it then sits frozen forever.
"dead %" below = hard bust OR frozen (hard bust is 0% everywhere). Live-table dead %: 25K 70 / 50K 58 / 100K 38 / 150K 31 (identical to the `frozen` column
of `out/tables.md`). The brief quoted 57 / 44 / 27.5 / 24.5 - same ranking, different source; I could not reproduce those exact figures with this engine.

**Kelly arithmetic.** Per micro: baseline mean $19.63, sd $213.7 -> Kelly 0.43 micro per $1,000 cushion; lock stream mean $20.51, sd $187.7 -> 0.58.

| plan | start cushion (MLL) | live size | Kelly size base | Kelly size lock | live / Kelly (lock) |
|---|---|---|---|---|---|
| 25K | $1,000 | 1 | 0.43 | 0.58 | 1.7x |
| 50K | $2,000 | 2 | 0.86 | 1.16 | 1.7x |
| 100K | $3,000 | 2 | 1.29 | 1.74 | 1.1x |
| 150K | $4,500 | 3 | 1.94 | 2.61 | 1.1x |

**Noise warning.** Dead % comes in lumps (0% vs 55% between neighbouring rules, e.g. 100K lock k=1.3 cap 2 -> 6% but cap 3 -> 56% on 2024-26): one or two
drawdown episodes decide a whole half because the rolling starts overlap. Treat single-cell differences well beyond the 3 pt / $10 rule with suspicion;
only patterns that hold on both halves AND both streams are trusted below.

## Verdicts

**A. Lock: PASSES on funded, neutral on eval.** Funded dead % is lower or equal on every plan and both halves (25K 66->63 / 74->59, 50K 53->53 / 64->60,
100K 17->7 / 63->36, 150K 15->14 / 50->6) and mean income is equal or higher everywhere (worst cell -$2). Survivor income is sometimes lower only because
more accounts survive. Eval: pass % within +-3 pts overall (50K: -5 pts on 2021-23, +7 on 2024-26), median sessions equal or shorter.

**B. Cushion sizing: does NOT beat the live tables under the stated pass rule.**
- The hypothesis is right about risk: at k <= 0.8 dead % falls to ~0% in almost every cell. But income falls faster than size, because payout rules
  (buffer, minimum cycle profit, minimum request) starve a small-size account: 150K at k=0.6 pays $91-135 vs $220-238 live; 100K at k=0.6 pays $54-102 vs $119-168.
  Mean income already counts the dead accounts' payouts, and the live tables still win on it.
- Mechanical passes are not robust across streams: 100K k=1.3 cap 4 passes on the baseline stream (dead 12% / 52% vs 17% / 63%, income $161 / $126 vs $160 / $119)
  but is clearly worse on the lock stream (21% / 57% vs 7% / 36%). 50K k=1.0 cap 3 passes on the lock stream (dead 3% / 27% vs 53% / 60%, income $101 / $114 vs $110 / $102)
  but loses income on the baseline stream ($95 / $75 vs $112 / $80, dead 13% / 65% vs 53% / 64%).
- Honest reading: no (k, cap) gives higher income with no more deaths on both halves and both streams. What cushion sizing does offer is a different trade:
  ~$10-25 less mean income per 2 weeks for far fewer dead accounts and a higher median, most clearly WITH the lock stream:
  50K k=0.8 cap 2: dead 0% / 0%, $89 / $106, median $97 / $106 (live: 53% / 60%, $110 / $102, median $60 / $36);
  100K k=1.0 cap 2: dead 0% / 4%, $149 / $132 (live 7% / 36%, $168 / $154); 150K k=1.0 cap 4: dead 0% / 2%, $221 / $202 (live 14% / 6%, $238 / $225).
  That is a user decision (fewer resets vs a little less mean income), not a measured improvement under the rule. On the baseline stream the 2024-26 half does not confirm it for 50K.
- EVAL: nothing passes. Low k removes frozen evals but pass % inside the window is lower or equal and the median is 20-100+ sessions longer.
  With the lock stream k=1.0 on 100K / 150K gives pass 68-73% / 69-72% vs 65 / 57 and 63 / 55 live but 20-40 sessions slower - slower-but-safer, not better by the rule.

**C. 25K is the worst account for this edge.** Same trades, 1 micro: funded 25K dead 70% (lock 61%), $53 ($56) per 2 wk; funded 50K at a fixed 1 micro dead 25%
(0% on 2021-23, 55% on 2024-26; lock stream 0% / 0%) and $63 ($86) per 2 wk - more income and far fewer deaths. The price is the eval: 50K at 1 micro passes 46-48%
within 120 sessions (median 80-83 sessions, frozen 13% / 0%, the rest still open) vs 25K 56-59% at a median 34-35 sessions with 41-44% frozen. Mean income per dead point
(all starts, baseline / lock): 25K 0.8 / 0.9, 50K live 1.7 / 1.9, 100K live 3.7 / 7.9, 150K live 6.0 / 22.4. Bigger accounts at their live tables give the best income
per unit of bust; the 150K is best. Account fees / reset prices are NOT in these numbers (not known to this study) - weigh them before choosing.

## A. Profit lock (NOISE +100 pts -> stop to +10, no re-entry) vs baseline, live size tables

EVAL: pass / frozen / bust % / median sessions to pass. Lock replayed intraday inside the engine (no day-level approximation).

| plan | stream | all starts | 2021-23 | 2024-26 |
|---|---|---|---|---|
| 25K | base | 56 / 44 / 0 / 34 | 66 / 33 / 0 / 40 | 47 / 53 / 0 / 27 |
| 25K | lock | 59 / 41 / 0 / 35 | 67 / 32 / 0 / 41 | 51 / 49 / 0 / 27 |
| 50K | base | 53 / 37 / 0 / 46 | 59 / 27 / 0 / 52 | 47 / 45 / 0 / 38 |
| 50K | lock | 54 / 35 / 0 / 42 | 54 / 29 / 0 / 50 | 54 / 40 / 0 / 36 |
| 100K | base | 62 / 36 / 0 / 86 | 68 / 28 / 0 / 99 | 55 / 45 / 0 / 72 |
| 100K | lock | 61 / 37 / 0 / 76 | 65 / 32 / 0 / 93 | 57 / 43 / 0 / 64 |
| 150K | base | 57 / 40 / 0 / 75 | 62 / 34 / 0 / 79 | 52 / 48 / 0 / 70 |
| 150K | lock | 59 / 38 / 0 / 75 | 63 / 31 / 0 / 83 | 55 / 45 / 0 / 65 |

FUNDED year 1 (260 sessions): dead % / mean income per 2 wk / survivor income per 2 wk / median per 2 wk.

| plan | stream | all starts | 2021-23 | 2024-26 |
|---|---|---|---|---|
| 25K | base | 70% / $53 / $128 / $21 | 66% / $63 / $124 / $35 | 74% / $42 / $134 / $0 |
| 25K | lock | 61% / $56 / $117 / $23 | 63% / $63 / $123 / $56 | 59% / $47 / $111 / $0 |
| 50K | base | 58% / $97 / $199 / $66 | 53% / $112 / $206 / $69 | 64% / $80 / $188 / $42 |
| 50K | lock | 57% / $106 / $221 / $54 | 53% / $110 / $212 / $60 | 60% / $102 / $234 / $36 |
| 100K | base | 38% / $141 / $203 / $130 | 17% / $160 / $187 / $154 | 63% / $119 / $245 / $46 |
| 100K | lock | 20% / $162 / $198 / $171 | 7% / $168 / $181 / $175 | 36% / $154 / $228 / $159 |
| 150K | base | 31% / $189 / $268 / $166 | 15% / $220 / $256 / $214 | 50% / $153 / $292 / $74 |
| 150K | lock | 10% / $232 / $256 / $225 | 14% / $238 / $274 / $259 | 6% / $225 / $235 / $225 |

## B. Cushion-proportional sizing, FUNDED - stream = base

n = clamp(floor(k x cushion / 1000), 1, cap). Cells: dead % / mean per 2 wk / survivor per 2 wk / median per 2 wk; avg q = mean micros per session. PICK = best 2021-23 mean income among rules whose 2021-23 dead % is not above live (else lowest dead %).


**50K** (live table size 2)

| rule | avg q | 2021-23 | 2024-26 | vs live |
|---|---|---|---|---|
| LIVE table | 1.48 | 53% / $112 / $206 / $69 | 64% / $80 / $188 / $42 | - |
| fixed 1 micro | 1.00 | 0% / $69 / $69 / $72 | 55% / $57 / $114 / $0 | FAIL (worse/worse) |
| k=0.4 cap 2 | 1.00 | 0% / $69 / $69 / $72 | 55% / $57 / $114 / $0 | FAIL (worse/worse) |
| k=0.4 cap 3 | 1.00 | 0% / $69 / $69 / $72 | 55% / $57 / $114 / $0 | FAIL (worse/worse) |
| k=0.4 cap 4 | 1.00 | 0% / $69 / $69 / $72 | 55% / $57 / $114 / $0 | FAIL (worse/worse) |
| k=0.6 cap 2 | 1.03 | 0% / $68 / $68 / $69 | 57% / $59 / $117 / $0 | FAIL (worse/worse) |
| k=0.6 cap 3 | 1.04 | 0% / $68 / $68 / $69 | 57% / $59 / $117 / $0 | FAIL (worse/worse) |
| k=0.6 cap 4 | 1.04 | 0% / $68 / $68 / $69 | 57% / $59 / $117 / $0 | FAIL (worse/worse) |
| k=0.8 cap 2 | 1.10 | 0% / $82 / $82 / $78 | 76% / $64 / $167 / $0 | FAIL (worse/worse) |
| k=0.8 cap 3 | 1.12 | 0% / $83 / $83 / $79 | 75% / $64 / $162 / $0 | FAIL (worse/worse) |
| k=0.8 cap 4 | 1.12 | 0% / $83 / $83 / $79 | 75% / $64 / $163 / $0 | FAIL (worse/worse) |
| k=1.0 cap 2 | 1.24 | 13% / $90 / $103 / $88 | 67% / $68 / $165 / $0 | FAIL (worse/worse) |
| k=1.0 cap 3 | 1.38 | 13% / $95 / $108 / $98 | 65% / $75 / $192 / $0 | FAIL (worse/same) |
| k=1.0 cap 4 | 1.44 | 13% / $92 / $105 / $96 | 67% / $72 / $190 / $0 | FAIL (worse/worse) |
| k=1.3 cap 2 | 1.40 | 34% / $95 / $130 / $103 | 60% / $79 / $161 / $53 | FAIL (worse/better) |
| k=1.3 cap 3 **PICK** | 1.58 | 37% / $107 / $156 / $92 | 68% / $86 / $185 / $19 | FAIL (better/worse) |
| k=1.3 cap 4 | 1.80 | 34% / $100 / $141 / $69 | 63% / $75 / $176 / $0 | FAIL (worse/same) |

**100K** (live table size 2)

| rule | avg q | 2021-23 | 2024-26 | vs live |
|---|---|---|---|---|
| LIVE table | 1.73 | 17% / $160 / $187 / $154 | 63% / $119 / $245 / $46 | - |
| fixed 1 micro | 1.00 | 0% / $42 / $42 / $29 | 0% / $55 / $55 / $43 | FAIL (worse/worse) |
| k=0.4 cap 2 | 1.02 | 0% / $42 / $42 / $29 | 0% / $53 / $53 / $43 | FAIL (worse/worse) |
| k=0.4 cap 3 | 1.02 | 0% / $42 / $42 / $29 | 0% / $53 / $53 / $43 | FAIL (worse/worse) |
| k=0.4 cap 4 | 1.02 | 0% / $42 / $42 / $29 | 0% / $53 / $53 / $43 | FAIL (worse/worse) |
| k=0.6 cap 2 | 1.12 | 0% / $54 / $54 / $40 | 0% / $55 / $55 / $40 | FAIL (worse/worse) |
| k=0.6 cap 3 | 1.14 | 0% / $54 / $54 / $40 | 0% / $56 / $56 / $40 | FAIL (worse/worse) |
| k=0.6 cap 4 | 1.14 | 0% / $54 / $54 / $40 | 0% / $55 / $55 / $40 | FAIL (worse/worse) |
| k=0.8 cap 2 | 1.44 | 0% / $76 / $76 / $68 | 53% / $75 / $149 / $40 | FAIL (worse/worse) |
| k=0.8 cap 3 | 1.51 | 0% / $97 / $97 / $79 | 52% / $75 / $147 / $28 | FAIL (worse/worse) |
| k=0.8 cap 4 | 1.56 | 0% / $96 / $96 / $77 | 52% / $79 / $154 / $28 | FAIL (worse/worse) |
| k=1.0 cap 2 | 1.58 | 0% / $129 / $129 / $122 | 47% / $99 / $186 / $46 | FAIL (worse/worse) |
| k=1.0 cap 3 | 1.78 | 0% / $136 / $136 / $102 | 54% / $105 / $214 / $44 | FAIL (worse/worse) |
| k=1.0 cap 4 | 1.94 | 0% / $137 / $137 / $100 | 57% / $105 / $229 / $44 | FAIL (worse/worse) |
| k=1.3 cap 2 | 1.66 | 11% / $146 / $160 / $130 | 50% / $119 / $223 / $49 | FAIL (worse/better) |
| k=1.3 cap 3 | 2.00 | 14% / $156 / $176 / $148 | 52% / $127 / $242 / $87 | FAIL (same/better) |
| k=1.3 cap 4 **PICK** | 2.30 | 12% / $161 / $180 / $152 | 52% / $126 / $250 / $87 | PASS |

**150K** (live table size 3)

| rule | avg q | 2021-23 | 2024-26 | vs live |
|---|---|---|---|---|
| LIVE table | 2.71 | 15% / $220 / $256 / $214 | 50% / $153 / $292 / $74 | - |
| fixed 1 micro | 1.00 | 0% / $10 / $10 / $0 | 0% / $25 / $25 / $19 | FAIL (worse/worse) |
| k=0.4 cap 3 | 1.04 | 0% / $11 / $11 / $0 | 0% / $27 / $27 / $18 | FAIL (worse/worse) |
| k=0.4 cap 4 | 1.04 | 0% / $11 / $11 / $0 | 0% / $27 / $27 / $18 | FAIL (worse/worse) |
| k=0.4 cap 5 | 1.04 | 0% / $11 / $11 / $0 | 0% / $27 / $27 / $18 | FAIL (worse/worse) |
| k=0.6 cap 3 | 1.76 | 0% / $91 / $91 / $46 | 0% / $85 / $85 / $30 | FAIL (worse/worse) |
| k=0.6 cap 4 | 1.82 | 0% / $94 / $94 / $47 | 0% / $82 / $82 / $28 | FAIL (worse/worse) |
| k=0.6 cap 5 | 1.86 | 0% / $94 / $94 / $47 | 0% / $83 / $83 / $28 | FAIL (worse/worse) |
| k=0.8 cap 3 | 2.19 | 0% / $149 / $149 / $123 | 15% / $131 / $155 / $79 | FAIL (worse/worse) |
| k=0.8 cap 4 | 2.36 | 0% / $151 / $151 / $121 | 15% / $130 / $153 / $69 | FAIL (worse/worse) |
| k=0.8 cap 5 | 2.50 | 0% / $149 / $149 / $104 | 16% / $127 / $151 / $66 | FAIL (worse/worse) |
| k=1.0 cap 3 | 2.32 | 0% / $173 / $173 / $140 | 44% / $147 / $260 / $76 | FAIL (worse/better) |
| k=1.0 cap 4 | 2.65 | 0% / $194 / $194 / $160 | 45% / $156 / $284 / $104 | FAIL (worse/better) |
| k=1.0 cap 5 | 2.93 | 0% / $190 / $190 / $147 | 45% / $160 / $290 / $104 | FAIL (worse/better) |
| k=1.3 cap 3 | 2.44 | 2% / $190 / $193 / $155 | 42% / $154 / $265 / $76 | FAIL (worse/better) |
| k=1.3 cap 4 **PICK** | 2.86 | 2% / $209 / $212 / $148 | 45% / $163 / $292 / $104 | FAIL (worse/better) |
| k=1.3 cap 5 | 3.10 | 4% / $188 / $194 / $139 | 48% / $155 / $285 / $104 | FAIL (worse/same) |

## B. Cushion-proportional sizing, FUNDED - stream = lock

n = clamp(floor(k x cushion / 1000), 1, cap). Cells: dead % / mean per 2 wk / survivor per 2 wk / median per 2 wk; avg q = mean micros per session. PICK = best 2021-23 mean income among rules whose 2021-23 dead % is not above live (else lowest dead %).


**50K** (live table size 2)

| rule | avg q | 2021-23 | 2024-26 | vs live |
|---|---|---|---|---|
| LIVE table | 1.51 | 53% / $110 / $212 / $60 | 60% / $102 / $234 / $36 | - |
| fixed 1 micro | 1.00 | 0% / $78 / $78 / $85 | 0% / $95 / $95 / $97 | FAIL (worse/better) |
| k=0.4 cap 2 | 1.01 | 0% / $78 / $78 / $85 | 0% / $95 / $95 / $94 | FAIL (worse/better) |
| k=0.4 cap 3 | 1.01 | 0% / $78 / $78 / $85 | 0% / $95 / $95 / $94 | FAIL (worse/better) |
| k=0.4 cap 4 | 1.01 | 0% / $78 / $78 / $85 | 0% / $95 / $95 / $94 | FAIL (worse/better) |
| k=0.6 cap 2 | 1.05 | 0% / $78 / $78 / $80 | 0% / $103 / $103 / $111 | FAIL (worse/better) |
| k=0.6 cap 3 | 1.07 | 0% / $78 / $78 / $80 | 0% / $101 / $101 / $106 | FAIL (worse/better) |
| k=0.6 cap 4 | 1.07 | 0% / $78 / $78 / $80 | 0% / $99 / $99 / $95 | FAIL (worse/better) |
| k=0.8 cap 2 | 1.18 | 0% / $89 / $89 / $97 | 0% / $106 / $106 / $106 | FAIL (worse/better) |
| k=0.8 cap 3 | 1.25 | 0% / $90 / $90 / $89 | 0% / $106 / $106 / $102 | FAIL (worse/better) |
| k=0.8 cap 4 | 1.28 | 0% / $89 / $89 / $88 | 0% / $97 / $97 / $69 | FAIL (worse/better) |
| k=1.0 cap 2 | 1.31 | 3% / $97 / $100 / $102 | 27% / $103 / $141 / $111 | FAIL (worse/better) |
| k=1.0 cap 3 **PICK** | 1.48 | 3% / $101 / $104 / $97 | 27% / $114 / $156 / $122 | PASS |
| k=1.0 cap 4 | 1.61 | 3% / $93 / $96 / $89 | 27% / $97 / $132 / $69 | FAIL (worse/better) |
| k=1.3 cap 2 | 1.45 | 43% / $89 / $134 / $104 | 45% / $103 / $186 / $69 | FAIL (worse/better) |
| k=1.3 cap 3 | 1.68 | 42% / $100 / $152 / $101 | 51% / $107 / $210 / $69 | FAIL (worse/better) |
| k=1.3 cap 4 | 1.95 | 41% / $99 / $156 / $69 | 52% / $90 / $182 / $27 | FAIL (worse/worse) |

**100K** (live table size 2)

| rule | avg q | 2021-23 | 2024-26 | vs live |
|---|---|---|---|---|
| LIVE table | 1.84 | 7% / $168 / $181 / $175 | 36% / $154 / $228 / $159 | - |
| fixed 1 micro | 1.00 | 0% / $49 / $49 / $54 | 0% / $75 / $75 / $72 | FAIL (worse/worse) |
| k=0.4 cap 2 | 1.01 | 0% / $49 / $49 / $54 | 0% / $70 / $70 / $64 | FAIL (worse/worse) |
| k=0.4 cap 3 | 1.01 | 0% / $49 / $49 / $54 | 0% / $70 / $70 / $64 | FAIL (worse/worse) |
| k=0.4 cap 4 | 1.01 | 0% / $49 / $49 / $54 | 0% / $70 / $70 / $64 | FAIL (worse/worse) |
| k=0.6 cap 2 | 1.11 | 0% / $57 / $57 / $55 | 0% / $102 / $102 / $106 | FAIL (worse/worse) |
| k=0.6 cap 3 | 1.14 | 0% / $57 / $57 / $54 | 0% / $100 / $100 / $103 | FAIL (worse/worse) |
| k=0.6 cap 4 | 1.14 | 0% / $57 / $57 / $54 | 0% / $99 / $99 / $103 | FAIL (worse/worse) |
| k=0.8 cap 2 | 1.49 | 0% / $93 / $93 / $95 | 0% / $139 / $139 / $141 | FAIL (worse/worse) |
| k=0.8 cap 3 | 1.60 | 0% / $118 / $118 / $122 | 0% / $153 / $153 / $150 | FAIL (worse/better) |
| k=0.8 cap 4 | 1.69 | 0% / $118 / $118 / $121 | 0% / $147 / $147 / $134 | FAIL (worse/better) |
| k=1.0 cap 2 | 1.63 | 0% / $149 / $149 / $143 | 4% / $132 / $136 / $131 | FAIL (worse/worse) |
| k=1.0 cap 3 | 1.90 | 0% / $147 / $147 / $141 | 15% / $167 / $194 / $149 | FAIL (worse/better) |
| k=1.0 cap 4 **PICK** | 2.12 | 0% / $153 / $153 / $138 | 17% / $172 / $204 / $139 | FAIL (worse/better) |
| k=1.3 cap 2 | 1.76 | 13% / $164 / $187 / $170 | 6% / $158 / $168 / $156 | FAIL (worse/better) |
| k=1.3 cap 3 | 2.04 | 22% / $156 / $189 / $150 | 56% / $161 / $335 / $87 | FAIL (worse/worse) |
| k=1.3 cap 4 | 2.36 | 21% / $164 / $198 / $138 | 57% / $169 / $359 / $87 | FAIL (worse/worse) |

**150K** (live table size 3)

| rule | avg q | 2021-23 | 2024-26 | vs live |
|---|---|---|---|---|
| LIVE table | 2.83 | 14% / $238 / $274 / $259 | 6% / $225 / $235 / $225 | - |
| fixed 1 micro | 1.00 | 0% / $13 / $13 / $0 | 0% / $45 / $45 / $23 | FAIL (worse/worse) |
| k=0.4 cap 3 | 1.05 | 0% / $15 / $15 / $0 | 0% / $58 / $58 / $25 | FAIL (worse/worse) |
| k=0.4 cap 4 | 1.05 | 0% / $15 / $15 / $0 | 0% / $58 / $58 / $25 | FAIL (worse/worse) |
| k=0.4 cap 5 | 1.05 | 0% / $15 / $15 / $0 | 0% / $58 / $58 / $25 | FAIL (worse/worse) |
| k=0.6 cap 3 | 1.74 | 0% / $113 / $113 / $98 | 0% / $135 / $135 / $50 | FAIL (worse/worse) |
| k=0.6 cap 4 | 1.82 | 0% / $115 / $115 / $98 | 0% / $131 / $131 / $50 | FAIL (worse/worse) |
| k=0.6 cap 5 | 1.85 | 0% / $114 / $114 / $98 | 0% / $129 / $129 / $48 | FAIL (worse/worse) |
| k=0.8 cap 3 | 2.23 | 0% / $165 / $165 / $157 | 0% / $178 / $178 / $152 | FAIL (worse/worse) |
| k=0.8 cap 4 | 2.42 | 0% / $189 / $189 / $193 | 0% / $187 / $187 / $161 | FAIL (worse/worse) |
| k=0.8 cap 5 | 2.62 | 0% / $183 / $183 / $179 | 0% / $192 / $192 / $163 | FAIL (worse/worse) |
| k=1.0 cap 3 | 2.40 | 0% / $199 / $199 / $188 | 1% / $187 / $188 / $171 | FAIL (worse/worse) |
| k=1.0 cap 4 | 2.76 | 0% / $221 / $221 / $225 | 2% / $202 / $205 / $167 | FAIL (worse/worse) |
| k=1.0 cap 5 | 3.09 | 0% / $221 / $221 / $225 | 2% / $216 / $219 / $167 | FAIL (worse/better) |
| k=1.3 cap 3 | 2.49 | 10% / $200 / $220 / $168 | 34% / $204 / $301 / $225 | FAIL (worse/worse) |
| k=1.3 cap 4 **PICK** | 2.85 | 6% / $238 / $251 / $225 | 51% / $182 / $352 / $104 | FAIL (better/worse) |
| k=1.3 cap 5 | 3.31 | 14% / $213 / $244 / $225 | 40% / $217 / $343 / $171 | FAIL (worse/worse) |

## B2. Cushion-proportional sizing, EVAL - stream = base

Cells: pass / frozen / bust % / median sessions. cap base = largest size of the live Eval-Mode row (50K 2, 100K 4, 150K 4). PICK = best 2021-23 pass %.


**50K**

| rule | 2021-23 | 2024-26 | vs live |
|---|---|---|---|
| LIVE eval row | 59 / 27 / 0 / 52 | 47 / 45 / 0 / 38 | - |
| fixed 1 micro | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.4 cap 2 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.4 cap 3 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.4 cap 4 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.6 cap 2 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.6 cap 3 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.6 cap 4 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | FAIL (worse/worse) |
| k=0.8 cap 2 | 43 / 0 / 0 / 87 | 46 / 26 / 0 / 75 | FAIL (worse/worse) |
| k=0.8 cap 3 | 43 / 0 / 0 / 87 | 46 / 26 / 0 / 75 | FAIL (worse/worse) |
| k=0.8 cap 4 | 43 / 0 / 0 / 87 | 46 / 26 / 0 / 75 | FAIL (worse/worse) |
| k=1.0 cap 2 | 29 / 0 / 0 / 88 | 39 / 33 / 0 / 60 | FAIL (worse/worse) |
| k=1.0 cap 3 | 29 / 0 / 0 / 88 | 39 / 33 / 0 / 60 | FAIL (worse/worse) |
| k=1.0 cap 4 | 29 / 0 / 0 / 88 | 39 / 33 / 0 / 60 | FAIL (worse/worse) |
| k=1.3 cap 2 **PICK** | 53 / 10 / 0 / 61 | 45 / 32 / 0 / 50 | FAIL (worse/worse) |
| k=1.3 cap 3 | 52 / 11 / 0 / 62 | 46 / 32 / 0 / 50 | FAIL (worse/worse) |
| k=1.3 cap 4 | 52 / 11 / 0 / 62 | 46 / 32 / 0 / 50 | FAIL (worse/worse) |

**100K**

| rule | 2021-23 | 2024-26 | vs live |
|---|---|---|---|
| LIVE eval row | 68 / 28 / 0 / 99 | 55 / 45 / 0 / 72 | - |
| fixed 1 micro | 12 / 0 / 0 / 226 | 51 / 0 / 0 / 185 | FAIL (worse/worse) |
| k=0.4 cap 4 | 16 / 0 / 0 / 213 | 52 / 0 / 0 / 173 | FAIL (worse/worse) |
| k=0.4 cap 5 | 16 / 0 / 0 / 213 | 52 / 0 / 0 / 173 | FAIL (worse/worse) |
| k=0.4 cap 6 | 16 / 0 / 0 / 213 | 52 / 0 / 0 / 173 | FAIL (worse/worse) |
| k=0.6 cap 4 | 34 / 0 / 0 / 184 | 57 / 0 / 0 / 168 | FAIL (worse/worse) |
| k=0.6 cap 5 | 34 / 0 / 0 / 184 | 57 / 0 / 0 / 168 | FAIL (worse/worse) |
| k=0.6 cap 6 | 34 / 0 / 0 / 184 | 57 / 0 / 0 / 168 | FAIL (worse/worse) |
| k=0.8 cap 4 | 57 / 0 / 0 / 127 | 52 / 48 / 0 / 112 | FAIL (worse/worse) |
| k=0.8 cap 5 | 57 / 0 / 0 / 127 | 52 / 48 / 0 / 112 | FAIL (worse/worse) |
| k=0.8 cap 6 | 57 / 0 / 0 / 127 | 52 / 48 / 0 / 112 | FAIL (worse/worse) |
| k=1.0 cap 4 | 58 / 0 / 0 / 130 | 51 / 49 / 0 / 86 | FAIL (worse/worse) |
| k=1.0 cap 5 | 58 / 0 / 0 / 130 | 51 / 49 / 0 / 88 | FAIL (worse/worse) |
| k=1.0 cap 6 | 58 / 0 / 0 / 130 | 51 / 49 / 0 / 88 | FAIL (worse/worse) |
| k=1.3 cap 4 | 69 / 7 / 0 / 106 | 55 / 45 / 0 / 71 | FAIL (worse/same) |
| k=1.3 cap 5 **PICK** | 69 / 11 / 0 / 103 | 54 / 46 / 0 / 72 | FAIL (worse/same) |
| k=1.3 cap 6 | 69 / 12 / 0 / 102 | 54 / 46 / 0 / 74 | FAIL (same/same) |

**150K**

| rule | 2021-23 | 2024-26 | vs live |
|---|---|---|---|
| LIVE eval row | 62 / 34 / 0 / 79 | 52 / 48 / 0 / 70 | - |
| fixed 1 micro | 0 / 0 / 0 / nan | 11 / 0 / 0 / 234 | FAIL (worse/worse) |
| k=0.4 cap 4 | 0 / 0 / 0 / nan | 20 / 0 / 0 / 222 | FAIL (worse/worse) |
| k=0.4 cap 5 | 0 / 0 / 0 / nan | 20 / 0 / 0 / 222 | FAIL (worse/worse) |
| k=0.4 cap 6 | 0 / 0 / 0 / nan | 20 / 0 / 0 / 222 | FAIL (worse/worse) |
| k=0.6 cap 4 | 36 / 0 / 0 / 138 | 37 / 0 / 0 / 111 | FAIL (worse/worse) |
| k=0.6 cap 5 | 36 / 0 / 0 / 138 | 37 / 0 / 0 / 111 | FAIL (worse/worse) |
| k=0.6 cap 6 | 36 / 0 / 0 / 138 | 37 / 0 / 0 / 111 | FAIL (worse/worse) |
| k=0.8 cap 4 | 58 / 0 / 0 / 114 | 51 / 13 / 0 / 99 | FAIL (worse/worse) |
| k=0.8 cap 5 | 59 / 0 / 0 / 111 | 50 / 13 / 0 / 97 | FAIL (worse/worse) |
| k=0.8 cap 6 | 60 / 0 / 0 / 112 | 50 / 13 / 0 / 98 | FAIL (worse/worse) |
| k=1.0 cap 4 | 66 / 0 / 0 / 108 | 53 / 44 / 0 / 79 | FAIL (same/worse) |
| k=1.0 cap 5 **PICK** | 66 / 0 / 0 / 104 | 54 / 45 / 0 / 76 | FAIL (same/worse) |
| k=1.0 cap 6 | 65 / 0 / 0 / 100 | 53 / 45 / 0 / 76 | FAIL (same/worse) |
| k=1.3 cap 4 | 64 / 0 / 0 / 97 | 54 / 45 / 0 / 72 | FAIL (worse/same) |
| k=1.3 cap 5 | 61 / 2 / 0 / 94 | 54 / 45 / 0 / 73 | FAIL (worse/same) |
| k=1.3 cap 6 | 65 / 3 / 0 / 93 | 54 / 46 / 0 / 70 | FAIL (worse/same) |

## B2. Cushion-proportional sizing, EVAL - stream = lock

Cells: pass / frozen / bust % / median sessions. cap base = largest size of the live Eval-Mode row (50K 2, 100K 4, 150K 4). PICK = best 2021-23 pass %.


**50K**

| rule | 2021-23 | 2024-26 | vs live |
|---|---|---|---|
| LIVE eval row | 54 / 29 / 0 / 50 | 54 / 40 / 0 / 36 | - |
| fixed 1 micro | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.4 cap 2 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.4 cap 3 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.4 cap 4 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.6 cap 2 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.6 cap 3 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.6 cap 4 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | FAIL (worse/worse) |
| k=0.8 cap 2 | 43 / 0 / 0 / 88 | 52 / 0 / 0 / 73 | FAIL (worse/worse) |
| k=0.8 cap 3 | 43 / 0 / 0 / 88 | 52 / 0 / 0 / 73 | FAIL (worse/worse) |
| k=0.8 cap 4 | 43 / 0 / 0 / 88 | 52 / 0 / 0 / 73 | FAIL (worse/worse) |
| k=1.0 cap 2 | 34 / 0 / 0 / 93 | 51 / 9 / 0 / 62 | FAIL (worse/worse) |
| k=1.0 cap 3 | 34 / 0 / 0 / 93 | 51 / 9 / 0 / 62 | FAIL (worse/worse) |
| k=1.0 cap 4 | 34 / 0 / 0 / 93 | 51 / 9 / 0 / 62 | FAIL (worse/worse) |
| k=1.3 cap 2 | 52 / 13 / 0 / 63 | 54 / 21 / 0 / 43 | FAIL (worse/worse) |
| k=1.3 cap 3 **PICK** | 54 / 13 / 0 / 62 | 54 / 21 / 0 / 42 | FAIL (worse/worse) |
| k=1.3 cap 4 | 54 / 13 / 0 / 62 | 54 / 21 / 0 / 42 | FAIL (worse/worse) |

**100K**

| rule | 2021-23 | 2024-26 | vs live |
|---|---|---|---|
| LIVE eval row | 65 / 32 / 0 / 93 | 57 / 43 / 0 / 64 | - |
| fixed 1 micro | 10 / 0 / 0 / 233 | 53 / 0 / 0 / 178 | FAIL (worse/worse) |
| k=0.4 cap 4 | 14 / 0 / 0 / 224 | 53 / 0 / 0 / 177 | FAIL (worse/worse) |
| k=0.4 cap 5 | 14 / 0 / 0 / 224 | 53 / 0 / 0 / 177 | FAIL (worse/worse) |
| k=0.4 cap 6 | 14 / 0 / 0 / 224 | 53 / 0 / 0 / 177 | FAIL (worse/worse) |
| k=0.6 cap 4 | 37 / 0 / 0 / 201 | 64 / 0 / 0 / 160 | FAIL (worse/same) |
| k=0.6 cap 5 | 37 / 0 / 0 / 201 | 64 / 0 / 0 / 160 | FAIL (worse/same) |
| k=0.6 cap 6 | 37 / 0 / 0 / 201 | 64 / 0 / 0 / 160 | FAIL (worse/same) |
| k=0.8 cap 4 | 67 / 0 / 0 / 131 | 68 / 0 / 0 / 122 | FAIL (worse/same) |
| k=0.8 cap 5 | 67 / 0 / 0 / 131 | 68 / 0 / 0 / 122 | FAIL (worse/same) |
| k=0.8 cap 6 | 67 / 0 / 0 / 131 | 68 / 0 / 0 / 122 | FAIL (worse/same) |
| k=1.0 cap 4 | 68 / 0 / 0 / 133 | 72 / 11 / 0 / 103 | FAIL (same/same) |
| k=1.0 cap 5 | 71 / 0 / 0 / 118 | 72 / 11 / 0 / 105 | FAIL (same/same) |
| k=1.0 cap 6 | 71 / 0 / 0 / 118 | 72 / 11 / 0 / 105 | FAIL (same/same) |
| k=1.3 cap 4 | 72 / 15 / 0 / 100 | 57 / 43 / 0 / 66 | FAIL (same/same) |
| k=1.3 cap 5 | 73 / 17 / 0 / 100 | 57 / 43 / 0 / 68 | FAIL (same/worse) |
| k=1.3 cap 6 **PICK** | 74 / 17 / 0 / 98 | 56 / 44 / 0 / 67 | FAIL (same/same) |

**150K**

| rule | 2021-23 | 2024-26 | vs live |
|---|---|---|---|
| LIVE eval row | 63 / 31 / 0 / 83 | 55 / 45 / 0 / 65 | - |
| fixed 1 micro | 0 / 0 / 0 / nan | 3 / 0 / 0 / 220 | FAIL (worse/worse) |
| k=0.4 cap 4 | 0 / 0 / 0 / nan | 36 / 0 / 0 / 198 | FAIL (worse/worse) |
| k=0.4 cap 5 | 0 / 0 / 0 / nan | 36 / 0 / 0 / 198 | FAIL (worse/worse) |
| k=0.4 cap 6 | 0 / 0 / 0 / nan | 36 / 0 / 0 / 198 | FAIL (worse/worse) |
| k=0.6 cap 4 | 48 / 0 / 0 / 171 | 51 / 0 / 0 / 124 | FAIL (worse/worse) |
| k=0.6 cap 5 | 48 / 0 / 0 / 172 | 51 / 0 / 0 / 124 | FAIL (worse/worse) |
| k=0.6 cap 6 | 48 / 0 / 0 / 172 | 51 / 0 / 0 / 124 | FAIL (worse/worse) |
| k=0.8 cap 4 | 70 / 0 / 0 / 122 | 65 / 0 / 0 / 108 | FAIL (same/same) |
| k=0.8 cap 5 | 68 / 0 / 0 / 120 | 66 / 0 / 0 / 108 | FAIL (same/same) |
| k=0.8 cap 6 | 71 / 0 / 0 / 118 | 64 / 0 / 0 / 109 | FAIL (same/same) |
| k=1.0 cap 4 | 72 / 0 / 0 / 109 | 69 / 1 / 0 / 93 | FAIL (same/same) |
| k=1.0 cap 5 | 73 / 0 / 0 / 105 | 69 / 1 / 0 / 92 | FAIL (same/same) |
| k=1.0 cap 6 | 72 / 0 / 0 / 103 | 69 / 1 / 0 / 91 | FAIL (same/same) |
| k=1.3 cap 4 | 71 / 4 / 0 / 100 | 61 / 38 / 0 / 75 | FAIL (same/same) |
| k=1.3 cap 5 | 73 / 8 / 0 / 106 | 71 / 28 / 0 / 79 | FAIL (same/same) |
| k=1.3 cap 6 **PICK** | 75 / 11 / 0 / 102 | 69 / 29 / 0 / 72 | FAIL (same/same) |

## C. Which account size for 1 micro? (same trades, fixed 1 micro, no brake)

EVAL pass / frozen / bust % / median sessions (25K, 50K: 120-session window; 100K, 150K: 250). FUNDED dead % / mean / survivor / median per 2 wk. 'inc per dead pt' = mean income per 2 wk / dead %.

| plan @ size | stream | EVAL all | EVAL 2021-23 | EVAL 2024-26 | FUNDED all | FUNDED 2021-23 | FUNDED 2024-26 | inc per dead pt |
|---|---|---|---|---|---|---|---|---|
| 25K @ 1 micro | base | 56 / 44 / 0 / 34 | 66 / 33 / 0 / 40 | 47 / 53 / 0 / 27 | 70% / $53 / $128 / $21 | 66% / $63 / $124 / $35 | 74% / $42 / $134 / $0 | 0.8 |
| 50K @ 1 micro | base | 46 / 13 / 0 / 80 | 42 / 0 / 0 / 88 | 49 / 25 / 0 / 73 | 25% / $63 / $82 / $58 | 0% / $69 / $69 / $72 | 55% / $57 / $114 / $0 | 2.5 |
| 50K @ live table | base | 53 / 37 / 0 / 46 | 59 / 27 / 0 / 52 | 47 / 45 / 0 / 38 | 58% / $97 / $199 / $66 | 53% / $112 / $206 / $69 | 64% / $80 / $188 / $42 | 1.7 |
| 100K @ 1 micro | base | 30 / 0 / 0 / 202 | 12 / 0 / 0 / 226 | 51 / 0 / 0 / 185 | 0% / $48 / $48 / $36 | 0% / $42 / $42 / $29 | 0% / $55 / $55 / $43 | 48.4 |
| 100K @ live table | base | 62 / 36 / 0 / 86 | 68 / 28 / 0 / 99 | 55 / 45 / 0 / 72 | 38% / $141 / $203 / $130 | 17% / $160 / $187 / $154 | 63% / $119 / $245 / $46 | 3.7 |
| 150K @ 1 micro | base | 5 / 0 / 0 / 234 | 0 / 0 / 0 / nan | 11 / 0 / 0 / 234 | 0% / $17 / $17 / $0 | 0% / $10 / $10 / $0 | 0% / $25 / $25 / $19 | 17.2 |
| 150K @ live table | base | 57 / 40 / 0 / 75 | 62 / 34 / 0 / 79 | 52 / 48 / 0 / 70 | 31% / $189 / $268 / $166 | 15% / $220 / $256 / $214 | 50% / $153 / $292 / $74 | 6.0 |
| 25K @ 1 micro | lock | 59 / 41 / 0 / 35 | 67 / 32 / 0 / 41 | 51 / 49 / 0 / 27 | 61% / $56 / $117 / $23 | 63% / $63 / $123 / $56 | 59% / $47 / $111 / $0 | 0.9 |
| 50K @ 1 micro | lock | 48 / 0 / 0 / 83 | 42 / 0 / 0 / 88 | 54 / 0 / 0 / 74 | 0% / $86 / $86 / $86 | 0% / $78 / $78 / $85 | 0% / $95 / $95 / $97 | 85.7 |
| 50K @ live table | lock | 54 / 35 / 0 / 42 | 54 / 29 / 0 / 50 | 54 / 40 / 0 / 36 | 57% / $106 / $221 / $54 | 53% / $110 / $212 / $60 | 60% / $102 / $234 / $36 | 1.9 |
| 100K @ 1 micro | lock | 30 / 0 / 0 / 200 | 10 / 0 / 0 / 233 | 53 / 0 / 0 / 178 | 0% / $61 / $61 / $58 | 0% / $49 / $49 / $54 | 0% / $75 / $75 / $72 | 60.7 |
| 100K @ live table | lock | 61 / 37 / 0 / 76 | 65 / 32 / 0 / 93 | 57 / 43 / 0 / 64 | 20% / $162 / $198 / $171 | 7% / $168 / $181 / $175 | 36% / $154 / $228 / $159 | 7.9 |
| 150K @ 1 micro | lock | 1 / 0 / 0 / 220 | 0 / 0 / 0 / nan | 3 / 0 / 0 / 220 | 0% / $28 / $28 / $18 | 0% / $13 / $13 / $0 | 0% / $45 / $45 / $23 | 28.0 |
| 150K @ live table | lock | 59 / 38 / 0 / 75 | 63 / 31 / 0 / 83 | 55 / 45 / 0 / 65 | 10% / $232 / $256 / $225 | 14% / $238 / $274 / $259 | 6% / $225 / $235 / $225 | 22.4 |
