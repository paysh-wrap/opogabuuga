# Shared brief — Paytience strategy research (read fully before starting)

## Goal
Find intraday futures strategies for **MNQ (Micro Nasdaq)** and **MGC (Micro Gold)** with the best *verified*
win rate AND positive expectancy after costs, that a Lucid Trading prop account can trade. "Verified" means:
documented in published research or replicated by us on real data with an honest held-out test. No hype, no
unverifiable claims. A high win rate with negative expectancy is a FAIL — always report expectancy.

## Paths
- Repo (read-only for you unless your task says otherwise): /home/user/opogabuuga  (CLAUDE.md = project rules)
- Python with pandas/numpy/scipy/databento + the app installed: /home/user/opogabuuga/.venv/bin/python
- Data (1-minute OHLCV, Databento continuous volume-roll `.v.0`, UTC timestamps, columns
  timestamp,open,high,low,close,volume):
  - /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/data/mnq_1m.csv
  - /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/data/mgc_1m.csv
  They may still be downloading (≈ 2019-05 → 2026-11-07). Done when `…/data/mnq.log` / `mgc.log` show a 2026
  line and the background job printed "done"; check `tail -1` of the log, do not re-download (it costs money).
  Write your own cached parquet next to your code if you want speed; never modify the CSVs.
- Your work dir: /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/agents/<your-name>/
- Your final report: /tmp/claude-0/-home-user-opogabuuga/586832a8-5df0-547f-b3c1-a5482ce5859f/scratchpad/results/<your-name>.md
- Do NOT edit, commit or push anything in the repo. Do NOT post to any external website/service (read-only web).

## Machine
4 CPUs shared with ~5 other agents. Vectorize with pandas/numpy; run at most ONE heavy process at a time
(prefix with `nice -n 10`). No grid searches with thousands of combos — keep it to a few dozen well-motivated
variants (overfitting is the enemy).

## Test protocol (binding)
- Convert to America/New_York. Use only closed bars, no lookahead. Signals on bar close → entry at next bar open,
  or a resting stop/limit order that fills only if price trades THROUGH the level by 1 tick.
- If stop and target are both touched inside the same 1-minute bar → assume the STOP hit first.
- Costs per round trip, 1 micro contract: MNQ fee $1.00 + 1 tick slippage on entry and on stop/market exits
  (tick 0.25 = $0.50) ; MGC fee $1.60 + 1 tick slippage each (tick 0.10 = $1.00). Limit-order targets: no slippage.
- Lucid / app constraints: flat by 16:40 ET every day (no overnight holds), max 1 open position per market,
  max 3 trades per day per market (report also uncapped), no hedging, MNQ RTH data quality best 09:30–16:00 but
  trading allowed 03:00–16:40 ET; skip 09:30–09:35 ET for new entries unless the strategy is defined on it
  (report if it is). News blackouts are not modeled — say so.
- Roll days: `.v.0` jumps at contract rolls (no back-adjust). Do not let multi-day indicators cross a roll jump
  silently: detect days whose overnight gap > 1.5% (MNQ) / 1.5% (MGC) and treat prior-day features as unknown there.
- Selection on **2019-05 → 2023-12 (in-sample)** only; then report the chosen variants unchanged on
  **2024-01 → 2026-11 (held-out)**. A strategy "passes" only if held-out expectancy > 0 after costs AND
  held-out profit factor ≥ 1.15 AND ≥ 100 held-out trades. Also show per-year results.

## Report format (results/<your-name>.md, ≤ 120 lines)
For each serious candidate: exact rules (so another engineer can code it), source/citation, then a table:
period | trades | trades/day | win% | avg win R | avg loss R | expectancy R | $/trade net (1 micro) | PF |
max DD (R) | worst losing streak. In-sample and held-out rows + per-year rows for the best one.
Then: verdict (PASS/FAIL per the rule above), risks, and how it would plug into Paytience (signal source,
stop/target logic, R:R, which existing gate/filters it conflicts with). Put code in your work dir; mention
the script name and the exact command to reproduce. Be honest — "nothing passed" is a valid, valuable result.

## Current baseline to beat (app's main strategy, engine, NEUTRAL bias)
MNQ every setup (1y Nov 2025–Oct 2026): 169 trades, 36% win, PF 1.12, +$562 (1 micro).
MNQ with structure-break filter: 40 trades, 45% win, PF 1.72. MGC every setup: 215 trades, 30% win, −$870.
R:R range 1.5–2.5 (config refuses < 1.5). Break-even at 1.8R average ≈ 36% wins.
