# Micro Gold (MGC) — research notes (agent, 2026-11-05; sources in the session log)
- Specs: 10 oz, tick $0.10 = $1.00; Sun 18:00 → Fri 17:00 ET, daily break 17:00–18:00. Months Feb/Apr/Jun/Aug/Oct/Dec.
  Front month now ≈ Dec 2026 (MGCZ6), roll 1–2 days before first notice (late Nov). MGC1! roll method unclear →
  backtest on real contracts or back-adjusted data; skip roll days.
- Lucid: MGC approved, $0.80/side ($1.60 round trip), max micros per plan; Flex funded scaling (10 micros = 1 mini).
- Best-supported windows: London open (~03:00 ET) through the London–NY overlap (08:20 COMEX open, 08:30 data) to
  ~11:00 ET; LBMA fixes ~05:30 and ~10:00 ET. Asia ≈ 42% of MGC volume — test separately.
- News: CPI, NFP, FOMC biggest; volatility elevated ~15 min after → no new gold entries for 15 min after a release.
- Costs: 1.6 ticks/round trip → stops < ~16 ticks are rejected (fees would dominate).
- Macro: real-yield and DXY correlations are unstable (−0.96 … 0) → no hard-coded macro filter. GLD = daily proxy only.
- No published evidence for sweep/CISD edge in gold → must be proven by our own out-of-sample MGC backtest.
- Applied in config: MGC windows [03:00–11:00, 13:30–15:30], min_stop_ticks 16, news_after_min 15.
- Open: CrossTrade order symbol for MGC must be the actual contract (e.g. MGCZ6) — VERIFY before live.
