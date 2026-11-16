# CANDACE ICT SCALP — rule sheet (from ONE transcript only)

Source: Chart Fanatics episode with Candace Lau (an ICT scalper who trades London and the New York open, Apex / personal
accounts), pasted by the user on 2026-11-16. Times are the transcript's `h:mm:ss`. Nothing here is copied from any existing
Paytience strategy; only app plumbing is shared. Her own claims (big single trades, "$4,000 in 9 minutes") are not ours.

She trades NQ (MNQ when the market is wild) with a 1-minute chart and watches 15- and 30-second charts for the speed of a
move (26:45–27:12). The seconds charts are NOT available in Paytience (the app and its history have 1-minute bars), so the
built version reads the 1-minute chart only; she says beginners should wait for the 1-minute candle body to close
(1:00:12–1:00:31, 28:07–28:13).

Rules marked **[GAP]** are not given as a number in the transcript. They are config settings with a documented default,
shown on the card as "not from the video", and must never be tuned to make a backtest look better.

## A. The plan: four things must be there (21:51–22:41)
| # | Rule | Time |
|---|------|------|
| A1 | HIGHER-TIME-FRAME analysis first: weekly and daily candles, and the 1-HOUR fair value gap (FVG); she ignores the 4-hour | 9:00–9:05, 27:53–28:32 |
| A2 | PREMIUM / DISCOUNT of the dealing range (**[GAP]** no number given; default: below 50% of the range = discount for longs, above = premium for shorts) | 21:57–22:12 |
| A3 | A LIQUIDITY POOL to target: equal highs / equal lows ("relative equal"), a swing high / low, the previous day's or session high / low, a daily or 1-hour FVG. "Without a liquidity pool there is no setup" (sometimes only a small minor one) | 22:07–22:30, 3:14–3:36 |
| A4 | A LIQUIDITY SWEEP = the manipulation: price runs the high (or low) of the pool, then reverses. She trades the reversal | 3:49–4:48, 22:30–22:41 |
| A5 | Frame: Asia accumulation, London manipulation, New York distribution (AMD). **[GAP]** the Asia range and midnight price need overnight bars; the built version uses what the bar history has (see section H) | 3:49–4:34 |
| A6 | If there is no clear Asia range or no clear pool, use the HIGHER-TIME-FRAME pools (daily FVG, previous daily high, last week's high) and the MIDNIGHT OPENING PRICE (the 00:00 ET open, "a magnet") and the new-week opening gap as references | 9:19–12:52 |

## B. When to trade (kill zones)
| # | Rule | Time |
|---|------|------|
| B1 | LONDON kill zone 02:00–05:00 ET. Never trade before 02:00 even if the setup looks right (her hard rule: it turns into more and more forced trades); moves usually come around 02:30 and 03:00–03:30 | 4:54–7:29 |
| B2 | NEW YORK: the pre-market and the 09:30 open; the whole trade usually ends within about 15 minutes of the entry; she looks at the chart from 09:00 | 16:31–16:50, 1:08:25–1:08:31, 18:27 |
| B3 | At 09:30 she does not force a trade: if the manipulation did not happen she waits for one (or skips) | 1:18:31–1:19:01 |
| B4 | **[GAP]** exact New York window (default 09:00–10:00 ET) and London window (02:00–05:00 ET); a time-based max hold (default 15 minutes in New York, **not from the video** for London) | 16:31–16:50 |

## C. Entry model (22:49–30:31, repeated in every example)
| # | Rule | Time |
|---|------|------|
| C1 | After the sweep, the move away leaves a FVG (a gap between candle 1's wick and candle 3's wick). Assume the opposite-colour FVG will become an INVERTED FVG (IFVG) | 22:49–23:35 |
| C2 | A VALID IFVG: a candle BODY closes completely through the FVG on the other side. While price is still inside the FVG it is not valid yet | 23:35–24:27, 25:09–25:43 |
| C3 | Entry = the RETRACE back into the IFVG after the valid close (market order), or the "average entry" | 24:06–24:27, 26:23–26:38 |
| C4 | Aggressive entry (experienced only): inside the FVG before the body closes through. Beginners wait for the body close | 24:06–24:18, 1:00:12–1:00:31 |
| C5 | DISPLACEMENT + SPEED: the candle that closes through must be a large, fast candle ("a huge candlestick"); a close only one tick past the FVG is not valid enough. **[GAP]** size: default body ≥ 1.5 x the average body of the last 10 bars | 25:50–26:23, 1:11:08–1:11:18, 27:01–27:12 |
| C6 | Extra confluence: a wick that retraced into the FVG, a volume imbalance next to the FVG (count them as one FVG), an order block | 54:06–54:32, 1:11:26–1:11:48 |
| C7 | The 1-HOUR FVG is both a target and a confluence; an A+ trade sweeps a daily or 1-hour FVG as well as equal highs | 28:17–28:50, 1:19:10–1:19:39 |
| C8 | RTH GAP (4:00 pm ET close to 09:30 ET open): mark it every day with its 25%, 50%, 75% levels; a REFERENCE, not a target she expects to fill; also the new-day opening gap | 30:41–31:45, 1:19:39–1:20:10, 1:29:56–1:30:14 |
| C9 | SMT with ES (one index sweeps a high / low the other does not) is a confirmation she checks | 1:39:46–1:40:27, 2:02:56 |
| C10 | Count confluences: the more (HTF FVG, equal highs, RTH gap, NDOG, SMT, kill zone) the better the grade | 1:19:10–1:20:28, 1:42:14–1:43:05 |

## D. Stop and target
| # | Rule | Time |
|---|------|------|
| D1 | STOP: beyond the swing high / low, or beyond the order block when that is very close to the swing | 31:45–32:04, 1:43:26, 1:45:29–1:45:48 |
| D2 | Maximum stop in points (her own rule of thumb for NQ): London 20–25 points; New York 30–40 points (a year ago 15 in London). If a larger stop is needed, "that is not the entry point" and she skips it (or switches to MNQ in a wild market) | 32:04–33:53 |
| D3 | TARGET: a bracket order of at least 1 : 2, moved to the CLOSEST liquidity pool; if the pool is at 1 : 3 or 1 : 4, extend it there | 36:44–37:15 |
| D4 | She takes PARTIAL profit at the first internal liquidity (a one-minute FVG or minor high / low) and the final target at the next pool; for an entry that came late she always takes a partial | 28:44–28:50, 1:14:25–1:15:01, 1:43:48–1:44:52 |
| D5 | Trail the stop to a tighter level when minor liquidity (equal highs on the 15-second chart) is swept; it need not be break-even; move to break-even once about 25% of the gap move is done | 47:19–48:21, 2:01:45–2:02:22 |
| D6 | She is a scalper: she closes at the target and does not hold for the whole daily move ("not diamond hand"); she tested different templates (close at 5–10% of the move, trail, close after three bearish candles) in her backtest | 16:44–17:03, 37:49–38:10, 39:33–40:09 |

## E. Grades and size
| # | Rule | Time |
|---|------|------|
| E1 | A+ setup (many confluences, HTF FVG swept, tight stop): larger size (5 contracts instead of her usual 2) and a bigger target | 1:19:10–1:22:21 |
| E2 | B and C setups are taken too, with LESS size; a C setup does not get scaled in (there is still obvious liquidity on the other side) | 1:15:26–1:16:10, 1:42:14–1:44:44 |
| E3 | **[GAP]** the grade rule as numbers: default grade = number of confluences from C5–C9 (A+ ≥ 4, B = 3, C ≤ 2); size multiplier A+ 2.0, B 1.0, C 0.5 of the Lucid-fit base size (tighten-only: never above the Lucid-fit size) | — |

## F. Limits
| # | Rule | Time |
|---|------|------|
| F1 | A DOLLAR daily loss limit, not a trade count (hers: $3,000 on a personal account; scaled by account size). Even a first stop-out can be followed by another valid setup | 50:53–51:52 |
| F2 | On prop accounts with a consistency rule she trades smaller (e.g. 2 contracts on 50K) and prefers London for the tighter stops | 40:25–41:30 |

## H. Data limits (honest)
Paytience has 1-minute bars only and the old backtest history is regular hours only: London, the Asia range, the midnight
price, 15 / 30-second speed and the overnight part of AMD **cannot be tested** here. The NY open window, the 1-hour FVG, the
RTH gap and IFVG / FVG on 1-minute bars can.

## Left out on purpose
Trade replay and live-stream habits, psychology, "ICT noise" talk, copy trading across 20 accounts (Paytience: one free
account per trade, no copy trading), swing / overnight holds (not allowed by Lucid / Paytience), seconds charts.

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge (D139), feed
checks, live gates, EOD drawdown on Pro 25K–150K. Variable size from grades can only TIGHTEN the Lucid-fit size.

## Implementation notes (D149, 2026-11-16)
Engine `backend/app/engine/candace_ict.py` (pure, 1-minute bars) — `replay_day(history: list[MBar], today: list[MBar],
cfg, tick) -> CandaceDay` (history = earlier days for the previous-day pools and the RTH gap; today = this ET day's bars,
any hour). Hook `strategy_service.run_candace_ict`; key `MNQ-CAND-<day>-<HHMM>`; plan mode `CANDACE_ICT`;
`strategy.candace_ict` (default OFF) + `strategy.candace_ict_cfg`.
**Built:** A1 (1-hour FVG from 1-minute bars; weekly / daily candles not used), A2 (50% of the last 60 bars' range = gap),
A3 (equal highs / lows within 2 ticks, 2-bar swings, previous-day and session high / low, 1-hour FVG edges), A4, B1
(London 02:00–05:00, OFF), B2/B4 (NY 09:00–10:00, 15-min max hold, `CAND_TIME_EXIT`), C1, C2, C3 (entry at the close of
the retrace bar), C5 (body ≥ 1.5 × 10-bar average), C7 (HTF FVG confluence), C8 (RTH gap 0/25/50/75/100% levels as a
confluence), C10/E3 grades (confluences: displacement, equal pool, HTF FVG, RTH gap, previous day; A+ ≥ 4, B 3, C ≤ 2),
D1 (2 ticks past the sweep extreme), D2 (NY 40 / London 25 pt → skip, never widen), D3 (≥ 1:2, extended to the nearest
pool beyond), F1 = Lucid DLL + max 3 losses a day (sizing divisor). **E1/E2 size:** multipliers 2.0 / 1.0 / 0.5 applied
TIGHTEN-ONLY as multiplier ÷ 2.0 of the Lucid-fit size (A+ = full fit size, B half, C a quarter; `CAND_GRADE_SIZE_BELOW_1`).
**Not built:** C4 aggressive entry, C6 volume imbalance / order block, C9 SMT with ES, D4 partial at the first internal
pool and D5 break-even after 25% of the move (the existing management only moves to break even on a leg fill — single
bracket ships; follow-up), D6 templates, A5/A6 Asia range, midnight price, new-week gap.
**Cannot be tested here:** London, the Asia range, the midnight price, the 15 / 30-second speed (1-minute, RTH-only
history). Fit table = BRUNI's (same divisor): 25K $158.33 (3 micros @20 pt), 50K $360 (8), 100K $540 (12), 150K $810 (19);
FUNDED 25K $180 (4).
