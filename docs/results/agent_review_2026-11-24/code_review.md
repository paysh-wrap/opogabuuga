# Code review: main strategy (NOISE + CANDACE + late-day), 2026-11-24

Scope: engine/noise.py, engine/candace_ict.py, engine/late_day.py, signals/strategy_service.py, risk/fast_pass.py, risk/checks.py, automation/controller.py (sizing path), risk/settings_store.py (D167).
Tests: the targeted unit suite passed (96 passed, 2 skipped). I also wrote 6 scratch tests that assert the current buggy behaviour (outside the repo, in the session scratch dir). All 6 passed, so the CONFIRMED findings below were reproduced by running code.

## CRITICAL

### C1. Early-close and holiday sessions: NOISE is never flattened before the CME halt (CONFIRMED)
- Where: strategy_service.py:306 (the flat is `k == flat_k`, which is k=389 only), and controller.flat_time_check (16:40 to 18:00 only). There is no early-close logic anywhere in the code (searched for half_day, early_close, 13:15).
- What happens: on Thanksgiving Thu 11-26 (Globex halts about 13:00 ET) and Fri 11-27 (halts 13:15 ET), a NOISE entry from a check between 10:00 and 13:00 is never flattened. The 16:00 bar never comes, the 16:40 flatten fails because the market is closed, and after 18:00 nothing retries. The position can be carried overnight and over the weekend, with gap risk through the stop. The research script skipped these days (fewer than 380 bars), and noise_sim flattens at the last bar, so live is the only path that holds.
- Scratch test: a Fri 2026-11-27 session that ends at 13:15 gives 1 entry, 0 exits, and the signal is still OPEN.
- Fix: add an exchange early-close table to the yaml (marked VERIFY). Skip NOISE and late-day on those sessions (this matches research), or flatten every strategy at early_close minus 2 min and start flat_time_check from there.
- Test: with FixedClock on 2026-11-27 and an open NOISE position, it is flattened before 13:15 and there are no entries.
- Urgent: these days are this week. Until fixed, turn NOISE off or watch it by hand on 11-26, 11-27 and 12-24.

## HIGH

### H1. CANDACE live reads overnight and pre-market bars; research was RTH-only (CONFIRMED)
- Where: strategy_service.py:1559 feeds every stored hour into replay_day. The Pine heartbeat runs 24h, and the MNQ windows include 03:00-09:30.
- Effects:
  - It trades 09:01-09:30, which was never tested.
  - SESSION, swing and hourly-FVG pools, the dealing range and the displacement average all include overnight bars.
  - On Mondays the "previous day" becomes Sunday evening, so there are no gap levels and PDH/PDL is wrong.
- Scratch tests: on 86 random-walk days, live gave 96 signals against 26 for RTH-only. 47 of the live signals were before 09:31, and 60 days differed. On a Monday, gap_levels is [] for live against 5 levels for research.
- Fix: filter history and today to bars that close in (09:30, 16:00]. Build the previous day from the last RTH session.
- Test: replay with all-hours bars must equal replay with RTH-only bars.

### H2. NOISE keeps a phantom position; live and backtest diverge (CONFIRMED)
- Where: controller._close_trade and _mark_signal_closed. A broker STOP or TP, a D57 exit or a kill flatten never sets the signal to CLOSED without exit_requested. Then strategy_service.py:304 treats the signal as still OPEN.
- Effects:
  - Research and noise_sim set pos=None after the emergency stop and re-enter at the next check. Live HOLDs instead and skips that trade.
  - The fast-pass $100/$75 stops (about 49/36 pt) make this common.
  - noise.decide gives EXIT then ENTER in the same direction when upper < close < VWAP (confirmed). On CrossTrade the exit fill arrives later, so the re-entry hits POSITION_OPEN. The account then sits flat while the strategy thinks it is long.
- Scratch test: a stopped 10:00 long, with price above the band and VWAP at 11:00, gives no entry.
- Fix:
  - When the last trade of a signal closes without exit_requested, mark the signal CLOSED (reason = broker reason).
  - In run_noise, merge a same-direction EXIT+ENTER into HOLD, but still count the entry.
- Test: an integration test where a STOP-closed trade leads to a new PASS at the next check, plus a merge test.
- Note: this is not the D139 reversal, which stays as designed.

## MEDIUM

### M1. Strategy exits depend on one exact bar or on the replay's own outcome (CONFIRMED by reading)
- Where: strategy_service.py:1564 sends CAND_TIME_EXIT only if the replay outcome is TIME and exit_time equals this bar. Also the NOISE flat at :306 (k==389) and the late flat (late_day.py:94, equality at 15:59).
- Failing cases:
  - The replay shows a TP touch that the live limit did not fill, or a stop that was rebuilt on the fill price. The replay then believes the trade closed, so there is no TIME exit and the 15-minute max hold (B2) is not enforced.
  - A missed heartbeat on the exit bar gives the same result.
  - In both cases the trade runs to its bracket or to the 16:40 flatten.
- Fix: exit when `at >= hold_until` (or flat_at) and the signal still has open trades.
- Test: TP touched but not filled leads to an exit at 15 minutes; a missing 15:59 bar leads to an exit at 16:00.

### M2. The N6 consistency waiver also covers CANDACE and LATE_DAY, which have real take-profits (CONFIRMED)
- Where: checks.py:262. It skips the TP-reward fit for every fixed-size strategy.
- Failing case (scratch test): 150K, today +$3,400, cap $3,600. CANDACE takes 5 micros with an 80 pt TP (+$800) and pretrade says ok. If the TP fills between P&L polls, the day ends at +$4,200, above the 40% cap. The CLAUDE.md contract says "reduce contracts to fit cap".
- Fix: add a `tp_is_exit` flag to TradeLimits so these modes keep the fit_contracts path. NOISE keeps N6.
- Test: CANDACE near the cap gets reduced contracts or CONSISTENCY_CAP.

### M3. Fast Evaluation can raise the late-day size above late_contracts and late_steps (latent; PLAUSIBLE)
- Where: controller.py:911 caps the size with `min(sized, fp.contracts)` only when fp is set. For LATE_DAY fp is None, so fast_contracts (ladder or early) can lift a braked 1-micro leg.
- It is OFF in the plan files today, which is why it is latent.
- Fix: cap with `(fp or late).contracts`. Test it the same way.

### M4. D167 one-strategy rule has holes (CONFIRMED: rollback)
- `rollback()` (settings_store.py:391) does no check. Scratch test: rolling back turns jj_fpt and gala_pa back on together.
- Stored pre-D167 settings that have two strategies ON stay ON. The check at settings_store.py:368 only runs when the change touches a strategy.
- `pm_fade` runs without NOISE (strategy_service.py:1683; the plan default is pm_fade: true). With any other choice, the fade trades every day on FUNDED accounts.
- `strategy.ai_bias` is not part of STRATEGY_CHOICES.
- Fix: enforce the rule in effective() or run() (block entries and show a banner), check it in rollback, and gate pm_fade on noise.

### M5. One runner's exception drops every strategy's exits for that bar (PLAUSIBLE)
- Where: run() makes a single commit at the end, and the webhook.py:117 path resets the outputs. An error in one runner rolls back the exit markers of the other runners.
- A deterministic error repeats on the exits_only replay, so it does not clear itself.
- Fix: wrap each runner in its own try/commit.

## NIT
- `paper_only` is ignored for LATE_DAY, MGC_NOISE and MGC_CANDACE (controller.py:545). The value is written into features but never read.
- NOISE `prior` (strategy_service.py:311) falls back to an older session's close when yesterday's 16:00 bar is missing; research skips that day. σ includes days with 300 to 379 bars; research requires at least 380.
- Same-bar priority between strategies comes only from code order: NOISE, then CANDACE, then LATE. This matters at 10:00 and 15:00. Document it and add a test.
- If starting_balance is None, the account falls back to the plan size (controller.py:612), so "own size only" is not really checked for the fast pass. Require a starting balance.
- late_day.py's docstring mentions a `replay` function that does not exist. The ATR includes partial sessions.

## Checked and OK
- Minute index, check bars and k=389 match noise_area.py.
- Late-day 13:30 and 15:00 indices match the study. The 15:59 exit is intentional (late_leg_sizes/app_variant.py).
- DST is handled through astimezone.
- Fast pass applies to EVAL accounts of their own size only, and is capped by firm and internal max, max_trade_risk_usd, the DLL/MLL worst case and the fast-eval cap (for NOISE and CANDACE).
- The D154 tie-break is correct.
- The hedge lock includes in-flight orders.
- D139 is intact.
