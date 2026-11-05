# Paytience — handoff for a new session (read first)

**Restore:** `git clone paytience.bundle paytience && cd paytience && git checkout phase-5` → read CLAUDE.md,
docs/DECISIONS.md (D1–D20), docs/CONVERSATION_LOG.md, docs/IMPROVEMENTS.md, docs/LUCID_RULES.md.
Setup: `make install` (Python venv, npm, TradingAgents v0.7.1 in .venv-ta), `make keys >> .env`,
`make create-admin` (user **PayDay**; the user knows the password — never commit it), `make build`, `make dev`.
Check: `E2E_PASSWORD=<pw> make check` (lint, mypy strict, 292 backend tests w/ 100% coverage on risk/management/phases,
10 UI tests, 20-step browser E2E).

## Status
- Phases 0–4 done. Phase 5 nearly done (branch phase-5): BrokerAdapter, Sim adapter, order manager (guard, 1:1, BE,
  trailing, emergency flatten, RR-after-fill), automation controller (OFF/SEMI/FULL, 5-session rule, approvals),
  selector, pre-flight, pauses, kill switch, flat times, reconciliation, automation API, CrossTrade adapter
  (docs-verified REST; needs CrossTrade Pro).
- Remaining Phase 5: CrossTrade WebSocket fills (executionUpdate) → wire CrossTrade into Controller when
  PAYTIENCE_ALLOW_LIVE + checklist; TradersPost send-only adapter (docs.traderspost.io needed);
  then Phase 6 UI (Automation page D4, Risk page w/ Eval Mode + 1:1 toggle, Accounts, Dashboard, Today, PWA).
- Indicators are spec-derived (docs/INDICATOR_SPEC.md); verify against original Pine source once
  www.tradingview.com is reachable (environment "Psyd" now has Full network access).

## User preferences
- Keep replies SHORT; do the complex work fully. Ask before building improvements. Never break Lucid rules.
- Always give a private download (bundle + zip + conversation log) after each phase. Nothing public.
- Route must be Tradovate + TradingView with the custom indicators. Paper first.
- Approved: 1:1 mode (D7/D16), win-rate filters E1–E7, self-learning A1–A8, funded 40% consistency (own limit),
  windows 06:45–09:30, 09:35–11:30, 13:30–15:30 ET, MNQ core + MES/MYM/MGC shadow until gated.
