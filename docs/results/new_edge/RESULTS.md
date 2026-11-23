# new_edge: search for a third, uncorrelated intraday leg (research only, 2026-11-23)

## Verdict
No candidate clears the full bar (PF > 1.2 held-out, beats random, >= 60 trades, strictly faster on every plan without cutting profit).
Best lead: **late-day momentum** (hold the sign of the 09:30-13:29 trend from 15:00 to the close). Real but decaying edge, daily-P&L correlation
0.11 with NOISE+CANDACE, and it speeds up every plan in the eval sim. It fails the held-out PF gate (1.12 < 1.2) and the judge rule on 3 of 4 plans.
Do not build it; re-test when overnight and MGC data are available.

## Limits of this run
- Data in the sandbox: MNQ RTH 1-min bars only (days.pkl, 2021-10-21..2026-10-30; the pick window therefore starts 2021-10, not 2019). No MGC, no MES, no overnight session, no Databento key.
  So **MGC noise-area momentum, MGC/MES variants, overnight-return momentum and pre-FOMC drift were NOT tested** (FOMC dates are not in the repo either).
- Costs: $2 per micro round trip ($1 fee + 1 tick slippage each way). Entry at the open of the bar after the signal bar; stop checked first when both hit. Pick 2021-10..2023-12, judge 2024-01..2026-10.
- All ideas trade MNQ, so the equity-index hedge lock (rule 7) applies against NOISE/CANDACE; the sim keeps one position per account (a leg is skipped while another is open).

## Screen (MNQ, 6 ideas, 328 configs; "pass both" = pick PF > 1.2 AND judge PF > 1.2 AND judge n >= 60)
| idea | configs | pass both | best-by-pick: judge PF (n) | random-direction judge PF p95 |
|---|---|---|---|---|
| first-30-min return (+gap) -> last 30 min | 24 | 0 | 1.08 (705) | 1.06-1.2 |
| trend-so-far -> last 30-60 min (late-day momentum) | 60 | 0 | 1.12 (602), pick 1.50 | 1.13 |
| gap continuation / fade (0.3-0.8 ATR) | 96 | 2 (same trade set, 120 trades) | 1.38 (120), pick n = 40 | 1.5 |
| afternoon VWAP reversion | 48 | 0 | 0.95-1.16 | 1.0-1.3 |
| lunch-range breakout | 64 | 0 | 0.68 (pick 1.55 collapses) | 1.2 |
| turn of month (long open-close) | 6 | 0 | 1.0-1.07 | 1.5 |

A first run of "trend to 15:29, enter 15:00" showed PF 2.4: a lookahead bug (signal bar after the entry). Fixed and guarded in code.
Gap continuation: 2 of 96 passing is chance level, it does not beat the random-direction p95, and the pick window holds only 35-40 trades.

## Late-day momentum lead (ref bar 239 = 13:29, min move 0.1 x 14-day avg range, enter 15:00, stop 60 pt, flat 15:59)
The neighbourhood is a smooth plateau (ref 209-269, stop 45-90: pick PF 1.28-1.60, judge 1.02-1.13), so it is not one lucky cell, but it decays out of sample.

| window | trades | PF | win % | net $/micro |
|---|---|---|---|---|
| pick 2021-23 | 465 | 1.50 | 53.1 | 7,756 |
| judge 2024-26 | 602 | 1.12 | 47.7 | 3,198 |

Daily-P&L correlation (5y, $/micro/day): vs NOISE 0.117, vs CANDACE -0.017, vs NOISE+CANDACE 0.109. 28% of its trades overlap a NOISE/CANDACE position in time; 57% fall on days they also trade.

Eval sim with the leg added as a fixed-size third leg (the sim's GALA slot, same $125 per-micro cap). Base rows reproduce exactly: 25K 61.8 %/56.5 d, 50K 66.3 %/62 d, 100K 71.4 %/87 d, 150K 76.4 %/82 d (the D163 74.4 %/80 d CANDACE-grow variant was not rebuilt).

| plan | base: pass % / med d / judge / pick / profit | + leg: pass % / med d / judge / pick / profit | rule check |
|---|---|---|---|
| 25K | 61.8 / 56.5 / 54.6 / 62.5 / $19.3K | 1 micro: 62.1 / 41 / 47.9 / 71.8 / $29.2K | faster, floor ok, profit up; judge -6.7 fails judge rule |
| 50K | 66.3 / 62 / 56.5 / 68.2 / $39.1K | 1 micro: 71.2 / 51 / 62.3 / 72.8 / $49.8K | passes every rule |
| 100K | 71.4 / 87 / 65.8 / 68.9 / $60.3K | 2 micros: 73.8 / 70 / 60.7 / 73.1 / $78.3K | faster, profit up; judge -5.1 fails judge rule |
| 150K | 76.4 / 82 / 58.0 / 72.8 / $100.6K | 2 micros: 71.2 / 65 / 48.9 / 73.1 / $118.5K (1 micro: 69.6 / 70) | judge -9 fails; 1 micro under the 70 % floor |

The speed-up is mostly extra expected profit from a weakly positive leg; the judge columns show the cost. The 50K row is the only strict pass and rests on a PF 1.12 held-out edge, so treat it as unproven.
Gap continuation as a third leg lowers pass % on every plan (100K 63.5 %, 150K 66.9 % at 1 micro); rejected.

## Next steps (need data or approval, nothing built)
1. Get MGC.v.0 and MNQ/MES with overnight bars (Databento key) and test MGC noise-area momentum and the full Gao/Han/Li/Zhou overnight + first-30-min predictor. MGC sits outside the equity hedge lock.
2. If late-day momentum is revisited: re-judge on 2025-26 only, 50K only, 1 micro.

Files: scripts/{lib_ne,research,survivors,run_leg,make_results_json}.py, scripts/trades_*.csv, scripts/leg_*.json, results.json.
