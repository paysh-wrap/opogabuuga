# Session 18 - ICT + SMC + Triple RSI + DMI: separate vs COMBINED (MNQ + MGC, Lucid Pro 25K / 50K / 100K / 150K, last 12 months only)

Research only. Everything is under `docs/results/session18/combined/` (no app code, no git, no download - Databento locked; cached MNQ.v.0 1m + MGC.v.0 1m CSVs).
Reproduce: `MKT=MNQ python3 -I cands.py; MKT=MGC python3 -I cands.py; python3 -I repro.py; python3 -I run.py; python3 -I report.py; python3 -I build_results.py` (numpy + pandas, ~2 min).
**One year is a small sample.** The judge window is 98 business days (~4 months): 22-200 trades per row, only 26 overlapping eval starts per row, so every PASS/BUST number moves in steps of ~4 points and nothing below is proof.

## 1. Verdict in plain language
- **None of the four strategies works on its own over the last 12 months once costs, a 2-micro cap and the app's day rules are applied**, and none comes near NOISE preset C. On the 25K account (judge window, last 4 months): ICT PF 0.61 (27 trades), SMC PF 0.80 (102), DMI PF 0.94 (133), Triple RSI PF 1.05 (190), against NOISE preset C PF 1.76 (51 trades, +$57/trade). Over the full 12 months: ICT 1.03, SMC 1.09, DMI 1.07, RSI 1.13, NOISE 1.53. Win rates are low for the trend/reversal-limit strategies (ICT 30%, SMC 31%, DMI 32% in the judge window; they rely on payoff 1.4-2.0) and 46% for Triple RSI with its 1.5R target (payoff 1.2).
- **Combining them in one account ("first signal wins") is the only version that is positive in both windows, but the gain is not what it looks like.** COMB-1 (all four scan at the same time, first signal wins): judge window 199 trades, 40% win, PF 1.16, payoff 1.72, +$14.9/trade, +$2,965, max DD $2,418; 12 months 564 trades, PF 1.18, +$10,383. It beats the random-direction benchmark (same entries/stops/exits, random side; PF 0.89 / 0.96) in 19 of 20 and 20 of 20 seeds, so the direction information is real. But (a) **about 70% of the 12-month profit is Triple RSI on MGC (+$7.5k of +$10.4k)**; MNQ trades as a whole are break-even to negative (judge window MNQ PF 0.71, 12 months PF 0.98) and MGC is OFF in the app plans; (b) **the combination is mostly two strategies**: with a 3-trade/day budget and one position, the high-frequency RSI (274 trades) and DMI (247) use the slots; SMC got 34 and ICT 9 of the 564 trades; (c) PASS/BUST is no better than NOISE: 25K rolling 46/54 (judge) and 35/65 (12 months) vs NOISE 46/54 and 53/46; bootstrap 37/63 vs 60/40 (strict MAE bust).
- **Arbitration matters, and the in-sample ranking did not carry over.** Priority/gating by in-sample PF (keep only SMC + ICT, the two with IS PF >= 1.2): IS PF 1.36 -> judge PF 0.81 (loses, 0/100 PASS/BUST at 25K). Vote (>= 2 strategies agree within 30 min, none opposing): IS PF 1.61 on 36 trades -> judge PF 0.58 on 22 trades (12 months PF 1.14 on 58 trades; too few to say anything; evals are very slow, median 66-96 days). First signal with <= 1 trade/day per strategy and market: PF 1.00 in the judge window (net $9). So "more strategies scanning" did not give a reliable edge; the best-looking mix (COMB-1) is mainly diversification of RSI + DMI.
- **Bigger accounts do not rescue it.** 50K (cap 2 micros, target $3,000): COMB-1 +$5,078 in the judge window but PASS/BUST 15/85. 100K / 150K (cap = plan max 60 / 100 micros; the 25%-of-MLL risk budget is the binding limit, average 3.5 / 5.6 micros, max 26 / 39): COMB-1 judge window +$9.1k / +$15.0k but max DD $8.2k / $12.7k and BUST 96% (PASS 4%); with the 2-micro cap on a 150K account BUST drops to 69% but profit to +$6.4k. NOISE preset C with its own size table (2 / 3 micros) is PASS 19 / BUST 0 in the same window. More contracts amplify a PF of ~1.15, they do not create margin of safety.
- **Do not build any of this as a live strategy on this evidence.** If anything: paper/SHADOW only, Triple RSI with a 1.5R target (all four 5m/15m variants are PF 1.01-1.13 in IS and 1.02-1.21 in the judge window; the IS pick TriRSI(3,7,14) 15m is 1.13 / 1.13 / 1.13 for IS / judge / 12 months, carried by the MGC leg: MGC IS 1.16 and judge 1.28, MNQ IS 0.81 and judge 0.93), and treat COMB-1 as "RSI + DMI on gold", not as a four-strategy confluence.

## 2. What was run (and where the spec was silent, what I assumed)
**Window / protocol.** Last 12 months only: 2025-11-06..2026-11-05 (MNQ cache ends 2026-11-05; MGC trimmed to the same last day in every portfolio number; the reproduction check below uses each study's own window). Pick on the first ~8 months (IS 2025-11-06..2026-06-30), judge on the last ~4 months (HO 2026-07-01..2026-11-05); the full 12 months are reported as well. Indicators warm up from 2025-09-01.

**Strategy definitions = the existing session-18 studies, code copied (cands.py), parameters unchanged; reproduced first (section 3).**
- **ICT** (`new_ict`): sweep of prior-day/session/5-bar-swing liquidity -> market-structure shift with displacement (>= 1 x ATR14) -> limit at the midpoint of the 1m fair-value gap, stop = sweep extreme +-1 tick, target 1.5R or 2R, setups only inside AM 10:00-11:00 / PM 14:00-15:00 ET (London 03:00-04:00 dropped: negative in the study and not RTH), time exit 60 min after the window but never later than 15:59. Max 1 trade/day per market. Variants: PM or AM+PM x 1.5R/2R.
- **SMC** (`smc` family C = "SuperTrend with FVG"): liquidity sweep + FVG limit at the gap midpoint (window 6 bars), only when SuperTrend(10,3) of the last closed 15m bar agrees; optional EMA200 side; 1m or 5m entry timeframe; 1.5R / 2R; signal window 09:35-15:30. 8 variants.
- **RSI** (`rsi_dmi` family A): three Wilder RSIs (2|3, 7, 14) all < 10/30/40 -> long, all > 90/70/60 -> short, 5m or 15m; exit RSI(2) crossing 50 ("mr") or 1.5R; stop 2 x ATR14 (cap $250). 8 variants (1m dropped: cost machine in the study).
- **DMI** (`rsi_dmi` family B): DMI(14), ADX > 20/25 and rising; exit on the DI flip (stop $250 cap) or 1.5R / 2R; 5m or 15m. 12 variants.
- Markets: MNQ (tick 0.25, $2/pt, fee $1.00 RT; stop 4-124 pt) and MGC (tick 0.10, $10/pt, fee $1.60 RT, stop 1.6-25 pt = the $250/micro cap; ICT min stop 1.6 pt). 1 tick slippage on every fill; stop first inside a bar; closed bars only; ICT keeps its conservative "1 tick of penetration to fill" rule. ICT/SMC/RSI/DMI session windows exactly as in the studies (RSI/DMI on MGC may enter from 03:05 ET like `rsi_dmi`; ICT/SMC only 09:35+ / 10-11 / 14-15).
- **IS pick (fixed in advance):** per strategy, the variant with the highest IS profit factor (1 micro, MNQ+MGC pooled, one position at a time) with >= 25 (ICT, SMC) or >= 30 (RSI, DMI) IS trades. Picks and their IS-vs-judge behaviour are in section 4; the priority order for arbitration is the rank by that IS PF.

**Account model (one Lucid Pro account, both markets).**
- **Max ONE open position per account**, across MNQ and MGC (CLAUDE.md non-negotiable 7). All four strategies keep scanning while a position is open; a signal (or limit fill) that arrives while the account is busy is dropped (no queue). Same-minute ties go to the higher in-sample-PF strategy.
- **Hedge lock (EQUITY_INDEX / METALS):** a single account with one position can never hold opposite directions in a group, so the lock is satisfied by construction. I count the signals that WOULD have been opposite-direction in the same group while a position was open ("would-be vetoes", e.g. 342 in COMB-1 over 12 months) - information only. Cross-account household locking is not modelled (one account at a time).
- **Size ("two micros total" on 25K/50K):** contracts n = max(1, min(cap, floor(budget / per-micro risk))), per-micro risk = stop distance in $ + fee + 1 tick slippage, budget = 25% of the plan's MLL (the NOISE convention: 1 micro x $250 stop on the 25K = 25% of $1,000). **25K and 50K: cap 2 micros (your rule). 100K and 150K: cap = the plan's `max_contracts.micros` from the Pro yaml = 60 and 100** (the app's own `internal_max_micros` is 40 / 60; the 25% risk budget is what actually limits size: average ~3.5 / 5.6 micros in COMB-1). So "two micros" = ONE position of up to 2 micros, never two positions. P&L and MAE scale linearly with n (assumes micros fill like 1 lot even at 20+ lots - optimistic on the big accounts).
- **Day rules (plan yaml `internal`, same for separate and combined):** max 3 trades/day, day stop after 2 consecutive losses, soft DLL where the Pro eval has one (25K: none; 50K $1,200; 100K $1,800; 150K $2,700) with the $40 margin (size reduced to fit, else skip). Flat by 15:59 ET (your 16:00 rule; app hard flat is 16:44). Sensitivity without day rules and with other budgets in section 7.
- **Eval simulator = the session-17 `sim.py` logic, generalised to the plan:** Pro eval target 1,250 / 3,000 / 6,000 / 9,000, EOD-trailing MLL 1,000 / 2,000 / 3,000 / 4,500 locking at start+100 once the EOD peak >= start+MLL+100, no consistency rule and pass-in-one-day allowed (Pro eval, yaml), 120-session horizon, days without trades count as sessions. **BUST = strict**: the worst open loss (MAE) of a trade is checked against the floor (the "seq" read that only checks closed-trade balance is also given in section 6; the older studies' headline numbers are "seq"). "Rolling" = a start every 2nd business day inside the window (26 starts judge, 111 starts 12 months; the remainder is still OPEN); "bootstrap" = 600 paths of 10-session blocks from the 12 months, cut at 500 sessions. Median days = median business days of the passes.
- **Consistency:** Pro eval has none (yaml), so it is not a gate; the funded payout rule (largest day / cycle profit <= 40%) is reported as information in section 6. **News blackout: not modelled** (no calendar in the sandbox; Pro firm rules allow news in the eval; a CPI/FOMC 14:00-15:00 ICT trade is not filtered).
- **Benchmarks:** NOISE preset C = the session-17 stream (`BASE__lock_.csv`, MNQ only) for the same window, scaled by the app size table (1 / 2 / 2 / 3 micros on 25K / 50K / 100K / 150K, no brake). Random benchmark = identical entry bars, stop distances, targets and exit rules but a random side per candidate (20 seeds, run through the same account rules); "real net beats random" = number of seeds the real net is above.
- **Combined variants:** COMB-1 first signal wins (chronological; ties by IS-PF rank). COMB-2 IS-PF gated priority: only strategies with IS PF >= 1.2 (SMC + ICT; rule is "at least the top 2"), ties by rank. COMB-3 vote: a candidate is taken only if another strategy raised a same-market same-side candidate in the previous 30 minutes and none raised the opposite side (the completing signal's own stop/target/exit are used). COMB-4 = COMB-1 with at most 1 trade per strategy per market per day (stops RSI/DMI from eating the 3-slot day budget).
- Not tested: order-flow confirmation, news filtering, MES/MYM, Evaluation Mode sizing, funded/live stage, multi-account hedge interaction.

## 3. Reproduction of the separate numbers on this window
Single strategy, 1 micro, own position only, no day rules (the studies' convention), 12-month window.
- **RSI / DMI:** 40 of 40 (variant x market) rows identical to `rsi_dmi/out/results_MNQ|MGC.json` (IS n, IS PF, judge n, judge net). Full list: `out/repro.md`.
- **SMC family C (MNQ):** 8 of 8 variants identical (trades, net $, PF) to the `smc/out` streams sliced to the window (e.g. 5m+ST15+EMA200 R2.0: 151 trades, +$1,366, PF 1.16). MGC was not run in the original smc study (new here).
- **ICT (MNQ):** the original had no 12-month table; its per-year table gives 2026 (to 11-05) AM+PM 2R untuned = 71 trades / +$7.4 per trade / PF 1.16 and PM 2R = 42 / +$3.2 / 1.07. With the original time exit (may run to the 16:00 bar close) my port gives exactly 71 / 7.4 / 1.16 and 42 / 3.2 / 1.07. In this study the time exit is capped at 15:59 (flat rule) and the same trades give 71 / +$9.3 / 1.20 and 42 / +$6.4 / 1.15. MGC ICT is new.

## 4. In-sample picks (1 micro, MNQ + MGC pooled) and how they held
| strategy | picked variant (best IS PF, IS n >= 25/30) | IS n / PF | HO n / PF / net $ | 12m n / PF / net $ | priority |
|---|---|---|---|---|---|
| ICT | PM 1.5R | 66 / 1.28 | 27 / 0.66 / -415 | 93 / 1.05 / 174 | 2 |
| SMC | 5m+ST15+EMA200 R2.0 | 161 / 1.42 | 106 / 0.78 / -1,311 | 267 / 1.14 / 1,864 | 1 |
| DMI | DMI adx>25 15m flip | 277 / 1.13 | 145 / 0.86 / -2,425 | 422 / 1.03 / 1,410 | 3 |
| RSI | TriRSI3 15m 1.5 | 377 / 1.13 | 214 / 1.13 / 2,523 | 591 / 1.13 / 7,345 | 4 |

The pick is chosen among 4-12 variants per strategy on ~8 months, so it is the best of several noisy numbers: three of the four picks fell in the judge window (ICT 1.28 -> 0.66, SMC 1.42 -> 0.78, DMI 1.13 -> 0.86), only Triple RSI held (1.13 -> 1.13). Full variant table (IS | judge | 12 months) in section 9.

## 5. Results per account (own strategy alone vs combined)
Columns: trades, win %, profit factor, avg win / avg loss (payoff), $ per trade, net, max drawdown of closed trades, rolling-start eval PASS / BUST % (strict MAE bust, remainder OPEN), median business days to pass, per-market n / net $ / PF, random-direction benchmark, and how many of 20 random seeds the real net beat. 25K and 50K: cap 2 micros. 100K / 150K: cap = plan max micros (60 / 100), budget 25% of MLL.

#### Pro 25K - last ~4 months (2026-07-01..2026-11-05) = JUDGE window
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 51 | 51.0 | 1.76 | 1.69 | 57.4 | 2,926 | 977 | 46 / 54 (26 starts) | 34 | 51 / 2,926 / 1.76 | 0 | - | - |
| ICT | 27 | 29.6 | 0.61 | 1.44 | -31.5 | -851 | 1,167 | 0 / 65 (26 starts) | - | 14 / -597 / 0.50 | 13 / -254 / 0.74 | 0.80 / -19 / 1/62 | 8/20 |
| SMC | 102 | 31.4 | 0.80 | 1.74 | -18.7 | -1,912 | 3,682 | 8 / 92 (26 starts) | 15 | 49 / 168 / 1.04 | 53 / -2,080 / 0.57 | 0.77 / -22 / 0/100 | 13/20 |
| DMI | 133 | 31.6 | 0.94 | 2.04 | -6.6 | -874 | 4,119 | 31 / 69 (26 starts) | 6 | 40 / -1,303 / 0.78 | 93 / 429 / 1.05 | 1.08 / 6 / 47/53 | 8/20 |
| RSI | 190 | 46.3 | 1.05 | 1.21 | 4.4 | 831 | 3,550 | 12 / 88 (26 starts) | 6 | 47 / -770 / 0.86 | 143 / 1,601 / 1.12 | 1.02 / 1 / 30/70 | 13/20 |
| COMB-1 first signal | 199 | 40.2 | 1.16 | 1.72 | 14.9 | 2,965 | 2,418 | 46 / 54 (26 starts) | 9 | 41 / -1,473 / 0.71 | 158 / 4,438 / 1.32 | 0.89 / -12 / 18/82 | 19/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 116 | 33.6 | 0.81 | 1.60 | -17.1 | -1,983 | 3,669 | 0 / 100 (26 starts) | - | 57 / -434 / 0.92 | 59 / -1,549 / 0.69 | 0.76 / -23 / 4/96 | 12/20 |
| COMB-3 vote >=2 | 22 | 36.4 | 0.58 | 1.02 | -41.0 | -902 | 1,032 | 0 / 4 (26 starts) | - | 12 / -566 / 0.51 | 10 / -336 / 0.67 | 0.74 / -27 / 0/24 | 6/20 |
| COMB-4 first, <=1/day/strat | 185 | 35.7 | 1.00 | 1.80 | 0.1 | 9 | 3,397 | 46 / 54 (26 starts) | 13 | 47 / -400 / 0.93 | 138 / 409 / 1.03 | 0.87 / -14 / 17/83 | 17/20 |

#### Pro 25K - full 12 months (2025-11-06..2026-11-05)
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 149 | 55.0 | 1.53 | 1.25 | 39.3 | 5,857 | 1,096 | 53 / 46 (111 starts) | 38 | 149 / 5,857 / 1.53 | 0 | - | - |
| ICT | 93 | 43.0 | 1.03 | 1.37 | 2.1 | 191 | 1,667 | 19 / 52 (111 starts) | 102 | 49 / -190 / 0.94 | 44 / 382 / 1.15 | 1.00 / -1 / 20/50 | 13/20 |
| SMC | 258 | 35.7 | 1.09 | 1.97 | 7.6 | 1,960 | 3,682 | 19 / 81 (111 starts) | 14 | 135 / 1,890 / 1.16 | 123 / 71 / 1.01 | 0.83 / -16 / 9/91 | 20/20 |
| DMI | 388 | 33.5 | 1.07 | 2.12 | 7.6 | 2,967 | 5,127 | 29 / 71 (111 starts) | 7 | 121 / 3,202 / 1.24 | 267 / -235 / 0.99 | 0.97 / -4 / 30/70 | 16/20 |
| RSI | 522 | 46.6 | 1.13 | 1.30 | 13.5 | 7,028 | 3,550 | 43 / 57 (111 starts) | 9 | 139 / -2,392 / 0.85 | 383 / 9,420 / 1.26 | 0.98 / -2 / 27/73 | 19/20 |
| COMB-1 first signal | 564 | 40.1 | 1.18 | 1.76 | 18.4 | 10,383 | 3,190 | 35 / 65 (111 starts) | 6 | 140 / -362 / 0.98 | 424 / 10,746 / 1.26 | 0.96 / -5 / 24/76 | 20/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 313 | 39.6 | 1.13 | 1.73 | 10.6 | 3,324 | 3,889 | 29 / 71 (111 starts) | 13 | 160 / 1,662 / 1.12 | 153 / 1,662 / 1.15 | 0.89 / -11 / 19/81 | 20/20 |
| COMB-3 vote >=2 | 58 | 41.4 | 1.14 | 1.61 | 11.4 | 664 | 1,032 | 43 / 28 (111 starts) | 66 | 34 / 1,772 / 1.73 | 24 / -1,109 / 0.52 | 0.99 / -3 / 19/46 | 13/20 |
| COMB-4 first, <=1/day/strat | 543 | 37.9 | 1.14 | 1.86 | 14.2 | 7,690 | 5,329 | 47 / 53 (111 starts) | 10 | 170 / -700 / 0.96 | 373 / 8,390 / 1.23 | 0.96 / -5 / 24/76 | 20/20 |

#### Pro 50K - last ~4 months (2026-07-01..2026-11-05) = JUDGE window
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 51 | 51.0 | 1.76 | 1.69 | 114.8 | 5,853 | 1,954 | 46 / 54 (26 starts) | 38 | 51 / 5,853 / 1.76 | 0 | - | - |
| ICT | 27 | 29.6 | 0.66 | 1.57 | -30.8 | -831 | 1,471 | 0 / 0 (26 starts) | - | 14 / -439 / 0.68 | 13 / -392 / 0.65 | 0.91 / -15 / 0/20 | 8/20 |
| SMC | 102 | 31.4 | 0.79 | 1.73 | -23.9 | -2,437 | 4,968 | 0 / 100 (26 starts) | - | 49 / -437 / 0.93 | 53 / -2,000 / 0.62 | 0.78 / -27 / 0/91 | 12/20 |
| DMI | 133 | 31.6 | 0.90 | 1.94 | -16.4 | -2,177 | 7,520 | 0 / 100 (26 starts) | - | 40 / -2,606 / 0.78 | 93 / 429 / 1.05 | 1.09 / 11 / 41/59 | 4/20 |
| RSI | 190 | 46.3 | 1.03 | 1.20 | 6.1 | 1,157 | 7,238 | 12 / 85 (26 starts) | 9 | 47 / -1,539 / 0.86 | 143 / 2,696 / 1.11 | 1.03 / 4 / 25/75 | 11/20 |
| COMB-1 first signal | 199 | 40.2 | 1.17 | 1.75 | 25.5 | 5,078 | 4,206 | 15 / 85 (26 starts) | 22 | 41 / -2,109 / 0.77 | 158 / 7,188 / 1.36 | 0.90 / -18 / 12/88 | 19/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 116 | 33.6 | 0.79 | 1.56 | -23.1 | -2,675 | 5,336 | 0 / 100 (26 starts) | - | 57 / -1,206 / 0.84 | 59 / -1,469 / 0.73 | 0.78 / -25 / 0/91 | 9/20 |
| COMB-3 vote >=2 | 22 | 36.4 | 0.54 | 0.94 | -62.4 | -1,373 | 1,503 | 0 / 0 (26 starts) | - | 12 / -1,056 / 0.41 | 10 / -317 / 0.73 | 0.79 / -32 / 0/4 | 5/20 |
| COMB-4 first, <=1/day/strat | 185 | 35.7 | 1.02 | 1.84 | 3.0 | 550 | 5,991 | 12 / 88 (26 starts) | 28 | 47 / -537 / 0.95 | 138 / 1,087 / 1.06 | 0.90 / -18 / 6/94 | 18/20 |

#### Pro 50K - full 12 months (2025-11-06..2026-11-05)
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 149 | 55.0 | 1.53 | 1.25 | 78.6 | 11,714 | 2,191 | 49 / 47 (111 starts) | 40 | 149 / 11,714 / 1.53 | 0 | - | - |
| ICT | 93 | 43.0 | 1.05 | 1.39 | 3.7 | 348 | 2,118 | 0 / 9 (111 starts) | - | 49 / 97 / 1.03 | 44 / 251 / 1.09 | 1.04 / 1 / 2/13 | 11/20 |
| SMC | 258 | 35.7 | 1.16 | 2.09 | 15.9 | 4,108 | 4,968 | 41 / 58 (111 starts) | 54 | 135 / 3,010 / 1.20 | 123 / 1,098 / 1.10 | 0.83 / -19 / 4/92 | 20/20 |
| DMI | 388 | 33.5 | 1.11 | 2.21 | 15.9 | 6,170 | 7,520 | 25 / 75 (111 starts) | 17 | 121 / 6,405 / 1.24 | 267 / -235 / 0.99 | 0.99 / -2 / 24/76 | 17/20 |
| RSI | 522 | 46.6 | 1.12 | 1.28 | 21.3 | 11,094 | 7,238 | 37 / 61 (111 starts) | 13 | 139 / -4,874 / 0.85 | 383 / 15,968 / 1.26 | 0.99 / -2 / 25/75 | 19/20 |
| COMB-1 first signal | 564 | 40.1 | 1.22 | 1.82 | 33.4 | 18,824 | 4,206 | 38 / 62 (111 starts) | 16 | 140 / 1,081 / 1.04 | 424 / 17,743 / 1.31 | 0.98 / -4 / 23/77 | 20/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 313 | 39.6 | 1.19 | 1.81 | 18.2 | 5,692 | 5,486 | 27 / 73 (111 starts) | 41 | 160 / 2,808 / 1.16 | 153 / 2,884 / 1.22 | 0.91 / -10 / 11/86 | 19/20 |
| COMB-3 vote >=2 | 58 | 41.4 | 1.24 | 1.76 | 26.8 | 1,557 | 1,503 | 33 / 0 (111 starts) | 88 | 34 / 3,037 / 1.91 | 24 / -1,480 / 0.52 | 1.12 / 7 / 10/21 | 14/20 |
| COMB-4 first, <=1/day/strat | 543 | 37.9 | 1.15 | 1.88 | 24.3 | 13,180 | 7,899 | 34 / 66 (111 starts) | 16 | 170 / 370 / 1.01 | 373 / 12,811 / 1.26 | 0.98 / -3 / 20/80 | 18/20 |

#### Pro 100K - last ~4 months (2026-07-01..2026-11-05) = JUDGE window
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 51 | 51.0 | 1.76 | 1.69 | 114.8 | 5,853 | 1,954 | 19 / 0 (26 starts) | 70 | 51 / 5,853 / 1.76 | 0 | - | - |
| ICT | 27 | 29.6 | 0.59 | 1.40 | -194.7 | -5,256 | 6,883 | 0 / 100 (26 starts) | - | 14 / -4,632 / 0.40 | 13 / -624 / 0.88 | 0.83 / -102 / 3/84 | 7/20 |
| SMC | 102 | 31.4 | 0.77 | 1.68 | -110.9 | -11,312 | 19,442 | 0 / 100 (26 starts) | - | 49 / -2,762 / 0.88 | 53 / -8,550 / 0.68 | 0.78 / -108 / 0/100 | 12/20 |
| DMI | 133 | 31.6 | 0.92 | 1.98 | -22.9 | -3,051 | 11,639 | 0 / 100 (26 starts) | - | 40 / -3,909 / 0.78 | 93 / 858 / 1.05 | 1.09 / 17 / 37/63 | 6/20 |
| RSI | 190 | 46.3 | 1.04 | 1.21 | 14.0 | 2,669 | 14,513 | 4 / 96 (26 starts) | 6 | 47 / -3,157 / 0.82 | 143 / 5,826 / 1.12 | 1.01 / 1 / 17/83 | 13/20 |
| COMB-1 first signal | 199 | 40.2 | 1.15 | 1.71 | 45.9 | 9,127 | 8,236 | 4 / 96 (26 starts) | 26 | 41 / -5,845 / 0.67 | 158 / 14,972 / 1.35 | 0.88 / -43 / 7/93 | 19/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 116 | 33.6 | 0.82 | 1.63 | -81.0 | -9,393 | 18,563 | 0 / 100 (26 starts) | - | 57 / -4,718 / 0.82 | 59 / -4,675 / 0.83 | 0.78 / -108 / 5/95 | 12/20 |
| COMB-3 vote >=2 | 22 | 36.4 | 0.54 | 0.95 | -195.9 | -4,310 | 5,350 | 0 / 54 (26 starts) | - | 12 / -2,929 / 0.49 | 10 / -1,381 / 0.62 | 0.72 / -120 / 0/72 | 4/20 |
| COMB-4 first, <=1/day/strat | 185 | 35.7 | 0.98 | 1.76 | -7.7 | -1,418 | 12,957 | 0 / 100 (26 starts) | - | 47 / -3,099 / 0.84 | 138 / 1,681 / 1.04 | 0.86 / -49 / 2/98 | 18/20 |

#### Pro 100K - full 12 months (2025-11-06..2026-11-05)
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 149 | 55.0 | 1.53 | 1.25 | 78.6 | 11,714 | 2,191 | 43 / 0 (111 starts) | 102 | 149 / 11,714 / 1.53 | 0 | - | - |
| ICT | 93 | 43.0 | 1.08 | 1.43 | 29.9 | 2,782 | 7,677 | 19 / 72 (111 starts) | 72 | 49 / -1,482 / 0.93 | 44 / 4,264 / 1.29 | 1.00 / -8 / 16/76 | 14/20 |
| SMC | 258 | 35.7 | 0.95 | 1.72 | -21.5 | -5,554 | 23,147 | 12 / 88 (111 starts) | 24 | 135 / -370 / 0.99 | 123 / -5,184 / 0.90 | 0.78 / -105 / 4/96 | 20/20 |
| DMI | 388 | 33.5 | 1.09 | 2.17 | 23.5 | 9,137 | 11,690 | 15 / 85 (111 starts) | 20 | 121 / 9,608 / 1.24 | 267 / -470 / 0.99 | 0.98 / -6 / 18/82 | 17/20 |
| RSI | 522 | 46.6 | 1.12 | 1.28 | 37.9 | 19,779 | 14,513 | 32 / 68 (111 starts) | 15 | 139 / -10,221 / 0.81 | 383 / 30,001 / 1.26 | 0.99 / -5 / 18/82 | 19/20 |
| COMB-1 first signal | 564 | 40.1 | 1.20 | 1.80 | 60.6 | 34,199 | 8,236 | 27 / 73 (111 starts) | 14 | 140 / -5,072 / 0.91 | 424 / 39,271 / 1.35 | 0.95 / -16 / 15/85 | 20/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 313 | 39.6 | 1.07 | 1.63 | 29.2 | 9,128 | 20,862 | 27 / 73 (111 starts) | 18 | 160 / 2,565 / 1.04 | 153 / 6,563 / 1.11 | 0.86 / -67 / 12/88 | 19/20 |
| COMB-3 vote >=2 | 58 | 41.4 | 0.98 | 1.39 | -7.0 | -406 | 5,350 | 14 / 45 (111 starts) | 84 | 34 / 4,726 / 1.37 | 24 / -5,132 / 0.46 | 0.89 / -47 / 6/77 | 12/20 |
| COMB-4 first, <=1/day/strat | 543 | 37.9 | 1.13 | 1.85 | 39.8 | 21,626 | 14,801 | 29 / 71 (111 starts) | 16 | 170 / -6,173 / 0.91 | 373 / 27,799 / 1.27 | 0.95 / -17 / 14/86 | 20/20 |

#### Pro 150K - last ~4 months (2026-07-01..2026-11-05) = JUDGE window
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 51 | 51.0 | 1.76 | 1.69 | 172.1 | 8,780 | 2,931 | 19 / 0 (26 starts) | 70 | 51 / 8,780 / 1.76 | 0 | - | - |
| ICT | 27 | 29.6 | 0.60 | 1.42 | -293.7 | -7,929 | 10,372 | 0 / 100 (26 starts) | - | 14 / -6,871 / 0.41 | 13 / -1,058 / 0.87 | 0.84 / -154 / 5/83 | 7/20 |
| SMC | 102 | 31.4 | 0.78 | 1.70 | -161.9 | -16,515 | 29,536 | 0 / 100 (26 starts) | - | 49 / -3,266 / 0.90 | 53 / -13,249 / 0.67 | 0.78 / -166 / 0/100 | 13/20 |
| DMI | 133 | 31.6 | 0.94 | 2.04 | -26.3 | -3,495 | 16,477 | 15 / 85 (26 starts) | 20 | 40 / -5,212 / 0.78 | 93 / 1,717 / 1.05 | 1.08 / 24 / 39/61 | 8/20 |
| RSI | 190 | 46.3 | 1.04 | 1.20 | 20.2 | 3,830 | 22,283 | 4 / 96 (26 starts) | 6 | 47 / -4,909 / 0.81 | 143 / 8,740 / 1.12 | 1.00 / -3 / 17/83 | 13/20 |
| COMB-1 first signal | 199 | 40.2 | 1.15 | 1.72 | 75.4 | 15,006 | 12,702 | 4 / 96 (26 starts) | 26 | 41 / -8,621 / 0.66 | 158 / 23,627 / 1.33 | 0.88 / -67 / 9/91 | 19/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 116 | 33.6 | 0.84 | 1.65 | -116.0 | -13,456 | 27,768 | 0 / 100 (26 starts) | - | 57 / -6,180 / 0.85 | 59 / -7,276 / 0.82 | 0.78 / -165 / 6/94 | 12/20 |
| COMB-3 vote >=2 | 22 | 36.4 | 0.53 | 0.93 | -309.1 | -6,801 | 8,361 | 0 / 96 (26 starts) | - | 12 / -4,243 / 0.50 | 10 / -2,558 / 0.57 | 0.71 / -189 / 0/78 | 4/20 |
| COMB-4 first, <=1/day/strat | 185 | 35.7 | 0.97 | 1.76 | -13.8 | -2,559 | 20,123 | 4 / 96 (26 starts) | 26 | 47 / -4,989 / 0.83 | 138 / 2,430 / 1.03 | 0.86 / -78 / 3/97 | 17/20 |

#### Pro 150K - full 12 months (2025-11-06..2026-11-05)
| config | trades | win % | PF | avg win / avg loss | $/trade | net $ | max DD $ | eval PASS / BUST % (rolling) | median days to pass | MNQ: n / net $ / PF | MGC: n / net $ / PF | random-direction: PF / $/tr / PASS/BUST % | real net beats random (seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE preset C (ref) | 149 | 55.0 | 1.53 | 1.25 | 117.9 | 17,571 | 3,286 | 43 / 0 (111 starts) | 102 | 149 / 17,571 / 1.53 | 0 | - | - |
| ICT | 93 | 43.0 | 1.08 | 1.43 | 45.0 | 4,189 | 11,733 | 19 / 72 (111 starts) | 72 | 49 / -2,260 / 0.93 | 44 / 6,450 / 1.29 | 1.00 / -12 / 17/76 | 15/20 |
| SMC | 258 | 35.7 | 0.96 | 1.73 | -28.0 | -7,215 | 34,529 | 13 / 87 (111 starts) | 25 | 135 / 478 / 1.01 | 123 / -7,694 / 0.91 | 0.78 / -160 / 4/96 | 20/20 |
| DMI | 388 | 33.5 | 1.07 | 2.12 | 30.6 | 11,869 | 20,508 | 14 / 86 (111 starts) | 12 | 121 / 12,810 / 1.24 | 267 / -941 / 0.99 | 0.97 / -16 / 19/81 | 16/20 |
| RSI | 522 | 46.6 | 1.11 | 1.27 | 55.7 | 29,058 | 22,283 | 30 / 70 (111 starts) | 14 | 139 / -16,822 / 0.78 | 383 / 45,880 / 1.24 | 0.98 / -12 / 18/82 | 19/20 |
| COMB-1 first signal | 564 | 40.1 | 1.18 | 1.77 | 90.2 | 50,899 | 13,764 | 16 / 84 (111 starts) | 11 | 140 / -9,254 / 0.88 | 424 / 60,154 / 1.30 | 0.95 / -27 / 16/84 | 20/20 |
| COMB-2 IS-PF gated (SMC+ICT) | 313 | 39.6 | 1.08 | 1.64 | 48.3 | 15,105 | 30,926 | 29 / 71 (111 starts) | 16 | 160 / 4,824 / 1.05 | 153 / 10,281 / 1.11 | 0.86 / -102 / 12/88 | 19/20 |
| COMB-3 vote >=2 | 58 | 41.4 | 0.98 | 1.39 | -13.0 | -752 | 8,361 | 14 / 52 (111 starts) | 84 | 34 / 7,560 / 1.40 | 24 / -8,311 / 0.44 | 0.88 / -76 / 6/80 | 12/20 |
| COMB-4 first, <=1/day/strat | 543 | 37.9 | 1.12 | 1.84 | 62.3 | 33,808 | 23,203 | 23 / 77 (111 starts) | 16 | 170 / -10,741 / 0.89 | 373 / 44,548 / 1.25 | 0.95 / -30 / 14/86 | 20/20 |


## 6. Other eval reads (bootstrap, non-strict bust, funded consistency, hedge-lock count, contracts used)
Bootstrap = the fairer PASS/BUST read for low-frequency rows (rolling windows often end OPEN). "seq" = bust only on closed-trade balance (session-17 headline convention). Consistency: largest day / net profit; > 40% would fail the funded payout rule (informational; ">300%" = net near zero).

| account | config | HO roll PASS/BUST % (strict) | HO roll PASS/BUST % (seq, no MAE) | 12m bootstrap PASS/BUST % (strict) | 12m bootstrap PASS/BUST % (seq) | median days (boot strict) | funded 40% consistency: largest day / net, HO | same, 12m | hedge-lock would-be vetoes (12m) | avg micros / max micros (12m) |
|---|---|---|---|---|---|---|---|---|---|---|
| 25K | NOISE preset C (ref) | 46 / 54 | 100 / 0 | 60 / 40 | 66 / 34 | 25 | 54% | 27% | 0 | 1.0 / 1 |
| 25K | ICT | 0 / 65 | 0 / 31 | 32 / 67 | 34 / 65 | 135 | -% | 178% | 0 | 1.9 / 2 |
| 25K | SMC | 8 / 92 | 8 / 92 | 36 / 64 | 42 / 58 | 18 | -% | 43% | 0 | 1.8 / 2 |
| 25K | DMI | 31 / 69 | 46 / 54 | 37 / 63 | 39 / 61 | 7 | -% | 73% | 0 | 1.0 / 1 |
| 25K | RSI | 12 / 88 | 23 / 77 | 39 / 61 | 45 / 55 | 10 | 114% | 14% | 12 | 1.0 / 2 |
| 25K | COMB-1 first signal | 46 / 54 | 62 / 38 | 37 / 63 | 45 / 55 | 7 | 52% | 21% | 342 | 1.1 / 2 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | 0 / 100 | 0 / 100 | 43 / 57 | 48 / 52 | 17 | -% | 21% | 3 | 1.8 / 2 |
| 25K | COMB-3 vote >=2 | 0 / 4 | 0 / 4 | 44 / 56 | 48 / 52 | 96 | -% | 111% | 0 | 1.6 / 2 |
| 25K | COMB-4 first, <=1/day/strat | 46 / 54 | 54 / 46 | 43 / 57 | 46 / 54 | 8 | >300% | 28% | 312 | 1.1 / 2 |
| 50K | NOISE preset C (ref) | 46 / 54 | 100 / 0 | 56 / 44 | 62 / 38 | 30 | 54% | 27% | 0 | 2.0 / 2 |
| 50K | ICT | 0 / 0 | 0 / 0 | 21 / 51 | 22 / 43 | 325 | -% | 195% | 0 | 2.0 / 2 |
| 50K | SMC | 0 / 100 | 0 / 100 | 41 / 59 | 44 / 56 | 48 | -% | 23% | 0 | 2.0 / 2 |
| 50K | DMI | 0 / 100 | 0 / 100 | 35 / 65 | 37 / 63 | 16 | -% | 51% | 0 | 1.3 / 2 |
| 50K | RSI | 12 / 85 | 23 / 69 | 34 / 66 | 43 / 57 | 14 | 163% | 18% | 12 | 1.8 / 2 |
| 50K | COMB-1 first signal | 15 / 85 | 27 / 73 | 42 / 58 | 49 / 51 | 15 | 31% | 15% | 342 | 1.6 / 2 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | 0 / 100 | 0 / 100 | 48 / 52 | 51 / 49 | 44 | -% | 17% | 3 | 2.0 / 2 |
| 50K | COMB-3 vote >=2 | 0 / 0 | 0 / 0 | 52 / 46 | 57 / 40 | 194 | -% | 95% | 0 | 1.9 / 2 |
| 50K | COMB-4 first, <=1/day/strat | 12 / 88 | 12 / 88 | 38 / 62 | 41 / 59 | 13 | >300% | 27% | 312 | 1.6 / 2 |
| 100K | NOISE preset C (ref) | 19 / 0 | 19 / 0 | 66 / 34 | 70 / 30 | 89 | 54% | 27% | 0 | 2.0 / 2 |
| 100K | ICT | 0 / 100 | 0 / 100 | 24 / 76 | 31 / 69 | 72 | -% | 76% | 0 | 14.1 / 42 |
| 100K | SMC | 0 / 100 | 0 / 100 | 16 / 84 | 20 / 80 | 19 | -% | -% | 0 | 11.5 / 51 |
| 100K | DMI | 0 / 100 | 0 / 100 | 27 / 73 | 30 / 70 | 18 | -% | 52% | 0 | 2.3 / 3 |
| 100K | RSI | 4 / 96 | 19 / 81 | 28 / 72 | 38 / 62 | 16 | 116% | 16% | 12 | 3.5 / 7 |
| 100K | COMB-1 first signal | 4 / 96 | 12 / 88 | 32 / 68 | 39 / 61 | 13 | 34% | 13% | 342 | 3.5 / 26 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | 0 / 100 | 0 / 100 | 26 / 74 | 32 / 68 | 17 | -% | 40% | 3 | 11.7 / 42 |
| 100K | COMB-3 vote >=2 | 0 / 54 | 0 / 54 | 19 / 81 | 23 / 77 | 122 | -% | -% | 0 | 9.2 / 28 |
| 100K | COMB-4 first, <=1/day/strat | 0 / 100 | 0 / 100 | 30 / 70 | 35 / 65 | 12 | -% | 26% | 312 | 3.7 / 37 |
| 150K | NOISE preset C (ref) | 19 / 0 | 19 / 0 | 66 / 34 | 70 / 30 | 89 | 54% | 27% | 0 | 3.0 / 3 |
| 150K | ICT | 0 / 100 | 0 / 100 | 24 / 76 | 31 / 69 | 72 | -% | 74% | 0 | 21.4 / 64 |
| 150K | SMC | 0 / 100 | 0 / 100 | 17 / 83 | 20 / 80 | 19 | -% | -% | 0 | 17.5 / 77 |
| 150K | DMI | 15 / 85 | 15 / 85 | 26 / 74 | 27 / 73 | 16 | -% | 73% | 0 | 4.0 / 4 |
| 150K | RSI | 4 / 96 | 19 / 81 | 28 / 72 | 38 / 62 | 15 | 120% | 16% | 12 | 5.4 / 11 |
| 150K | COMB-1 first signal | 4 / 96 | 12 / 88 | 27 / 73 | 36 / 64 | 11 | 41% | 17% | 342 | 5.6 / 39 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | 0 / 100 | 0 / 100 | 28 / 72 | 34 / 66 | 16 | -% | 37% | 3 | 17.8 / 64 |
| 150K | COMB-3 vote >=2 | 0 / 96 | 0 / 65 | 19 / 81 | 22 / 78 | 117 | -% | -% | 0 | 14.0 / 42 |
| 150K | COMB-4 first, <=1/day/strat | 4 / 96 | 4 / 96 | 28 / 72 | 34 / 66 | 12 | -% | 26% | 312 | 5.9 / 56 |


## 7. Sensitivity of the combined variants (25K / 50K / 100K / 150K)
Same trades, other sizing or rules: "no day rules" (no 3/day, no 2-loss stop, no DLL stop; still one position), risk budget 12.5% / 50% of MLL instead of 25%, and cap 2 micros on every account (what the 2-micro rule would do on 100K / 150K).

| account | combined variant | sizing / rule variant | HO trades | HO PF | HO $/tr | HO net $ | HO maxDD $ | HO PASS/BUST % | 12m trades | 12m PF | 12m net $ | 12m maxDD $ | 12m PASS/BUST % | avg micros |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | COMB-1 first signal | base (25% MLL budget, app day rules) | 199 | 1.16 | 14.9 | 2,965 | 2,418 | 46 / 54 | 564 | 1.18 | 10,383 | 3,190 | 35 / 65 | 1.1 |
| 25K | COMB-1 first signal | no day rules | 264 | 1.08 | 7.2 | 1,911 | 2,267 | 46 / 54 | 726 | 1.15 | 11,017 | 5,223 | 39 / 61 | 1.1 |
| 25K | COMB-1 first signal | budget 12.5% MLL | 199 | 1.18 | 16.0 | 3,193 | 2,333 | 54 / 46 | 564 | 1.18 | 10,083 | 3,272 | 39 / 61 | 1.0 |
| 25K | COMB-1 first signal | cap 2 micros | 199 | 1.16 | 14.9 | 2,965 | 2,418 | 46 / 54 | 564 | 1.18 | 10,383 | 3,190 | 35 / 65 | 1.1 |
| 25K | COMB-1 first signal | budget 50% MLL | 199 | 1.17 | 25.5 | 5,078 | 4,206 | 27 / 73 | 564 | 1.22 | 18,824 | 4,206 | 32 / 68 | 1.6 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | base (25% MLL budget, app day rules) | 116 | 0.81 | -17.1 | -1,983 | 3,669 | 0 / 100 | 313 | 1.13 | 3,324 | 3,889 | 29 / 71 | 1.8 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | no day rules | 124 | 0.78 | -20.0 | -2,475 | 4,021 | 8 / 92 | 329 | 1.10 | 2,510 | 4,116 | 24 / 76 | 1.8 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | budget 12.5% MLL | 116 | 0.83 | -10.9 | -1,264 | 2,818 | 0 / 100 | 313 | 1.15 | 2,715 | 2,888 | 25 / 75 | 1.4 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | cap 2 micros | 116 | 0.81 | -17.1 | -1,983 | 3,669 | 0 / 100 | 313 | 1.13 | 3,324 | 3,889 | 29 / 71 | 1.8 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | budget 50% MLL | 116 | 0.79 | -23.1 | -2,675 | 5,336 | 15 / 85 | 313 | 1.19 | 5,692 | 5,486 | 32 / 68 | 2.0 |
| 25K | COMB-3 vote >=2 | base (25% MLL budget, app day rules) | 22 | 0.58 | -41.0 | -902 | 1,032 | 0 / 4 | 58 | 1.14 | 664 | 1,032 | 43 / 28 | 1.6 |
| 25K | COMB-3 vote >=2 | no day rules | 22 | 0.58 | -41.0 | -902 | 1,032 | 0 / 4 | 58 | 1.14 | 664 | 1,032 | 43 / 28 | 1.6 |
| 25K | COMB-3 vote >=2 | budget 12.5% MLL | 22 | 0.54 | -35.5 | -780 | 910 | 0 / 0 | 58 | 1.11 | 411 | 910 | 35 / 0 | 1.3 |
| 25K | COMB-3 vote >=2 | cap 2 micros | 22 | 0.58 | -41.0 | -902 | 1,032 | 0 / 4 | 58 | 1.14 | 664 | 1,032 | 43 / 28 | 1.6 |
| 25K | COMB-3 vote >=2 | budget 50% MLL | 22 | 0.54 | -62.4 | -1,373 | 1,503 | 0 / 23 | 58 | 1.24 | 1,557 | 1,503 | 57 / 25 | 1.9 |
| 25K | COMB-4 first, <=1/day/strat | base (25% MLL budget, app day rules) | 185 | 1.00 | 0.1 | 9 | 3,397 | 46 / 54 | 543 | 1.14 | 7,690 | 5,329 | 47 / 53 | 1.1 |
| 25K | COMB-4 first, <=1/day/strat | no day rules | 234 | 0.96 | -4.1 | -965 | 4,816 | 46 / 54 | 662 | 1.10 | 7,023 | 5,227 | 46 / 54 | 1.1 |
| 25K | COMB-4 first, <=1/day/strat | budget 12.5% MLL | 185 | 1.00 | 0.4 | 70 | 3,110 | 46 / 54 | 543 | 1.14 | 7,863 | 5,092 | 45 / 55 | 1.0 |
| 25K | COMB-4 first, <=1/day/strat | cap 2 micros | 185 | 1.00 | 0.1 | 9 | 3,397 | 46 / 54 | 543 | 1.14 | 7,690 | 5,329 | 47 / 53 | 1.1 |
| 25K | COMB-4 first, <=1/day/strat | budget 50% MLL | 185 | 1.02 | 3.0 | 550 | 5,991 | 19 / 81 | 543 | 1.15 | 13,180 | 7,899 | 35 / 65 | 1.6 |
| 50K | COMB-1 first signal | base (25% MLL budget, app day rules) | 199 | 1.17 | 25.5 | 5,078 | 4,206 | 15 / 85 | 564 | 1.22 | 18,824 | 4,206 | 38 / 62 | 1.6 |
| 50K | COMB-1 first signal | no day rules | 264 | 1.02 | 2.8 | 736 | 5,489 | 4 / 96 | 726 | 1.15 | 16,153 | 6,501 | 24 / 76 | 1.6 |
| 50K | COMB-1 first signal | budget 12.5% MLL | 199 | 1.16 | 14.9 | 2,965 | 2,418 | 12 / 88 | 564 | 1.18 | 10,383 | 3,190 | 23 / 77 | 1.1 |
| 50K | COMB-1 first signal | cap 2 micros | 199 | 1.17 | 25.5 | 5,078 | 4,206 | 15 / 85 | 564 | 1.22 | 18,824 | 4,206 | 38 / 62 | 1.6 |
| 50K | COMB-1 first signal | budget 50% MLL | 199 | 1.18 | 32.2 | 6,408 | 4,696 | 50 / 50 | 564 | 1.18 | 20,100 | 6,545 | 34 / 66 | 2.0 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | base (25% MLL budget, app day rules) | 116 | 0.79 | -23.1 | -2,675 | 5,336 | 0 / 100 | 313 | 1.19 | 5,692 | 5,486 | 27 / 73 | 2.0 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | no day rules | 124 | 0.76 | -25.5 | -3,166 | 5,688 | 0 / 100 | 329 | 1.16 | 4,891 | 5,688 | 23 / 77 | 2.0 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | budget 12.5% MLL | 116 | 0.81 | -17.1 | -1,983 | 3,669 | 0 / 100 | 313 | 1.13 | 3,324 | 3,889 | 39 / 59 | 1.8 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | cap 2 micros | 116 | 0.79 | -23.1 | -2,675 | 5,336 | 0 / 100 | 313 | 1.19 | 5,692 | 5,486 | 27 / 73 | 2.0 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | budget 50% MLL | 116 | 0.79 | -23.1 | -2,675 | 5,336 | 0 / 100 | 313 | 1.19 | 5,692 | 5,486 | 27 / 73 | 2.0 |
| 50K | COMB-3 vote >=2 | base (25% MLL budget, app day rules) | 22 | 0.54 | -62.4 | -1,373 | 1,503 | 0 / 0 | 58 | 1.24 | 1,557 | 1,503 | 33 / 0 | 1.9 |
| 50K | COMB-3 vote >=2 | no day rules | 22 | 0.54 | -62.4 | -1,373 | 1,503 | 0 / 0 | 58 | 1.24 | 1,557 | 1,503 | 33 / 0 | 1.9 |
| 50K | COMB-3 vote >=2 | budget 12.5% MLL | 22 | 0.58 | -41.0 | -902 | 1,032 | 0 / 0 | 58 | 1.14 | 664 | 1,032 | 0 / 0 | 1.6 |
| 50K | COMB-3 vote >=2 | cap 2 micros | 22 | 0.54 | -62.4 | -1,373 | 1,503 | 0 / 0 | 58 | 1.24 | 1,557 | 1,503 | 33 / 0 | 1.9 |
| 50K | COMB-3 vote >=2 | budget 50% MLL | 22 | 0.55 | -64.2 | -1,412 | 1,542 | 0 / 0 | 58 | 1.18 | 1,259 | 1,542 | 27 / 0 | 2.0 |
| 50K | COMB-4 first, <=1/day/strat | base (25% MLL budget, app day rules) | 185 | 1.02 | 3.0 | 550 | 5,991 | 12 / 88 | 543 | 1.15 | 13,180 | 7,899 | 34 / 66 | 1.6 |
| 50K | COMB-4 first, <=1/day/strat | no day rules | 234 | 0.94 | -10.1 | -2,352 | 10,116 | 15 / 85 | 662 | 1.10 | 10,446 | 10,116 | 41 / 59 | 1.7 |
| 50K | COMB-4 first, <=1/day/strat | budget 12.5% MLL | 185 | 1.00 | 0.1 | 9 | 3,397 | 0 / 100 | 543 | 1.14 | 7,690 | 5,329 | 38 / 62 | 1.1 |
| 50K | COMB-4 first, <=1/day/strat | cap 2 micros | 185 | 1.02 | 3.0 | 550 | 5,991 | 12 / 88 | 543 | 1.15 | 13,180 | 7,899 | 34 / 66 | 1.6 |
| 50K | COMB-4 first, <=1/day/strat | budget 50% MLL | 185 | 1.01 | 2.0 | 369 | 6,123 | 35 / 65 | 543 | 1.15 | 15,812 | 10,128 | 41 / 59 | 2.0 |
| 100K | COMB-1 first signal | base (25% MLL budget, app day rules) | 199 | 1.15 | 45.9 | 9,127 | 8,236 | 4 / 96 | 564 | 1.20 | 34,199 | 8,236 | 27 / 73 | 3.5 |
| 100K | COMB-1 first signal | no day rules | 264 | 1.06 | 19.3 | 5,095 | 10,756 | 4 / 96 | 726 | 1.15 | 32,754 | 14,935 | 31 / 69 | 3.8 |
| 100K | COMB-1 first signal | budget 12.5% MLL | 199 | 1.14 | 18.9 | 3,755 | 3,826 | 0 / 100 | 564 | 1.19 | 14,020 | 3,826 | 34 / 59 | 1.5 |
| 100K | COMB-1 first signal | cap 2 micros | 199 | 1.18 | 32.2 | 6,408 | 4,696 | 23 / 77 | 564 | 1.18 | 20,100 | 6,545 | 22 / 78 | 2.0 |
| 100K | COMB-1 first signal | budget 50% MLL | 199 | 1.12 | 63.0 | 12,527 | 15,163 | 15 / 85 | 564 | 1.15 | 45,885 | 19,849 | 21 / 79 | 6.3 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | base (25% MLL budget, app day rules) | 116 | 0.82 | -81.0 | -9,393 | 18,563 | 0 / 100 | 313 | 1.07 | 9,128 | 20,862 | 27 / 73 | 11.7 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | no day rules | 124 | 0.77 | -106.1 | -13,161 | 21,634 | 0 / 100 | 329 | 1.03 | 4,221 | 23,326 | 26 / 74 | 11.8 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | budget 12.5% MLL | 116 | 0.81 | -41.3 | -4,786 | 8,917 | 0 / 100 | 313 | 1.05 | 3,202 | 10,266 | 20 / 80 | 5.6 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | cap 2 micros | 116 | 0.79 | -23.1 | -2,675 | 5,336 | 0 / 100 | 313 | 1.19 | 5,692 | 5,486 | 27 / 58 | 2.0 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | budget 50% MLL | 116 | 0.87 | -102.0 | -11,837 | 31,779 | 8 / 92 | 313 | 1.13 | 28,431 | 31,779 | 27 / 73 | 19.4 |
| 100K | COMB-3 vote >=2 | base (25% MLL budget, app day rules) | 22 | 0.54 | -195.9 | -4,310 | 5,350 | 0 / 54 | 58 | 0.98 | -406 | 5,350 | 14 / 45 | 9.2 |
| 100K | COMB-3 vote >=2 | no day rules | 22 | 0.54 | -195.9 | -4,310 | 5,350 | 0 / 54 | 58 | 0.98 | -406 | 5,350 | 14 / 45 | 9.2 |
| 100K | COMB-3 vote >=2 | budget 12.5% MLL | 22 | 0.53 | -95.0 | -2,089 | 2,609 | 0 / 0 | 58 | 0.94 | -635 | 2,609 | 0 / 0 | 4.3 |
| 100K | COMB-3 vote >=2 | cap 2 micros | 22 | 0.55 | -64.2 | -1,412 | 1,542 | 0 / 0 | 58 | 1.18 | 1,259 | 1,542 | 0 / 0 | 2.0 |
| 100K | COMB-3 vote >=2 | budget 50% MLL | 22 | 0.50 | -438.2 | -9,641 | 11,721 | 0 / 100 | 58 | 0.91 | -3,907 | 12,160 | 11 / 89 | 18.3 |
| 100K | COMB-4 first, <=1/day/strat | base (25% MLL budget, app day rules) | 185 | 0.98 | -7.7 | -1,418 | 12,957 | 0 / 100 | 543 | 1.13 | 21,626 | 14,801 | 29 / 71 | 3.7 |
| 100K | COMB-4 first, <=1/day/strat | no day rules | 234 | 0.95 | -17.8 | -4,173 | 19,138 | 4 / 96 | 662 | 1.10 | 21,111 | 19,138 | 35 / 65 | 4.3 |
| 100K | COMB-4 first, <=1/day/strat | budget 12.5% MLL | 185 | 0.96 | -6.5 | -1,195 | 5,474 | 0 / 100 | 543 | 1.13 | 9,140 | 6,664 | 32 / 68 | 1.6 |
| 100K | COMB-4 first, <=1/day/strat | cap 2 micros | 185 | 1.01 | 2.0 | 369 | 6,123 | 0 / 100 | 543 | 1.15 | 15,812 | 10,128 | 24 / 76 | 2.0 |
| 100K | COMB-4 first, <=1/day/strat | budget 50% MLL | 185 | 1.05 | 31.6 | 5,849 | 20,810 | 12 / 88 | 543 | 1.11 | 34,739 | 28,019 | 25 / 75 | 6.6 |
| 150K | COMB-1 first signal | base (25% MLL budget, app day rules) | 199 | 1.15 | 75.4 | 15,006 | 12,702 | 4 / 96 | 564 | 1.18 | 50,899 | 13,764 | 16 / 84 | 5.6 |
| 150K | COMB-1 first signal | no day rules | 264 | 1.09 | 45.8 | 12,080 | 12,308 | 4 / 96 | 726 | 1.16 | 54,399 | 23,599 | 23 / 77 | 6.1 |
| 150K | COMB-1 first signal | budget 12.5% MLL | 199 | 1.16 | 36.2 | 7,207 | 5,974 | 0 / 100 | 564 | 1.19 | 24,687 | 6,837 | 32 / 68 | 2.7 |
| 150K | COMB-1 first signal | cap 2 micros | 199 | 1.18 | 32.2 | 6,408 | 4,696 | 0 / 69 | 564 | 1.18 | 20,100 | 6,545 | 34 / 57 | 2.0 |
| 150K | COMB-1 first signal | budget 50% MLL | 199 | 1.11 | 93.7 | 18,649 | 22,359 | 15 / 85 | 564 | 1.15 | 70,450 | 30,820 | 19 / 81 | 9.7 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | base (25% MLL budget, app day rules) | 116 | 0.84 | -116.0 | -13,456 | 27,768 | 0 / 100 | 313 | 1.08 | 15,105 | 30,926 | 29 / 71 | 17.8 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | no day rules | 124 | 0.78 | -154.4 | -19,145 | 32,344 | 8 / 92 | 329 | 1.04 | 7,709 | 34,538 | 29 / 71 | 17.9 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | budget 12.5% MLL | 116 | 0.84 | -53.2 | -6,177 | 13,154 | 0 / 100 | 313 | 1.06 | 5,796 | 14,926 | 22 / 77 | 8.7 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | cap 2 micros | 116 | 0.79 | -23.1 | -2,675 | 5,336 | 0 / 46 | 313 | 1.19 | 5,692 | 5,486 | 0 / 32 | 2.0 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | budget 50% MLL | 116 | 0.88 | -147.4 | -17,098 | 48,191 | 8 / 92 | 313 | 1.13 | 45,244 | 48,191 | 27 / 73 | 29.5 |
| 150K | COMB-3 vote >=2 | base (25% MLL budget, app day rules) | 22 | 0.53 | -309.1 | -6,801 | 8,361 | 0 / 96 | 58 | 0.98 | -752 | 8,361 | 14 / 52 | 14.0 |
| 150K | COMB-3 vote >=2 | no day rules | 22 | 0.53 | -309.1 | -6,801 | 8,361 | 0 / 96 | 58 | 0.98 | -752 | 8,361 | 14 / 52 | 14.0 |
| 150K | COMB-3 vote >=2 | budget 12.5% MLL | 22 | 0.55 | -145.0 | -3,189 | 3,969 | 0 / 0 | 58 | 0.97 | -443 | 3,969 | 0 / 0 | 6.9 |
| 150K | COMB-3 vote >=2 | cap 2 micros | 22 | 0.55 | -64.2 | -1,412 | 1,542 | 0 / 0 | 58 | 1.18 | 1,259 | 1,542 | 0 / 0 | 2.0 |
| 150K | COMB-3 vote >=2 | budget 50% MLL | 22 | 0.51 | -666.5 | -14,663 | 17,848 | 0 / 100 | 58 | 0.92 | -5,780 | 18,635 | 11 / 89 | 27.9 |
| 150K | COMB-4 first, <=1/day/strat | base (25% MLL budget, app day rules) | 185 | 0.97 | -13.8 | -2,559 | 20,123 | 4 / 96 | 543 | 1.12 | 33,808 | 23,203 | 23 / 77 | 5.9 |
| 150K | COMB-4 first, <=1/day/strat | no day rules | 234 | 0.96 | -22.4 | -5,242 | 26,422 | 4 / 96 | 662 | 1.10 | 34,017 | 26,422 | 27 / 73 | 6.7 |
| 150K | COMB-4 first, <=1/day/strat | budget 12.5% MLL | 185 | 0.98 | -4.3 | -802 | 9,140 | 0 / 100 | 543 | 1.13 | 17,270 | 11,296 | 32 / 68 | 2.8 |
| 150K | COMB-4 first, <=1/day/strat | cap 2 micros | 185 | 1.01 | 2.0 | 369 | 6,123 | 0 / 100 | 543 | 1.15 | 15,812 | 10,128 | 31 / 62 | 2.0 |
| 150K | COMB-4 first, <=1/day/strat | budget 50% MLL | 185 | 1.06 | 52.0 | 9,620 | 31,251 | 12 / 88 | 543 | 1.11 | 54,602 | 43,287 | 26 / 74 | 10.2 |


## 8. MNQ-only and MGC-only (each combination restricted to one market)

| account | config | scope | HO n | HO win % | HO PF | HO $/tr | HO net $ | HO PASS/BUST % | 12m n | 12m PF | 12m net $ | 12m PASS/BUST % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25K | ICT | MNQ only | 16 | 25.0 | 0.45 | -49.1 | -785 | 0 / 50 | 54 | 1.06 | 212 | 22 / 54 |
| 25K | ICT | MGC only | 14 | 35.7 | 0.68 | -24.4 | -341 | 0 / 0 | 47 | 1.11 | 318 | 0 / 0 |
| 25K | SMC | MNQ only | 53 | 32.1 | 0.96 | -3.9 | -205 | 12 / 88 | 151 | 1.13 | 1,767 | 51 / 49 |
| 25K | SMC | MGC only | 57 | 29.8 | 0.55 | -40.6 | -2,316 | 0 / 69 | 137 | 0.99 | -78 | 41 / 52 |
| 25K | DMI | MNQ only | 79 | 32.9 | 0.80 | -25.9 | -2,042 | 0 / 100 | 224 | 1.16 | 3,766 | 37 / 63 |
| 25K | DMI | MGC only | 108 | 35.2 | 0.97 | -2.6 | -285 | 65 / 35 | 317 | 0.92 | -2,689 | 26 / 74 |
| 25K | RSI | MNQ only | 80 | 46.2 | 0.95 | -5.4 | -435 | 27 / 73 | 247 | 0.86 | -3,776 | 13 / 87 |
| 25K | RSI | MGC only | 160 | 51.2 | 1.22 | 18.3 | 2,926 | 12 / 88 | 429 | 1.23 | 9,510 | 39 / 61 |
| 25K | COMB-1 first signal | MNQ only | 135 | 39.3 | 0.90 | -12.3 | -1,664 | 12 / 88 | 383 | 1.12 | 4,698 | 35 / 65 |
| 25K | COMB-1 first signal | MGC only | 187 | 44.9 | 1.32 | 26.5 | 4,947 | 54 / 46 | 525 | 1.18 | 9,345 | 39 / 61 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | MNQ only | 65 | 32.3 | 0.91 | -8.6 | -558 | 4 / 96 | 193 | 1.17 | 2,708 | 56 / 44 |
| 25K | COMB-2 IS-PF gated (SMC+ICT) | MGC only | 67 | 32.8 | 0.62 | -31.7 | -2,127 | 0 / 69 | 174 | 1.07 | 900 | 19 / 74 |
| 25K | COMB-3 vote >=2 | MNQ only | 12 | 33.3 | 0.51 | -47.1 | -566 | 0 / 0 | 35 | 1.67 | 1,678 | 54 / 0 |
| 25K | COMB-3 vote >=2 | MGC only | 10 | 40.0 | 0.67 | -33.6 | -336 | 0 / 0 | 24 | 0.52 | -1,109 | 0 / 40 |
| 25K | COMB-4 first, <=1/day/strat | MNQ only | 126 | 37.3 | 0.88 | -14.3 | -1,806 | 8 / 92 | 362 | 1.10 | 3,775 | 33 / 67 |
| 25K | COMB-4 first, <=1/day/strat | MGC only | 164 | 40.2 | 1.03 | 2.6 | 418 | 62 / 38 | 467 | 1.09 | 4,324 | 45 / 55 |
| 50K | ICT | MNQ only | 16 | 25.0 | 0.61 | -39.2 | -627 | 0 / 0 | 54 | 1.17 | 688 | 0 / 9 |
| 50K | ICT | MGC only | 14 | 35.7 | 0.60 | -34.2 | -479 | 0 / 0 | 47 | 1.06 | 188 | 0 / 0 |
| 50K | SMC | MNQ only | 53 | 32.1 | 0.88 | -15.8 | -838 | 0 / 100 | 151 | 1.16 | 2,733 | 28 / 42 |
| 50K | SMC | MGC only | 57 | 29.8 | 0.60 | -39.2 | -2,236 | 0 / 50 | 137 | 1.07 | 828 | 29 / 53 |
| 50K | DMI | MNQ only | 79 | 32.9 | 0.80 | -51.7 | -4,085 | 0 / 100 | 224 | 1.16 | 7,533 | 34 / 66 |
| 50K | DMI | MGC only | 108 | 35.2 | 0.97 | -2.6 | -285 | 46 / 50 | 317 | 0.92 | -2,689 | 12 / 87 |
| 50K | RSI | MNQ only | 80 | 46.2 | 0.95 | -10.9 | -871 | 27 / 73 | 247 | 0.86 | -7,471 | 12 / 88 |
| 50K | RSI | MGC only | 160 | 51.2 | 1.20 | 31.7 | 5,078 | 12 / 88 | 429 | 1.24 | 16,146 | 44 / 56 |
| 50K | COMB-1 first signal | MNQ only | 135 | 39.3 | 0.86 | -32.2 | -4,343 | 12 / 88 | 383 | 1.12 | 8,972 | 32 / 68 |
| 50K | COMB-1 first signal | MGC only | 187 | 44.9 | 1.34 | 41.1 | 7,692 | 50 / 50 | 525 | 1.23 | 16,173 | 42 / 58 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | MNQ only | 65 | 32.3 | 0.88 | -15.9 | -1,033 | 0 / 100 | 193 | 1.21 | 4,150 | 36 / 45 |
| 50K | COMB-2 IS-PF gated (SMC+ICT) | MGC only | 67 | 32.8 | 0.65 | -32.6 | -2,184 | 0 / 50 | 174 | 1.11 | 1,689 | 35 / 50 |
| 50K | COMB-3 vote >=2 | MNQ only | 12 | 33.3 | 0.41 | -88.0 | -1,056 | 0 / 0 | 35 | 1.86 | 2,943 | 42 / 0 |
| 50K | COMB-3 vote >=2 | MGC only | 10 | 40.0 | 0.73 | -31.7 | -317 | 0 / 0 | 24 | 0.52 | -1,480 | 0 / 0 |
| 50K | COMB-4 first, <=1/day/strat | MNQ only | 126 | 37.3 | 0.84 | -36.6 | -4,611 | 4 / 96 | 362 | 1.11 | 7,733 | 33 / 67 |
| 50K | COMB-4 first, <=1/day/strat | MGC only | 164 | 40.2 | 1.07 | 8.7 | 1,421 | 42 / 58 | 467 | 1.13 | 8,182 | 49 / 51 |
| 100K | ICT | MNQ only | 16 | 25.0 | 0.48 | -272.5 | -4,360 | 0 / 100 | 54 | 1.09 | 1,870 | 0 / 94 |
| 100K | ICT | MGC only | 14 | 35.7 | 0.77 | -97.5 | -1,365 | 0 / 0 | 47 | 1.23 | 3,753 | 18 / 26 |
| 100K | SMC | MNQ only | 53 | 32.1 | 0.83 | -77.9 | -4,126 | 0 / 100 | 151 | 1.01 | 900 | 14 / 86 |
| 100K | SMC | MGC only | 57 | 29.8 | 0.64 | -179.8 | -10,247 | 0 / 100 | 137 | 0.88 | -7,243 | 5 / 95 |
| 100K | DMI | MNQ only | 79 | 32.9 | 0.80 | -77.6 | -6,128 | 0 / 100 | 224 | 1.16 | 11,300 | 31 / 69 |
| 100K | DMI | MGC only | 108 | 35.2 | 0.97 | -5.3 | -570 | 46 / 50 | 317 | 0.92 | -5,378 | 12 / 87 |
| 100K | RSI | MNQ only | 80 | 46.2 | 0.90 | -34.5 | -2,762 | 19 / 81 | 247 | 0.82 | -16,052 | 5 / 95 |
| 100K | RSI | MGC only | 160 | 51.2 | 1.20 | 62.3 | 9,974 | 4 / 96 | 429 | 1.24 | 30,536 | 34 / 66 |
| 100K | COMB-1 first signal | MNQ only | 135 | 39.3 | 0.87 | -51.0 | -6,891 | 12 / 88 | 383 | 1.07 | 9,217 | 23 / 77 |
| 100K | COMB-1 first signal | MGC only | 187 | 44.9 | 1.34 | 87.9 | 16,437 | 42 / 58 | 525 | 1.24 | 34,195 | 38 / 62 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | MNQ only | 65 | 32.3 | 0.81 | -85.3 | -5,542 | 0 / 100 | 193 | 1.10 | 7,948 | 29 / 71 |
| 100K | COMB-2 IS-PF gated (SMC+ICT) | MGC only | 67 | 32.8 | 0.72 | -131.6 | -8,816 | 0 / 100 | 174 | 1.00 | 352 | 16 / 84 |
| 100K | COMB-3 vote >=2 | MNQ only | 12 | 33.3 | 0.49 | -244.1 | -2,929 | 0 / 65 | 35 | 1.30 | 4,021 | 42 / 33 |
| 100K | COMB-3 vote >=2 | MGC only | 10 | 40.0 | 0.62 | -138.1 | -1,381 | 0 / 0 | 24 | 0.46 | -5,132 | 0 / 63 |
| 100K | COMB-4 first, <=1/day/strat | MNQ only | 126 | 37.3 | 0.86 | -55.7 | -7,017 | 4 / 96 | 362 | 1.04 | 5,744 | 14 / 86 |
| 100K | COMB-4 first, <=1/day/strat | MGC only | 164 | 40.2 | 1.05 | 14.5 | 2,375 | 12 / 88 | 467 | 1.12 | 15,297 | 35 / 65 |
| 150K | ICT | MNQ only | 16 | 25.0 | 0.49 | -403.0 | -6,448 | 0 / 100 | 54 | 1.09 | 2,775 | 0 / 94 |
| 150K | ICT | MGC only | 14 | 35.7 | 0.77 | -153.4 | -2,148 | 0 / 0 | 47 | 1.23 | 5,718 | 18 / 26 |
| 150K | SMC | MNQ only | 53 | 32.1 | 0.86 | -101.9 | -5,399 | 4 / 96 | 151 | 1.02 | 2,158 | 16 / 84 |
| 150K | SMC | MGC only | 57 | 29.8 | 0.64 | -276.8 | -15,779 | 0 / 100 | 137 | 0.88 | -10,804 | 7 / 93 |
| 150K | DMI | MNQ only | 79 | 32.9 | 0.80 | -103.4 | -8,170 | 0 / 100 | 224 | 1.16 | 15,066 | 31 / 69 |
| 150K | DMI | MGC only | 108 | 35.2 | 0.97 | -10.5 | -1,139 | 46 / 54 | 317 | 0.92 | -10,757 | 15 / 85 |
| 150K | RSI | MNQ only | 80 | 46.2 | 0.88 | -64.3 | -5,140 | 15 / 85 | 247 | 0.80 | -25,553 | 3 / 97 |
| 150K | RSI | MGC only | 160 | 51.2 | 1.20 | 95.0 | 15,202 | 4 / 96 | 429 | 1.22 | 46,544 | 32 / 68 |
| 150K | COMB-1 first signal | MNQ only | 135 | 39.3 | 0.89 | -62.5 | -8,437 | 12 / 88 | 383 | 1.06 | 11,831 | 26 / 74 |
| 150K | COMB-1 first signal | MGC only | 187 | 44.9 | 1.32 | 141.6 | 26,488 | 19 / 81 | 525 | 1.22 | 52,819 | 29 / 71 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | MNQ only | 65 | 32.3 | 0.84 | -113.3 | -7,362 | 0 / 100 | 193 | 1.10 | 12,848 | 31 / 69 |
| 150K | COMB-2 IS-PF gated (SMC+ICT) | MGC only | 67 | 32.8 | 0.72 | -202.0 | -13,535 | 0 / 100 | 174 | 1.01 | 902 | 16 / 84 |
| 150K | COMB-3 vote >=2 | MNQ only | 12 | 33.3 | 0.50 | -353.6 | -4,243 | 0 / 65 | 35 | 1.32 | 6,479 | 44 / 33 |
| 150K | COMB-3 vote >=2 | MGC only | 10 | 40.0 | 0.57 | -255.8 | -2,558 | 0 / 0 | 24 | 0.44 | -8,311 | 0 / 62 |
| 150K | COMB-4 first, <=1/day/strat | MNQ only | 126 | 37.3 | 0.88 | -70.6 | -8,890 | 4 / 96 | 362 | 1.03 | 6,390 | 16 / 84 |
| 150K | COMB-4 first, <=1/day/strat | MGC only | 164 | 40.2 | 1.05 | 22.7 | 3,720 | 23 / 77 | 467 | 1.11 | 23,855 | 34 / 66 |


## 9. Every variant (1 micro, pooled) and every subset of the four strategies
Variant table (IS = first ~8 months, HO = judge window; the picks are the best IS PF with the minimum IS n):

| strategy | variant | IS n | IS PF | IS net $ | HO n | HO win % | HO PF | HO net $ | 12m n | 12m PF | 12m net $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DMI | DMI adx>25 15m flip | 277 | 1.13 | 3,835 | 145 | 30.3 | 0.86 | -2,425 | 422 | 1.03 | 1,410 |
| DMI | DMI adx>25 15m 2.0 | 322 | 1.12 | 4,193 | 168 | 35.1 | 0.76 | -4,549 | 490 | 0.99 | -356 |
| DMI | DMI adx>25 15m 1.5 | 347 | 1.04 | 1,431 | 181 | 35.9 | 0.73 | -5,442 | 528 | 0.93 | -4,011 |
| DMI | DMI adx>20 15m flip | 345 | 1.04 | 1,369 | 187 | 30.5 | 0.89 | -2,163 | 532 | 0.99 | -794 |
| DMI | DMI adx>20 15m 2.0 | 404 | 1.01 | 577 | 211 | 36.5 | 0.84 | -3,561 | 615 | 0.96 | -2,984 |
| DMI | DMI adx>20 15m 1.5 | 441 | 0.97 | -1,493 | 228 | 37.7 | 0.80 | -4,740 | 669 | 0.91 | -6,233 |
| DMI | DMI adx>20 5m 2.0 | 839 | 0.94 | -4,392 | 454 | 33.9 | 0.80 | -7,006 | 1293 | 0.90 | -11,398 |
| DMI | DMI adx>25 5m flip | 565 | 0.93 | -3,034 | 330 | 34.5 | 0.92 | -1,851 | 895 | 0.93 | -4,885 |
| DMI | DMI adx>20 5m 1.5 | 925 | 0.92 | -6,475 | 514 | 38.7 | 0.82 | -6,749 | 1439 | 0.88 | -13,224 |
| DMI | DMI adx>25 5m 2.0 | 638 | 0.91 | -5,478 | 357 | 33.6 | 0.80 | -6,146 | 995 | 0.87 | -11,624 |
| DMI | DMI adx>25 5m 1.5 | 703 | 0.88 | -7,275 | 404 | 37.6 | 0.75 | -7,897 | 1107 | 0.84 | -15,173 |
| DMI | DMI adx>20 5m flip | 799 | 0.81 | -11,758 | 451 | 34.4 | 0.94 | -1,662 | 1250 | 0.85 | -13,420 |
| ICT | PM 1.5R | 66 | 1.28 | 589 | 27 | 29.6 | 0.66 | -415 | 93 | 1.05 | 174 |
| ICT | AM+PM 2.0R | 112 | 1.23 | 1,139 | 50 | 26.0 | 0.65 | -885 | 162 | 1.03 | 254 |
| ICT | PM 2.0R | 65 | 1.20 | 451 | 27 | 25.9 | 0.79 | -263 | 92 | 1.05 | 188 |
| ICT | AM+PM 1.5R | 113 | 1.19 | 926 | 50 | 32.0 | 0.67 | -768 | 163 | 1.02 | 159 |
| RSI | TriRSI3 15m 1.5 | 377 | 1.13 | 4,822 | 214 | 48.6 | 1.13 | 2,523 | 591 | 1.13 | 7,345 |
| RSI | TriRSI2 15m 1.5 | 515 | 1.11 | 5,926 | 258 | 48.8 | 1.21 | 4,806 | 773 | 1.14 | 10,731 |
| RSI | TriRSI3 15m mr | 459 | 1.10 | 2,836 | 252 | 61.9 | 0.88 | -1,793 | 711 | 1.02 | 1,044 |
| RSI | TriRSI2 15m mr | 680 | 1.09 | 3,616 | 368 | 62.2 | 0.93 | -1,341 | 1048 | 1.04 | 2,275 |
| RSI | TriRSI2 5m 1.5 | 1148 | 1.06 | 5,225 | 624 | 43.8 | 1.02 | 949 | 1772 | 1.05 | 6,173 |
| RSI | TriRSI2 5m mr | 1953 | 1.05 | 3,394 | 1075 | 61.4 | 0.86 | -4,380 | 3028 | 0.99 | -986 |
| RSI | TriRSI3 5m 1.5 | 961 | 1.01 | 1,104 | 534 | 46.4 | 1.15 | 5,236 | 1495 | 1.06 | 6,340 |
| RSI | TriRSI3 5m mr | 1334 | 1.00 | 124 | 755 | 62.9 | 0.92 | -1,700 | 2089 | 0.98 | -1,576 |
| SMC | 5m+ST15+EMA200 R2.0 | 161 | 1.42 | 3,175 | 106 | 31.1 | 0.78 | -1,311 | 267 | 1.14 | 1,864 |
| SMC | 5m+ST15+EMA200 R1.5 | 167 | 1.38 | 2,685 | 109 | 33.9 | 0.74 | -1,518 | 276 | 1.09 | 1,166 |
| SMC | 5m+ST15 R2.0 | 191 | 1.18 | 1,747 | 113 | 30.1 | 0.75 | -1,545 | 304 | 1.01 | 202 |
| SMC | 5m+ST15 R1.5 | 201 | 1.17 | 1,522 | 118 | 33.9 | 0.74 | -1,585 | 319 | 1.00 | -63 |
| SMC | 1m+ST15+EMA200 R1.5 | 757 | 1.14 | 2,609 | 401 | 35.4 | 0.85 | -1,479 | 1158 | 1.04 | 1,129 |
| SMC | 1m+ST15 R1.5 | 968 | 1.12 | 2,878 | 517 | 36.0 | 0.81 | -2,317 | 1485 | 1.02 | 560 |
| SMC | 1m+ST15+EMA200 R2.0 | 730 | 1.11 | 2,238 | 387 | 29.5 | 0.93 | -743 | 1117 | 1.05 | 1,496 |
| SMC | 1m+ST15 R2.0 | 930 | 1.08 | 2,141 | 488 | 28.9 | 0.86 | -1,783 | 1418 | 1.01 | 359 |


Subsets (first-signal-wins; the IS-best subset is ICT+SMC at IS PF 1.36 but it lost in the judge window; DMI+RSI and ICT+DMI+RSI look best afterwards but that is post-hoc, they were not chosen in-sample):

#### Pro 25K sizing - every subset of the four picked strategies, first-signal-wins (exploratory)
| subset | IS n | IS PF | IS net $ | HO n | HO win % | HO PF | HO net $ | HO PASS/BUST % | 12m n | 12m PF | 12m net $ | 12m PASS/BUST % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ICT | 66 | 1.27 | 1,042 | 27 | 29.6 | 0.61 | -851 | 0 / 65 | 93 | 1.03 | 191 | 19 / 52 |
| SMC | 156 | 1.31 | 3,872 | 102 | 31.4 | 0.80 | -1,912 | 8 / 92 | 258 | 1.09 | 1,960 | 19 / 81 |
| DMI | 255 | 1.14 | 3,841 | 133 | 31.6 | 0.94 | -874 | 31 / 69 | 388 | 1.07 | 2,967 | 29 / 71 |
| RSI | 332 | 1.18 | 6,198 | 190 | 46.3 | 1.05 | 831 | 12 / 88 | 522 | 1.13 | 7,028 | 43 / 57 |
| ICT+SMC | 197 | 1.36 | 5,307 | 116 | 33.6 | 0.81 | -1,983 | 0 / 100 | 313 | 1.13 | 3,324 | 29 / 71 |
| ICT+DMI | 267 | 1.14 | 3,979 | 138 | 30.4 | 0.91 | -1,472 | 31 / 69 | 405 | 1.06 | 2,507 | 27 / 73 |
| ICT+RSI | 352 | 1.20 | 6,928 | 196 | 44.9 | 1.00 | 18 | 12 / 88 | 548 | 1.13 | 6,946 | 43 / 57 |
| SMC+DMI | 282 | 1.19 | 5,307 | 158 | 30.4 | 0.89 | -1,848 | 15 / 85 | 440 | 1.08 | 3,460 | 26 / 74 |
| SMC+RSI | 367 | 1.23 | 8,500 | 213 | 43.7 | 1.03 | 656 | 15 / 85 | 580 | 1.16 | 9,156 | 50 / 50 |
| DMI+RSI | 352 | 1.17 | 6,454 | 191 | 41.9 | 1.22 | 3,996 | 58 / 42 | 543 | 1.19 | 10,450 | 35 / 65 |
| ICT+SMC+DMI | 290 | 1.19 | 5,586 | 160 | 30.0 | 0.88 | -2,069 | 15 / 85 | 450 | 1.08 | 3,518 | 25 / 75 |
| ICT+SMC+RSI | 378 | 1.24 | 9,117 | 213 | 43.7 | 1.04 | 725 | 15 / 85 | 591 | 1.17 | 9,842 | 51 / 49 |
| ICT+DMI+RSI | 357 | 1.19 | 7,074 | 193 | 42.0 | 1.24 | 4,265 | 58 / 42 | 550 | 1.21 | 11,339 | 35 / 65 |
| SMC+DMI+RSI | 361 | 1.17 | 6,595 | 197 | 40.1 | 1.14 | 2,696 | 46 / 54 | 558 | 1.16 | 9,292 | 32 / 68 |
| ICT+SMC+DMI+RSI | 365 | 1.19 | 7,418 | 199 | 40.2 | 1.16 | 2,965 | 46 / 54 | 564 | 1.18 | 10,383 | 35 / 65 |

#### Pro 150K sizing - every subset of the four picked strategies, first-signal-wins (exploratory)
| subset | IS n | IS PF | IS net $ | HO n | HO win % | HO PF | HO net $ | HO PASS/BUST % | 12m n | 12m PF | 12m net $ | 12m PASS/BUST % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ICT | 66 | 1.36 | 12,118 | 27 | 29.6 | 0.60 | -7,929 | 0 / 100 | 93 | 1.08 | 4,189 | 19 / 72 |
| SMC | 156 | 1.09 | 9,300 | 102 | 31.4 | 0.78 | -16,515 | 0 / 100 | 258 | 0.96 | -7,215 | 13 / 87 |
| DMI | 255 | 1.14 | 15,364 | 133 | 31.6 | 0.94 | -3,495 | 15 / 85 | 388 | 1.07 | 11,869 | 14 / 86 |
| RSI | 332 | 1.15 | 25,227 | 190 | 46.3 | 1.04 | 3,830 | 4 / 96 | 522 | 1.11 | 29,058 | 30 / 70 |
| ICT+SMC | 197 | 1.24 | 28,561 | 116 | 33.6 | 0.84 | -13,456 | 0 / 100 | 313 | 1.08 | 15,105 | 29 / 71 |
| ICT+DMI | 267 | 1.15 | 16,665 | 138 | 30.4 | 0.87 | -8,898 | 12 / 88 | 405 | 1.04 | 7,766 | 10 / 90 |
| ICT+RSI | 352 | 1.18 | 31,319 | 196 | 44.9 | 0.98 | -2,633 | 0 / 100 | 548 | 1.10 | 28,686 | 30 / 70 |
| SMC+DMI | 282 | 1.20 | 24,558 | 158 | 30.4 | 0.82 | -14,435 | 0 / 100 | 440 | 1.05 | 10,123 | 13 / 87 |
| SMC+RSI | 367 | 1.15 | 30,332 | 213 | 43.7 | 1.04 | 4,611 | 12 / 88 | 580 | 1.11 | 34,943 | 28 / 72 |
| DMI+RSI | 352 | 1.16 | 27,848 | 191 | 41.9 | 1.21 | 18,814 | 35 / 65 | 543 | 1.18 | 46,662 | 21 / 79 |
| ICT+SMC+DMI | 290 | 1.22 | 27,866 | 160 | 30.0 | 0.80 | -16,596 | 0 / 100 | 450 | 1.05 | 11,270 | 15 / 85 |
| ICT+SMC+RSI | 378 | 1.17 | 34,621 | 213 | 43.7 | 1.04 | 4,654 | 12 / 88 | 591 | 1.12 | 39,275 | 37 / 63 |
| ICT+DMI+RSI | 357 | 1.18 | 30,804 | 193 | 42.0 | 1.22 | 19,183 | 35 / 65 | 550 | 1.19 | 49,987 | 18 / 82 |
| SMC+DMI+RSI | 361 | 1.17 | 30,989 | 197 | 40.1 | 1.15 | 14,637 | 4 / 96 | 558 | 1.17 | 45,626 | 11 / 89 |
| ICT+SMC+DMI+RSI | 365 | 1.20 | 35,894 | 199 | 40.2 | 1.15 | 15,006 | 4 / 96 | 564 | 1.18 | 50,899 | 16 / 84 |


## 10. Combinations that could work (hypotheses, not proven)
1. **RSI + DMI (+ ICT) on gold, first signal wins**: DMI+RSI judge PF 1.22 / 12-month PF 1.19 / IS PF 1.17 (25K), ICT+DMI+RSI 1.24 / 1.21 / 1.19. The only mixes positive in IS, judge and 12 months at the same time; the strength is diversification (DMI alone judge PF 0.94, RSI 1.05), but it is post-hoc, MGC-driven and MGC is OFF in the plans.
2. **Triple RSI with a 1.5R target (mainly the MGC leg)** as a stand-alone paper-test: the only strategy family positive in IS, judge and 12 months in every variant (pick TriRSI(3,7,14) 15m: 1.13 / 1.13 / 1.13 pooled). Payoff ~1.2 at 46-49% win, so a small edge that needs ~2 years more data.
3. **Per-strategy daily caps** (COMB-4 style) so a quiet, high-quality strategy (ICT/SMC) is not crowded out by the busy ones; here it did not improve results, but it is the right structure if a future ICT/SMC variant shows an edge.
4. **Vote/confluence** has slightly better bootstrap numbers than the other combinations at 25K / 50K (44/56 and 52/46 vs 37/63 and 42/58 for COMB-1; still below NOISE 60/40) but only 58 trades a year; worth re-testing on 2019-2026 (the cached MGC files go back to 2019 as well as MNQ) - which breaks the "last 12 months only" rule, so only if you allow it.
5. The studies' own hypotheses remain open: SuperTrend 15m / DMI direction as a side filter for NOISE, Triple RSI as a "do not chase" guard in NOISE. Combining NOISE with these four was not tested here (NOISE is MNQ-only, one trade a day).
**Rough honest expectation:** with ~0.5-2 trades per day available, profit factors of 1.0-1.2 and 40% win rates, a 2-micro 25K/50K account cannot reach the target before the MLL is hit more often than NOISE does; the 100K/150K accounts only turn that into bigger swings.

## 11. Files
`mlib.py` (loader + 1-micro simulator), `cands.py` (candidate trades per strategy/market, incl. random-direction twins), `port.py` (account selector, stats, eval sim), `repro.py`, `run.py`, `report.py`, `build_results.py`; `out/cands_*.pkl` (45k candidate trades), `out/results.json`, `out/picks.json`, `out/variants_pooled_1micro.csv`, `out/subsets.csv`, `out/trades_COMB-*_25k.csv` (taken trades, 25K sizing), `out/repro.md`, `out/tables_*.md`.
