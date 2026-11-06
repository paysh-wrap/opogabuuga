# The 58% plan (D36/D37) — RETIRED as main by D47; kept for reference

Live plan: `config/rules/lucid_flex_25k.yaml` (default; same rules in all Pro/Flex plans). MGC only (D42), Intraday mode
only (Scalp/1:1 retired, D43). Measured: 22 sessions Oct–Nov 2026 → 24 trades, 58% win, PF 1.69, +$324 (Results H).
Binding: never add anything that lowers this; add only measured improvements (CLAUDE.md WIN-RATE RULE).

## The mix (why it is ~58% and not ~35%)
A pure fixed 1.75R target on these setups wins only ~28–36% (Results O, 7 years). The plan wins more because it picks
the TARGET per setup instead of forcing 1.75R:
1. **Structure-break setups** (CHoCH/BoS after the sweep) → target the model's own T1/T2, R:R 1.75–3R.
2. **No-break setups** → target capped at **1R** (`filters.no_break_rr_cap: 1.0`, D36/D36b). These are the high
   win-rate trades; in the 22-session sample 15 of 24 trades aimed at 1R.
3. `trade_plan.rr_min: 1.0` allows the 1R trades; anything below 1R is skipped (RR_BELOW_MIN).
So the 58% is a blend: many ~1R trades at a high hit rate + fewer 1.75–3R trades. Averaged it is positive (+0.38R).

## The steps (every one is in code — the engine repeats them on every bar, every day)
1. **Model**: LunqFX C1→C2→C3 fractal on 1m (TIGHT) and 5m→1H (STD); C2 must close inside C1 (pillar).
2. **Sweep + CISD**: price sweeps C1's extreme, then a change-in-state-of-delivery; limit entry at the CISD level
   (`entry.mode: limit_cisd`, 4-bar timeout, max 6 bars wait).
3. **Gates G1–G8**: entry hours, bias (TradingAgents; NEUTRAL in backtests), news blackout, MSO structure (score only),
   structure break (score only), C1 ≥ 0.4 × ATR, R:R window, cooldown/one entry per model.
4. **Best hours (D37 "H1")**: MGC entries only 05–07, 09–12, 13–15:30 ET (Intraday mode). Raised MGC 61%→71% in-sample.
5. **Score ≥ 60** (neutral bias too) with **oscillator strength ≥ 20** (`score.osc_strength_min: 20`).
6. **Stop** = sweep extreme + 4-tick buffer (min 16 ticks MGC); **target** per the mix above.
7. **Risk**: 7/9/11% of risk base by score tier, max 5 trades/day, 2 losses/day stop, day lock-in at +2R,
   flat by 16:40 ET, all Lucid rules (MLL/DLL/consistency) checked before every order.

## How to keep it repeatable
- Nothing here is discretionary: the TradingView bridge sends the bars, the engine applies the same steps, and
  `make test` (534 tests, 100% on risk/management/phases) locks the behaviour.
- The Strategy Lab (D40) may only tune within §17.2 bounds and only promotes a challenger that beats the champion
  out-of-sample; it auto-rolls back if live results drop (D40b).
- Any new idea (indicator, hour change, bias source) must first beat the plan on held-out data — Results O shows why:
  Squeeze looked like 54% on 4 months and was 30% on 7 years.

## Re-measured on the last 2 years (Nov 2024 – Oct 2026, Databento MGC.v.0, engine, NEUTRAL bias) — Results P
| | trades | win | PF | $ | R/trade |
|---|---|---|---|---|---|
| all | 391 | 43% | 0.87 | −1,201 | −0.05 |
| ~1R targets | 320 | 45% | 0.86 | −934 | −0.07 |
| 1.75R+ targets | 71 | 32% | 0.88 | −268 | +0.02 |
The 58% came from 22 sessions and did NOT hold. Replaced as main strategy by D47 (docs/STRATEGY_MAIN.md).
