# Refine round 2 (2026-11-24, research only; no app code changed, nothing pushed)
Scope cut by the coordinator (usage limit): ideas 1, 3, 6 run; ideas 2, 4, 5 NOT RUN.
Scripts/data: `run_r2.py` (reuses held_out_tests/hot_lib.py gen2), `results_r2.json`.

## Baseline reproduction
NOISE shipped: 654 trades, $19,293 (asserted trade-count and net). Pick 298 / PF 1.55 / $8,468. Judge 356 / PF 1.50 / $10,826.
Rules: pick 2021-10-21..2023-12-31, judge 2024-01-01..2026-10-30, $2/micro RT, pass = judge net AND PF beat base, >=60 trades, beats random-direction control (60 seeds, judge p95).

## Pre-registration
| idea | variants | pick rule | control |
|---|---|---|---|
| 1 | lock trigger {60,80,100,120,140} x locked offset {0,10,20,30} (19 variants, shipped 100/10 excluded) | pick PF >= base AND pick net >= base; highest pick net | judge net and PF above p95 of random-direction run of the pick (60 seeds) |
| 3 | stop $150/200/250/300 per micro (250 = shipped) | same | same |
| 6 | early-close days listed from data | n/a | n/a |

## Pick vs judge (1 micro; trades / PF / net)
| variant | pick | judge |
|---|---|---|
| base (L100/10, S250) | 298 / 1.55 / 8,468 | 356 / 1.50 / 10,826 |
| **idea 1 pick: L120/10** | 300 / 1.55 / 8,746 | 360 / 1.45 / 10,375 |
| idea 3 stop variants | S150 307/1.49/7,765; S200 300/1.55/8,302; S300 298/1.48/7,736 | S150 386/1.43/9,600; S200 368/1.42/9,523; S300 354/1.48/10,702 |
No stop variant passed the pick rule (S250 is the shipped one), so idea 3 has no pick. Judge numbers are shown for information only: all three are below shipped on net and PF.
Other idea 1 grid (pick/judge net): L80/10 7,960/11,674 (pick below base, so not eligible; judge looks higher, which is the kind of post-hoc result this protocol exists to ignore), L140/30 8,608/9,964, L120/0 8,567/10,149.

## Random control
Random-direction p95 on judge: net about $6,291-6,401, PF about 1.22. L120/10 clears the control (the NOISE edge is real), but fails the base comparison: judge net -$451 and PF 1.45 < 1.50.

## Variants tried
Idea 1: 19. Idea 3: 3 (plus shipped). Total 22 NEW variants. At 22 tries, about 2 false wins at 10 % are expected; none passed.

## Idea 6 (half-day proxy): CANNOT BE MEASURED FROM THIS DATA
days.pkl has 1,266 days, every one with 390 bars with no NaN. All known early-close days (2021-11-26, 2021-12-24, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) are ABSENT from the file. So the backtest never traded them, there are no short sessions, and the open-at-last-bar count is 0 by construction. This sizes nothing about the live early-close bug. Needs half-day bars from another source (Databento is off) or a synthetic test of the app flat-time logic.

## Verdicts
| idea | verdict |
|---|---|
| 1 lock level/offset | REJECT (pick L120/10, judge net and PF below base; plateau is flat, all within noise) |
| 2 time-of-day cutoff | NOT RUN |
| 3 stop distance | REJECT (no variant beats shipped $250 on pick; judge also lower for all) |
| 4 CANDACE grade sizing | NOT RUN |
| 5 CANDACE news blackout/window | NOT RUN |
| 6 half-day proxy | INCONCLUSIVE (data contains no early-close days) |
Nothing is adopted. Keep shipped settings.
