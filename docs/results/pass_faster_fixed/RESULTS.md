# Fixed-size NOISE + CANDACE (25K: 1+1 micro, 50K: 1 NOISE + 2 CANDACE micros) - research only

No app/config/frontend change, nothing committed. Full tables: `tables.md`; raw: `results.json`; code: `run_fixed.py` (account loop), `report.py`. Builds on `../pass_faster/pf_sim.py` (NOISE sizing/shrink/room check, kill distance, STUCK rule, rolling-start protocol) and `../pass_faster_c125/` (streams, D154 CANDACE 09:30-10:00).

## Reproduction
`run_fixed.py check`: BASE and C125_1 on 25K (5y and judge) re-run with the study code match `pass_faster_c125/results.json` exactly. The new account loop (open positions realise P&L at their exit) also reproduces C125_1 exactly when run as variant A on 25K (pass 49.5 / stuck 45.3 / median 48 / plan-sized $21,501): A on 25K == C125_1.

## Sizes / rules as implemented
NOISE: 1 micro, $250 stop, shipped D57 shrink + room check (no brake, no size table). CANDACE: 25K 1 micro, 50K 2 micros; per-micro risk (stop $ + fee + slippage) never exceeded $125 on any of the 304 signals. A CANDACE trade is sized down to fit, else skipped, if combined worst case + $40 margin does not fit MLL room (minus kill distance) or DLL left; this never triggered in the static replay and nothing was shrunk. DLL incl. LucidScale, trailing EOD MLL + lock, 40% consistency + 38% day stop (trade capped, day ends), kill distance, STUCK = NOISE cannot be sized (as BASE).
- Variant A: one position at a time (the other strategy's signal is skipped).
- Variant B: both at once, same direction nets (<=2 micros on 25K, <=3 on 50K), opposite direction skipped ("hedge"), combined worst case must fit room.
- Simplifications: when the day stop/DLL hits, any other open position is dropped (flatten). CANDACE room uses bal-floor-kd (the older sim double-counted today's P&L in that room; with fixed small sizes it does not bind, confirmed by the exact match above).

## Rows (rolling starts; all non-passing accounts are "stuck", bust 0%)
| plan | window | row | pass % | stuck % | run % | median / p75 d | <=60 d % | profit $ | worst DD $ | trades/wk |
|---|---|---|---|---|---|---|---|---|---|---|
| 25K | 5y | BASE (= 1 micro NOISE) | 58.6 | 35.9 | 5.5 | 74 / 122 | 23.0 | 19,293 | 2,096 | 2.6 |
| 25K | 5y | C125_1 (earlier) | 49.5 | 45.3 | 5.2 | 48 / 72 | 31.5 | 21,501 | 1,967 | 3.8 |
| 25K | 5y | A | 49.5 | 45.3 | 5.2 | 48 / 72 | 31.5 | 21,501 | 1,967 | 3.8 |
| 25K | 5y | B | 49.4 | 45.4 | 5.2 | 48 / 72 | 31.3 | 21,252 | 1,967 | 3.8 |
| 25K | judge | BASE | 38.6 | 51.6 | 9.8 | 50 / 73 | 23.7 | 10,826 | 2,096 | 2.5 |
| 25K | judge | A (= C125_1) | 40.6 | 50.2 | 9.2 | 47 / 71 | 26.1 | 11,788 | 1,967 | 3.5 |
| 25K | judge | B | 40.3 | 50.5 | 9.2 | 47 / 71 | 25.7 | 11,538 | 1,967 | 3.5 |
| 25K | pick | BASE | 58.9 | 15.5 | 25.6 | 74 / 103 | 22.1 | 8,468 | 944 | 2.7 |
| 25K | pick | A / B | 57.2 | 30.3 | 12.4 | 47 / 69 | 38.6 | 9,714 | 980 | 4.0 |
| 50K | 5y | BASE (2 micros + brake) | 68.8 | 21.4 | 9.7 | 92 / 132 | 19.7 | 38,586 | 4,193 | 2.6 |
| 50K | 5y | NOISE 1 micro alone | 76.1 | 12.9 | 10.9 | 148 / 212 | 5.8 | 19,293 | 2,096 | 2.6 |
| 50K | 5y | A | 80.7 | 9.7 | 9.6 | 121 / 173 | 5.7 | 23,348 | 2,087 | 3.8 |
| 50K | 5y | B | 80.0 | 10.4 | 9.6 | 121 / 179 | 5.7 | 23,099 | 2,087 | 3.8 |
| 50K | judge | BASE | 55.3 | 27.4 | 17.3 | 83 / 123 | 19.0 | 21,651 | 4,193 | 2.5 |
| 50K | judge | NOISE 1 micro | 57.6 | 23.0 | 19.4 | 131 / 170 | 3.8 | 10,826 | 2,096 | 2.5 |
| 50K | judge | A | 65.7 | 17.3 | 17.0 | 125 / 150 | 2.8 | 12,601 | 2,087 | 3.5 |
| 50K | judge | B | 64.5 | 18.4 | 17.0 | 126 / 154 | 2.8 | 12,352 | 2,087 | 3.5 |
| 50K | pick | BASE | 73.1 | 0.0 | 26.9 | 86 / 118 | 20.7 | 16,935 | 1,888 | 2.7 |
| 50K | pick | NOISE 1 micro | 65.1 | 0.0 | 34.9 | 137 / 179 | 8.2 | 8,468 | 944 | 2.7 |
| 50K | pick | A / B | 64.0 | 0.0 | 36.0 | 93 / 113 | 9.3 | 10,748 | 1,128 | 4.0 |

Profit / drawdown / trades per week are fresh-account static replays at plan sizes (BASE without brake/shrink there); trade counts are the same on 25K and 50K because sizes never bind on a fresh account.

## CANDACE / NOISE trades taken and skipped (static, 5y; judge in brackets)
- Signals: NOISE 654 (356), CANDACE 304 (150).
- A: NOISE taken 638 (349), skipped 16 (7) "CANDACE position open"; CANDACE taken 303 (150), skipped 1 (0) "NOISE position open". No size skips, no resizing, no signal above $125 per micro.
- B: NOISE taken 639 (350), skipped 15 (6) as OPPOSITE direction to an open CANDACE trade (hedge); CANDACE 303 (150), 1 (0) hedge skip. Holding both at once changes only about one trade versus A, so B adds essentially nothing (and is marginally worse: 25K 5y profit -$250, pass -0.1 pt; 50K judge pass -1.2 pts).
- Balance-dependent skips inside the rolling runs are not counted separately.

## Verdict (judge AND 5y on the plan; pass % higher OR passed<=60 higher; stuck not > BASE+2 pts; profit not lower than BASE)
| plan | variant | judge | 5y | failing criterion |
|---|---|---|---|---|
| 25K | A | PASS (pass +2.0, <=60d +2.4, stuck -1.4, profit +$962) | FAIL (pass -9.1 but <=60d +8.5; stuck +9.4) | stuck (5y) |
| 25K | B | PASS (+1.7, +2.0, -1.1, +$712) | FAIL (stuck +9.6) | stuck (5y) |
| 50K | A | FAIL (pass +10.4, <=60d -16.2, stuck -10.1, profit -$9,050) | FAIL (pass +11.8, <=60d -14.1, stuck -11.7, profit -$15,238) | profit |
| 50K | B | FAIL (profit -$9,300) | FAIL (profit -$15,487) | profit |
| 50K | NOISE 1 micro alone (ref) | FAIL profit | FAIL profit | profit |

**Nothing is worth building under the binding rules.**
- 25K: A is identical to the earlier C125_1. Better over the last 33 months, but 5y stuck is +9.4 pts above BASE (pick window 30% vs 16%). B gives nothing over A.
- 50K: the fixed 1 NOISE + 2 CANDACE split cuts profit versus the shipped 2-micro NOISE (-$15k plan-sized over 5y, -$9k judge) and is much slower (median 121 d vs 92; passed within 60 days 5.7% vs 19.7%), although more accounts pass in the long run (80.7% vs 68.8%, stuck 9.7% vs 21.4%) because the smaller size keeps accounts out of the kill zone. That is a safety/pass-rate gain bought with profit and speed, which the profit rule forbids recommending. NOISE at 1 micro alone shows the same pattern, so the gain comes from smaller size, not from CANDACE. Pick window: pass 64.0% vs 73.1% (worse).
- B (both at once) needs a change to non-negotiable 7 and is not better than A on either plan, so there is no reason to ask for that change.

Multiple testing: this adds 2 variants x 2 plans to the earlier C125/LOCK80/VWAP tests on the same 5-year MNQ sample; rolling starts overlap heavily (about 20 independent evaluation lengths) and the judge window has been seen many times, so differences of 2-4 pts are within noise.
