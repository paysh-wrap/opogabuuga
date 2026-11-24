# Model QA: NOISE + CANDACE + late-day leg (independent audit, 2026-11-24)

Scope: the research behind the live MNQ strategy (NOISE, CANDACE ICT D154, late-day D166) and the Lucid eval pass-rate sims.
Data: /home/user/days.pkl (MNQ RTH 1-min, 1,266 days 2021-10-01..2026-10-30; MES not used). No Databento, no repo code changed.
Pick = 2021-10..2023-12, judge = 2024-01..2026-10 (the user's rule). Costs as in the studies ($1 fee + 1 tick each side = $2/micro RT) unless stated.
Every number below was recomputed here. Scripts: `model_qa_scripts/` (gen.py loads the session-20 generator on days.pkl; `simp/run*.py`
need patched copies of pass_fastest/sim150.py + gen_lib.py with PKL/SCR/WT pointed at days.pkl and a scratch folder, made with `sed`).

Reproduction first: the NOISE BASE stream reproduces exactly (654 trades, $19,293 net, same as session20 streams_BASE.csv).
The 150K pass-fastest row "#2 NOISE 4@$100 + CAND 3 + brake" reproduces exactly (pass 79.1 %, judge 63.7 %, profit $78,612).

## Verdict per leg

| Leg | Verdict | One line |
|---|---|---|
| NOISE | **Sound, with caveats** | Real edge: PF 1.52, beats every one of 200 random-direction runs, flat plateau across parameters, cost-robust. Recent-window PF is noisy (CI includes 0.90). |
| CANDACE ICT (D154) | **Unsound as evidence / caveated as a small leg** | PF 1.22, CI 0.92-1.59, held-out CI 0.76-1.75. Only at the 95th percentile of random-direction. Live engine sees overnight bars the research never had. |
| Late-day (D166) | **Unsound** | Judge PF 1.12 (CI 0.89-1.40) is inside the random-direction band (p95 1.18). Its own study said "do not build". Lowers judge pass on 100K/150K. |
| Eval pass-rate sims | **Caveated (optimistic in practice)** | Rule logic is careful. But pass % swings 7-12 pts on small, realistic changes, and rests on about 11 independent windows. |

## Ranked findings

### 1. HIGH - Pass % is fragile and has few independent samples
- What: the headline pass rates (e.g. 150K 79 %, 50K 69 %) come from rolling starts on every day. Starts share the same future path.
- Evidence (150K #2 config, sim150.py reproduced):
  - Pass % by start half-year: 2022H1-2023H2 100 %, 2024H2 90 %, **2025H1 14 %**, 2025H2 100 %, 2026H1 57 % (43 % still open). It is regime on/off, not a probability per account.
  - Median 111 sessions to pass over 1,252 starts = about **11 independent windows**. A 79 % estimate from about 11 windows has a binomial 95 % range of roughly 55-100 %.
  - Small perturbations move it a lot, and not monotonically:

| change (150K #2) | pass % | judge % | profit $ |
|---|---|---|---|
| as reported | 79.1 | 63.7 | 78,612 |
| CANDACE +$2 RT per micro | 66.8 | 51.9 | 76,794 |
| CANDACE off | 69.5 | 46.1 | 70,502 |
| NOISE +$2 RT per micro | 71.4 | 60.6 | 72,820 |
| both +$2 RT | 69.7 | 60.0 | 71,002 |
| kill distance $100 instead of $50 | 72.3 | 51.9 | 78,612 |

- Impact: config ranking by 0.1-2 pt differences (pass_fastest RESULTS.md "0.1 pt better (about 1 start)") is noise. Fast-pass rows were picked from 108-137 configs per plan, in rounds (pass_fastest, passfloor, pass70, final_search), with the judge window inside the selection rule ("judge pass >= BASE judge - 3"). There is no untouched hold-out left for the fast-pass rows.
- Fix/test: report pass % with a block-bootstrap CI over history (sim150.boot_intervals exists; use it for every row shown in the UI). Show the per-half-year table. Freeze one never-touched window (e.g. the next 6 months of paper/live data) before any further row changes. Treat differences under ~10 pts as ties.

### 2. HIGH - CANDACE live engine is not the backtested engine (overnight bars)
- What: research ran CANDACE on RTH-only bars. Live replays "today's bars (all hours stored)".
- Evidence: strategy_service.py:1542-1559 loads 4 days of all-hours bars; `today` = bars after 00:00 ET, `hist` = before. In candace_ict.py:229-238 and pools() (158-182) the SESSION high/low, swing/equal pools, PDH/PDL (whole previous calendar day incl. evening Globex) and 1-hour FVGs (`prior[-60*24:]` = 1 all-hours day live vs ~3.7 RTH days in research) all change with overnight bars. CANDACE_ICT_RULES.md:72 itself says overnight could not be tested.
- Impact: the 310-trade, PF 1.22 result does not describe what live trades. Trade count, side and grade mix will differ. Unknown sign.
- Fix/test: either feed replay_day RTH-only bars live (match the evidence), or get all-hours MNQ history and re-run the study. Add a test that replays one recorded live day through both paths and compares signals.

### 3. HIGH - CANDACE edge is not statistically established
- What: 310 trades (D154), avg $5.95/trade/micro. 286 of 310 are grade C.
- Evidence (streams_candace_base.csv = D154 stream, recomputed):
  - PF 1.22 all; pick 1.27 (n 160), judge 1.18 (n 150). By year: 2021 0.58, 2022 1.55, 2023 1.27, **2024 0.80**, 2025 1.20, 2026 1.52.
  - Trade bootstrap PF 95 % CI: all **0.92-1.59** (P(net <= 0) 8 %); judge **0.76-1.75** (P(net <= 0) 22 %).
  - Random direction at the same moments, same stop/target distances, stop-first: PF median 1.02, p95 1.22. Real PF sits at the **95th percentile** (one-sided p about 0.05). Opposite direction: PF 0.84.
  - Variants tried before D154: about 15 [GAP] parameters chosen by the builder (config.py:909-929), ~12 one-factor changes in candace_trade_more, 5 keep-sweeps variants, window tests. A p of 0.05 after ~20 tries is chance level.
  - Costs: +$1 RT -> PF 1.18, +$2 -> 1.14, +$3 -> 1.10. Edge per trade is about 3 RT costs.
  - News (not in the research): live blocks entries from 09:45 and flattens at 09:58 before 10:00 high-impact releases (controller.py:1772-1795, `no_entry_before_news_min: 15`, `news_flatten_before_min: 2`). With only ISM Mfg + ISM Services approximated as 10:00 events, CANDACE drops to 282 trades, PF 1.20, net $1,532 (-17 %). A full calendar would cut more.
  - D154 itself failed the held-out rule (judge $814 vs BASE $1,211, DECISIONS.md:1161); adopted on the 5-year view by explicit user exception.
- Impact on pass %: CANDACE carries a large share of fast-pass speed. 150K: CANDACE off -> pass 69.5 % and judge 46.1 % (from 79.1 / 63.7). If CANDACE's true PF is about 1.0, the fast-pass rows that rely on it (150K C5 + grow, 100K C3, 50K C4, 25K C2) are tuned to noise.
- Fix/test: keep CANDACE at the smallest size until about 300 more out-of-sample (paper or live) trades show PF > 1.15. Pre-register that bar now. Add the news blackout to the CANDACE research sim.

### 4. HIGH - Late-day leg (D166) is at random-direction level held-out
- What: 15:00 entry with the 09:30-13:30 trend, 60 pt stop, flat 15:59. Picked from 60 configs inside a 328-config, 6-idea screen.
- Evidence (trades_lastmom239.csv, recomputed): pick PF 1.50 (n 465), judge **1.12** (n 602). By year 2022 1.75, 2023 1.24, 2024 1.05, 2025 1.26, 2026 1.04. Judge bootstrap CI **0.89-1.40**, P(net <= 0) 18 %. Judge random-direction PF median 1.00, p95 **1.18** (new_edge RESULTS.md says p95 1.13). On days NOISE is flat at 15:00 (what live can trade under one position) judge PF 1.16; on days NOISE is busy PF 1.00.
- new_edge/RESULTS.md: "fails the held-out PF gate ... Do not build it". late_leg_sizes/RESULTS.md: judge pass falls 10 pts (100K) and 9.5 pts (150K) with the chosen sizes; 150K sits exactly on the 70 % floor.
- Impact: adds variance and speed in-sample, not a proven edge. It breaks the binding "improve on held-out" rule on 2 of 3 plans where it is on.
- Fix/test: keep `fast_pass_late_day` OFF. If kept, 1 micro, 50K only, and re-judge on data after 2026-11 only.

### 5. MEDIUM - NOISE parity test does not cover what runs live or what the eval sims use
- What: tests/unit/test_noise_engine.py:147 compares backtest/noise_sim.simulate (engine decide()) with docs/results/tools/noise_area.py on 40 synthetic days (line 102).
- Gaps: (a) neither side has the profit lock (+100 -> entry+10), the Monday skip, or the "locked exit ends the day" rule; (b) the eval/fast-pass sims use a third implementation, session20 noise3.gen, which is never parity-tested; (c) the live path is signals/strategy_service.run_noise (278-384) + controller + management/profit_lock, not noise_sim. Live adds news blackout, structure_check, AI ledger blocks, HEDGE_LOCK, and counts skipped signals toward max entries (`entries = len(sigs)`, line 326); (d) live builds the $ stop from the check-bar close, research from the fill.
- Impact: the "trade-for-trade parity" claim (noise.py:4) is true only for the no-lock, Mondays-on, 1 % or $250-stop version. Probably small P&L impact, but untested.
- Fix/test: add a parity test of noise3.gen (BASE: lock + Monday skip + $ stop) vs noise_sim with the lock on real days.pkl days (e.g. 60 days), and a replay test that drives run_noise with stored bars and compares to noise3.gen trades.

### 6. MEDIUM - NOISE "roll guard" is really a gap filter and misses most rolls
- What: days with |open / prior close - 1| > 1.5 % are skipped (noise3.py:57; live roll_guard, strategy_service.py:314).
- Evidence: 109 of 1,266 days (8.6 %) are skipped. Most are real market gaps (2022 bear market, Apr 2025 tariffs). True roll gaps on the unadjusted series are often 1.0-1.5 % (2023-03-14 +1.23 %, 2023-06-14 +1.24 %, 2024-03-18 +1.25 %, 2025-06-18 +1.21 %, 2026-03-16 +1.06 %) and are traded with an old-contract prior close. That shifts the lower band by the roll spread (shorts suppressed that day).
- Sensitivity: guard 1.5 % net $19,293 PF 1.52; no guard $20,854 PF 1.52 (pick +$2,033, judge -$472). Small either way.
- Impact: correctness, not PF. Live TradingView MNQ1! may roll on different days than Databento .v.0, so live and research skip different days.
- Fix/test: skip (or back-adjust) on a roll calendar, not on a gap threshold. Measure the gap filter separately under the held-out rule.

### 7. MEDIUM - "Last 12 months PF 1.72" is not clean held-out and is noisy (answers the lead's question)
- The last 12 months were the session-20 judge window used to accept the lock and Monday skip, and session 20 picked on 2019-05..2025-11 (lib.py:4), not 2021-23. So it is no longer held out.
- On days.pkl the same window (2025-11-06..2026-10-30) gives n = 118, PF **1.58**, bootstrap CI **0.90-2.64**, P(net <= 0) 6 %. Since mid-2024: n = 286, PF 1.58, CI **1.11-2.19**, P(net <= 0) 0.6 %. 2025 alone: PF 1.13, CI 0.61-1.93.
- Rolling 12-month PF over 5 years: min 1.02, p10 1.18, median 1.55, p90 1.87. 23 % of windows show >= 1.72. If the true PF were the 5-year 1.52, a 12-month window would be >= 1.58 43 % of the time and < 1.2 19 % of the time.
- Luck vs edge: a single 12-month PF of 1.6-1.7 says little (zero-edge null still gives >= 1.58 about 4 % of the time). The stronger evidence is the 5-year record (PF 1.52, CI 1.22-1.88; pick 1.55 / judge 1.49) and random-direction: 0 of 200 runs reach 1.52 (median 1.07, max 1.36).
- External decay (Strategy Trials on SPY, Bullring on S&P futures): our MNQ data does not show the decay since mid-2024 (PF 1.58). Reasons that may differ: NQ trends more than SPX, the lock and Monday rules, and fixed 1-micro sizing (no 4x vol leverage). But a 2025-style year (PF 1.13) is fully consistent with "weak edge after publication". Plan for a true PF of 1.2-1.4, not 1.7.
- Costs do not decide for MNQ at this size: $2 RT is about 0.5 bp of notional. NOISE at +$1 / +$2 / +$4 RT extra: since-mid-2024 PF 1.56 / 1.54 / 1.50. Lucid lists $0.50/side commission (LUCID_RULES.md); confirm it includes exchange/NFA fees (about $0.35/side more if not). 1 tick/side slippage is fair for 1-6 micros at hourly checks; stop exits in fast tape may slip 2-4 ticks, still small vs $29.50/trade.
- Fix: quote NOISE as "PF about 1.5 over 5 years, recent 12 months not distinguishable from that". Drop "held out" from the 1.72 line in MAIN_STRATEGIES_BRIEF_2026-11-22.md:11.

### 8. MEDIUM - News handling differs between research and live
- Research: no news model for any leg (session20 RESULTS.md:169). Live: entries blocked 15 min before to 1 min after high-impact USD news; all accounts flattened 2 min before (controller.py:1772-1795), even on EVAL where Lucid allows news.
- NOISE approximation (ISM Mfg/Services at 10:00 block the 10:00 entry; FOMC days block 14:00 and flatten at 13:58): 638 trades, PF 1.55, net $19,474 vs $19,293. No harm on this partial calendar. CANDACE: -17 % (finding 3).
- Fix/test: put the real calendar (the app's own source) into both research sims; re-measure pass % with it.

### 9. LOW - NOISE tweaks: small, partly against the held-out rule
- Under pick 2021-23 / judge 2024-26: the profit lock lowers judge net ($10,826 vs $10,989 without it) while raising PF; Monday skip raises judge net +$567 and lowers pick net -$356. Both tiny vs noise.
- Neighbourhood is a plateau (look 10/14/20, step 60, max 3: PF 1.44-1.52 all; both halves 1.35-1.57). The core rules come from the paper, so selection bias is low for NOISE.

### 10. LOW - Fill and cost mechanics are mostly fair
- NOISE: decision on the check-bar close, fill next-bar open +/- 1 tick, stop checked first every bar, gaps through the stop fill at the open, lock moves the stop only from the next bar. Sigma uses only prior days (noise3.py moves[i-look:i]). VWAP in days.pkl is causal: 0 violations in 492,474 bar steps (each step moves toward the bar's typical price, never past it; bar 0 = typical price on all days). No missing minutes.
- CANDACE: entry at the signal-bar close; next-open fill changes almost nothing (PF 1.23). Stop-first, 0 stops gapped through, 0 touch-only targets. Fine.
- Pass sim (sim150.py): EOD trailing MLL + lock, DLL incl. LucidScale, 40 % consistency at pass + 38 % day stop, intraday kill using NOISE MAE, room check, one position. Bust checked after each closed trade (conservative vs Lucid EOD). The DLL is not checked against intra-trade MAE (live Lucid would liquidate), small at current sizes. Kill distance is $50 (yaml line 370, D71); CLAUDE.md still says $100: fix the doc.

### 11. INFO - Headline numbers disagree across docs
- noise.py:3 says held-out 2024-26 "440 trades, 45.0 % win, PF 1.33" (1 % stop, no lock). The brief says 7.5 years PF 1.49 and last 12 months PF 1.72. days.pkl BASE gives 654 trades PF 1.52, judge 1.49. Each is a different config or data set. Keep one table of record per config.

## What would most strengthen confidence
1. Run CANDACE live on RTH-only bars (or test it on all-hours history) so live = evidence. Until then treat CANDACE as unproven.
2. Pre-register out-of-sample bars now: NOISE PF > 1.2 and CANDACE PF > 1.15 over the next ~150 / ~300 paper or live trades, sizes frozen meanwhile.
3. Publish pass % with bootstrap CIs and the per-half-year table; stop picking fast-pass rows on differences under ~10 pts.
4. One NOISE implementation of record: parity-test noise3.gen (lock + Monday skip + $ stop) against the engine path on real days.
5. Add the real news calendar and a roll calendar to the research sims, then re-run the pass tables once.
6. Turn `fast_pass_late_day` off until it beats its random-direction p95 on post-2026-11 data.
7. Confirm all-in MNQ cost with Lucid (commission + exchange/NFA) and log live slippage per fill to replace the 1-tick assumption.
