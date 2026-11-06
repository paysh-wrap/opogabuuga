# UI audit against §18 (2026-11-06)

"Before" = state at b318bc0. "Now" = after this branch. Tests: `frontend/src/pages/Audit.test.tsx` (unit),
`frontend/e2e/full.mjs` (`make e2e`, real server on a scratch DB).

| Page | Item | Before | Now |
|---|---|---|---|
| All | "Paytience" at top + tab "Paytience · <Page>" (incl. login/404) | done | done (E2E every page) |
| All | Font colours blue/gold only, WCAG AA | partial (theme.ts test only) | done (theme test + rendered-page contrast E2E; calendar tints fixed) |
| All | Loading / empty / error states | partial | done for every page touched here; others unchanged |
| All | Mobile 390 px, no horizontal scroll, usable nav | partial (Connections only) | done (every page; selects/labels fixed) |
| Header | Paytience · PAPER/LIVE · Automation · EVAL MODE · Trading N of M · ET clock · flatten countdown · jobs · status · KILL SWITCH · alerts | done | done |
| Login | form, error | done | done |
| Dashboard | account cards: stage, risk base/MLL/DLL distance, MLL locked badge | done | done |
| Dashboard | guard ON/OFF, Eval Mode badge, day lock-in badge | missing | done (new dashboard fields) |
| Dashboard | P&L ▲/▼, days since last trade | partial (idle only as alert) | done |
| Dashboard | eval pace incl. 40% consistency headroom + profitable days | missing | done (`/api/accounts/{id}/eval-pace`) |
| Dashboard | cooldown banner per profile (+ typed clear) | missing | done |
| Dashboard | approval queue | missing | done |
| Dashboard | signal / why no trade | done | done |
| Dashboard | bias raw five-tier rating, blackouts | partial (mapped only) | done |
| Dashboard | next Friday payout estimate | missing | done (`/api/plan`) |
| Dashboard | $50k / $70k progress | missing | done |
| Signals | G1–G8, score, plan prices, C1 vs ATR, skip reason | done | done |
| Signals | gross/net R, guard mode, risk profile, per-account result | partial | partial (unchanged) |
| Trade | mode panel, approvals, manual ticket, positions, flatten, arm, pre-flight, attestation | done | done |
| Trade | orders list | partial (positions only) | partial |
| Accounts | mapping, stage, drawdown type, DLL, arm, Eval Mode inherit/on/off, 1–5 selector + priority | done | done |
| Accounts | Lucid link, inactivity | done | done (E2E) |
| Accounts | history | missing | done (audit log per account) |
| Accounts | consistency %, profile, per-account mode override | missing | missing |
| Risk | My Settings + versions | partial (no versions list) | done |
| Risk | Impact Preview before save | missing | done (save disabled until a valid preview) |
| Risk | What-If | missing | done (floor/middle/ceiling, nothing saved) |
| Risk | rollback | missing | done |
| Risk | Evaluation Mode panel: Impact Preview + typed "ENABLE EVALUATION MODE"; OFF one click | partial (confirm() sent the phrase automatically) | done |
| Risk | eval pace | partial (Today only) | done via Dashboard/Today cards |
| Risk | day lock-in, model-fail cooldown, kill log | missing | done |
| Risk | Firm Rules incl. purchase profile, VERIFY badges | missing | done (read-only; editing still via API) |
| Risk | gauges | missing | missing (rule-proximity meters live on Dashboard) |
| Backtest | jobs, results, skip reasons, CSV import | done | done (E2E job) |
| Backtest | guard ON/OFF compare | missing | done (drawdown_type param + pair run + compare table) |
| Backtest | Eval Mode ON/OFF compare | missing | done |
| Backtest | bias ablation | missing | done (recorded vs NEUTRAL pair; "filter OFF" mode not in the engine) |
| Backtest | weekly payout simulation | missing | done (same `plan_payout` as live) |
| Backtest | Monte Carlo P(≥$50k)/P(≥$70k), N = 1..5 | missing | done (10,000 block-bootstrap paths) |
| Strategy Lab | champion/challenger, proposals, rollback, insights | done | done |
| Payouts & Plan | tickets sweep/skim, submitted/processed, frequency, skim mode, tracker, projection | done | done (E2E) |
| Connections | broker, webhook URL/secret, heartbeat, calendar, TradingAgents version | done | done |
| Connections | test alert | missing | done (dry-run `POST /api/webhook/test-alert`, nothing stored) |
| Journal & Logs | search, snapshots, CSV | done | done |
| Settings | mode, notifications, schedule, auto-resume, checklist, purchase gate | done | done |
| Settings | weights | partial | partial |
| Today (§24.1) | eval pace from `/api/accounts/{id}/eval-pace` | partial | done |

Safety fix found by the E2E: arming a first-sessions account while FULL-AUTO kept FULL; it now downgrades to
SEMI-AUTO with audit + notice (§13).
