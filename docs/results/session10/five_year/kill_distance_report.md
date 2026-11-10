# Kill-switch distance $100 vs $50 (vs $0 bound) under the LIVE pre-trade rule - Pro eval / funded backtest

Date 2026-11-10. Change under test: `internal.kill_switch_mll_distance` 100 -> 50 on all Pro plans (D71). No app code was edited.

## Method (what was run)
- Simulator: per-trade re-simulation of the MAIN strategy (NOISE hourly-check momentum + afternoon VWAP fade, MNQ, 1-minute bars, 2021-11 -> 2026-10)
  = `docs/results/session10/five_year/eval25k_total_risk.py` (copied unchanged as `base_sim.py`: prep / calendar / first_hit / trade_stop_exit). Stop fills at
  `min(stop, bar open) -/+ 1 tick`, fee $1 RT, slippage 1 tick, skipped signals consume NOISE entries, STALL = 20 idle sessions in a row = FROZEN.
- `kill_study.py` re-implements `day_sim` with: kill distance as a parameter; the live rule of `backend/app/risk/checks.py pretrade` (room0 = min(DLL left, equity - floor - kill);
  allowed = 0.6 x room0; stop tightened with ROUND_DOWN ticks; skip DRAWDOWN_TOO_DEEP if tightened stop < 0.2% of price; worst case + $40 <= room0; `dist > kill` else NEAR_MLL);
  DLL as soft day stop (D18 trailing-from-day-peak room); per-trade stats (type, tightened stop, worst intraday point on 1-minute bars, loss beyond the planned worst case).
  Funded engine = copy of `income_projection.funded_path` + the same pre-trade rule (payout every 10 sessions for 25K/50K, 5 for 150K; max eligible; 40% consistency; MLL lock on payout; plan rules from `config/rules/lucid_pro_*.yaml`).
- Verification (`kill_study.py verify`): kill $100 reproduces the previous live-rule study exactly (Regular 55.5% pass / 43.7% stall / median 35 / chain 59; High risk 31.2% / 68.8% / 8 / 42);
  no-rule run reproduces 63.4% pass / 34.4% bust / win rate 50.5%; funded engine with no rule reproduces `income_projection.project()` (25K: mean $1,646.40 vs $1,646.41, bust 56.6%; 150K x3: $4,962.78 vs $4,962.79, 24.5%).
- Configs: Pro 25K eval (target 1,250, MLL 1,000, no DLL, lock 26,100, 120 sessions, starts every 2 sessions, 593 starts): 1 micro x $250 (Regular); 3 micros x $150 taper->1 below 50% of target remaining (High risk);
  2 x $225 taper. Pro 50K eval (target 3,000, MLL 2,000, DLL 1,200): 2 x $250, brake <50% cushion -> 1. Funded year 1 (260 sessions, 523 starts): 25K x1, 50K x2 (brake->1), 150K x3 (brake->2), 150K x4 High risk (brake->2); every funded config uses the $250/micro base stop.
- "no rule" rows = the old study assumption (no tightening, no kill check, 124-pt stop; busts count, nothing freezes). "$0" = bound (kill check `dist > 0`).
- Value per eval = pass% x year-1 take-home of the matching funded config at the same kill distance (25K x1 for all 25K evals, 50K x2 for the 50K eval).
- Era 1 = starts 2021-11 -> 2023-12, era 2 = 2024-01 -> 2026-10.
- Files: `kill_study.py` (run / verify / stress / fadecode), `tables.py`, `paired.py`, `stress_tables.py`, `bars.py`; raw `results_main.json`, `results_stress{25,50,100}.json`, `results_fadecode.json`, `paired.json`, `min_dist.json`; `tables_main.md`.


## Verdict (short)
1. $50 vs $100 changes almost nothing material. Pass rate +0.5 pt (Regular 25K), +1.9 pt (High risk 3x$150), +4.3 pt (2x$225), 0.0 pt (50K); frozen falls by the same amount; busts stay 0.0% everywhere;
   year-1 take-home per account +$45 (25K x1), +$17 (50K x2), +$11 (150K x3), +$6 (150K x4 High risk) - below 3.5% of the base value in every case. Median sessions to pass unchanged (35 / 8 / 15 / 43 vs 35 / 8 / 14 / 44).
   Paired by start (same data, only the kill distance differs) 99.2% / 98.1% / 95.6% / 99.0% of eval starts end identically; the changed ones are almost all "frozen -> pass".
2. Why so little: the freeze is not decided by the kill distance. It is decided by the minimum-stop rule (tightened stop < 0.2% of price -> DRAWDOWN_TOO_DEEP). That rule needs a minimum cushion to trade
   (1 micro x $250 at MNQ 21,000: $243 at kill 100, $193 at kill 50, $143 at kill 0; 3 micros x $150: $528 / $478 / $428; see table "min cushion"). Moving the kill distance only shifts that cushion by exactly $50,
   so only accounts parked in a $50 band above the threshold benefit. 33-34% (Regular) of the signals are skipped DRAWDOWN_TOO_DEEP either way (kill 100: 33.9%, kill 50: 33.0%); NEAR_MLL itself never fires (0.0%) because DEEP triggers first.
   The only lever that would really cut freezing is the 0.2% minimum (or the 0.6 shrink fraction), not the kill distance.
3. Win rate is NOT affected by the kill distance and NOT hurt by the tightening versus the study assumption (~50%): executed-trade win rate at 1 micro x $250 = 50.7% ($100) / 50.6% ($50) / 50.3% ($0) vs 50.5% with no rule
   (NOISE 45.5% / fade 59%, avg win $142-144, avg loss $110-111, PF 1.30-1.34). Only 1.7-1.9% of all trades (15-16% of the tightened ones) end at the tightened stop.
   The 3x$150 High-risk eval is lower by construction (46.2-46.4% vs 46.7% no rule; 8.2% of all trades / 41% of the tightened ones are stopped at the tightened stop; PF 1.24-1.27); 2x$225 taper 47.8-48.4% vs 49.5%.
4. Extra risk is small and bounded by construction: with the 0.6 shrink every executed trade has its worst case <= 0.6 x (cushion - kill), so after a stop-out the equity stays >= kill + 0.4 x (cushion - kill) above the floor.
   Base replay (1-minute bars, 5 years): ZERO trades came within $50 of the floor at kill $100 or $50, ZERO realised or intraday kill-switch trips, ZERO stop-outs worse than the planned stop (no gap through a stop in the data).
   The only change: 12 of 20,823 trades (25K Regular, 0.06%), 36 of 30,013 (50K), 29 of 62,533 (funded 25K), 44 of 74,901 (funded 50K) had their intraday worst point within $50-$100 of the floor (0 at kill $100, by construction); none reached $50.
   Most plausibly these are trades at low index prices (2022, MNQ ~11-13k) where the 0.2% minimum stop is only ~$45-55 per micro, so the minimum tradable cushion at kill $50 is ~$150 (min-cushion table below).
5. Gap tolerance (stress, artificial: extra loss on EVERY stop-out fill): +$25 per stop-out - no busts, no kill-switch trips, nothing within $50 of the floor at either kill (kill $50 is not worse). +$50 per stop-out - no busts; at kill $50
   1.3-1.6 per 1,000 trades (25K) end within $50 of the floor (the controller would kill-switch -> permanent pause, since kill pauses never auto-resume); at kill $100 the same trades end within $100 (0.8-1.3/1,000 trips).
   +$100 per stop-out (a 50-point miss on every stop) - kill $50 busts 0.5% (25K Regular eval), 2.4% (50K eval), 2.9% (funded 25K), 6.1% (funded 50K) while kill $100 busts 0.0% everywhere. That is the real price of the narrower margin:
   it removes the ability to absorb a slippage of more than ~$50-$100 per micro beyond the planned stop. In the data, bar-to-bar opening gaps > 25 pts ($50/micro) happened 9 times in 5 years (max 42 pts = $84/micro, bars.py) and none went through one of our stops (planned-vs-actual excess = 0 for every simulated trade), so I rate the risk acceptable for MNQ micros in RTH.
   It is not acceptable to assume it for news spikes with 1-minute bars of > 50 pts (about 1,000 bars per year exceed that range) combined with a stop-market that slips - consider the Pro news rule (flat before news) as the actual protection.
6. Sensitivity (important): PM_FADE as coded in the controller (`automation/controller.py:508` passes `shrink_fraction` only for NOISE and AI_BIAS) is NOT tightened - it keeps the pause floor (risk base >= $500) and the plain worst-case check.
   Replaying it as coded (table "fade as in live controller") gives the same qualitative answer with more freezing/skips, and a larger kill-distance effect: Regular eval pass 49.7% -> 56.2% (+6.5 pt), funded 25K $1,077 -> $1,380 (+$303), 150K x4 $4,793 -> $4,958, 50K eval +3.9 pt - never worse at $50. Win rate unchanged (49.9% / 50.1%).
   Note the task description said both strategies are tightened; the code only tightens NOISE (and AI_BIAS).
7. Noise warning: rolling windows overlap heavily (about 10 independent 120-session windows in 5 years) and the freeze is an absorbing state, so small differences (<~3 pt) are noise and path chaos can swing results by 5-10 pt with a $25 change (see the stress table: kill $100 pass 42.3% vs kill $50 54.8% with +$25 per stop-out). The direction is consistent (kill $50 >= kill $100 in every comparison, 0 of 523 funded starts worse), the size is small.

## Compact comparison ($100 / $50 / $0 bound / no rule = old study assumption)
**Eval** (pass / bust / frozen / median sessions to pass / restart-chain median / skip share / value per eval / win rate all-NOISE-fade / avg win / avg loss / PF)

| config | kill | pass | bust | frozen | med | chain | skip | value/eval | win rate (all / NOISE / fade) | avg win | avg loss | PF | era1 pass/frozen | era2 pass/frozen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $100 | 55.5% | 0.0% | 43.7% | 35 | 59 | 34.2% | $739 | 50.7% / 45.7% / 59.3% | $144 | $111 | 1.34 | 65% / 34% | 47% / 53% |
| E25 1 micro x $250 (Regular) | $50 | 56.0% | 0.0% | 43.2% | 35 | 57 | 33.1% | $771 | 50.6% / 45.5% / 59.0% | $142 | $110 | 1.32 | 65% / 34% | 48% / 52% |
| E25 1 micro x $250 (Regular) | $0 | 56.3% | 0.0% | 42.8% | 35 | 57 | 32.6% | $773 | 50.3% / 45.2% / 58.9% | $141 | $110 | 1.30 | 65% / 34% | 49% / 51% |
| E25 1 micro x $250 (Regular) | no rule | 63.4% | 34.4% | 0.0% | 36 | 47 | 0.0% | - | 50.5% / 45.2% / 59.7% | $142 | $112 | 1.30 | 66% / 0% | 61% / 0% |
| E25 2 micros x $225 taper | $100 | 34.1% | 0.0% | 65.9% | 14 | 45 | 71.3% | $454 | 47.8% / 42.0% / 57.9% | $228 | $167 | 1.25 | 38% / 62% | 30% / 70% |
| E25 2 micros x $225 taper | $50 | 38.4% | 0.0% | 61.6% | 15 | 40 | 68.3% | $529 | 48.4% / 42.4% / 58.5% | $230 | $167 | 1.29 | 41% / 59% | 36% / 64% |
| E25 2 micros x $225 taper | $0 | 41.0% | 0.0% | 59.0% | 15 | 39 | 66.2% | $562 | 48.5% / 42.6% / 58.7% | $230 | $169 | 1.28 | 44% / 56% | 38% / 62% |
| E25 2 micros x $225 taper | no rule | 53.5% | 46.5% | 0.0% | 18 | 24 | 0.0% | - | 49.5% / 43.6% / 59.7% | $230 | $179 | 1.26 | 56% / 0% | 51% / 0% |
| E25 3 micros x $150 taper (High risk) | $100 | 31.2% | 0.0% | 68.8% | 8 | 42 | 80.8% | $416 | 46.4% / 40.8% / 56.2% | $292 | $199 | 1.27 | 35% / 65% | 28% / 72% |
| E25 3 micros x $150 taper (High risk) | $50 | 33.1% | 0.0% | 66.9% | 8 | 39 | 79.2% | $455 | 46.2% / 40.7% / 55.8% | $288 | $200 | 1.24 | 38% / 62% | 29% / 71% |
| E25 3 micros x $150 taper (High risk) | $0 | 34.6% | 0.0% | 65.4% | 8 | 37 | 78.0% | $474 | 46.0% / 40.3% / 56.0% | $299 | $205 | 1.24 | 38% / 62% | 32% / 68% |
| E25 3 micros x $150 taper (High risk) | no rule | 48.7% | 51.3% | 0.0% | 10 | 16 | 0.0% | - | 46.7% / 41.1% / 57.2% | $302 | $218 | 1.22 | 54% / 0% | 44% / 0% |
| E50 2 micros x $250 brake<50%->1 | $100 | 49.2% | 0.0% | 43.8% | 44 | 76 | 25.8% | $1,184 | 50.6% / 45.5% / 59.2% | $245 | $201 | 1.25 | 52% / 42% | 47% / 46% |
| E50 2 micros x $250 brake<50%->1 | $50 | 49.2% | 0.0% | 43.2% | 43 | 77 | 24.9% | $1,192 | 50.3% / 45.1% / 59.0% | $243 | $198 | 1.24 | 52% / 41% | 47% / 45% |
| E50 2 micros x $250 brake<50%->1 | $0 | 49.4% | 0.0% | 42.3% | 43 | 78 | 24.4% | $1,214 | 50.2% / 45.0% / 59.0% | $241 | $197 | 1.23 | 52% / 40% | 47% / 44% |
| E50 2 micros x $250 brake<50%->1 | no rule | 57.2% | 29.2% | 0.0% | 46 | 68 | 0.0% | - | 49.9% / 45.1% / 58.0% | $241 | $191 | 1.26 | 62% / 0% | 53% / 0% |

**Funded year 1** (take-home per account, 260 sessions)

| config | kill | take-home mean | median | bust | frozen | skip | win rate (all / NOISE / fade) | avg win | avg loss | PF | stopped at tightened stop (share of all trades) | era1 take/frozen | era2 take/frozen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F150 3 micros brake<50%->2, pay/5 | $100 | $4,913 | $4,291 | 0.0% | 31.5% | 30.3% | 50.8% / 45.5% / 59.5% | $412 | $322 | 1.32 | 0.2% | $5,719 / 15% | $3,962 / 51% |
| F150 3 micros brake<50%->2, pay/5 | $50 | $4,924 | $4,313 | 0.0% | 31.4% | 30.1% | 50.8% / 45.5% / 59.5% | $413 | $323 | 1.32 | 0.2% | $5,719 / 15% | $3,987 / 50% |
| F150 3 micros brake<50%->2, pay/5 | $0 | $4,933 | $4,313 | 0.0% | 31.0% | 29.5% | 50.8% / 45.5% / 59.5% | $413 | $323 | 1.32 | 0.2% | $5,736 / 14% | $3,987 / 50% |
| F150 3 micros brake<50%->2, pay/5 | no rule | $4,963 | $4,314 | 24.5% | 0.0% | 0.0% | 50.9% / 45.4% / 59.6% | $413 | $324 | 1.32 | 0.0% | $5,770 / 0% | $4,011 / 0% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | $4,744 | $2,700 | 0.0% | 52.4% | 51.9% | 50.8% / 45.3% / 59.7% | $513 | $405 | 1.31 | 0.7% | $5,164 / 48% | $4,250 / 58% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | $4,750 | $2,700 | 0.0% | 52.4% | 51.8% | 50.8% / 45.3% / 59.7% | $513 | $405 | 1.31 | 0.7% | $5,164 / 48% | $4,263 / 58% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $0 | $4,762 | $2,700 | 0.0% | 51.8% | 51.0% | 50.8% / 45.3% / 59.7% | $513 | $405 | 1.31 | 0.7% | $5,164 / 48% | $4,288 / 57% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | no rule | $5,532 | $5,138 | 27.9% | 0.0% | 0.0% | 51.0% / 45.5% / 59.9% | $514 | $407 | 1.32 | 0.0% | $6,442 / 0% | $4,460 / 0% |
| F25 1 micro (Regular), pay/10 | $100 | $1,332 | $0 | 0.0% | 78.8% | 70.7% | 51.0% / 46.2% / 59.2% | $136 | $111 | 1.28 | 1.9% | $1,535 / 71% | $1,093 / 88% |
| F25 1 micro (Regular), pay/10 | $50 | $1,377 | $465 | 0.0% | 76.7% | 68.5% | 50.9% / 46.0% / 59.1% | $136 | $111 | 1.28 | 1.7% | $1,579 / 69% | $1,139 / 86% |
| F25 1 micro (Regular), pay/10 | $0 | $1,372 | $465 | 0.0% | 76.5% | 68.0% | 50.8% / 45.9% / 59.0% | $135 | $111 | 1.26 | 1.6% | $1,579 / 69% | $1,129 / 86% |
| F25 1 micro (Regular), pay/10 | no rule | $1,646 | $900 | 56.6% | 0.0% | 0.0% | 51.1% / 45.8% / 59.7% | $142 | $112 | 1.33 | 0.0% | $1,794 / 0% | $1,472 / 0% |
| F50 2 micros brake<50%->1, pay/10 | $100 | $2,404 | $967 | 0.0% | 64.8% | 61.7% | 50.9% / 45.6% / 59.7% | $245 | $205 | 1.24 | 1.4% | $2,675 / 64% | $2,084 / 66% |
| F50 2 micros brake<50%->1, pay/10 | $50 | $2,421 | $1,063 | 0.0% | 62.9% | 60.2% | 50.8% / 45.5% / 59.6% | $243 | $203 | 1.23 | 1.3% | $2,706 / 61% | $2,084 / 65% |
| F50 2 micros brake<50%->1, pay/10 | $0 | $2,456 | $1,133 | 0.0% | 61.2% | 58.6% | 50.8% / 45.5% / 59.7% | $242 | $203 | 1.23 | 1.3% | $2,745 / 59% | $2,116 / 63% |
| F50 2 micros brake<50%->1, pay/10 | no rule | $2,933 | $2,614 | 44.2% | 0.0% | 0.0% | 50.7% / 45.4% / 59.4% | $255 | $202 | 1.30 | 0.0% | $3,386 / 0% | $2,399 / 0% |

**Trades near the floor (executed trades, intraday worst point on 1-minute bars)**

| config | kill | executed trades | within $100 of floor | within $50 | at/below floor | trades stopped at tightened stop (share of all) |
|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $100 | 19633 | 0 (0.0/1k) | 0 | 0 | 1.9% |
| E25 1 micro x $250 (Regular) | $50 | 20823 | 12 (0.6/1k) | 0 | 0 | 1.7% |
| E25 1 micro x $250 (Regular) | $0 | 21179 | 185 (8.7/1k) | 7 | 0 | 1.6% |
| E25 1 micro x $250 (Regular) | no rule | 24842 | 818 (32.9/1k) | 588 | 347 | 0.0% |
| E25 2 micros x $225 taper | $100 | 6276 | 0 (0.0/1k) | 0 | 0 | 7.4% |
| E25 2 micros x $225 taper | $50 | 6785 | 0 (0.0/1k) | 0 | 0 | 6.8% |
| E25 2 micros x $225 taper | $0 | 7202 | 65 (9.0/1k) | 0 | 0 | 6.3% |
| E25 2 micros x $225 taper | no rule | 9634 | 791 (82.1/1k) | 622 | 478 | 0.0% |
| E25 3 micros x $150 taper (High risk) | $100 | 3849 | 0 (0.0/1k) | 0 | 0 | 8.2% |
| E25 3 micros x $150 taper (High risk) | $50 | 4236 | 0 (0.0/1k) | 0 | 0 | 8.2% |
| E25 3 micros x $150 taper (High risk) | $0 | 4350 | 2 (0.5/1k) | 0 | 0 | 7.9% |
| E25 3 micros x $150 taper (High risk) | no rule | 6616 | 675 (102.0/1k) | 542 | 445 | 0.0% |
| E50 2 micros x $250 brake<50%->1 | $100 | 29072 | 0 (0.0/1k) | 0 | 0 | 2.0% |
| E50 2 micros x $250 brake<50%->1 | $50 | 30013 | 36 (1.2/1k) | 0 | 0 | 1.9% |
| E50 2 micros x $250 brake<50%->1 | $0 | 30755 | 183 (6.0/1k) | 32 | 0 | 1.8% |
| E50 2 micros x $250 brake<50%->1 | no rule | 36955 | 963 (26.1/1k) | 615 | 423 | 0.0% |
| F150 3 micros brake<50%->2, pay/5 | $100 | 108220 | 0 (0.0/1k) | 0 | 0 | 0.2% |
| F150 3 micros brake<50%->2, pay/5 | $50 | 108417 | 0 (0.0/1k) | 0 | 0 | 0.2% |
| F150 3 micros brake<50%->2, pay/5 | $0 | 108955 | 2 (0.0/1k) | 0 | 0 | 0.2% |
| F150 3 micros brake<50%->2, pay/5 | no rule | 115076 | 239 (2.1/1k) | 185 | 175 | 0.0% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | 84698 | 0 (0.0/1k) | 0 | 0 | 0.7% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | 84821 | 0 (0.0/1k) | 0 | 0 | 0.7% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $0 | 85739 | 47 (0.5/1k) | 0 | 0 | 0.7% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | no rule | 109333 | 524 (4.8/1k) | 456 | 336 | 0.0% |
| F25 1 micro (Regular), pay/10 | $100 | 59079 | 0 (0.0/1k) | 0 | 0 | 1.9% |
| F25 1 micro (Regular), pay/10 | $50 | 62533 | 29 (0.5/1k) | 0 | 0 | 1.7% |
| F25 1 micro (Regular), pay/10 | $0 | 63385 | 399 (6.3/1k) | 44 | 0 | 1.6% |
| F25 1 micro (Regular), pay/10 | no rule | 81329 | 1197 (14.7/1k) | 794 | 507 | 0.0% |
| F50 2 micros brake<50%->1, pay/10 | $100 | 72888 | 0 (0.0/1k) | 0 | 0 | 1.4% |
| F50 2 micros brake<50%->1, pay/10 | $50 | 74901 | 44 (0.6/1k) | 0 | 0 | 1.3% |
| F50 2 micros brake<50%->1, pay/10 | $0 | 77168 | 282 (3.7/1k) | 44 | 0 | 1.3% |
| F50 2 micros brake<50%->1, pay/10 | no rule | 98479 | 1340 (13.6/1k) | 859 | 559 | 0.0% |

## Paired outcome flips, kill $100 -> $50 (same 593 eval starts / 523 funded starts; paired.py)
| config | starts identical | gained pass | lost pass | (gained = frozen -> pass) |
|---|---|---|---|---|
| E25 Regular 1 x $250 | 588 / 593 | 4 | 1 | 4 |
| E25 High risk 3 x $150 | 582 / 593 | 11 | 0 | 11 |
| E25 2 x $225 | 567 / 593 | 26 | 0 | 26 |
| E50 2 x $250 | 587 / 593 | 1 | 1 | 1 |

Funded take-home, paired per start: 25K x1 mean +$44.5 (8 starts better, 0 worse, 515 identical of 523); 50K x2 +$16.7 (3 / 0); 150K x3 +$11.2 (1 / 0); 150K x4 +$6.0 (1 / 0).

## Minimum cushion (equity - floor) needed to trade (live rule, no DLL), by kill distance and MNQ price

| setup | price | kill $100 | kill $50 | kill $0 |
|---|---|---|---|---|
| 1 micro(s) x $250 | 11,000 | $199 | $149 | $99 |
| 1 micro(s) x $250 | 15,000 | $203 | $153 | $103 |
| 1 micro(s) x $250 | 21,000 | $243 | $193 | $143 |
| 1 micro(s) x $250 | 26,000 | $276 | $226 | $176 |
| 2 micro(s) x $225 | 11,000 | $252 | $202 | $152 |
| 2 micro(s) x $225 | 15,000 | $305 | $255 | $205 |
| 2 micro(s) x $225 | 21,000 | $385 | $335 | $285 |
| 2 micro(s) x $225 | 26,000 | $452 | $402 | $352 |
| 3 micro(s) x $150 | 11,000 | $328 | $278 | $228 |
| 3 micro(s) x $150 | 15,000 | $408 | $358 | $308 |
| 3 micro(s) x $150 | 21,000 | $528 | $478 | $428 |
| 3 micro(s) x $150 | 26,000 | $628 | $578 | $528 |

## Stress (artificial extra slippage on every stop-out, stress_tables.py)

Base replay has zero stop fills worse than planned; this injects an extra loss (total per trade, split over the micros) on every stop-out to see how much margin each kill distance leaves. Note the $25 row: kill $100 pass 42.3% vs 55.5% base is path chaos (freeze is absorbing), not a systematic effect.

| config | extra $ per stop-out | kill | pass/take | bust | frozen | trades within $100 of floor /1k | within $50 /1k | at/below floor (bust) /1k | realised within kill dist /1k | loss > plan+$50 /1k |
|---|---|---|---|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $25 | $100 | 42.3% | 0.0% | 57.7% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 1 micro x $250 (Regular) | $25 | $50 | 54.8% | 0.0% | 44.0% | 3.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 2 micros x $225 taper | $25 | $100 | 29.3% | 0.0% | 70.7% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 2 micros x $225 taper | $25 | $50 | 33.7% | 0.0% | 66.3% | 3.6 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 3 micros x $150 taper (High risk) | $25 | $100 | 29.2% | 0.0% | 70.8% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 3 micros x $150 taper (High risk) | $25 | $50 | 31.4% | 0.0% | 68.6% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E50 2 micros x $250 brake<50%->1 | $25 | $100 | 45.2% | 0.0% | 48.1% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E50 2 micros x $250 brake<50%->1 | $25 | $50 | 45.2% | 0.0% | 47.6% | 2.2 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 3 micros brake<50%->2, pay/5 | $25 | $100 | $4,680 | 0.0% | 32.7% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 3 micros brake<50%->2, pay/5 | $25 | $50 | $4,680 | 0.0% | 32.9% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $25 | $100 | $4,769 | 0.0% | 48.4% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $25 | $50 | $4,787 | 0.0% | 48.4% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F25 1 micro (Regular), pay/10 | $25 | $100 | $619 | 0.0% | 94.3% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F25 1 micro (Regular), pay/10 | $25 | $50 | $1,293 | 0.0% | 81.8% | 2.6 | 0.0 | 0.0 | 0.0 | 0.0 |
| F50 2 micros brake<50%->1, pay/10 | $25 | $100 | $2,079 | 0.0% | 75.3% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F50 2 micros brake<50%->1, pay/10 | $25 | $50 | $2,082 | 0.0% | 73.2% | 1.9 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 1 micro x $250 (Regular) | $50 | $100 | 40.8% | 0.0% | 59.2% | 1.0 | 0.0 | 0.0 | 1.0 | 0.0 |
| E25 1 micro x $250 (Regular) | $50 | $50 | 41.5% | 0.0% | 58.5% | 4.6 | 1.3 | 0.0 | 1.3 | 0.0 |
| E25 2 micros x $225 taper | $50 | $100 | 28.5% | 0.0% | 71.5% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 2 micros x $225 taper | $50 | $50 | 31.4% | 0.0% | 68.6% | 5.5 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 3 micros x $150 taper (High risk) | $50 | $100 | 25.3% | 0.0% | 74.7% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| E25 3 micros x $150 taper (High risk) | $50 | $50 | 28.0% | 0.0% | 72.0% | 1.1 | 0.0 | 0.0 | 0.0 | 0.0 |
| E50 2 micros x $250 brake<50%->1 | $50 | $100 | 44.7% | 0.0% | 48.2% | 1.3 | 0.0 | 0.0 | 1.3 | 0.0 |
| E50 2 micros x $250 brake<50%->1 | $50 | $50 | 44.7% | 0.0% | 48.1% | 5.5 | 0.3 | 0.0 | 0.3 | 0.0 |
| F150 3 micros brake<50%->2, pay/5 | $50 | $100 | $4,466 | 0.0% | 35.6% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 3 micros brake<50%->2, pay/5 | $50 | $50 | $4,466 | 0.0% | 35.4% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | $100 | $4,326 | 0.0% | 56.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | $50 | $4,340 | 0.0% | 55.1% | 0.4 | 0.0 | 0.0 | 0.0 | 0.0 |
| F25 1 micro (Regular), pay/10 | $50 | $100 | $620 | 0.0% | 93.5% | 0.8 | 0.0 | 0.0 | 0.8 | 0.0 |
| F25 1 micro (Regular), pay/10 | $50 | $50 | $578 | 0.0% | 93.9% | 4.8 | 1.6 | 0.0 | 1.6 | 0.0 |
| F50 2 micros brake<50%->1, pay/10 | $50 | $100 | $2,058 | 0.0% | 80.1% | 0.7 | 0.0 | 0.0 | 0.7 | 0.0 |
| F50 2 micros brake<50%->1, pay/10 | $50 | $50 | $2,056 | 0.0% | 79.2% | 3.7 | 0.3 | 0.0 | 0.3 | 0.0 |
| E25 1 micro x $250 (Regular) | $100 | $100 | 31.0% | 0.0% | 69.0% | 13.0 | 1.8 | 0.0 | 13.0 | 98.7 |
| E25 1 micro x $250 (Regular) | $100 | $50 | 34.9% | 0.5% | 64.6% | 19.5 | 8.9 | 0.2 | 8.7 | 99.5 |
| E25 2 micros x $225 taper | $100 | $100 | 25.1% | 0.0% | 74.9% | 3.9 | 0.0 | 0.0 | 3.9 | 158.7 |
| E25 2 micros x $225 taper | $100 | $50 | 28.3% | 0.0% | 71.7% | 15.5 | 4.4 | 0.0 | 4.4 | 151.9 |
| E25 3 micros x $150 taper (High risk) | $100 | $100 | 20.6% | 0.0% | 79.4% | 0.3 | 0.0 | 0.0 | 0.3 | 274.7 |
| E25 3 micros x $150 taper (High risk) | $100 | $50 | 22.4% | 0.0% | 77.6% | 4.7 | 0.3 | 0.0 | 0.3 | 281.2 |
| E50 2 micros x $250 brake<50%->1 | $100 | $100 | 41.0% | 0.0% | 51.1% | 2.6 | 0.3 | 0.0 | 2.6 | 97.3 |
| E50 2 micros x $250 brake<50%->1 | $100 | $50 | 41.1% | 2.4% | 48.6% | 5.7 | 2.2 | 0.5 | 1.7 | 98.6 |
| F150 3 micros brake<50%->2, pay/5 | $100 | $100 | $3,898 | 0.0% | 45.3% | 0.0 | 0.0 | 0.0 | 0.0 | 90.8 |
| F150 3 micros brake<50%->2, pay/5 | $100 | $50 | $3,898 | 0.0% | 45.3% | 0.8 | 0.0 | 0.0 | 0.0 | 90.8 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | $100 | $3,905 | 0.0% | 58.5% | 0.2 | 0.0 | 0.0 | 0.2 | 93.8 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | $50 | $3,906 | 0.0% | 58.3% | 0.8 | 0.5 | 0.0 | 0.5 | 93.3 |
| F25 1 micro (Regular), pay/10 | $100 | $100 | $443 | 0.0% | 95.8% | 8.8 | 1.3 | 0.0 | 8.8 | 96.5 |
| F25 1 micro (Regular), pay/10 | $100 | $50 | $463 | 2.9% | 94.5% | 13.6 | 7.3 | 0.5 | 6.8 | 96.5 |
| F50 2 micros brake<50%->1, pay/10 | $100 | $100 | $1,610 | 0.0% | 82.0% | 2.2 | 0.4 | 0.0 | 2.2 | 94.9 |
| F50 2 micros brake<50%->1, pay/10 | $100 | $50 | $1,610 | 6.1% | 76.5% | 4.9 | 2.1 | 0.5 | 1.5 | 95.0 |

## PM_FADE as coded in the controller (not tightened; pause floor $500 + worst-case check), fadecode

| config | kill | pass/take | bust | frozen | skip share | win rate all | NOISE | fade |
|---|---|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $100 | 49.7% | 0.0% | 50.3% | 41.0% | 49.9% | 44.5% | 59.9% |
| E25 1 micro x $250 (Regular) | $50 | 56.2% | 0.0% | 43.5% | 36.1% | 50.1% | 45.2% | 59.6% |
| E25 1 micro x $250 (Regular) | $0 | 57.7% | 0.0% | 40.6% | 34.3% | 49.7% | 45.1% | 59.3% |
| E25 2 micros x $225 taper | $100 | 36.4% | 0.0% | 63.6% | 69.4% | 48.2% | 42.2% | 60.1% |
| E25 2 micros x $225 taper | $50 | 40.6% | 0.0% | 59.4% | 66.6% | 48.7% | 42.6% | 60.4% |
| E25 2 micros x $225 taper | $0 | 44.4% | 0.0% | 55.6% | 64.1% | 49.3% | 43.5% | 60.5% |
| E25 3 micros x $150 taper (High risk) | $100 | 32.2% | 0.0% | 67.8% | 81.1% | 46.4% | 40.8% | 57.3% |
| E25 3 micros x $150 taper (High risk) | $50 | 35.2% | 0.0% | 64.8% | 77.9% | 46.8% | 40.9% | 57.2% |
| E25 3 micros x $150 taper (High risk) | $0 | 36.3% | 0.0% | 63.7% | 77.1% | 46.5% | 40.7% | 57.1% |
| E50 2 micros x $250 brake<50%->1 | $100 | 49.1% | 0.0% | 42.7% | 26.9% | 50.4% | 45.0% | 59.8% |
| E50 2 micros x $250 brake<50%->1 | $50 | 53.0% | 0.0% | 36.8% | 24.1% | 50.3% | 45.4% | 59.1% |
| E50 2 micros x $250 brake<50%->1 | $0 | 54.6% | 0.0% | 35.2% | 23.4% | 50.2% | 45.4% | 59.1% |
| F150 3 micros brake<50%->2, pay/5 | $100 | $4,913 | 0.0% | 31.5% | 29.9% | 50.8% | 45.4% | 59.6% |
| F150 3 micros brake<50%->2, pay/5 | $50 | $4,924 | 0.0% | 31.4% | 29.6% | 50.8% | 45.4% | 59.6% |
| F150 3 micros brake<50%->2, pay/5 | $0 | $4,933 | 0.0% | 31.0% | 29.4% | 50.8% | 45.4% | 59.6% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | $4,793 | 0.0% | 51.4% | 51.7% | 50.8% | 45.4% | 59.9% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | $4,958 | 0.0% | 47.8% | 48.3% | 50.7% | 45.4% | 59.6% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $0 | $4,980 | 0.0% | 47.0% | 47.4% | 50.8% | 45.4% | 59.7% |
| F25 1 micro (Regular), pay/10 | $100 | $1,077 | 0.0% | 78.8% | 73.8% | 50.6% | 45.6% | 59.4% |
| F25 1 micro (Regular), pay/10 | $50 | $1,380 | 0.0% | 70.0% | 67.0% | 50.8% | 45.8% | 59.5% |
| F25 1 micro (Regular), pay/10 | $0 | $1,444 | 0.0% | 66.7% | 63.5% | 50.5% | 45.7% | 59.1% |
| F50 2 micros brake<50%->1, pay/10 | $100 | $2,434 | 0.0% | 63.5% | 60.6% | 50.9% | 45.5% | 60.1% |
| F50 2 micros brake<50%->1, pay/10 | $50 | $2,534 | 0.0% | 57.7% | 55.7% | 50.6% | 45.4% | 59.6% |
| F50 2 micros brake<50%->1, pay/10 | $0 | $2,585 | 0.0% | 54.7% | 53.7% | 50.5% | 45.4% | 59.5% |

## Appendix: full tables (tables.py)

### EVAL: pass / bust / frozen

| config | kill | pass | bust | frozen | open | med sess to pass | p75 | restart-chain med | skip share | value/eval | era1 pass/bust/frozen/med/chain | era2 pass/bust/frozen/med/chain |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $100 | 55.5% | 0.0% | 43.7% | 0.8% | 35 | 55 | 59 | 34.2% | $739 | 65%/0%/34%/41/56 | 47%/0%/53%/26/66 |
| E25 1 micro x $250 (Regular) | $50 | 56.0% | 0.0% | 43.2% | 0.8% | 35 | 55 | 57 | 33.1% | $771 | 65%/0%/34%/41/56 | 48%/0%/52%/26/60 |
| E25 1 micro x $250 (Regular) | $0 | 56.3% | 0.0% | 42.8% | 0.8% | 35 | 55 | 57 | 32.6% | $773 | 65%/0%/34%/41/56 | 49%/0%/51%/26/60 |
| E25 1 micro x $250 (Regular) | no rule | 63.4% | 34.4% | 0.0% | 2.2% | 36 | 56 | 47 | 0.0% | - | 66%/31%/0%/41/56 | 61%/37%/0%/32/40 |
| E25 2 micros x $225 taper | $100 | 34.1% | 0.0% | 65.9% | 0.0% | 14 | 21 | 45 | 71.3% | $454 | 38%/0%/62%/17/50 | 30%/0%/70%/11/43 |
| E25 2 micros x $225 taper | $50 | 38.4% | 0.0% | 61.6% | 0.0% | 15 | 22 | 40 | 68.3% | $529 | 41%/0%/59%/17/44 | 36%/0%/64%/12/38 |
| E25 2 micros x $225 taper | $0 | 41.0% | 0.0% | 59.0% | 0.0% | 15 | 23 | 39 | 66.2% | $562 | 44%/0%/56%/17/46 | 38%/0%/62%/13/35 |
| E25 2 micros x $225 taper | no rule | 53.5% | 46.5% | 0.0% | 0.0% | 18 | 27 | 24 | 0.0% | - | 56%/44%/0%/19/25 | 51%/49%/0%/15/24 |
| E25 3 micros x $150 taper (High risk) | $100 | 31.2% | 0.0% | 68.8% | 0.0% | 8 | 15 | 42 | 80.8% | $416 | 35%/0%/65%/10/39 | 28%/0%/72%/6/44 |
| E25 3 micros x $150 taper (High risk) | $50 | 33.1% | 0.0% | 66.9% | 0.0% | 8 | 15 | 39 | 79.2% | $455 | 38%/0%/62%/10/37 | 29%/0%/71%/7/42 |
| E25 3 micros x $150 taper (High risk) | $0 | 34.6% | 0.0% | 65.4% | 0.0% | 8 | 15 | 37 | 78.0% | $474 | 38%/0%/62%/10/36 | 32%/0%/68%/7/38 |
| E25 3 micros x $150 taper (High risk) | no rule | 48.7% | 51.3% | 0.0% | 0.0% | 10 | 18 | 16 | 0.0% | - | 54%/46%/0%/12/17 | 44%/56%/0%/8/16 |
| E50 2 micros x $250 brake<50%->1 | $100 | 49.2% | 0.0% | 43.8% | 6.9% | 44 | 64 | 76 | 25.8% | $1,184 | 52%/0%/42%/48/77 | 47%/0%/46%/38/76 |
| E50 2 micros x $250 brake<50%->1 | $50 | 49.2% | 0.0% | 43.2% | 7.6% | 43 | 64 | 77 | 24.9% | $1,192 | 52%/0%/41%/48/77 | 47%/0%/45%/38/78 |
| E50 2 micros x $250 brake<50%->1 | $0 | 49.4% | 0.0% | 42.3% | 8.3% | 43 | 64 | 78 | 24.4% | $1,214 | 52%/0%/40%/48/77 | 47%/0%/44%/38/78 |
| E50 2 micros x $250 brake<50%->1 | no rule | 57.2% | 29.2% | 0.0% | 13.7% | 46 | 65 | 68 | 0.0% | - | 62%/21%/0%/52/73 | 53%/37%/0%/38/64 |

### FUNDED year 1 (260 sessions, rolling starts every 2)

| config | kill | take-home / account (mean) | median | bust | frozen (>=20 idle sessions) | any payout | max payouts | payouts/acct | skip share | era1 take/bust/frozen | era2 take/bust/frozen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F150 3 micros brake<50%->2, pay/5 | $100 | $4,913 | $4,291 | 0.0% | 31.5% | 74.0% | 8.8% | 2.11 | 30.3% | $5,719/0%/15% | $3,962/0%/51% |
| F150 3 micros brake<50%->2, pay/5 | $50 | $4,924 | $4,313 | 0.0% | 31.4% | 74.2% | 8.8% | 2.11 | 30.1% | $5,719/0%/15% | $3,987/0%/50% |
| F150 3 micros brake<50%->2, pay/5 | $0 | $4,933 | $4,313 | 0.0% | 31.0% | 74.6% | 8.8% | 2.11 | 29.5% | $5,736/0%/14% | $3,987/0%/50% |
| F150 3 micros brake<50%->2, pay/5 | no rule | $4,963 | $4,314 | 24.5% | 0.0% | 75.7% | 8.8% | 2.13 | 0.0% | $5,770/9%/0% | $4,011/43%/0% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | $4,744 | $2,700 | 0.0% | 52.4% | 59.1% | 9.6% | 1.80 | 51.9% | $5,164/0%/48% | $4,250/0%/58% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | $4,750 | $2,700 | 0.0% | 52.4% | 59.1% | 9.6% | 1.80 | 51.8% | $5,164/0%/48% | $4,263/0%/58% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $0 | $4,762 | $2,700 | 0.0% | 51.8% | 59.3% | 9.6% | 1.80 | 51.0% | $5,164/0%/48% | $4,288/0%/57% |
| F150 4 micros (High risk) brake<50%->2, pay/5 | no rule | $5,532 | $5,138 | 27.9% | 0.0% | 75.5% | 9.6% | 2.11 | 0.0% | $6,442/13%/0% | $4,460/45%/0% |
| F25 1 micro (Regular), pay/10 | $100 | $1,332 | $0 | 0.0% | 78.8% | 48.9% | 4.2% | 1.37 | 70.7% | $1,535/0%/71% | $1,093/0%/88% |
| F25 1 micro (Regular), pay/10 | $50 | $1,377 | $465 | 0.0% | 76.7% | 50.3% | 4.2% | 1.41 | 68.5% | $1,579/0%/69% | $1,139/0%/86% |
| F25 1 micro (Regular), pay/10 | $0 | $1,372 | $465 | 0.0% | 76.5% | 50.1% | 4.2% | 1.41 | 68.0% | $1,579/0%/69% | $1,129/0%/86% |
| F25 1 micro (Regular), pay/10 | no rule | $1,646 | $900 | 56.6% | 0.0% | 58.3% | 4.2% | 1.65 | 0.0% | $1,794/57%/0% | $1,472/56%/0% |
| F50 2 micros brake<50%->1, pay/10 | $100 | $2,404 | $967 | 0.0% | 64.8% | 54.7% | 3.6% | 1.40 | 61.7% | $2,675/0%/64% | $2,084/0%/66% |
| F50 2 micros brake<50%->1, pay/10 | $50 | $2,421 | $1,063 | 0.0% | 62.9% | 55.1% | 3.6% | 1.41 | 60.2% | $2,706/0%/61% | $2,084/0%/65% |
| F50 2 micros brake<50%->1, pay/10 | $0 | $2,456 | $1,133 | 0.0% | 61.2% | 56.0% | 3.6% | 1.43 | 58.6% | $2,745/0%/59% | $2,116/0%/63% |
| F50 2 micros brake<50%->1, pay/10 | no rule | $2,933 | $2,614 | 44.2% | 0.0% | 65.8% | 3.6% | 1.70 | 0.0% | $3,386/40%/0% | $2,399/49%/0% |

### WIN RATES and trade statistics (executed trades, all rolling-start horizon runs)

| config | kill | trades | win rate all | NOISE | fade | avg win | avg loss | PF all | PF NOISE | PF fade | stopped out (all) | tightened trades | stopped at tightened stop (share of all trades) | stop-out share among tightened | avg stop $/micro | avg micros |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $100 | 19633 | 50.7% | 45.7% | 59.3% | $144 | $-111 | 1.34 | 1.35 | 1.33 | 10.1% | 12.4% | 1.9% | 15.3% | $240 | 1.00 |
| E25 1 micro x $250 (Regular) | $50 | 20823 | 50.6% | 45.5% | 59.0% | $142 | $-110 | 1.32 | 1.33 | 1.29 | 9.7% | 10.7% | 1.7% | 15.5% | $241 | 1.00 |
| E25 1 micro x $250 (Regular) | $0 | 21179 | 50.3% | 45.2% | 58.9% | $141 | $-110 | 1.30 | 1.30 | 1.30 | 10.0% | 8.8% | 1.6% | 17.6% | $243 | 1.00 |
| E25 1 micro x $250 (Regular) | no rule | 24842 | 50.5% | 45.2% | 59.7% | $142 | $-112 | 1.30 | 1.30 | 1.28 | 9.0% | 0.0% | 0.0% | - | $248 | 1.00 |
| E25 2 micros x $225 taper | $100 | 6276 | 47.8% | 42.0% | 57.9% | $228 | $-167 | 1.25 | 1.26 | 1.23 | 15.9% | 27.9% | 7.4% | 26.6% | $204 | 1.61 |
| E25 2 micros x $225 taper | $50 | 6785 | 48.4% | 42.4% | 58.5% | $230 | $-167 | 1.29 | 1.30 | 1.27 | 15.2% | 26.1% | 6.8% | 26.0% | $206 | 1.61 |
| E25 2 micros x $225 taper | $0 | 7202 | 48.5% | 42.6% | 58.7% | $230 | $-169 | 1.28 | 1.29 | 1.28 | 14.9% | 24.0% | 6.3% | 26.3% | $207 | 1.61 |
| E25 2 micros x $225 taper | no rule | 9634 | 49.5% | 43.6% | 59.7% | $230 | $-179 | 1.26 | 1.27 | 1.26 | 11.6% | 0.0% | 0.0% | - | $223 | 1.64 |
| E25 3 micros x $150 taper (High risk) | $100 | 3849 | 46.4% | 40.8% | 56.2% | $292 | $-199 | 1.27 | 1.33 | 1.16 | 27.0% | 19.7% | 8.2% | 41.6% | $139 | 2.09 |
| E25 3 micros x $150 taper (High risk) | $50 | 4236 | 46.2% | 40.7% | 55.8% | $288 | $-200 | 1.24 | 1.30 | 1.13 | 27.2% | 19.7% | 8.2% | 41.4% | $140 | 2.09 |
| E25 3 micros x $150 taper (High risk) | $0 | 4350 | 46.0% | 40.3% | 56.0% | $299 | $-205 | 1.24 | 1.28 | 1.15 | 27.5% | 19.1% | 7.9% | 41.3% | $141 | 2.13 |
| E25 3 micros x $150 taper (High risk) | no rule | 6616 | 46.7% | 41.1% | 57.2% | $302 | $-218 | 1.22 | 1.24 | 1.18 | 25.2% | 0.0% | 0.0% | - | $148 | 2.16 |
| E50 2 micros x $250 brake<50%->1 | $100 | 29072 | 50.6% | 45.5% | 59.2% | $245 | $-201 | 1.25 | 1.24 | 1.27 | 10.8% | 6.4% | 2.0% | 30.4% | $244 | 1.74 |
| E50 2 micros x $250 brake<50%->1 | $50 | 30013 | 50.3% | 45.1% | 59.0% | $243 | $-198 | 1.24 | 1.23 | 1.26 | 10.9% | 6.2% | 1.9% | 31.0% | $244 | 1.73 |
| E50 2 micros x $250 brake<50%->1 | $0 | 30755 | 50.2% | 45.0% | 59.0% | $241 | $-197 | 1.23 | 1.22 | 1.26 | 10.9% | 5.8% | 1.8% | 31.7% | $244 | 1.71 |
| E50 2 micros x $250 brake<50%->1 | no rule | 36955 | 49.9% | 45.1% | 58.0% | $241 | $-191 | 1.26 | 1.27 | 1.25 | 10.3% | 0.0% | 0.0% | - | $248 | 1.63 |
| F150 3 micros brake<50%->2, pay/5 | $100 | 108220 | 50.8% | 45.5% | 59.5% | $412 | $-322 | 1.32 | 1.35 | 1.27 | 9.4% | 1.1% | 0.2% | 19.1% | $247 | 2.87 |
| F150 3 micros brake<50%->2, pay/5 | $50 | 108417 | 50.8% | 45.5% | 59.5% | $413 | $-323 | 1.32 | 1.35 | 1.27 | 9.4% | 1.0% | 0.2% | 19.6% | $247 | 2.87 |
| F150 3 micros brake<50%->2, pay/5 | $0 | 108955 | 50.8% | 45.5% | 59.5% | $413 | $-323 | 1.32 | 1.35 | 1.26 | 9.4% | 1.0% | 0.2% | 19.9% | $248 | 2.87 |
| F150 3 micros brake<50%->2, pay/5 | no rule | 115076 | 50.9% | 45.4% | 59.6% | $413 | $-324 | 1.32 | 1.35 | 1.26 | 9.5% | 0.0% | 0.0% | - | $248 | 2.86 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | 84698 | 50.8% | 45.3% | 59.7% | $513 | $-405 | 1.31 | 1.32 | 1.28 | 9.3% | 3.1% | 0.7% | 23.1% | $246 | 3.67 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | 84821 | 50.8% | 45.3% | 59.7% | $513 | $-405 | 1.31 | 1.32 | 1.28 | 9.3% | 2.8% | 0.7% | 25.2% | $246 | 3.67 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $0 | 85739 | 50.8% | 45.3% | 59.7% | $513 | $-405 | 1.31 | 1.32 | 1.28 | 9.3% | 2.6% | 0.7% | 25.1% | $246 | 3.66 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | no rule | 109333 | 51.0% | 45.5% | 59.9% | $514 | $-407 | 1.32 | 1.33 | 1.28 | 9.3% | 0.0% | 0.0% | - | $248 | 3.59 |
| F25 1 micro (Regular), pay/10 | $100 | 59079 | 51.0% | 46.2% | 59.2% | $136 | $-111 | 1.28 | 1.31 | 1.23 | 10.3% | 8.3% | 1.9% | 23.0% | $242 | 1.00 |
| F25 1 micro (Regular), pay/10 | $50 | 62533 | 50.9% | 46.0% | 59.1% | $136 | $-111 | 1.28 | 1.30 | 1.23 | 10.1% | 7.7% | 1.7% | 21.6% | $243 | 1.00 |
| F25 1 micro (Regular), pay/10 | $0 | 63385 | 50.8% | 45.9% | 59.0% | $135 | $-111 | 1.26 | 1.29 | 1.21 | 10.1% | 7.2% | 1.6% | 22.4% | $244 | 1.00 |
| F25 1 micro (Regular), pay/10 | no rule | 81329 | 51.1% | 45.8% | 59.7% | $142 | $-112 | 1.33 | 1.37 | 1.25 | 9.3% | 0.0% | 0.0% | - | $248 | 1.00 |
| F50 2 micros brake<50%->1, pay/10 | $100 | 72888 | 50.9% | 45.6% | 59.7% | $245 | $-205 | 1.24 | 1.23 | 1.25 | 9.9% | 5.5% | 1.4% | 25.4% | $245 | 1.83 |
| F50 2 micros brake<50%->1, pay/10 | $50 | 74901 | 50.8% | 45.5% | 59.6% | $243 | $-203 | 1.23 | 1.23 | 1.25 | 9.8% | 5.1% | 1.3% | 26.3% | $245 | 1.82 |
| F50 2 micros brake<50%->1, pay/10 | $0 | 77168 | 50.8% | 45.5% | 59.7% | $242 | $-203 | 1.23 | 1.22 | 1.25 | 9.8% | 4.7% | 1.3% | 27.2% | $245 | 1.81 |
| F50 2 micros brake<50%->1, pay/10 | no rule | 98479 | 50.7% | 45.4% | 59.4% | $255 | $-202 | 1.30 | 1.32 | 1.27 | 9.3% | 0.0% | 0.0% | - | $248 | 1.79 |

### SKIPS (share of signals) and tail events (count per 1,000 executed trades)

| config | kill | skip share | NEAR_MLL | DRAWDOWN_TOO_DEEP | WORST_CASE | intraday equity within $100 of floor | within $50 | at/below floor | within kill dist | realised equity within kill dist (kill-switch trips) per 1,000 | loss > plan | > plan+$25 | > plan+$40 | > plan+$50 | max excess $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E25 1 micro x $250 (Regular) | $100 | 34.2% | 0.0% | 33.9% | 0.3% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 1 micro x $250 (Regular) | $50 | 33.1% | 0.0% | 33.0% | 0.1% | 0.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 1 micro x $250 (Regular) | $0 | 32.6% | 0.0% | 32.6% | 0.0% | 8.7 | 0.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 1 micro x $250 (Regular) | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 32.9 | 23.7 | 14.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 2 micros x $225 taper | $100 | 71.3% | 0.0% | 71.3% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 2 micros x $225 taper | $50 | 68.3% | 0.0% | 68.3% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 2 micros x $225 taper | $0 | 66.2% | 0.0% | 66.2% | 0.0% | 9.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 2 micros x $225 taper | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 82.1 | 64.6 | 49.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 3 micros x $150 taper (High risk) | $100 | 80.8% | 0.0% | 80.8% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 3 micros x $150 taper (High risk) | $50 | 79.2% | 0.0% | 79.2% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 3 micros x $150 taper (High risk) | $0 | 78.0% | 0.0% | 78.0% | 0.0% | 0.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E25 3 micros x $150 taper (High risk) | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 102.0 | 81.9 | 67.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E50 2 micros x $250 brake<50%->1 | $100 | 25.8% | 0.0% | 25.7% | 0.1% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E50 2 micros x $250 brake<50%->1 | $50 | 24.9% | 0.0% | 24.9% | 0.0% | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E50 2 micros x $250 brake<50%->1 | $0 | 24.4% | 0.0% | 24.4% | 0.0% | 6.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| E50 2 micros x $250 brake<50%->1 | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 26.1 | 16.6 | 11.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 3 micros brake<50%->2, pay/5 | $100 | 30.3% | 0.0% | 30.3% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 3 micros brake<50%->2, pay/5 | $50 | 30.1% | 0.0% | 30.1% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 3 micros brake<50%->2, pay/5 | $0 | 29.5% | 0.0% | 29.5% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 3 micros brake<50%->2, pay/5 | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 2.1 | 1.6 | 1.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $100 | 51.9% | 0.0% | 51.9% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $50 | 51.8% | 0.0% | 51.8% | 0.0% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | $0 | 51.0% | 0.0% | 51.0% | 0.0% | 0.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F150 4 micros (High risk) brake<50%->2, pay/5 | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 4.8 | 4.2 | 3.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F25 1 micro (Regular), pay/10 | $100 | 70.7% | 0.0% | 68.1% | 2.6% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F25 1 micro (Regular), pay/10 | $50 | 68.5% | 0.0% | 64.0% | 4.6% | 0.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F25 1 micro (Regular), pay/10 | $0 | 68.0% | 0.0% | 64.6% | 3.4% | 6.3 | 0.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F25 1 micro (Regular), pay/10 | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 14.7 | 9.8 | 6.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F50 2 micros brake<50%->1, pay/10 | $100 | 61.7% | 0.0% | 58.8% | 2.9% | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F50 2 micros brake<50%->1, pay/10 | $50 | 60.2% | 0.0% | 56.8% | 3.4% | 0.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F50 2 micros brake<50%->1, pay/10 | $0 | 58.6% | 0.0% | 57.9% | 0.7% | 3.7 | 0.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| F50 2 micros brake<50%->1, pay/10 | no rule | 0.0% | 0.0% | 0.0% | 0.0% | 13.6 | 8.7 | 5.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |

## Caveats
- Research replay on 1-minute bars (no intrabar order path: stop vs target within one bar resolved as stop first for fade; MNQ only; news not modelled). Rolling starts overlap strongly (about 10 independent windows); era split shows era 2 (2024-2026) freezes far more (e.g. funded 25K 86-88% frozen) than era 1.
- "Frozen" = 20 sessions in a row without an executed trade (sticky flag in the funded run). It counts any permanent skip state (DRAWDOWN_TOO_DEEP) plus idle stretches; the real controller's kill-switch pause (equity - MLL <= kill) never auto-resumes, which the replay only hits in the stress runs.
- Funded configs use the $250/micro base stop for every size (150K x4 is therefore $1,000 of stop risk per trade, well inside the 150K cushion).
- Value per eval uses the year-1 take-home of the 1-micro 25K funded account for all 25K evals (so High risk is not credited with a larger funded stake).
