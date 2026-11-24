# Held-out tests of improvement ideas (2026-11-24, research only)

Nothing in the app was changed. Nothing was committed.

## Verdict

| idea | pick-window choice | judge result | verdict |
|---|---|---|---|
| 1. 30-min NOISE entry checks (exits stay hourly) | E30a (10:00-15:30) | net $8,285 vs $10,826, PF 1.30 vs 1.50 | **REJECT** |
| 2. Volatility-targeted sizing (1-3 micros) | none: worse than fixed 2 micros on the pick window | FYI: more $, but lower Sharpe, higher drawdown, no timing skill | **REJECT** |
| 3. CANDACE regime gate (noise sigma / opening range) | G3 (opening range >= median) | net $698 vs $814 (PF 1.33 vs 1.18), below random p95 | **REJECT** |
| 3b. VIX gate (FRED, added mid-task) on NOISE / CANDACE | NOISE: none. CANDACE: G5 (VIX >= median) | CANDACE G5: 20 judge trades, net $534 vs $814 | **REJECT** |
| 4. Leg priority NOISE-first | none: worse on the pick window | judge -$170 | **REJECT** |
| 5. GitHub ports of the paper | not run | the paper differences they would show are ideas 1 and 2 | not tested |

**Nothing passes. Keep the shipped settings.**
Total variants tried: **12** (idea 1: 2, idea 2: 1, idea 3: 4, idea 3b: 4, idea 4: 1). With 12 tries, about one false "win" at the 10 % level is expected by chance. None appeared.

**Decay check (lead's request).** Our MNQ NOISE shows **no measurable decay** on average: pick PF 1.55 / $28 per trade, judge PF 1.50 / $30 per trade. But the judge profit is lumpy: half of it came from 2024 H2. Without that half-year the judge PF is 1.29. The last 16 months (PF 1.48) sit only just above the random-direction 95th percentile (1.46). So the edge is still there, but it is thinner and more uneven than the 5-year average suggests. Costs are not the problem on MNQ: $4 per micro instead of $2 cuts judge profit by 7 %.

## Rules used

- Data: `/home/user/days.pkl`, MNQ 1-min RTH bars. Pick = 2021-10-21..2023-12-31 (the first 14 days are history). Judge = 2024-01-01..2026-10-30.
- Costs $2 per micro round trip ($1 fee + 1 tick each side). Entry at the next bar open. Stop checked first.
- Pass needs all of: judge net up, judge PF up, at least 60 judge trades, and a win over the pre-set random control.
- Choices were made on the pick window only. They were saved in `prereg.json` / `prereg_extra.json` before any judge number was computed.

## Step 0: baseline reproduction

| stream | check | pick: trades / PF / net | judge: trades / PF / net |
|---|---|---|---|
| NOISE shipped (1 micro) | 654 trades, $19,293 = session 20 BASE; **trade-for-trade identical** to `session20/strategy_review/streams_BASE.csv` | 298 / 1.55 / $8,468 | 356 / 1.50 / $10,826 |
| CANDACE keep_all ON (D154) | IS 160 / +$1,030 / PF 1.27, J 150 / +$814 / PF 1.18 = `candace_keep_sweeps` V1 | 154 / 1.27 / $1,016 (from 10-21) | 150 / 1.18 / $814 |
| Late-day leg (D166, app-faithful) | PF 1.44 pick / 1.10 judge = `new_edge/late_leg_sizes` | 465 / 1.44 / $6,710 | 602 / 1.10 / $2,578 |

The NOISE generator is the session-20 one. I copied it with one change: entry checks and exit checks are separate inputs. With the default inputs it gives the same 654 trades.

## Duplicate check (what was already tested)

- 30-min checks for entries AND exits: tested in sessions 9, 11, 15 (N6/N7). Worse. Extra exit checks only: session 20 F5. Worse. **Entry-only 30-min checks were never tested**, so idea 1 was run.
- Volatility sizing: session 10 (`five_year/vol_sizing_report.md`) tested it on funded payouts. No gain. Idea 2 was rerun once, cheaply, at trade level with Sharpe and drawdown, as asked.
- CANDACE regime gate: never tested. Note: the premise "CANDACE lost 2021-23" is true only for the old engine. With keep_all ON (shipped), CANDACE made +$1,030 in 2021-23.
- Leg priority: never measured.

## Pre-registration

| idea | variants | pick rule | random control |
|---|---|---|---|
| 1 | E30a: entries every 30 min 10:00-15:30. E30b: every 30 min 10:00-15:00. Exits hourly in both. | pick PF and net >= base; take the highest pick net | (a) above p95 of the random-direction version (500 seeds); (b) gain over base above p95 of random-direction gains |
| 2 | VT: q = clip(round(2 x target / vol14), 1, 3) micros. vol14 = std of the last 14 daily returns. target = pick median (1.41 %). Pro 50K frame: base = fixed 2 micros at $250 (3 x $250 = $750, under the $1,000 per-trade cap). | pick net >= base and pick Sharpe > base | gain above p95 of 2,000 shuffles of the same sizes |
| 3 | G1/G2: trade only if sig10 (prior 14-day noise sigma at 10:00) is >= / < its pick median. G3/G4: same for or5 (09:30-09:34 range / 14-day average range; every CANDACE entry is at bar 5 or later, so no lookahead). | pick trades >= 60, pick PF > base, pick net >= base; take the highest pick PF | above p95 of 5,000 random subsets of the same size |
| 3b | V1/V2: NOISE only if the prior-day VIX close is >= / < the pick median (20.3). G5/G6: same for CANDACE. | same as 3 | same as 3 |
| 4 | P1 NOISE-first: if NOISE signals while CANDACE or late-day holds the account, flatten that position at the NOISE bar open; NOISE fills one bar later (D139 wait-for-flat). Base = shipped first-come, NOISE wins same-bar ties. | pick net and PF >= base (NOISE + CANDACE) | gain above p95 of gains with a random-direction NOISE stream (500 seeds) |

Pick-window results: idea 1 picked E30a. Idea 2 had no pick. Idea 3 picked G3. Idea 3b picked G5 for CANDACE and nothing for NOISE. Idea 4 had no pick.

## Pick vs judge (1 micro unless stated; max DD = closed-trade drawdown)

| idea | variant | window | trades | win % | PF | net $ | $/trade | max DD $ | Sharpe |
|---|---|---|---|---|---|---|---|---|---|
| 1 | base (hourly) | pick | 298 | 48.0 | 1.55 | 8,468 | 28.4 | 944 | 1.83 |
| 1 | base (hourly) | judge | 356 | 54.2 | 1.50 | 10,826 | 30.4 | 2,096 | 1.45 |
| 1 | **E30a (pick)** | pick | 360 | 49.2 | 1.60 | 10,514 | 29.2 | 1,111 | 2.08 |
| 1 | **E30a (pick)** | judge | 427 | 48.7 | **1.30** | **8,285** | 19.4 | 2,192 | 1.04 |
| 1 | E30b | pick | 343 | 47.8 | 1.58 | 9,786 | 28.5 | 1,227 | 1.96 |
| 1 | E30b | judge | 412 | 49.3 | 1.35 | 9,211 | 22.4 | 1,852 | 1.16 |
| 2 | base 2 micros | pick | 298 | 48.0 | 1.55 | 16,935 | 56.8 | 1,888 | 1.83 |
| 2 | base 2 micros | judge | 356 | 54.2 | 1.50 | 21,651 | 60.8 | 4,193 | 1.45 |
| 2 | VT (no pick) | pick | 298 | 48.0 | 1.51 | 15,460 | 51.9 | 2,832 | 1.72 |
| 2 | VT (no pick) | judge | 356 | 54.2 | 1.52 | 27,716 | 77.9 | 5,786 | 1.43 |
| 3 | CANDACE base | pick | 154 | 41.6 | 1.27 | 1,016 | 6.6 | 478 | 0.81 |
| 3 | CANDACE base | judge | 150 | 37.3 | 1.18 | 814 | 5.4 | 504 | 0.45 |
| 3 | G1 sig10 high | pick / judge | 76 / 32 | 38.2 / 37.5 | 1.06 / 1.56 | 128 / 600 | | 631 / 288 | |
| 3 | G2 sig10 low | pick / judge | 78 / 118 | 44.9 / 37.3 | 1.58 / 1.06 | 888 / 213 | | 362 / 660 | |
| 3 | **G3 or5 high (pick)** | pick | 78 | 43.6 | 1.77 | 1,319 | 16.9 | 440 | 1.29 |
| 3 | **G3 or5 high (pick)** | judge | 70 | 40.0 | 1.33 | **698** | 10.0 | 508 | 0.53 |
| 3 | G4 or5 low | pick / judge | 76 / 80 | 39.5 / 35.0 | 0.85 / 1.05 | -304 / 116 | | 976 / 874 | |
| 3b | NOISE V1 VIX high | pick / judge | 141 / 53 | 46.1 / 54.7 | 1.54 / 0.87 | 4,764 / -515 | | 840 / 1,642 | |
| 3b | NOISE V2 VIX low | pick / judge | 157 / 303 | 49.7 / 54.1 | 1.56 / 1.63 | 3,703 / 11,340 | | 666 / 1,638 | |
| 3b | **CANDACE G5 VIX high (pick)** | pick / judge | 79 / **20** | 46.8 / 45.0 | 1.61 / 1.81 | 1,208 / **534** | | 401 / 400 | |
| 3b | CANDACE G6 VIX low | pick / judge | 75 / 130 | 36.0 / 36.2 | 0.89 / 1.07 | -192 / 279 | | 439 / 642 | |
| 4 | NOISE+CANDACE P0 (shipped) | pick | 442 | 46.4 | 1.53 | 9,714 | 22.0 | 980 | 2.05 |
| 4 | NOISE+CANDACE P0 (shipped) | judge | 499 | 49.5 | 1.46 | 11,788 | 23.6 | 1,870 | 1.55 |
| 4 | P1 NOISE-first (no pick) | pick | 451 | 45.7 | 1.49 | 9,320 | 20.7 | 1,006 | 1.96 |
| 4 | P1 NOISE-first (no pick) | judge | 506 | 49.4 | 1.44 | 11,618 | 23.0 | 2,192 | 1.50 |
| 4 | + late leg, P0 | pick / judge | 763 / 947 | 48.9 / 47.8 | 1.48 / 1.31 | 14,108 / 13,896 | | 1,170 / 1,902 | |
| 4 | + late leg, P1 | pick / judge | 771 / 952 | 48.4 / 47.9 | 1.46 / 1.31 | 13,712 / 13,970 | | 1,170 / 1,990 | |

All rows: `pick_judge_table.csv`. Full numbers: `results.json`, `extra_results.json`.

## Random controls and uncertainty

| idea | control result | passes? |
|---|---|---|
| 1 E30a | Judge PF 1.30 is at the 97th percentile of random-direction E30a (p95 1.28). So the edge exists. But the gain over hourly is -$2,541. Random gains average +$1,506 (p95 +$9,631). The change itself adds nothing. Paired 95 % CI of the judge gain: -$5,752 to +$530. | no |
| 2 VT | Judge $27,716 sits at the 56th percentile of shuffled sizes (p95 $31,789). The extra money only comes from larger average size in calm 2024-26 (2.52 micros vs 2.08 in pick), not from timing. Sharpe 1.43 vs 1.45. Max DD $5,786 vs $4,193 (+38 %). | no |
| 3 G3 | 72nd percentile of random subsets (p95 $1,265). | no |
| 3b G5 | 20 judge trades (< 60). Net below base. | no |
| 4 P1 | Judge gain -$170, 36th percentile of random (p95 +$998). Paired 95 % CI: -$1,733 to +$1,843. | no |

Other notes:
- E30 by year: it beat hourly only in 2023 (PF 1.83 vs 1.60). It lost in 2022, 2024, 2025 and 2026. Pick-window gains were mostly 2023.
- VIX V2 (NOISE only when VIX is low) looks good in judge (PF 1.63, +$514) but it lost on the pick window, so it was not picked. The judge window was mostly low-VIX (303 of 356 trades), so this is not evidence. Do not chase it.

## Leg interaction (idea 4, measurement)

- CANDACE blocks a NOISE entry **16 times in 5 years** (7 in judge). All at the 10:00 check. CANDACE trades end by 10:15.
- NOISE blocks CANDACE once in 5 years.
- The late-day leg can never block NOISE under hourly checks. NOISE's last entry is at the same 15:00 bar and wins the tie.
- **NOISE blocks the late-day leg 298 times in 5 years (154 of 602 judge signals, 26 %).** That matters for any late-leg study. The combined late leg is smaller than its standalone numbers.
- Taking NOISE first does not help. The 16 flattened CANDACE trades were worth about as much as the NOISE trades that replaced them.

## Decay check (requested mid-task)

Quarterly and rolling numbers: `decay_quarterly.csv`, `decay_rolling.csv` (6 and 12 months).

| segment | trades | win % | PF | net $/micro | $/trade | Sharpe | $/month |
|---|---|---|---|---|---|---|---|
| pick 2021-10..2023-12 | 298 | 48.0 | 1.55 | 8,468 | 28.4 | 1.83 | 311 |
| 2024 H1 | 70 | 48.6 | 1.07 | 276 | 3.9 | 0.33 | 45 |
| 2024 H2 | 66 | 65.2 | 2.98 | 5,298 | 80.3 | 4.08 | 843 |
| 2025 H1 | 54 | 50.0 | 0.92 | -332 | -6.1 | -0.32 | -54 |
| 2025 H2 | 59 | 45.8 | 1.34 | 1,333 | 22.6 | 0.90 | 212 |
| 2026 (to 10-30) | 107 | 57.9 | 1.56 | 4,250 | 39.7 | 1.60 | 411 |

Rolling 12-month PF: 1.5-1.8 through 2023, 1.32 in spring 2024, 1.96 in early 2025, **low of 1.04 in January 2026**, back to 1.59 by October 2026. Trades per quarter are stable (about 30-38).

Cost sensitivity (NOISE, 1 micro):

| cost per micro RT | pick PF / net | judge PF / net | 2025-07..2026-10 PF / net |
|---|---|---|---|
| $2 (model) | 1.55 / $8,468 | 1.50 / $10,826 | 1.48 / $5,584 |
| $3 | 1.52 / $8,170 | 1.48 / $10,470 | 1.47 / $5,418 |
| $4 | 1.50 / $7,872 | 1.46 / $10,114 | 1.45 / $5,252 |

Plain answer: **is our edge decaying? Not measurably, but it is not as solid as the average says.**
- The judge average ($30/trade) is no lower than the pick average ($28). The 95 % CI of that difference is -$30 to +$34 per trade. So the data cannot rule out a fall to about zero, or a big rise.
- A straight-line trend on quarterly $/trade gives -$0.5 per year (standard error $5.7). That is flat.
- The judge window depends on one strong half-year (2024 H2: 49 % of judge profit). Without it the judge PF is 1.29.
- Since 2025-07 the PF is 1.48. Random-direction NOISE scores PF 1.12 on average and 1.46 at p95 in the same months, so the recent edge is only borderline above luck.
- Costs do not explain anything here. MNQ trades are large in points, so going from $2 to $4 cuts judge profit by only 7 %. This is unlike the SPY rebuilds the lead cited. Our version also uses fixed size, not 2 % vol sizing. Idea 2 shows vol sizing would not help us either, which matches the "refined version trailed the plain one" report.
- What to watch: a rolling 12-month PF below 1.1 for two quarters in a row. That happened once (late 2025 to early 2026) and it recovered.

## Caveats

- The 2024-26 judge window was seen by earlier sessions, so it is not a pristine holdout. Every reject here is still a reject.
- News blackouts are not modelled. VWAP is the precomputed series. NOISE trades blocked by another leg are dropped and the rest of the NOISE day is unchanged. This matches the app: the NOISE signal is account-independent.
- P1 flattening uses the bar open and a one-bar NOISE delay. If a NOISE trade stopped out on its own entry bar, the shift is approximate (rare).
- VIX: FRED VIXCLS, prior-day close, so it is known before the open. Stored as `VIXCLS.csv` (free source, downloaded 2026-11-24). yfinance was not needed.

## Files

`hot_lib.py` (loader, generator, stats, bootstrap) · `run_all.py` (ideas 1-4 + controls) · `run_extra.py` (decay check + VIX gates) · `prereg.json`, `prereg_extra.json` (frozen picks) · `results.json`, `extra_results.json` · `pick_judge_table.csv` · `noise_base_trades.csv` · `decay_quarterly.csv`, `decay_rolling.csv` · `VIXCLS.csv`. Run order: `python3 run_all.py; python3 run_extra.py` (about 4 minutes in total).
