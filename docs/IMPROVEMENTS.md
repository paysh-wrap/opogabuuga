# Improvement proposals — NOT built. Each needs your approval ("ask before you do it").
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
