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
