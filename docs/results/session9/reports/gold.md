# Agent "gold" — MGC session-structure strategies (verdict: NOTHING PASSED on an honest selection)

Data: MGC.v.0 1m, 2019-05-05 → 2026-11-06 (1,940 session days; only 2 days with overnight gap > 1.5%,
flagged as roll days; daily ATR uses H-L only, 20-day trend uses summed intraday log(c/o) so roll gaps cannot leak).
Protocol per BRIEF: closed bars, next-bar-open market entries (+1 tick), stop entries fill only 1 tick through the
level (+1 tick slip), limit targets need 1 tick through (no slip), stop exits −1 tick, stop-first on same-bar touch,
flat ≤ 16:40 ET, fee $1.60 RT, ≤ 1 trade/day per variant (cap 3 never binds). News blackouts NOT modeled.
R = net P&L / (|fill − stop| × $10). 36 variants, all fixed a priori; 3 selected by IS expectancy (≥ 200 IS trades).
Code: `agents/gold/gold.py`. Reproduce: `cd …/scratchpad/agents/gold && nice -n 10 /home/user/opogabuuga/.venv/bin/python gold.py`
(outputs run.txt, summary.csv = all IS/OOS rows, trades.csv = every trade).

## Rules tested (ET times; "Asian range" = 18:00 prev day → 02:00)
- A Asian-range breakout 02:00–05:00: stop entry 1 tick beyond Asian H/L; stop = opposite side (or range mid);
  target 1.5/2/3R; exit 11:30.
- B London sweep → reversal: 02:00–05:00 price trades beyond Asian H (L), then a 5m bar closes back inside →
  enter opposite at next open; stop = sweep extreme ± 1 tick; target 1.5R / 2R / opposite Asian side (≤ 3R).
- C London-open range 03:00–03:30, breakout until 06:00, stop opposite side, 1.5R/2R.
- D COMEX 08:20 ORB (5/15/30 min), breakout until 11:30, stop opposite side (or 0.25×ATR14), targets
  1.5/2/2.5/3R or no target with exit 11:30 / 16:40.
- E Trend continuation: |close(10:00) − open(08:20)| > k×ATR14 (k 0.3/0.5) → limit at 08:20-anchored VWAP,
  10:00–13:00, stop 0.25×ATR, 2R, exit 16:40.
- F Fade: 10:00–11:30 first 1m close > k×ATR from VWAP → fade at next open, stop 0.25×ATR, target VWAP.
- G 20-day trend filter (sign of prior-20-day summed intraday return; only trade that side) on the picks + ORB15 2R.
Sources: ORB/session-range breakouts are standard practitioner ideas (Crabel 1990 "Day Trading with Short Term
Price Patterns and Opening Range Breakout"); no published, verified MGC edge found for any of them.

## In-sample selection (2019-05 → 2023-12): EVERY one of the 36 variants had negative expectancy after costs.
Best IS: E_trend_pb_k0.3_2R −0.021R (216 tr), D_comex_orb5_x1640 −0.031R, D_comex_orb15_x1130 −0.043R.

| variant | period | trades | tr/day | win% | avgW R | avgL R | exp R | $/tr | PF | maxDD R | worst streak |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E_trend_pb_k0.3_2R (pick 1) | IS | 216 | 1.0 | 44.4 | 1.02 | −0.86 | −0.021 | −1.31 | 0.96 | 27.7 | 8 |
| | OOS | 116 | 1.0 | 37.9 | 1.02 | −0.83 | −0.124 | −12.67 | 0.83 | 14.7 | 6 |
| D_comex_orb5_x1640 (pick 2) | IS | 1160 | 1.0 | 19.5 | 4.40 | −1.10 | −0.031 | −0.38 | 0.99 | 78.4 | 17 |
| | OOS | 719 | 1.0 | 16.3 | 5.09 | −1.05 | −0.054 | −6.55 | 0.87 | 70.8 | 33 |
| D_comex_orb15_x1130 (pick 3) | IS | 1181 | 1.0 | 35.5 | 1.56 | −0.93 | −0.043 | −0.98 | 0.97 | 62.8 | 13 |
| | OOS | 726 | 1.0 | 33.3 | 1.73 | −0.95 | −0.053 | −8.55 | 0.87 | 61.3 | 15 |
| D_comex_orb15_2R | IS | 1181 | 1.0 | 38.0 | 1.32 | −0.93 | −0.076 | −2.29 | 0.92 | 92.1 | 12 |
| | OOS | 726 | 1.0 | 37.7 | 1.48 | −0.96 | −0.037 | −7.04 | 0.89 | 49.3 | 13 |
| D_comex_orb15_2R + tr20 | IS | 584 | 1.0 | 39.9 | 1.31 | −0.94 | −0.043 | −3.73 | 0.88 | 26.6 | 8 |
| | OOS | 361 | 1.0 | 39.1 | 1.53 | −0.94 | +0.024 | −4.13 | 0.94 | 31.4 | 11 |
| E_trend_pb_k0.3_2R + tr20 | IS | 109 | 1.0 | 44.0 | 1.08 | −0.85 | +0.001 | −1.01 | 0.97 | 12.6 | 7 |
| | OOS | 59 | 1.0 | 47.5 | 0.93 | −0.86 | −0.015 | +14.60 | 1.25 | 6.2 | 4 |
| B_asia_sweep_rev_2 (the app's "sweep" idea) | IS | 781 | 1.0 | 31.8 | 1.80 | −1.21 | −0.251 | −3.46 | 0.78 | 205 | 14 |
| | OOS | 433 | 1.0 | 30.5 | 1.89 | −1.12 | −0.204 | −7.74 | 0.76 | 87 | 13 |
| F_fade_k0.3_vwap | IS | 444 | 1.0 | 48.0 | 0.69 | −0.74 | −0.057 | −3.71 | 0.84 | 33 | 10 |
| | OOS | 223 | 1.0 | 48.9 | 0.64 | −0.76 | −0.076 | −14.91 | 0.74 | 22 | 8 |
| A_asia_bo_opp_2R (NOT selected) | IS | 908 | 1.0 | 39.3 | 1.14 | −0.82 | −0.051 | −1.49 | 0.97 | 50.6 | 9 |
| | OOS | 505 | 1.0 | 48.9 | 0.88 | −0.72 | +0.063 | +23.84 | 1.26 | 15.5 | 7 |

Best held-out row of the honestly selected picks: none positive. (Picks 1–3 all lose OOS, PF 0.83–0.87.)

## Per-year, best-looking OOS family (A Asian-range breakout, opposite-side stop, 2R) — shown because it is the
only family with OOS PF ≥ 1.15; it fails the selection rule (IS negative) and is regime-driven:
| year | trades | win% | exp R | $/tr | PF | median risk $/micro |
|---|---|---|---|---|---|---|
| 2019 | 121 | 34.7 | −0.168 | −5.48 | 0.82 | 63 |
| 2020 | 183 | 41.5 | −0.013 | +4.90 | 1.09 | 118 |
| 2021 | 204 | 38.7 | −0.061 | −4.37 | 0.91 | 90 |
| 2022 | 204 | 43.1 | −0.005 | +1.90 | 1.04 | 91 |
| 2023 | 196 | 36.7 | −0.053 | −5.52 | 0.88 | 80 |
| 2024 | 203 | 45.3 | +0.076 | +8.52 | 1.17 | 123 |
| 2025 | 176 | 46.6 | −0.003 | +8.51 | 1.09 | 265 |
| 2026 | 126 | 57.9 | +0.135 | +69.96 | 1.45 | 508 |
OOS profit is mostly 2026 (gold's record-volatility trend year); 5 of 8 years have negative R expectancy.
Median risk of $265–508 per single micro is also incompatible with the $600 DLL / Eval max_risk_usd $140.

## 20-day trend filter stability (ORB15 2R, exp R with-trend vs against, by year)
with-trend: 2019 −0.09, 2020 −0.06, 2021 +0.01, 2022 +0.07, 2023 −0.17, 2024 −0.06, 2025 +0.08, 2026 +0.05.
against: −0.33, −0.07, −0.11, −0.11, +0.03, −0.09, +0.03, −0.23. With-trend is better in 6/8 years but itself is
≤ 0 in 4/8 years — it reduces losses (halves trades), it does not create an edge. The sign flip in 2023 seen in
the repo is reproduced.

## Verdict: FAIL — no variant passes (held-out exp > 0, PF ≥ 1.15, ≥ 100 trades) under honest IS selection.
- MGC intraday session structure (Asian/London/COMEX ranges, ORB, VWAP pullback/fade) shows no stable edge after
  realistic costs 2019–2026. Gross (pre-cost) expectancy is ≈ 0 for most families; costs (~$3.6/RT vs
  $60–120 typical risk pre-2024) turn them negative. Edge "appears" only when gold trends violently (2025–26).
- The liquidity-sweep-reversal of session ranges (B) is the worst family (−0.20 to −0.30R both periods), which is
  consistent with the app's MGC every-setup loss: on gold, session-range sweeps tend to continue, not reverse.
- Recommendation for Paytience: keep MGC trading OFF or paper-only; do not add any of these as a live signal.
  If anything is pursued, A (Asian-range breakout during London, 02:00–05:00) is the only candidate worth a
  forward/paper test — it would conflict with D2's 06:45–11:30 window, needs a stop at the opposite Asian
  extreme (often > the $140 Eval risk cap), and its R:R (2R target) fits the 1.5–2.5 config. Treat as hypothesis.
- Risks/caveats: news not modeled; 1 micro only; continuous .v.0 without back-adjust (only 2 gap days found, so
  roll impact is small); stop-first assumption is conservative.
