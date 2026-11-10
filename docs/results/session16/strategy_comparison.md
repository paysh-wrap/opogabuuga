# Session 16 - comparison of every strategy / variant ever tested in Paytience

Read-only synthesis of existing records (nothing re-run, no code changed). Every number is copied from the file named in the last column; "n/a" = not in the records.
**HO** = held-out (2024-01..2026-10/11, not used to pick the rule). **IS** = in-sample (pick period, or a window the rule was tuned/looked at). **SMALL** = tiny sample (22 sessions to ~1 year), anecdotal.
Sizes: 1 micro unless stated. "Pass/bust" = Lucid evaluation pass / bust rate where recorded. DD = max drawdown (account-level where stated).
Source paths are under `docs/results/` unless noted.

## 1. Table

| # | Strategy (decision id) | Markets | Period tested | IS / HO | Trades | Win % | Avg R or R:R / PF | Net $ | Max DD | Eval pass / bust | Status | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **NOISE + profit lock** (D75-P1, N1; +100 pt -> stop entry+10, $250 stop) | MNQ | 2021-11..2023-12 / 2024-01..2026-10 | IS / **HO** | 354 / **424** | 48.0 / **52.1** | PF 1.50 / **1.38**; avg win/loss 1.27 (HO) | $9,260 / **$10,259** | n/a (5y lock stream DD $2,589, worst day -$748; session 11) | HO bootstrap: 50K 77/23, 100K 78/19, 150K 77/18 (sized small); 25K 56/44 | PROPOSED, not built in app (best recommendation) | session15/README.md; session11/final_push/winrate.md |
| 2 | **NOISE plain** (D55; hourly checks, band/VWAP exit, 1% then $250 emergency stop) | MNQ | IS 2019-05..2023-12 (s9) ; HO 2024-01..2026-11 (s9); 2021-11..2026-10 (s15) | IS / **HO** | 727 / **440** (s9); 357 / **446** (s15) | 44.3 / **45.0** (s9); 45.4 / **44.2** (s15) | PF 1.32 / **1.33** (s9); 1.45 / **1.31** (s15); $/tr +25.81 HO | IS +$15.28/tr (s9); HO +$25.81/tr (s9); s15: $8,742 / **$10,188** | -$1,466 IS / **-$2,214 HO** (s9) | Pro 25K HO: **56.9 / 42.2** (s9, 1 micro). Today's setup HO: 25K 47/53, 50K 51/49, 100K 57/43, 150K 48/52 (s15) | LIVE (D55, ON in Pro/Flex) | 2026-11-09_session9_strategy_research.md; session15/README.md |
| 3 | NOISE variants: 30-min checks (N6) / 30-min + lock (N7) | MNQ | 2021-11..2026-10 | IS / **HO** | 470 / **580**; 461 / **540** | 43.4 / **40.3**; 45.6 / **47.0** | PF 1.40 / **1.27**; 1.43 / **1.29** | $8,989 / **$10,262**; $9,218 / **$8,942** | n/a | HO 50K: 60/40 (N6), 67/33 (N7) vs 66/34 plain, 77/23 lock | Rejected (worse accounts) | session15/README.md |
| 4 | NOISE + half off at 0.5R / 1R then BE (N3, N2) - violate R:R>=1.5 | MNQ | 2021-11..2026-10 | IS / **HO** | n/a | 54.1 / **57.8** (N3); 46.8 / **49.0** (N2) | PF 1.35 / **1.17**; 1.43 / **1.22** | $6,216 / **$4,895**; $8,112 / **$6,967** | n/a | HO 50K: 66/34 (N3), 69/31 (N2) | Rejected (halves profit; breaks R:R rule) | session15/README.md |
| 5 | NOISE stop-size grid ($80 / $100 / $120 / $250 / 1%) | MNQ | 5y 2021-11..2026-10 | both halves | 793-970 | 33.0-45.3 | PF 1.26-1.36 | $13,637-$18,930 (5y) | -$2,182..-$2,720 | 25K 5y: 55-57 / 34-37 | $250 chosen (narrow peak, "probably sample-specific") | session10/five_year/singles_report.md; session10/README.md s10,14 |
| 6 | NOISE on MES (N4) | MES | 2021-11..2026-10 | IS / **HO** | 377 / **478** | 44.0 / **40.2** | PF 1.17 / **0.81** | $2,460 / **-$4,186** | n/a | Pro 25K HO (s9): 0 / 71 | FAILED held-out; MES OFF | session15/README.md; 2026-11-09_session9... |
| 7 | NOISE on MGC (N5) | MGC | 2021-11..2026-10 | IS / **HO** | 369 / **436** | 41.2 / **38.5** | PF 0.93 / **1.17** | -$533 / **$3,414** | n/a | n/a | FAILED IS; MGC OFF (s9: PF 0.73-0.95) | session15/README.md |
| 8 | NOISE + MYM / M2K (second market) | MYM, M2K | 2021-10..2026-10 | both halves | 1,317 / 1,292 (NOISE+fade) | 43.8 / 43.8 | PF 0.89 / 0.97 | -$4,232 / -$926 | -$4,785 / -$2,254 | n/a | FAILED (MES 5y PF 1.02, HO 0.94 too) | session11/final_push/second_market.md |
| 9 | **NOISE + afternoon (PM) fade, hindsight rule** (D55/D58, since refuted) | MNQ | 2021-11..2026-10 | IS / HO | 564 / 727 | 48.6 / 51.0 | PF 1.30 / 1.34 | $9,363 / $15,982 | $1,538 / $2,591 | 25K 5y 56-66 / 31-35; HO 57-66/33-42 | Look-ahead bias: replaced by row 10 | session10/README.md; session14/causal_projections.md |
| 10 | **NOISE + PM fade, CAUSAL (current live rule)** | MNQ | 2021-11..2026-10 | IS / **HO** | 578 / **740** | 47.2 / **50.0** | PF 1.18 / **1.24** | $6,269 / **$12,270** (5y $18,539, -27% vs hindsight) | n/a | 25K Regular 45 pass, 55 frozen; HO 40% pass; 150K 49/47 | LIVE (fade slated OFF, D81) | session14/causal_projections.md |
| 11 | PM fade alone, causal (session 14 / D81) | MNQ | same | IS / **HO** | 549 (5y) | 51.3 / **57.5** (5y 54.8) | PF 0.85 IS / **1.09 HO**, 5y 0.99 | -$2,177 / **+$1,744** (5y -$432) | n/a | n/a | No edge -> switch OFF (proposed) | session14/causal_projections.md; session15/README.md |
| 12 | NOISE + PM fade, hindsight "NOISE-free days" 1y | MNQ | 2025-11..2026-10 | **HO**, SMALL | 91 (fade) | 57.1 | PF 1.56 | +$2,765 (fade only) | -$903 | 75 / 0 (91 trades) | Superseded by row 11 | session10/README.md s6 |
| 13 | Opening-drive pullback (OPEN_DRIVE, paper button) | MNQ | 2021-11..2026-10 | IS / **HO** | 66 / **107** | 57.2 (5y) | PF 1.00 / **1.24**; 5y 1.16 | -$5 / **+$1,455** (5y $1,449) | -$1,104 (5y) | pass 0.3% (alone) | Paper accounts only; not promoted | session10/five_year/singles_report.md; session10/README.md |
| 14 | Opening-range breakout (ORB), many variants incl. Zarattini ZAR5 | MNQ, MGC | 2019-05..2023-12 / 2024-01..2026-11 | IS / **HO** | 718 / **419** (IS-picked B30_2.5+on) | 46.4 / **44.6** | exp 0.113R / **0.012R**; PF 1.25 / **1.03** | $/tr +16.90 / **-3.58** | n/a | ORB IS pick, Pro 25K: 34.3 / 63.5 | FAILED (39 variants); s15 O3: 18-25% win | session9/reports/orb.md; session15/README.md |
| 15 | ORB 15-min 1.5R | MNQ | 2025-11..2026-10 | **HO**, SMALL | 226 | 43.4 | PF 0.90 | -$3,068 | -$8,526 | n/a | FAILED | session10/README.md s5 |
| 16 | Last-half-hour momentum | MNQ | 2021-11..2026-10 | IS / **HO** | 491 / 645 | 48.6 (5y) | PF 0.79 / **1.09** | -$3,614 / **+$2,076** (5y -$1,538) | -$4,657 (5y) | n/a | FAILED (sign flips) | session10/five_year/singles_report.md; session9 |
| 17 | Overnight Asia-range breakout / London-session NOISE | MNQ | 1y; 5y; 2024-26 | mixed | 0.79/day (1y); n/a | 45.7 (1y); London HO 36.9 / 32.5 | PF 0.96 (1y); London HO 0.92 / 0.87 | -$634 (1y); 5y -$5,532 | -$3,751 (1y) | NOISE+overnight 1y 19/81 | FAILED | session10/README.md; 2026-11-09_session9... |
| 18 | Mean-reversion family (VWAP-band fade, RSI(2), gap fill, PDH/PDL sweep, opening-drive pullback) | MNQ, MGC (and MES in s15) | 2019-05..2026-11 (s9); 2021-11..2026-10 (s15, 21 ideas) | IS / **HO** | 38 variants (s9) | 60-69 exist but lose; s15: V1 37% / O1 43% etc. | best IS pick PDH/PDL: IS +0.04R, **HO -0.34R, PF 0.62**; s15 all PF 0.66-1.18 | negative after costs (MNQ gap fill HO -$5,236) | n/a | n/a | FAILED (all) | session9/reports/meanrev.md; session15/README.md |
| 19 | Gold session-structure family (Asian/London/COMEX ranges, sweeps, fix fade, 20d trend) | MGC | 2019-05..2026-11 | IS / HO | 36 variants | sweep-reversal ~31 | all 36 negative IS | negative | n/a | n/a | FAILED | session9/reports/gold.md |
| 20 | VWAP trend (1m/5m) | MNQ, MGC | 2019..2026 | IS / HO | 6 variants | 21-35 | PF <= 1.09 | n/a | n/a | n/a | FAILED | 2026-11-09_session9... |
| 21 | **LunqFX fractal confluence, D36/D37 "58%" plan** (Intraday H1, 1R mix) | MGC, MNQ | 22 sessions (Oct-Nov 2026); re-measured 2024-11..2026-10 | IS (22 s) / **HO 2y** | 24 (MGC), 9 (MNQ) SMALL; **391 (2y engine)** | 58 / 44 SMALL; **43** (2y) | PF 1.69 / 0.93 SMALL; **0.87** (2y) | +$324 / -$16 SMALL; **-$1,201** (2y) | n/a | n/a | RETIRED/refuted; 84% of trades aimed <1.75R (root cause D36/D36b) | 2026-11-06_backtests.md B, P, Q |
| 22 | LunqFX Intraday at fixed 1.75R, offline screen | MGC, MNQ | 22 sessions | IS+test SMALL | 66 / 60 setups | 19/26; 7/12 (MGC; MNQ) | -0.43R/-0.24R; -0.79R/-0.59R | n/a | n/a | n/a | FAILED (60% at 1.75-3R not reached) | 2026-11-06_backtests.md H |
| 23 | LunqFX engine, "r175" and "r175brk" | MGC, MNQ | 22 sessions | SMALL | 16 / 6 (MGC) | 38 / 50 | PF 1.32 / 2.27; +0.32R / +0.73R | +$151 / +$173 | n/a | n/a | Too few trades | 2026-11-06_backtests.md I |
| 24 | **D47 main** (UT Bot 5m + EMA200 5m + T2>=1.75R) | MGC | picked 2019-23; engine 2024-11..2026-10 | IS offline / **HO engine** | 60 / 44 offline; **65** engine | 43 / 39 offline; **40** engine | offline -0.01R / -0.01R; engine **PF 1.34, +0.13R** | **+$594** (engine, 2y) | n/a | n/a | Superseded by D49 | 2026-11-06_backtests.md P |
| 25 | **D49 trend-aligned 1.5-2.5R** (main strategy per CLAUDE.md) | MGC + MNQ + MES | 2024-11..2025-08 (10 months, engine) | HO (not used to pick) but SMALL | **72** (33/25/14) | **39** (36/44/36) | PF 1.45; +0.21R/trade (MGC 1.14, MNQ 1.94, MES 1.32) | **+$978** (MGC +142, MNQ +696, MES +140) | n/a | n/a | Not re-measured over multi-year; superseded in practice by NOISE (D55) | 2026-11-06_backtests.md R |
| 26 | D52 final plan Normal / Lower risk (LunqFX engine, trend filter on MGC) | MGC, MNQ | 2025-11..2026-10 | HO, SMALL | 216 / 226 (both) | MGC 32-33; MNQ 34-36 | PF 1.16 / 1.22 (MGC); 1.12 / 1.03 (MNQ) | +$777 (Normal) / +$391 (Lower risk) | n/a | n/a | Lower-risk kept as option | 2026-11-06_backtests.md T |
| 27 | User's original spec | MNQ | 2025-11..2026-10 | HO, SMALL | 13 | 46 | PF 2.22; +0.64R | +$458 | worst day -$65 | n/a | Too rare (~1/month) | 2026-11-06_backtests.md S |
| 28 | LunqFX candidate pool + OB filter (D76) | MNQ | 22 sampled months | IS / **HO** | 508 / **675** baseline; 440 / **603** w/ OB filter | 54.7 / **53.9**; 65.9 / **62.9** | baseline HO PF ~0.88 | **-$11,555 / -$27,322** baseline; +$4,736 / **-$5,724** filtered | n/a | n/a | OB filter lifts win rate but still LOSES; stays OFF (shadow) | session12/LUNQFX.md |
| 29 | LunqFX fractal (15m/60m) and MSO structure/divergence gates ON NOISE | MNQ | 2021-11..2026-10 | IS / **HO** | n/a | 52.9-59.2 HO | n/a | HO profit down 36-66% | n/a | n/a | Rejected | session13/README.md |
| 30 | OB / SMT filters or OB stop anchor on NOISE + fade (D76) | MNQ (+MES for SMT) | same | IS / **HO** | 727 base | HO 50.2-53.1 (SMT) | n/a | SMT: profit -23..-65% HO | n/a | n/a | Not enabled (shadow log) | session12/README.md |
| 31 | Scalp mode (D38) | MNQ, MGC | 22 sessions; 35 months 2024-01..2026-11 | SMALL; **HO (OOS 2024, 2025)** | 18 / 25 SMALL; 628 (35 mo) | 56 / 40 SMALL; 39-50 | PF 1.22 / 0.45 SMALL; **0.67-0.96** | +$30 / -$187 SMALL; **about -$1,465 over 35 mo** | $456-$813 per half | n/a | RETIRED (D43) | 2026-11-06_backtests.md B; 2026-11-06_results_K_mnq_scalp.md |
| 32 | 1:1 mode (D7/D38) | MGC, MNQ | 22 sessions | SMALL | 36 / 22 | 50 / 45 | PF 0.61 / 0.72 | -$304 / -$126 | n/a | n/a | RETIRED (D43) | 2026-11-06_backtests.md B |
| 33 | Low risk mode | MGC, MNQ | 22 sessions; 1y | SMALL | 41 / 24 | 49 / 38 | PF 1.04 / 0.83 | +$26 / -$92 | n/a | n/a | Kept as option ("Lower risk") | 2026-11-06_backtests.md B, T |
| 34 | Squeeze Momentum 5m+15m filter (D45) | MGC | 4 mo (Jul-Oct 2026); 7y 2019-2026 | 4 mo SMALL; 7y both halves | 45 (4 mo); 325 / 435 (7y) | 43-54 (4 mo); 30 / 33 (7y) | 4 mo +0.07R/+0.46R; **7y -0.30R / -0.18R** (1.75R target) | n/a | n/a | n/a | FAILED (fluke); OFF | 2026-11-06_backtests.md N, O |
| 35 | Trend filters D44 (VWAP, EMA200 5m, UT Bot 5m) at fixed 1.75R | MGC | 7y 2019-2026 | older / newer half | 766 / 891 (UT Bot) | 37 / 33 (UT Bot); EMA200 34 / 31; VWAP 35 / 30 | -0.14R/-0.20R (UT Bot); best pair -0.02R / -0.12R | n/a | n/a | n/a | No filter reaches 50%; EMA200+UT Bot kept as D47/D49 gate | 2026-11-06_backtests.md O, P |
| 36 | TradingAgents + Vibe-Trading daily bias (D50-D53, D72, D74) | MNQ, MGC | estimates only (no real LLM backtest allowed) | hindsight / simulated | n/a | NOISE needs ~70% accuracy to break even as gate; published 50-56% | at 55%: NOISE gate $7,069 vs $11,358 without (s9); +0.0..+0.5 pt win (s13) | AI sizing (D74): +$11 (100K) / +$1 (150K) per 2 wk at 55%; neg on 25K | n/a | n/a | ADVISORY; no live ledger rows yet | 2026-11-09_session9...; session13/README.md; session14/causal_projections.md |
| 37 | AI-only strategy (D56), hindsight upper bound | MNQ | 2025-11..2026-10 | simulated (not a backtest) | 248 sessions | 50% acc: 39; 70%: 54; 100%: 77 | PF 1.05 / 1.94 / 5.33 | +$1,866 / +$27,601 / +$66,202; worst trade -$314 | n/a | n/a | Paper only, default OFF | session10/README.md s3 |
| 38 | NOISE + MES combined (one position per account) | MNQ + MES | 2024-01..2026-11 | **HO** | n/a | 41.8 | PF 1.17 | +$11.24/tr | n/a | 29 / 71 | FAILED (worse than MNQ alone) | 2026-11-09_session9... |

Account-level result of the NOISE family (session 15, held-out bootstrap, NOISE+lock, small sizes): Pro 150K 3 micros (1 under $2,250 cushion) pass 77%, eval bust 18%, funded yr-1 bust 11%, about $79 per 2 weeks per account; today's NOISE-alone on same plan 48 / 52 / 46%, $52. Pro 25K cannot meet the limits (best 56/44, 62% funded bust).

## 2. Ranked list (best -> worst, honest held-out results only)

1. **NOISE + profit lock (MNQ)** - HO 424 trades, 52% win, PF 1.38, +$10,259; the only idea that improves on plain NOISE in both periods and the one that makes prop accounts survive; proposal only, not in app.
2. **NOISE plain (MNQ, live)** - HO 440-446 trades, 44-45% win, PF 1.31-1.33; a real, repeatable, positive edge, but 40-50% of Lucid evaluations bust at live sizes.
3. **NOISE + causal PM fade (current live combo)** - HO PF 1.24, +$12,270, but the fade part adds nothing causally (IS -$2,177), so this is NOISE with extra noise.
4. **Opening-drive pullback** - HO PF 1.24 on 107 trades (+$1,455), but flat in-sample and too few trades; paper only.
5. **D49 / D47 trend-aligned 1.5-2.5R (MGC/MNQ/MES)** - small positive (PF 1.34-1.45, +$594/+$978) on 2024-25 data but only 44-72 trades; never confirmed on multi-year data and effectively superseded.
6. **Last-half-hour momentum / ORB / overnight / London** - HO PF 1.0-1.1 at best, negative in-sample or most years; costs eat it.
7. **LunqFX fractal confluence (all modes, MGC+MNQ)** - looked good on 22 sessions (58%, PF 1.69), but 2 years of engine data show PF 0.87 / -$1,201; with the OB filter win rate rises to 63% but it still loses money.
8. **Intraday / Low risk / D36-D37 "58%" plan** - same family as 7; 84% of trades aimed below 1.75R; retired as the main plan.
9. **Scalp, 1:1, Squeeze (D45), trend filters alone, VWAP trend, mean reversion, gold structure, NOISE on MES/MGC/MYM/M2K** - PF below 1 on held-out data (Scalp 0.67-0.96 over 35 months; Squeeze -0.18R at 1.75R; mean reversion HO -0.34R).
10. **TradingAgents / Vibe-Trading bias, AI-only** - not testable on the past; at realistic 50-56% accuracy it adds about +0 to +0.5 win-rate points while cutting trades; no real ledger yet.

## 3. Conclusions (plain language)

- **Only one family has a verified, repeatable edge: NOISE on MNQ** (hourly noise-band momentum). It is positive in both pick and held-out years (PF about 1.3-1.4), including after 1-tick slippage and fees. Everything outside that family that was tested on multi-year data failed.
- **The win rate users asked for (58-70%) was never reached with a real edge.** The best honest figure is 52% (NOISE + profit lock, held-out). Every 55-65% result either was a 22-session fluke (the old "58%" plan), needed targets below 1.5R, or lost money anyway.
- **Small samples lied repeatedly.** 22 sessions gave 58-71% for LunqFX, 4 months gave 54% for Squeeze, 1 year gave 57% for the fade; the 2-7 year re-tests gave PF 0.87, -0.18R and PF 0.99. Treat anything under about 100 trades or one regime as unproven.
- **Hindsight and tuning inflated several results:** the afternoon fade (-27% profit once made causal), IS-picked filters (ORB, trend pairs, PDH/PDL) and 22-session indicator screens. After correction, only the lock (a stop move, picked then judged) survived.
- **Account survival, not win rate, decides Lucid outcomes.** The same NOISE trades pass 48-57% of evaluations at live sizes but 77% when sized small with a cushion brake (150K, 3 micros, 1 under $2,250); Pro 25K cannot be made safe, and MNQ at ~23,000 swings more dollars per micro than at 13,700, so sizes must be re-checked as the index rises.

## Caveats
Rows mix different data (Yahoo 22 sessions vs Databento 5-7y), periods, plans and cost models; compare PF and win rate only within the same source. "Eval pass / bust" definitions differ between sessions 9, 10, 14 and 15 (bootstrap vs rolling start; session 15 counts intraday touch and frozen accounts as dead). News blackouts, eval fees and gap slippage are not modelled in most records. Row 2 IS net $ for session 9 was not stated as a total in the record (only +$15.28/tr), so it is left as per-trade only.

## 4. Most-recent-1-year view (2025-11..2026-10, 1 micro; all HO / SMALL = one regime)
Only records that cover this window are shown with 1-year figures. "1-yr n/a" = records have only multi-year totals (shown instead, see section 1).

| Strategy | Markets | 1-yr trades | Win % | PF | Net $ | Max DD | Pro 25K pass / bust | Status | Source |
|---|---|---|---|---|---|---|---|---|---|
| NOISE ($250 fixed stop) | MNQ | 160 | 43.8 | 1.21 | +$2,948 | -$2,228 | 45 / 56 | LIVE | session10/README.md s9 |
| NOISE (1% stop) | MNQ | 153 | 45.1 | 1.16 | +$2,319 | -$2,214 | 48 / 47 | LIVE (older stop) | session10/README.md s5 |
| NOISE + PM fade, HINDSIGHT rule (optimistic) | MNQ | n/a (0.98/day) | 49.6 | 1.26 | +$5,084 | -$2,914 | 51 / 45 | refuted by causal re-test | session10/README.md s6 |
| NOISE + profit lock | MNQ | 1-yr n/a (HO 2024-26: 424 tr, 52.1%, PF 1.38, +$10,259) | | | | | 1-yr n/a | PROPOSED | session15/README.md |
| NOISE + causal PM fade | MNQ | 1-yr n/a (HO: 740 tr, 50.0%, PF 1.24, +$12,270) | | | | | 1-yr n/a | LIVE (fade to be OFF) | session14 |
| Opening-drive pullback | MNQ | 45 | 55.6 | 1.18 | +$590 | -$1,104 | n/a | paper only | session10/README.md s5 |
| Last-half-hour momentum | MNQ | 226 | 46.0 | 1.13 | +$1,173 | -$1,937 | n/a | failed multi-year | session10/README.md s5 |
| ORB 15-min 1.5R | MNQ | 226 | 43.4 | 0.90 | -$3,068 | -$8,526 | n/a | failed | session10/README.md s5 |
| Overnight Asia breakout | MNQ | ~0.79/day | 45.7 | 0.96 | -$634 | -$3,751 | 30 / 70 | failed | session10/README.md s6 |
| LunqFX engine, D52 Normal (MNQ, every setup) | MNQ | 169 | 36 | 1.12 | +$562 | n/a | n/a | shadow/legacy | 2026-11-06_backtests.md T |
| LunqFX engine, D52 Normal (MGC, trend filter) | MGC | 47 | 32 | 1.16 | +$215 | n/a | n/a | legacy | 2026-11-06_backtests.md T |
| LunqFX Lower-risk (MNQ+MGC) | both | 226 | MNQ 34 / MGC 33 | 1.03 / 1.22 | +$391 | n/a | n/a | option | 2026-11-06_backtests.md T |
| Original spec | MNQ | 13 | 46 | 2.22 | +$458 | worst day -$65 | n/a | too rare | 2026-11-06_backtests.md S |
| AI-only (hindsight bound, not a backtest) | MNQ | 248 sessions | 39 (50% acc) / 54 (70%) | 1.05 / 1.94 | +$1,866 / +$27,601 | n/a | n/a | paper only | session10/README.md s3 |
| D49 trend-aligned 1.5-2.5R, D47, "58%" plan, Scalp, 1:1, Squeeze, trend filters, NOISE on MES/MGC, mean reversion, gold, ORB multi-year | various | 1-yr n/a (see section 1 multi-year figures) | | | | | | retired / failed | section 1 |

1-year ranking by net $: NOISE $250 (+$2,948) > NOISE 1% (+$2,319) > LHH (+$1,173) > Opening drive (+$590, best win rate 55.6%) > LunqFX MNQ (+$562) > ORB/overnight (losers). The last year was NOISE's weakest (PF 1.16-1.21 vs 1.31-1.33 HO average), and its 45-56% bust rate on Pro 25K at 1 micro stands. Same one-year conclusion as the multi-year view: only NOISE is both profitable and the largest earner.
