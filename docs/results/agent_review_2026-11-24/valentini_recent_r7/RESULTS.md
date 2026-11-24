# Valentini-proxy, recent regime only (r7, research only, 2026-11-24)

No app code changed, nothing pushed. Scripts: `run7.py` (proxy from news_and_ideas_r5 `run_ideas.py`, same definition: first-30-min efficiency >= thr, first VWAP pullback 10:00-11:30 in trend direction, 0.25 pt slippage, $2 RT, 1 micro), `h7.py` (refine_round3 harness plus a third leg, 1 micro, shrink-only), `run7.log`. Data /home/user/days.pkl.

**Variants: 6 (counted)**: thr {0.35, 0.5} x stop/target {40/60, 30/45, 60/90}. Chosen on 2024-01..2025-06 only (best PF, n>=40): thr 0.5, 40/60 (PF 1.33 on 134 trades; the others 1.12-1.26). Frozen, then judged on 2025-07..2026-10 unchanged.

| part | n | win % | PF | net | max DD |
|---|---|---|---|---|---|
| pre-2024 (transparency) | 206 | 41.7 | 1.03 | $255 | $1,120 |
| recent pick 2024-01..2025-06 | 134 | 48.5 | 1.33 | $1,873 | $548 |
| **recent judge 2025-07..2026-10** | **134** | 46.3 | **1.23** | **$1,343** | $794 |
| full 2024-26 | 268 | 47.4 | 1.28 | $3,215 | $1,096 |

Per half-year (PF / net): 2021H2 0.73/-247, 2022H1 0.89/-244, 2022H2 0.98/-44, 2023H1 0.97/-64, 2023H2 1.40/+855, 2024H1 1.05/+99, 2024H2 1.69/+1300, 2025H1 1.25/+474, **2025H2 0.84/-461**, 2026H1 1.78/+1346, 2026H2 (to Oct) 1.35/+458.

Judge random-direction control (1000 draws, same entries): PF p95 1.17, net p95 $1,012. Real PF 1.23 / $1,343 beats it (just). Trade count 134 >= 40.

Correlation of daily P&L with the verified NOISE+CANDACE stream (1 micro each): 0.09 (full), 0.09 (2024-26), 0.07 (judge); 0.12-0.17 on days the proxy traded. Nearly uncorrelated.

## Fast-pass eval sim (refine_round3 built config, reproduced 66.3%/61d at 50K and 74.4%/80d at 150K; proxy added as third leg, 1 micro, shrink-only)

Pass % / median days among passers / stuck+bust %, by start window:

| | all starts | starts 2024+ | starts 2025-07+ | static 5-yr profit |
|---|---|---|---|---|
| 50K base | 66.3 / 61 / 26.2 | 56.5 / 64.5 / 30.2 | 36.2 / 57 / 35.6 | $39,080 |
| 50K +proxy | 61.4 / 57 / 32.6 | 53.9 / 60 / 35.5 | 26.9 / 44.5 / 50.6 | $38,368 |
| 150K base | 74.4 / 80 / 4.4 | 57.3 / 70 / 5.0 | 35.3 / 66.5 / 0.0 | $100,575 |
| 150K +proxy | 71.0 / 76 / 17.2 | 48.5 / 62 / 30.5 | 33.5 / 80.5 / 22.2 | $98,122 |

Adding the leg lowers pass % in every window, raises stuck+bust sharply, and trims profit. The speed gain on all starts is only the survivor mix changing, not a real speedup. The proxy leg is another trade that can hit the account's room with no sizing control on a thin cushion.

## Verdict: REJECT as a fast-pass leg (INCONCLUSIVE as a standalone edge)

Checklist: recent-judge PF 1.23 > 1.2 yes (barely); beats random p95 yes (barely); net positive in both recent halves: yes for 2024-01..2025-06 and 2025-07..2026-10 as defined, but **no by calendar half-year (2025H2 is -$461)**; sim improves pass % and speed without cutting profit: **NO** (pass % down in all six cells, profit down). One failed criterion is enough.

Plain caveats: a recent-only result is weaker evidence than a result that holds across regimes; it is a regime bet. The proxy was 1.03 PF before 2024, so the edge could be a post-2024 volatility/trend regime that ends. Parameters chosen on 18 months and judged on 16 months, with 6 variants; the judge margin over the random control (PF 1.23 vs 1.17) is thin, and the whole judge net ($1,343 over 134 trades, about $10/trade) is about $1 of margin per trade over the $2 cost scale. Not order-flow data: this is not Valentini's CVD method, only a bar proxy. Nothing adopted; user decides.
