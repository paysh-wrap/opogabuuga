# Order blocks + simulated footprint, MNQ (session 21, research only)

**Footprint = OHLC-derived estimate, not real order flow.** Volume is the Databento 1-minute volume recovered from the stored VWAP (v_k/V_k = (vwap_k - vwap_(k-1)) / (tp_k - vwap_(k-1)); ill-conditioned bars imputed by local median; imputed share MNQ 0.06%, MES 0.33%). Delta = volume x (2 x close-location - 1) (tick rule if h == l), exactly the app's method; CVD = running sum from 09:30. Robustness: range-as-volume and volume = 1 rows below.

## 1. Answer

**No edge.** Pick on IS only: OB on 5-minute bars, variant V2 (absorption), R 2.5: IS PF 1.18 (+8.4 $/trade) but on the judge window J PF 0.83, -12.9 $/trade, net -2,406; it beat 18/30 random-side seeds on J (needs 27). Verdict rule (J PF >= 1.15, net > 0, beats >= 90% of seeds) fails on all three. MES check also negative. So NOISE + OB was not built. Every plain-OB / footprint-confirmed variant on J has PF < 1.0 on 5m and 1m.

Eval bootstrap (10-day blocks, 600 paths, 400 sessions), pass% / bust%, size = plan size_table micros (Daily 25K has no table: 1 micro). Brake rows ignored.

| Plan | micros | OB IS | OB J | NOISE IS | NOISE J |
|---|---|---|---|---|---|
| pro_25k | 1 | 56 / 44 (63d) | 16 / 84 (30d) | 70 / 30 (53d) | 55 / 45 (32d) |
| pro_50k | 2 | 53 / 47 (79d) | 12 / 88 (40d) | 68 / 32 (60d) | 54 / 46 (43d) |
| pro_100k | 2 | 56 / 33 (212d) | 4 / 95 (115d) | 80 / 17 (161d) | 70 / 30 (114d) |
| pro_150k | 3 | 56 / 33 (212d) | 4 / 95 (115d) | 80 / 17 (161d) | 70 / 30 (114d) |
| flex_25k | 1 | 56 / 44 (63d) | 13 / 87 (30d) | 68 / 32 (63d) | 52 / 48 (63d) |
| flex_50k | 2 | 53 / 47 (79d) | 11 / 89 (42d) | 67 / 33 (70d) | 50 / 50 (70d) |
| flex_100k | 2 | 56 / 33 (212d) | 4 / 95 (115d) | 80 / 17 (169d) | 69 / 30 (121d) |
| flex_150k | 3 | 56 / 33 (212d) | 4 / 95 (115d) | 80 / 17 (169d) | 69 / 30 (121d) |
| daily_25k | 1 | 56 / 44 (63d) | 13 / 87 (30d) | 68 / 32 (63d) | 54 / 46 (64d) |

(median sessions to pass in brackets). Pro 100K and 150K match because 2/3000 and 3/4500 micros per MLL are the same ratio.

## 2. The pick (selected on IS)

Columns: trades / win / PF / $ per trade / net $ / max closed-trade DD $ (1 micro).

- IS (to 2025-11-05): 972 / 35.2% / 1.18 / +8.4 / +8,161 / 3,128
- J (2025-11-06..2026-10-30): 187 / 28.9% / 0.83 / -12.9 / -2,406 / 4,456
- MES check (same config, 1 micro): IS 956 / 28.8% / 0.85 / -4.6 / -4,368 / 5,263; J 228 / 32.9% / 0.86 / -5.2 / -1,180 / 2,478

Per-year (all trades):

| Year | trades | win | PF | $/trade | net |
|---|---|---|---|---|---|
| 2021 | 69 | 52.2% | 2.41 | +38.2 | +2,636 |
| 2022 | 252 | 30.6% | 1.10 | +5.7 | +1,440 |
| 2023 | 241 | 36.9% | 1.21 | +7.5 | +1,814 |
| 2024 | 226 | 37.6% | 1.34 | +14.4 | +3,262 |
| 2025 | 213 | 30.0% | 0.90 | -6.2 | -1,316 |
| 2026 | 158 | 28.5% | 0.82 | -13.2 | -2,080 |

NOISE baseline (1 micro): IS 536 / 49.6% / 1.50 / +27.2 / +14,556 / 2,096; J 118 / 59.3% / 1.58 / +40.1 / +4,737 / 1,024

## 3. Full grid (recovered volume; only the pick was judged, the J columns are shown for completeness)

| TF | Var | R | IS n | IS PF | IS $/tr | J n | J PF | J $/tr | eligible | picked |
|---|---|---|---|---|---|---|---|---|---|---|
| 5m | V0 | 1.5 | 1732 | 1.06 | +1.9 | 330 | 0.91 | -4.9 | yes | not picked |
| 5m | V0 | 2.0 | 1696 | 1.10 | +3.7 | 325 | 0.93 | -4.1 | yes | not picked |
| 5m | V0 | 2.5 | 1665 | 1.14 | +5.3 | 321 | 0.94 | -3.7 | yes | not picked |
| 5m | V1 | 1.5 | 463 | 1.06 | +2.4 | 92 | 0.81 | -12.8 | yes | not picked |
| 5m | V1 | 2.0 | 461 | 1.16 | +7.0 | 92 | 0.81 | -14.5 | yes | not picked |
| 5m | V1 | 2.5 | 458 | 1.12 | +5.6 | 90 | 0.69 | -25.2 | yes | not picked |
| 5m | V2 | 1.5 | 1023 | 1.12 | +4.8 | 196 | 0.97 | -1.6 | yes | not picked |
| 5m | V2 | 2.0 | 992 | 1.08 | +3.5 | 192 | 0.78 | -15.8 | yes | not picked |
| 5m | V2 | 2.5 | 972 | 1.18 | +8.4 | 187 | 0.83 | -12.9 | yes | PICK |
| 5m | V3 | 1.5 | 265 | 1.06 | +2.5 | 57 | 0.79 | -15.8 | yes | not picked |
| 5m | V3 | 2.0 | 264 | 1.16 | +7.5 | 57 | 0.79 | -17.3 | yes | not picked |
| 5m | V3 | 2.5 | 263 | 1.10 | +5.1 | 57 | 0.71 | -24.4 | yes | not picked |
| 1m | V0 | 1.5 | 3063 | 0.90 | -2.0 | 733 | 0.89 | -3.3 | no | not picked |
| 1m | V0 | 2.0 | 3063 | 0.90 | -2.2 | 733 | 0.89 | -3.6 | no | not picked |
| 1m | V0 | 2.5 | 3061 | 0.91 | -2.1 | 731 | 0.86 | -4.7 | no | not picked |
| 1m | V1 | 1.5 | 2135 | 0.93 | -1.6 | 505 | 0.90 | -3.7 | no | not picked |
| 1m | V1 | 2.0 | 2099 | 0.94 | -1.5 | 502 | 0.92 | -3.1 | no | not picked |
| 1m | V1 | 2.5 | 2074 | 0.92 | -2.3 | 497 | 0.98 | -1.0 | no | not picked |
| 1m | V2 | 1.5 | 2817 | 1.00 | -0.0 | 653 | 0.90 | -3.9 | no | not picked |
| 1m | V2 | 2.0 | 2791 | 0.98 | -0.4 | 649 | 0.90 | -4.1 | no | not picked |
| 1m | V2 | 2.5 | 2757 | 0.98 | -0.5 | 642 | 0.95 | -2.0 | no | not picked |
| 1m | V3 | 1.5 | 1321 | 1.01 | +0.3 | 314 | 0.83 | -6.6 | no | not picked |
| 1m | V3 | 2.0 | 1293 | 1.02 | +0.5 | 309 | 0.86 | -6.0 | no | not picked |
| 1m | V3 | 2.5 | 1275 | 0.99 | -0.3 | 306 | 0.93 | -3.0 | no | not picked |

Robustness: the pick under other volume definitions (not used for selection)

| Volume | IS n | IS PF | J n | J PF |
|---|---|---|---|---|
| rec | 972 | 1.18 | 187 | 0.83 |
| range | 972 | 1.18 | 186 | 0.82 |
| one | 961 | 1.18 | 188 | 0.82 |

(The full grid for range and volume=1 proxies is in results.json.)

## 4. Random-side benchmark (pick, same entries/stops/R, 30 seeds)

- J: pick -12.9 $/trade; random mean -16.1; pick beat 18/30 (needs >= 27).
- IS: random mean +1.5; pick beat 30/30 (the IS pick is mostly a win on the IS window and did not carry over).

## 5. Caveats
- Footprint is estimated from OHLC close location with VWAP-recovered volume, not aggressor-side order flow; per-day scale only.
- RTH-only data (no overnight context); ATR carried across days.
- J is about 245 sessions (~190 pick trades), J was seen before by the team; about 24 grid rows tested (x3 volume variants for robustness).
- News not modelled; stop-first inside bars; V0 limit fill gets no target credit on its entry bar.
- Accounts: bootstrap resamples only ~245 J sessions with 10-day blocks over 400 sessions; brake rows ignored; DLL/consistency per plan YAML via session15 engine (`lib._day`, `lib.eval_run`); plans read directly with PyYAML (lib.plan_rules only covers Pro).
- One OB candidate per OB, consumed on first touch in the 09:45-15:00 window; multi-OB ties resolved by earliest entry.
- Files: ob.py (engine), run.py, report.py, results.json, streams_pick_MNQ.csv, streams_pick_MES.csv.

## Review notes (main session, 2026-11-13)

- Verdict checked against results.json: no order-block / footprint variant has an edge on J (all 24 rows J PF < 1.0); the IS pick loses on J and beats
  only 18/30 random-side seeds. Order blocks stay a display/research item; nothing is proposed for the app.
- **Account engine differs from sessions 19–20, and that matters for NOISE too.** This study uses the session-15 engine, which also ends the
  account when a trade's worst open loss (MAE) touches the drawdown floor during the day (Lucid enforces the EOD-set floor in real time).
  The session-19/20 simulator (`lib.eval_run`) only checks closed trades. Same NOISE stream, same Pro 25K rules: J 68/32 (closed trades only)
  vs 55/45 (intraday touches); IS 72/28 vs 70/30. The Strategy-page cards and presets quote the closed-trade numbers, so they are optimistic.
  Not changed in the app; flagged for the user.
