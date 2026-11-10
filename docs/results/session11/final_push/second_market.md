# Second market for the MAIN strategy (NOISE + PM fade): MES / MYM / M2K — verdict: NONE qualifies, stay all-MNQ
Date 2026-11-10. Scripts (this folder): `dl_second.py` (download), `second_streams.py` (per-market trades), `mix_engine.py` (account engine, `verify` / `run`),
`second_tables.py`. Outputs: `second_streams.json`, `streams/second_<mkt>.csv`, `second_mix.json`.

## Data and method
- Databento GLBX.MDP3 ohlcv-1m, MES.v.0 / MYM.v.0 / M2K.v.0, 2021-10-01..2026-10-31, per quarter, cached in `backend/app/backtest/data/raw/<mkt>_v0_*.csv` + `<mkt>_5y.csv`
  (same call as `rebuild_main_csv.py`). 1,243–1,245 complete RTH days per market (MNQ 1,245).
- Same code as the MNQ generator (`rebuild_main_csv.noise_t` / `pm_fade`), nothing tuned: 14-day noise band, hourly checks, max 3 NOISE trades, band/VWAP exits,
  flat 16:00, fade = VWAP ±2 sd -> VWAP on days without a NOISE trade. Fee $1 round trip, 1 tick slippage per side.
- Stop = same % of price as MNQ's 124 pt: MES 35.5 pt ($181 per micro), MYM 264 pt ($134), M2K 14.1 pt ($72). Point values MES $5, MYM $0.50, M2K $5.
- Check: MNQ through this path = 1,291 trades, 50.0% win, PF 1.33, +$25,345 (matches the main CSV).

## Per market, 1 micro, 5 years
| market | trades | win % | PF | $ per micro | max DD $ | 2021-23 $ (PF) | 2024-26 $ (PF) | NOISE $ / fade $ | daily P&L corr with MNQ |
|---|---|---|---|---|---|---|---|---|---|
| MNQ (ref) | 1,291 | 50.0 | 1.33 | +25,345 | -2,591 | +9,363 (1.30) | +15,982 (1.34) | +18,930 / +6,416 | 1.00 |
| MES | 1,321 | 48.8 | 1.02 | +1,179 | -3,873 | +2,724 (1.13) | -1,545 (0.94) | -1,008 / +2,187 | 0.55 (same sign 70% of shared days) |
| MYM | 1,317 | 43.8 | 0.89 | -4,232 | -4,785 | -1,971 (0.89) | -2,261 (0.89) | -6,424 / +2,192 | 0.20 (55%) |
| M2K | 1,292 | 43.8 | 0.97 | -926 | -2,254 | +375 (1.03) | -1,301 (0.92) | -1,854 / +928 | 0.25 (59%) |

Per year $: MES 2022 +1,245, 2023 +1,429, 2024 +958, 2025 -849, 2026 -1,654. MYM negative in 5 of 6 years. M2K 2024 -915, 2025 +743, 2026 -1,129.
Test 1 (profitable on BOTH halves): MES fail (2024-26 loses), MYM fail (both lose), M2K fail (2024-26 loses). NOISE itself loses money on all three; only the small
PM fade part is positive (PF 1.13–1.28), and it is far smaller than on MNQ.

## Mixed account vs all-MNQ (live rules)
Engine `mix_engine.py` = multi-instrument port of `pm_fade_d57_study.py`: D57 stop-shrink 0.6 for NOISE, fade as coded ($500 pause + worst-case check), kill $50,
soft DLL, D68 cadence (50K every 10 days, 100K/150K every 5), D66 eval rows, 260-day funded horizon, starts every 2nd day. `verify`: all-MNQ reproduces the
reference engine exactly (50K funded $2,534 / 150K $4,924; eval 50K 53.0%, 100K 61.9%).
Mixing rules: MNQ primary; second market never opens against an open MNQ trade or a conflicting MNQ signal; if MNQ enters against an open second-market trade
that trade is flattened; open planned risk is deducted from the room before a new trade is sized. Braked size = MNQ only.
Size column = funded size. Eval uses the same replacement of ONE MNQ (150K eval = 3 MNQ + n other; 100K eval grows 2->4 with one MNQ replaced).
Equal-dollar-risk replacement of 1 MNQ ($250) = 1 MES ($181), 2 MYM ($268), 3 M2K ($216); the "+1 M2K / +1 MYM" rows carry LESS total risk than all-MNQ.
Funded $ = average paid out over 260 trading days (about 1 year); H1 = starts 2021-23, H2 = starts 2024-26. Bust was 0.0% in every row (funded and eval).

| plan | size | funded $/yr all (H1 / H2) | bust | frozen | eval pass all (H1 / H2) | eval bust | eval frozen | beats MNQ both halves? |
|---|---|---|---|---|---|---|---|---|
| 50K | 2 MNQ (today) | 2,534 (2,915 / 2,084) | 0.0% | 58% | 53.0% (59.4% / 47.1%) | 0.0% | 37% | - |
| 50K | 1 MNQ + 1 M2K | 1,586 (1,841 / 1,286) | 0.0% | 22% | 46.4% (46.6% / 46.1%) | 0.0% | 16% | no (income H1, income H2, pass H1, pass H2 worse) |
| 50K | 1 MNQ + 3 M2K | 1,112 (1,644 / 484) | 0.0% | 45% | 42.0% (47.7% / 36.8%) | 0.0% | 28% | no (income H1, income H2, pass H1, pass H2 worse) |
| 50K | 1 MNQ + 1 MES | 1,949 (2,228 / 1,621) | 0.0% | 55% | 43.8% (47.7% / 40.3%) | 0.0% | 25% | no (income H1, income H2, pass H1, pass H2 worse) |
| 50K | 1 MNQ + 1 MYM | 1,531 (1,750 / 1,272) | 0.0% | 39% | 45.7% (43.5% / 47.7%) | 0.0% | 21% | no (income H1, income H2, pass H1 worse) |
| 50K | 1 MNQ + 2 MYM | 1,336 (1,534 / 1,101) | 0.0% | 53% | 43.5% (40.3% / 46.5%) | 0.0% | 33% | no (income H1, income H2, pass H1, pass H2 worse) |
| 100K | 2 MNQ (today) | 3,674 (4,168 / 3,093) | 0.0% | 38% | 61.9% (67.8% / 55.1%) | 0.0% | 36% | - |
| 100K | 1 MNQ + 1 M2K | 1,137 (1,167 / 1,102) | 0.0% | 0% | 52.1% (59.0% / 44.1%) | 0.0% | 24% | no (income H1, income H2, pass H1, pass H2 worse) |
| 100K | 1 MNQ + 3 M2K | 960 (1,433 / 403) | 0.0% | 17% | 43.6% (53.7% / 31.8%) | 0.0% | 27% | no (income H1, income H2, pass H1, pass H2 worse) |
| 100K | 1 MNQ + 1 MES | 1,889 (2,437 / 1,242) | 0.0% | 27% | 57.0% (72.4% / 39.2%) | 0.0% | 28% | no (income H1, income H2, pass H2 worse) |
| 100K | 1 MNQ + 1 MYM | 1,063 (1,233 / 863) | 0.0% | 14% | 48.1% (50.2% / 45.7%) | 0.0% | 24% | no (income H1, income H2, pass H1, pass H2 worse) |
| 100K | 1 MNQ + 2 MYM | 1,147 (1,442 / 800) | 0.0% | 36% | 45.8% (50.5% / 40.4%) | 0.0% | 40% | no (income H1, income H2, pass H1, pass H2 worse) |
| 150K | 3 MNQ (today) | 4,924 (5,719 / 3,987) | 0.0% | 31% | 57.4% (62.2% / 51.8%) | 0.0% | 40% | - |
| 150K | 2 MNQ + 1 M2K | 2,891 (3,464 / 2,216) | 0.0% | 22% | 66.5% (74.9% / 56.7%) | 0.0% | 27% | no (income H1, income H2 worse) |
| 150K | 2 MNQ + 2 M2K | 2,789 (3,391 / 2,078) | 0.0% | 18% | 61.9% (68.2% / 54.7%) | 0.0% | 35% | no (income H1, income H2 worse) |
| 150K | 2 MNQ + 3 M2K | 2,669 (3,326 / 1,894) | 0.0% | 16% | 59.5% (62.5% / 55.9%) | 0.0% | 36% | no (income H1, income H2 worse) |
| 150K | 2 MNQ + 1 MES | 3,689 (4,596 / 2,619) | 0.0% | 32% | 60.4% (68.2% / 51.4%) | 0.0% | 37% | no (income H1, income H2, pass H2 worse) |
| 150K | 2 MNQ + 2 MES | 3,748 (4,620 / 2,719) | 0.0% | 37% | 58.5% (65.7% / 50.2%) | 0.0% | 40% | no (income H1, income H2, pass H2 worse) |
| 150K | 2 MNQ + 1 MYM | 2,926 (3,464 / 2,292) | 0.0% | 24% | 64.4% (72.4% / 55.1%) | 0.0% | 29% | no (income H1, income H2 worse) |
| 150K | 2 MNQ + 2 MYM | 2,764 (3,227 / 2,218) | 0.0% | 34% | 58.3% (63.3% / 52.7%) | 0.0% | 38% | no (income H1, income H2 worse) |

Test 2 (mix beats all-MNQ on both halves, bust not higher): no row passes. Funded income falls 24–74% in every mix, on both halves.
Eval pass rate falls on 50K and 100K. Only the 150K eval pass rate rises with a small second leg (3 MNQ + 1 M2K 66.5% vs 57.4%, both halves) — that is a
size effect (4 -> 3 MNQ plus a $72 leg = less risk, fewer freezes), not a second-market edge; the same accounts earn 41% less when funded.
Possible follow-up (not tested here, needs its own study): 150K eval with 3 MNQ instead of 4.

## Verdict
No second market. MES, MYM and M2K all fail test 1 (not profitable on both halves) and test 2 (every mix earns less than all-MNQ). Lower correlation
(MYM 0.20, M2K 0.25) does not help because the added stream has no edge: diversifying into a PF < 1 stream only dilutes MNQ. Keep the full size on MNQ.
Limits: the mix engine deducts open planned risk and settles trades at exit time (no intrabar mark-to-market of two open positions); fade eligibility uses
"no NOISE signal later that day" (identical results to the reference for all-MNQ). No parameter was varied for any market.
