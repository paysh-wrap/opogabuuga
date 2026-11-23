# late_leg_sizes: late-day momentum as a 3rd edge on the BUILT D163 fast-pass rows (2026-11-23)

Research only for Step 1; the build (D166) follows the picks below. Sim: `pass_fastest/final_search` (one account, one position, DLL, EOD MLL + lock,
C40 day stop 38 %, kill switch, $125 per-micro cap), 5 years MNQ, rolling starts. Rows rebuilt from D163: 150K CANDACE grow +1 per $1,500 (max 6), 50K day lock 0.4.
Base rows (no late leg): 25K 61.8 % / 56.5 d, 50K 66.3 % / 61 d, 100K 71.4 % / 87 d, 150K 74.4 % / 80 d (the 150K D163 base was rebuilt here; new_edge/RESULTS.md only had the pre-D163 76.4 %).

Late leg = `lastmom239`: sign of (13:30 close - 09:30 open) if >= 0.1 x 14-day avg range, enter 15:00, 60 pt stop, flat 15:59. Rule 7: the sim takes it only when
NOISE / CANDACE hold no position (one per account); all legs are MNQ (equity-index lock applies across accounts, tested in the app). Lucid rules on: it never trades
more than the DLL left / MLL room allow (shrink, else skip). Columns: ALL = 5-year rolling starts; judge = starts in 2024-26; pick = starts 2021-23.
`flatN` = N micros; `brakeN` = N micros, 1 micro when cushion < the plan's first NOISE brake (25K: CANDACE brake $333, 50K $667, 100K $1,000, 150K $2,250);
`brakeHN` = 1 micro below $ 0.5 x MLL. (150K: brakeN = brakeHN.)

## Picks (floor: ALL pass >= 70 % on 100K / 150K, 62 % on 25K / 50K; lowest median days)
| plan | pick | pass % (base) | median days (base) | judge % (base) | profit (base) | note |
|---|---|---|---|---|---|---|
| 25K | NONE - inert | best 58.7 (flat1; base 61.8) | - | - | - | no size keeps the 62 % floor with the app-faithful leg (the study leg's flat1 = 62.1 % was a +0.3 pt hair above the base) -> `late_contracts` left unset |
| 50K | 2 micros, 1 below cushion $667 (brake2) | 69.7 (66.3) | 51 (61) | 58.2 (56.5) | 56,628 (39,080) | judge holds (+1.7) |
| 100K | 2 micros, 1 below cushion $1,000 (brake2) | 70.5 (71.4) | 69 (87) | 55.7 (65.8) | 74,782 (60,345) | floor margin only 0.5 pt; judge -10 pt (flagged) |
| 150K | 4 micros, 1 below cushion $2,250 (brake4) | 70.6 (74.4) | 64 (80) | 47.8 (57.3) | 129,449 (100,575) | only size at the 70 % floor; judge -9.5 pt (flagged) |

FLAG: the held-out judge pass drops on 100K (-10) and 150K (-9.5); the user accepted that. The leg itself is UNVERIFIED (held-out PF 1.12 study / 1.10 app-faithful, decaying edge).
Median days fall 9-23 on every plan that keeps the floor, pass % also falls 1-4 pt on 100K / 150K (pass % is not the target here).

## Full size tables
### APP-FAITHFUL leg (exit 15:59 bar close, 3R = 180 pt safety target) - what the app trades; picks come from this table

**25K**  (floor 62 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 61.8 | 56.5 | 54.6 | 62.5 | 19,328 | below |
| flat1 | 58.7 | 40 | 47.2 | 64.9 | 27,452 | below |
| flat2 | 45.1 | 25 | 33.8 | 52.7 | 35,578 | below |
| flat3 | 33.7 | 15 | 22.7 | 41.3 | 43,702 | below |
| flat4 | 27.6 | 11 | 18.0 | 36.6 | 51,828 | below |
| brake2 | 45.1 | 25 | 33.8 | 52.7 | 35,578 | below |
| brake3 | 33.7 | 15 | 22.7 | 41.3 | 43,702 | below |
| brake4 | 27.6 | 11 | 18.0 | 36.6 | 51,828 | below |
| brakeH2 | 45.9 | 25 | 35.5 | 54.7 | 35,578 | below |
| brakeH3 | 33.5 | 15 | 24.4 | 39.7 | 43,702 | below |
| brakeH4 | 28.0 | 12 | 19.6 | 35.5 | 51,828 | below |

**50K**  (floor 62 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 66.3 | 61 | 56.5 | 68.2 | 39,080 | ok |
| flat1 | 69.7 | 53 | 59.9 | 71.8 | 47,854 | ok |
| flat2 | 68.5 | 51 | 56.6 | 72.4 | 56,628 | ok |
| flat3 | 57.2 | 38 | 50.1 | 56.7 | 65,402 | below |
| flat4 | 50.1 | 34 | 40.6 | 53.6 | 74,176 | below |
| brake2 | 69.7 | 51 | 58.2 | 73.3 | 56,628 | ok |
| brake3 | 61.1 | 42 | 54.8 | 61.1 | 65,402 | below |
| brake4 | 52.6 | 35 | 41.6 | 59.0 | 74,176 | below |
| brakeH2 | 68.9 | 52 | 57.0 | 73.3 | 56,628 | ok |
| brakeH3 | 60.0 | 42 | 55.5 | 55.8 | 65,402 | below |
| brakeH4 | 55.4 | 36 | 49.9 | 56.9 | 74,176 | below |

**100K**  (floor 70 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 71.4 | 87 | 65.8 | 68.9 | 60,345 | ok |
| flat1 | 66.9 | 76 | 52.5 | 72.0 | 67,564 | below |
| flat2 | 73.0 | 70 | 57.9 | 73.1 | 74,782 | ok |
| flat3 | 66.5 | 64 | 56.9 | 61.4 | 82,000 | below |
| flat4 | 61.7 | 62.5 | 53.9 | 55.9 | 89,219 | below |
| brake2 | 70.5 | 69 | 55.7 | 73.1 | 74,782 | ok |
| brake3 | 63.5 | 66 | 53.9 | 57.6 | 82,000 | below |
| brake4 | 59.3 | 62 | 50.8 | 53.9 | 89,219 | below |
| brakeH2 | 68.9 | 69 | 52.6 | 72.4 | 74,782 | below |
| brakeH3 | 68.5 | 67 | 52.3 | 72.4 | 82,000 | below |
| brakeH4 | 62.0 | 61 | 51.8 | 62.0 | 89,219 | below |

**150K**  (floor 70 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 74.4 | 80 | 57.3 | 72.8 | 100,575 | ok |
| flat1 | 66.5 | 68.5 | 40.4 | 72.9 | 107,794 | below |
| flat2 | 66.4 | 64 | 46.4 | 65.3 | 115,012 | below |
| flat3 | 68.5 | 59 | 52.3 | 63.6 | 122,230 | below |
| flat4 | 66.6 | 57 | 52.6 | 60.1 | 129,449 | below |
| brake2 | 68.1 | 66 | 43.3 | 73.1 | 115,012 | below |
| brake3 | 69.8 | 65 | 46.4 | 73.1 | 122,230 | below |
| brake4 | 70.6 | 64 | 47.8 | 73.3 | 129,449 | ok |
| brakeH2 | 68.1 | 66 | 43.3 | 73.1 | 115,012 | below |
| brakeH3 | 69.8 | 65 | 46.4 | 73.1 | 122,230 | below |
| brakeH4 | 70.6 | 64 | 47.8 | 73.3 | 129,449 | ok |

### STUDY leg (exit 16:00 close, no target; new_edge/scripts/trades_lastmom239.csv)

**25K**  (floor 62 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 61.8 | 56.5 | 54.6 | 62.5 | 19,328 | below |
| flat1 | 62.1 | 41 | 47.9 | 71.8 | 29,204 | ok |
| flat2 | 44.2 | 24 | 31.9 | 55.0 | 39,080 | below |
| flat3 | 35.8 | 17 | 26.4 | 44.8 | 48,957 | below |
| flat4 | 29.6 | 12 | 18.3 | 43.3 | 58,834 | below |
| brake2 | 44.2 | 24 | 31.9 | 55.0 | 39,080 | below |
| brake3 | 35.8 | 17 | 26.4 | 44.8 | 48,957 | below |
| brake4 | 29.6 | 12 | 18.3 | 43.3 | 58,834 | below |
| brakeH2 | 46.6 | 24 | 34.6 | 58.9 | 39,080 | below |
| brakeH3 | 33.5 | 16 | 23.3 | 46.4 | 48,957 | below |
| brakeH4 | 29.9 | 13 | 20.9 | 41.5 | 58,834 | below |

**50K**  (floor 62 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 66.3 | 61 | 56.5 | 68.2 | 39,080 | ok |
| flat1 | 71.2 | 52 | 62.3 | 72.8 | 49,751 | ok |
| flat2 | 67.1 | 48 | 55.2 | 74.0 | 60,422 | ok |
| flat3 | 57.3 | 41 | 47.2 | 62.5 | 71,093 | below |
| flat4 | 51.0 | 34 | 38.9 | 59.4 | 81,764 | below |
| brake2 | 69.7 | 50 | 59.7 | 73.7 | 60,422 | ok |
| brake3 | 57.3 | 40 | 47.5 | 62.7 | 71,093 | below |
| brake4 | 55.3 | 34 | 42.8 | 64.5 | 81,764 | below |
| brakeH2 | 68.8 | 51 | 57.6 | 74.4 | 60,422 | ok |
| brakeH3 | 66.5 | 46 | 55.7 | 72.6 | 71,093 | ok |
| brakeH4 | 60.3 | 40 | 50.4 | 69.5 | 81,764 | below |

**100K**  (floor 70 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 71.4 | 87 | 65.8 | 68.9 | 60,345 | ok |
| flat1 | 68.0 | 75 | 54.2 | 72.2 | 69,323 | below |
| flat2 | 73.8 | 70 | 60.7 | 73.1 | 78,301 | ok |
| flat3 | 69.1 | 64 | 53.0 | 75.3 | 87,279 | below |
| flat4 | 57.8 | 59 | 47.9 | 58.1 | 96,257 | below |
| brake2 | 70.2 | 68 | 55.2 | 73.1 | 78,301 | ok |
| brake3 | 66.2 | 66 | 53.3 | 69.3 | 87,279 | below |
| brake4 | 57.3 | 58 | 51.3 | 55.6 | 96,257 | below |
| brakeH2 | 69.5 | 68 | 53.8 | 73.1 | 78,301 | below |
| brakeH3 | 68.5 | 66 | 52.9 | 73.1 | 87,279 | below |
| brakeH4 | 67.0 | 61 | 51.9 | 74.4 | 96,257 | below |

**150K**  (floor 70 % pass)

| late leg | pass % ALL | median days | judge pass % | pick pass % | profit $ (5y, 1 acct) | floor |
|---|---|---|---|---|---|---|
| no late leg (D163 base) | 74.4 | 80 | 57.3 | 72.8 | 100,575 | ok |
| flat1 | 67.4 | 68 | 42.1 | 73.1 | 109,553 | below |
| flat2 | 71.0 | 66 | 48.5 | 73.1 | 118,531 | ok |
| flat3 | 69.5 | 60 | 52.6 | 65.8 | 127,509 | below |
| flat4 | 68.5 | 60 | 52.8 | 69.7 | 136,487 | below |
| brake2 | 69.0 | 67 | 45.0 | 73.1 | 118,531 | below |
| brake3 | 72.3 | 66 | 50.8 | 73.1 | 127,509 | ok |
| brake4 | 72.7 | 64 | 51.5 | 73.7 | 136,487 | ok |
| brakeH2 | 69.0 | 67 | 45.0 | 73.1 | 118,531 | below |
| brakeH3 | 72.3 | 66 | 50.8 | 73.1 | 127,509 | ok |
| brakeH4 | 72.7 | 64 | 51.5 | 73.7 | 136,487 | ok |

## What the build trades (differences to the study, both measured above)
- exit on the 15:59 bar close (study: 16:00 close) and a safety target at 3R = 180 pt (study: none) because every bracket needs one: judge PF 1.12 -> 1.10, pick 1.50 -> 1.44.
- sizes per plan in `config/rules/lucid_pro_*k.yaml` `fast_pass_*_cfg.late_contracts` / `late_steps`; 25K unset (inert).
- Reproduce: `cd backend && PYTHONPATH=. python3 ../docs/results/new_edge/late_leg_sizes/run_sizes.py` (study leg) / `LATE_VARIANT=app ...` (after `app_variant.py`). Data: days.pkl (MNQ RTH 1-min, 2021-10..2026-10).
- Not modelled: the cross-account HEDGE_LOCK (the sim is one account; all legs are the same instrument and the lock only skips); the Lucid payout/consistency cap after the pass.
