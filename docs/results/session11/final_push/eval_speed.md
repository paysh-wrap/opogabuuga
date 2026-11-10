# Eval speed / pass-rate study under the LIVE rules (session 11 final push, 2026-11-10)

Scripts: `eval_speed_engine.py` (engine; defaults reproduce `pm_fade_d57_study.py` exactly: 25K 56.2 / 25K-HR 35.2 / 50K 53.0 /
100K 61.9 / 150K 57.4 % pass, 0% bust) and `eval_speed_run.py stage1|stage2|stage3` (grids → `eval_speed_stage*.json`, full tables on stdout).
Data: MNQ 1-min 2021-11..2026-10, rolling starts every 2 sessions, horizon 120 (25K/50K) / 250 (100K/150K) sessions.
IS = starts 2021-11..2023-12 (n=283), OOS = starts 2024-01.. (n=310 / 245). Cells: pass / bust / frozen / still-open %, median sessions
of passers, **spp** = sessions consumed by all attempts per pass (speed incl. failures).
Pass rule: bust not higher on either half AND (pass% ≥ +3 pts on both, OR spp ≥ 10% lower on both with pass% not down > 3 pts).

## Headline
- **Almost nothing in the requested list passes.** Baseline is unchanged for 25K Regular, 50K, 100K, 150K on the strategy side.
- Bust stayed 0.0% in EVERY variant, including relaxed shrink / min-stop. That is a property of the simulator (stops fill at the stop
  ±1 tick, $50 kill distance), NOT evidence the relaxed safety rules are safe: gaps / fast-market slippage are not modelled.
  "Frozen" is the real failure mode and economically equals a bust (reset fee).
- New operational lever (not in the brief): **reset a frozen account at once** instead of waiting. Pass% is identical, sessions per pass
  drop. Thresholds where IS pass% is untouched: 25K cushion < $150 (15% MLL), 100K < $300 (10%), 150K < $225 (5%), 50K none (even 10% costs 7 pts IS:
  deep 50K/100K/150K accounts DO recover in 2022-23).
- 25K High-risk is the only plan with real gains: recover-mode (drop to fewer micros when 3 do not fit) +4.6 / +6.2 pts.

## Stage 1 singles (IS | OOS) — pass / bust / frozen / open, median, spp
| Plan | Variant | IS | OOS | verdict |
|---|---|---|---|---|
| 25K | BASE | 66.1/0/33.2/0.7 · 40 · 76.6 | 47.1/0/52.9/0 · 27 · 82.0 | — |
| 25K | 30-min checks (±5 entries) | 52.3/0/37.8/9.9 · 30 · 98.1 | 33.9/0/66.1/0 · 32 · 116.9 | FAIL (−14 / −13) |
| 25K | 5 entries/day | 66.1 · 76.6 | 48.1 · 79.8 | no effect |
| 25K | opening-drive | 66.1/0/32.5/1.4 · 40 · 76.7 | 52.9/0/47.1/0 · 25 · 68.6 | fail (OOS only) |
| 25K | $100/$125/$150 tier when frozen, recover | = base | = base | no effect |
| 25K | shrink 0.7 / 0.8 | 69.3 · 73.6 / 55.5 · 86.0 | 46.8 · 83.4 / 44.8 · 85.2 | fail |
| 25K | min-stop 0.15% / 0.10% | 66.1 · 79.3 | 47.1 / 47.4 | no effect |
| 25K | front 2 micros at peak (= prop $500) | 54.1/0/45.9/0 · 33 · 70.8 | 44.8/0/54.8 · 19 · 77.0 | fail (−12 IS) |
| 25K | front 3 at peak | 38.2 · 11 · 99.1 | 34.8 · 11.5 · 92.9 | FAIL |
| 25K-HR | BASE | 38.9/0/61.1/0 · 10 · 55.0 | 31.9/0/68.1/0 · 7 · 63.8 | — |
| 25K-HR | recover-mode | 43.5/0/56.5 · 11 · 51.9 | 38.1/0/61.9 · 8 · 58.5 | **PASS** |
| 25K-HR | min-stop 0.10% | 42.0 · 51.6 | 36.5 · 58.8 | PASS (safety rule) |
| 25K-HR | shrink 0.8 (+min 0.10%) | 43.1 · 48.6 | 34.5 (36.8) · 59.0 | borderline (safety rule) |
| 25K-HR | 30-min checks | 44.2 · 45.4 | 31.9 · 61.9 | fail (IS only) |
| 50K | BASE | 59.4/0/27.2/13.4 · 52.5 · 116.3 | 47.1/0/45.5/7.4 · 37.5 · 118.4 | — |
| 50K | 30-min (+5) | 54.4 · 38 · 121.7 | 49.0 · 47.5 · 104.8 | fail |
| 50K | opening-drive | 51.9 · 131.8 | 53.2 · 97.2 | fail (IS −7.5) |
| 50K | shrink 0.7 / 0.8 | 62.2 · 106.9 / 104.4 | 48.4 · 110.8 / 108.4 | fail (+2.8 / +1.3 = noise; spp −8%) |
| 50K | min-stop 0.10% | 59.4 | 51.0 | fail |
| 50K | front 3 / 4 at peak | 54.1 · 46 / 50.2 · 45.5 | 43.9 · 29.5 / 45.2 · 29 | fail (faster passers, fewer of them) |
| 50K | cushion-proportional ($500–$1000 per micro) | 28.6–45.6 | 39.4–46.1 | FAIL |
| 100K | BASE | 67.8/0/27.9/4.2 · 99 · 182.0 | 55.1/0/44.9/0 · 72 · 140.1 | — |
| 100K | 30-min + 5 + opening-drive | 82.3/0/16.6/1.1 · 115 · 143.6 | 53.5/0/46.5/0 · 60 · 128.2 | fail (IS only; spp −21% / −8.5%) |
| 100K | shrink 0.7 | 72.1 · 161.6 | 55.1 · 140.5 | fail (IS only) |
| 100K | front 3/4/6 at peak, prop | 58.0–68.6 | 51.4–55.5 | fail |
| 150K | BASE | 62.2/0/33.6/4.2 · 79 · 175.0 | 51.8/0/48.2/0 · 70 · 143.6 | — |
| 150K | 30-min checks | 77.0 · 115 · 148.7 | 53.1 · 79 · 138.2 | fail (IS only) |
| 150K | opening-drive | 63.3 · 168.8 | 58.8 · 63.5 · 120.7 | fail (OOS only) |
| 150K | 30-min + 5 + opening-drive | 80.9/0/15.5/3.5 · 119 · 142.9 | 53.1/0/46.9/0 · 69.5 · 140.5 | fail (IS only) |
| 150K | recover-mode | 55.1 · 197.9 | 51.8 · 166.6 | FAIL |
| 150K | front 5/6/8 at peak; prop $750–$1125 | 52.7–71.7 (prop: 28–37% still open) | 48.6–54.3 | fail |
| all | fade under D57 | −1.4 … −8.5 IS | ≈ 0 | fail |
| all | day cap 35% of target | = base | = base | no effect (no day reaches it) |

Consistency (4): the Pro eval yaml has `consistency_max_day_pct: null` (no rule; pass possible in one day). IF Lucid applied 40% to the eval:
25K 64.7 / 42.3, 25K-HR 30.0 / 22.3 (median 38 / 35 sessions instead of 10 / 7), 50K 59.4 / 43.9, 100K 67.8 / 51.8, 150K 62.2 / 49.8 —
and a 35% or 25% day cap recovers none of it (≤ +0.6 pt). Verify the Pro eval consistency rule with Lucid; it matters only for 25K-HR.

## Stage 2/3 combos (IS | OOS)
| Plan | Recipe | IS | OOS | verdict |
|---|---|---|---|---|
| 25K | reset when cushion < 15% MLL | 66.1 · spp 69.8 | 47.1 · spp 71.6 | PASS (same passes, −9% / −13% sessions) |
| 25K | opening-drive + shrink 0.7 + reset<15% | 68.6 · 65.5 | 52.6 · 57.7 | passes on spp only; pass% +2.5 IS = noise; needs OD on EVAL + a safety-rule change |
| 25K-HR | recover + reset<15% | 43.5 · 11 · 27.0 | 38.1 · 8 · 35.8 | **PASS** |
| 25K-HR | recover + reset<20% | 42.8 · 25.4 | 37.4 · 26.8 | **PASS** (spp −54% / −58%) |
| 25K-HR | recover, 2 micros × $250, reset<15% | 47.0 · 19 · 34.5 | 41.0 · 13 · 46.9 | PASS (highest pass%, slower) |
| 25K-HR | recover + opening-drive + reset<15% | 44.5 · 25.8 | 41.0 · 33.8 | PASS (OD adds +1 / +3 = noise) |
| 25K-HR | recover + 30-min + reset<15% | 50.5 · 23.9 | 37.4 · 41.0 | PASS, but 30-min gain is IS only |
| 50K | reset<10% | 52.3 · 108.9 | 47.1 · 99.7 | fail (−7 IS) |
| 50K | opening-drive + shrink 0.7 | 61.5 · 106.1 | 54.8 · 90.8 | fail (+2.1 IS = noise; spp −9% IS) |
| 100K | reset<10% | 67.8 · 169.1 | 55.1 · 120.7 | PASS (same passes, −7% / −14% sessions) |
| 100K | 30-min+5+OD + reset<10% | 71.0 · 79 · 139.8 | 53.5 · 60 · 107.5 | PASS on spp (−23% both); pass% +3.2 / −1.6 |
| 150K | reset<5% | 62.2 · 168.2 | 51.8 · 138.3 | same passes, −4% sessions |
| 150K | 30-min+5+OD + reset<10% | 80.9 · 119 · 132.1 | 53.1 · 69.5 · 115.9 | PASS on spp (−25% / −19%); pass% +18.7 / +1.3 |

## Best recipe per plan
- **25K Regular**: keep live rules. Add "reset when EOD cushion < $150" (identical pass%, ~10% fewer sessions per pass). Nothing else.
- **25K High-risk**: add recover-mode (fewer micros when 3 × $150 does not fit) + reset when cushion < $150–$200:
  pass 38.9 / 31.9 → 43.5 / 38.1, sessions per pass 55 / 64 → 27 / 36. Still far more resets per pass than Regular (2.4 vs 1.8 evals)
  but ~half the calendar time. Alternative 2 × $250 + recover: 47 / 41 % pass, median 19 / 13.
- **50K**: keep live rules. No lever passes (best candidate OD + shrink 0.7 is within noise in-sample).
- **100K**: keep live sizing; reset when cushion < $300. Optional (weaker evidence, per-stage signals needed): 30-min + 5 entries + opening-drive.
- **150K**: keep live sizing (4, brake → 2); reset when cushion < $225. Optional as for 100K (+ reset < $450).
- Do NOT: front-load size, cushion-proportional size, $100–$150 frozen tier, fade under D57, day cap, 30-min checks on 25K/50K.

## Caveats
- Rolling starts overlap heavily; IS and OOS disagree in sign for most "extras" (30-min: big IS gain on 100K/150K, loss on 25K/50K) → regime noise.
- IS starts late in 2023 run into 2024 bars (same convention as earlier studies).
- Opening-drive = `od_t` from session10/five_year/run_b.py, with pause floor + structural stop, one position at a time; it is PAPER-only (D55).
- Reset thresholds were read off both halves; only "pass% identical" thresholds are recommended, which is dominance rather than a tuned edge.
- Nothing in backend/app or config was changed.
