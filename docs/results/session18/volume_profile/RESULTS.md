# Session 18 - Volume-profile strategy (tradealgo "Strategy 5") on MNQ + MGC, last 12 months

Research only (SOURCE_RULES.md claims UNVERIFIED). Scripts: `vp.py` (`MKT=MNQ|MGC python3 -I vp.py`), `report.py` (-> `tables.md`), per-config trade streams + json in `out/`. Reuses `rsi_dmi/lib.py` (loader, `run_trade`, costs) and the session-17 Lucid Pro 25K eval sim.

## Method
- Data: cached Databento 1m only (no download), last 12 months 2025-11-06..2026-11-05. **Pick on first ~8 months (IS, to 2026-06-30), judge on last ~4 (HO, 2026-07-01..).** ONE YEAR IS SMALL: V1/V2 have 10-46 trades per 12 months, HO 4-24 trades; every PF/PASS figure below is anecdote-level, roll PASS/BUST uses only ~24 start dates.
- Prior-session profile from 1m bars: close-binned volume (MNQ 1.0 pt bins over RTH 09:30-16:00; MGC 0.5 pt bins over COMEX RTH 08:20-13:30 ET, MGC volume re-read from the csv), POC = max bin, value area = 70% of volume grown from the POC two bins at a time (VAH/VAL). Open = first RTH bar open. Prior-day RTH high/low (PDH/PDL) also kept.
- Entries are LIMIT orders at the level at first touch (never in the first 5 min, none in the last 60 min MNQ / 30 min MGC); first touch per side per day; 1 micro, one position at a time, stop-first inside a bar, $1.00 (MNQ) / $1.60 (MGC) RT fee + 1 tick slippage on every fill, flat 15:59 (MNQ) / 13:30 (MGC). $250 risk cap.
- V1 open > VAH -> buy dip to VAH. V2 open < VAL -> sell rally to VAL. V3 open inside VA -> buy first VAL touch / sell first VAH touch. V1+V2 = trend-days only (drop the inside-value fades). V5 = V1+V2+V3. Stop kinds: `pct8` = the article's 8 ES points scaled by price level (8/6000 = 0.133% of price: MNQ ~30+ pt, MGC ~5 pt), `atr` = 1.5 x 15m ATR(14) at the open, `tick` = fixed (MNQ 30 pt = 120 ticks, MGC 5.0 pt = 50 ticks). Targets: 1.5R, 2.0R, STRUCT (trend: PDH/PDL, replaced by 2R if < 0.75R away; V3: POC), OPP (V3 only: opposite VA edge).
- Random-entry benchmark: same events, same level, same stop distance and target distance, random side (15 seeds, HO PF shown). IS-pick rule fixed in advance: best IS PF per variant with IS n >= 15. NOISE preset C stream from session 17 (MNQ).

## 80% rule (open inside value, first edge touch, does price reach the opposite edge before the close)
| market | days | reached opposite edge | median minutes | IS | HO | from VAL (long) | from VAH (short) | touch bar closed back inside VA |
|---|---|---|---|---|---|---|---|---|
| MNQ | 57 | **42.1%** | 143 | 45.0% (40) | 35.3% (17) | 39.3% (28) | 44.8% (29) | 46.4% (28) |
| MGC | 55 | **25.5%** | 74 | 27.8% (36) | 21.1% (19) | 22.2% (27) | 28.6% (28) | 26.5% (34) |
Claimed ~80%; measured 42% / 26% (and below 50% = a coin flip for MNQ). Even with the "closed back inside" acceptance filter the hit rate does not approach 80%.

## Claimed win rate 55-65% vs measured
Real (non-random) win rates in the full 12 months: trend (V1 buy above VAH, 1.5R, pct8) MNQ 51% (n=35), MGC 47% (n=32); V1+V2 trend-only 35-43% typical; inside-value fades 30-53% depending on target (MNQ atr/STRUCT 53%, OPP 43%); combined 29-50%. The 55-65% claim is only ever approached with 1.5R/near targets on tiny samples (MNQ V1 pct8 1.5R HO 60% on n=10, MGC V2 atr 58% on n=12); with the structural opposite-edge target the win rate is 27-47%, i.e. it is a PF-by-wide-target system, not a high win-rate one. Never above 65% anywhere on n >= 30.

## Key reading
All PF figures are 12-month (n) unless HO stated. Full grid (every variant x stop x target, IS + HO + 12mo + random benchmark) in `tables.md` below.

| market / variant (IS pick) | HO n | win% | PF | $/tr | net $ | maxDD $ | roll PASS/BUST % | random-side HO PF |
|---|---|---|---|---|---|---|---|---|
| MNQ NOISE preset C (baseline) | 51 | 51.0 | 1.76 | 57.38 | 2,926 | 977 | 100/0 (12mo: 78/21) | - |
| MNQ V1 above-VAH (pct8, STRUCT) | 10 | 50.0 | 2.67 | 67.15 | 672 | 238 | 0/0 (too few) | 2.00 |
| MNQ V2 below-VAL | 4 | 25.0 | 0.33 | -76.88 | -308 | 462 | 0/0 | 0.99 |
| MNQ V1+V2 trend-only (tick, STRUCT) | 14 | 28.6 | 1.34 | 15.14 | 212 | 378 | 0/0 | 1.37 |
| MNQ V3 inside fade (tick, OPP) | 19 | 26.3 | 1.38 | 17.37 | 330 | 310 | 0/0 | 1.62 |
| MNQ V5 combined (tick, OPP) | 33 | 27.3 | 1.36 | 16.42 | 542 | 434 | 0/0 | 1.53 |
| MGC V1 above-VAH (tick, 2R) | 12 | 33.3 | 0.90 | -3.60 | -43 | 214 | 0/0 | 1.75 |
| MGC V2 below-VAL (atr, 2R) | 12 | 58.3 | 2.46 | 66.48 | 798 | 127 | 0/0 | 2.11 |
| MGC V1+V2 trend-only (pct8, 1.5R) | 24 | 45.8 | 1.14 | 4.42 | 106 | 235 | 0/0 | 2.13 |
| MGC V3 inside fade (atr, OPP) | 20 | 20.0 | 0.45 | -44.05 | -881 | 1,167 | 0/25.9 | 0.75 |
| MGC V5 combined (pct8, OPP) | 45 | 26.7 | 0.79 | -9.51 | -428 | 604 | 0/0 | 1.56 |

Best HO rows (NOT IS picks, look-ahead selected, shown for hypotheses only): MNQ V5 atr/OPP HO n=32 PF 1.78 win 46.9% $57/tr net 1,832 maxDD 740, roll PASS 92.6 / BUST 0 (median 65 days; 12-month roll 64.9 / 33.3, PF 1.56, n=107; random-side HO PF 1.61); MNQ V3 atr/OPP HO n=18 PF 2.00 roll PASS 74/0 (random 2.12). MGC best HO V1+V2 atr/STRUCT n=24 PF 1.85 (but 12-month PF 0.93, BUST 51%, random 2.17).

## Verdict (plain language)
- **The 80% rule does not hold on this data**: price traversed to the opposite value-area edge 42% of the time on MNQ and 26% on MGC (n=55-57 days), not 80%. The inside-value fade (V3) therefore has no claimed edge; its results come from wide-target payoff geometry, not high accuracy.
- **Open above/below value (V1/V2):** too few trades (MNQ 46 + 22, MGC 39 + 39 in 12 months). V1 (buy above VAH) is positive on MNQ (PF 1.5-2.0, 46-51% win, n=35) but V2 (sell below VAL) loses on MNQ (PF 0.2-0.7); MGC is break-even to negative over 12 months (PF 0.5-1.4). The "random-side at the same level" benchmark scores similar or higher PFs (MNQ 2.0, MGC 2.0+), so the direction rule has no proven edge over random entries at the same levels with the same exits. HO windows hold 4-24 trades.
- **Combined / dropping the fades:** trend-only (V1+V2) is no better than the combined system on MNQ and unreliable on MGC. The combined system on MNQ with ATR stops and the opposite-edge target looks decent (12-month PF 1.56, HO PF 1.78) but its IS-pick (tick stop) yields HO PF 1.36 and random sides give PF 1.5-1.6, and 12-month roll BUST is 33%. MGC: negative or noise in every combined row (PF 0.7-1.1); MGC is also OFF in the plans.
- **Versus NOISE preset C** (HO PF 1.76, 51 trades, 12-month 78% PASS / 21% BUST, PF 1.53): no volume-profile variant beats it on an honest IS-pick basis (best IS-picks: PF 1.3-1.4 with 26-50% win, n 10-33). The article's 55-65% win rate is not reproduced (27-53% typical, never > 65% at n >= 30).
- **Do NOT add as a strategy button.** One year, ~100 trades max, no edge over random-side-at-level.

## Combinations that could work (hypotheses only; need >= 3 years of data, i.e. after Databento is unlocked)
1. **MNQ combined (V1+V2+V3) with ATR stop + opposite-VA-edge / POC target** as a NOISE side filter or secondary (small, 12-mo PF 1.56 n=107; fragile vs random PF 1.6): re-test 2019-2026 with IS-pick/HO-judge and compare to random-side-at-level before anything else.
2. **Use prior-day VAH/VAL/POC as filters / targets inside NOISE** (e.g. skip NOISE longs directly into a prior-day VAH, or open above/below value as the bias for NOISE direction) - 0-2 parameters, tested on the NOISE trade list, not as a separate system.
3. **V1 only (open above VAH, buy the dip)** with PDH/POC target on MNQ: the only directional row consistently positive (PF 1.5-2.0, n=35), but its random benchmark is as good - test on 2019-2026 first.
4. Drop the 80% rule: measured hit rate 26-42%; at most use "touch of VAH/VAL then POC" (V3 STRUCT) as a target idea.


## Full tables (IS = first 8 months, HO = last ~4 months; 'stop=x tgt=y' columns; rand-entry = random side at the same level/exits)

### MNQ
80% rule: {"all": {"days": 57, "hit": 42.1, "med_min": 143.5}, "IS": {"days": 40, "hit": 45.0, "med_min": 102.0}, "HO": {"days": 17, "hit": 35.3, "med_min": 197.0}, "long_from_VAL": {"days": 28, "hit": 39.3, "med_min": 148.0}, "short_from_VAH": {"days": 29, "hit": 44.8, "med_min": 139.0}, "accepted_close_inside": {"days": 28, "hit": 46.4, "med_min": 79.0}}

| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net | HO maxDD | roll PASS/BUST % | med d | 12mo n | 12mo win% | 12mo PF | 12mo net | 12mo PASS/BUST | rand-entry HO PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 above-VAH buy | stop=pct8 tgt=1.5 | 25 | 1.3 | 10 | 60.0 | 2.18 | 37.83 | 378 | 82 | 0.0/0.0 | nan | 35 | 51.4 | 1.52 | 666 | 0.0/0.0 | 1.98 |
| V1 above-VAH buy | stop=pct8 tgt=2.0 | 25 | 1.45 | 10 | 50.0 | 1.94 | 37.65 | 376 | 238 | 0.0/0.0 | nan | 35 | 45.7 | 1.58 | 846 | 0.0/0.0 | 1.81 |
| V1 above-VAH buy | stop=pct8 tgt=STRUCT | 25 | 1.69 | 10 | 50.0 | 2.67 | 67.15 | 672 | 238 | 0.0/0.0 | nan | 35 | 45.7 | 1.96 | 1402 | 0.0/0.0 | 2.0 |
| V1 above-VAH buy | stop=atr tgt=1.5 | 25 | 1.34 | 10 | 60.0 | 2.18 | 64.32 | 643 | 294 | 0.0/0.0 | nan | 35 | 51.4 | 1.55 | 1178 | 18.0/0.0 | 1.19 |
| V1 above-VAH buy | stop=atr tgt=2.0 | 25 | 1.58 | 10 | 60.0 | 2.91 | 104.35 | 1044 | 294 | 0.0/0.0 | nan | 35 | 51.4 | 1.92 | 1977 | 39.6/0.0 | 1.16 |
| V1 above-VAH buy | stop=atr tgt=STRUCT | 25 | 1.4 | 10 | 60.0 | 2.45 | 79.1 | 791 | 294 | 0.0/0.0 | nan | 35 | 51.4 | 1.67 | 1436 | 21.6/0.0 | 1.27 |
| V1 above-VAH buy | stop=tick tgt=1.5 | 25 | 1.31 | 10 | 40.0 | 0.95 | -2.0 | -20 | 222 | 0.0/0.0 | nan | 35 | 45.7 | 1.2 | 230 | 0.0/0.0 | 1.46 |
| V1 above-VAH buy | stop=tick tgt=2.0 | 25 | 1.5 | 10 | 40.0 | 1.27 | 10.0 | 100 | 192 | 0.0/0.0 | nan | 35 | 42.9 | 1.43 | 530 | 0.0/0.0 | 1.87 |
| V1 above-VAH buy | stop=tick tgt=STRUCT | 25 | 1.66 | 10 | 40.0 | 2.24 | 46.0 | 460 | 192 | 0.0/0.0 | nan | 35 | 40.0 | 1.83 | 1076 | 0.0/0.0 | 2.57 |
| V2 below-VAL sell | stop=pct8 tgt=1.5 | 15 | 0.21 | 4 | 25.0 | 0.45 | -33.44 | -134 | 245 | 0.0/0.0 | nan | 19 | 15.8 | 0.26 | -858 | 0.0/0.0 | 22.01 |
| V2 below-VAL sell | stop=pct8 tgt=2.0 | 15 | 0.28 | 4 | 25.0 | 0.61 | -24.0 | -96 | 245 | 0.0/0.0 | nan | 19 | 15.8 | 0.35 | -754 | 0.0/0.0 | 22.55 |
| V2 below-VAL sell | stop=pct8 tgt=STRUCT | 15 | 0.49 | 4 | 0.0 | 0.0 | -80.62 | -322 | 322 | 0.0/0.0 | nan | 19 | 10.5 | 0.36 | -789 | 0.0/0.0 | 0.64 |
| V2 below-VAL sell | stop=atr tgt=1.5 | 15 | 0.46 | 4 | 25.0 | 0.33 | -76.88 | -308 | 462 | 0.0/0.0 | nan | 19 | 26.3 | 0.43 | -1340 | 0.0/5.4 | 2.56 |
| V2 below-VAL sell | stop=atr tgt=2.0 | 15 | 0.37 | 4 | 25.0 | 0.33 | -76.88 | -308 | 462 | 0.0/0.0 | nan | 19 | 21.1 | 0.37 | -1611 | 0.0/7.2 | 3.14 |
| V2 below-VAL sell | stop=atr tgt=STRUCT | 15 | 0.75 | 4 | 25.0 | 0.33 | -76.88 | -308 | 462 | 0.0/0.0 | nan | 19 | 36.8 | 0.65 | -669 | 0.0/0.0 | 0.99 |
| V2 below-VAL sell | stop=tick tgt=1.5 | 15 | 0.22 | 4 | 25.0 | 0.47 | -24.5 | -98 | 186 | 0.0/0.0 | nan | 19 | 15.8 | 0.27 | -728 | 0.0/0.0 | 0.66 |
| V2 below-VAL sell | stop=tick tgt=2.0 | 15 | 0.29 | 4 | 25.0 | 0.63 | -17.0 | -68 | 186 | 0.0/0.0 | nan | 19 | 15.8 | 0.36 | -638 | 0.0/0.0 | 0.87 |
| V2 below-VAL sell | stop=tick tgt=STRUCT | 15 | 0.56 | 4 | 0.0 | 0.0 | -62.0 | -248 | 248 | 0.0/0.0 | nan | 19 | 10.5 | 0.43 | -602 | 0.0/0.0 | 0.02 |
| V1+V2 trend-only | stop=pct8 tgt=1.5 | 40 | 0.77 | 14 | 50.0 | 1.43 | 17.46 | 244 | 246 | 0.0/0.0 | nan | 54 | 38.9 | 0.92 | -191 | 0.0/0.0 | 2.0 |
| V1+V2 trend-only | stop=pct8 tgt=2.0 | 40 | 0.91 | 14 | 42.9 | 1.43 | 20.04 | 280 | 330 | 0.0/0.0 | nan | 54 | 35.2 | 1.04 | 93 | 0.0/0.0 | 2.22 |
| V1+V2 trend-only | stop=pct8 tgt=STRUCT | 40 | 1.13 | 14 | 35.7 | 1.48 | 24.93 | 349 | 330 | 0.0/0.0 | nan | 54 | 33.3 | 1.23 | 614 | 1.8/0.0 | 1.37 |
| V1+V2 trend-only | stop=atr tgt=1.5 | 40 | 0.86 | 14 | 50.0 | 1.33 | 23.98 | 336 | 402 | 0.0/0.0 | nan | 54 | 42.6 | 0.96 | -161 | 1.8/3.6 | 1.16 |
| V1+V2 trend-only | stop=atr tgt=2.0 | 40 | 0.9 | 14 | 50.0 | 1.73 | 52.57 | 736 | 402 | 0.0/0.0 | nan | 54 | 40.7 | 1.08 | 366 | 1.8/2.7 | 1.28 |
| V1+V2 trend-only | stop=atr tgt=STRUCT | 40 | 1.09 | 14 | 50.0 | 1.48 | 34.54 | 484 | 402 | 0.0/0.0 | nan | 54 | 46.3 | 1.19 | 768 | 34.2/0.0 | 1.05 |
| V1+V2 trend-only | stop=tick tgt=1.5 | 40 | 0.76 | 14 | 35.7 | 0.79 | -8.43 | -118 | 408 | 0.0/0.0 | nan | 54 | 35.2 | 0.77 | -498 | 0.0/0.0 | 0.96 |
| V1+V2 trend-only | stop=tick tgt=2.0 | 40 | 0.92 | 14 | 35.7 | 1.06 | 2.29 | 32 | 378 | 0.0/0.0 | nan | 54 | 33.3 | 0.95 | -108 | 0.0/0.0 | 1.23 |
| V1+V2 trend-only | stop=tick tgt=STRUCT | 40 | 1.15 | 14 | 28.6 | 1.34 | 15.14 | 212 | 378 | 0.0/0.0 | nan | 54 | 29.6 | 1.2 | 474 | 1.8/0.0 | 1.37 |
| V3 inside fade | stop=pct8 tgt=1.5 | 44 | 1.2 | 21 | 42.9 | 0.98 | -0.7 | -15 | 290 | 0.0/0.0 | nan | 65 | 44.6 | 1.12 | 324 | 0.0/0.0 | 1.36 |
| V3 inside fade | stop=pct8 tgt=2.0 | 43 | 1.09 | 21 | 38.1 | 1.06 | 3.24 | 68 | 240 | 0.0/0.0 | nan | 64 | 37.5 | 1.08 | 241 | 0.0/0.0 | 1.18 |
| V3 inside fade | stop=pct8 tgt=STRUCT | 43 | 1.17 | 21 | 38.1 | 1.16 | 7.81 | 164 | 243 | 0.0/0.0 | nan | 64 | 40.6 | 1.17 | 468 | 0.0/0.0 | 1.43 |
| V3 inside fade | stop=pct8 tgt=OPP | 37 | 1.71 | 19 | 31.6 | 1.43 | 23.42 | 445 | 319 | 0.0/0.0 | nan | 56 | 30.4 | 1.61 | 1758 | 11.7/0.0 | 1.91 |
| V3 inside fade | stop=atr tgt=1.5 | 44 | 1.75 | 21 | 47.6 | 1.13 | 9.26 | 194 | 530 | 0.0/0.0 | nan | 65 | 50.8 | 1.53 | 2102 | 39.6/0.0 | 1.77 |
| V3 inside fade | stop=atr tgt=2.0 | 42 | 1.69 | 21 | 42.9 | 1.09 | 7.29 | 153 | 428 | 0.0/0.0 | nan | 63 | 44.4 | 1.47 | 2126 | 40.5/0.0 | 1.42 |
| V3 inside fade | stop=atr tgt=STRUCT | 43 | 1.45 | 21 | 52.4 | 1.33 | 21.31 | 448 | 447 | 0.0/0.0 | nan | 64 | 53.1 | 1.41 | 1576 | 3.6/0.0 | 1.66 |
| V3 inside fade | stop=atr tgt=OPP | 35 | 1.93 | 18 | 44.4 | 2.0 | 74.94 | 1349 | 360 | 74.1/0.0 | 64.0 | 53 | 43.4 | 1.95 | 3720 | 52.3/0.0 | 2.12 |
| V3 inside fade | stop=tick tgt=1.5 | 44 | 1.42 | 21 | 38.1 | 0.87 | -4.86 | -102 | 248 | 0.0/0.0 | nan | 65 | 46.2 | 1.22 | 470 | 0.0/0.0 | 1.07 |
| V3 inside fade | stop=tick tgt=2.0 | 44 | 1.27 | 21 | 38.1 | 1.04 | 1.71 | 36 | 248 | 0.0/0.0 | nan | 65 | 40.0 | 1.19 | 466 | 0.0/0.0 | 1.02 |
| V3 inside fade | stop=tick tgt=STRUCT | 43 | 1.25 | 21 | 33.3 | 1.08 | 3.43 | 72 | 310 | 0.0/0.0 | nan | 64 | 37.5 | 1.19 | 480 | 0.0/0.0 | 1.04 |
| V3 inside fade | stop=tick tgt=OPP | 37 | 1.96 | 19 | 26.3 | 1.38 | 17.37 | 330 | 310 | 0.0/0.0 | nan | 56 | 28.6 | 1.76 | 1876 | 11.7/0.0 | 1.62 |
| V5 combined | stop=pct8 tgt=1.5 | 84 | 0.97 | 35 | 45.7 | 1.15 | 6.56 | 230 | 485 | 0.0/0.0 | nan | 119 | 42.0 | 1.03 | 133 | 0.0/0.0 | 1.56 |
| V5 combined | stop=pct8 tgt=2.0 | 83 | 1.0 | 35 | 40.0 | 1.21 | 9.96 | 348 | 485 | 0.0/0.0 | nan | 118 | 36.4 | 1.06 | 334 | 0.0/0.0 | 1.54 |
| V5 combined | stop=pct8 tgt=STRUCT | 83 | 1.15 | 35 | 37.1 | 1.29 | 14.66 | 513 | 556 | 0.0/0.0 | nan | 118 | 37.3 | 1.2 | 1082 | 9.0/0.0 | 1.54 |
| V5 combined | stop=pct8 tgt=OPP | 77 | 1.41 | 33 | 33.3 | 1.45 | 24.06 | 794 | 485 | 3.7/0.0 | 60.0 | 110 | 31.8 | 1.42 | 2371 | 41.4/0.0 | 1.77 |
| V5 combined | stop=atr tgt=1.5 | 84 | 1.23 | 35 | 48.6 | 1.22 | 15.15 | 530 | 816 | 0.0/0.0 | nan | 119 | 47.1 | 1.23 | 1941 | 15.3/59.5 | 1.52 |
| V5 combined | stop=atr tgt=2.0 | 82 | 1.25 | 35 | 45.7 | 1.34 | 25.4 | 889 | 740 | 0.0/0.0 | nan | 117 | 42.7 | 1.27 | 2492 | 19.8/51.4 | 1.59 |
| V5 combined | stop=atr tgt=STRUCT | 83 | 1.25 | 35 | 51.4 | 1.4 | 26.6 | 931 | 742 | 0.0/0.0 | nan | 118 | 50.0 | 1.3 | 2344 | 39.6/34.2 | 1.59 |
| V5 combined | stop=atr tgt=OPP | 75 | 1.47 | 32 | 46.9 | 1.78 | 57.27 | 1832 | 740 | 92.6/0.0 | 65.0 | 107 | 44.9 | 1.56 | 4487 | 64.9/33.3 | 1.61 |
| V5 combined | stop=tick tgt=1.5 | 84 | 1.06 | 35 | 37.1 | 0.84 | -6.29 | -220 | 562 | 0.0/0.0 | nan | 119 | 41.2 | 0.99 | -28 | 0.0/0.0 | 1.01 |
| V5 combined | stop=tick tgt=2.0 | 84 | 1.09 | 35 | 37.1 | 1.05 | 1.94 | 68 | 454 | 0.0/0.0 | nan | 119 | 37.0 | 1.08 | 358 | 0.0/0.0 | 1.1 |
| V5 combined | stop=tick tgt=STRUCT | 83 | 1.2 | 35 | 31.4 | 1.19 | 8.11 | 284 | 478 | 0.0/0.0 | nan | 118 | 33.9 | 1.2 | 954 | 18.9/0.0 | 1.29 |
| V5 combined | stop=tick tgt=OPP | 77 | 1.54 | 33 | 27.3 | 1.36 | 16.42 | 542 | 434 | 0.0/0.0 | nan | 110 | 29.1 | 1.49 | 2350 | 33.3/0.0 | 1.53 |

**IS-pick (best IS PF, IS n>=15) per variant, judged on HO (MNQ)**

| variant | pick | IS n/PF | HO n | win% | PF | $/tr | net | maxDD | PASS/BUST | rand PF |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 above-VAH buy | stop=pct8 / tgt=STRUCT | 25/1.69 | 10 | 50.0 | 2.67 | 67.15 | 672 | 238 | 0.0/0.0 | 2.0 |
| V1+V2 trend-only | stop=tick / tgt=STRUCT | 40/1.15 | 14 | 28.6 | 1.34 | 15.14 | 212 | 378 | 0.0/0.0 | 1.37 |
| V2 below-VAL sell | stop=atr / tgt=STRUCT | 15/0.75 | 4 | 25.0 | 0.33 | -76.88 | -308 | 462 | 0.0/0.0 | 0.99 |
| V3 inside fade | stop=tick / tgt=OPP | 37/1.96 | 19 | 26.3 | 1.38 | 17.37 | 330 | 310 | 0.0/0.0 | 1.62 |
| V5 combined | stop=tick / tgt=OPP | 77/1.54 | 33 | 27.3 | 1.36 | 16.42 | 542 | 434 | 0.0/0.0 | 1.53 |

### MGC
80% rule: {"all": {"days": 55, "hit": 25.5, "med_min": 73.5}, "IS": {"days": 36, "hit": 27.8, "med_min": 138.0}, "HO": {"days": 19, "hit": 21.1, "med_min": 27.5}, "long_from_VAL": {"days": 27, "hit": 22.2, "med_min": 75.0}, "short_from_VAH": {"days": 28, "hit": 28.6, "med_min": 73.5}, "accepted_close_inside": {"days": 34, "hit": 26.5, "med_min": 120.0}}

| variant | IS n | IS PF | HO n | HO win% | HO PF | HO $/tr | HO net | HO maxDD | roll PASS/BUST % | med d | 12mo n | 12mo win% | 12mo PF | 12mo net | 12mo PASS/BUST | rand-entry HO PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 above-VAH buy | stop=pct8 tgt=1.5 | 20 | 1.11 | 12 | 50.0 | 1.33 | 10.02 | 120 | 177 | 0.0/0.0 | nan | 32 | 46.9 | 1.19 | 198 | 0.0/0.0 | 2.06 |
| V1 above-VAH buy | stop=pct8 tgt=2.0 | 20 | 0.81 | 12 | 41.7 | 1.29 | 10.23 | 123 | 177 | 0.0/0.0 | nan | 32 | 34.4 | 0.96 | -48 | 0.0/0.0 | 2.01 |
| V1 above-VAH buy | stop=pct8 tgt=STRUCT | 20 | 0.78 | 12 | 41.7 | 1.27 | 9.32 | 112 | 177 | 0.0/0.0 | nan | 32 | 28.1 | 0.92 | -108 | 0.0/0.0 | 1.36 |
| V1 above-VAH buy | stop=atr tgt=1.5 | 20 | 0.35 | 12 | 41.7 | 1.05 | 3.11 | 37 | 348 | 0.0/0.0 | nan | 32 | 28.1 | 0.53 | -1373 | 0.0/27.0 | 1.94 |
| V1 above-VAH buy | stop=atr tgt=2.0 | 20 | 0.47 | 12 | 41.7 | 1.05 | 2.98 | 36 | 348 | 0.0/0.0 | nan | 32 | 28.1 | 0.62 | -1116 | 0.0/24.3 | 2.09 |
| V1 above-VAH buy | stop=atr tgt=STRUCT | 20 | 0.49 | 12 | 50.0 | 1.15 | 8.15 | 98 | 238 | 0.0/0.0 | nan | 32 | 34.4 | 0.65 | -959 | 0.0/24.3 | 1.39 |
| V1 above-VAH buy | stop=tick tgt=1.5 | 20 | 0.89 | 12 | 41.7 | 0.95 | -1.52 | -18 | 214 | 0.0/0.0 | nan | 32 | 40.6 | 0.91 | -90 | 0.0/0.0 | 1.8 |
| V1 above-VAH buy | stop=tick tgt=2.0 | 20 | 1.2 | 12 | 33.3 | 0.9 | -3.6 | -43 | 214 | 0.0/0.0 | nan | 32 | 37.5 | 1.08 | 85 | 0.0/0.0 | 1.75 |
| V1 above-VAH buy | stop=tick tgt=STRUCT | 20 | 0.55 | 12 | 33.3 | 0.99 | -0.43 | -5 | 214 | 0.0/0.0 | nan | 32 | 25.0 | 0.69 | -394 | 0.0/0.0 | 1.25 |
| V2 below-VAL sell | stop=pct8 tgt=1.5 | 19 | 0.67 | 12 | 41.7 | 0.97 | -1.18 | -14 | 183 | 0.0/0.0 | nan | 31 | 35.5 | 0.77 | -290 | 0.0/0.0 | 2.01 |
| V2 below-VAL sell | stop=pct8 tgt=2.0 | 19 | 0.69 | 12 | 33.3 | 0.9 | -4.1 | -49 | 308 | 0.0/0.0 | nan | 31 | 29.0 | 0.77 | -323 | 0.0/0.0 | 1.96 |
| V2 below-VAL sell | stop=pct8 tgt=STRUCT | 19 | 0.97 | 12 | 33.3 | 1.26 | 10.32 | 124 | 308 | 0.0/0.0 | nan | 31 | 32.3 | 1.07 | 95 | 0.0/0.0 | 4.0 |
| V2 below-VAL sell | stop=atr tgt=1.5 | 19 | 0.77 | 12 | 58.3 | 2.13 | 51.4 | 617 | 127 | 0.0/0.0 | nan | 31 | 41.9 | 1.1 | 230 | 0.0/0.0 | 2.09 |
| V2 below-VAL sell | stop=atr tgt=2.0 | 19 | 1.03 | 12 | 58.3 | 2.46 | 66.48 | 798 | 127 | 0.0/0.0 | nan | 31 | 41.9 | 1.38 | 849 | 0.0/0.0 | 2.11 |
| V2 below-VAL sell | stop=atr tgt=STRUCT | 19 | 0.83 | 12 | 58.3 | 2.67 | 75.9 | 911 | 127 | 0.0/0.0 | nan | 31 | 41.9 | 1.28 | 623 | 0.0/22.5 | 3.34 |
| V2 below-VAL sell | stop=tick tgt=1.5 | 19 | 0.62 | 12 | 41.7 | 0.95 | -1.52 | -18 | 161 | 0.0/0.0 | nan | 31 | 35.5 | 0.74 | -282 | 0.0/0.0 | 1.74 |
| V2 below-VAL sell | stop=tick tgt=2.0 | 19 | 0.34 | 12 | 33.3 | 0.9 | -3.6 | -43 | 268 | 0.0/0.0 | nan | 31 | 22.6 | 0.53 | -607 | 0.0/0.0 | 1.71 |
| V2 below-VAL sell | stop=tick tgt=STRUCT | 19 | 0.4 | 12 | 33.3 | 1.4 | 14.32 | 172 | 268 | 0.0/0.0 | nan | 31 | 25.8 | 0.75 | -309 | 0.0/0.0 | 2.79 |
| V1+V2 trend-only | stop=pct8 tgt=1.5 | 39 | 0.87 | 24 | 45.8 | 1.14 | 4.42 | 106 | 235 | 0.0/0.0 | nan | 63 | 41.3 | 0.96 | -92 | 0.0/0.0 | 2.13 |
| V1+V2 trend-only | stop=pct8 tgt=2.0 | 39 | 0.75 | 24 | 37.5 | 1.08 | 3.07 | 74 | 235 | 0.0/0.0 | nan | 63 | 31.7 | 0.86 | -371 | 0.0/0.0 | 2.17 |
| V1+V2 trend-only | stop=pct8 tgt=STRUCT | 39 | 0.86 | 24 | 37.5 | 1.26 | 9.82 | 236 | 235 | 0.0/0.0 | nan | 63 | 30.2 | 1.0 | -13 | 0.0/0.0 | 2.78 |
| V1+V2 trend-only | stop=atr tgt=1.5 | 39 | 0.53 | 24 | 50.0 | 1.51 | 27.25 | 654 | 348 | 0.0/0.0 | nan | 63 | 34.9 | 0.78 | -1142 | 0.0/54.1 | 1.82 |
| V1+V2 trend-only | stop=atr tgt=2.0 | 39 | 0.71 | 24 | 50.0 | 1.65 | 34.73 | 834 | 348 | 0.0/0.0 | nan | 63 | 34.9 | 0.95 | -267 | 0.0/48.6 | 1.98 |
| V1+V2 trend-only | stop=atr tgt=STRUCT | 39 | 0.64 | 24 | 54.2 | 1.85 | 42.02 | 1009 | 257 | 14.8/0.0 | 65.0 | 63 | 38.1 | 0.93 | -336 | 3.6/51.4 | 2.17 |
| V1+V2 trend-only | stop=tick tgt=1.5 | 39 | 0.75 | 24 | 41.7 | 0.95 | -1.52 | -36 | 286 | 0.0/0.0 | nan | 63 | 38.1 | 0.82 | -372 | 0.0/0.0 | 1.82 |
| V1+V2 trend-only | stop=tick tgt=2.0 | 39 | 0.71 | 24 | 33.3 | 0.9 | -3.6 | -86 | 311 | 0.0/0.0 | nan | 63 | 30.2 | 0.78 | -522 | 0.0/0.0 | 1.86 |
| V1+V2 trend-only | stop=tick tgt=STRUCT | 39 | 0.48 | 24 | 33.3 | 1.19 | 6.94 | 167 | 268 | 0.0/0.0 | nan | 63 | 25.4 | 0.72 | -703 | 0.0/0.0 | 2.19 |
| V3 inside fade | stop=pct8 tgt=1.5 | 34 | 1.2 | 22 | 36.4 | 0.78 | -8.42 | -185 | 297 | 0.0/0.0 | nan | 56 | 42.9 | 1.03 | 55 | 0.0/0.0 | 1.34 |
| V3 inside fade | stop=pct8 tgt=2.0 | 34 | 1.07 | 21 | 28.6 | 0.74 | -11.36 | -239 | 239 | 0.0/0.0 | nan | 55 | 34.5 | 0.94 | -136 | 0.0/0.0 | 1.09 |
| V3 inside fade | stop=pct8 tgt=STRUCT | 32 | 0.92 | 22 | 22.7 | 0.24 | -35.46 | -780 | 780 | 0.0/0.0 | nan | 54 | 29.6 | 0.63 | -894 | 0.0/0.0 | 0.79 |
| V3 inside fade | stop=pct8 tgt=OPP | 32 | 1.48 | 21 | 14.3 | 0.4 | -31.6 | -664 | 742 | 0.0/0.0 | nan | 53 | 20.8 | 1.04 | 108 | 0.0/0.0 | 0.68 |
| V3 inside fade | stop=atr tgt=1.5 | 34 | 1.35 | 21 | 33.3 | 0.72 | -19.41 | -408 | 607 | 0.0/0.0 | nan | 55 | 43.6 | 1.11 | 429 | 12.6/0.0 | 1.3 |
| V3 inside fade | stop=atr tgt=2.0 | 34 | 1.63 | 20 | 25.0 | 0.73 | -20.1 | -402 | 722 | 0.0/0.0 | nan | 54 | 38.9 | 1.29 | 1169 | 42.3/0.0 | 1.37 |
| V3 inside fade | stop=atr tgt=STRUCT | 32 | 1.13 | 22 | 27.3 | 0.22 | -58.69 | -1291 | 1413 | 0.0/66.7 | nan | 54 | 42.6 | 0.74 | -1009 | 0.0/39.6 | 0.95 |
| V3 inside fade | stop=atr tgt=OPP | 29 | 1.83 | 20 | 20.0 | 0.45 | -44.05 | -881 | 1167 | 0.0/25.9 | nan | 49 | 34.7 | 1.26 | 1009 | 40.5/36.9 | 0.75 |
| V3 inside fade | stop=tick tgt=1.5 | 34 | 1.05 | 22 | 36.4 | 0.76 | -8.15 | -179 | 250 | 0.0/0.0 | nan | 56 | 41.1 | 0.93 | -127 | 0.0/0.0 | 1.35 |
| V3 inside fade | stop=tick tgt=2.0 | 34 | 1.42 | 21 | 28.6 | 0.72 | -10.74 | -226 | 226 | 0.0/0.0 | nan | 55 | 38.2 | 1.11 | 202 | 0.0/0.0 | 1.36 |
| V3 inside fade | stop=tick tgt=STRUCT | 32 | 1.15 | 22 | 22.7 | 0.28 | -29.96 | -659 | 659 | 0.0/0.0 | nan | 54 | 29.6 | 0.76 | -489 | 0.0/0.0 | 0.89 |
| V3 inside fade | stop=tick tgt=OPP | 33 | 1.06 | 21 | 14.3 | 0.45 | -25.27 | -531 | 643 | 0.0/0.0 | nan | 54 | 16.7 | 0.82 | -437 | 0.0/0.0 | 0.78 |
| V5 combined | stop=pct8 tgt=1.5 | 73 | 1.02 | 46 | 41.3 | 0.95 | -1.72 | -79 | 410 | 0.0/0.0 | nan | 119 | 42.0 | 0.99 | -37 | 0.0/0.0 | 1.69 |
| V5 combined | stop=pct8 tgt=2.0 | 73 | 0.89 | 45 | 33.3 | 0.91 | -3.67 | -165 | 360 | 0.0/0.0 | nan | 118 | 33.1 | 0.9 | -507 | 0.0/0.0 | 1.55 |
| V5 combined | stop=pct8 tgt=STRUCT | 71 | 0.89 | 46 | 30.4 | 0.72 | -11.84 | -545 | 564 | 0.0/0.0 | nan | 117 | 29.9 | 0.82 | -907 | 0.0/0.0 | 1.64 |
| V5 combined | stop=pct8 tgt=OPP | 71 | 1.15 | 45 | 26.7 | 0.79 | -9.51 | -428 | 604 | 0.0/0.0 | nan | 116 | 25.9 | 1.02 | 95 | 6.3/17.1 | 1.56 |
| V5 combined | stop=atr tgt=1.5 | 73 | 0.85 | 45 | 42.2 | 1.09 | 5.48 | 246 | 506 | 0.0/0.0 | nan | 118 | 39.0 | 0.92 | -713 | 6.3/44.1 | 1.57 |
| V5 combined | stop=atr tgt=2.0 | 73 | 1.07 | 44 | 38.6 | 1.15 | 9.81 | 432 | 600 | 0.0/0.0 | nan | 117 | 36.8 | 1.1 | 902 | 40.5/8.1 | 1.51 |
| V5 combined | stop=atr tgt=STRUCT | 71 | 0.82 | 46 | 41.3 | 0.9 | -6.14 | -283 | 671 | 0.0/0.0 | nan | 117 | 40.2 | 0.85 | -1345 | 4.5/53.2 | 1.45 |
| V5 combined | stop=atr tgt=OPP | 68 | 1.09 | 44 | 38.6 | 1.05 | 2.9 | 128 | 838 | 0.0/0.0 | nan | 112 | 36.6 | 1.08 | 673 | 11.7/55.9 | 1.37 |
| V5 combined | stop=tick tgt=1.5 | 73 | 0.88 | 46 | 39.1 | 0.86 | -4.69 | -216 | 519 | 0.0/0.0 | nan | 119 | 39.5 | 0.87 | -498 | 0.0/0.0 | 1.66 |
| V5 combined | stop=tick tgt=2.0 | 73 | 1.0 | 45 | 31.1 | 0.81 | -6.93 | -312 | 430 | 0.0/0.0 | nan | 118 | 33.9 | 0.92 | -320 | 0.0/0.0 | 1.59 |
| V5 combined | stop=tick tgt=STRUCT | 71 | 0.75 | 46 | 28.3 | 0.72 | -10.71 | -493 | 536 | 0.0/0.0 | nan | 117 | 27.4 | 0.74 | -1192 | 0.0/0.0 | 1.58 |
| V5 combined | stop=tick tgt=OPP | 72 | 0.75 | 45 | 24.4 | 0.8 | -8.09 | -364 | 467 | 0.0/0.0 | nan | 117 | 21.4 | 0.77 | -1140 | 0.0/27.0 | 1.45 |

**IS-pick (best IS PF, IS n>=15) per variant, judged on HO (MGC)**

| variant | pick | IS n/PF | HO n | win% | PF | $/tr | net | maxDD | PASS/BUST | rand PF |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 above-VAH buy | stop=tick / tgt=2.0 | 20/1.2 | 12 | 33.3 | 0.9 | -3.6 | -43 | 214 | 0.0/0.0 | 1.75 |
| V1+V2 trend-only | stop=pct8 / tgt=1.5 | 39/0.87 | 24 | 45.8 | 1.14 | 4.42 | 106 | 235 | 0.0/0.0 | 2.13 |
| V2 below-VAL sell | stop=atr / tgt=2.0 | 19/1.03 | 12 | 58.3 | 2.46 | 66.48 | 798 | 127 | 0.0/0.0 | 2.11 |
| V3 inside fade | stop=atr / tgt=OPP | 29/1.83 | 20 | 20.0 | 0.45 | -44.05 | -881 | 1167 | 0.0/25.9 | 0.75 |
| V5 combined | stop=pct8 / tgt=OPP | 71/1.15 | 45 | 26.7 | 0.79 | -9.51 | -428 | 604 | 0.0/0.0 | 1.56 |

NOISE preset C (MNQ): HO {"n": 51, "win": 51.0, "pf": 1.76, "avg": 57.38, "net": 2926, "dd": 977, "passp": 100.0, "bust": 0.0, "med": 48.0} | 12mo {"n": 149, "win": 55.0, "pf": 1.53, "avg": 39.31, "net": 5857, "dd": 1096, "passp": 78.4, "bust": 20.7, "med": 45.0}
