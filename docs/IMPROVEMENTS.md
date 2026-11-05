# Improvement proposals
Status (D16, 2026-11-05): **§A approved** (A4, A5 built; A1/A2/A8 → Phase 8; A3/A6/A7 → Phase 9) ·
**§E approved** (E1–E7 built for 1:1 mode; E8 → Phase 9) · §B: B1 done (D10), B2–B5 still need approval ·
§C still needs approval.
All stay inside the master prompt + Lucid rules. Pillars are never changed by the Lab.

## A. Self-learning (Lab §17) — "backtest every trade"
| # | Proposal | Why | Rules impact |
|---|---|---|---|
| A1 | **Per-trade post-mortem**: every closed live/paper trade is replayed nightly through the same engine on recorded bars; decision parity (live = replay) + fill slippage vs model; stores MFE/MAE (best/worst excursion in R). | Finds bugs/drift fast; MFE/MAE is the key data for TP cap, runner trail, early exits. Mismatch → alert + blocks promotions. | None (read-only) |
| A2 | **Skipped-signal outcomes**: every rejected signal is simulated forward; report "what each skip reason cost/saved in R". | Shows which filters earn their keep. Lab may tune only tunable thresholds; pillar gates are report-only. | None |
| A3 | **Score calibration**: check that score tiers really rank outcomes (60–74 < 75–89 < 90+). If not, Lab proposes weight changes. | Sizing is score-driven; a mis-ordered score sizes up the wrong trades. | Weights are tunable 50–150% |
| A4 | **Regime + time-slice tags** on every trade (ATR percentile, HTF trend, 30-min slice, weekday, news day). | Your new 06:45 window adds pre-market; slice data tells where edge really is. | Slice disabling is tunable |
| A5 | **Shadow-trade MES/MYM/MGC from day one** (signals + simulated fills, no orders). | Builds the ≥100 trades §16.6 needs before they can be enabled — months faster. | None (no orders) |
| A6 | **Stronger overfit guard**: purged walk-forward with embargo + Deflated-Sharpe style multiple-trial penalty. | Spec requires "multiple-trial adjustment"; this is a concrete, proven method. | Stricter only |
| A7 | **Bias scorecard**: TradingAgents rating vs next-session move and vs trade E(R), plus $ cost per day. | Tells you if the AI bias is worth its LLM bill. | Report-only (G2 is a pillar) |
| A8 | **Measured slippage per slice** feeds backtests (pre-market likely wider). | Keeps backtests honest. | Stricter only |

## B. Strategy (each would be added as a TUNABLE or user setting, then proven in shadow first)
- B1 **Keep 09:30–09:35 excluded** inside your new 06:45–11:30 window (the original 09:35 start avoided the opening-bell whipsaw). Proposed windows: 06:45–09:30, 09:35–11:30, 13:30–15:30.
- B2 **08:30 ET medium-impact releases** also blacked out before 09:30 (thin pre-market + data prints).
- B3 **Limit entry at CISD** (already a tunable) run as a challenger vs market entry.
- B4 **Time-stop**: exit at breakeven-or-better if +0.5R not reached within N bars of C3 open (new tunable).
- B5 **ATR-scaled stop buffer** instead of fixed 4 ticks (new tunable, bounded).

## C. Safety / ops
- C1 Dashboard exposure: put the dashboard behind **Cloudflare Access** (free) and expose only `/api/webhook/*` publicly; add TOTP 2FA to login.
- C2 Your password is a long all-caps phrase; fine for local use, but with internet exposure C1 is strongly recommended.

## D7 — 1:1 mode math (for your decision)
With 50% off at 0.75R and 50% at 1R: full win ≈ +0.875R; loss = −1R (+ fees). Break-even win rate ≈ 53–55% after
fees; if the remainder is moved to breakeven after the partial, wins can be as small as +0.375R. Recommend:
run 1:1 mode in SHADOW until it shows E ≥ 0.20R net over ≥100 trades before enabling it on a paid account.

## E. Raising the 1:1-mode win rate toward 65–72% (proposals — need approval)
Each is a 1:1-mode-only ENTRY FILTER (stricter only: it can skip trades, never loosen a rule). Each is tested in
backtest + shadow and kept only if, out-of-sample, it raises win rate WITHOUT pushing E below 0.20R net or trades
below ~150/year. No promise of a win rate — the backtest measures it.

| # | Filter | Why it should raise win rate |
|---|---|---|
| E1 | **1R target must sit at or before the model's T1** (first objective) | Price only has to make part of the move the model expects first; biggest expected lever |
| E2 | **Own T1 hit-rate ≥ threshold** per symbol+profile (≥30 recorded samples) | Trades only where this setup has proven to reach T1 |
| E3 | **Score ≥ 75 in 1:1 mode** (instead of 60) | Takes only the cleaner setups (early CISD + structure turn) |
| E4 | **Require CHoCH** (not just BoS) after the sweep | Stronger reversal evidence |
| E5 | **Bias aligned + HTF structure agrees** (no NEUTRAL days in 1:1 mode) | Trades with the higher-timeframe flow |
| E6 | **Volatility band**: skip when HTF ATR is in its top/bottom 10% | Avoids whipsaw and no-follow-through days |
| E7 | **Skip 09:30–09:35 and 5 min after any high-impact release** | Avoids the most random minutes |
| E8 | **Lab ranks 30-min slices by measured win rate** (already tunable) | Drops the weakest times of day, inside your windows only |

Expectancy check (1:1, 50% at 0.75R then BE, fees ignored): win rate 60% → about +0.13R per trade,
65% → +0.22R, 72% → +0.35R. So 65% is roughly where 1:1 mode clears the 0.20R gate.
