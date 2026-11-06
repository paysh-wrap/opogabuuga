# Main strategy (D49) — trend-aligned 1.5–2.5R on Micro Gold, Nasdaq and S&P

Live in every Pro/Flex plan (`config/rules/lucid_{pro,flex}_*.yaml`), locked by
`backend/tests/unit/test_plans.py::test_main_strategy_d49`. History: D47 (1.75R, MGC only) → D49 (user: "it can even
be as low as 1.5 — do 1.5–2.5"; "profit first + test MNQ/MES with the same rules").

## What it trades (all automatic — the engine repeats it on every bar)
1. **Markets / hours (ET)**: MGC 03:00–15:30 · MNQ and MES 06:45–09:30 + 09:35–15:30. Flat by 16:40.
2. **Setup**: LunqFX C1→C2→C3 fractal — C2 sweeps C1's high/low and closes back inside (pillar), CISD, limit entry
   at the CISD level (4-bar timeout). Both profiles: TIGHT (1m→15m) and STD (5m→1H).
3. **Target**: the model's own T2, capped at **2.5R**; setups whose T2 is closer than **1.5R** are skipped.
   Never a 1R trade (the config refuses any plan below 1.5R — D48/D49).
4. **Trend agreement**: only when **UT Bot Alerts 5m** AND **EMA 200 5m** both point the trade's way.
5. **Unchanged gates + Lucid rules**: score ≥ 60, C1 ≥ 0.4 × ATR, news blackouts, cooldowns, one entry per model per
   account, MLL/DLL/consistency/max-contracts/hedge-lock (MNQ+MES never opposite) checked before every order,
   1 position per account, risk 7/9/11% of risk base.
6. **TradingAgents (G2)**: daily LONG-only / SHORT-only / NEUTRAL per proxy (GLD, QQQ, SPY). Not connected yet →
   NO_TRADE (no API key = no trades).

## Results — real engine, Databento futures, NEUTRAL bias (Results R)
| Nov 2024 – Aug 2025 (first 10 months) | trades | win | PF | $ |
|---|---|---|---|---|
| MGC | 33 | 36% | 1.14 | +142 |
| MNQ | 25 | 44% | 1.94 | +696 |
| MES | 14 | 36% | 1.32 | +140 |
| **combined** | **72** | **39%** | **1.45** | **+978** |
Old plan (D36/D37 1R mix), MGC, Nov 2024 – Oct 2026: 391 tr, 43%, −$1,201. Break-even at ~1.8R average ≈ 36% wins.
Full 2-year numbers are appended to Results R when the runs finish.

## Likely win rate WITH TradingAgents (docs/results/tools/bias_est.py)
| Daily bias accuracy | trades | win | $ (same 10 months, 3 markets) |
|---|---|---|---|
| none (today's backtests) | 72 | 39% | +978 |
| 55% (likely for an LLM daily call) | ~38 | ~40% | ~+597 |
| 60% | ~41 | ~41% | ~+706 |
| 100% (perfect, impossible) | 60 | ~46% | ~+1,575 |
~85% of these trades already go with the day's direction (the trend filters see it intraday), so a daily bias
mostly removes good trades on the days it is wrong. Recommended (needs your OK): let TradingAgents block only on
strong ratings (BUY → long only, SELL → short only; OVERWEIGHT/HOLD/UNDERWEIGHT → both sides).

## Trades per day
≈ 0.33/day for one account across the three markets (≈ 1–2 per week). 2–4/day at 1.5–2.5R is not reachable
profitably with these setups: every MGC setup with a ≥1.5R target is ~1.7/day and loses ~−0.3R/trade.

## How to keep it repeatable / improve it safely
- Settings live in the plan files; the Risk page switches are versioned with rollback. The Lab can't touch R:R.
- A new idea must be chosen on 2019–2023, beat this on 2024–2026 (`best1525.py`), then be confirmed in the engine
  (`research.py` per month + `combo_markets.py`).
- When TradingAgents is connected: paper-trade ≥ 30 trades and compare with/without its bias before going live.
