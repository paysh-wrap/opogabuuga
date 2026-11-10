# Session 16 - TradingAgents MGC research (D84) inside the AI Duo button

| area | file | change |
|---|---|---|
| runner | `backend/app/bias/ta_runner.py` | `research` command (runs only in `.venv-ta`): TradingAgents analysis + gold prompt (DXY, real yields, Fed/CPI, risk sentiment, trend/levels, 2R target) -> `TA_SETUP` JSON line; pure helpers `research_prompt`, `parse_setup_line`, `finish_research` (stdlib, tested with a fake LLM) |
| adapter | `backend/app/bias/tradingagents_adapter.py` | `research()` (same venv/env/key path as `run`) |
| job + ledger | `backend/app/bias/ta_mgc_research.py`, `main.py::_ta_mgc_research` | 02:45 ET weekday job (only while AI Duo is on with MGC), retry every 30 min on failure; Vibe-Trading opinion on MGC via the existing connection; stored as BiasDecision proxy `GLD.RS` (JSON setup + vt + report); no key = nothing runs |
| pure engine | `backend/app/engine/ta_mgc.py` | `parse_setup` (reason codes), `valid_until_at`, `in_zone`, `past_levels`, `build_plan` (section 7 builder + $ cap + 2R tag), `vibe_agrees` (calls the shared `ai_duo.agree`) |
| runtime | `backend/app/signals/strategy_service.py::_duo_research` | MGC research path inside `run_ai_duo`: one decision a day (trade or SKIP + code), entry at the 1-minute close inside the zone before valid-until |
| UI/API | `api/dashboard.py::_ta_mgc`, `frontend/src/components/TaMgcCard.tsx` | latest research + setup + Vibe opinion + decision; "AI key not connected" fallback |

Tests: `tests/unit/test_ta_mgc.py`, `tests/integration/test_ta_mgc.py` (subprocesses mocked), `TaMgcCard.test.tsx`.
Honest limits: the runner's second LLM step uses `ta.quick_thinking_llm.invoke(...)` of the TradingAgents graph; the package is not installable in the build environment, so this was NOT run against the real library (fake graph in tests). If the attribute is absent the run reports an error and the day is skipped (RESEARCH_FAILED), never a crash. No back-test exists (LLM calls cannot be back-tested).

## D85 additions (AI Duo, same button)
- `risk/checks.py`: `AccountView.max_open_positions/open_positions/open_risk_usd`, `TradeLimits.max_risk_usd`, checks `one_position` (count based), `trade_risk_cap`, `aggregate_risk`; `tests/unit/test_duo_risk.py`; 100% coverage of risk/ kept.
- `management/trade_manage.py` + order manager hook (`MANAGE:<rule>` stop moves) + snapshot persistence; `tests/unit/test_trade_manage.py` (BE, config lock, AI lock, market cap, trail ratchet, short side, real trade through the order manager, restart snapshot).
- Controller: 150K gate, per-account open count and open-risk sum, cushion brake via `auto_contracts`, guard auto rule, per-position `ManageCfg`; `tests/integration/test_ai_duo.py` (150K holds MNQ + MGC, 25K rejects a 2nd position, kill switch flattens all, per-market accounts/windows, AI lock level reaches the position).
