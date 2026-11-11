# Session 18 - Order-flow intraday study for MNQ (BLOCKED, no data)

Status 2026-11-11: **not run. No data could be downloaded.**

## What happened
- `metadata.get_cost` on hist.databento.com (GLBX.MDP3, MNQ.v.0, `trades` and `tbbo`, 2023-01-03..2026-11-07) returned
  **HTTP 403 `auth_account_locked`: "Your account has been locked for security reasons."** This is the Databento account behind the proxy.
  Nothing was downloaded and nothing was spent ($0).
- No local tick, trades, tbbo or MBO data exists in the repo or the container. The repo has only 1-minute OHLCV bars,
  which carry no aggressor side, so footprint, delta, imbalance and sweep signals can't be rebuilt from them.
  Using a proxy such as candle-body "delta" would not test real order flow, so I didn't.
- No numbers are reported, which keeps the rule that nothing is made up.

## Needed to unblock
The user unlocks the Databento account (log in or contact Databento support). Then re-run the cost check. Expected size:
`trades` RTH-only for 2023-2026 MNQ is the cheapest schema with aggressor side. Check the price before downloading and keep it under about $30;
if it costs more, sample days. MBO for iceberg detection is very likely too expensive, so skip it.

## Planned protocol (ready to run once data is available)
- Bars: 1m/5m footprint from `trades`: per-price bid/ask volume, bar delta, cumulative session delta, POC.
- Signals: (1) absorption at session low/high or prior-day H/L; (2) cumulative-delta divergence at a new N-bar or session extreme -> fade;
  (3) 3+ stacked 3:1 imbalances -> follow; (4) POC as magnet/target; (5) sweep bar through 3+ levels with large aggressive volume -> follow.
- Trade: 1 micro, stop 1 tick beyond the defended level, 2R target, flat 16:00 ET, fees and slippage as in session 17
  (next-bar open +/-1 tick, stop checked first).
- Pick on 2023, judge only on 2024-2026. Compare with the NOISE baseline (session 17 preset C HO: 427 trades, 52.2% win,
  $27.19/trade, PF 1.43, max DD $2,028, Pro 25K PASS 33% / BUST 64%) and with random entries using the same exits.
  Use the session-17 `sim.py` for the Pro 25K eval.
- Note: the user's YouTube videos could not be watched. The study uses only general published order-flow concepts.

## Verdict
None yet. No order-flow edge has been measured. Nothing should be built or switched on from this study.
