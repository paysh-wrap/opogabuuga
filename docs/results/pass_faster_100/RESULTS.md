# $100-per-contract NOISE + CANDACE (25K/50K: 2+1 micros; 100K/150K double size: 4+2) - research only

No app/config/frontend change, nothing committed. Full tables (every window, skip counts, verdict cells): `tables.md`; raw `results.json`; code `gen_stop100.py` (NOISE stream), `run_100.py` (rows), `report.py`. Builds on `../pass_faster_fixed/run_fixed.py` (account loop, unchanged), `../pass_faster/pf_sim.py` (sizing/shrink/room check/kill distance/STUCK rule), `../pass_faster_c125/`.

## Interpretation
- NOISE: shipped generator (`session20 noise3.gen`: preset C lock +100pt -> entry+10, Mondays off, fade off, hourly checks, band/VWAP exits) re-run with `stop_usd=100` = 49 pt hard stop, risk per micro exactly $100 (stop $98 + fee $1 + slippage $1). The same generator at $250 reproduces the shipped stream exactly (654 trades, identical P&L). The $100 stop gives 740 trades (more re-entries after earlier stop-outs).
- CANDACE: 1 micro (2 on 100K/150K), per-micro risk cap $100 (stop $ + fee + slippage). All 304 signals fit (max stop-based risk is below $100), so 0 skipped for the cap.
- Same sizes on 25K and 50K (2 NOISE + 1 CANDACE); 100K and 150K double (4 + 2). All Lucid rules in the sim and only shrinking/skipping: DLL (incl. LucidScale), trailing EOD MLL + lock, kill distance, room check (D57 shrink), 40% consistency + 38% day stop, flat by close, never hedge.
- A: one position at a time. B: both at once; same direction nets, opposite direction is skipped (never hedge), combined worst case must fit room.
- Rows: BASE = shipped size table (25K 1 micro; 50K 2 + brake; 100K 2 + brake; 150K 3 + brake, $250 stop), NOISE@$100 alone (same micros as A/B, no CANDACE), A, B. Windows: 5y rolling starts, judge 2024-01..2026-10, pick 2021-10..2023-12.

## Reproduction
- 25K and 50K BASE (5y and judge) match `pass_faster_fixed/results.json` exactly (pass and stuck identical).
- 100K BASE 5y: pass 77.7 % (target 77, within 2 pts); 150K: 77.1 % (target 78, within 2). The eval_odds figures list bust = stuck 18 / 14; this rolling-start sim gives stuck 11.3 / 10.5 (and 10.9 / 12.5 % still running), different protocol, so only pass % is compared. In this sim "bust" is always 0; non-passing accounts are stuck (cannot size NOISE) or still running.

## Key table (5y rolling; judge window in tables.md)
| plan | row | pass % | stuck % | run % | median / p75 d | <=60 d % | plan-sized profit $ | worst DD $ | trades/wk |
|---|---|---|---|---|---|---|---|---|---|
| 25K | BASE | 58.6 | 35.9 | 5.5 | 74 / 122 | 23.0 | 19,293 | 2,096 | 2.6 |
| 25K | NOISE-2@$100 | 32.9 | 39.6 | 27.5 | 29 / 40 | 30.4 | 35,251 | 3,404 | 3.0 |
| 25K | A | 34.0 | 63.2 | 2.8 | 28 / 37 | 33.1 | 38,382 | 3,157 | 4.1 |
| 25K | B | 34.0 | 63.2 | 2.8 | 28 / 37 | 33.1 | 38,184 | 3,157 | 4.1 |
| 50K | BASE | 68.8 | 21.4 | 9.7 | 92 / 132 | 19.7 | 38,586 | 4,193 | 2.6 |
| 50K | NOISE-2@$100 | 66.1 | 7.2 | 26.7 | 79 / 142 | 21.2 | 35,251 | 3,404 | 3.0 |
| 50K | A | 59.1 | 30.6 | 10.3 | 67 / 107 | 25.5 | 38,382 | 3,157 | 4.1 |
| 50K | B | 58.6 | 31.1 | 10.3 | 67 / 108 | 25.5 | 38,184 | 3,157 | 4.1 |
| 100K | BASE | 77.7 | 11.3 | 10.9 | 152 / 218 | 5.8 | 38,586 | 4,193 | 2.6 |
| 100K | NOISE-4@$100 | 45.4 | 2.6 | 52.0 | 63 / 83 | 21.2 | 70,502 | 6,808 | 3.0 |
| 100K | A | 51.9 | 34.0 | 14.1 | 62 / 92 | 25.5 | 76,765 | 6,314 | 4.1 |
| 100K | B | 51.4 | 34.5 | 14.1 | 61 / 91 | 25.5 | 76,367 | 6,314 | 4.1 |
| 150K | BASE | 77.1 | 10.5 | 12.5 | 159 / 221 | 5.8 | 57,879 | 6,290 | 2.6 |
| 150K | NOISE-4@$100 | 69.7 | 0.0 | 30.3 | 110 / 169 | 8.0 | 70,502 | 6,808 | 3.0 |
| 150K | A | 73.9 | 16.0 | 10.1 | 105 / 163 | 8.9 | 76,765 | 6,314 | 4.1 |
| 150K | B | 73.5 | 16.4 | 10.1 | 105 / 163 | 8.9 | 76,367 | 6,314 | 4.1 |

Judge window pass / stuck / <=60 d (BASE -> A): 25K 38.6/51.6/23.7 -> 22.8/72.2/22.6; 50K 55.3/27.4/19.0 -> 48.9/32.8/22.4; 100K 60.4/20.1/3.8 -> 44.7/30.4/22.4; 150K 59.3/18.6/3.8 -> 64.3/17.7/6.7.

Profit and drawdown are fresh-account static replays at the row's own size (BASE without brake/shrink there); "worst DD" is closed-trade drawdown with no account rules, so it can exceed the plan's MLL (25K: $1,000) - in the rolling runs the kill switch / room check / shrink act on it. Trades per week are the same across plans (sizes never bind on a fresh account).

## NOISE with the $100 stop vs $250 (per micro, generator level)
| window | stop | trades | win % | PF | net $ per micro |
|---|---|---|---|---|---|
| 5y | $250 | 654 | 51.4 | 1.52 | 19,293 |
| 5y | $100 | 740 | 43.4 | 1.49 | 17,626 |
| judge | $250 | 356 | 54.2 | 1.49 | 10,826 |
| judge | $100 | 413 | 43.3 | 1.50 | 10,226 |
| pick | $250 | 298 | 48.0 | 1.55 | 8,468 |
| pick | $100 | 327 | 43.4 | 1.48 | 7,399 |

The tighter stop lowers win rate by about 8-11 pts, PF stays about the same (1.49 vs 1.52), net per micro is 9 % lower over 5y, and the trade count rises 13 %. Per dollar of risk the $100 stop is not worse; what raises account profit is the 2 (or 4) micros, not the stop.

## Trades taken / skipped (static, 5y; judge in brackets; identical on all four plans because sizes never bind on a fresh account)
- Signals: NOISE 740 (413), CANDACE 304 (150).
- A: NOISE taken 724 (406), skipped 16 (7) "CANDACE position open"; CANDACE taken 303 (150), skipped 1 (0) "NOISE position open". 0 skipped for the $100 per-micro cap, 0 for room, 0 resized.
- B: NOISE 725 (407) taken, 15 (6) skipped as opposite direction (hedge); CANDACE 303 (150), 1 (0) hedge skip. B differs from A by one trade, so B adds nothing and is marginally worse everywhere (and would need a change to non-negotiable 7, which is not warranted).
- Balance-dependent skips inside the rolling runs (shrink/room/STUCK) are not counted separately; they show up as "stuck".

## Verdict (rule: in judge AND 5y on that plan: pass % higher OR passed<=60 d higher; stuck not > BASE + 2 pts; profit not lower than BASE)
| plan | row | judge | 5y | failing criterion |
|---|---|---|---|---|
| 25K | NOISE-2@$100 | FAIL | FAIL | pass/speed (judge: pass -17.4, <=60 d -2.6); stuck 5y (+3.8) |
| 25K | A | FAIL | FAIL | stuck (+20.6 judge, +27.3 5y); judge also pass/speed |
| 25K | B | FAIL | FAIL | same as A |
| 50K | NOISE-2@$100 | FAIL | FAIL | profit (-$1,198 judge, -$3,335 5y) |
| 50K | A | FAIL | FAIL | stuck (+5.4, +9.2); 5y also profit (-$204) |
| 50K | B | FAIL | FAIL | stuck; 5y profit (-$402) |
| 100K | NOISE-4@$100 | PASS | PASS | none (pass -26 / -32 but <=60 d +15.9 / +15.4, stuck -20 / -9, profit +$19k / +$32k) |
| 100K | A | FAIL | FAIL | stuck (+10.2 judge, +22.7 5y) |
| 100K | B | FAIL | FAIL | stuck |
| 150K | NOISE-4@$100 | PASS | PASS | none (pass -12.5 / -7.3, <=60 d +1.1 / +2.2, stuck down, profit +$8k / +$13k) |
| 150K | A | PASS | FAIL | stuck 5y (+5.5 pts; judge -0.9) |
| 150K | B | PASS | FAIL | stuck 5y (+5.9) |

**Nothing combining CANDACE (A or B) passes on any plan in both windows.** The only rows that pass the rule are NOISE alone at 4 micros with a $100 stop on 100K and on 150K, and they pass only through the "passed within 60 days" alternative (+15 pts on 100K, +1 to +2 pts on 150K): their pass % is clearly lower than BASE (100K 45 vs 78 %; 150K 70 vs 77 %), with most of the difference left running rather than failed. That is a NOISE sizing/stop finding, not a CANDACE one; it is a speed gain bought with a lower completed-pass rate, and the 150K speed gain is small (<=60 d 8.0 vs 5.8 %). Not recommended on its own evidence: the 100K/150K BASE already passes 77 % and a "pass within 60 days" gain of 2 pts is inside noise.

What drives the results:
- 25K: the 2-micro size doubles profit and halves time to pass (median 28 vs 74 d) but the 1,000 MLL leaves little room, so most non-passing accounts become stuck (A: 63 %). Pass % falls from 58.6 to 34.0.
- 50K: A passes 59 % vs 69 %, is faster (median 67 vs 92 d) but stuck rises 9 pts.
- 100K/150K: doubling the base size raises profit (+$38k / +$19k plan-sized over 5y vs BASE) and speed (median 62 / 105 d vs 152 / 159); on 150K, A gets within 3 pts of BASE's pass and wins in the judge window, but 5y stuck is +5.5 pts.
- CANDACE adds +$3k (1 micro) to +$6k (2 micros) 5y plan-sized on top of NOISE alone but raises stuck by 24 pts (25K) and 31 pts (100K), because the added trades cost extra drawdown at the same MLL.

## Caveats
- Multiple testing: 4 plans x 3 rows x 2 windows added to earlier C125/LOCK80/VWAP/fixed-size tests on the same 5-year MNQ sample; rolling starts overlap heavily (about 20 independent evaluation lengths) and the judge window has been seen many times, so 2-4 pt differences are noise. The two "PASS" rows rest on a single secondary criterion.
- The $100-stop NOISE stream changes exits, entries and re-entries (not just sizing); the shrink/D57 logic still operates on a $100 risk per micro.
- 100K/150K BASE pass reproduces eval_odds within 2 pts; stuck/bust definitions differ from eval_odds (see Reproduction).
- No live-rule change was tested; hedge lock, one position per account and all Lucid limits are untouched in every row.
