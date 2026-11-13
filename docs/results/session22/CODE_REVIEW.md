# Session 22 code review (2026-11-13) — branch ccr-49c22917-zlwvy3, base ffcf7e2 (D138)

## Scope and method
- Read line by line: automation/controller.py (all), execution/order_manager.py, execution/adapters/{sim,router,crosstrade}.py,
  risk/checks.py, automation/state.py, phases/{phase_engine,mll_tracker,payout_plan}.py, engine/noise.py, engine/order_flow.py,
  signals/strategy_service.py (NOISE + Order Flow paths), webhook/{service,security}.py, api/webhook.py, risk/{hedge_lock,eval_mode,
  eod_balance,lucid_scale}.py, main.py background loops, and every D137 / D138 diff (risk, phases, automation, config, API, YAMLs).
- Everything else was checked by the automated gates only (ruff, mypy --strict, eslint, tsc, 1,259 backend + 111 frontend tests,
  100 % coverage on risk/management/phases, browser E2E). A review cannot prove "no bugs"; it lowers the risk where money moves.

## Baseline (ffcf7e2, before any change)
Backend 1,252 passed / 3 skipped, coverage 100 % (risk, management, phases); ruff + format + mypy clean; frontend 111 passed,
eslint + tsc clean. The last commit's "full suite running" note is now confirmed green.

## Bugs found and FIXED (each with a regression test that fails without the fix)
| # | Where | Bug | Fix | Test |
|---|---|---|---|---|
| R1 | controller._one (hedge-lock position read) | `open_positions()` reads every account's broker positions without catching BrokerError: one unreadable account raised out of `execute()`, aborting the whole signal with no banner / per-account reason (§1.8 no silent failures). Fail-closed, but silent. | Caught → `BROKER_ERROR: …` result for that account (still blocks the trade). | test_automation_flow::test_unreadable_positions_skip_with_broker_error_not_exception |
| R2 | order_manager._entries_done | When the RR re-check after a fill failed and the flatten then raised BrokerError, the exception escaped `on_fill` before `closing` was set: the watchdog never retried, and in `_one` the Trade row was rolled back while the order manager still tracked the trade. | `closing` set first; a failed flatten emits PAUSE (banner) and `retry_closing` flattens again while the position is open. | test_order_manager::test_rr_invalid_flatten_failure_pauses_and_stays_closing |
| R3 | adapters/sim.py | The simulator pushed one PnlUpdate per account on EVERY bar into a queue nothing reads → unbounded memory growth for as long as the app runs (several MB a day). | Backlog capped at 1,000 (oldest dropped). | test_order_manager::test_sim_pnl_stream_backlog_is_bounded |
| R4 | adapters/crosstrade._req | A non-JSON reply (proxy / Cloudflare HTML error page) raised a plain ValueError that escaped every BrokerError handler — on `place_bracket` an order of unknown outcome could go untracked. A 504 gateway timeout on a mutation was treated as "not done". | Unreadable reply → UnconfirmedError on mutations (2xx or 5xx), BrokerError on reads; 504 joins 500/502 as "outcome unknown". | test_crosstrade_adapter::test_unreadable_reply_is_a_broker_error_never_a_crash |
| R5 | live restart recovery (CrossTrade) | The adapter's order-id → role map lives in memory and the snapshot never stored the take-profit order id: after a restart, the stop / target fill of a recovered live bracket came back EXTERNAL, was ignored, and the trade stayed "open" until the 16:40 flatten closed it with an unverified $0 P&L. | Legs store `tp_order_id` (snapshot field, old snapshots still load); recovery re-registers bracket / stop / TP ids with the live adapter (`register_bracket`). | test_restart_recovery::test_live_restart_re_registers_bracket_order_roles, test_crosstrade_adapter::test_registered_bracket_maps_fills_after_restart, test_trade_state::test_tp_order_id_round_trips_and_old_snapshots_still_load |

| R6 | connections/service.run_test | D3 "keys are write-only, never returned" broken: Alpha Vantage quotes the key in its error text ("We have detected your API key as …") and the app relayed that text to the Connections page (caught by the browser E2E). | Every secret field's value is replaced by ••• in a test result before it is stored, audited or returned (all providers). | test_connections::test_key_quoted_back_by_the_service_is_redacted |

R4 and R5 are on the LIVE path only (paper accounts never touch CrossTrade); live trading stays behind the Live-Readiness Checklist.

## Browser E2E (§21, `make e2e`) — stale since the D93 mission UI, repaired
At ffcf7e2 the suite ran 3 passed / 17 failed. Not app bugs; the test had not followed the D93 look:
- every page heading's accessible name is "Paytience · <Page>" (mission.css `h1::before`), so `exact: true` on "Dashboard" never
  matched → heading lookup accepts the optional brand prefix, case-insensitive (headings are uppercased by CSS);
- the backtest card is uppercased by CSS → read `textContent`, not `innerText`;
- the gold gradient "Paytience" brand (background-clip: text, color transparent) was scored on its transparent colour (1.07) →
  gradient text is judged on its gradient stops (worst stop kept).
After the fixes: **20 passed / 0 failed**, including the R6 key-redaction check that found a real bug.

## Findings NOT changed (need a user decision or are by design)
- F1 LucidScale DLL (D138, VERIFY): `dll_for` uses `acct.mll_peak`, but `update_mll` stops updating the peak once the MLL has locked.
  The scaled DLL is therefore frozen at 60 % of the profit at lock time (Pro 25K ≈ $660–750) instead of growing with the peak EOD
  balance. This is TIGHTER than the plan card, never looser. Changing it would loosen a loss limit → left as is; ask the user / Lucid.
- F2 NOISE reversal on a LIVE account: on a check bar that exits and re-enters the other way, a CrossTrade trade is still "closing"
  until its exit fill arrives, so the reversal entry is skipped (POSITION_OPEN) and its signal stays OPEN as a phantom position for
  the rest of the day (no order, no money at risk; one missed trade). Paper (simulator) flattens instantly and is not affected.
  Fixing it means deciding how a live reversal should wait for the fill — not done without approval.
  **CLOSED by D139 (user 2026-11-13): correct, by design. Never hedge — a reversal must never be entered while the old position
  is still open or awaiting its exit fill. Do not change.**
- F3 Brackets on the sim: a limit entry's own bar does not check stop/target (`continue` after the fill) — conservative for TP,
  optimistic for a same-bar stop. Research convention elsewhere is stop-first; documented, unchanged.
- F4 controller line ~539: the Order Flow / AI cushion brake uses `rules.eval.max_loss_limit` also for funded accounts (equal in every
  current plan, so no effect today).

## After the fixes
See HANDOFF.md session 22 for the final test counts, E2E and build.
