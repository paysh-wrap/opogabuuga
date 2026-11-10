# Session 16 - AI Duo build (D83)

Spec: docs/results/session16/ai_combined_strategy_design.md plus the user updates of 2026-11-10 (window 03:00-11:30 ET, MNQ + MGC).

| area | file | change |
|---|---|---|
| pure engine | `backend/app/engine/ai_duo.py` | `ai_side` (reason codes), `aggregate`, `pullback_trigger`, `plan` (structure stop capped at the NOISE $ stop, 2.0R target, 1.5R floor) |
| config | `backend/app/config.py` | `AiDuoCfg` (markets, window_start/end, excluded, rr_target/rr_min >= 1.5, paper_only Literal[True]), `strategy.ai_duo` (default False) |
| runtime | `backend/app/signals/strategy_service.py` | `run_ai_duo` per market (one decision/day, SKIP rows with codes, audit log), `hedge_lock_vs`, NOISE blocked while Duo holds the opposite side, `_gate(enabled=...)` |
| AI call for MGC | `backend/app/bias/service.py` | proxies include the Duo markets (GLD for MGC) while Duo is on |
| controller | `backend/app/automation/controller.py` | AI_DUO strategy mode, paper-only guard, fixed 1 micro |
| ledger/API/UI | `bias/ledger.py` `duo_decisions`, `api/dashboard.py`, `engine/strategy_catalog.py`, `StrategyButtons.tsx` | button via catalog, decisions list with reason codes |
| settings | `risk/settings_store.py` | `strategy.ai_duo`, `strategy.ai_duo_cfg.markets/window_start/window_end` (validated) |

Tests: `tests/unit/test_ai_duo.py` (engine + config), `tests/integration/test_ai_duo.py` (long/capped entry, every no-trade code, no-pullback skip, news, 03:00 London entry, configurable start, 09:30-09:35 bar, MGC entry, markets setting, hedge cases: NOISE opposite / same / closed / Duo-first / same-bar tie / MGC no clash, non-paper refusal, settings validation, MGC AI proxy), `StrategyButtons.test.tsx` (decision list).
Known limits: the preset-style caveat on hedge lock: a NOISE signal that was never executed (e.g. rejected by risk) still reads as pending and blocks an opposite Duo that day (conservative). No historical performance exists (not back-testable).
