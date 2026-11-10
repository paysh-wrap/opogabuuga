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

---

# Session 13 audit (2026-11-10) — read-only review, NOTHING BUILT (needs user approval)

Scope: live path webhook -> signal -> strategy_service -> automation controller -> CrossTrade adapter; NOISE / PM fade win rate; D77 hindsight; PAPER UX; cost.
Paths are under `backend/app/`. Priority: P1 = fix before any LIVE order, P2 = before FULL-AUTO / eval, P3 = nice to have. Effort S < 0.5 day, M 1-2 days, L 3+ days.

## P1 — reliability / live path

**1. Open trades are not rebuilt after a restart (in-memory only).**
- Problem: `OrderManager.trades` is filled only when an entry is placed (`execution/order_manager.py:175-213`); `lifespan` (`main.py:371-423`) rebuilds market state and accounts but not open trades, and `_pending_exits` (`automation/controller.py:100`) is lost too. After a crash/redeploy with a NOISE position open, the bracket stays at the broker but the app no longer manages it: no band/VWAP exit, no 16:00 flat for that trade, no BE/trailing. `reconcile` then sees broker qty != expected 0 and pauses the account (`controller.py:886-902`) - safe but the position is orphaned until the hard flat.
- Fix: on startup (and after `_start_live`), rebuild `om.trades` from the `Trade`/`Order` rows still open + broker positions; if they cannot be matched, flatten and pause with a banner "restart found an unmanaged position". Add a test that restarts the app mid-trade (paper + CrossTrade fake).
- Risk: touches order manager state (pillar-adjacent); needs 100% coverage. Effort: M.

**2. Strategy exit is committed as CLOSED before the broker confirms.**
- Problem: `run_noise` calls `_close(open_sig, ...)` and `run()` commits (`strategy_service.py:213-216, 505-517`) before `ctl.strategy_exit` runs (`api/webhook.py` after `_after_accept`). If the app dies or the exit is waiting out the 6 s hold (`controller.py:623-641`, kept only in memory), the signal says CLOSED while the position is still open; nothing retries it after a restart. Also `run_pm_fade`/`run_ai_bias` flat exits follow the same pattern.
- Fix: persist an `exit_requested` marker (reason + time) on the signal and keep `state=OPEN` until the trade is really closed (`_close_trade`); a watchdog step re-issues exits for any signal with `exit_requested` and an open trade (also covers item 1). The hard flat 16:44 stays the backstop.
- Risk: low-medium. Effort: S-M.

**3. Accepted-but-not-processed webhook (lost signal / lost exit).**
- Problem: `ingest` commits the Event and bar first, and the strategy run happens later in a FastAPI BackgroundTask (`api/webhook.py` `tradingview` -> `_after_accept`). If the process dies between the two, TradingView's retry is answered as DUPLICATE (`webhook/service.py` IntegrityError branch) and is never processed. NOISE only decides on check minutes (`engine/noise.py is_check`, `strategy_service.py:203`), so one lost 1-minute heartbeat at :00/:30 silently skips that check (an exit check lost = position held 30 min longer).
- Fix: add `processed_at` to Event; at startup and every minute in the watchdog, reprocess unprocessed heartbeats of the last 5 minutes (idempotent: model_key per entry is deterministic). Add a "missed check minute" alert when a check minute has no stored bar by +90 s.
- Risk: low. Effort: M.

**4. Duplicate-order guard relies on a DB read inside one process only.**
- Problem: `_execute` checks `Order.account_id` for "ALREADY_TRADED" (`controller.py:300-307`), but NOISE keys are `SYMBOL-NOISE-day-N` where N = len(today's signals) (`strategy_service.py:236,246`); a skipped signal also consumes N, and the 4th/5th entry rules differ per strategy. The CrossTrade `clOrdId` is `req.client_id[:64]` - confirm it is derived from signal id + account (not time) so a manual re-run is rejected broker-side as well. After `UnconfirmedError` (500/502/timeout) the code correctly never resends; verify the follow-up reconcile runs within seconds and blocks new entries on that account until it does.
- Fix: unit test "UnconfirmedError on place -> account paused -> no second place on the next heartbeat"; make client_id deterministic (`P-{signal_id}-{account_id}`) and assert it.
- Risk: low. Effort: S.

**5. Tunnel / heartbeat loss while in a position.**
- Problem: the watchdog (`controller.py:1101`, `main.py:_watchdog`) flattens at fixed wall-clock times and checks MLL, but a dead tunnel or a TradingView alert that stopped firing only produces a "No public webhook URL" banner (`tunnel.py`) and `feed_status` stale in the UI (`api/webhook.py /webhook/status`). With NOISE position open and no 1-minute bars, band/VWAP exits and the strategy's own risk stop-outs by price are blind; only the native broker SL/TP protect.
- Fix: watchdog rule "position open AND no 1-minute bar for > 3 min -> notify error + block new entries; > 6 min -> flatten with reason FEED_LOST" (user-configurable, default on). CrossTrade `get_positions` / `open_pnl` already give a price-independent check; use it to monitor P&L without TradingView.
- Risk: medium (new auto-flatten; protective, never waits). Effort: M.

**6. Webhook hardening for the public ngrok URL.**
- Problem: secret is in the JSON body and compared constant-time (`webhook/security.py`) - good; rate limit is per IP (`SlidingWindow`), but behind ngrok every request has the same client IP (the proxy), so the limiter cannot separate attackers from TradingView and a flood can lock TradingView out (429 for real alerts). `request.client.host` is the tunnel, not the sender.
- Fix: read `X-Forwarded-For` only when the peer is the local tunnel process; exempt requests with a valid secret from the IP limit and rate-limit invalid-secret attempts instead (they already audit once a minute). Optional: TradingView source-IP allowlist at ngrok (ngrok supports IP policies on paid plans only - skip).
- Risk: low. Effort: S.

**7. Stale heartbeat data not tied to the user-visible root cause.**
- Problem: session 13 spent hours on "STALE 603 s" (10-minute delayed CME data). The status endpoint reports rejected counts but not "your TradingView data is delayed".
- Fix: when 3+ consecutive STALE rejections have an age within 540-660 s, show the plain message "TradingView is sending 10-minute delayed prices - buy the CME real-time data (about $7/month)" on Connections and the pre-flight list. Effort: S.

**8. Pre-flight timing and the "bias" check.**
- Problem: CLAUDE.md says pre-flight 06:40 / bias 06:10 (D2) while `automation/preflight.py` docstring and D34 say 02:50 / 02:40; two sources of truth. The `bias_loaded` check ("TradingAgents bias for today", `preflight.py:46`) can fail the whole pre-flight and force OFF while the AI is only ADVISORY (D72) and the key is not connected - a non-technical user is blocked by a feature that does nothing today.
- Fix: make the bias check a warning (not a failure) while `ledger.may_block` is not proven; align CLAUDE.md with `config.schedule`. Effort: S.

## P2 — win rate / profit hypotheses (testable; run on held-out data, pick on 2021-23, judge on 2024-26, causal data only)

**9. D75-P1 NOISE profit lock** already measured (win 50 -> 53.2%); still awaiting user. Re-test it on the CAUSAL baseline (item 13), because the hindsight set flatters the fade and may change which lock level is best. Effort: S (existing scripts).

**10. Fade-only exit improvement: time-based partial.** Hypothesis: the PM fade (target = VWAP) gives back profit late; exit at 15:30 instead of 15:55 if open and +0.5R, or move the stop to entry once VWAP-distance halves. Test: replay fade trades with the 1-minute bars, compare win rate and bust on HO; keep only if IS and HO both improve. Risk: overfitting, only 1 trade/day. Effort: S.

**11. NOISE entry confirmation (two consecutive closes outside the band).** Hypothesis: a single-bar band touch at the 30-minute check is partly noise; requiring the previous check (or the previous minute close) also outside cuts false breakouts at the cost of trades. Test on the 5-year MNQ set with the existing `noise_sim.py`; accept only if win rate AND profit rise in both halves (the session-13 rule - the single-gate tests so far all failed it, so expect failure; costs only compute). Effort: S.

**12. Day-of-week / event-day sizing, not filtering.** Hypothesis: win rate is lower on FOMC/CPI/NFP days and the day before holidays; instead of skipping, test size 1 vs 0 on those days (a filter) using a stored event calendar (needs historical calendar - the session-13 note says none is cached; free source: BLS/Fed schedules by hand for 5 years). Effort: M.

**13. VIX / realised-vol regime for NOISE.** Hypothesis: the sigma-band breakout works when realised vol of the last 5 days is above its 60-day median (trending days) and fails when low; test as a skip rule and as 1 vs 2 micro sizing on HO. Causal inputs only (prior closes). Effort: M.

## P2 — D77 hindsight fade: causal rebuild plan

**14. Rebuild `main_strategy_5y.csv` and projections from the causal generator.**
- Problem: the live app is already causal (`strategy_service.run_pm_fade` skips only if a NOISE PASS signal exists *so far*, `strategy_service.py:~390`), but `app/backtest/data/main_strategy_5y.csv` (rebuilt by `docs/results/session11/rebuild_main_csv.py`) and `backtest/income_projection.py` use "NOISE never trades all day". Session 13 `causal.py` shows -25% profit and +10 pts bust: pass rates, income and risk numbers shown on Dashboard/Today and used in D70-D75 decisions are optimistic.
- Fix (all steps are offline, no live-code change):
  1. Extend `rebuild_main_csv.py` to import the causal rule from `docs/results/session13/causal.py`: for each day, simulate NOISE minute by minute; a fade at 13:00-15:29 is allowed iff no NOISE entry has fired before that minute; once a fade is open NOISE entries later that day are blocked only if live blocks them (check `controller` rule: one open position per account, max 1 per account).
  2. Output a new CSV (keep the old one as `main_strategy_5y_hindsight.csv`) with a `causal=1` column; add a unit test that every fade row has no NOISE entry earlier that day.
  3. Point `income_projection.py` at the causal file; keep the notice on Dashboard/Today until deployed, then replace it with "causal" and the number date.
  4. Re-run the D70/D71/D74/D75 sizing and eval-pass studies (agents) on the causal CSV and record which conclusions change (the 25K High-risk taper, P2 freeze reset, AI sizing break-even).
  5. Parity test: replay the last N paper days through `strategy_service` and compare with the generator trade by trade (same sort of check D55 already does for NOISE).
- Risk: lowers displayed income (honest). Effort: M (script) + M (re-run studies, agents).

## P3 — UX for a non-technical user running PAPER daily

**15. One "Start my day" screen.** Today the user must attest (`automation/state.py:170 attested_today`), pass pre-flight (11 checks, `preflight.py`), arm accounts and set a mode in separate places; any failed check turns automation OFF with a banner. Fix: a single card on Dashboard: green "Ready to trade" or a plain-language to-do list ("Confirm no other positions" button, "TradingView data is late" fix link). Attestation = one click with a text summary of what is attested; remember "attest daily at 06:30" only as a reminder notification, never auto-attest (non-negotiable #11). Effort: M.

**16. Alerts: one daily digest + push only for actions needed.** `controller.notify` sends many levels (info/warn/error). Fix: collapse info into a 16:30 summary (trades, P&L, skipped reasons in plain words), keep immediate alerts for: feed lost, position mismatch, kill switch, exit missing, tunnel down. Effort: S-M.

**17. Plain-language skip reasons.** Signals store codes (`OUTSIDE_WINDOW`, `NEWS_BLACKOUT`, `PAPER_ONLY_STRATEGY`...). Map each code to one sentence in the UI (single dict in the frontend; test that every backend code has a text). Effort: S.

**18. "Why no trade today?" panel.** Daily list of check minutes with the NOISE band distance (close vs band) and the reason each did not fire; reduces support questions on quiet days. Effort: M.

## P3 — cost

**19. Run the daily AI calls only when they can change a decision.** TradingAgents + Vibe-Trading run every morning for each proxy (`main.py:165 _daily_bias`, `bias/service.py`) even though the result is advisory (D72) and nothing blocks until >= 30 scored calls. Keep recording (the proof needs it), but: (a) run only for the proxy the active strategy uses (MNQ today; MGC is OFF); (b) skip weekends/holidays/no-calendar days; (c) use the cheaper model for Vibe-Trading (`bias/vibe_trading.py:30` defaults to a top model) and measure that its accuracy is not lower on the ledger; (d) cap max tokens per call and cache the OpenBB context per day. Backfill (D78) should be one-off and rate-limited (already). Saves the largest part of the recurring LLM bill. Risk: low. Effort: S.

**20. Data cost.** CME real-time on TradingView (about $7/month) is required; CrossTrade Pro (about $49/month) only when going LIVE - keep PAPER on the simulated adapter. Databento: keep downloads for research only (cached bars are gitignored; document the exact re-download commands and the one-time cost so nobody re-downloads); do not use a paid feed in the live path (bars come from TradingView). Effort: S (docs).

**21. Repo size.** A 40 MB `days.pkl` sits in history at commit 62252ba (HANDOFF session 12), which bloats the bundle and clones. Fix: leave it (no force pushes) but stop the handoff bundle from embedding history older than a shallow baseline, or build the bundle from `git archive` of HEAD. Effort: S.

## Suggested order
1, 2, 3 (restart + exits + missed heartbeat), then 5 (feed-lost flatten), 4 and 6 (tests + limiter), 14 (causal projections, so decisions use honest numbers), 8, 15-17 (UX), 19 (AI cost). 9-13 are experiments for agents after 14 exists.
