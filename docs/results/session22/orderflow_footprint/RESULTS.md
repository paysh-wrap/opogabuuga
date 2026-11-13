# Order flow (AR Model + Casper) with a simulated footprint, 5 years MNQ / MES (session 22, research only)

**The footprint is an ESTIMATE, not real aggressor flow.** Volume is recovered from the stored VWAP (session 21 method, imputed share MNQ 0.06%, MES 0.33%). Each 1-minute bar's volume is spread over its price rows (row = 0.5 pt MNQ, 0.25 pt MES), buy share = close location, tick rule if high == low (the app's `footprint.py` method; my vectorised copy matches the app code on 200/200 sampled 5m candles for POC and 200/200 for delta). The gates (`check_ar`, `check_casper`), the plan (`build_plan`) and the trail (`trail_stop`) are the app's own functions. Every table below is path filter OFF (no Asia data) unless it says otherwise.

## 1. Answer

**No edge.** The shipped config as-is (path filter ON, location ON) makes **0 trades** on this data: the Asia range does not exist in RTH-only bars, so every candidate that survives the location gate is skipped with `OF_PATH_UNKNOWN` (32 reach that layer, 5837 die earlier at location). With the path filter OFF the 16-row grid has **no eligible row** (IS n >= 150 and PF > 1.05): the two location-ON rows that look best on IS have only 6 to 11 trades in 4 years (the shipped location gate fires about once per 150 sessions), and every row with enough trades has IS PF between 0.85 and 1.02. The literal pre-registered pick (best score among all rows) is a 6-trade IS row, judged on 1 J trade, which means nothing. I therefore also judged the best row with IS n >= 150 (k 1.5, exit AR trail (BE+fee after +1R, then behind each closed 5m candle), location OFF, Casper ON, path OFF): IS 479 trades PF 1.02 (+0.3 $/trade), J 62 trades PF 0.69 (-6.7 $/trade, net -414); it beat 1/30 random-side seeds on J (needs 27); the same config on MES loses in both windows. On the 9 plans it passes 0% on J and busts 38% on Pro 25K, against NOISE 55 / 45. **Verdict: not an edge** (no eligible pick; J PF < 1.15; random-side 1/30; MES negative). Small samples cut both ways: this does not prove real aggressor-flow order flow has no edge, only that this estimated, bar-derived version of it has none here.

Deviation to flag: the rule "if none eligible, pick the best score anyway" selects the 6-trade row, so a second pick (best score with IS n >= 150) was added after the IS table and before any J number was computed. Both are judged below; neither passes.

## 2. The pick

Columns: trades / win / PF / $ per trade / net $ / max closed-trade drawdown $ (1 micro; MNQ $2.00/pt, MES $5.00/pt, $1.00 round-trip fee, 1 tick slippage on entry and on stop / flat exits; targets need a 1-tick trade-through; stop checked first inside a 1m bar). IS = 2021-10-01..2025-11-05, J = 2025-11-06..2026-10-30.

**Pick used for the verdict: best row with IS n >= 150 (no row was eligible)**: k 1.5, exit AR trail (BE+fee after +1R, then behind each closed 5m candle), location OFF, Casper ON, path OFF.

- MNQ IS: 479 / 37.4% / 1.02 / +0.3 / +157 / 1,581
- MNQ J: 62 / 33.9% / 0.69 / -6.7 / -414 / 497
- MES IS (same config, no re-pick): 823 / 41.1% / 0.87 / -2.2 / -1,798 / 2,806
- MES J: 186 / 34.4% / 0.66 / -7.3 / -1,366 / 1,612

Per-year MNQ (all trades):

| Year | trades | win | PF | $/trade | net |
|---|---|---|---|---|---|
| 2021 | 14 | 50.0% | 1.39 | +5.1 | +71 |
| 2022 | 122 | 37.7% | 0.97 | -0.5 | -58 |
| 2023 | 131 | 37.4% | 0.87 | -2.3 | -306 |
| 2024 | 136 | 34.6% | 0.87 | -2.5 | -338 |
| 2025 | 82 | 36.6% | 1.46 | +8.2 | +669 |
| 2026 | 56 | 37.5% | 0.76 | -5.3 | -296 |

**Literal pre-registered pick (best score, tiny sample)**: k 1.5, exit fixed 2R, location ON, Casper ON, path OFF.

- MNQ IS: 6 / 50.0% / 1.34 / +7.0 / +42 / 45
- MNQ J: 1 / 0.0% / 0.00 / -31.0 / -31 / 31
- MES IS (same config, no re-pick): 4 / 0.0% / 0.00 / -34.1 / -136 / 136
- MES J: 1 / 0.0% / 0.00 / -38.5 / -38 / 38

NOISE baseline (1 micro): IS 536 / 49.6% / 1.50 / +27.2 / +14,556 / 2,096; J 118 / 59.3% / 1.58 / +40.1 / +4,737 / 1,024

## 3. Full grid (path filter OFF (no Asia data); J columns shown for completeness, NOT used for the pick)

| k | exit | location | Casper | IS n | IS PF | IS $/tr | J n | J PF | J $/tr | eligible | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.0 | 2R | ON | ON | 7 | 1.24 | +4.5 | 1 | 0.00 | -31.0 | no | not picked |
| 1.0 | 2R | ON | OFF | 11 | 1.13 | +2.5 | 2 | 0.00 | -22.8 | no | not picked |
| 1.0 | 2R | OFF | ON | 949 | 0.92 | -2.0 | 162 | 0.85 | -4.0 | no | not picked |
| 1.0 | 2R | OFF | OFF | 1640 | 0.89 | -2.5 | 297 | 0.83 | -4.2 | no | not picked |
| 1.0 | trail5 | ON | ON | 7 | 0.84 | -2.0 | 1 | 0.00 | -31.0 | no | not picked |
| 1.0 | trail5 | ON | OFF | 11 | 1.23 | +2.5 | 2 | 0.00 | -22.8 | no | not picked |
| 1.0 | trail5 | OFF | ON | 954 | 0.91 | -1.6 | 163 | 0.87 | -2.8 | no | not picked |
| 1.0 | trail5 | OFF | OFF | 1648 | 0.86 | -2.5 | 301 | 0.86 | -3.0 | no | not picked |
| 1.5 | 2R | ON | ON | 6 | 1.34 | +7.0 | 1 | 0.00 | -31.0 | no | literal pick |
| 1.5 | 2R | ON | OFF | 7 | 1.01 | +0.1 | 2 | 0.00 | -22.8 | no | not picked |
| 1.5 | 2R | OFF | ON | 479 | 0.92 | -1.9 | 61 | 0.87 | -3.4 | no | not picked |
| 1.5 | 2R | OFF | OFF | 845 | 0.85 | -3.8 | 117 | 0.96 | -1.0 | no | not picked |
| 1.5 | trail5 | ON | ON | 6 | 0.96 | -0.6 | 1 | 0.00 | -31.0 | no | not picked |
| 1.5 | trail5 | ON | OFF | 7 | 1.15 | +1.6 | 2 | 0.00 | -22.8 | no | not picked |
| 1.5 | trail5 | OFF | ON | 479 | 1.02 | +0.3 | 62 | 0.69 | -6.7 | no | n>=150 pick |
| 1.5 | trail5 | OFF | OFF | 854 | 0.94 | -1.1 | 119 | 1.21 | +4.0 | no | not picked |

Diagnostic only (not part of the pre-registered grid, never eligible): location measured at the absorption extreme (touch of the 0.705-0.886 zone and value side at the candle low/high) instead of the candle close. Still a handful of trades; IS PFs look better only because n is 7 to 27.

| k | exit | Casper | IS n | IS PF | IS $/tr | J n | J PF |
|---|---|---|---|---|---|---|---|
| 1.0 | 2R | ON | 15 | 1.32 | +6.4 | 1 | 0.00 |
| 1.0 | 2R | OFF | 27 | 1.42 | +7.9 | 1 | 0.00 |
| 1.0 | trail5 | ON | 15 | 1.71 | +10.3 | 1 | 0.00 |
| 1.0 | trail5 | OFF | 26 | 1.49 | +6.4 | 1 | 0.00 |
| 1.5 | 2R | ON | 7 | 1.43 | +10.5 | 1 | 0.00 |
| 1.5 | 2R | OFF | 14 | 1.00 | +0.1 | 1 | 0.00 |
| 1.5 | trail5 | ON | 7 | 2.54 | +24.5 | 1 | 0.00 |
| 1.5 | trail5 | OFF | 14 | 1.63 | +9.5 | 1 | 0.00 |

Shipped config as-is (path ON, location ON, Casper ON, k 1.0, 2R): **0 trades**. Gate counts at the first entry bar: OF_LOCATION 5837, OF_PATH_UNKNOWN 32.

## 4. Random-side benchmark (same entries / stops / R, random direction, 30 seeds)

- n>=150 pick: J pick -6.7 $/trade vs random mean +0.7, beat 1/30 (needs 27). IS pick +0.3 vs random mean -3.9, beat 30/30.
- literal pick: J pick -31.0 $/trade vs random mean -31.0, beat 0/30 (needs 27). IS pick +7.0 vs random mean -1.3, beat 18/30.

The IS random-side mean is about -4 $/trade for the n>=150 pick, so the direction logic adds a few dollars per trade in sample, but that is not enough to turn a positive net and it vanishes on J.

## 5. Nine-plan eval vs NOISE (session-21 bootstrap: 10-day blocks, 600 paths, 400 sessions, plan size_table micros, session-15 engine with the intraday MAE floor)

pass% / bust% (rest = still open after 400 sessions). Plans read from the session-21 commit `87ef163` so the NOISE column reproduces session 21 exactly (NOISE matches session 21: True; pro_25k NOISE J 55 / 45). The Pro YAMLs were changed afterwards (D138: eval consistency 40%, DLL 600); that only moves Pro numbers a point or two and is shown in the second table.

| Plan | micros | pick IS | pick J | NOISE IS | NOISE J |
|---|---|---|---|---|---|
| pro_25k | 1 | 8 / 22 | 0 / 38 | 70 / 30 | 55 / 45 |
| pro_50k | 2 | 3 / 22 | 0 / 38 | 68 / 32 | 54 / 46 |
| pro_100k | 2 | 0 / 2 | 0 / 9 | 80 / 17 | 70 / 30 |
| pro_150k | 3 | 0 / 2 | 0 / 9 | 80 / 17 | 70 / 30 |
| flex_25k | 1 | 8 / 22 | 0 / 38 | 68 / 32 | 52 / 48 |
| flex_50k | 2 | 3 / 22 | 0 / 38 | 67 / 33 | 50 / 50 |
| flex_100k | 2 | 0 / 2 | 0 / 9 | 80 / 17 | 69 / 30 |
| flex_150k | 3 | 0 / 2 | 0 / 9 | 80 / 17 | 69 / 30 |
| daily_25k | 1 | 8 / 22 | 0 / 38 | 68 / 32 | 54 / 46 |

"pick" = the n>=150 pick. The literal pick is 0 / 0 everywhere in IS (6 trades in 4 years, no path to the target) and has 1 trade in J, so it is not shown.

Pro plans with today's YAMLs (D138):

| Plan | pick IS | pick J | NOISE IS | NOISE J |
|---|---|---|---|---|
| pro_25k | 8 / 22 | 0 / 38 | 68 / 32 | 54 / 46 |
| pro_50k | 3 / 22 | 0 / 38 | 67 / 33 | 53 / 47 |
| pro_100k | 0 / 2 | 0 / 9 | 80 / 17 | 69 / 30 |
| pro_150k | 0 / 2 | 0 / 9 | 80 / 17 | 69 / 30 |

## 6. Footprint snapshots (ESTIMATED; 3 most recent J trades of the n>=150 pick)

Volume units are the recovered relative units x 1000 (the recovery fixes volume only up to a per-day unit). Ladder = the 5 one-minute bars of the confirmation candle, built with the app's `footprint()` and summed per row (row 0.5 pt). Because each 1m bar spreads its volume evenly over its rows, identical neighbouring rows are collapsed below and stacked-imbalance counts are inflated by that assumption.

**2026-10-14 SHORT (DELTA FLIP)**, confirmation candle 10:35-10:40 ET: O 30510.25 H 30513.5 L 30455.75 C 30461.25; env ROTATION; candle delta -1114; CVD at entry -1492; est. POC 30489.25; stacked imbalances buy 1 / sell 65; location OFF.
Limit 30489.25 (valid 3 min), entry bar 10:42, fill incl. slippage 30489.0, stop 30513.75, AR trail (no fixed target), exit bar 10:47, **P&L -51.0 $ (1 micro)**.

| price row | est. bid vol | est. ask vol | delta | |
|---|---|---|---|---|
| 30513.5 to 30513.0 (2 rows) | 4.74 | 0.07 | -4.67 |  |
| 30512.5 to 30509.0 (8 rows) | 10.13 | 0.71 | -9.42 |  |
| 30508.5 to 30489.5 (39 rows) | 15.63 | 1.01 | -14.62 |  |
| 30489.0 | 15.63 | 1.01 | -14.62 | POC |
| 30488.5 to 30482.0 (14 rows) | 10.24 | 0.37 | -9.87 |  |
| 30481.5 to 30478.0 (8 rows) | 11.70 | 4.11 | -7.59 |  |
| 30477.5 to 30477.0 (2 rows) | 6.96 | 4.04 | -2.92 |  |
| 30476.5 to 30456.0 (42 rows) | 10.97 | 5.46 | -5.51 |  |
| 30455.5 | 9.51 | 1.72 | -7.79 |  |

**2026-10-14 LONG (DELTA FLIP)**, confirmation candle 14:45-14:50 ET: O 30126.75 H 30156.0 L 30118.0 C 30150.0; env ROTATION; candle delta +426; CVD at entry -5751; est. POC 30141.25; stacked imbalances buy 36 / sell 1; location OFF.
Limit 30141.25 (valid 3 min), entry bar 14:52, fill incl. slippage 30141.5, stop 30117.75, AR trail (no fixed target), exit bar 15:00, **P&L -49.0 $ (1 micro)**.

| price row | est. bid vol | est. ask vol | delta | |
|---|---|---|---|---|
| 30156.0 to 30149.5 (14 rows) | 2.26 | 3.30 | +1.04 |  |
| 30149.0 to 30146.0 (7 rows) | 3.19 | 10.72 | +7.53 |  |
| 30145.5 to 30141.5 (9 rows) | 4.43 | 14.21 | +9.78 |  |
| 30141.0 | 4.43 | 14.21 | +9.78 | POC |
| 30140.5 to 30140.0 (2 rows) | 2.17 | 10.91 | +8.74 |  |
| 30139.5 to 30136.5 (7 rows) | 1.24 | 3.49 | +2.25 |  |
| 30136.0 | 3.41 | 7.99 | +4.58 |  |
| 30135.5 to 30130.0 (12 rows) | 3.75 | 12.49 | +8.74 |  |
| 30129.5 to 30126.0 (8 rows) | 2.51 | 9.00 | +6.49 |  |
| 30125.5 to 30118.0 (16 rows) | 0.34 | 4.50 | +4.16 |  |

**2026-10-15 SHORT (DELTA FLIP)**, confirmation candle 14:10-14:15 ET: O 29993.75 H 29996.5 L 29960.0 C 29962.75; env ROTATION; candle delta -233; CVD at entry +4838; est. POC 29968.25; stacked imbalances buy 1 / sell 12; location OFF.
Limit 29968.25 (valid 3 min), entry bar 14:15, fill incl. slippage 29968.0, stop 29996.75, AR trail (no fixed target), exit bar 14:49, **P&L -59.0 $ (1 micro)**.

| price row | est. bid vol | est. ask vol | delta | |
|---|---|---|---|---|
| 29996.5 to 29988.5 (17 rows) | 2.09 | 1.27 | -0.82 |  |
| 29988.0 to 29987.5 (2 rows) | 4.95 | 2.87 | -2.08 |  |
| 29987.0 to 29981.0 (13 rows) | 8.35 | 3.27 | -5.08 |  |
| 29980.5 to 29974.5 (13 rows) | 6.26 | 2.00 | -4.26 |  |
| 29974.0 to 29973.5 (2 rows) | 3.40 | 0.40 | -3.00 |  |
| 29973.0 to 29972.5 (2 rows) | 7.51 | 0.69 | -6.82 |  |
| 29972.0 to 29968.5 (8 rows) | 9.83 | 4.36 | -5.47 |  |
| 29968.0 | 9.83 | 4.36 | -5.47 | POC |
| 29967.5 to 29962.0 (12 rows) | 6.43 | 3.96 | -2.47 |  |
| 29961.5 to 29960.0 (4 rows) | 2.32 | 3.67 | +1.35 |  |

## 7. Caveats

- The footprint is estimated from OHLC close location and VWAP-recovered volume, not aggressor-side flow. Absorption, delta flips, stacked imbalances and the candle POC are therefore functions of the bar shape only. Real delta could behave differently; this test cannot say.
- RTH only (09:30-16:00 ET). There is no overnight / Asia data, so the PATH layer cannot run (shipped config = 0 trades, reported above) and there is no 4h structure: bias = 1h + 15m confirmed swings (k = 2 bars) carried across days, tied or missing bias = no location trade.
- Environment, ATR(5m)/ATR(20d), ER and delta baselines use windows inside the day (>= 6 five-minute candles), so no trade before about 10:00 ET. ATR/overlap thresholds (30th / 95th pct, median) come from IS only; MES uses the MNQ-IS thresholds.
- Location uses the candle close for the fib depth and value side (pre-registered); swing range must be 0.2 to 2.5 daily ATR(20) (from ar.py). Fixed-range profile volumes are scale-equalised per day (needed only for multi-day swings). The shipped location gate fires about once per 150 sessions on this data, so every location-ON row is a tiny sample.
- Casper price_confirms uses the 1m candle that closed just before the fill bar (a causal reading of 'entry candle'); STACKED_IMBALANCE is not generated as a signal kind here (only absorption and delta flip), so the stacked rule is inert and Casper ON = price_confirms only.
- Limit at the confirmation candle's POC, live for the next 3 one-minute bars (confirm time = last 1m bar of the candle, so `confirm_max_age_min` 3 passes); filled on a touch; cancelled if the bar opens through the stop; a bar that touches both limit and stop is a loss. No target credit on the entry bar. Max 3 trades a day, one at a time, entries 09:35-15:30, flat 16:00.
- Targets fill at their price after a 1-tick trade-through (session 15/21 convention) rather than with a further tick of slippage.
- Sample sizes: n>=150 pick has 479 IS and only 62 J trades; J (about 245 sessions) was seen before by the team; the grid is 16 rows (plus 8 diagnostic). Bootstrap resamples only about 245 J sessions.
- Accounts: brake rows ignored; Daily 25K has no size table (1 micro); numbers are from the session-15 engine as in session 21.
- Files: of.py (engine), run.py, report.py, results.json, streams_pick_MNQ*.csv, streams_pick_MES*.csv (the `_n150` files are the pick used for the verdict).

## Review notes (main session, 2026-11-13, session 22)

- Re-ran `run.py` from a clean checkout of these files: results.json identical except `runtime_s` (the run is deterministic). NOISE column
  reproduces session 21 on all 9 plans (s21-era plan YAMLs); with today's D138 Pro YAMLs NOISE Pro 25K J = 54 / 46.
- Verdict checked: no grid row is eligible; the only rows with a usable sample have IS PF 0.85–1.02; the n ≥ 150 pick loses on J
  (PF 0.69, beats 1/30 random seeds) and on MES. The row with J PF 1.21 (k 1.5, trail, location OFF, Casper OFF) has IS PF 0.94 and was
  correctly not picked. The second pick (n ≥ 150) was added after the IS table and before any J number, and is flagged as a deviation.
- The SHIPPED Order Flow config cannot trade on RTH-only bars (no Asia range → OF_PATH_UNKNOWN); the shipped location gate fires about
  once per 150 sessions. Nothing changes in the app: Order Flow stays default OFF / unverified until real aggressor-side data
  (Databento `trades`, still locked: 403 auth_account_locked on 2026-11-13) is available.
