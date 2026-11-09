# NOISE on a second market (agentG) - verdict: NO market passes
Files: noise_gen.py (generalized strategy), verify.py, dl.sh/retry.sh/assemble.py (data), study.py, corr.py; outputs study_out.txt, study_ffill.txt, corr_out.txt, trades_*.csv.
Verification: noise_gen on MNQ (stop off) = noise_area.py exactly (808 trades, identical pnl, $18,691). MNQ with $250 fixed stop: n=820 PF 1.36.
Fixed $250 stop: points=(250-fee-2*tick$)/pv. Fee $1 RT, 1 tick slippage each side. Roll guard: MCL 5%, M6E 1.5%, 10Y 3% (fixed in advance).
Spend (metadata.get_cost estimates): MCL 6.59 + M6E 8.20 + 10Y 1.76 = ~$16.55. M2K ($9.14) and MYM ($9.39) skipped: would exceed $25 (MYM is also an index twin of MNQ). Some chunks failed ("upstream request failed") and were re-downloaded.
Data notes: MCL starts 2021-07 (micro launch), so in-sample is only 2021-07..2023-12. 10Y: ~50% of minutes have no trade (median 193 of 400 bars/day; only 20 days >350 bars) -> not testable honestly (0 complete days under the strict filter). M6E/MCL micro bars are also gappy; "strict" = require >=97% of bars with first bar present (M6E 643 days, MCL 1283 days); "ffill" (primary) = forward-fill empty minutes if >=50% traded (M6E 1913 days, MCL 1357 days).

## Results (ffill variant; strict variant is similar - MCL IN 376 / PF .92, HELD 446 / PF .76; M6E IN 263 / PF .77, HELD 184 / PF .77)
| market | period | trades | win % | $/trade | PF | max DD $ | total $ |
|---|---|---|---|---|---|---|---|
| MCL | IN 2021-07..2023 | 392 | 39.3 | -0.90 | 0.97 | -1,663 | -354 |
| MCL | HELD 2024-26 | 478 | 37.2 | -7.33 | 0.71 | -3,731 | -3,502 |
| M6E | IN 2019-05..2023 | 806 | 35.9 | -2.59 | 0.78 | -2,476 | -2,090 |
| M6E | HELD 2024-26 | 517 | 30.2 | -5.23 | 0.54 | -2,687 | -2,702 |
| 10Y | - | not testable (illiquid 1-min bars) | | | | | |
| MNQ ref (noise_gen, $250 stop) | HELD 2024-26 | 446 | 44.2 | +22.84 | 1.31 | -2,228 | +10,188 |

Per-year totals $ - MCL: 2021 -358, 2022 +344, 2023 -340, 2024 -315, 2025 -2,159, 2026 -1,028. M6E: 2019 -499, 2020 -988, 2021 -347, 2022 -521, 2023 +266, 2024 -1,005, 2025 -977, 2026 -720.

## Pass test (held-out PF>=1.15, expectancy>0, >=100 trades, in-sample PF>=1.0)
MCL FAIL (HELD PF 0.71, IS PF 0.97). M6E FAIL (HELD PF 0.54, IS 0.78). 10Y untestable. Nothing tuned on held-out; no parameters were varied.
Why: the noise-area edge needs trending, volume-rich index futures; costs are a large share of a micro FX/oil trade (M6E: $3.50 RT cost vs ~tick-size moves), and the 2025 oil/EUR chop hurt most.

## Correlation with MNQ MAIN (informational only, markets failed)
Daily P&L corr: MCL +0.01, M6E -0.00 (uncorrelated, but both lose money, so no diversification benefit).
Combined-portfolio Pro 150K projection NOT run: no passing market (a losing leg only adds drawdown).
