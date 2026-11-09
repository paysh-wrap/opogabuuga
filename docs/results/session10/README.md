# Session 10 — NOISE e2e diagnosis + "AI only" strategy button (D56)

## 1. Why the e2e app backtest ran only 2 NOISE trades (diagnosed)
Re-ran the app backtest (Databento MNQ 1m, Pro 25K plan, fresh account, Jul 2026 →). Signals ARE generated as in research
(9 NOISE signals in the first 10 post-warm-up sessions, 16–29 Jul). Execution stops because the account fails the
**Pillar §9 pre-trade check `RISK_BASE_BELOW_PAUSE`** (risk_base = equity − MLL < $500): after 6 trades (−141, +83, −233,
+62, −14.5, −295 = −$539) risk_base = $461, every later signal is rejected and an EOD-trailing account cannot recover without
trading. NOT a signal/engine bug. Research sim (tools/sim25k.py) busts only at the full $1,000 MLL, so the app is stricter
than the research. Decision needed from the user (do NOT change a Pillar silently): keep the $500 pause (safe, far fewer
trades), or lower it for NOISE/Pro 25K. Backtest runs per month with fresh accounts give the true per-eval picture.

## 2. AI-only strategy button (D56, paper only)
`strategy.ai_bias` (default OFF). Trades only when TradingAgents AND Vibe-Trading agree strongly (policy.combine
`agree_strong`, ≈ 27% of days): enter at the 09:31 bar close in that direction, 0.5% broker stop, flat 16:00, 1 micro,
paper accounts only. Code: `strategy_service.run_ai_bias`, `AiBiasCfg`, catalog + Strategy-page card, tests.

## 3. One year of data — HINDSIGHT UPPER BOUND (not a backtest of the AI)
The LLM tools cannot be run on past dates (§15 / training-data leakage), so the table shows what a daily call of accuracy
`a` WOULD earn on real MNQ 2025-11-03 → 2026-10-30 (248 sessions), 1 micro, $2 costs/trade, stop 0.5% (`ai_only_bound.py`):
| accuracy | $/trade | total (248 days) | win % | PF |
|---|---|---|---|---|
| 100% (ceiling) | +266.94 | +66,202 | 77% | 5.33 |
| 70% | +111.29 | +27,601 | 54% | 1.94 |
| 60% | +59.41 | +14,733 | 46% | 1.43 |
| 55% | +33.47 | +8,300 | 43% | 1.23 |
| 50% (coin flip) | +7.53 | +1,866 | 39% | 1.05 |
Worst single trade −$314 (> $140 eval-mode risk cap and ≈ 1/3 of the $1,000 MLL). Always-long +$2,507, always-short +$1,226
(MNQ drifted up; a coin flip earns that drift). With a 1% stop even a coin flip is negative (−$975). Published LLM next-day
index accuracy ≈ 50–55% → realistic edge ≈ the drift, minus the days both tools disagree (≈ 73% of days no trade).
Real evidence = the live calibration ledger (Strategy page); gate stays paper-only until Wilson LB ≥ 60%.
