# Main strategy (D47) — trend-aligned 1.75R on MGC

Saved as the main strategy on 2026-11-06 at the user's request: "find the best intraday strategy … 1.75 R:R … still
save it as the main strategy — we are missing the main component, TradingAgents". Live in every Pro/Flex plan
(`config/rules/lucid_{pro,flex}_*.yaml`), locked by `tests/unit/test_plans.py::test_main_strategy_d47`.

## What it trades (every step is automatic — the engine repeats it on every bar)
1. **Market / hours**: MGC (Micro Gold) only, entries 03:00–15:30 ET, flat by 16:40 ET (Lucid rules unchanged).
2. **Setup**: LunqFX C1→C2→C3 fractal — C2 sweeps C1's high/low and closes back inside (pillar), CISD, limit entry at
   the CISD level (4-bar timeout).
3. **Target**: every trade aims at **1.75–1.8R** (`rr_min 1.75`, `rr_max 1.8`). Setups whose own T2 is closer than
   1.75R are skipped. No 1R trades any more (`no_break_rr_cap: null`).
4. **Trend agreement** (the edge): trade only when **UT Bot Alerts 5m** AND **EMA 200 5m** both point in the trade's
   direction (`filters.trend.utbot_5m`, `filters.trend.ema200_5m`). Same math as TradingView (parity 99.8–99.9%).
5. **Gates unchanged**: score ≥ 60 (sizing only), C1 ≥ 0.4 × ATR, MSO/structure as score items, news blackouts,
   cooldowns, one entry per model, all Lucid checks (MLL/DLL/consistency/hedge/max contracts) before every order.
6. **Daily bias (G2)**: TradingAgents on GLD at 02:40 ET decides LONG only / SHORT only / NEUTRAL / NO_TRADE. Not
   connected yet → the app takes no trades until the Anthropic key is added (fail-safe).

## Why this one (7 years of real MGC data, Results O + P)
| | 2019–2023 (used to choose) | 2024–2026 (never seen when choosing) |
|---|---|---|
| All setups at 1.75R, no filter | 3,000 tr 30% −0.33R | 2,768 tr 28% −0.32R |
| **Main: UT Bot 5m + EMA200 5m, T2 ≥ 1.75R, score 60, C1 0.4** | **60 tr 43% −0.01R** | **44 tr 39% −0.01R** |
| Old plan's best hours (D37) added | 56 tr 41% −0.10R | 63 tr 30% −0.26R |
| Squeeze 5m+15m (D45) | 325 tr 30% −0.30R (older half) | 435 tr 33% −0.18R (newer half) |
- 103,256 filter combinations were searched; the ones that looked best on 2019–2023 (47–48%) fell to 25–38% on
  2024–2026 → over-fitting. The main strategy was chosen for holding up on the unseen years, not for its best number.
- **70% at 1.75R is not reachable with these setups.** Break-even at 1.75R (after fees) is ≈ 38–39% wins.
- Old plan (D36 1R/2–3R mix + D37 hours) in the engine, Nov 2024 – Oct 2026: 391 tr, 43% win, −$1,201.

## What TradingAgents can add (upper limit measured on the same 7 years)
| Bias source | trades | win | R/trade |
|---|---|---|---|
| none (all backtests) | 104 | 41% | −0.01R |
| **perfect** daily direction (hindsight — no real tool can do this) | 73 | 49% | +0.18R |
| 20-day trend at the open (simple, no lookahead) | 55 | 47% | +0.15R (2024–26: 40%, +0.08R, 20 tr) |
| previous day's direction | 67 | 37% | −0.12R |
A good daily bias can turn the strategy profitable (+0.1 to +0.2R per trade) but cannot push it to 70%.

## How to keep it repeatable / improve it safely
- Change nothing by hand in the plan files; switches live on the Risk page (My Settings, versioned + rollback).
- Any new idea must beat this table on 2024–2026 after being chosen on 2019–2023 only
  (`docs/results/tools/best175.py`), then be confirmed in the engine (`research.py` per month + `planmix.py`).
- Re-measure every month with new Databento data; when TradingAgents is connected, compare paper results with and
  without its bias for ≥ 30 trades before going live.
- Open options for the user (not built): (a) 20-day-trend bias as a fallback when TradingAgents is unavailable (today:
  no bias = no trade); (b) never flatten a trade that filled at a BETTER price than planned (the §7 recheck currently
  flattens some gap-through fills as "stop too tight" — pillar rule, needs approval).
