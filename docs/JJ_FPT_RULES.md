# JJ F.P.T STRAT — rule sheet (from the transcripts only)

Source: four videos by JJ, pasted by the user on 2026-11-14. Nothing here is copied from another Paytience strategy;
only the app's plumbing (bar feed, order routing, Lucid safety checks) is shared. Each rule cites the video and time.

- **V1** "Step-by-step strategy that made me $1.6M" (80 trades, 8 days)
- **V2** "Every trade for $59K of payouts in 2 weeks" (at $1.828M; the NEWEST trading video)
- **V3** "$0 → $2M roadmap" (bankroll / scaling; no new entry rules)
- **V4** Chart Fanatics interview (whiteboard rules + live trading; recorded at ~$1.5M)

When two videos disagree the newer one wins (V2 > V1 > V4 for trading rules), and the conflict is listed below.

## Market and chart
| # | Rule | Source |
|---|------|--------|
| 1 | NASDAQ futures only (NQ; the app trades MNQ micros, same points) | V4 22:48 |
| 2 | 1-minute chart for everything; waits for candle CLOSES, never wicks or limits | V4 5:57, V1 15:02, V4 18:35 |

## Sessions
| # | Rule | Source |
|---|------|--------|
| 3 | Trade the first 90 minutes of a session open: 5 min continuation + 85 min reversion | V1 1:47, 2:48; V4 12:02 |
| 4 | New York 09:30 ET is the best and the main session; done at 11:00 and sticks to it | V1 1:39, 11:35 |
| 5 | Also trades 6 PM (18:00) and Asia (20:00) opens, and NY PM 14:00 | V2 0:59–5:42; V4 12:02, 42:26 |
| 6 | Sometimes goes past 11:00 only when fewer than 10 trades were taken | V2 22:23 |

## Fair price
| # | Rule | Source |
|---|------|--------|
| 7 | Fair price = the session's opening price, 95% of the time | V1 2:48; V4 3:43 |
| 8 | Expected 8:30 red-folder news is priced in: fair = the pre-news price (open of the 8:30 candle); the news move is reverted | V1 21:20; V4 13:07 |
| 9 | News day at 09:30: if the open comes back to the pre-news price, pre-news stays fair; if the open continues away from it, the 09:30 open is fair | V4 1:02:05 |
| 10 | If price breaks structure AWAY from fair price and continues (volume moves it away), delete the old fair price; the new one is the most recent consolidation | V1 8:17, 10:43; V4 32:50 |
| 11 | No adjustment while price is coming back toward fair | V1 13:40 |
| 12 | Asia: fair = Asia open, unless Asia's first move goes straight to the 6 PM open → 6 PM open is fair | V2 1:31, 12:02, 35:09 |
| 13 | NY PM 14:00: revert back toward the 09:30 price | V4 42:26 |

## Continuation (first 5 minutes)
| # | Rule | Source |
|---|------|--------|
| 14 | Direction = opening candle colour; enter at its close if it breaks the previous candle's structure | V1 5:17; V4 4:25 |
| 15 | Must align with the higher-time-frame bias = the reverse of the previous 6–12 hours | V4 3:54 |
| 16 | No continuation into a huge wick rejecting that side | V1 18:59 |
| 17 | More continuation entries inside the first 5 minutes whenever it breaks structure in favour; none after minute 5 | V2 36:18, 30:12 |
| 18 | Opening candle body > 25 pt → 50 pt stop / 76 pt target (half the contracts); else 25 / 38 | V1 6:03; V4 4:38; V2 18:22 |
| 19 | 6 PM: no continuation against the gap; take it if the opening candle filled the gap | V2 0:59, 6:56, 16:07, 19:23, 23:14 |
| 20 | No continuation trades off the 8:30 news candle | V2 7:40; V4 1:08:49 |

## Reversion (minute 5 → 90)
| # | Rule | Source |
|---|------|--------|
| 21 | Only trades toward fair price (above fair → shorts, below → longs) | V1 2:39; V4 4:54 |
| 22 | DISPLACEMENT: body larger than the previous body AND closes beyond the previous candle's wick | V4 5:23; V1 6:16 |
| 23 | It must displace a candle of the opposite colour | V4 1:09:30 |
| 24 | BREAK OF STRUCTURE: a wick lower (higher) than the candles before and after it; enter on a CLOSE beyond it | V4 6:49, 55:01; V1 15:02 |
| 25 | Room = points to fair price. 30–76+ → 25 / 38; 15–30 → 12.5 / 19 with double contracts; < 15 → no trade | V2 9:40, 26:34, 35:51 |
| 26 | After two losses, wait for a break of structure | V2 31:26 |
| 27 | Three losses in a row in a session → done for that session | V4 34:35 |

## Size and accounts
| # | Rule | Source |
|---|------|--------|
| 28 | Same dollars at risk on every trade (halve / double contracts with the stop) | V2 9:24; V4 1:06:47 |
| 29 | 25 pt on 1 NQ = $500 on a $2,000 drawdown → 25% of the drawdown per trade | V4 22:42, 1:06:04 |
| 30 | One account at a time; a layered entry goes on ANOTHER account; never copy trade | V1 9:16, 14:10, 26:55; V4 38:47 |
| 31 | Evaluations: every displacement + break of structure. Funded: break of structure only | V4 9:38 |
| 32 | Consistency-rule accounts stay at 1:1.5 (Lucid has consistency → 25 / 38 on every stage) | V4 11:16 |
| 33 | Hold to target or stop; break-even only when the next session opens mid-trade | V1 16:35; V2 4:20 |

## Conflicts and how they are resolved
- **12.5 pt stops in New York**: V4 1:09:54 says "never less than 25 points in the New York session"; V2 (newer) takes
  19 / 12.5 trades in New York (CPI Wednesday). → V2 wins: rule 25 is ON; `small_room_tier: false` turns it off.
- **Three losses then stop (27)** vs V1 day 3 (kept trading after 3 losses because the fair price moved). → The loss
  count restarts when the fair price is adjusted (rule 10).

## Not mechanical (left out, on purpose)
Tweets / unexpected news (cannot be seen in bars), "combine two or three candles" (discretion; switch
`combine_candles`, default off), A+/A/B grading, per-account dollar targets from his private dashboard (mentorship),
London (he does not trade it: V2 20:44).

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge
(D139), feed checks, live gates. A JJ signal that hits one of these is skipped with its reason code.

## Lucid Pro fit (D143, sizing only — the entry rules above are unchanged)
Per-trade risk = min(`risk_pct_of_drawdown` × MLL, DLL left today × `dll_use_pct` / `stop_after_losses`,
(equity − EOD-trailed MLL − kill distance) / `stop_after_losses`, `strategy.max_trade_risk_usd`, consistency day stop /
`stop_after_losses`) — `engine/jj_fpt.trade_risk_usd`, numbers from the plan yaml (`jj_fpt_cfg`, DLL via `dll_for`
incl. LucidScale). So JJ's worst session (3 losses in a row) fits the DLL, the day stop and never reaches the kill
switch. Contracts = risk ÷ (stop $ + fee + 2 × slippage), then firm max micros and `internal_max_micros`; < 1 →
`JJ_SIZE_BELOW_1`. Fixed-size handling as NOISE: no TP-reward fit, flattened live at the consistency day stop (N6);
flat 16:40 / 16:44, news flatten and the news blackout (wider of the EVAL / FUNDED windows) apply. Fresh account, MNQ
($52 / $27 / $102 per micro at 25 / 12.5 / 50 pt), EVAL and FUNDED (same numbers):

| Plan | MLL (EOD) | DLL | Consistency cap / day stop | Per-trade risk | 25 pt | 50 pt | 12.5 pt |
|---|---|---|---|---|---|---|---|
| Pro 25K | $1,000 | $600 | $500 / $475 | $158.33 (day stop / 3) | 3 | 1 | 5 |
| Pro 50K | $2,000 | $1,200 | $1,200 / $1,140 | $360 (DLL × 0.9 / 3) | 6 | 3 | 13 |
| Pro 100K | $3,000 | $1,800 | $2,400 / $2,280 | $540 (DLL × 0.9 / 3) | 10 | 5 | 20 |
| Pro 150K | $4,500 | $2,700 | $3,600 / $3,420 | $810 (DLL × 0.9 / 3) | 15 | 7 | 30 |

Asserted in `backend/tests/unit/test_jj_lucid_fit.py` from the real plan yamls. VERIFY: Lucid fees/slippage, LucidScale
DLL interpretation (D138), funded consistency reference (= eval target until the cycle profit is larger).
