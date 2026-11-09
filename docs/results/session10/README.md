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

## 4. D57 — scale risk down in drawdown instead of pausing (user 2026-11-09: "lower risk as account goes into drawdown")
Fixed-size strategies NOISE and AI_BIAS no longer stop at the $500 pause floor. Pure `risk/checks.pretrade`: when the
worst case at the plan's emergency stop exceeds `strategy.drawdown_shrink` (0.6) × room (room = min(DLL left, equity −
MLL − $100 kill distance)), the emergency stop is tightened to fit; below `drawdown_min_stop_pct` (0.2% of price) →
skip `DRAWDOWN_TOO_DEEP`. Fresh Pro 25K: room $900 → $540 allowed ≥ $520 at 1% → unchanged. Base $460: room $360 → stop
≈ 0.41% (research: 0.3–0.5% stops still profitable held-out, PF 1.18). Base ≈ $270 → 0.2% → stops trading. Kill switch,
DLL, MLL, one-position, hedge lock unchanged. OPEN_DRIVE keeps the pause floor (its stop is structural). LunqFX unchanged.
Tests: 592 passed, risk/management/phases coverage 100%.

## 5. One year, NOISE vs the next three strategies (one_year_compare.py, MNQ 2025-11-03 → 2026-10-30, 248 sessions, 1 micro)
| Strategy | trades | win | $/trade | total | PF | max DD | worst trade | trades/wk |
|---|---|---|---|---|---|---|---|---|
| **NOISE (on)** | 153 | 45.1% | +15.15 | **+$2,319** | 1.16 | −$2,214 | −$610 | 3.1 |
| Opening-drive pullback (paper button) | 45 | **55.6%** | +13.11 | +$590 | 1.18 | −$1,104 | −$236 | 0.9 |
| Last-half-hour momentum | 226 | 46.0% | +5.19 | +$1,173 | 1.13 | −$1,937 | −$306 | 4.6 |
| ORB 15-min, 1.5R | 226 | 43.4% | −13.58 | −$3,068 | 0.90 | −$8,526 | −$656 | 4.6 |
NOISE's last year was weaker than its 2024–26 held-out average (PF 1.16 vs 1.33). Opening-drive and last-half-hour are
small positives on this one year but failed the multi-year test in session 9 (in-sample PF 1.00 / sign flips) → not
promoted. ORB loses again. Per-trade CSVs are reproducible with the script.

## 6. Add-ons that never overlap NOISE, 1 year (addons_1y.py, MNQ 2025-11-03 → 2026-10-30, 1 micro)
| Set | trades/day | win | $/tr | total | PF | max DD | Pro 25K eval pass / bust |
|---|---|---|---|---|---|---|---|
| NOISE alone | 0.62 | 45.1% | +15.15 | +$2,319 | 1.16 | −$2,214 | 48% / 47% |
| Overnight Asia-range breakout | 0.79 | 45.7% | −3.22 | −$634 | 0.96 | −$3,751 | 30% / 70% |
| **PM fade (NOISE-free days only)** | 0.37 | **57.1%** | +30.38 | +$2,765 | **1.56** | −$903 | 75% / 0% (only 91 trades) |
| **NOISE + PM fade** | **0.98** | 49.6% | +20.83 | **+$5,084** | 1.26 | −$2,914 | **51% / 45%** |
| NOISE + overnight | 1.41 | 45.4% | +4.81 | +$1,685 | 1.06 | −$3,453 | 19% / 81% |
| NOISE + both | 1.78 | 47.8% | +10.09 | +$4,450 | 1.13 | −$2,627 | 29% / 71% |
Funded columns of sim25k are meaningless on one year (runs are cut off) → only eval pass/bust shown. ONE year only:
the session-9 VWAP-band fade (all days) failed 2019–2026; "only on days NOISE didn't trade" is new and unverified →
needs the multi-year test (pick 2019–2023, judge 2024–2026) before it may trade anything but paper.

## 7. D57 checked end-to-end in the app (MNQ Jul–Aug 2026, Pro 25K, fresh account, 45 sessions) — DID NOT HELP
| | trades | P&L | blocked later signals |
|---|---|---|---|
| before D57 (pause at $500) | 6 | −$539 | RISK_BASE_BELOW_PAUSE ×3 (run stopped 29 Jul) |
| **with D57 (scaled stop)** | 7 | **−$795** (bal $24,204.50) | DRAWDOWN_TOO_DEEP ×12 |
On 28 Jul the tightened stops were hit (−$394 at a $393 stop, then −$158 at a $157 stop) where the 1% stop version lost
−$295 on the trail exit. The account then sat $204 above the MLL and every later signal was too deep to trade.
Read: NOISE's edge needs the wide stop; shrinking it in a drawdown turns trail exits into full stop-outs. One account,
one bad July — but it is evidence AGAINST D57. User decision needed: revert D57 (back to the $500 pause), or keep it.
Also: July 2026 alone was −$795 for NOISE at 1 micro on a fresh eval → the 42–47% bust rate is real.

## 8. NOISE with an $80–120 stop (user: "why can't it risk $80–120 per trade?"), 1 year, noise_area.py --hard
| stop (≈$ at 1 micro) | trades | win | $/tr | total | PF | worst | Pro 25K pass/bust 1 micro |
|---|---|---|---|---|---|---|---|
| 1.00% ($520, current) | 153 | 45.1% | +15.15 | +$2,319 | 1.16 | −$610 | 48% / 47% |
| 0.50% ($260) | 158 | 43.7% | +15.19 | +$2,399 | 1.16 | −$307 | — |
| 0.23% ($120) | 185 | 34.1% | +15.92 | +$2,945 | 1.22 | −$142 | 29% / 71% |
| 0.19% ($100) | 196 | 31.1% | +13.61 | +$2,668 | 1.21 | −$119 | 64% / 34% |
| 0.15% ($78) | 209 | 26.3% | +9.85 | +$2,059 | 1.17 | −$95 | 28% / 72% |
Profit holds up on this year, but win rate falls to 26–34% and the eval pass rate jumps 28% → 64% → 29% between
neighbouring stops = noise from one year's losing streaks, not a reliable edge. 2–3 micros at any stop: pass ≤ 32%.
Session 9 (2024–26 held-out) found 0.3–0.5% stops cut PF 1.33 → 1.18. Needs the multi-year test before any change.
