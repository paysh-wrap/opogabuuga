# Indicator definitions used by Paytience (Python reference + Paytience_Bridge.pine)

**Status (2026-11-05): VERIFIED against both original sources.**
- Fractal model = port of "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]" (PUB;121faffd…, open-source).
- MSO = port of "Market Structure Oscillator [BigBeluga]" (PUB;8eb87677…, CC BY-NC-SA 4.0).
Python (backend/app/indicators/) and pine/Paytience_Bridge.pine follow the originals; their module docstrings are the
authoritative rule list (they supersede the older spec-derived text below). PERSONAL USE ONLY.
Remaining LIVE gate (§5.2): three-way parity over ≥ 20 recorded sessions.

## Timeframes
| Profile | Chart (LTF) | HTF candle | Grouping |
|---|---|---|---|
| TIGHT | 1 min | 15 min | HTF open time = floor(bar open time / 15 min) |
| STD | 5 min | 60 min | HTF open time = floor(bar open time / 60 min) |
An HTF candle closes on the LTF bar whose close time equals HTF open + HTF length.

## Fractal model (LunqFX role: WHERE / WHAT)
For each pair of consecutive HTF candles: **C1** = the completed candle, **C2** = the next one, **C3** = the one after.

During C2, on each LTF close:
- **Sweep**: LONG side swept when an LTF low < C1 low; SHORT side when an LTF high > C1 high.
  First sweep emits `C1_SWEPT` (direction LONG for a low sweep, SHORT for a high sweep).
  `sweep_extreme` = most extreme price beyond C1 so far; `sweep_time_ms` = close time of that bar.
  If C2 sweeps BOTH sides, no model forms from this C2.
- **CISD level**: when a new sweep extreme is made, `cisd_level` = open of the first candle of the most recent
  run of consecutive opposite-colour LTF candles (bearish run for LONG, bullish run for SHORT) ending at or before
  the extreme bar. If no such run exists, the extreme bar's open.
- **CISD**: an LTF candle CLOSES beyond `cisd_level` (above for LONG, below for SHORT) after the extreme.
  A new extreme resets the CISD. `cisd_before_c2_close` = CISD printed by the bar that closes C2.
- **T1 pre-tick**: price touched T1 during C2 after the sweep → `t1_preticked = true`.

At C2 close — **MODEL_CONFIRMED** when exactly one side was swept and C2 closes strictly inside C1
(C1 low < C2 close < C1 high; "Require C2 to close back inside C1" = ON, a pillar). Fields:
- `t1` = C1 midpoint rounded to tick; `t2` = C1 high (LONG) / C1 low (SHORT)
- `invalid` = `sweep_extreme` (stop anchor); `c1_time_ms` = C1 open time (model key)
- `htf_atr14` = Wilder ATR(14) of completed HTF candles including C2
- `c3_close_time_ms` = C2 close + HTF length

During C3 (model active), on each LTF close:
- `CISD` if not printed yet (then `cisd_before_c2_close = false`)
- `MODEL_FAILED` if price trades beyond `invalid` before T1 is hit. If one bar touches both T1 and invalid, it
  counts as FAILED (conservative).
- `T1_HIT`, then `T2_HIT` when price reaches them.
- `C3_CLOSED` at C3 close; the model ends.
Models overlap naturally: C3 of one model is C2 of the next.

## Market Structure Oscillator (BigBeluga role: WHEN / WHETHER)
Inputs: `pivot_left` = 5, `pivot_right` = 3, `osc_length` = 14 (VERIFY vs original).
- **Pivot high** at bar t: high[t] > the `pivot_left` highs before it and >= the `pivot_right` highs after it.
  Known only at bar t + `pivot_right` (the CONFIRMATION bar). Pivot low symmetric.
- **Structure**: on each close, if close > last unbroken confirmed pivot high → bullish break: `MSO_CHOCH` LONG
  if trend was BEAR, else `MSO_BOS` LONG; trend = BULL; that pivot is consumed. Bearish symmetric.
- **Oscillator**: raw = Wilder RSI(close, `osc_length`). Trend BULL → osc = 50 + raw/2; BEAR → osc = raw/2;
  no trend yet → osc = raw. So osc > 50 in bullish structure and < 50 in bearish structure.
- **Divergence** (at the pivot's confirmation bar): new pivot high with higher price but lower raw RSI than the
  previous pivot high → `MSO_DIV` SHORT; new pivot low with lower price but higher raw RSI → `MSO_DIV` LONG.
  `confirm_time_ms` = confirmation bar close, never the pivot bar.
- **HTF trend**: the same structure logic on completed HTF candles → `htf_trend`.

## Alert id
`<ticker>-<profile>-<bar close ms>-<EVENT>-<DIRECTION>` (D12 — direction prevents same-bar collisions).

## Heartbeat
Every LTF close sends `HEARTBEAT` with OHLCV. No heartbeat for 2× the bar interval during CME session hours →
feed STALE → new entries blocked.
