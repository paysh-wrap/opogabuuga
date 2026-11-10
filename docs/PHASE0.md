# Phase 0 — Decisions, File Tree, Open Questions

Status: **WAITING FOR APPROVAL**. No code until the blocking questions (B1–B6) are answered.

## 1. File tree (spec §3, to be scaffolded in Phase 1)

```
paytience/
├── CLAUDE.md  README.md  Makefile  docker-compose.yml  .env.example  .gitignore
├── config/rules/lucid_daily_25k.yaml
├── docs/  (MASTER_PROMPT_v9.2.md, PHASE0.md, ADRs)
├── pine/  Paytience_Bridge.pine  Paytience_Bridge_Strategy.pine
├── backend/
│   ├── pyproject.toml  alembic.ini  alembic/
│   ├── app/
│   │   ├── main.py config.py clock.py db.py ws.py
│   │   ├── models/ schemas/ api/
│   │   ├── webhook/      security.py parser_bridge.py parser_original.py
│   │   ├── indicators/   lunqfx_fractal.py bigbeluga_mso.py atr.py smt.py
│   │   ├── engine/       state_machine.py confluence.py scoring.py trade_plan.py filters.py   (PURE)
│   │   ├── management/   drawdown_guard.py runner.py exits.py                               (PURE)
│   │   ├── risk/         risk_base.py tiers.py sizing.py checks.py validation.py
│   │   │                 eval_mode.py consistency.py hedge_lock.py                          (PURE)
│   │   ├── phases/       phase_engine.py mll_tracker.py transitions.py                      (PURE)
│   │   ├── automation/   controller.py preflight.py pauses.py account_selector.py cooldown.py
│   │   ├── execution/    order_manager.py adapters/{base,tradovate,sim}.py
│   │   ├── monitor/      pnl_monitor.py kill_switch.py reconcile.py inactivity.py
│   │   ├── payouts/      payout_engine.py plan_tracker.py
│   │   ├── bias/         tradingagents_adapter.py
│   │   ├── calendar/     econ_calendar.py
│   │   ├── backtest/     data_store.py replay.py sim_fills.py metrics.py monte_carlo.py
│   │   ├── lab/          tunables.py pillars.py walk_forward.py optimizer.py shadow.py
│   │   └── workers/      jobs.py scheduler.py
│   └── tests/ unit/ property/ integration/ fixtures/
└── frontend/
    ├── package.json vite.config.ts tsconfig.json tailwind.config.ts playwright.config.ts
    └── src/ app/ components/ pages/ lib/{api.ts,ws.ts,theme.ts}
```

Note: the package `app/calendar/` shadows Python's stdlib `calendar` only for relative imports; all imports will be absolute (`app.calendar...`) — fine, but I'd rename to `econ/` if you don't mind (Q-C9).

## 2. Broker route — research findings + recommendation (BLOCKING, B1)

Findings (third-party sources, must be verified by you with Lucid/Tradovate):
- Lucid reportedly **allows automation/API trading** on eval and funded accounts; bans HFT, microscalping and cross-account hedging; trader is liable for software errors. LucidDaily funded is reportedly intraday drawdown with a "flat 1 min before/after" news rule — matches spec.
- **Native Tradovate API keys are generally NOT issued for prop-firm accounts** (reports: requires own live account with ~$1,000 equity + ~$25/mo API add-on, and prop accounts have API disabled). Partner-OAuth routes (CrossTrade, PickMyTrade) exist precisely because of this.

Consequence for the architecture: the `BrokerAdapter` needs `get_positions`, `get_balance`, `stream_fills`, `modify_stop`. A webhook-only relay is mostly **one-way**: we can send brackets, but may not be able to read positions/fills/balance back. Without read-back, the kill switch ($100 from MLL), reconcile, hedge detection and stop-modify confirmation cannot be enforced → the app would be in permanent CONSERVATIVE MODE, and per §1.9 that may block FULL-AUTO entirely.

Options:
| Option | Send orders | Read positions/fills/P&L | Notes |
|---|---|---|---|
| A. Tradovate native API (OAuth/partner) | ✅ | ✅ | Best fit for spec; only if Lucid/Tradovate grant API access on your Lucid accounts |
| C. CrossTrade / PickMyTrade-style partner | ✅ | ⚠️ varies | Third-party dependency + fee |

**Recommendation:** ask Lucid support in writing (a) whether API trading via Tradovate is permitted on LucidDaily eval/funded and (b) whether they/Tradovate will enable API access (OAuth) on those account IDs. If yes → Option A primary, Sim for paper. If no → Option B, and I'll implement `capabilities` honestly so SEMI-AUTO works but FULL-AUTO stays blocked until position read-back exists. Phase 1–4 do not depend on this, so we can proceed with Sim while you ask.

## 3. Historical/market data — recommendation (BLOCKING, B2)

- **Recorder (free):** our own heartbeat recorder — but only starts accumulating after Phase 2; not enough for the §16.9 gate (≥100 trades).
- **Recommended: Databento** (CME Globex MDP3 OHLCV-1m for MNQ/MES/NQ/ES; pay-per-use, typically small $ for a few years of 1m bars). Gives back-adjusted signals + real-contract P&L, and ES for SMT.
- Alternative: TradingView CSV export (manual, limited history per plan) imported via the CSV importer.
- Live market data via Tradovate API needs a CME data subscription — not needed if live signals come only from TradingView webhooks (they do, §1.1).

## 4. BLOCKING questions (need answers before Phase 1/2)

- **B1 Broker route** — see §2. Have you confirmed with Lucid that automation + API/OAuth is allowed and available on your account IDs? Which option?
- **B2 Data source** — Databento OK (you create the account and API key; I never see a password)? Budget cap?
- **B3 Indicator sources + licenses** — I will not scrape TradingView (§1.1). Please paste the Pine source + license text of "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]" and "Market Structure Oscillator [BigBeluga]". If either is **protected/invite-only**, Option A (port) is impossible for it and we must use Option B (original script + "Any alert() function call") — and only if that script emits alert() calls with the fields we need. BigBeluga scripts are usually CC BY-NC-SA 4.0 → README "PERSONAL USE ONLY".
- **B4 Hosting** — where does it run: your PC (Docker + Cloudflare Tunnel on 443) or a VPS? Windows/macOS/Linux? This container is ephemeral; I need a **GitHub repo** to push to (name/owner?).
- **B5 TradingAgents** — it needs an LLM provider API key + market-data source (yfinance/Alpha Vantage). Which LLM provider/model and daily budget? I'll pin the latest release verified at install (v0.3.x/v0.4.0 seen; the five-tier BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL scale exists since v0.2.2 — matches §15).
- **B6 Verify firm numbers** — every `# VERIFY` in §23, especially: eval drawdown EOD with lock 25,100 @ 26,100; funded intraday; DLL $600 both stages; 40% consistency; MNQ fees $1.50 RT (Tradovate+exchange fees with Lucid are often higher — please give the real all-in RT); max contracts; flat_by 16:45.

## 5. Spec issues I found (please confirm intended behavior)

- **S1 STD profile can never trade on EVAL.** Profile rule: TIGHT if risk base < $1,500, STD if ≥ $1,500. EVAL max risk base is $1,437.50 (and FUNDED while trailing ≤ $1,000). So STD only appears after FUNDED lock. Intended? (Alternatively "both may run" = profile choice is per-account setting.)
- **S2 Funded-trailing phase is very restrictive.** Guard ON needs ≥2 contracts; at base ≤ $1,000 × 7% = $70, two MNQ contracts fit only if stop ≤ ~16 pts (34$/contract) — but min_stop_ticks 20 = 5 pts, so OK range is 5–16 pts. Wider-stop setups skip (spec test confirms). Fine, just flagging that many funded-trailing signals will be STOP_TOO_WIDE.
- **S3 `plan.r_avg_assumed: 255`** — I read this as **$ per 1R** (average risk in dollars across stages). Correct?
- **S4 Header says "PART 1 of 2"** but the text ends with "END PROMPT" and includes §24 (v9.3). I'm treating it as complete — please paste Part 2 if it exists.
- **S5 TradingAgents runs on QQQ/SPY** (equity ETF, daily) at 07:00 — its rating uses prior-day data; fine for daily bias, just confirming you accept the cost per day (several LLM calls).
- **S6 Rapid-trade metric** "firm limit 50%" and min_hold 6 s — Lucid's microscalping rule wording should be verified (B6).
- **S7 All spec arithmetic checks out** — I verified every §21 numeric case by hand (plan/guard/runner/sizing/tiers/DLL tests/streaks/Eval Mode/consistency/MLL/payouts). No contradictions found.

## 6. Other questions (non-blocking, defaults in brackets)

- C1 Notifications: Discord / Telegram / email? [Discord webhook]
- C2 How many Lucid accounts do you have now, and stages? [design for 5]
- C3 TradingView plan with webhooks + 2FA already active? [assume yes]
- C4 Economic calendar source for high-impact USD events (Forex Factory JSON, Finnhub, Trading Economics)? No data = no trading. [Finnhub free tier, verify]
- C5 Python 3.11 pinned in Docker (container here has 3.13)? [python:3.11-slim in Docker, code 3.11+ compatible]
- C6 Dashboard login: single user? [single admin user, Argon2]
- C7 Postgres now or SQLite first? [SQLite, Postgres-ready]
- C8 OK to add the full master prompt verbatim as `docs/MASTER_PROMPT_v9.2.md`? [yes — please paste it as a file or I'll transcribe it]
- C9 Rename `calendar/` package to `econ_calendar/`? [yes]

## 7. Phase 0 tests

None — no code yet. Phase 1 starts with scaffold + config loader + validation tests.
