# D87 Fast Evaluation — review of commit 50ae195 (2026-11-10)

Verdict: no real bugs found; no code changed. make test (850 passed, 100% cov on risk/management/phases), make lint, make typecheck: green.

Checked:
- EVAL-only: `fast_eval_effective(stage, on)` returns False for any stage != EVAL; evaluated per trade from `a.stage`, so a mid-day stage change takes effect on the next trade. `pretrade` re-checks `acct.stage == "EVAL"` before the early tier. `applies_to_stages` is `Literal["EVAL"]`.
- Default OFF: holder `fast_eval_on=False`, no DB row → off; every mechanism `enabled: false` in all plan YAMLs.
- No martingale: `fast_contracts` returns base after any loss (last closed or today); ladder/early also 0 after loss; never below base; `pace_escalation: Literal[False]`.
- Ladder: extra only while cushion (risk_base) >= cushion_frac x MLL distance; steps validated ascending; capped by `max_contracts`, then by firm_max/internal_max in pretrade.
- Harvest: `min(existing day_stop, x% of target)` — tighten only; cap unchanged.
- Early tier: risk_pct bounded (0, 0.14], raise-only, same window/no-loss/cushion conditions; risk_usd caps and DLL check run after.
- Quality filter: returns a skip reason or None — can only skip.
- Kill switch, DLL/MLL, gates, R:R, hedge, consistency cap: untouched; all pretrade checks still run after sizing.
- Decimal throughout; rule numbers only in YAML (VERIFY-marked); typed phrase "ENABLE FAST EVALUATION" to enable, one-click disable, enable refused without EVAL accounts.
- UI labels honest ("Simulated / unproven", no measured benefit noted, VERIFY badges).

Minor notes (not bugs): `fast_eval.early.until_profit_frac` is not in MY_SETTINGS_KEYS (editable only via YAML); FastEvalCfg.default_on/confirm_phrase in YAML are informational (the phrase constant lives in settings_store).
