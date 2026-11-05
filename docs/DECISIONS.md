# Decisions log (user-approved changes to Master Prompt v9.2)

## D1 — 2026-11-05 — Instruments added
- MGC (Micro Gold, COMEX): tick 0.10, tick_value $1.00, fee_rt VERIFY, enabled: false until §16.6 gate passes.
- MYM (Micro Dow / "US30"): tick 1.0, tick_value $0.50, fee_rt VERIFY, enabled: false until §16.6 gate passes.
- Lucid availability: both listed on Lucid's "Approved Products and Commissions" support article
  (per search results; the article host is blocked in this build session — confirm in your dashboard).
- Fees updated from Lucid's list: MNQ/MES/MYM $0.50/side → fee_rt 1.00; MGC $0.80/side → fee_rt 1.60 (VERIFY).
  The spec's §21 unit cases keep using the $1.50 placeholder as explicit test inputs.
- Correlation: MYM ∈ {YM,MYM} ⊂ EQUITY_INDEX (hedge lock applies with MNQ/MES).
  MGC ∈ {GC,MGC} ⊂ new METALS super-group (own hedge lock; not locked against equity index).
- Max 1 open position per account still applies across all instruments.
- min_stop_ticks / stop_buffer_ticks / slippage become per-instrument (global default + override).
- Bias proxies: YM→DIA, GC→GLD (TradingAgents).

## D2 — 2026-11-05 — Morning window 06:45–11:30 ET (was 09:35–11:30)
- windows: [["06:45","11:30"],["13:30","15:30"]] (still a user setting, editable in Risk UI).
- Schedule moved so everything is ready before 06:45:
  calendar 06:00 → bias 06:10 (10-min timeout) → pre-flight 06:40.
- Pre-09:30 is Globex overnight: thinner liquidity, 08:30 ET news (blackouts still apply).
  Backtest data must include overnight bars; report results per window slice.

## D3 — 2026-11-05 — API Keys page (UI + API)
- Page "API Keys" (under Connections): TradingAgents (repo URL, pinned version/tag, LLM provider + key,
  data vendor key), historical data key (e.g. Databento), broker/relay, notification webhooks.
- Keys write-only: encrypted at rest (OS keychain/Fernet), never returned by the API (last 4 only),
  never logged; "Test" button per key; audit-logged changes.
- TradingAgents key added later by user; until then bias = NO_TRADE + alert (spec §15) — so
  trading stays blocked by G2 unless user enables a documented bias-OFF ablation for PAPER only.

## D4 — 2026-11-05 — Dedicated Automation page
- New UI page "Automation" (not only a panel on Trade): master mode OFF/SEMI/FULL, per-account arm +
  overrides, pre-flight result, attestation, auto-pause reasons + resume rules, kill switch, approval queue,
  live rule-check table per account (DLL left, MLL distance, consistency headroom, hedge lock, news/flat times).
- Built in Phase 5 (controller) + Phase 6 (UI). Every Lucid rule check runs in pure risk code before any
  order; any error blocks new entries (§1.9).

## D5 — 2026-11-05 — Dashboard login
- Admin login created via `make create-admin` (Argon2 hash in DB only; plaintext never stored or committed).

## D6 — 2026-11-05 — TradingAgents install
- Pinned tag v0.7.1 (commit 3e44faafa042daf953f6ec2422ae36bb1fd4f50f), Apache-2.0.
- Installed by `make tradingagents` into its own venv (.venv-ta); trading process talks to it via a
  JSON subprocess runner with a hard timeout. REVIEW / unknown rating → NO_TRADE + alert.

## D7 — 2026-11-05 — "1:1 mode" toggle (REQUESTED — details pending user answers; build in Phases 3/4/6)
User request: Risk Management toggle enabling 1:1 reward:risk trades; ONLY in that mode up to 3 losses/day
(normal mode keeps 2); in that mode take 50% profit at 75% of the distance to take-profit.
This overrides the §7 2–3R pillar while ON (user-owned change; the Lab may never toggle or tune it).
Unchanged in this mode: all gates, DLL/MLL pre-trade checks, kill switch, consistency guard, hedge lock,
news/flat times, force_floor after a loss, Evaluation Mode scope.
Open questions: Q1 TP exactly 1R? Q2 stop → breakeven after the 75% partial? Q3 1-contract sizes: skip or
no partial? Q4 which stages? Q5 max trades/day stays 3? Q6 own backtest gate before enabling on paid accounts?

## D8 — 2026-11-05 — Minimum hold time (Lucid microscalping rule)
- Lucid (FAQ, per search results): flagged if > 50% of profits come from trades held <= 5 s. VERIFY.
- Parameters: behavior.min_hold_seconds 6, firm_microscalp_hold_seconds 5, rapid_trade_warn_pct 20,
  firm_microscalp_pct 50 (config-validated: hold > 5 s, warn < firm limit).
- Enforcement (Phase 4/5): every app-initiated exit waits until held >= 6 s. Never delayed: stop-loss,
  broker TP leg, kill switch, MLL/DLL breach, news flatten, flat times (earlier rules win, per user).
- Metric: % of profit from trades held <= 5 s, per account per payout cycle; warn at 20%.
- Proposal (needs approval): pause NEW entries on an account if that share reaches 35%.
