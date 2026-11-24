# Fixes report, branch review-fixes-2026-11-24 (2026-11-24)

Source reviews: model_qa.md, held_out_tests/RESULTS.md, code_review.md, ux_review.md, ui_review.md (this folder).

## OPEN, NOT FIXED (user decision, out of scope this session)
- **Item 1: early-close days.** NOISE (and CANDACE/late-day) are never flattened before the CME halt on Nov 26, Nov 27, Dec 24. Keep NOISE off or watch it by hand on those days. Needs a half-day calendar and a flatten before the close.

## Done (commit)
| Item | Status | Commit |
|---|---|---|
| 2 NOISE phantom position after broker stop/TP; same-direction exit+re-entry | done, tests | 54eae72 |
| 3 Consistency cap: TP-fit waiver NOISE only; CANDACE/late-day shrink or skip | done, tests | e1389b2 |
| 4 Live CANDACE fed regular-hours bars only (parity test) | done, tests | 0b2518b |
| 5 UI: alert on failed saves; error + Retry instead of endless "Loading"; safety banner on /api/safety failure | done, tests | e4f1f74, e9bb66e |
| 6a One runner error no longer drops other strategies' exits | done, test | e090ef6 |
| 6b Rollback / pre-D167 saves keep at most one choice ON | done, test | ec4fe97 |
| 6c Time exits fire on first bar at/after the time | done, 3 tests | 15895cc |
| 6d/6e Late-day size under fast evaluation; paper_only for late-day and MGC | done, 2 tests | a86db3d |
| 8 One API-driven UNVERIFIED badge per strategy; late-day PF from API | done (UI side) | 8253691 |
| 10 Docs: kill switch $50 on Pro / $100 Flex+Daily; brief wording; D169-D173; HANDOFF | done | 37bd6b8, 56933b9, ac0ecd9 |
| 11-12 "Now running" strip; NOISE+CANDACE one radio card | done, tests | b30c9aa, f309028 |
| 13 Contrast (blueLight labels, 78% secondary, tint-aware e2e check) | done, static tests only | 343cc1a |
| 14 Plain labels for ~130 skip codes, grouped by strategy, higher on Dashboard | done, tests | 615ae69 |
| 15 Fast-pass cards 2x2, formula in a fold, one disclaimer, badges in title row | done | 5f2c23b |
| 16 Calm animation, distinct KILL SWITCH | done | 32ae324 |
| 17 Phone: header fold, scroll wrappers, fancy glass/gradient polish | partly | 5f2c23b, ed194d6, later CSS commit |

## Not done / partly
- **7 NOISE health warning** (rolling 12-month PF < 1.1 for two quarters): not built. No NOISE parameter was changed (12 variants rejected).
- **9 Fast-pass odds caveat** (odds swing 14%-100% by start period; chosen on judge window): only the single disclaimer under the calculator was kept; the specific swing text was not added.
- **Late-day PF label:** UI reads it from the API; the backend label still says 1.10 and must change to 1.12.
- **Order Flow skips** still do not reach /api/signals/skips (backend).
- **Strategy page phone folds** (page is ~15,500 px tall at 390px): not done.
- "Applies to: <size> EVAL accounts only" on fast-pass cards assumes EVAL-only; not checked against the backend.
- JJ, GALA, zone cards lose per-card badge detail text until the API sends a `badge` field (they still say UNVERIFIED).

## Verification
- Backend full suite: **1675 passed, 5 skipped** (pytest -n auto, 214 s). The `make test` 100%-coverage gate on risk/management/phases was NOT run; run `make test` before relying on this.
- Frontend: vitest 160 passed (38 files); tsc and eslint clean on touched files.
- Browser screenshots and the rendered contrast check: see ui_after/ if present; otherwise not run.
- Never skipped or disabled a test. One late-day assertion was adjusted (late-day now fits to 1 micro under the cap).

## Planning numbers (from the reviews)
NOISE: plan on true PF ~1.2-1.4 (5-year PF 1.52, 95% range 1.22-1.88). CANDACE PF 1.22 (0.92-1.59), unproven. Late-day: chance level, keep OFF. 150K pass odds swing 14%-100% by start half-year.
