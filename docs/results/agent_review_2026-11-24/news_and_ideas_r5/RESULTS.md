# News releases and idea search, round 5 (research only, 2026-11-24)

No app code changed, nothing pushed. Scripts: `build_dates.py`, `run_news.py`, `run_ideas.py`. Prereg: `prereg.json`, `prereg_part2.txt` (written before any judge number). Data: `/home/user/days.pkl` MNQ 1-min RTH; pick 2021-10..2023-12, judge 2024-01..2026-10; $2 per micro round trip. NOISE = session-20 generator (654 trades, net $19,293, reproduced exactly); CANDACE = `pass_faster_c125/streams_candace_base.csv` (310 trades); late-day = `new_edge/late_leg_sizes/trades_app.csv` (1,067).

## 1. Dates (file: `dates_us_releases.csv`, 369 rows, every row has a source URL)

| release | time ET | rows | source | coverage 2021-10..2026-10 |
|---|---|---|---|---|
| CPI, PPI, Employment Situation, JOLTS | 08:30 (JOLTS 10:00) | 60 each | BLS yearly schedule pages bls.gov/schedule/YYYY/home.htm | Full. 2025 shows the shutdown dates (CPI Oct 24, Dec 18; PPI Nov 25; jobs Nov 20, Dec 16): there is no Oct/Nov-2025 jobs or CPI row, so those two months are only as complete as BLS's own page. |
| FOMC decision + minutes | 14:00 | 41 + 41 | federalreserve.gov/monetarypolicy/fomccalendars.htm (decision = last meeting day) | Full. The Aug 22 2025 notation vote is excluded. |
| GDP (adv/2nd/3rd) | 08:30 | 47 | BEA release pages for the Q4-2021, Q4-2022, Q4-2023 advance releases (each carries that year's schedule) and bea.gov/news/schedule/full-2025 | 2022-2025 only. NOT covered: Oct-Dec 2021, Jan-Oct 2026 (BEA's archive was not reachable; current page shows only Nov 25 and Dec 23 2026). |
| ISM Manufacturing/Services (10:00) | | 0 | ismworld.org calendar needs a login | NOT covered. No sourced dates. |
| Retail sales (08:30) | | 0 | census.gov schedule page only shows 2026-27 | NOT covered. |

BLS blocks `curl` (403), so the BLS tables were read with WebFetch and not parsed from raw HTML; I checked that no date falls on a weekend and that 2023 CPI matches the pattern, nothing more. Other 10:00 releases (new home sales, consumer confidence) and Beige Book, FOMC speeches are not in the list.

Release times inside each strategy's window: NOISE (entries on the hour 10:00-15:00, exits on hourly checks): **10:00** (JOLTS; ISM and others unsourced) and **14:00** (FOMC decision and minutes). CANDACE (signals 09:35-10:00): the **10:00** release. Late-day (enters 15:00-15:59): **none**; the 14:00 FOMC is an hour before entry. **08:30** releases (CPI, PPI, NFP, GDP) are before the open for all three, so they only act through the opening gap, not through the news rules.

## 2. Part (b): cost of the app's actual news rules

Rules from code/config: entries blocked from 15 min before to 1 min after a high-impact USD event (`no_entry_before_news_min: 15`, `news_breach_min_after: 1`); all open positions flattened 2 min before (`news_flatten_before_min: 2`). This applies to EVAL, FUNDED and LIVE alike. `lucid_pro_50k.yaml` sets `news_allowed_by_firm: true` for eval and funded, so for those stages the firm itself requires nothing and every cost below is self-imposed. LIVE is the hard-breach stage (flat 1 min before to 1 min after). A hard-breach rule on its own (blocked [-1,+1], flat at -1) is the second table. Per stage: **EVAL = FUNDED = APP table; LIVE = APP table (its extra hard-breach window sits inside it); firm-only cost = HARD table (LIVE only), 0 for EVAL/FUNDED.** Blocked trades are dropped, not re-entered (NOISE has hourly checks, so a later re-entry is possible and would reduce the loss slightly).

Sourced events only (no ISM, no retail sales; JOLTS 10:00 and FOMC 14:00 are what hits the windows).

**APP rules (all stages)**

| strategy | window | base n / net | blocked | cut short | new net | change |
|---|---|---|---|---|---|---|
| NOISE | pick | 298 / $8468 | 1 | 2 | $7952 | -516 (-6.1%) |
| NOISE | judge | 356 / $10826 | 6 | 6 | $9511 | -1314 (-12.1%) |
| CANDACE | pick | 160 / $1030 | 6 | 0 | $1225 | +195 (+18.9%) |
| CANDACE | judge | 150 / $814 | 6 | 0 | $900 | +86 (+10.6%) |
| LATE | pick | 465 / $6710 | 0 | 0 | $6710 | +0 (+0.0%) |
| LATE | judge | 602 / $2578 | 0 | 0 | $2578 | +0 (+0.0%) |

**HARD-breach window only (LIVE firm rule)**

| strategy | window | base n / net | blocked | cut short | new net | change |
|---|---|---|---|---|---|---|
| NOISE | pick | 298 / $8468 | 1 | 2 | $7966 | -501 (-5.9%) |
| NOISE | judge | 356 / $10826 | 6 | 6 | $9496 | -1330 (-12.3%) |
| CANDACE | pick | 160 / $1030 | 1 | 3 | $1116 | +86 (+8.3%) |
| CANDACE | judge | 150 / $814 | 1 | 4 | $949 | +136 (+16.7%) |
| LATE | pick | 465 / $6710 | 0 | 0 | $6710 | +0 (+0.0%) |
| LATE | judge | 602 / $2578 | 0 | 0 | $2578 | +0 (+0.0%) |

**Sensitivity: APP rules plus ISM approximated as 1st and 3rd trading day at 10:00 (UNSOURCED, same approximation the QA used)**

| strategy | window | base n / net | blocked | cut short | new net | change |
|---|---|---|---|---|---|---|
| NOISE | pick | 298 / $8468 | 11 | 2 | $7909 | -558 (-6.6%) |
| NOISE | judge | 356 / $10826 | 21 | 6 | $9044 | -1782 (-16.5%) |
| CANDACE | pick | 160 / $1030 | 17 | 1 | $835 | -195 (-18.9%) |
| CANDACE | judge | 150 / $814 | 19 | 0 | $929 | +116 (+14.2%) |
| LATE | pick | 465 / $6710 | 0 | 0 | $6710 | +0 (+0.0%) |
| LATE | judge | 602 / $2578 | 0 | 0 | $2578 | +0 (+0.0%) |

Reading: the late-day leg is untouched in every case. NOISE pays 6% (pick) to 12% (judge) of profit with sourced dates, 7% to 17% if ISM is added; the loss is about 70-80% from blocked 10:00 and 14:00 entries and the rest from the 13:58 flatten on FOMC days (cut trades: judge original +$703, after cut +$440). CANDACE does not lose profit with the sourced dates (blocked trades were net losers: +19% pick, +11% judge). The QA's -17% depends on the approximated ISM days and the pick window only (-19% pick, +14% judge here); with real ISM dates the sign is not established. So "the blackout cuts CANDACE ~17%" is **not confirmed**; the effect is within noise on 6 to 19 trades. Verdict on the news rules as a cost: NOISE cost real but modest; keep them (they protect against the 14:00 FOMC gap), INCONCLUSIVE for CANDACE.

## 3. Part (a): event days vs non-event days (`part_a_event_days.csv`)

Avg $ per trade, event-day class vs non-event days (all windows; p = permutation test of the mean difference, 5,000 shuffles; about 90 comparisons are in the file, so a few p<0.05 are expected by chance).

| strategy | any-event days | no-event days | note |
|---|---|---|---|
| NOISE all | n=194, PF 1.66, $35/trade | n=460, PF 1.46, $27 | p=0.65. FOMC-decision day $36/trade (n=26), CPI $36, NFP $60, minutes day -$27 (n=22). Nothing separates from normal. |
| CANDACE all | n=77, PF 0.93, -$1.9 | n=233, PF 1.32, +$8.5 | p=0.31. The whole CANDACE edge sits on non-event days, but it is not significant; the sign flips between pick (+$4.6 vs +$7.1) and judge (-$10 vs +$10), JOLTS day -$24 (n=15, p=0.11). |
| late-day all | n=287, PF 1.49, $19 | n=780, PF 1.13, $4.8 | p=0.06. Judge: event days PF 1.60, non-event 0.93 (p=0.009), but pick is the opposite (1.34 vs 1.48). Not stable across windows. |

## 4. Part (c): skip or halve NOISE on event days (6 variants, prereg, random-control)

Event-day pool: FOMC decision (V1, V6), CPI (V2), NFP (V3), union FOMC/CPI/NFP (V4 skip, V5 halve). Pass needs pick uplift >= 0, judge uplift >= 0, judge PF up, and judge uplift above the 95th percentile of skipping the same number of random days.

| variant | pick uplift | judge uplift | judge PF base to new | judge random p95 | pass |
|---|---|---|---|---|---|
| V1 skip FOMC | -$430 | -$496 | 1.49 to 1.49 | $825 | no |
| V2 skip CPI | +$676 | -$1,501 | 1.49 to 1.43 | $835 | no |
| V3 skip NFP | +$152 | -$2,596 | 1.49 to 1.41 | $974 | no |
| V4 skip union | +$398 | -$4,548 | 1.49 to 1.33 | $797 | no |
| V5 halve union | +$199 | -$2,274 | 1.49 to 1.42 | $418 | no |
| V6 halve FOMC | -$215 | -$248 | 1.49 to 1.49 | $410 | no |

**REJECT all six.** The days with the worst NOISE results flip between windows (CPI was the worst class in pick, best in judge). Do not skip or halve on event days. With 6 variants about 0.3 false passes are expected at 5%; none occurred.

## 5. Part 2: last30days and idea search

The engine ran for all 4 topics (raw files `last30days_run1..4.txt`, saved under `/root/Documents/Last30Days/*-v5.md`). YouTube is bot-blocked (not bypassed); Reddit/web returned nothing; GitHub and HN gave 0-2 relevant items per topic (mostly unrelated: a BYD story, repo issues such as DaltonDom/moon-ai issue 100 "Prop-firm rule simulator: Lucid 50k and Tradeify" and Leblepito/efloud-bot PR 258 mentioning TradingAgents). **The engine gave no usable trading ideas**; the ideas below come from WebSearch.

Sources: Zarattini/Aziz SSRN 4416622 (5-min ORB, QQQ/TQQQ) and the 2024 SFI paper 24-98 (stocks in play); an MQL5 blog replication claiming "gross reproduced, net zero" on NQ and other indices (secondary, not verified); Valentini rules appear only in vendor pages (PickMyTrade blog, TradingView "AMT Institutional Model", tradezella): auction market theory, day type balance/imbalance, CVD/delta, NY open NQ. TTrades daily-bias appears as third-party TradingView indicators (daily close vs prior-day high/low). Axia Futures, SMB Capital, Jigsaw: searches returned nothing usable.

Ideas (max 5), codable ones tested on 1-min bars, 1 micro, $2 RT plus 0.25 pt entry slippage:

| # | idea | codable? | result | verdict |
|---|---|---|---|---|
| I1 | Zarattini 5-min opening-range breakout, EOD exit | yes (3 variants) | prereg pick choice = 15-min OR with candle filter: pick PF 1.36 net $11,220, judge **PF 1.09 net $4,070**, below the random-direction p95 (PF 1.17, net $7,326). The 5-min filtered variant: judge PF 1.19, net $7,727 vs control p95 PF 1.17, net $7,434 (just at the line, pick PF 1.16 only, not the pick choice). | **REJECT** (consistent with the MQL5 "net zero" claim) |
| I2 | TTrades-style daily bias (close vs prior-prior high/low) as a NOISE filter | yes (3 variants) | dropping counter-bias trades: pick net $5,110 vs $8,468 (worse), judge net $10,873 vs $10,826 and PF 1.69 vs 1.49, random control p=0.06. Aligned-only: far lower profit. | **REJECT** (pick fails; judge PF gain not enough, profit flat) |
| I3 | Valentini proxy: imbalance day (first-30-min efficiency >= threshold), first VWAP pullback 10:00-11:30 in trend direction, stop 40 / target 60 | partly (no CVD, delta or footprint) | prereg pick choice thr 0.35: pick n=286 **PF 1.05 net $695**; judge n=372 **PF 1.21 net $3,487**, above random p95 (PF 1.08, net $1,373). Thr 0.5: pick PF 1.03, judge PF 1.28 net $3,215. | **INCONCLUSIVE** (passes the judge control but pick is breakeven; edge only after 2024; 2 variants, one regime) |
| I4 | Valentini CVD/delta aggression, Jigsaw DOM | no (needs tick/order-flow data) | not tested | n/a |
| I5 | ORB/gap on Lucid consistency-rule sizing (prop-firm idea) | no new rule found in the search results | not tested | n/a |

Nothing is adopted. No ADOPT CANDIDATE found. I3 would be the one to re-test with more out-of-sample days or tick data.

## Caveats

- WebFetch summaries were used for BLS and BEA tables; I did not see the raw pages. Spot check only (weekdays, 2023 CPI).
- Not covered: ISM, retail sales, GDP 2021Q4 and 2026, other 10:00 and 14:00 releases the app's calendar (ForexFactory high-impact USD) would include. The app's real blackout is therefore probably bigger than modelled for NOISE and CANDACE.
- Streams were not re-generated under the blackout (blocked trades are dropped, not replaced).
