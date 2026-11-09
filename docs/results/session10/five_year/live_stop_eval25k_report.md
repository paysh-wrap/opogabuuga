# Live D57 stop-tightening vs the study assumption: Pro 25K high-risk eval (MNQ 5y, 2021-11 to 2026-10)

Script: /tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/agentO/livestop.py  (`livestop.py verify`, `livestop.py run`; raw numbers results.json, table.md)

## 1. The live rule (backend/app/risk/checks.py pretrade, fixed-size branch), reproduced
Per trade at entry: dist = equity - MLL floor; skip NEAR_MLL if dist <= $100; room0 = dist - $100 (no DLL on the Pro eval);
usd = n x (stop_ticks x $0.50 + $1.00 + 1 tick x $0.50) (base stop 124 pts = 496 ticks -> $249.50 per micro);
allowed = room0 x shrink (0.6). If usd > allowed: ticks = floor((allowed/n - 1)/0.5 - 1); if ticks x 0.25 < 0.2% x entry -> skip DRAWDOWN_TOO_DEEP (40-52 pts at 20-26k) else the stop is entry -/+ ticks x 0.25.
Then the worst-case check: worst + $40 <= room0, else skip WORST_CASE_EXCEEDS_LIMITS.
Examples (fresh eval, cushion $1,000, room0 $900): 4 micros -> stop 66.75 pts = $134/micro (matches the brief); 3 micros -> 89.25 pts ($178); 2 and 1 micro -> not tightened (124 pts).
Coordinator variant (e): allowed = room0 - $40 (shrink "just under 1.0"): fresh 4 micros -> 106.75 pts = $214/micro; 3, 2, 1 micro -> not tightened.
Where trades die: at 0.6 the min-stop skip starts when dist < 236 (1 micro), < 360 (2), < 480 (3), < 643 (4 micros); at room-40 about 222 / 305 / 390 / 466.

## 2. Simulator and verification
Per-trade re-simulation on 1-minute bars (generators copied from agent1/gen.py): NOISE (hourly checks 10:00-15:00, up to 3 entries, trail exit on band/VWAP, gap guard) + afternoon 2-sd VWAP fade on days NOISE took no trade. Stop distance of each trade comes from the live rule using the account's CURRENT balance and floor at the moment of entry (so within a day later trades see earlier P&L). Pass-fill/slippage/fees as in gen.py.
- Verified: with the fixed 124-pt stop the simulator reproduces agent1/trades_main.csv exactly (1,291 trades, $25,345.27, 0 of 1,111 day mismatches).
- Verified: no tightening reproduces the earlier study: a0 = 63.4/34.4/2.2% pass/bust/open, median 36, p75 56, chain 47 (study BASE) and c4 = 52.4/47.6, median 7, p75 14, chain 11 (study B2). c3 = 50.1/49.9, c2 = 51.9/48.1.
Eval engine as the earlier study: target $1,250, EOD trailing MLL $1,000, lock at 26,100 peak -> floor 25,100, no DLL, >= 1 profitable day, bust when balance <= floor intraday, size set at session start (taper to 1 micro when < 50% of target remains), 120-session horizon, 593 rolling starts every 2 sessions, era1 = starts to 2023-12-31, era2 after.
New: a signal the live rule rejects is a SKIP (consumes one of the 3 NOISE entries, position stays flat); NOISE-day fade is allowed when NOISE executed nothing. STALL = 20 consecutive sessions with no executed trade (account frozen by DRAWDOWN_TOO_DEEP/NEAR_MLL: the cushion cannot grow without trades and the floor does not fall, so this is absorbing). A stalled eval is a failed eval for the restart chain (the chain restarts on BUST or STALL; chain sessions include the 20 idle ones). Skip share = skipped / all signals inside the 120-session horizon runs; the second figure is the same inside evals that PASSED.
Value per eval = pass% x $1,646.41 (funded year-1 take-home at 1 micro, as before; eval fee not modelled).

## 3. Results
(a) = 1 micro; b = live rule 0.6; c = no tightening (the study's assumption); e = live rule with shrink to room - $40; b/c/e with 4, 3, 2 micros all taper to 1 micro when < 50% of the target is left. s/t rows are NOT live: they step the contract count down instead of skipping (diagnostic).

| config | pass | bust | stall | open | med | p75 | chain med | skip share (all / in passing evals) | avg stop $/micro | avg micros | chain censored | value/eval | era1 pass/bust/med/chain | era2 pass/bust/med/chain |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a  1 micro, live rule 0.6 | 55.5% | 0.0% | 43.7% | 0.8% | 35 | 55 | 59 | 34.2% / 0.2% | $240 | 1.00 | 0% | $913 | 65%/0%/41/56 | 47%/0%/26/66 |
| a' 1 micro, live rule room-40 | 56.2% | 0.0% | 43.0% | 0.8% | 35 | 55 | 58 | 33.4% / 0.0% | $244 | 1.00 | 0% | $925 | 65%/0%/41/56 | 48%/0%/26/63 |
| a0 1 micro, no tightening (study base) | 63.4% | 34.4% | 0.0% | 2.2% | 36 | 56 | 47 | 0.0% / 0.0% | $248 | 1.00 | 0% | $1,044 | 66%/31%/41/56 | 61%/37%/32/40 |
| b4 4->1 taper50, LIVE 0.6 | 25.1% | 0.0% | 74.9% | 0.0% | 4 | 10 | 55 | 88.1% / 8.5% | $180 | 2.62 | 1% | $414 | 29%/0%/4/52 | 22%/0%/4/58 |
| c4 4->1 taper50, NO tightening (study) | 52.4% | 47.6% | 0.0% | 0.0% | 7 | 14 | 11 | 0.0% / 0.0% | $248 | 2.54 | 0% | $863 | 56%/44%/7/11 | 49%/51%/6/11 |
| e4 4->1 taper50, shrink to room-$40 | 33.2% | 0.0% | 66.8% | 0.0% | 5 | 11 | 35 | 83.5% / 0.0% | $217 | 2.53 | 0% | $547 | 38%/0%/6/30 | 29%/0%/4/41 |
| b3 3->1 taper50, LIVE 0.6 | 31.0% | 0.0% | 69.0% | 0.0% | 8 | 15 | 43 | 81.7% / 0.2% | $195 | 2.10 | 1% | $511 | 36%/0%/10/36 | 26%/0%/6/46 |
| c3 3->1 taper50, NO tightening (study) | 50.1% | 49.9% | 0.0% | 0.0% | 10 | 17 | 16 | 0.0% / 0.0% | $248 | 2.11 | 0% | $825 | 51%/49%/12/16 | 50%/50%/9/15 |
| e3 3->1 taper50, shrink to room-$40 | 37.6% | 0.0% | 62.4% | 0.0% | 8 | 16 | 33 | 77.0% / 0.0% | $232 | 2.04 | 0% | $619 | 41%/0%/11/34 | 34%/0%/7/31 |
| b2 2->1 taper50, LIVE 0.6 | 33.6% | 0.0% | 66.4% | 0.0% | 13 | 20 | 47 | 71.7% / 0.0% | $222 | 1.61 | 2% | $553 | 35%/0%/17/56 | 32%/0%/11/40 |
| c2 2->1 taper50, NO tightening (study) | 51.9% | 48.1% | 0.0% | 0.0% | 17 | 25 | 24 | 0.0% / 0.0% | $248 | 1.64 | 0% | $855 | 53%/47%/19/25 | 51%/49%/14/22 |
| e2 2->1 taper50, shrink to room-$40 | 38.8% | 0.0% | 61.2% | 0.0% | 14 | 21 | 40 | 67.6% / 0.0% | $237 | 1.60 | 2% | $639 | 38%/0%/16/48 | 39%/0%/12/36 |
| s4 4->1 taper50, NOT LIVE step-down contracts (0.6) | 35.1% | 0.0% | 64.9% | 0.0% | 6 | 13 | 36 | 76.5% / 1.7% | $157 | 2.29 | 3% | $577 | 36%/0%/6/36 | 34%/0%/7/36 |
| t4 4->1 taper50, NOT LIVE step-down contracts (room-40) | 36.9% | 0.0% | 63.1% | 0.0% | 6 | 12 | 30 | 81.0% / 0.0% | $213 | 2.49 | 0% | $608 | 40%/0%/6/30 | 34%/0%/6/30 |
| s3 3->1 taper50, NOT LIVE step-down contracts (0.6) | 36.6% | 0.0% | 63.4% | 0.0% | 8 | 16 | 39 | 73.6% / 0.0% | $177 | 1.97 | 0% | $602 | 39%/0%/11/38 | 34%/0%/7/40 |
| t3 3->1 taper50, NOT LIVE step-down contracts (room-40) | 39.1% | 0.0% | 60.9% | 0.0% | 8 | 15 | 33 | 75.1% / 0.0% | $224 | 2.02 | 0% | $644 | 42%/0%/11/32 | 36%/0%/7/34 |
| s2 2->1 taper50, NOT LIVE step-down contracts (0.6) | 37.9% | 0.0% | 62.1% | 0.0% | 14 | 22 | 43 | 65.9% / 0.0% | $209 | 1.57 | 2% | $625 | 40%/0%/17/48 | 36%/0%/12/39 |
| t2 2->1 taper50, NOT LIVE step-down contracts (room-40) | 39.8% | 0.0% | 60.2% | 0.0% | 14 | 22 | 40 | 66.4% / 0.0% | $235 | 1.59 | 1% | $655 | 39%/0%/16/47 | 41%/0%/13/36 |

(a0 is the previous study's 1-micro baseline with no tightening; a and a' are the 1-micro baseline under the live rule 0.6 and room-40.)

## 4. Findings
1. The live safety rule never lets an account bust (0.0% in every live row) but it freezes accounts instead: 4 micros at 0.6 -> 24.8% pass, 0% bust, 75% STALL (study assumption: 52.4% pass / 47.6% bust). The tightened first stop (66.75 pts, 0.33% of price) is hit often; one stop-out costs up to $540 and leaves a cushion of about $460, at which 4 micros need a stop under 40 pts -> DRAWDOWN_TOO_DEEP on every later signal -> the eval is dead but not busted. The taper at 50% target does not help because the freeze happens before the profit is made. Value per eval falls $863 -> $414 (-52%).
2. Speed: for the evals that do pass, speed is unchanged or better (4 micros median 4-5 sessions, p75 10-11). But because passes are so few the restart-chain median to a first pass is 55 sessions at 0.6 (vs 11 in the study and 47 for 1 micro with no tightening, 58 for 1 micro under the live rule). So the live rule costs the 4-micro profile its pass rate (-27 pts) and, measured as time to a pass across restarts, ALL of its speed advantage.
3. Raising the shrink to room-$40 (e) helps but only partly: 4 micros 33.2% (chain 35), 3 micros 37.6% (chain 33), 2 micros 38.8% (chain 40). The cap is the regular loss limit minus the kill distance and margin, so the first full stop takes the account to about $140 above the kill line, and the min-stop skip then freezes it.
4. 1 micro is also affected: the 1-micro baseline loses 7-8 pts (63.4% -> 55.5%/56.2%; era2 61% -> 47%) because a stop-out deep in a drawdown is replaced by a skip and the account stalls (43-44% of evals) where it previously busted (34%) or occasionally recovered. 44% of evals stall under the live rule at 1 micro versus 34% bust before, so the live rule at 1 micro costs about 8 pass points and cuts nothing from the number of failed evals.
5. Contract step-down (not live) does not rescue it (t4 36.9%, t3 39.1%, t2 39.8%): the freeze is mostly a 1-micro, cushion-below-about-$230 problem, not a sizing one. The real lever would be the min-stop floor (0.2% of price) and the 0.6/room-40 cap interacting with a fixed 124-pt strategy exit, not the contract count.
6. Era split: every live row is worse in era2 (2024-26: 22-48%) than era1 (29-65%), the same direction as the study.

## 5. Verdict
- Does the live safety rule cost the 25K high-risk profile its speed or pass rate? Yes. Pass rate: 4 micros 52.4% (study) -> 24.8% (live 0.6) / 33.2% (room-40). Speed: median-to-pass among passers stays 4-5 sessions, but the time to get a pass including restarts goes from 11 sessions to 55 (0.6) / 35 (room-40), no better than 1 micro (58 live, 47 unshielded). The high-risk profile as modelled in the study (52% pass, ~11-session chain) does not exist under the live check.
- Best micro count under the LIVE rule (0.6): by pass rate 2 micros (33.6%, value $553, median 13, chain 47) > 3 (31.0%, $511, 8, chain 43) > 4 (25.1%, $414, 4, chain 55). By time to a pass across restarts 3 micros is fastest (chain 43), 2 micros second. 1 micro is best on pass rate (55.5%, $913) but slow (median 35, chain 59).
- Best micro count when the cap is the regular loss limit (room - $40, e): 3 micros is the best balance: 37.6% pass, median 8 / p75 16, restart chain 33 sessions (fastest), value $619; 2 micros has the highest pass rate (38.8%, $639) but median 14 and chain 40; 4 micros is worst on pass (33.2%, $547) and not faster across restarts (chain 35). Recommendation: if the high-risk profile stays, use 3 micros with the shrink fraction raised to room-$40; 2 micros if pass rate matters more than speed. Neither reaches the study's 50% pass; against plain 1 micro (56% pass, median 35, chain ~58) 3 micros e gives roughly 1.7x faster chain at 19 pts fewer passes.

## 6. Caveats
- Starts overlap (about 10 independent 120-session windows); differences of 2-3 pass points are noise, the stall effect (25-40% vs 52%) is not.
- Day stops (2 consecutive losses etc.), the intra-trade kill-switch flatten, firm max contracts and the 6-s hold rule are not modelled (same as the earlier study; no live rule can bust the account in the tightened rows, since worst case <= room).
- STALL = 20 idle sessions is a modelling choice; it does not change pass %, only how chain time is counted (a frozen eval costs 20 sessions before the user would restart).
- The tightened stop is applied at the plan entry price (fill price in the sim); gap fills beyond the stop (min(stop, open)) can exceed the planned worst case in the sim, the live code assumes none; bust stays at 0% in the live rows so the gap risk was not hit.
- Funded year-1 value ($1,646) uses the 1-micro funded stream; an eval fee and the cost of failed evals are not charged.
