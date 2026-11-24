# Legacy NOISE removal inventory (D174, user-approved 2026-11-24)

Newest NOISE = main choice NOISE + CANDACE through Fast Evaluation fast-pass (D156-D163) plus its late-day option. Everything below was searched with `grep -rn "noise_ai_split|split_risk|AI Duo|ai_duo|noise_only|legacy"` over backend/app, frontend/src, config.

| Item | Where used | Decision | Reason |
|---|---|---|---|
| "NOISE + AI Duo 50/50 risk split" button, `strategy.noise_ai_split` (+ `_share`), D92 | config.py, settings_store (allowed key, choice map), catalog, dashboard flag, strategy_gates card, controller sizing block, UI choice maps | REMOVED | Older NOISE variant, never measured, not the main strategy. |
| `risk/split_risk.py` (split_contracts, split_budget, side_budget_left, split_active) | only the controller block, dashboard, gates | REMOVED | Used only by the split. |
| Tests `test_split_risk.py` (unit and integration) | shared helpers also used by 6 test files | REMOVED; helpers moved to `tests/integration/trade_helpers.py` | |
| Preset `pro25k_classic` ("NOISE $250 stop + afternoon fade ON", already `superseded: true`, D134) | config/strategy_presets.yaml, tests | REMOVED | Superseded NOISE-only setup. A save naming it loads as "custom" (`REMOVED_PRESETS`). |
| `SPLIT_BUDGET_EXCEEDED` check (`TradeLimits.side_budget_left`) in risk/checks.py | risk check | KEPT for safety/compat, forced OFF | It is a risk check; no caller sets it now (default None). Own unit test keeps coverage at 100%. |
| Presets `pro25k_s19`, `pro50k_s19`, `pro100k_low_risk`, `pro150k_low_risk` | Strategy page presets | KEPT | Not superseded; the low-risk ones are lower-risk modes; size tables feed non-eval sizing. |
| Preset UI `superseded` badge | StrategyPresets.tsx | KEPT | Generic data-driven, no hard-coded NOISE variant. |
| AI Duo itself, TA MGC research, D85 management | engine, signals, UI | KEPT | Not a NOISE variant (its own Lesser-dropdown strategy). |
| `LEGACY_LUNQFX_KEYS`, "OD" lock tag | config.py, strategy_service | KEPT | Settings migration / old open positions. |
| D133 eval size tables, `FastPassCfg` fields, D156 sizes | fast-pass sizing | KEPT | Still read by fast-pass and 25K/50K/100K/150K switches; no unused legacy field found. |
| ORDER_FLOW_AUCTION `risk_share` (plans A/B) | order flow | KEPT | Different feature (Order Flow, secondary). |
| Lucid/risk checks, lower-risk mode, hedge lock, kill switch, per-account plans | | KEPT | Out of scope. |

Old saved settings: stored `strategy.noise_ai_split`, `strategy.noise_ai_split_share` and `strategy.preset = pro25k_classic` are ignored on load (`merged_raw` skips them; `StrategyCfg` strips them from old plan files). Test: `test_old_saved_settings_with_removed_toggles_still_load`.
