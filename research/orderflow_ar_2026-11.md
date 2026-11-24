# Order flow + AR models — research brief (window: ~Oct 25 – Nov 24, 2026)

## Bottom line
1. **Best-supported order-flow signal: Cont–Kukanov–Stoikov OFI**, depth-normalised. It explains a lot of
   *same-bar* price change (linear, slope ∝ 1/depth), but its *forecasting* power decays within about 1–2 horizons.
2. **The AR fit: an ARX/VAR model.** Use next-bar return ~ lagged returns + lagged OFI, with a ridge penalty, refit
   walk-forward. This is the standard econometric vehicle (VAR on E-mini returns/OFI, VAR+NN hybrids).
3. **Main risk: costs.** The newest paper in the window (arXiv 2611.14117, Nov 2026) states plainly that sub-second
   order-flow forecasts are **smaller than spread + fees**. Trade only when the forecast clears cost, use longer bars
   (5s–1m), or use the signal for execution/entry timing rather than as a standalone alpha.

## What's new in the last 30 days
- **arXiv 2611.14117: "Fine-Tuning an Order-Flow Foundation Model for Sub-Second Forecasting"** (BTC/USD, Bitstamp,
  Sept–Oct 2026 data).
  - Level-1 OFI predictive correlation is only 0.07 / 0.04 / 0.00 at 0.2 / 0.5 / 1 s.
  - 10-level OFI scores 0.23 / 0.20 / 0.16.
  - GBM on order-flow features scores 0.39 / 0.37 / 0.31.
  - A 300M-parameter transformer scores 0.44 / 0.45 / 0.39.
  - The edge **disappears by 5–30 s**, and none of these forecasts clears about 2 bps one-way cost.
  - Methodology lessons:
    - Use **true exchange timestamps**. A cumulative-dt timeline drifted 2.25 s and leaked the future.
    - Anchor the target *after* the current event.
    - Use a purged/embargoed holdout.
    - Use Huber loss because returns are heavy-tailed.
  - Caveat: these figures partly come from a summary of the later tables and are not checked against the PDF.
- **June 2026 crypto OFI review (Vafin).** Lagged cross-asset OFI helps forecast returns. Once you use multi-level
  OFI, cross-impact terms add little.
- **Hawkes order-flow models (Jan–May 2026 revisions).** These are theory and diagnostics. None of them shows a signal
  that is profitable after costs.

## Established background
- Cont, Kukanov & Stoikov (J. Fin. Econometrics, 2014): ΔP ≈ β·OFI with β ∝ 1/depth. This is more robust than
  volume-based impact.
- Multi-level OFI (arXiv 2112.13213): deeper levels add explanatory power. The levels are highly collinear (PC1 > 80%
  of variance), so use the first PC or ridge, not plain OLS.
- Takahashi (2025): a structural VAR on E-mini found that returns↔OFI dynamics change sharply around macro news.
  **Gate the strategy off around scheduled releases.**
- Hu & Zhang (2025, CSI300 futures): OFI impact is mean-reverting (OU-like) and regime-dependent, so refit on a
  rolling window.

## Discretionary / retail order flow (cumulative delta, footprint, absorption)
- Recent material is mostly vendor indicators (TradingView, Bookmap), not tested backtests.
- Recurring setups:
  - Cumulative delta / price divergence.
  - **Absorption:** delta makes a new extreme while price fails to.
  - Stacked 3:1 imbalances.
  - VWAP or deviation-band confluence.
- Treat these as features to test, not as proven edges. Absorption maps cleanly onto the ARX framework as
  `sign(OFI) ≠ sign(ret)` with large |OFI|.

## Implementation (in `orderflow/`)
- `ofi.py`: event-level L1 OFI, clock-time bars, depth-normalised `nofi`. Empty bars are dropped, not
  forward-filled.
- `arx.py`:
  - Walk-forward ridge ARX(p return lags, q OFI lags).
  - Backtest that trades only when |forecast| > k·cost, and charges cost on turnover.
- `tests/`: hand-checked OFI cases, alignment, signal recovery, null-signal-loses-after-costs, no-lookahead.

### Recommended starting config for CME index futures (ES/MES/NQ)
- Data: Databento `GLBX.MDP3`, schema `mbp-1` (or `mbp-10` for multi-level). RTH only.
- Bars: test 1s, 5s, 15s and 1m. Expect the information coefficient (IC) to decline at longer horizons while the
  forecast size per trade grows. Pick the bar size where forecast size beats about 1 tick round trip.
- p = 3, q = 3. Window of about 1 trading day of bars, refit about every 30 minutes. Ridge 1e-3.
- Filters:
  - Flat around 8:30 / 10:00 / 14:00 ET releases.
  - Flat in the first and last 5 minutes.
- Additional features to add one at a time, each checked out-of-sample:
  1. First PC of 10-level OFI.
  2. Trade-sign imbalance (aggressor flow).
  3. Absorption flag.
  4. Lagged OFI from a correlated contract (ES↔NQ cross-impact).

## Improving the existing "main" strategy
That strategy was not available in this session: the repo was empty, and attaching `paysh-wrap/beast` was blocked.
Generic upgrades that the literature supports:
1. Use OFI as an **entry-timing filter** on existing signals: enter only when depth-normalised OFI agrees. This is
   cheaper than a standalone OFI strategy.
2. Add a **cost gate**: skip trades whose expected move is under about 1.5× the round-trip cost.
3. Add a **regime gate**: no trading around news, and refit parameters on a rolling basis.
4. Tighten **validation**: walk-forward, purged/embargoed splits, paired-bootstrap confidence intervals vs the current
   version, and exchange timestamps only.

## Sources
- https://arxiv.org/html/2611.14117
- https://arxiv.org/abs/1011.6402
- https://arxiv.org/html/2112.13213v1
- https://arxiv.org/html/2411.08382v1
- https://arxiv.org/html/2508.06788v2
- https://arxiv.org/abs/2505.17388
- https://arxiv.org/html/2408.03594v1
- https://arxiv.org/abs/2601.23172v2
- https://www.researchgate.net/publication/408460451
- https://bookmap.com/blog/how-order-flow-imbalance-can-boost-your-trading-success
- https://www.tradingview.com/script/kyOZgm39-Order-Flow-Delta-Tracker
