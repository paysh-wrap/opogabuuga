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

## 9. NOISE with a fixed $250 emergency stop (user request), 1 year, 1 micro (fixed points: (250−2)/2 = 124 pts)
| stop | trades | win | $/tr | total | PF | avg loss | worst | max DD | hit the stop | Pro 25K pass / bust |
|---|---|---|---|---|---|---|---|---|---|---|
| $520 fixed (≈1%) | 153 | 45.1% | +16.77 | +$2,566 | 1.18 | −$173 | −$520 | −$2,214 | 5 | 49% / 47% |
| **$250 fixed** | 160 | 43.8% | +18.43 | **+$2,948** | 1.21 | −$159 | **−$250** | −$2,228 | 41 | 45% / 56% |
Bad months stay bad (Jan −$1,604, Jul −$1,074 at $250). The stop only caps single trades; drawdown comes from many
ordinary hourly-exit losses in a row, so the eval bust rate does not improve (slightly worse on this year).

## 10. FIVE YEARS (MNQ 2021-11-01 → 2026-10-30, 1,245 sessions, 1 micro) — five_year/singles_report.md + combos_report.md
| Set | trades/day | win | total | PF | Pro 25K pass / bust | value per eval | 2021–23 pass | 2024–26 pass | losing years |
|---|---|---|---|---|---|---|---|---|---|
| NOISE 1% (current) | 0.64 | 45.3% | +$18,588 | 1.35 | 57.0% / 35.7% | $502 | 63.9% | 55.1% | none |
| NOISE $250 stop | 0.64 | 44.7% | +$18,930 | 1.36 | 55.0% / 37.0% | $468 | 66.2% | 50.3% | none |
| NOISE $100 stop | 0.73 | 37.4% | +$15,871 | 1.33 | 56.9% / 33.6% | $389 | 58.9% | 58.6% | 2021 (2 mo) |
| NOISE + Opening drive | 0.68 | 46.3% | +$19,553 | 1.35 | 58.1% / 35.9% | $585 | 64.6% | 57.7% | none |
| **NOISE + PM fade** | **1.03** | 48.3% | **+$24,813** | 1.32 | **62.1% / 37.3%** | **$1,083** | **73.8%** | 56.6% | none |
| NOISE + OD + PM fade | 1.07 | 48.9% | +$25,778 | 1.32 | 62.7% / 36.7% | $1,130 | 74.5% | 57.1% | none |
| + Overnight | 1.89 | 46.6% | +$20,246 | 1.16 | 55.8% / 44.2% | $289 | 61.6% | 51.7% | 2021 |
Alone: Opening drive +$1,449 PF 1.16 (pass 0.3%), PM fade +$6,225 PF 1.26 (loses 2022), ORB −/flat PF 1.02, last-half-hour
−$1,538, overnight −$5,532. Verdict: keep NOISE 1%; PM fade (NOISE-free days) is the only add-on that clearly helps in BOTH
halves (profit + pass rate) — but its gain is uneven (2021–23 +$824, 2024–26 +$5,401) and the 2024–26 bust rate stays ≈ 42%.
Opening drive adds ≈ nothing (120 of 173 trades overlap NOISE). Overnight hurts.

## 11. Afternoon-fade settings + 2 micros on the fade only (five_year/fade_settings.py; NOISE stays 1 micro), 5 years
| set | fade trades | total | PF | max DD | worst day | 5y pass/bust · value | 2021–23 | 2024–26 | fade losing years |
|---|---|---|---|---|---|---|---|---|---|
| fade 1.5 sd ×1 | 578 | +$20,626 | 1.25 | −$2,817 | −$774 | 58%/42% · $656 | 70%/25% · $977 | 53%/47% · $490 | 2022, 2023, 2025 |
| fade 1.5 sd ×2 | 578 | +$22,665 | 1.21 | −$3,842 | −$1,037 | 53%/47% · $466 | 56%/44% · $494 | 54%/46% · $483 | 2022, 2023, 2025 |
| **fade 2.0 sd ×1 (tested setting)** | 488 | +$24,813 | **1.32** | −$2,914 | −$774 | **62%/37% · $1,083** | **74%/21% · $1,295** | 57%/42% · $1,011 | 2022 |
| fade 2.0 sd ×2 | 488 | **+$31,038** | 1.31 | −$4,546 | −$1,233 | 62%/38% · $875 | 65%/34% · $1,221 | **63%/37%** · $596 | 2022 |
| fade 2.5 sd ×1 | 348 | +$20,803 | 1.29 | −$2,571 | −$774 | 61%/37% · $927 | 75%/17% · $1,244 | 54%/44% · $817 | 2021, 2022 |
| fade 2.5 sd ×2 | 348 | +$23,019 | 1.25 | −$4,000 | −$1,541 | 59%/41% · $648 | 65%/35% · $847 | 57%/43% · $497 | 2021, 2022 |
| fade 3.0 sd ×1 | 228 | +$18,590 | 1.28 | −$2,271 | −$774 | 57%/41% · $519 | 67%/27% · $589 | 52%/46% · $451 | 4 years |
| fade 3.0 sd ×2 | 228 | +$18,593 | 1.24 | −$3,445 | −$913 | 53%/46% · $454 | 61%/39% · $379 | 49%/50% · $541 | 4 years |
2.0 sd stays the best band (the neighbours 1.5/2.5 are worse on every column → not a lucky peak, but a peak). 2 micros on
the fade: +$6,225 more profit, same 5-year pass rate, better 2024–26 pass (63% vs 57%) but worse 2021–23 (65% vs 74%),
lower value per eval ($875 vs $1,083), max DD −$4,546 and worst day −$1,233 (> the $1,000 MLL in one day is possible).

## 12. $250 stops on NOISE and the fade (five_year/stops_250.py, 5 years, 1 micro each)
| set | trades | win | total | PF | max DD | worst trade | 5y pass/bust · value | 2021–23 | 2024–26 | losing yrs |
|---|---|---|---|---|---|---|---|---|---|---|
| NOISE 1% + fade 2 sd (previous best) | 1,281 | 48.3% | +$24,813 | 1.32 | −$2,914 | −$617 | 62%/37% · $1,083 | 74%/21% · $1,295 | 57%/42% · $1,011 | none |
| NOISE $250 + fade 2 sd | 1,291 | 47.9% | +$25,155 | 1.33 | −$2,958 | −$617 | 64%/36% · $825 | 74%/20% | 60%/40% | none |
| NOISE $250 + fade min(2 sd, $250) | 1,291 | 47.8% | +$24,675 | 1.32 | −$2,747 | −$250 | 63%/36% · $826 | 74%/20% | 60%/40% | none |
| **NOISE $250 + fade fixed $250** | 1,291 | **50.0%** | **+$25,345** | **1.33** | **−$2,591** | **−$250** | **66%/32% · $1,045** | 71%/21% · $1,009 | **66%/33% · $1,011** | 2021 (2 months) |
| NOISE 1% + fade min(2 sd, $250) | 1,281 | 48.2% | +$24,333 | 1.31 | −$2,703 | −$610 | 62%/37% · $1,081 | 74%/21% | 57%/42% | none |
Fixed $250 on the fade usually WIDENS its stop (2 sd is normally < 124 pts) → more fades reach VWAP (50% win). Best set
on 5 years: highest pass rate, lowest bust, smallest drawdown, every trade capped at −$250, and the most even halves.

## 13. Take-home from 5 FUNDED Pro 25K accounts, payout request every 2 weeks (five_year/funded_biweekly.py)
523 rolling funded starts 2021-11 → 2025-10, each followed for 12 months, 1 micro, 90% split, Pro payout rules (cycle ≥ $250,
$26,100 buffer, ≥ $500 request, 40% consistency, caps $1,000 / $1,500, max 5). 5 accounts take the same trades → 5 × one.
| set | bust in yr 1 | ≥1 payout | days to 1st payout | per account yr 1 mean / median | **5 accounts yr 1 mean / median** | 5 accounts per 2 weeks (mean) |
|---|---|---|---|---|---|---|
| NOISE $250 + fade $250 | 57% | 58% | 70 | $1,646 / $900 | **$8,232 / $4,500** | **≈ $317** |
| NOISE 1% + fade 2 sd | 68% | 59% | 60 | $1,625 / $900 | $8,123 / $4,500 | ≈ $312 |
Payouts in year 1 (best set): 0 → 42%, 1 → 12%, 2 → 9%, 3 → 17%, 4 → 15%, 5 → 4%. Worst 25% of starts: $0 (all 5 bust
before a payout, together). Maximum possible per account = (1,000 + 4 × 1,500) × 90% = $6,300 → $31,500 for 5. Eval fees
and resets are NOT subtracted (user's fee needed); a busted funded account needs a new eval (pass ≈ 66%).

## 14. Stop-size grid, NOISE $150–520 × fade $100–400 (five_year/stop_grid_report.md, 49 combos, 5 years)
Only 250/200 (66.2% / 31.6%, $1,080 per eval) and 250/350 (66.5% / 31.3%) beat 66% pass with ≤ 32% bust — by < 1 point.
Fade axis: $200–400 is a flat plateau (≈ 65–67% pass) → the fade stop barely matters. NOISE axis: only the $250 row is
good; $200 and $300 drop to 57–63% pass / 37–43% bust → $250 is a narrow, probably sample-specific peak. Wider NOISE
stops ($350–400) pay more per pass ($1,240 per eval) but bust 37–38%. Built: NOISE $250 + fade $250 (centre of the plateau).

## 15. Bi-weekly take-home, 5 funded accounts, MAIN strategy (app/backtest/income_projection.py — same code as the Dashboard)
| plan, 5 accounts | micros each | per 2 weeks (avg) | year 1 avg / median | middle half | ≥1 payout | bust yr 1 | 1st payout |
|---|---|---|---|---|---|---|---|
| Pro 25K | 1 | $317 | $8,232 / $4,500 | $0 – $16,875 | 58% | 57% | 70 days |
| **Pro 50K** | 1 | $317 | $8,248 / **$7,617** | $0 – $13,398 | **70%** | **21%** | 100 days |
| **Pro 50K** | **2** | **$595** | **$15,457** / $9,000 | $0 – $31,429 | 61% | 52% | 60 days |
| Pro 50K | 3 | $463 | $12,041 / $0 | $0 – $20,250 | 47% | 63% | 45 days |
50K at 1 micro: same average as 25K but far safer (bust 21%), slower first payout ($52,100 buffer). 50K at 2 micros: best
average; risk like 25K at 1. 3 micros: worse. Eval fees not subtracted; 5 accounts take the same trades.

## 16. Pro 25K vs Pro 50K, two stop sets, fixed size vs D60 account growth (five_year/sizing_plans.py, 5 years)
Eval = 120-session window, rolling starts (pass + bust < 100%: the rest is still open after 120 sessions). Funded = 5
accounts, payout every 2 weeks, first 12 months. Growth = +1 micro per $X of cushion above the trailing MLL (max 5).
| set | plan | sizing | eval pass / bust | 5 funded: per 2 wk | year avg / median | ≥1 payout | funded bust yr 1 |
|---|---|---|---|---|---|---|---|
| $250 / $250 | Pro 25K | 1 micro | 63% / 35% | $317 | $8,232 / $4,500 | 58% | 57% |
| $250 / $250 | Pro 25K | 2 micros | 46% / 54% | $203 | $5,271 / $0 | 36% | 73% |
| $250 / $250 | Pro 25K | **grow +1 per $1,000** | 63% / 35% | **$348** | **$9,049** / $4,500 | 58% | 56% |
| $250 / $250 | Pro 50K | 1 micro | 46% / 14% | $317 | $8,248 / $7,617 | 70% | 21% |
| $250 / $250 | Pro 50K | **2 micros** | **60%** / 37% | **$595** | **$15,457** / $9,000 | 61% | 52% |
| $250 / $250 | Pro 50K | grow +1 per $1,000 | 39% / 17% | $436 | $11,337 / $7,550 | 64% | 29% |
| $350 / $100 | Pro 25K | 1 micro | 62% / 37% | $304 | $7,915 / $4,500 | 58% | 56% |
| $350 / $100 | Pro 25K | grow +1 per $1,000 | 62% / 37% | $281 | $7,318 / $4,500 | 57% | 55% |
| $350 / $100 | Pro 50K | 1 micro | 50% / **6%** | $324 | $8,429 / **$8,544** | 67% | 22% |
| $350 / $100 | Pro 50K | 2 micros | 60% / 38% | $563 | $14,647 / $9,000 | 59% | 54% |
Notes: the 25K eval here is 63% / 35% (Dashboard engine, requires 1 profitable day, starts up to 130 sessions before the
end) vs 66% / 32% in sim25k.py — same trades, slightly different start window. $40,000/yr from 5 accounts is NOT
reached by any setting: best average is 5 × 50K at 2 micros ≈ $15,500 (typical year $9,000).
