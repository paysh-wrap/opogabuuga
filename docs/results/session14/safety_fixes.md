# Session 14 safety fixes (audit items 1-5 + trade-ref and failed-exit bugs)

Approved by the user after the Session 13 audit (docs/IMPROVEMENTS.md). No risk check, sizing, kill switch or consistency rule was changed.

## What changed

| Item | Change | Main files (backend/app) |
|---|---|---|
| 1 Restart recovery | Every tracked trade is snapshotted onto `Trade.om_state` (plan, legs, stops, flags) at each commit. On startup (lifespan) the controller rebuilds `OrderManager.trades`: paper = the in-memory simulator is re-seeded from the snapshot (`SimAdapter.restore_bracket`); live = snapshot must match the broker position/working orders. Position flat at broker -> trade waits in `closing=RESTART_FLAT` and closes after the 60 s grace with the existing "P&L unverified" alert. Unmatched / different-size position -> flatten + pause account `RESTART_UNMANAGED` + error "Restart found an unmanaged position". Broker unreadable -> account paused `RESTART_UNVERIFIED`, trades kept from snapshot, retried every watchdog tick. Rows without a snapshot (older) behave as before (paper: `SIM_RESTART`). | `automation/controller.py` (`recover_open_trades`, `_recover`, `_recover_live`, `_restore_sim`), `execution/trade_state.py` (new), `execution/adapters/sim.py`, `main.py` |
| 2 Exit confirmation | A strategy exit now only writes `features.exit_requested = {reason, at}` on the signal; `state` stays `OPEN` until `_close_trade` (or `_drop_unfilled_trade`) books the real close, which flips it to `CLOSED`. No open trade at request time -> CLOSED immediately (old behaviour). New watchdog step `exit_watchdog` re-issues exits for every marker with an open trade (also for trades not under management: flattens the account). Applies to NOISE, OPEN_DRIVE, PM_FADE and AI_BIAS exits (all use `_close`). The 16:44 hard flat is unchanged. | `signals/strategy_service.py`, `automation/controller.py` |
| 3 Lost signals | `Event.processed_at` (set after the strategy run; NULL = accepted but maybe never processed). At startup and every watchdog tick, heartbeats of the last `reliability.reprocess_window_min` (5) min with `processed_at` NULL and at least 20 s old are replayed in exits-only mode (no new entry from a stale bar; market state / LunqFX gate not re-applied; fills, stops and strategy exits on that bar still run). In-flight guard, 3 attempts then marked + alert, same-bar entry guard in `run_noise`. "Missed check minute" error alert when a NOISE check minute has no stored 1-minute bar `reliability.missed_check_alert_s` (90) s after it closed. | `signals/recovery.py` (new), `api/webhook.py` (`after_accept`), `signals/strategy_service.py`, `main.py` |
| 4 Duplicate orders | Trade id and broker client id are deterministic: `P-{signal_id}-{account_id}` (legs `...-A`/`-B`/`-ONLY`), so a manual re-run is rejected by the existing one-order-per-signal-per-account guard and by the broker. Test: `UnconfirmedError` on place -> account paused `ORDER_REJECTS` (after the emergency flatten) -> no second place on the next heartbeat. | `automation/controller.py`, `execution/order_manager.py` |
| 5 Feed lost | Watchdog (`feed_guard`, also after each heartbeat): a position is open (tracked trade or broker position) and no 1-minute bar for > `feed_warn_min` (3) min -> error notify once + new entries blocked (`FEED_LOST` result); > `feed_flatten_min` (6) min -> flatten reason `FEED_LOST` (protective, no hold wait). Falls back to the finest slower feed (5-minute profile) with the extra bar minutes added. On/off and both thresholds are rules config (`reliability.*` in every plan yaml, validated, editable in My Settings). The broker's own open P&L keeps feeding the existing MLL/DLL monitor. | `automation/controller.py`, `config.py` (`ReliabilityCfg`), `risk/settings_store.py`, `config/rules/*.yaml` |
| Bug A | Trade refs restarted at `T1` after each restart and the lookups used `scalar_one_or_none` (MultipleResultsFound -> P&L and day stats never booked). Refs are now unique; lookups use `_trade_row` (open rows only, newest first, `.first()`). | `automation/controller.py` |
| Bug B | A failed strategy exit (`BrokerError`/`UnconfirmedError` from flatten) escaped the BackgroundTask silently. Now caught in `ctl.strategy_exit`, `_retry_strategy_exits` and the webhook loop: error notify "Exit order failed - retrying", trade goes to pending exits (marker is persisted), retried each bar and from `watchdog_tick`. | `automation/controller.py`, `api/webhook.py` |

Migration: `backend/alembic/versions/b4c8d2e6f1a3_restart_recovery_processed_at.py` (`trades.om_state`, `events.processed_at`; existing events are marked processed).
New API: `GET /api/safety` (unmanaged, feed, pending exits, missed checks); `GET /api/positions` rows carry `exit_pending`.

## UI

- `components/SafetyBanners.tsx` (in `Layout`, every page): banners for unmanaged position after restart, feed lost, missed check minute, exit pending broker confirmation.
- Trade page, Positions table: badge "exit pending broker confirmation".
- Risk page: `components/FeedGuardSettings.tsx` (on/off + warn/close minutes).

## Tests

- backend: `tests/integration/test_restart_recovery.py` (paper restart mid-trade then TP, live matched / flat / unmanaged / unreadable, duplicate legacy refs, deterministic client id, UnconfirmedError, failed exit retry, marker survives restart, positions/safety API), `tests/integration/test_reliability.py` (processed_at, replay, age/in-flight guards, give-up, startup replay, missed check, feed guard warn/block/flatten/clear/settings/off/slower feed), `tests/integration/test_strategy_service.py` (marker semantics, exits-only), `tests/unit/test_trade_state.py`.
- frontend: `components/SafetyBanners.test.tsx`, `pages/Trade.test.tsx` (badge).

## Known limits

- Order rows are not updated by the snapshot; recovery uses `Trade.om_state` (Order rows stay informational).
- A restarted paper trade has no simulator price until the next bar (open P&L reads 0 until then).
- Live recovery was tested against a fake broker only (no CrossTrade account here).
