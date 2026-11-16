# OKALA 8020 — rule sheet (from ONE transcript only)

Source: Chart Fanatics episode with "Okala" (a prop-firm trader who trades from his phone), pasted by the user on
2026-11-16. Times are the transcript's `h:mm:ss`. Nothing here is copied from any existing Paytience strategy; only app
plumbing is shared. His own claims: 70%+ win rate ("mid to low 70s", 34:59–35:06), over $5M in prop payouts.

He trades the NASDAQ only ("these levels have worked only on the NASDAQ", 3:14–3:20), as a REVERSION trader (4:02, 17:46).

Rules marked **[GAP]** are not given as a number in the transcript. They are config settings with a documented default,
shown on the card as "not from the video", and must never be tuned to make a backtest look better.

## A. Levels: "80" and "20"
| # | Rule | Time |
|---|------|------|
| A1 | The levels are where the NASDAQ price ends in **80** or **20** in every hundred (e.g. 25,680 and 25,620). The big levels are 80 and 20; there are others in between (not used) | 3:28–3:46, 5:04–5:16 |
| A2 | 80 is not only long and 20 is not only short; either level can be traded either way depending on the reaction | 7:53–8:05 |
| A3 | Look for an instant reaction when price taps a level: if the level is respected, take the entry in the direction of the reaction | 4:49–5:16 |
| A4 | Price does not have to fully tap the level (a strong candle that stops at 19.75 still counts); a limit order can sit a little past it (e.g. 23 for the 20 level) on a strong move | 13:53–14:13, 15:22–15:40 |
| A5 | If the entry is missed, do NOT chase and do not leave the limit order there; wait for the next entry | 14:19–15:07 |
| A6 | Limit orders are placed at the level, each with its 10-point stop already in | 15:07–15:22 |

## B. Charts and conditions
| # | Rule | Time |
|---|------|------|
| B1 | Two time frames: a **10-minute** chart for the overall structure and a **200-second** chart for entries (200 s = one third of a 10-minute candle) | 6:02–6:36, 7:41–7:53 |
| B2 | He prefers a CHOPPY market ("I make all my money doing that"); trending up is read as structure too | 4:09–4:26, 17:46–18:00 |
| B3 | Trade the New York open (the volatile window); avoid the lunch hour; avoid slow choppy and slow trending conditions | 10:09–10:41, 12:39–12:51 |
| B4 | He sometimes trades before the open but usually not; before the open: 1 contract, at most 2 | 54:47–54:58, 1:01:47–1:02:13 |

## C. Stop, targets, scaling (every setup)
| # | Rule | Time |
|---|------|------|
| C1 | STOP: always 10 points (if wrong by 10, probably wrong by 50 or 100) | 8:24–8:35, 15:16 |
| C2 | TP1 = 15 points (covers the risk); he trades multiple contracts. 12 – 15 is possible depending on how strong the move is | 8:35–8:54, 50:24–50:40 |
| C3 | After TP1 move the stop to break even (a point beyond entry to cover commission) | 9:20–9:54, 1:06:52–1:07:09 |
| C4 | The rest is a runner: no fixed TP2; "squeeze" the capitulation move (40–100 points) but cover the risk first. A strong magnet can justify more than 15 on the first TP | 8:55–9:35, 38:13–38:30 |
| C5 | Scaling by size: 3 contracts → 2 off at 15, 1 trailing runner; 4 contracts → 2 off at 15, then 1 at about 30, the last at about 60; 2 contracts → 1 off at 12–15, the other to break even | 49:44–50:40 |
| C6 | Prop-firm play = base hits that stack with consistency; watch each firm's consistency rule (an outsized day can break it); with an EOD drawdown firm the runners are fine | 50:47–52:21 |
| C7 | Sizing: the point stop stays static; when hot, add contracts, not points | 34:42–34:55 |
| C8 | Both contracts of a trade can carry the same stop | 1:03:44–1:04:02 |

## D. The setups (market structure)
Best entries mix several confluences: a level + a structure pattern + a magnet, with the 10-point stop and a 3–5x reward
(30:46–32:56, 1:05:14–1:05:38). Entries without a level can work ("structure is structure") but are subpar (32:22–32:50).

| # | Setup | Rule | Time |
|---|-------|------|------|
| D1 | **FORK** (long) | After a STRONG move down off the open (100–150 points), a candle with a LONG WICK and a SHORT BODY (sellers step off the gas) = the "initiation candle". The NEXT candle tests that candle's low but does NOT break it, then makes a higher high. ENTRY after the low held (low 23, entry 27); stop ~10 points (slightly under the low, e.g. 17); TP1 15. Best when the low sits at a 20/80 level | 18:00–21:13, 30:46–31:20 |
| D2 | **Reverse fork** (short) | The mirror image after a strong move UP | 38:43–38:59, 1:06:36–1:06:42 |
| D3 | **H pattern** (short continuation) | A strong move lower, a bounce up into an 80 level (a stronger up move with a long lower wick and small body, "like the fork on the other side"), then a roll over that forms a lowercase "h". It is a structure pattern, not itself the entry; the entry is the cross-section (D4). A continuation of a short-term downtrend. Mirror for longs | 21:21–25:50, 45:00–46:17 |
| D4 | **CROSS-SECTION** entry | Where two strong candles meet (the "cross" between the two breakdown / breakout candles), price comes back, taps the cross and rejects → entry with a 10-point stop, TP1 15. Works for a trend or a reversion. Strongest when the cross coincides with an 80/20 level | 23:38–25:50, 46:37–47:53, 48:19–49:28, 57:07–57:32 |
| D5 | **REPAIR / magnet** | A candle that STARTS with a body and no wick on its opening side (e.g. a strong down candle with no top wick). No orders above could fill, so price is pulled back to it ("a magnet"). Valid as long as price has not touched it. Use as a TARGET and as extra confluence for entries toward it; shorts at a repair above (limit just above the previous high, risk 10 to make ~28) | 35:16–39:56, 41:18–44:09, 53:00–54:04 |
| D6 | Adding to winners | If the trade idea is playing out, add in the same direction ("step on the gas"). **User-approved exception (2026-11-16, D145):** OKALA 8020 may hold more than one position on an account, same direction only, with the safety limits listed under "Add-to-winners limits" below | 1:07:45–1:08:08 |
| D7 | Confluence count | More confluences (level, cross, repair, H, fork) = a better trade; a doubled-up second entry on the same idea can be "greedy" | 1:05:14–1:05:38, 1:08:50–1:09:16 |

## E. Limits and discipline
| # | Rule | Time |
|---|------|------|
| E1 | No fixed daily trade cap ("if you're hot, step on the gas") but be careful when the market is not giving the criteria — that is when overtrading and forcing trades start | 33:06–34:16 |
| E2 | Overtrading is the biggest culprit; do not take sub-par entries just because the model gives many | 31:44–32:50 |
| E3 | If stopped out, do not overanalyze; take the next valid setup | 59:35–59:43 |

## Gaps and honest limits
- **[GAP] 200-second bars.** The app and its stored history have 1-minute bars; 200 s cannot be built from them. Default:
  3-minute bars (the nearest candle size built from 1-minute bars), clearly flagged; the 10-minute chart is built from the
  1-minute bars exactly. (TradingView Plus has no custom-second intervals per the user's screen recording; a second-based
  feed would need another plan.)
- **[GAP] "strong move" size** (default 100 points off the open, the low end of "100–150"), **"long wick / short body"** (default
  wick ≥ 2x body), **"chop vs trend"** on the 10-minute chart, **"cross-section" geometry** (default: the junction price
  where candle 1 closes and candle 2 opens, within a tolerance band), **"no wick"** (default: wick ≤ a few ticks), **trading
  windows** (default 09:30–11:30 ET; lunch 11:30–13:30 excluded; no overnight), **max losses per day** (the transcript has
  none; Lucid sizing needs one: default 3).
- **Add-to-winners (D6)** is built as a narrow, user-approved exception (D145), see below.
- **Phone discretion** ("how strong is the move", "my own judgment call") is not mechanical and is left out.

## Add-to-winners limits (user-approved exception, D145)
Only this strategy may add to an open position. Everything else keeps "max 1 open position per account".
- SAME direction only. An opposite-side order is never allowed (hedge lock and D139 stay as they are).
- Only while the open position's stop is at break-even or better (TP1 taken) — the video adds "when the idea is playing out"
  (1:07:45–1:08:08) and keeps the same stop on both contracts when entering together (1:03:44–1:04:02). **[GAP]** exact trigger: default = TP1 hit and the stop at break-even.
- The add carries its own 10-point stop, and the TOTAL worst-case loss of the account's open JJ-style position stays inside the same per-trade
  risk cap as a normal trade (D143-style: DLL left, MLL room, consistency day stop, plan risk cap) — adds are sized from the remaining cap.
- At most `max_adds` adds per position (**[GAP]**, default 2); never more than the firm / internal max micros in total.
- Before the open: 1 contract, at most 2 (1:01:47–1:02:13).
- Every Lucid check (news, DLL, MLL kill switch, consistency, flat times) still runs on every add and can refuse it.

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge (D139), feed
checks, live gates, EOD drawdown on Pro 25K–150K. A signal that hits one of these is skipped with its reason code.

## Implementation notes (D145, 2026-11-16)
Engine `backend/app/engine/okala_8020.py` (pure) — `replay_day(today: list[MBar], cfg, tick) -> OkalaDay` (`.signals`:
entries and adds with outcome STOP / BE / RUNNER / TIME). Hook `strategy_service.run_okala_8020`; key
`MNQ-OKALA-<day>-<HHMM>`; plan mode `OKALA_8020`; `strategy.okala_8020` (default OFF) + `strategy.okala_8020_cfg`.
**Built:** A1–A4 (A4 tap tolerance 0.25 / through 3 pt), A2, B1 (10-min exact; entries on **3-minute** bars — FLAG:
200 s impossible from 1-minute data), B3 (09:30–11:30, lunch out, no pre-open: B4 not needed), C1 10 pt, C2 TP1 15,
C3 break even + 1 pt, C4 runner to the nearest untouched repair magnet or 30 pt (gap), D1 fork, D2 reverse fork, D3 H
pattern (confluence of a cross), D4 cross-section, D5 repair magnets (target + confluence), D6 adds (D145), D7
confluences stored on the signal (not used for size), E1/E3 no trade cap, max_losses_per_day 3 (gap).
**C5 scaling:** 1 micro → single bracket at TP1; 2+ micros → the existing Drawdown-Guard two-leg bracket (leg A =
ceil(n/2) at TP1 15 pt, leg B to the runner target; leg B stop to entry + 1 pt on the leg-A fill). This matches the 2- and
3-contract rows; the 4-contract "1 at 30, last at 60" ladder is NOT built (leg B goes to one runner target).
**Not built:** A5/A6 limit orders resting at the level (entries are market at the 3-minute close), phone discretion,
B2 chop-vs-trend regime, the "subpar without a level" judgment (confluences recorded, not filtered).
**Add-to-winners (D145):** `risk/add_to_winners.add_allowed` (pure, 100% covered) + controller: only plan mode
OKALA_8020; same direction (else `OKALA_ADD_OPPOSITE`), every open leg's stop at entry or better (else
`OKALA_ADD_NOT_AT_BE`), ≤ max_adds (else `OKALA_MAX_ADDS`), contracts from (per-trade cap − worst case still open)
(else `OKALA_ADD_CAP`); every pre-trade check (news, DLL, MLL kill switch, consistency, hedge lock, flat times) runs on
the add. Every other strategy still gets `POSITION_OPEN`.

| Plan | EVAL $/trade | micros @10 pt | FUNDED $/trade | micros @10 pt |
|------|------|------|------|------|
| Pro 25K | 158.33 | 7 | 180.00 | 8 |
| Pro 50K | 360.00 | 16 | 360.00 | 16 |
| Pro 100K | 540.00 | 24 | 540.00 | 24 |
| Pro 150K | 810.00 | 36 | 810.00 | 36 |
