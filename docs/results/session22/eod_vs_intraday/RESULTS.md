# Session 22 - EOD trailing vs intraday trailing drawdown (same strategy, same plans)

Scripts (run with .venv/bin/python, in this order): `run.py` (all numbers, 5 s on 4 cores), `ORDER=worst python run.py`, `ORDER=best python run.py` (bar-order sensitivity), `stats.py`, `report.py`. Engine: `sim.py` (plan loader, copy of session 21 pro_rules), `sim2.py` (session 21 pro_rules simulator, EOD code unchanged, plus `build_paths` and `sim_intra`). Raw: `results.json` (+ `_worst`, `_best`), `trade_stats.json`.
Setup identical to session 21 pro_rules: NOISE shipped eval stream (`streams_BASE.csv`, 654 trades), entry = MNQ open from days12.pkl, eras ALL 2021-10-21..2026-10-30 / IS ..2025-11-05 / J 2025-11-06..2026-10-30, 10-day block bootstrap, 600 paths x 400 sessions, seed 7, regular size table, kill distance and margin from the YAMLs, pre-trade room check, size-table brake, D57 stop shrink (0.6 x room, min stop 0.2 % of price, STUCK when 0.6 x room < $112), D138 plan YAMLs (md5 unchanged since session 21 pro_rules).

## 1 Answer
Intraday trailing is clearly worse than EOD trailing for the same strategy. On the small plans (25K) it costs about 15 to 20 pass points over the whole history (Pro 25K 57 to 39, Daily and Flex 25K about 52 to 34) and about 19 over the last 12 months (Pro 25K 40 to 21, bust 60 to 79). On 50K it costs 8 to 10 points (ALL) and 17 to 18 points in J, on 100K and 150K 5 to 8 points ALL and 13 to 19 points in J. The reason is simple: the NOISE trades hold 1 to 6 hours and give back a lot of open profit (mean best open profit per micro $185, mean closed result $29.5). An intraday account counts every one of those unrealised highs as a new peak and lifts the floor by it, so the room shrinks after trades that closed flat or small. A small account has only $1,000 of room, so the app's room check and the D57 shrink soon leave no room for a valid stop (STUCK) or the kill switch fires. EOD trailing only counts the closing balance, so those intraday highs cost nothing. Passes are also a little faster under intraday (it locks earlier) but there are far fewer of them.

## 2 Table: EOD vs intraday trailing (pass / bust %, regular size table, bust includes STUCK)
EOD column = kill switch OFF (balance + open P&L), the shipped default. Intraday = floor trails equity incl. open profit, kill switch on equity within the plan's kill distance of the current floor.

| plan | micros | EOD ALL | EOD IS | EOD J | intraday ALL | intraday IS | intraday J | diff pass pts ALL / IS / J | median sessions to pass EOD vs intraday (ALL / J) |
|---|---|---|---|---|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 | 52 / 48 | 37 / 63 | 34 / 66 | 36 / 64 | 18 / 82 | -18 / -16 / -18 | 54 vs 48 ; 38 vs 34 |
| lucid_flex_100k | 2 | 76 / 20 | 78 / 17 | 67 / 32 | 69 / 28 | 72 / 24 | 48 / 52 | -7 / -6 / -19 | 162 vs 161 ; 123 vs 119 |
| lucid_flex_150k | 3 | 78 / 16 | 78 / 15 | 70 / 8 | 72 / 22 | 73 / 20 | 56 / 15 | -6 / -5 / -14 | 169 vs 168 ; 128 vs 128 |
| lucid_flex_25k | 1 | 51 / 49 | 52 / 48 | 32 / 68 | 34 / 66 | 36 / 64 | 17 / 83 | -17 / -16 / -15 | 52 vs 48 ; 35 vs 32 |
| lucid_flex_50k | 2 | 61 / 39 | 66 / 34 | 48 / 52 | 53 / 47 | 55 / 45 | 31 / 69 | -8 / -10 / -17 | 74 vs 76 ; 55 vs 51 |
| lucid_pro_100k | 2 | 77 / 18 | 79 / 16 | 68 / 31 | 69 / 28 | 73 / 22 | 49 / 50 | -8 / -6 / -19 | 162 vs 161 ; 124 vs 121 |
| lucid_pro_150k | 3 | 78 / 14 | 79 / 14 | 71 / 6 | 74 / 21 | 73 / 20 | 58 / 14 | -5 / -5 / -13 | 170 vs 173 ; 130 vs 132 |
| lucid_pro_25k | 1 | 57 / 43 | 57 / 43 | 40 / 60 | 39 / 61 | 42 / 58 | 21 / 79 | -18 / -15 / -19 | 56 vs 50 ; 40 vs 35 |
| lucid_pro_50k | 2 | 65 / 34 | 66 / 33 | 52 / 48 | 55 / 44 | 58 / 41 | 34 / 66 | -10 / -8 / -18 | 78 vs 78 ; 55 vs 53 |

Pass-point difference = intraday minus EOD. The 150K and Flex 150K J rows have 28 to 29 % of paths still open after 400 sessions (so bust understates the damage there; pass is the safer number).

## 3 Kill-switch setting check (EOD accounts: strategy.eod_closed_balance OFF vs ON)
Confirmed: identical, and not just in the totals. In all 9 plans and all 3 eras every one of the 600 paths ends with the same outcome on the same session under both settings.

| plan | ALL off | ALL on | IS off | IS on | J off | J on | identical paths (of 600, ALL/IS/J) |
|---|---|---|---|---|---|---|---|
| lucid_daily_25k | 52 / 48 | 52 / 48 | 52 / 48 | 52 / 48 | 37 / 63 | 37 / 63 | 600 / 600 / 600 |
| lucid_flex_100k | 76 / 20 | 76 / 20 | 78 / 17 | 78 / 17 | 67 / 32 | 67 / 32 | 600 / 600 / 600 |
| lucid_flex_150k | 78 / 16 | 78 / 16 | 78 / 15 | 78 / 15 | 70 / 8 | 70 / 8 | 600 / 600 / 600 |
| lucid_flex_25k | 51 / 49 | 51 / 49 | 52 / 48 | 52 / 48 | 32 / 68 | 32 / 68 | 600 / 600 / 600 |
| lucid_flex_50k | 61 / 39 | 61 / 39 | 66 / 34 | 66 / 34 | 48 / 52 | 48 / 52 | 600 / 600 / 600 |
| lucid_pro_100k | 77 / 18 | 77 / 18 | 79 / 16 | 79 / 16 | 68 / 31 | 68 / 31 | 600 / 600 / 600 |
| lucid_pro_150k | 78 / 14 | 78 / 14 | 79 / 14 | 79 / 14 | 71 / 6 | 71 / 6 | 600 / 600 / 600 |
| lucid_pro_25k | 57 / 43 | 57 / 43 | 57 / 43 | 57 / 43 | 40 / 60 | 40 / 60 | 600 / 600 / 600 |
| lucid_pro_50k | 65 / 34 | 65 / 34 | 66 / 33 | 66 / 33 | 52 / 48 | 52 / 48 | 600 / 600 / 600 |

Why: the pre-trade room check plus the D57 shrink only allow a trade when q x stop + margin fits in (balance - floor - kill distance), and the broker stop caps the loss at that stop. An open loss therefore cannot reach the kill line on an EOD account (the stop fires first), so "balance + open P&L" never triggers where "closed balance" would not. The two settings would only differ if a stop failed to fill (gap, slippage beyond the 1 tick modelled) or if a trade were sized without the room check. The simulation does not model such failures, so this is a floor on the difference, not proof it is zero in real trading.

## 4 Mechanism: intraday highs that reversed
| plan | era | intraday fails (bust+stuck, % of 600 paths) | of which killed in a trade | of which stuck below the room | fails with intraday floor above the EOD floor | kills the EOD floor would NOT have touched | paths EOD pass -> intraday fail |
|---|---|---|---|---|---|---|---|
| lucid_daily_25k | ALL | 393 (66%) | 56 | 337 | 376 (96%) | 56 of 56 | 105 |
| lucid_daily_25k | J | 489 (82%) | 112 | 377 | 456 (93%) | 112 of 112 | 109 |
| lucid_flex_100k | ALL | 170 (28%) | 22 | 148 | 150 (88%) | 22 of 22 | 40 |
| lucid_flex_100k | J | 311 (52%) | 88 | 223 | 269 (86%) | 88 of 88 | 118 |
| lucid_flex_150k | ALL | 135 (22%) | 11 | 124 | 115 (85%) | 11 of 11 | 33 |
| lucid_flex_150k | J | 92 (15%) | 34 | 58 | 73 (79%) | 34 of 34 | 46 |
| lucid_flex_25k | ALL | 396 (66%) | 53 | 343 | 379 (96%) | 53 of 53 | 100 |
| lucid_flex_25k | J | 497 (83%) | 97 | 400 | 462 (93%) | 97 of 97 | 88 |
| lucid_flex_50k | ALL | 284 (47%) | 34 | 250 | 247 (87%) | 34 of 34 | 57 |
| lucid_flex_50k | J | 413 (69%) | 84 | 329 | 367 (89%) | 84 of 84 | 108 |
| lucid_pro_100k | ALL | 167 (28%) | 22 | 145 | 147 (88%) | 22 of 22 | 45 |
| lucid_pro_100k | J | 301 (50%) | 87 | 214 | 260 (86%) | 87 of 87 | 115 |
| lucid_pro_150k | ALL | 125 (21%) | 11 | 114 | 107 (86%) | 11 of 11 | 32 |
| lucid_pro_150k | J | 86 (14%) | 31 | 55 | 70 (81%) | 31 of 31 | 42 |
| lucid_pro_25k | ALL | 366 (61%) | 46 | 320 | 350 (96%) | 46 of 46 | 110 |
| lucid_pro_25k | J | 473 (79%) | 115 | 358 | 440 (93%) | 115 of 115 | 112 |
| lucid_pro_50k | ALL | 267 (44%) | 29 | 238 | 229 (86%) | 29 of 29 | 63 |
| lucid_pro_50k | J | 393 (66%) | 94 | 299 | 351 (89%) | 94 of 94 | 110 |

Reading: "fails with intraday floor above the EOD floor" counts failed paths where, at the moment of failure, the floor had been lifted above what an EOD-trailing floor would be on the same path, by open profit that was not banked. Most intraday fails have this (77 to 95 % of kills, 79 to 97 % of stuck fails, by plan and era); the remainder are fails EOD would also have had. The kill-in-trade column is smaller than the stuck column: most intraday failures are not a sudden breach but the account slowly running out of trading room as the floor creeps up on unrealised peaks (STUCK), which the app treats as failure because no valid stop fits any more. Every in-trade kill is a trade that would not have touched the EOD floor (column 'kills the EOD floor would NOT have touched', n of n), so those busts exist only because of a high made intraday. Per path, on the 25K plans 100 to 112 of 600 paths that pass under EOD fail under intraday (17 to 19 % of all paths), 40 to 63 on 50K, 32 to 45 on 100K/150K (ALL) and more in J; only 0 to 7 paths move the other way.
Trade-level evidence (`trade_stats.json`, 654 trades): mean best open profit per micro $185, mean closed pnl $29.5, 61 % of trades gave back $100 or more from their high, 64 of 318 losing trades were up $100 or more at some point. The intraday floor ratchets on every one of these highs.

## 5 Caveats
- Bootstrap of one 654-trade NOISE stream; J is only about 245 sessions (118 trades), so J cells are +-5 pts or more. ALL contains J.
- Intraday path = 1-minute bars of the trade window with the stream's own MAE definition (entry open + 1 tick, MAE +1 tick). Within a bar the order of high and low is unknown; I used the close-direction rule and re-ran with favourable-first and adverse-first for every bar: pass and bust did not change in any cell (results_worst/best.json), so the assumption does not matter at 1-minute resolution.
- Real intraday accounts re-evaluate the floor on every tick; 1-minute extremes understate it slightly (so the intraday penalty is if anything a bit larger).
- Intraday lock: floor locks at lock_level once the intraday peak reaches lock_trigger (same numbers as EOD, per YAML). The unrealised peak counts toward the lock, which is why intraday passes in slightly fewer sessions on 25K.
- Kill switch in intraday mode uses the plan's kill distance on equity. Without any kill switch intraday accounts would breach at the touch instead of at floor+distance: not simulated.
- DLL and the consistency day stop are applied on closed P&L as in session 21 (no intratrade DLL touch); LucidScale uses EOD peak as in session 21.
- D57 shrink, brake rows, STUCK rule, gmin $112 are the session 21 assumptions, unchanged. Lucid's lock and EOD rules are as written in the YAMLs (VERIFY items stay VERIFY).
- Statuses: 'open' paths (no pass or bust after 400 sessions) are not failures; 150K plans in J have about 28 % open.
- NOISE only; other strategies hold shorter and would give back less.

## Review notes (main session, 2026-11-14)
- Spot-checked: the EOD columns equal config/eval_odds.yaml (Pro 25K regular ALL 57/43, J 40/60) — the app's shown odds are the EOD ones.
- Plans: Pro + Flex trail EOD in eval AND funded, lock at an EOD peak of $26,100 → floor $25,100 (25K); Daily funded is intraday
  (Lucid help center, confirmed by the user 2026-11-13) — unchanged.
- UI fix the same day: the EOD toggle worked, but its option buttons read "ON/OFF ·" (= selected / not selected) and the selected one was
  a faded disabled button with a "not allowed" cursor → now "✓ IN USE" (bright, clicking it does nothing) vs "USE THIS".
