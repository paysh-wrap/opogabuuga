# Session 20 — B2: does the SHIPPED config reproduce the session-19 numbers?

Date 2026-11-12. Script: `docs/results/session19/refine/run_shipped.py` (same `lib.py` / `noise2.py` / `fade2.py` generators,
data, costs and Lucid Pro eval simulator as the session-19 refine study). Raw output: `refine/shipped_results.json`.
Pick = IS 2019-05-06..2025-11-05, judge = J 2025-11-06..2026-11-06, ALL = both (7.5 yr). 1 micro unless noted; pass / bust =
block-bootstrap % (table 1: 600 paths × 400 sessions, the §1/§2 protocol; tables 2–3: 400 paths × 500 sessions, the §4 protocol).

## Verdict
1. **Reproduced exactly.** S0 (NOISE preset C lock +100 pt → entry +10, Mondays off, fade OFF) = session-19 R6 to the trade:
   IS 814 tr / 48.6 % / PF 1.44 / $17,156; J 121 / 59.5 % / 1.72 / $6,087; 25K IS 76/24, J 69/31; 50K IS 74/26, J 68/32. §4 cells
   match too: 25K×1 72/28, 50K×1 90/6, 50K×2 70/30, 100K×2 83/15, 150K×3 83/15, 150K×4 75/24.
2. **The pre-fix plans were NOT what was measured and were clearly worse:** S3 (no lock + Mondays off + fade trading Mondays, the
   shipped default before D132) 25K 58/42 (J 52/48) vs 72/28. → **profit lock ON in every plan (D132).**
3. **Fade on Mondays (S1) is worse than fade skipping Mondays (S2)** in IS, J and ALL on every size → **PM_FADE now respects
   `noise_cfg.skip_weekdays` (D132).**
4. **Fade OFF beats fade ON for evaluations in-sample and over 7.5 yr** (25K ALL 72/28 vs 68/32, IS 75/25 vs 66/34; 50K×2 70/30 vs
   67/33); only J favours the fade (25K 67/33 vs 72/28, inside J noise ±5 pt). The fade adds net profit (ALL $28.5k vs $23.2k) →
   **I3 toggle "Afternoon fade off during evaluations" default ON** (EVAL stage only); funded accounts keep the fade.

## Table 1 — stats and Pro 25K / 50K eval (600 paths)
| Variant | IS n | win % | PF | net $ | J n | win % | PF | net $ | ALL n | PF | net $ | 25K IS | 25K J | 50K×2 IS | 50K×2 J |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 NOISE C + Mon off, fade OFF | 814 | 48.6 | 1.44 | 17,156 | 121 | 59.5 | 1.72 | 6,087 | 935 | 1.49 | 23,242 | 76 / 24 | 69 / 31 | 74 / 26 | 68 / 32 |
| S1 NOISE C + Mon off, fade ON (fade trades Mondays) | 1592 | 51.8 | 1.26 | 19,231 | 231 | 58.4 | 1.57 | 8,594 | 1823 | 1.31 | 27,825 | 62 / 38 | 70 / 30 | 60 / 40 | 69 / 31 |
| S2 NOISE C + Mon off, fade ON (fade skips Mondays) | 1343 | 51.9 | 1.32 | 19,950 | 192 | 59.9 | 1.69 | 8,502 | 1535 | 1.38 | 28,452 | 67 / 33 | 72 / 28 | 65 / 35 | 70 / 30 |
| S3 pre-fix default: NOISE no lock + Mon off, fade ON (Mondays) | 1605 | 50.1 | 1.26 | 20,798 | 245 | 51.4 | 1.33 | 6,356 | 1850 | 1.28 | 27,153 | 61 / 39 | 53 / 47 | 58 / 42 | 50 / 50 |
| S4 NOISE no lock + Mon off, fade OFF | 827 | 45.3 | 1.43 | 18,722 | 135 | 46.7 | 1.30 | 3,849 | 962 | 1.41 | 22,571 | 73 / 27 | 44 / 56 | 72 / 28 | 40 / 60 |

## Table 2 — §4 protocol, ALL 7.5 yr, pass / bust %
| Variant | 25K×1 | 50K×1 | 50K×2 | 100K×2 | 150K×3 | 150K×4 |
|---|---|---|---|---|---|---|
| S0 NOISE C + Mon off, fade OFF | 72 / 28 | 90 / 6 | 70 / 30 | 83 / 15 | 83 / 15 | 75 / 24 |
| S1 NOISE C + Mon off, fade ON (fade trades Mondays) | 65 / 35 | 80 / 19 | 62 / 38 | 71 / 29 | 71 / 28 | 64 / 36 |
| S2 NOISE C + Mon off, fade ON (fade skips Mondays) | 68 / 32 | 88 / 12 | 67 / 33 | 79 / 20 | 79 / 20 | 70 / 30 |
| S3 pre-fix default: NOISE no lock + Mon off, fade ON (Mondays) | 58 / 42 | 74 / 25 | 55 / 45 | 63 / 37 | 63 / 36 | 56 / 44 |
| S4 NOISE no lock + Mon off, fade OFF | 64 / 36 | 81 / 13 | 62 / 38 | 72 / 25 | 72 / 25 | 62 / 38 |

## Table 3 — §4 protocol, IS and J, pass / bust %
| Variant | 25K×1 IS | 25K×1 J | 50K×2 IS | 50K×2 J | 150K×3 J | 150K×4 J |
|---|---|---|---|---|---|---|
| S0 NOISE C + Mon off, fade OFF | 75 / 25 | 67 / 33 | 74 / 26 | 65 / 35 | 78 / 22 | 68 / 32 |
| S1 NOISE C + Mon off, fade ON (fade trades Mondays) | 62 / 38 | 69 / 31 | 59 / 41 | 68 / 32 | 83 / 17 | 71 / 29 |
| S2 NOISE C + Mon off, fade ON (fade skips Mondays) | 66 / 34 | 72 / 28 | 65 / 35 | 70 / 30 | 87 / 13 | 75 / 25 |
| S3 pre-fix default: NOISE no lock + Mon off, fade ON (Mondays) | 60 / 40 | 52 / 48 | 57 / 43 | 49 / 51 | 56 / 44 | 48 / 52 |
| S4 NOISE no lock + Mon off, fade OFF | 75 / 25 | 43 / 57 | 74 / 26 | 38 / 62 | 40 / 60 | 34 / 66 |

Caveats (unchanged from session 19): J has only 121–245 trades; news blackouts and intraday MLL touches are not modelled;
the fade's 6.5-year edge is thin (stand-alone PF 1.12 vs random 1.00); the eval sim does not model the brake/grow rows.
