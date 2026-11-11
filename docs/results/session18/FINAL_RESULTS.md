# Session 18 — final results of all new strategies (held-out / last-4-months judge windows; small samples, UNVERIFIED)
Baseline to beat: NOISE preset C (MNQ): 51% win, PF 1.43-1.76, +$2.9k on the 4-month judge window, eval PASS 60-67% / BUST 33-39%.
No new strategy beat NOISE. None is built as a live button except Order Flow (paper-only, default OFF, UNVERIFIED).

| Strategy | Win % | Avg win/avg loss | PF | Net (judge) | Eval PASS / BUST | Verdict |
|---|---|---|---|---|---|---|
| NOISE preset C (baseline) | 51-52 | 1.7 | 1.4-1.8 | +$2.9k..+11.6k | 60-67 / 33-39 | main strategy |
| ICT Silver Bullet (sweep+MSS+FVG), 2024-26 | 44 (AM+PM) | - | 1.23 | +$2.1k | 59 / 36 | tiny edge, ~0.3 trades/day; London window loses |
| SMC: SuperTrend 5m | 44 | - | 0.98 | -$1.0k | 37 / 64 | no edge (= random) |
| SMC: sweep+FVG | 35 | - | 0.98 | -$1.2k | 17 / 72 | no edge |
| SMC combined (SuperTrend filter) | 43 | - | 1.03 | +$0.7k | 10 / 35 | no edge |
| Triple RSI (MNQ 5m) | 57 | 0.6 | 0.76 | -$4.1k | 0 / 100 | wins often, loses overall |
| Triple RSI (MGC 15m) | 67 | - | 1.02 | +$0.2k | 22 / 67 | break-even |
| DMI (MNQ 15m) | 39 | - | 0.85 | -$1.8k | 4 / 96 | loses |
| SuperTrend 15m (MNQ) | 28 | - | 0.52 | -$4.7k | 4 / 96 | loses |
| Triple RSI + SuperTrend15 filter, 1.5R | 50 | - | 1.28 | +$2.4k | 56 / 26 | only weak lead (MNQ) — retest multi-year |
| Volume profile (prior-day VA rules) | 27-53 | - | 0.79-1.4 | tiny | too few trades | no edge; 80% rule measured 42% (MNQ) / 26% (MGC), not 80% |
| Order flow (generic, estimated bars) | 31.5 | - | 1.00 | -$24 | 31 / 69 | no edge on estimated data |
| Order flow teacher CZT (estimated bars) | 35 | - | 0.98 | -$38 | 8 / 75 | no edge on estimated data (needs real tick data) |
| Combined ICT+SMC+RSI+DMI (first signal wins, 2 micros 25K/50K) | 40 | 1.72 | 1.16 | +$3.0k | 46 / 54 | ~70% of profit = Triple RSI on MGC; MNQ ~break-even |
| Split NOISE + AI Duo 50/50 | see split_combo | | | | | beats NOISE alone only at AI accuracy >= 60-70% |

Order Flow vs Volume Profile: neither shows an edge on 1 year of cached 1-minute data. Order flow was only tested with ESTIMATED buy/sell volume
(Databento locked, no tick data); volume profile's article claims (55-65% win, 80% rule) were NOT reproduced. Re-test both on real tick data /
multi-year data once Databento is unlocked. Details: docs/results/session18/*/RESULTS.md.
