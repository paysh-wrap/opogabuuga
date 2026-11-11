# Session 18: AR Model (Christopher Creamer), bar-only approximation, MNQ + MGC, last 12 months (2026-11-11)

**Verdict: shadow only. Nothing here beats NOISE preset C, and the full four-layer AR Model does not work on these bars.**
On the picking months (PICK) the full model (ENV+LOC+PATH+CONF) has PF below 1 for every market and session. It fires only 2 to 11 times
in the 4 judging months (JUDGE), so its good-looking JUDGE numbers are noise. Random sides at the same moments with the same exits do as well
or better. The app's Order Flow button should stay **OFF / SHADOW**, with no live parameter set.

## Setup and caveats
- Rules: `../order_flow/AR_MODEL_RULES.md`. Script: `ar.py` produces `ar.json` and `stream_*.csv`. Data: cached MNQ.v.0 1m and MGC 1m CSVs. Nothing was downloaded (Databento is locked).
- **ESTIMATED order flow only** (signed volume = close-location x volume). There is no real delta, footprint imbalance, DOM or gamma data.
- PICK = 2025-11-06..2026-07-03 and JUDGE = 2026-07-06..2026-11-05. **Small sample**: the full model has 2-11 JUDGE trades per market/session.
- 1 micro, flat 16:00 ET, fee $1.00 (MNQ) / $1.60 (MGC) plus 1 tick slippage on the entry and on every exit, stop checked first inside a 1m bar.
  Risk per trade: MNQ 4-124 pt, MGC 1.6-25 pt. At most 2 trades a day. The day stops after the first win (teacher: "green, stop") or after 2 losses.
  AM = entries 09:35-11:00 ET. RTH = entries 09:35-15:30 ET.
- Eval: session-17 `sim.py`, Lucid Pro 25K, block bootstrap inside the window (400 paths). PASS and BUST are bootstrap percentages.
  Median days = median number of sessions to PASS.

## Layer implementation (bar-only)
1. ENVIRONMENT (rolling 12 x 5m bars): compression = (ATR5/ATR20d below the PICK 30th percentile AND mean candle overlap above the PICK median)
   OR ATR5/ATR20d above the PICK 95th percentile (teacher: stand aside on huge ATR). Compression means no trade.
   Expansion = efficiency ratio ≥ 0.4, and then only trades in the move's direction (continuation). Everything else is balance, where both sides are allowed.
2. LOCATION: top-down bias = sum of the 4h/1h/15m swing structure (HH+HL = +1, LH+LL = -1, from confirmed 2-2 pivots); bias is non-zero only when 4h does not oppose.
   The location is the 15m swing range fib zone 0.705-0.886 on the bias side (discount for longs, premium for shorts). It is invalid after any 5m close beyond 0.886 since the swing.
   The range must be 0.2-2.5 x ATR20d. The location can also be a touch of the prior-day RTH VAL (long, below prior POC) or VAH (short, above prior POC).
   The location stays active for 3 bars (it is a zone).
3. PATH: Asia range = 18:00-03:00 ET. Zones are measured in ATR20d units beyond the Asia high/low. The multipliers are quantiles (20/35/50/70/90%) of the
   PICK-day extension past Asia, giving Level1/AVR-/AVR/AVR+/MAX:
   MNQ up 0.118/0.204/0.295/0.474/0.804, down 0.107/0.195/0.312/0.479/1.064. MGC up 0.123/0.212/0.281/0.359/0.531, down 0.105/0.179/0.280/0.456/0.992.
   A long is OK when the day's low since 03:00 has reached Level1..MAX below the Asia low (London/NY manipulation done) or when price is above the Asia high
   and has not yet reached AVR. Shorts mirror this.
4. CONFIRMATION (5m): estimated absorption (heavy opposing delta > k x avg|delta|(20) but close in the favourable half) or a delta flip
   (prior bar delta against, this bar heavy delta for, close beyond the prior bar's extreme). ENTRY = a limit at the confirmation candle's estimated POC
   (price of its highest-volume 1m bar), valid 10 minutes; it is cancelled if the stop trades first. Stop = 1 tick beyond the confirmation candle's extreme (the absorption).
   Exits: fixed 2R; or trail5 / trail15 = breakeven + 2 ticks after +1R follow-through, then the stop sits 1 tick behind the POC of each newly closed 5m/15m candle (ratchet only).
   If CONF is off, entry is at the next 1m open with the same stop.
- PICK grid: k ∈ {1.0, 1.5} x exit {2R, trail5, trail15}. The full model was picked on PICK PF. Picks: MNQ AM k1 trail15, MNQ RTH k1 trail5, MGC AM k1.5 2R, MGC RTH k1 2R.

## Full AR Model (all 4 layers), JUDGE window
| market / session | PICK n / win% / PF | JUDGE n | win % | avg win / loss $ | PF | $/trade | net $ | max DD $ | PASS / BUST % | med days | random same exits $/tr, PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ AM | 10 / 10 / 0.56 | 2 | 50 | 796 / -77 | 10.4 | 360 | 719 | 77 | 81 / 0 | 107 | 71.5, n/a (2 trades) |
| MNQ RTH | 22 / 41 / 0.91 | 6 | 67 | 124 / -63 | 3.91 | 61.5 | 369 | 77 | 37 / 0 | 193 | 26.7, 2.61 |
| MGC AM | 4 / 25 / 0.39 | 3 | 67 | 69 / -51 | 2.70 | 28.8 | 87 | 51 | 0 / 0 | - | 23.6, 2.58 |
| MGC RTH | 11 / 18 / 0.27 | 11 | 27 | 64 / -41 | 0.58 | -12.6 | -138 | 150 | 0 / 2 | - | 18.1, 2.19 |
| Combined AM | 14 / 14 / 0.49 | 5 | 60 | 311 / -64 | 7.31 | 161 | 806 | 77 | 83 / 0 | 111 | - |
| Combined RTH | 33 / 33 / 0.59 | 17 | 41 | 98 / -46 | 1.50 | 13.6 | 231 | 141 | 10 / 0 | 206 | - |
| **NOISE preset C (MNQ)** | 100 / 57 / 1.44 | 49 | 51 | 247 / -150 | **1.72** | **52.5** | 2,574 | 977 | **68 / 32** | 23 | - |

Full year, combined: AM 19 trades, PF 1.33, net +$340, max DD $721. RTH 50 trades, PF 0.81, net -$367. NOISE: 149 trades, PF 1.53, net +$5,857.
The JUDGE PASS figures of 81-83% come from 2-5 trades and need about 110 sessions, so they are not evidence.

## Ablation (picked exit/k per row; JUDGE n / win% / PF / $ per trade; PICK PF in brackets)
| layers | MNQ AM | MNQ RTH | MGC AM | MGC RTH |
|---|---|---|---|---|
| L | 52/25/1.28/12.9 (0.65) | 87/28/0.72/-10.1 (0.76) | 48/25/0.52/-18.3 (1.49) | 81/25/0.52/-17.4 (1.14) |
| C | 126/28/0.67/-15.3 (0.90) | 144/36/0.72/-13.0 (0.82) | 67/48/1.81/29.0 (1.42) | 131/44/1.48/15.4 (1.09) |
| E+L | 43/28/1.49/20.4 (0.75) | 74/31/0.96/-1.2 (0.64) | 40/25/0.49/-21.2 (1.24) | 70/24/0.52/-19.0 (0.96) |
| E+C | 96/29/0.78/-10.5 (0.95) | 136/41/1.03/1.2 (0.90) | **64/47/1.59/22.6 (1.72)** | 129/42/1.31/10.8 (1.23) |
| L+C | 15/47/3.00/62.5 (0.63) | 26/50/2.02/27.6 (0.78) | 7/57/2.64/33.9 (1.06) | 22/41/1.22/5.8 (1.25) |
| P+C | 71/27/0.87/-5.9 (0.94) | 119/40/1.00/-0.1 (1.05) | 38/37/0.98/-0.8 (1.07) | 92/40/1.11/4.1 (0.76) |
| E+L+P | 17/29/2.14/44.1 (0.66) | 36/31/1.00/0.0 (0.49) | 12/25/0.43/-25.7 (1.71) | 30/23/0.50/-18.4 (1.48) |
| E+L+C | 10/70/5.67/115.8 (0.52) | 17/65/2.83/51.5 (0.80) | 6/67/3.08/43.0 (1.14) | 19/42/1.29/7.6 (0.74) |
| E+P+C | 47/26/1.00/-0.2 (1.12) | 110/45/1.23/6.5 (1.08) | 35/40/0.96/-2.0 (1.28) | 88/40/0.99/-0.5 (0.78) |
| L+P+C | 3/33/10.3/240 (0.71) | 10/50/2.63/31.9 (0.76) | 3/67/2.70/28.8 (0.35) | 11/36/0.92/-2.0 (0.24) |
| E+L+P+C | 2/50/10.4/360 (0.56) | 6/67/3.91/61.5 (0.91) | 3/67/2.70/28.8 (0.39) | 11/27/0.58/-12.6 (0.27) |
Full ablation rows (avg win/loss, net, DD, PASS/BUST, med days) are in `ar.json`.

What the ablation shows:
- **LOCATION** (bias + fib 0.705-0.886 + VA) has PICK PF below 1 on MNQ in every row. On MGC it looks good on PICK (1.1-1.7) but **collapses on JUDGE (0.4-0.5)**.
  It does not generalise in either direction.
- **PATH** (Asia/ATR zones) never helps: P+C is about the same as or worse than C alone.
- **ENVIRONMENT** (skip compression, continuation-only in expansion) is mildly positive almost everywhere, e.g. MNQ RTH C 0.72 to E+C 1.03 on JUDGE.
- Rows with L+C look strong on JUDGE (PF 2-10) but have PF below 1 on PICK and 3-26 trades, which looks like regime luck.
- The only row that is positive on both windows with a usable sample is **MGC AM, E+C** (estimated confirmation + environment, no location/path):
  PICK 109 trades PF 1.72, JUDGE 64 trades, 47% win, PF 1.59, $22.6/trade, max DD $642, PASS 89 / BUST 11, med 57 days.
  Random sides at the same moments with the same exits make $8.3 (PICK) / $4.0 (JUDGE) per trade with PF 1.14 / 1.04, so the confirmation adds about $15-20/trade over chance.
  But this row was found after the fact in the ablation, not chosen in advance. It is less than half of NOISE's $/trade, and it is not the AR Model (its location layer hurt).
  It is worth a SHADOW run, not a live button.

## Recommendation for the app's Order Flow button
- **SHADOW only. No LIVE/PAPER-armed parameter set**, because nothing beats NOISE preset C on held-out data (NOISE JUDGE: PF 1.72, $52.5/trade, PASS 68%).
- If a shadow logger is wanted, use the one positive candidate exactly as tested: MGC, AM entries 09:35-11:00 ET, environment filter (compression skip:
  ATR5(12)/ATR20d < 0.0372 with overlap > 0.628, or > 0.1146; expansion ER(12) ≥ 0.4 means continuation only), confirmation = estimated absorption/delta flip with k = 1.5,
  limit at the confirmation candle's estimated POC (10 min), stop 1 tick beyond the candle extreme, risk 1.6-25 pt, fixed 2R, flat 16:00, max 2/day, stop after the first win
  or after 2 losses. Re-judge after ≥ 60 new shadow trades against random sides.
- Real footprint data (Databento `trades`) would be needed to test the actual AR Model; the bar-only version cannot.
