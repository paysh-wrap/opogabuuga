# Published accuracy of TradingAgents and Vibe-Trading (session 11)

Sources read (public, as data only, nothing executed):
- https://github.com/TauricResearch/TradingAgents (README, CHANGELOG.md): no results published. README says "Backtest results are not guaranteed to match any published figure."
- https://arxiv.org/abs/2412.20138 (TradingAgents paper, HTML Section 5, Table 1; text read to char 100000 of 117246)
- https://github.com/HKUDS/Vibe-Trading (README): no accuracy/return claims. Only an engine-correction example (AAPL 20/60 SMA excess return 22.5% -> 18.4%, period unstated) and example commands.
- arXiv 2509.11420 (Trading-R1) is linked from the TradingAgents README; not read.

## Numbers
TradingAgents paper: AAPL, GOOGL, AMZN only, 2024-01-01 to 2024-03-29 (3 months, no train/test split).
| Ticker | Cum. return | Annualized | Sharpe | Max DD |
|---|---|---|---|---|
| AAPL | 26.62% | 30.5% | 8.21 | 0.91% |
| GOOGL | 24.36% | 27.58% | 6.39 | 1.69% |
| AMZN | 23.21% | 24.90% | 5.60 | 2.11% |
- Trade count: not stated. Daily direction accuracy / hit rate: NOT reported.
- Authors' own caveats: 3-month window, Sharpe "exceeds our expected empirical range", few pullbacks, 3 sampled stocks. Effectively in-sample, a single bull period.

Vibe-Trading: no published direction accuracy or returns.

## Index futures / NQ / QQQ / SPY
Nothing published for either tool. No direction accuracy exists for index futures.
(Earlier repo note, docs/results/2026-11-09_session9_strategy_research.md: published LLM next-day accuracy about 50-56%; that figure is from other literature, not from these two repos.)

## Implication for sizing and the 70% gate
ai_bias_sizing_study.py does not exist in docs/results/session11/, so it was not run. Existing repo study (tools/noise_biascheck.py, session 9) on the noise strategy:
- 89% of trades already go with the day (393/440, 49% win, +$20,209); against-day trades lost -$8,851.
- As a hard block filter: 55% accuracy -> $7,069 vs $11,358 unfiltered (worse); 75% -> $12,890; break-even about 70%.
- At the realistic 50-56% range, blocking loses money, and a +1/-1 micro size tilt cannot help either, because it adds exposure on a side already mostly chosen by the strategy. A +/-1 micro tilt was not re-simulated here.
- Conclusion: the published material gives no evidence to relax the 70% gate. Keep the AI bias advisory until the calibration ledger (bias/ledger.py) shows at least 70% on at least 30 scored calls.
