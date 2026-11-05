# CLAUDE.md — Paytience (read at the start of EVERY session)

Automated confluence trading app for 1–5 Lucid Trading LucidDaily 25K accounts.
Purchase profile: EOD drawdown | DLL ON | Consistency 40% | Weekly payouts.
Full spec: `docs/MASTER_PROMPT_v9.2.md` (binding; user to add verbatim). This file is the condensed contract.

## How we work
- Priorities: firm-rule compliance > capital safety > correctness > working UI > readability.
- Build phase by phase (spec §22). After each phase: run ALL tests, show results, list open questions, STOP for approval.
- One phase per branch (`phase-N`), small commits, plan mode per phase, never commit secrets.
- Ask before guessing on money, rules, credentials, broker APIs, data sources.
- Never weaken a safety check to make a test pass. `Decimal` for every price and money value.
- Code names/signatures in the spec are binding contracts.
- Rule numbers live ONLY in `config/rules/lucid_daily_25k.yaml` + DB (editable via validated Risk UI). Hardcoded rule value = bug. `# VERIFY` values show a gold badge until confirmed.
- engine/, management/, risk/, phases/ are PURE (no I/O, injected Clock). Live, paper, replay, backtest and shadow call the SAME code.

## Non-negotiables (§1)
1. Never automate/scrape TradingView or Lucid websites. Live signals ONLY via TradingView webhooks. Playwright tests OUR app only.
2. Never persist passwords. Encrypted tokens only (OS keychain preferred), memory-only credential modal.
3. Lucid has no API. Lucid account = Tradovate account ID + rule profile + stage (EVAL/FUNDED/LIVE). "Lucid" button just opens their dashboard.
4. Never disguise automation as manual trading.
5. Default PAPER. LIVE needs `PAYTIENCE_ALLOW_LIVE=true` + Settings toggle + typed "I ACCEPT LIVE RISK" + Live-Readiness Checklist.
6. Respect script licenses; keep attribution; non-commercial → "PERSONAL USE ONLY". Never touch protected code.
7. Never hedge. Household-wide EQUITY_INDEX direction lock across accounts/profiles/instruments → Skip("HEDGE_LOCK"). Max 1 open position per account.
8. No silent failures: error → block new entries + log + UI banner + notify.
9. Lab may NEVER modify a Pillar (§17.1) — enforced by registry + tests + pillar-module hash.
10. Evaluation Mode applies ONLY to stage EVAL — never FUNDED/LIVE. Enforced in pure risk code + tests.
11. External-positions attestation required each session before arming.

## Confluence engine (§6)
- LunqFX Fractal = WHERE/WHAT (direction, INVALID→stop anchor, T2→target). MSO = WHEN/WHETHER. TradingAgents = WHICH SIDE TODAY. Phase/Guard/Risk = WHETHER + HOW. None triggers alone.
- C2 sweeps C1 LOW + closes inside → LONG; sweeps C1 HIGH → SHORT. "C2 closes back inside C1" = ON (pillar). CISD counts only if printed before C2 close.
- State: IDLE→SWEEP→CONFIRMED→ARMED→ENTERED→MANAGING→RESOLVED(TP|STOP|BE|TRAIL|TIME|STRUCT|MODEL_FAILED|EXPIRED|CANCELLED)→IDLE.
- One entry per model (model_key = symbol+profile+c1_time_ms). Model-fail cooldown: 3 consecutive MODEL_FAILED → profile paused 5 sessions (user setting).
- MSO events timestamped at CONFIRMATION bar (pivot + right bars), never the pivot bar. Closed bars only, no lookahead.
- Gates (all at entry-bar close): G1 window/news/feed/halt/cooldown · G2 bias · G3 model valid + C1 range ≥ c1_min_range_atr×HTF ATR(14) · G4 MSO structure agrees · G5 CHoCH/BoS after sweep · G6 no opposing div · G7 valid TradePlan · G8 Phase+Guard+Risk+consistency+hedge approve.
- Score (sizing only), normalized to 100; < min_score(60) → no trade; NEUTRAL bias needs ≥ 75. Every skip stores a reason code.
- Profiles: TIGHT 1m→15m (risk base < $1,500), STD 5m→1H (≥ $1,500). MNQ core; MES only after §16.6 gate.

## TradePlan (§7) — R:R 2.0–3.0 [Pillar]
stop = invalid − sign×buffer, tick-rounded away from entry; skip STOP_INVALID / STOP_TOO_TIGHT / RR_BELOW_MIN; TP = min(T2, 3R) rounded toward entry; recheck ≥2R after rounding. After market fill: rebuild with fill price; outside 2–3R → flatten "RR_INVALID_AFTER_FILL".

## Drawdown Guard (§8) [Pillar]
- auto: ON only if drawdown_type == intraday AND MLL not locked. EVAL (EOD) → OFF.
- ON: 2 brackets (leg A = ceil(n/2) TP at 50% of TP; leg B TP full); leg A fill → leg B stop to BE (entry + fee_cover_ticks); runner trail ≤ 2R, ratchet only. Min 2 contracts. Stop-modify failure → flatten + pause.
- OFF: 1 bracket full size, min 1 contract. Trade keeps its mode until closed.
- Early exits (C3 close, MSO CHoCH against) only before +1R / partial.

## Risk engine (§9) — 100% coverage
- risk_base = equity incl. open P&L − current MLL. cfg = effective_risk_cfg(acct, base_cfg, eval_cfg).
- Tiers standard 60–74→7%, 75–89→9%, ≥90→11%. Eval Mode 10/12/14%, max_risk_usd $140, warmup 10.
- Ceiling only if: first trade today AND last closed not a loss AND not streak-floor AND trades_in_stage ≥ warmup; else middle.
- Force floor: losses_today>0 | today_net_r ≥ 2R | dd_from_peak_base ≥ 20% | in warmup | after 4 consecutive losses (until 2 wins).
- size_contracts: per = stop_ticks×tick_value + fee_rt + slip_ticks×tick_value; n = min(risk//per, firm_max, internal_max); < min_qty → STOP_TOO_WIDE.
- Day stop: 2 consecutive losses | risk + margin > DLL remaining | max trades | (EVAL) today's profit ≥ consistency day stop.
- Pause account: risk_base < $500. Kill switch: within $100 of MLL or any breach (checked every P&L update, incl. intraday on EOD accounts).
- Hold rule (D8): app-initiated exits wait ≥ 6 s; protective exits (stop, TP leg, kill switch, breach, news, flat) never wait. Warn at 20% of profit from ≤ 5 s holds (Lucid limit 50%).

## Phase engine + MLL (§10)
- update_mll: intraday trails always; EOD trails only on the once-per-session EOD call with settled balance; lock when peak ≥ lock_trigger.
- EVAL: target $1,250, 40% consistency, ≥3 profitable days, $1,000 EOD DD (MLL 24,000 → lock 25,100 at EOD peak 26,100), DLL $600, news blacked out. Pass → auto-disarm "PASSED – awaiting Lucid", Eval Mode auto-OFF.
- FUNDED: intraday trailing until 26,100 → locked 25,100; DLL $600; news = HARD BREACH (flat 1 min before → 1 min after); $6,000 day → live move.
- LIVE: per config (VERIFY). Any account LIVE → block household sim accounts.
- Stage change away from EVAL → Eval Mode forced OFF + audit + notify. Inactivity alert at 21 days.

## Evaluation Mode (§11C)
Changes ONLY tiers/floor/middle/ceiling (10/12/14), warmup 10, max_risk_usd 140. Never changes gates, score, R:R, guard, DLL/MLL, day stops, lock-in, kill switch, pause floor, bounds, hedge/news/flat rules. No martingale, no pace escalation. Enable = Impact Preview + typed "ENABLE EVALUATION MODE"; disable = one click. Applies to next NEW trade. Auto-OFF on PASSED/stage change/reclassification.
Consistency guard (EVAL): cap 40%×1,250 = $500; day stop 35%×1,250 = $437.50; reduce contracts to fit cap else Skip("CONSISTENCY_CAP").

## Automation (§13) & Payouts (§14)
- Modes OFF | SEMI-AUTO | FULL-AUTO. Starts OFF. First 5 sessions of each stage: OFF/SEMI only.
- Pre-flight 09:25: broker, token >2 h, heartbeat, calendar, bias, VERIFY (LIVE), reconciled, no orphans, attestation, clock drift <2 s. Fail → OFF + banner.
- Kill switch / mismatch / hedge / stop-modify pauses NEVER auto-resume.
- Flatten: news −2 min; auto 16:40; hard flat 16:44 ET.
- Payouts weekly Fri 17:05: balance ≥ 28,600 → sweep to 28,100; else if locked & skim=half → 50% of week profit if ≥ $500 and leaves ≥ 26,100; else none. Submitted → trading blocked until processed. Never leave balance < $26,100.

## Lab (§17)
Tunables only within §17.2 bounds; walk-forward + guards; challenger in SHADOW ≥10 sessions/20 trades; user approval; apply at 18:00; max 1 per 14 days; auto-rollback. Never touches pillars, eval_mode, cooldown, lock-in, payout keys.

## UI (§18)
"Paytience" on every page; tab "Paytience · <Page>". Font colors blue/gold only (theme.ts). Red/green only as small badges; P&L uses ▲/▼ + sign. No mock data in pages.

## Commands
`make install` · `make keys` · `make create-admin` · `make migrate` · `make dev` (API+UI :8000) · `make web` (Vite :5173)
`make test` · `make lint` · `make typecheck` · `make e2e` (E2E_PASSWORD=…) · `make check` · `make up` (Docker)
TradingAgents runs ONLY in `.venv-ta` via `app/bias/ta_runner.py` (subprocess JSON). Never import it in the API process.
Pending proposals: docs/IMPROVEMENTS.md (build nothing there without approval). Decisions: docs/DECISIONS.md.

## Approved changes (see docs/DECISIONS.md — these override the master prompt)
- D1: instruments MNQ (core), MES, MYM, MGC; MES/MYM/MGC disabled until §16.6 gate. METALS super-group for MGC.
- D2: morning window 06:45–11:30 ET; calendar 06:00, bias 06:10, pre-flight 06:40.
- D3: API Keys page; keys write-only, encrypted, never logged/returned.
