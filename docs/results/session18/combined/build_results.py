"""Assemble RESULTS.md from the narrative below + the generated table fragments (python3 -I build_results.py)."""
HERE = "/home/user/opogabuuga/docs/results/session18/combined"
rd = lambda f: open(HERE + "/out/" + f).read()
doc = f"""# Session 18 - ICT + SMC + Triple RSI + DMI: separate vs COMBINED (MNQ + MGC, Lucid Pro 25K / 50K / 100K / 150K, last 12 months only)

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
{rd("tables_picks.md").split(chr(10)+chr(10))[0]}

The pick is chosen among 4-12 variants per strategy on ~8 months, so it is the best of several noisy numbers: three of the four picks fell in the judge window (ICT 1.28 -> 0.66, SMC 1.42 -> 0.78, DMI 1.13 -> 0.86), only Triple RSI held (1.13 -> 1.13). Full variant table (IS | judge | 12 months) in section 9.

## 5. Results per account (own strategy alone vs combined)
Columns: trades, win %, profit factor, avg win / avg loss (payoff), $ per trade, net, max drawdown of closed trades, rolling-start eval PASS / BUST % (strict MAE bust, remainder OPEN), median business days to pass, per-market n / net $ / PF, random-direction benchmark, and how many of 20 random seeds the real net beat. 25K and 50K: cap 2 micros. 100K / 150K: cap = plan max micros (60 / 100), budget 25% of MLL.
{rd("tables_main.md")}

## 6. Other eval reads (bootstrap, non-strict bust, funded consistency, hedge-lock count, contracts used)
Bootstrap = the fairer PASS/BUST read for low-frequency rows (rolling windows often end OPEN). "seq" = bust only on closed-trade balance (session-17 headline convention). Consistency: largest day / net profit; > 40% would fail the funded payout rule (informational; ">300%" = net near zero).

{rd("tables_boot.md")}

## 7. Sensitivity of the combined variants (25K / 50K / 100K / 150K)
Same trades, other sizing or rules: "no day rules" (no 3/day, no 2-loss stop, no DLL stop; still one position), risk budget 12.5% / 50% of MLL instead of 25%, and cap 2 micros on every account (what the 2-micro rule would do on 100K / 150K).

{rd("tables_sens.md")}

## 8. MNQ-only and MGC-only (each combination restricted to one market)

{rd("tables_mkt.md")}

## 9. Every variant (1 micro, pooled) and every subset of the four strategies
Variant table (IS = first ~8 months, HO = judge window; the picks are the best IS PF with the minimum IS n):

{rd("tables_picks.md").split(chr(10)+chr(10))[1]}

Subsets (first-signal-wins; the IS-best subset is ICT+SMC at IS PF 1.36 but it lost in the judge window; DMI+RSI and ICT+DMI+RSI look best afterwards but that is post-hoc, they were not chosen in-sample):
{rd("tables_subsets.md")}

## 10. Combinations that could work (hypotheses, not proven)
1. **RSI + DMI (+ ICT) on gold, first signal wins**: DMI+RSI judge PF 1.22 / 12-month PF 1.19 / IS PF 1.17 (25K), ICT+DMI+RSI 1.24 / 1.21 / 1.19. The only mixes positive in IS, judge and 12 months at the same time; the strength is diversification (DMI alone judge PF 0.94, RSI 1.05), but it is post-hoc, MGC-driven and MGC is OFF in the plans.
2. **Triple RSI with a 1.5R target (mainly the MGC leg)** as a stand-alone paper-test: the only strategy family positive in IS, judge and 12 months in every variant (pick TriRSI(3,7,14) 15m: 1.13 / 1.13 / 1.13 pooled). Payoff ~1.2 at 46-49% win, so a small edge that needs ~2 years more data.
3. **Per-strategy daily caps** (COMB-4 style) so a quiet, high-quality strategy (ICT/SMC) is not crowded out by the busy ones; here it did not improve results, but it is the right structure if a future ICT/SMC variant shows an edge.
4. **Vote/confluence** has slightly better bootstrap numbers than the other combinations at 25K / 50K (44/56 and 52/46 vs 37/63 and 42/58 for COMB-1; still below NOISE 60/40) but only 58 trades a year; worth re-testing on 2019-2026 (the cached MGC files go back to 2019 as well as MNQ) - which breaks the "last 12 months only" rule, so only if you allow it.
5. The studies' own hypotheses remain open: SuperTrend 15m / DMI direction as a side filter for NOISE, Triple RSI as a "do not chase" guard in NOISE. Combining NOISE with these four was not tested here (NOISE is MNQ-only, one trade a day).
**Rough honest expectation:** with ~0.5-2 trades per day available, profit factors of 1.0-1.2 and 40% win rates, a 2-micro 25K/50K account cannot reach the target before the MLL is hit more often than NOISE does; the 100K/150K accounts only turn that into bigger swings.

## 11. Files
`mlib.py` (loader + 1-micro simulator), `cands.py` (candidate trades per strategy/market, incl. random-direction twins), `port.py` (account selector, stats, eval sim), `repro.py`, `run.py`, `report.py`, `build_results.py`; `out/cands_*.pkl` (45k candidate trades), `out/results.json`, `out/picks.json`, `out/variants_pooled_1micro.csv`, `out/subsets.csv`, `out/trades_COMB-*_25k.csv` (taken trades, 25K sizing), `out/repro.md`, `out/tables_*.md`.
"""
open(HERE + "/RESULTS.md", "w").write(doc)
print(len(doc))
