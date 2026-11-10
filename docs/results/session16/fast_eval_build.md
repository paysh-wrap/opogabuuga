# Session 16 - Fast Evaluation build (D87)

Code: `backend/app/risk/fast_eval.py` (pure, 100% covered), config `FastEvalCfg` (config.py) + `fast_eval:` in config/rules/*.yaml,
master switch `RiskProfile(kind="fast_eval")` via `settings_store.set_fast_eval`, API `/api/risk/fast-eval` (+ `/preview`),
wiring in `automation/controller.py` (fixed-size ladder/early extras, quality-day skip `FAST_EVAL_QUALITY_DAY`, tightened day stop)
and `risk/checks.pretrade(fast=...)` (early risk % on score-tier strategies). UI: `frontend/src/components/FastEvalPanel.tsx` on the Risk page.

Mechanisms: ladder (extra micros while cushion >= step x loss limit, 0 after any loss), harvest (day stop = min(existing, x% of target)),
early tier (first N trades and/or below a profit share, cushion >= threshold, never after a loss), quality day (prev_day / trailing).
Safety: after sizing, DLL room, MLL distance minus kill distance, worst case, consistency cap and every other pre-trade check still run.

Study defaults (reading A, held-out, simulated): 150K ladder; 50K quality-day filter; 100K/25K none; harvest/early no measured benefit (OFF).
Impact Preview numbers: config/fast_eval_study.yaml (copied from the README table). Open points: the study ladder used a 1-micro base; the
150K size table base is larger, so max_contracts 2 leaves that account at its base (ladder is a no-op there) - raise `max_contracts`
only after a re-run at the real base. True noise-band-width day filters were not studied (stream proxies only).
Tests: tests/unit/test_fast_eval.py, test_risk_phase4 (pretrade), test_risk_api, test_auto_size (EVAL-only, ladder, quality day), Audit.test.tsx.
