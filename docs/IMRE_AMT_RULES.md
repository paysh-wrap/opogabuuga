# ORDER FLOW · AUCTION (IMRE) — rule sheet (from ONE transcript only)

Source: Chart Fanatics episode with Imre Gans (a professional trader; auction market theory + order flow), pasted by the user
on 2026-11-16 ("add as an order flow option"). Times are the transcript's `h:mm:ss`. Nothing here is copied from any
existing Paytience strategy; only app plumbing is shared. In Paytience it is built as one more **Order Flow option**, like
the existing Order Flow types: its own card, key `order_flow_auction`, setting
`strategy.order_flow_cfg.auction.enabled`, turning Order Flow on with it (`also: strategy.order_flow`), default OFF.

He trades ES (and options); the logic is the same on the NASDAQ, so Paytience applies it to MNQ micros.

Rules marked **[GAP]** are not given as a number in the transcript. They are config settings with a documented default,
shown on the card as "not from the video", and must never be tuned to make a backtest look better.

## A. Regime first: balance or imbalance (7:36–28:00, 36:20–38:13)
| # | Rule | Time |
|---|------|------|
| A1 | The market only does one thing: negotiate fair value. Two regimes: BALANCE (a range; buyers and sellers agree on value) and IMBALANCE (trending; value migrating). Roughly 68–70% of the time the market is balanced; about 30% (about 6 days a month) is imbalanced, and trend days cluster | 12:51–13:12, 25:42–26:50, 57:11–57:52 |
| A2 | ONE TIME FRAMING UP (OTFU), on higher time frames (weekly, daily): each candle makes a HIGHER HIGH, a HIGHER LOW and a HIGHER CLOSE. One time framing DOWN (OTFD): lower high, lower low, lower close. His definition is stricter than the textbook one | 20:20–24:45, 22:00–23:29 |
| A3 | Balance = neither of the two (candles sweep both sides, a failed break, messy overlap) | 27:59–28:20 |
| A4 | Trade MOMENTUM / BREAKOUTS only when the market is one time framing (up or down). In balance he does not trade outright momentum; he fades the edges of value | 24:08–25:30 |
| A5 | A trend is not just price making higher highs; it needs VALUE to build higher (new balance ranges, each higher than the last). A news spike without new value reverses | 14:24–17:03 |
| A6 | The day-time-frame (DTF) participants (day traders, intraday algos, CTAs) vs the OTHER-time-frame (OTF) participants (funds, pensions). OTF participants have an interest in keeping the market in balance while they accumulate; align with them | 17:14–19:45 |
| A7 | He reads the regime BEFORE the session; a day trader often has "won or lost the session before the first trade" | 21:01–21:41, 1:43:45–1:43:56 |

## B. Value (38:13–39:30, 1:36:00–1:43:30)
| # | Rule | Time |
|---|------|------|
| B1 | Value area (VA) = where about 70% of the trade took place; VALUE AREA HIGH (VAH) and VALUE AREA LOW (VAL); POINT OF CONTROL (POC) = the most volume, near the middle of a balanced range (the POC is an AREA, not an exact tick) | 8:38–9:32, 38:32–38:45, 1:48:53–1:49:24 |
| B2 | Prices outside the VA are "unfair"; pokes outside the VA are often rejected violently (a feature, not a bug) | 38:45–39:10 |
| B3 | ACCEPTANCE = balance (time and trade) BEYOND a value-area extreme; confirmation of control = a breakout of that structure (e.g. a daily close below the prior low); a failure to hold = trapped traders and a rotation back | 1:40:04–1:41:32 |
| B4 | VOLUME BY TIME: in a balance the volume gradually falls; it rises at the boundaries; a day of heavy volume that does not continue = trapped traders on that side | 1:36:00–1:39:34 |
| B5 | Profiles to build: the DEVELOPING WEEKLY profile (VAL, VAH, POC area, high and low volume nodes), the prior CASH-SESSION profile (value area), a COMPOSITE profile when several sessions overlap in value, and the FULL-session (Globex + RTH) profile when there was a big overnight move | 1:33:41–1:34:24, 1:44:55–1:56:32 |
| B6 | Mark ZONES not exact levels; stack levels that agree across profiles (congruence); the zone just above and below the prior VA and the weekly VAL are the "control zones" / "line in the sand" | 1:49:00–1:50:11, 1:54:50–1:56:46 |
| B7 | Where the day OPENS relative to the prior session's value matters: opening INSIDE the prior value = mixed day; get excited only on a break of the prior VAL or acceptance above | 1:50:30–1:53:05, 1:57:53–1:58:27 |

## C. Order-flow reading (what he looks at on the footprint)
| # | Rule | Time |
|---|------|------|
| C1 | AGGRESSIVE sellers / buyers = large market-order volume at a price (big sell / buy "bubbles", delta outliers) | 51:04–51:20, 52:00–52:40 |
| C2 | ABSORPTION = heavy aggressive volume that does not move price; the side that was absorbed is TRAPPED | 52:39–52:46, 2:04:14–2:05:23 |
| C3 | The side that stepped in to absorb gives a logical place for the STOP (use the aggressive counterparties as the shield) | 52:06–52:58, 1:00:56–1:01:08 |
| C4 | **[GAP]** Paytience data: only 1-minute bars with volume (the Pine script's delta is real only on a TradingView plan that has it; otherwise ESTIMATED). The DOM / heatmap he also reads (pulled resting orders, big limit sellers) is NOT available and is not built | 2:04:14, 2:10:31–2:10:56 |
| C5 | **[GAP]** "big bubble" as a number: default a 1-minute bar whose |delta| is at least 2 x the average |delta| of the last 20 bars and that closes in the delta's direction | — |

## D. Setup 1: FAILED AUCTION (49:46–56:50) — in a BALANCE, fade the edges of value
| # | Rule | Time |
|---|------|------|
| D1 | Location is what makes it work: only at the edge of the value area, in a balanced regime | 50:05–50:23 |
| D2 | FLAVOUR 1, V-SHAPE REVERSAL (long): price pushes BELOW the VAL with aggressive SELLERS; then it snaps back and RECLAIMS the VAL with aggressive BUYERS (big buy bubbles); the sellers are trapped | 50:48–52:06 |
| D3 | Entry: BUY AT MARKET (cross the spread) as the VAL is reclaimed, not a limit order | 52:14–52:33 |
| D4 | Stop: below the aggressive buyers (the low of the reversal) | 52:06–52:14, 52:46–52:58 |
| D5 | Target: the POC first (scale out, trim, stop to entry, trail), then the opposite value extreme (VAH) | 52:58–53:23 |
| D6 | FLAVOUR 2, SLOWER (short): price tries to break out ABOVE the VAH, builds some value up there, FAILS to continue and breaks back INSIDE the VA (no aggressive bubbles); then wait for value to build LOWER (a MICRO RANGE below the VAH) | 53:29–54:08, 55:07–55:27 |
| D7 | Flavour 2 entry, plan A: sell the TOP of the micro range when aggressive selling stops a move higher; plan B: sell when aggressive selling breaks BELOW the micro range. Stop above the large sellers; target a rotation back toward the VAL (POC on the way) | 54:08–54:57 |
| D8 | Mirror for the other side (a failed auction below the VAL → long; above the VAH → short) | 51:04–51:34, 53:29–53:36 |

## E. Setup 2: BREAKOUT, filtered (56:50–1:05:16) — in an IMBALANCE
| # | Rule | Time |
|---|------|------|
| E1 | NEVER buy the initial breakout: that is price, not value | 59:21–59:35 |
| E2 | Wait for the MICRO RANGE ("the range after the range"): value forming just beyond the old range = acceptance. This is his favourite breakout filter | 59:35–1:00:07 |
| E3 | PLAN A (best price): aggressive sellers try to break DOWN out of the micro range, buyers ABSORB, big buy bubbles appear, and price reclaims the LOWER boundary of the micro range → buy; stop below the aggressive buyers | 1:00:18–1:01:13 |
| E4 | PLAN B: aggressive BUYING breaks out of the micro range's value area HIGH → he trusts the breakout (growing evidence of imbalance); the target is further expansion | 1:01:13–1:01:35 |
| E5 | He SPLITS his risk between plan A and plan B (it does not increase total risk) | 1:03:20–1:03:41 |
| E6 | After a run, value builds again and the same setup repeats; in an imbalance PREVIOUS VALUE IS A TRAMPOLINE, not a magnet (price should not spend time back there). A test of the previous VAH by trapped sellers (red bubbles) followed by buy bubbles that reclaim it = long | 1:01:35–1:01:49, 1:04:01–1:05:08 |
| E7 | LOW VOLUME NODES (air pockets) in the profile: if price pushes into one and is defended, other-time-frame buyers are present; if it slices through and reverses violently, they are NOT present | 1:01:57–1:03:08 |
| E8 | Do not front-run a breakout, unless it is from value (e.g. after a sweep absorbed back into the range) | 2:12:56–2:13:20 |

## F. Management, risk, timing
| # | Rule | Time |
|---|------|------|
| F1 | Scale out at the first target (POC / prior high), move the stop to ENTRY, trail the rest | 53:06–53:23, 2:17:09, 2:22:35 |
| F2 | Invalidation: the move fails back below the range / the buyers stop defending (live examples: stop at entry, stopped out at entry) | 2:17:32–2:17:54, 2:18:46–2:19:01 |
| F3 | Small, defined risk (he shows 2 minis / 1 mini; "the P&L isn't worth anything"); the live trigger example is a pop above a range with a big buy bubble and a risk of about 3 points | 2:06:34–2:06:50, 2:21:29–2:21:49 |
| F4 | He does not start trading before the 09:30 ET cash open | 1:30:03–1:30:10 |
| F5 | NEWS: he does not trade the instant after the release, and does not hold an intraday position into it; the miss versus expectations sets bias and conviction for later in the session | 1:30:03–1:30:36 |
| F6 | Quick scalps: out at the upper part of the range / prior high; a trade idea can be re-entered after being stopped | 2:07:00–2:07:22, 2:14:37–2:14:52 |
| F7 | **[GAP]** reward : risk minimum and exact stop buffer (not given; defaults: a 2-tick buffer beyond the absorbing side, minimum 1 : 1.5 to the first target, **not from the video**) | — |
| F8 | **[GAP]** window (default 09:30–11:30 ET) and a maximum of trades per day (default 3, **not from the video**) | — |

## Left out on purpose
Options structures (he prefers options: "bend the curve"), the fundamentals dashboard and the AI terminal (only the news rule
F5 is kept), the exit-liquidity story (qualitative), DOM / heatmap and pulled-order reading, live-stream chatter.

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge (D139), feed
checks, live gates, EOD drawdown on Pro 25K–150K. Sizing uses the Lucid-fit helper; splitting risk across plans A and B only
divides the same budget. Order-flow data is estimated unless the TradingView plan provides real footprint delta.

## Implementation notes (D150, 2026-11-16)
An Order Flow option: card key `order_flow_auction`, setting `strategy.order_flow_cfg.auction.enabled` (default OFF,
`also: strategy.order_flow`), its own plan mode `ORDER_FLOW_AUCTION` (Lucid-fit sized, one free account per trade).
Engine `backend/app/engine/auction_imre.py` (pure) — `replay_day(history: list[MBar], today: list[MBar], cfg, tick) ->
AuctionDay` (history = earlier sessions' 1-minute bars). Hook `strategy_service.run_order_flow_auction`; key
`MNQ-OFA-<day>-<HHMM>`. The logic uses NOTHING from the other Order Flow types.
**Built:** A1–A4 (daily one-time-framing from RTH 1-minute bars; weekly OTF reported as context), B1 (tick-bin profile,
70% VA, POC, LVNs below 30% of the mean bin — gap), B5 (prior cash-session profile only), B7 (open vs prior value,
recorded), C1/C2/C5 big bubble (|delta| ≥ 2 × 20-bar average, closing its way), D1–D5 + D8 V-shape failed auction
(BALANCE only; market entry on the reclaim; stop 2 ticks past the reversal extreme; POC then the opposite VA extreme),
D6/D7 slower flavour (close beyond, back inside, 5-bar ≤ 15 pt micro range — gaps; plan A at its outer edge / plan B out
of its inner side), E1–E5 breakout (IMBALANCE only, with the regime's side; never the first break; micro range beyond
value; plan A absorbed reclaim, plan B close beyond the micro VAH; target 2R — gap), E5 risk split 0.5 / 0.5 of the SAME
Lucid-fit budget (controller), F1 (2+ micros: leg A at the first target, the rest's stop to ENTRY on that fill, leg B to
the second target — the existing two-leg bracket; 1 micro → single bracket at the first target), F4 (no trade before
09:30), F5 (= the Lucid news blackout gate), F7 (2-tick buffer, ≥ 1 : 1.5 — gaps), F8 (09:30–11:30, 3 trades — gaps).
**Delta:** ESTIMATED from each 1-minute bar (volume × (close − open) / range). Stored bars carry no footprint delta, so
real delta from the Pine script is NOT used by this option. **Not built:** DOM / heatmap (C4, no data), A5/A6 value
migration and OTF participants (qualitative), B3/B4 acceptance-by-time and volume-by-time reads, B5 developing weekly /
composite / Globex profiles, B6 congruent zones, E6 trampoline re-test, E7 LVN defence, E8 front-running, F2/F6 trail.

| Plan | EVAL $/trade | micros @8 / 16 pt | FUNDED $/trade | micros @8 / 16 pt |
|------|------|------|------|------|
| Pro 25K | 158.33 | 8 / 4 | 180.00 | 10 / 5 |
| Pro 50K | 360.00 | 20 / 10 | 360.00 | 20 / 10 |
| Pro 100K | 540.00 | 30 / 15 | 540.00 | 30 / 15 |
| Pro 150K | 810.00 | 45 / 23 | 810.00 | 45 / 23 |
(plans A / B each get half: 25K EVAL $79.16 → 4 micros at 8 pt.)
