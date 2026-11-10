# Session 16 - NOISE strategy presets (D82)

User approval 2026-11-10 ("Yes build abc"): three presets for NOISE on MNQ, selectable on the Strategy page.

## What changed
| area | file | change |
|---|---|---|
| preset definitions (rule numbers) | `config/strategy_presets.yaml` | A `pro25k_classic`, B `pro100k_low_risk`, C `pro150k_low_risk`: labels, pass/bust, warning text, overlay (noise, pm_fade, noise_cfg stop + lock, size tables) |
| config | `backend/app/config.py` | `NoiseCfg.profit_lock_trigger_pts/profit_lock_pts` (+validator), `StrategyCfg.preset` with a before-validator that overlays the preset, `load_presets()` |
| settings | `backend/app/risk/settings_store.py` | `strategy.preset` added to My Settings keys (versioned, audited, validated, rollback) |
| pure profit lock | `backend/app/management/profit_lock.py` | `lock_triggered`, `lock_stop` (Decimal, tick-rounded toward entry, no clock/I/O) |
| order manager | `backend/app/execution/order_manager.py`, `trade_state.py` | `OpenTrade.profit_lock/profit_locked`; on each bar the stop of open legs is ratcheted to entry+lock; a STOP fill after a lock is reported `PROFIT_LOCK`; snapshot round trip (old snapshots load) |
| controller | `backend/app/automation/controller.py` | NOISE trades get the lock from config; `PROFIT_LOCK` exit marks the signal `lock_exit` + CLOSED |
| strategy service | `backend/app/signals/strategy_service.py` | `lock_exit` today -> no new NOISE entries |
| API | `backend/app/api/dashboard.py` | `/api/strategies` returns `presets` (rows, active, plan size, matches_plan) |
| UI | `frontend/src/components/StrategyPresets.tsx`, `pages/Strategy.tsx`, `StrategyButtons.tsx` types | radio cards with pass/bust labels, warning badges (A, B), recommended C preselected, detail line, Apply / Back to custom |

## Behaviour notes
- Default is no preset (plan file values). Nothing changes until the user clicks Apply; mode stays PAPER.
- Every preset keeps: $250 stop per micro on every trade, hourly band/VWAP trailing exits, 16:00 flat. Preset C adds the profit lock; A/B turn the afternoon fade on (paper accounts only, existing rule), C turns it off.
- Evaluation Mode size tables (size_table_eval*) are not touched by presets (test `test_preset_touches_nothing_else`).
- The preset's single size row is used for every account (tier_for falls back to the smallest row). The UI warns when the loaded plan's account size differs from the preset's. D74 AI sizing still adds +1 micro once the live ledger is proven.
- Not changed: plain (non-lock) broker stop-outs still leave the NOISE signal state as before (pre-existing behaviour, out of scope).

## Tests
New: `tests/unit/test_profit_lock.py` (7: pure long/short/rounding, order-manager lock + locked exit, short side, no-lock/plain stop, stop-modify failure, snapshot), `tests/integration/test_presets.py` (9: yaml labels, A/B/C overlays, nothing else changed, bad preset/lock rejected, select via My Settings + audit + API, controller locked-stop exit ends the day, strategy service suppresses entries), `frontend/src/components/StrategyPresets.test.tsx` (3).
Results: see final lines below.

Results: backend 699 passed / 5 skipped, coverage risk+management+phases 100%; frontend 65 passed (18 files); ruff, eslint, mypy, tsc clean.
