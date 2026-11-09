# meanrev — high-win-rate / mean-reversion study (MNQ, MGC)

**Verdict: nothing passed.** 38 a-priori variants. None has in-sample expectancy that is clearly positive after
costs. The variant that was best in-sample (MNQ PDH/PDL sweep → mid-range, IS +0.04R) collapses held-out (−0.34R, PF 0.62).
Win rates of 60–70% do occur (RSI2, gap-fill 50%, opening-drive pullback 0.5×), but the losses are 2× the wins,
so after costs the expectancy is ≤ 0. That is the usual pattern for retail-cost mean reversion on 1-minute futures.

Data: Databento `.v.0` 1m, 2019-05 → 2026-11-06, ET. IS = 2019-05..2023-12, OOS = 2024-01..2026-11. Costs per the brief
(MNQ $1 + 1 tick in and 1 tick out on stop/market exits; MGC $1.60 + 1 tick). Targets are limits that fill only on a
1-tick trade-through. If the stop and target are hit in the same bar, the stop counts. Flat 16:40, 1 position, max 3 trades/day
(the uncapped results are in summary.csv and are almost the same). R = net $ / initial risk $. News is not modeled. Roll days
(overnight gap > 1.5%) blank out prior-day features. I did not use an external source to tune anything. The rules are the
textbook versions (Connors RSI(2), VWAP σ bands, gap fill, PDH/PDL sweep, opening-drive pullback).

## Rules (as coded in `agents/meanrev/mr.py`)
1. **VWAPfade**: RTH VWAP from 09:30, with volume-weighted σ of the typical price. Signal when a 1m close crosses outside VWAP ± kσ
   between 10:00 and 15:30. Fade it at the next open. Stop at (k+1)σ, or 3×ATR30(1m). Target VWAP or 1σ. k ∈ {2, 2.5, 3}.
2. **RSI2**: 5m bars, Wilder RSI(2) and EMA200 (both carried across days, reset at rolls). Long when RSI2 < 5 and close > EMA200;
   short when RSI2 > 95 and close < EMA200. Signals 09:35–15:30. Exit at the next open after RSI2 crosses 50 (or 70), with a 60-minute time stop.
   Stop at 1.5 or 3 × ATR14(5m).
3. **GapFill (MNQ)**: gap = 09:30 open vs the prior RTH close, 0.3% or 0.5% up to 1.5%. Fade it at the 09:30 open (the strategy is *defined on*
   09:30, so it is exempt from the 09:30–09:35 skip). Stop 1× gap beyond the open. Target a full or 50% fill. Time stop 11:30.
4. **PDsweep**: price trades beyond the prior RTH high (or low), then a 1m close comes back inside within N ∈ {3, 5} bars. Enter at the next open.
   Stop at the sweep extreme ± 1 tick. Target the prior-day mid-range, or 1R. Signals 09:35–15:30.
5. **OpenDrive pullback**: the 09:30–10:00 move must be ≥ 0.35 × the 14-day average RTH range. Rest a limit at the 38.2% retrace of the drive
   (open→extreme) until 12:30. Stop at the 78.6% retrace. Target the drive extreme (1.0×) or halfway (0.5×). Time stop 13:00.

## Key rows (cap 3/day, 1 micro). R:R < 1.5 marked ⚠ (each needs the user to override the rr_min 1.5 pillar); BE = break-even win% = |avgL|/(avgW+|avgL|)
| variant | period | trades | /day | win% | avgW R | avgL R | exp R | $/trade | PF | maxDD R | worst streak |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ PDsweep N=5 →mid (**IS-best, selected**) | IS | 384 | 1.06 | 14.1 | 7.13 | −1.12 | +0.037 | −0.13 | 1.04 | 46.4 | 24 |
| 〃 | **OOS** | 207 | 1.04 | 15.5 | 3.64 | −1.07 | **−0.344** | −3.68 | **0.62** | 84.8 | 24 |
| MNQ OpenDrive 1.0× ⚠ (R:R≈0.9, BE 52%) | IS | 139 | 1.0 | 51.8 | 0.88 | −0.95 | −0.002 | −0.16 | 1.00 | 8.1 | 7 |
| 〃 | OOS | 108 | 1.0 | 58.3 | 0.89 | −0.97 | +0.117 | +9.95 | 1.29 | 7.1 | 7 |
| MNQ OpenDrive 0.5× ⚠ (BE 68%) | IS | 139 | 1.0 | 65.5 | 0.46 | −0.96 | −0.034 | −2.91 | 0.90 | 13.3 | 7 |
| 〃 | OOS | 108 | 1.0 | 69.4 | 0.46 | −0.98 | +0.017 | −3.30 | 1.06 | 9.0 | 7 |
| MNQ RSI2 exit50 stop3ATR ⚠ (BE 66%) | IS | 1374 | 1.66 | 64.0 | 0.22 | −0.43 | −0.017 | −1.78 | 0.89 | 29.2 | 5 |
| 〃 | OOS | 890 | 1.73 | 62.4 | 0.23 | −0.45 | −0.029 | −3.00 | 0.83 | 30.6 | 6 |
| MNQ GapFill ≥0.3% 50% ⚠ (BE 62%) | IS | 626 | 1.0 | 60.5 | 0.47 | −0.77 | −0.019 | −6.39 | 0.94 | 23.1 | 5 |
| 〃 | OOS | 366 | 1.0 | 59.6 | 0.46 | −0.76 | −0.034 | −10.51 | 0.89 | 17.9 | 8 |
| MNQ GapFill ≥0.5% full ⚠ (BE 47%) | IS | 419 | 1.0 | 45.8 | 0.76 | −0.68 | −0.02 | — | 0.95 | — | — |
| 〃 | OOS | 245 | 1.0 | 50.6 | 0.63 | −0.62 | +0.014 | −0.54 | 1.04 | 9.1 | 6 |
| MNQ VWAPfade k2.5 1σ ATRstop ⚠ (BE 49%) | IS | 1267 | 1.69 | 43.9 | 1.07 | −1.02 | −0.103 | −4.49 | 0.82 | 136.8 | 10 |
| 〃 | OOS | 765 | 1.70 | 48.1 | 1.04 | −1.01 | −0.024 | −4.83 | 0.95 | 49.2 | 9 |
| MGC RSI2 exit70 stop3ATR ⚠ (BE 66%) | IS | 1482 | 1.74 | 53.5 | 0.22 | −0.46 | −0.097 | −4.01 | 0.55 | 143.8 | 7 |
| 〃 | OOS | 822 | 1.68 | 59.9 | 0.24 | −0.46 | −0.040 | −2.44 | 0.79 | 37.3 | 11 |

All MGC variants were negative in-sample (best IS: PDsweep N=5 mid −0.19R; VWAP fades −0.18 to −0.32R; OpenDrive −0.15R).
Full table (38 variants × IS/OOS × cap3/uncapped): `agents/meanrev/summary.csv`.

## Per year — the selected IS-best (MNQ PDsweep N=5 → mid), exp R / PF / win%
2019 −0.09/0.91/17.5 · 2020 −0.34/0.66/12.5 · 2021 +0.46/1.47/13.3 · 2022 +0.03/1.03/15.6 · 2023 +0.04/1.04/11.8 ·
**2024 −0.73/0.28/7.5 · 2025 −0.03/0.97/24.3 · 2026 −0.31/0.66/13.6**. One year (2021) carries the whole in-sample result: overfit / fat-tail noise.
Highest-win-rate row (MNQ OpenDrive 0.5×) per year, win%/exp R: 2019 64.5/−0.02 · 2020 61.9/−0.11 · 2021 62.5/−0.10 · 2022 74.1/+0.12 ·
2023 64.3/−0.07 · 2024 82.9/+0.24 · 2025 69.4/−0.00 · 2026 56.8/−0.17. Its $/trade is negative overall because the larger-risk trades lose.

## Lucid 25K eval bootstrap (held-out days resampled iid, zero-trade days included, 10,000 paths, 120-day cap; `evalsim.py`)
Model: target +$1,250, EOD trailing max loss $1,000. DLL and the 40% consistency rule are not modeled.
| variant | 1 micro pass/bust | 2 micros | 3 micros |
|---|---|---|---|
| MNQ PDsweep N=5 mid (selected) | 1.7% / 8.6% (90% neither) | 15.6% / 53.1% | 25.1% / 69.0% |
| MNQ OpenDrive 0.5× (highest win%) | 0.0% / 5.6% | 8.8% / 38.6% | 23.1% / 59.2% |
| MNQ OpenDrive 1.0× (best OOS, *not* IS-selected) | 4.8% / 8.8% | 33.2% / 41.7% | 42.6% / 53.7% |
Every case is more likely to bust than to pass. At 1 micro none of them reaches $1,250 within 120 days.

## Verdict, risks, Paytience fit
- PASS rule (OOS exp > 0, PF ≥ 1.15, ≥ 100 trades): **no variant passes when selection is done honestly on IS.** OpenDrive 1.0× clears the
  thresholds OOS (108 trades, PF 1.29), but it was flat in-sample (PF 1.00). Choosing it now would be selecting on held-out data,
  which the protocol forbids. At most it is a candidate for a *new* forward/shadow test, not for adoption.
- The high-win-rate variants (RSI2, gap fill 50%, OpenDrive 0.5×) all have R:R ≈ 0.5, so they need roughly 62–68% wins to break even.
  They reach 57–69%, which is not enough after costs. They would also violate rr_min 1.5 (a pillar) and the WIN-RATE RULE (D49 forbids 1R-or-less targets).
  **Do not add them.**
- Plug-in (if a forward test is ever approved): OpenDrive would use heartbeat bars as the signal source, a resting limit at 38.2%, the stop at 78.6% as the
  TradePlan invalid level, and the target at the drive extreme. It conflicts with rr_min 1.5 (G7), with the Fractal/MSO gates G3–G5 (not a C1/C2
  sweep model), and with D2 (this one is OK: 10:00–12:30 lies inside the window).

Reproduce: `cd …/scratchpad/agents/meanrev && nice -n 10 /home/user/opogabuuga/.venv/bin/python mr.py` (~5 min, writes summary.csv and trades.pkl),
then `…/python evalsim.py MNQ "OpenDrive pullback tgt=1.0x"`.
