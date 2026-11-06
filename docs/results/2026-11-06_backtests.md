# Backtest results — 2026-11-06 (kept in the repo so nothing is lost)

Data: Yahoo continuous futures 1-minute bars (data/futures/*_yahoo_1m.csv). Plan: Lucid Pro 25K
(config/rules/lucid_pro_25k.yaml), bias NEUTRAL (TradingAgents may not be backtested on past dates, §15/§16.7).
All numbers are backtests, not live results. Small samples: treat single-digit trade counts as noise.

## A. Before the realistic-fill fix (D39), 18 sessions — DO NOT USE (inflated by false fills)
| Mode | MGC | MNQ |
|---|---|---|
| Intraday H1 | 24 tr, 71% win, PF 3.92, +$846 | 12 tr, 67%, PF 4.66, +$666 |
| Low risk | 42 tr, 60%, PF 1.67 | 25 tr, 48%, PF 2.00 |
| 1:1 (D38) | 40 tr, 65%, PF 1.56 | 24 tr, 50%, PF 2.06 |
| Scalp (D38) | 22 tr, 50%, PF 0.66 | 16 tr, 56%, PF 5.75 |

## B. After D39 (realistic fills), 22 sessions — CURRENT BASELINE
| Mode | MGC | MNQ |
|---|---|---|
| Intraday H1 | 24 tr, 58% win, PF 1.69, +$324 | 9 tr, 44%, PF 0.93, −$16 |
| Low risk | 41 tr, 49%, PF 1.04, +$26 | 24 tr, 38%, PF 0.83, −$92 |
| 1:1 | 36 tr, 50%, PF 0.61, −$304 | 22 tr, 45%, PF 0.72, −$126 |
| Scalp | 25 tr, 40%, PF 0.45, −$187 | 18 tr, 56%, PF 1.22, +$30 |

## C. Fill-rate tests (Intraday, 22 sessions) — rejected
| Variant | MGC | MNQ |
|---|---|---|
| limit timeout 8 bars | 29 tr, 52%, PF 1.28, +$181 | 12 tr, 42%, PF 0.92 |
| market entry | 23 tr, 43%, PF 1.10, +$54 | 12 tr, 33%, PF 0.43, −$248 |

## D. MNQ fixes (Intraday, 22 sessions) — none profitable
| Variant | MNQ |
|---|---|
| stop buffer 12 ticks | 8 tr, 38%, PF 0.64, −$88 |
| min stop 40 ticks | 10 tr, 50%, PF 0.91, −$23 |
| STD (5m) profile only | 1 tr, −$54 |
| require structure break (+MSO agree) | 4 tr, 50%, PF 1.12, +$12 |
| (MGC with require break) | 10 tr, 50%, PF 1.95, +$198 |

## E. Daily-bias value (Intraday, 22 sessions)
| Bias | MGC | MNQ |
|---|---|---|
| oracle (hindsight: day's real direction) | 22 tr, 59%, PF 1.49, +$206 | 5 tr, 40%, PF 0.60, −$61 |
| trend (prior closes only, no lookahead) | 19 tr, 63%, PF 1.80, +$236 | 4 tr, 50%, PF 1.13, +$12 |
Even a perfect daily direction adds ~nothing here → TradingAgents' value must be measured live (A7 scorecard).

## F. Offline Lab walk-forward on MGC Intraday (train = older 16 sessions, test = newest 6)
Champion: train 19 tr, 53% win, +0.237R/trade · test 6 tr, 67%, +0.297R.
| One-step change | Train trades | Win | R/trade |
|---|---|---|---|
| score.min_score 57 | 19 | 53% | +0.237 |
| score.osc_strength_min 10 | 21 | 52% | +0.271 |
| **score.osc_strength_min 20** | 16 | **62%** | **+0.502** (fails the ≥90% trade-count rule: 16 < 17.1) |
| score.tp_rate_min 0.40 / 0.50 | 19 | 53% | +0.237 |
| score.div_lookback_bars 5 / 7 | 19 | 53% | +0.237 |
| filters.c1_min_range_atr 0.5 | 19 | 53% | +0.237 |
| trade_plan.stop_buffer_ticks 3 | 19 | 53% | +0.249 |
| trade_plan.stop_buffer_ticks 5 | 20 | 50% | +0.155 |
| trade_plan.min_stop_ticks 16 / 24 | 19 | 53% | +0.237 (MGC uses its own min_stop_ticks 16) |
| entry.max_wait_bars 5 | 18 | 56% | +0.266 |
| entry.max_wait_bars 7 | 19 | 53% | +0.237 |
| entry.limit_timeout_bars 3 | 17 | 53% | +0.229 |
| entry.limit_timeout_bars 5 | 20 | 50% | +0.170 |
| internal.no_entry_before_news_min 10 / 20 | 19 | 53% | +0.237 |

Lab verdict: best train candidate = entry.max_wait_bars 5 (18 tr, 56%, +0.266R); on the 6 unseen sessions it was
identical to the champion (6 tr, 67%, +0.297R) → not ≥ +0.03R better → NO proposal. Intraday MGC unchanged (correct,
conservative behaviour). Bug found + fixed by this run: invalid candidate rule sets now skipped (commit 7e2d6d4).

## G. MNQ under master-prompt settings (22 sessions, neutral bias) — almost no trades
spec = G4/G5 hard, R:R ≥ 2, neutral_min_score 75, C1 ≥ 0.6 ATR · spec175 = same with R:R ≥ 1.75 (identical
results) · gates = only G4/G5 hard (R:R from 1.0, neutral 60, C1 0.4).
| MNQ mode | spec / spec175 | gates |
|---|---|---|
| Intraday | 1 tr, 0%, −$52 | 4 tr, 50%, PF 1.12, +$12 |
| Low risk | 2 tr, 0%, −$105 | 7 tr, 43%, PF 0.96, −$7 |
| 1:1 | 6 tr, 50%, PF 1.08, +$9 | 7 tr, 43%, PF 0.48, −$90 |
| Scalp | 6 tr, 50%, PF 5.37, +$42 | 6 tr, 83%, PF 8.94, +$64 |
Too few trades to trust any of these. MGC under the same variants: cancelled at the user's request (focus Intraday).

## H. Can Intraday reach 60%+ wins at R:R 1.75–3? (offline screening of every setup, 22 sessions)
Method: research.py exports every setup that passed the gates (loose plan: score/C1 minimums off, full hours,
R:R ≥ 1.75, T2 must reach 1.75R); screen.py / frontier.py simulate each bracket exactly like the engine (limit at
CISD, 4-bar timeout, stop-first, 1-tick stop slip, fees, flat 16:40). Verified against the engine on a probe
(same fills, same stops). Train = older 15–16 sessions, test = newest 6.
| Market | Setups filled | Win at ≥1.75R targets (train / test) | R/trade (train / test) |
|---|---|---|---|
| MGC | 66 | 19% / 26% | −0.43 / −0.24 |
| MNQ | 60 | 7% / 12% | −0.79 / −0.59 |
- No filter combination (hour, break, score, osc, C1 size, ATR, direction, profile, R:R) reached 60% with ≥ 8
  trades on train. Breakeven at +1R / +1.25R did not help (MGC non-loss 26–37%, still negative).
- Frontier (same entries/stops, target k·R): MGC all hours 1.0R 34%/42% … 1.75R 23%/32% … 3R 15%/21%;
  MNQ 1.0R 16%/24% … 1.75R 12%/24% … 3R 7%/12%. All negative.
- Caveat: this set excluded setups whose model T2 is < 1.75R away (the plan required ≥1.75R) — those are the
  setups behind the current 58% (D36b: no-break setups aim for 1R). Re-run with the real R:R floor 1.0 pending.

## I. Engine backtests, Intraday at R:R 1.75–3 (best hours H1, 22 sessions, risk base ≈ $1,000 = equity − MLL)
r175 = rr_min 1.75 and no 1R cap for no-break setups; r175brk = + structure break required.
| Variant | MGC | MNQ |
|---|---|---|
| r175 | 16 tr, 38% win, PF 1.32, +$151, +0.32R/trade | 5 tr, 20%, PF 0.69, −$54 |
| r175brk | 6 tr, 50%, PF 2.27, +$173, +0.73R/trade | 1 tr, 0%, −$52 |
Note: the engine beats the offline screener (section H) because of its early exits / half-off defence → judge
strategy changes with full engine backtests, not the offline screener.

## J. Final results this session (engine, Intraday best hours, 22 sessions, risk base ≈ $1,000)
| Variant | MGC | MNQ |
|---|---|---|
| Current plan (baseline) | 24 tr, 58%, PF 1.69, +$324 | 9 tr, 44%, PF 0.93, −$16 |
| osc_strength_min 20 (current plan) | 21 tr, 57%, PF 1.76, +$318, +0.38R | 8 tr, 63%, PF 1.52, +$76 |
| R:R ≥1.75 + osc 20 | 14 tr, 43%, PF 1.62, +$236, +0.52R | 4 tr, 50%, +$38 |
| R:R ≥1.75 + structure break | 6 tr, 50%, PF 2.27, +$173 | 1 tr, −$52 |
| R:R ≥1.75 plain | 16 tr, 38%, PF 1.32, +$151 | 5 tr, 20%, −$54 |
Engine's 24 baseline MGC trades: 13 TP, 9 STOP; 15 of 24 aim for 1R (D36b) → that is why win rate is 58%.
60%+ at R:R 1.75–3 not reached on this data. Nothing applied to the live plan (user decides).

## L. TradingView indicator filters at a fixed 1.75R target (session 7, MGC, 22 Yahoo sessions — TOO SMALL)
Tool: docs/results/tools/indscreen.py on research.py setups (loose plan, R:R floor 1.0, every PASS setup, target
forced to exactly 1.75R). 87 filled setups; train = older 12 sessions, test = newest 6. Breakeven ≈ 38% win.
| Filter (trade only in its direction) | Train | Test |
|---|---|---|
| none (all setups) | 56 tr 20% −0.54R | 31 tr 29% −0.27R |
| Session VWAP side | 15 tr 40% −0.03R | 7 tr 43% +0.11R |
| UT Bot (1, 10) 5m | 11 tr 36% −0.13R | 10 tr 60% +0.60R |
| EMA 200 5m | 15 tr 33% −0.21R | 12 tr 42% +0.07R |
| EMA 200 15m + Supertrend 15m | 15 tr 33% −0.21R | 12 tr 42% +0.06R |
| ADX ≥ 25, RVOL > 1, WaveTrend extreme | worse than none | worse |
Trend-side filters (VWAP, EMA 200, UT Bot) roughly double win rate at 1.75R; momentum/strength filters don't help.
Samples are 7–15 trades → NOT applied. Needs the long Databento history (research_par.sh, monthly chunks × 4 workers).

## M. DATA WARNING — Databento MGC.c.0 is broken for gold (session 7)
`MGC.c.0` (stype continuous, calendar roll) follows the nearest calendar month. Gold's liquid months are G/J/M/Q/V/Z;
the serial months barely trade (2026-06-02: 13 one-minute bars vs ~1,380 in the active contract). Backtests on it see
only a few sessions per month. Use `MGC.v.0` (highest volume). docs/results/tools/dbget.py fixed. Any earlier MGC
result built on MGC.c.0 Databento data (session 5/6 MGC Lab on long data) should be re-checked. MNQ (quarterly
H/M/U/Z, always the front) is far less affected.

## N. TradingView indicators on 4 months of REAL MGC data (Databento MGC.v.0, Jul–Oct 2026, session 7)
Tool: research_par.sh (research_rr1.yaml = loose plan, R:R floor 1.0, every PASS setup) → indscreen.py. 2,892 signals →
343 filled setups, 81 sessions; train = older 48 sessions, test = newest 33. Fixed target 1.75R (breakeven ≈ 38%).
Full output: docs/results/ind/. PARITY: the engine's live D44 switches (VWAP / EMA200 5m / UT Bot 5m) agree with the
screener's own math on 100% of 343 setups → the live code computes exactly what was researched.
| Filter (trade only in its direction) | Train (48 sessions) | Test (33 sessions) |
|---|---|---|
| none | 197 tr 26% −0.34R | 146 tr 27% −0.31R |
| Session VWAP | 78 tr 22% −0.45R | 46 tr 30% −0.25R |
| EMA 200 5m | 80 tr 22% −0.43R | 51 tr 33% −0.17R |
| UT Bot 5m | 51 tr 31% −0.15R | 42 tr 43% +0.12R |
| Squeeze Momentum [LazyBear] rising 5m | 83 tr 35% −0.09R | 68 tr 35% −0.09R |
| **Squeeze rising 5m AND 15m** | **21 tr 43% +0.07R** | **24 tr 54% +0.46R** |
| Squeeze rising 5m + squeeze OFF 60m | 67 tr 39% +0.02R | 50 tr 40% +0.03R |
- The 22-session VWAP/EMA200 result (section L) did NOT hold on 4 months → small samples mislead.
- Best and consistent in both halves: Squeeze Momentum momentum rising in the trade direction on BOTH 5m and 15m.
  45 trades in 4 months (~0.5/day) and it is the best of ~1,800 pairs → must be confirmed on the 7-year data before use.
- At a 1R target: none 40%/36% (−0.24R/−0.34R); UT Bot 5m 51%/50% (≈0R). Offline sim has no early exits; the
  engine usually does better (section I) → engine confirm running (base, UT Bot) on the same 4 months.

## O. 7 years of REAL MGC data: does the Squeeze 5m+15m filter hold? (session 8, 2026-11-06)
Data: Databento MGC.v.0 1m, May 2019 – Nov 5 2026 (2.56M bars). research_par.sh (research_rr1.yaml: every PASS setup,
R:R floor 1.0) → indscreen.py at a FIXED 1.75R target. 57,944 signals → 5,768 filled setups, 1,672 sessions.
Halves = older 836 / newer 836 sessions. Parity engine switches vs research math: 99.7–99.9% (5,768 setups).
| Filter | Older half | Newer half |
|---|---|---|
| none | 2,531 tr 30% −0.33R | 3,237 tr 28% −0.32R |
| **Squeeze rising 5m + 15m (D45)** | **325 tr 30% −0.30R** | **435 tr 33% −0.18R** |
| UT Bot 5m | 766 tr 37% −0.14R | 891 tr 33% −0.20R |
| VWAP | 751 tr 35% −0.17R | 1,068 tr 30% −0.27R |
| EMA 200 5m | 829 tr 34% −0.20R | 1,130 tr 31% −0.26R |
| best pair (EMA200 5m & UT Bot 5m) | 276 tr 41% −0.02R | 323 tr 37% −0.12R |
By year, Squeeze 5m+15m: 2019 39% · 2020 28% · 2021 24% · 2022 33% · 2023 27% · 2024 34% · 2025 30% · 2026 42% (+0.10R).
- VERDICT: the 4-month result (Results N, 54% win) was a small-sample fluke; only 2026 is positive. Squeeze does NOT
  beat 58% at 1.75R → per the user's rule ("if it doesn't beat 58% at 1.75R keep what achieved that") the live plan is
  unchanged and the D45 switch stays OFF. Engine before/after (step 4) skipped: the condition "if it holds" failed.
- No TradingView filter or pair reaches even 50% at a fixed 1.75R in any half; best single year is UT Bot 2019 (47%).
- Engine side note: 116 of 612 research trades (19%) were flattened right after the fill as RR_INVALID_AFTER_FILL
  (1-tick slippage pushes R:R under the minimum) → candidate for a fill-rate/R:R-buffer study.
- Caveat on the live plan's 58% (Results H): 22 sessions only, and 15 of its 24 trades aimed at 1R (D36b), not 1.75R.
  It has NOT been re-measured on 7 years (engine run ≈ 3 h on 4 CPUs) — recommended next.
Full output: docs/results/ind7y/screen_175.txt.

## P. Best strategy at 1.75R on ALL MGC data + live plan re-measured (session 8, 2026-11-06) → D47 main strategy
Data: every MGC 1-minute bar since the contract launched (Databento MGC.v.0, May 2019 – Oct 2026).
1) Live plan (D36 1R/2–3R mix + D37 hours), ENGINE, Nov 2024 – Oct 2026, NEUTRAL bias (ind7y/live_plan_2y_engine.txt):
| | trades | win | PF | $ | R/trade |
|---|---|---|---|---|---|
| all | 391 | 43% | 0.87 | −1,201 | −0.05 |
| ~1R targets | 320 | 45% | 0.86 | −934 | −0.07 |
| 1.75R+ targets | 71 | 32% | 0.88 | −268 | +0.02 |
| exits | TP 145 · STOP 191 · RR_INVALID_AFTER_FILL 50 · FLAT 5 | | | | |
→ the 58% (22 sessions) does not hold on 2 years.
2) Hold-out search at a fixed 1.75R (best175.py; 5,768 setups; 103,256 combos of ≤3 filters with ≥100 picks):
chosen on 2019–2023 only, judged on 2024–2026. Top picks 47–48% on 2019–23 → 25–38% on 2024–26 (over-fit).
No combination reaches 50% on the unseen years; 70% at 1.75R is not reachable with these setups.
| Candidate (engine settings only) | 2019–2023 | 2024–2026 (unseen) |
|---|---|---|
| live gates, T2 ≥ 1.75R | 283 tr 34% −0.19R | 307 tr 29% −0.30R |
| **UT Bot 5m + EMA200 5m + T2 ≥ 1.75R + score 60 + C1 0.4 (D47 main)** | **60 tr 43% −0.01R** | **44 tr 39% −0.01R** |
| same without score/C1 (not allowed: score < 60 has no risk tier) | 99 tr 48% +0.11R | 104 tr 38% −0.02R |
| + D37 best hours | 56 tr 41% −0.10R | 63 tr 30% −0.26R |
3) Bias ceiling on the D47 setups (all 7 years): none 104 tr 41% −0.01R · PERFECT daily direction 73 tr 49% +0.18R ·
20-day trend at open 55 tr 47% +0.15R (2019–23 51%, 2024–26 40% +0.08R, 20 tr) · previous day 67 tr 37% −0.12R.
→ TradingAgents can add ~+0.1–0.2R/trade at best; it cannot lift these setups to 70%.
4) D47 main strategy in the ENGINE, Nov 2024 – Oct 2026 (main175.yaml = the saved plan; ind7y/main_d47_2y_engine.txt):
| Engine, Nov 2024 – Oct 2026, NEUTRAL bias | trades | win | PF | $ | R/trade |
|---|---|---|---|---|---|
| old live plan (D36/D37 mix) | 391 | 43% | 0.87 | −1,201 | −0.05 |
| **D47 main (all targets 1.75–1.8R)** | **65** | **40%** | **1.34** | **+594** | **+0.13** |
| D47 by year: 2024 (Nov–Dec) 5 tr 60% +$202 · 2025 28 tr 32% −$227 · 2026 32 tr 44% +$619 | | | | | |
Exits: TP 26 · STOP 36 · RR_INVALID_AFTER_FILL 3. These 2 years were NOT used to choose D47 (chosen on 2019–2023).
Engine beats the offline estimate (39%, −0.01R) as in section I (early exits). ~2.7 trades/month — small sample.
