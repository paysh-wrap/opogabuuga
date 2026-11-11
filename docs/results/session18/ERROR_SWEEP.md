# Error sweep (session 18, D120)

Run: scratch DB + temp admin, Playwright over all 16 routes at 1280 px and 390 px (console, 4xx/5xx, NaN/undefined/None/%%/Invalid Date, horizontal overflow).
Used the existing frontend/dist (NO build, per instruction), so UI source changes from this session are not in the bundle yet.

## Fixed
- backend/app/main.py:68 CSP had no `font-src`; the inlined `data:` woff2 fonts were blocked on EVERY page (console error). Added `font-src 'self' data:`.
- pine/Paytience_Bridge.pine:96 the `if barstate.isconfirmed` guard had been deleted by the earlier WIP (indented body left orphaned = Pine syntax error and no closed-bar guarantee). Restored.
- Stale tests updated for D120: test_webhook, test_signals_flow, test_pipeline_parity, test_mso_disabled, test_zone_atr (1.15 * zAtr5).

## Clean
No 4xx/5xx, no page errors, no horizontal overflow at 390 px, no NaN/undefined/%%/Invalid Date. The "None" hits are legitimate copy ("None waiting", "None today").

## Listed, not fixed (other agents' areas)
- backend/tests/integration/test_auto_size.py:103 (test_high_risk_profile_switches_table), test_eval_mode_uses_eval_table_only_on_eval_accounts, test_eval_growth_row_is_applied_by_the_controller: sizing returns 2 contracts where 3 is expected (sizing/controller work in progress).
- backend/tests/unit/test_plans.py::test_strategy_buttons_d55[pro/flex 50k,100k,150k], ::test_size_table_validation_and_plans, tests/unit/test_order_flow.py::test_config_paper_only_is_a_choice_and_floor_stays: failed in the full run against the in-progress plan YAMLs (sizing agent).
- Dormant MSO code kept (engine/confluence.py, scoring.py, structure_filter.py, indicators/bigbeluga_mso.py, backtest/parity.py, replay.py, many unit tests rely on `indicators.mso.enabled=True`); deleting needs a larger refactor. Dashboard `mso_enabled` is now always false.
