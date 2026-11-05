# Decisions log (user-approved changes to Master Prompt v9.2)

## D1 — 2026-11-05 — Instruments added
- MGC (Micro Gold, COMEX): tick 0.10, tick_value $1.00, fee_rt VERIFY, enabled: false until §16.6 gate passes.
- MYM (Micro Dow / "US30"): tick 1.0, tick_value $0.50, fee_rt VERIFY, enabled: false until §16.6 gate passes.
- Lucid availability of both: VERIFY.
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
