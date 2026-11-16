# GALA PRICE ACTION — rule sheet (from ONE transcript only)

Source: Chart Fanatics episode with "Gala Trades" (Kamjan) — price-action strategy (trend, hourly levels, break and retest,
bounce, rejection), then a live trade, pasted by the user on 2026-11-16. Times below are the transcript's `h:mm:ss`.
Nothing here is copied from JJ F.P.T, NOISE, Order Flow or any other Paytience strategy; only app plumbing (bar feed,
order routing, Lucid safety checks) is shared.

He trades stock OPTIONS (TSLA, SPY, QQQ, AMD, PLTR, MSFT) in the video, and says he trades ES and NQ futures with the
same setups (1:42:56 – 1:43:44). Paytience trades MNQ micros, so the price-action rules are applied to MNQ and the
option-only parts (strike, expiry, IV decay, % option stops) are left out (listed at the end).

Rules marked **[GAP]** are not given as a number in the transcript. They are config settings with a documented default,
shown on the card as "not from the video", and must never be tuned to make a backtest look better.

## A. Pre-market plan (done before the open)
| # | Rule | Time |
|---|------|------|
| A1 | Trend and levels are marked on the **hourly** chart, before the open | 4:37, 10:12–10:23, 16:46–17:01 |
| A2 | Trend = highs and lows, not channel lines: higher highs + higher lows = up (calls = LONG); lower highs + lower lows = down (puts = SHORT). The trend only picks the SIDE | 2:19–4:12 |
| A3 | Choppy / inconsistent trend, or a chart that "looks weird" → skip it, no trade | 3:05, 10:28–10:41, 17:56–18:11 |
| A4 | A level = a pivot on the hourly chart. Use candle BODIES, ignore wicks: draw it at the OPEN of the hourly candle where the colour changes (green after red, or red after green) | 4:52–5:53 |
| A5 | The day's opening price is also a level (lower confidence: 3 of 5; regular pivots 5 of 5; invalidated 2.5 of 5) | 1:07:25, 1:12:05–1:12:24 |
| A6 | A candle that pierces through a level invalidates it (delete it, or keep a dashed lower-confidence line) | 1:07:04–1:07:17, 1:09:28 |
| A7 | Use regular trading hours only. Extended hours (pre-market and after-hours) are one candle, from the close to the next open | 1:02:32, 1:13:22–1:13:55 |
| A8 | Note where price is closer to: the higher or the lower level. If the plan is LONG and price is closer to the upper level → look for a break-and-retest of it; if closer to the lower level → look for a bounce off it. SHORT mirrors (rejection) | 5:59–6:49, 29:25–30:17, 34:13–34:46 |
| A9 | Check the economic calendar; trade only when nothing is scheduled in the first hour | 1:22:57–1:23:49 |
| A10 | Keep the watch list short; trade only names where the trend is clear and the chart looks clean | 1:09:11, 1:15:21 |

## B. The open
| # | Rule | Time |
|---|------|------|
| B1 | Do not trade the first 5 minutes of the open (he skips the first 5-minute candle; he is thinking of cutting this to 2 minutes, but the rule today is 5) | 1:24:36–1:25:07, 1:27:20 |
| B2 | All entries and exits are within about 1 hour of trading a day (trades usually last under 1 hour) | 11:03, 13:06–13:18, 39:11 |
| B3 | Do not go against the market: if the indices are weak and the plan is LONG, skip it (relative strength matters) | 1:33:07–1:33:18, 1:38:22 |
| B4 | If every plan is invalidated, stop for the day; do not force trades | 1:29:00–1:29:22 |
| B5 | Plan is LONG but the trend flips only on very strong index trending → still only tiny size against the plan (no rule given; not built) | 1:34:22–1:34:54, 1:37:09 |

## C. Entry setups (2-minute and 5-minute charts; the 5-minute decides)
| # | Rule | Time |
|---|------|------|
| C1 | Entry candles are read on the 2- to 5-minute chart; the 5-minute chart is preferred and decides. If 2-min looks good but 5-min looks bad → no trade | 10:23–10:50, 1:32:05–1:32:40 |
| C2 | **Perfect entry candle**: its wick goes slightly BELOW the level (LONG) but its BODY is above / closes above the level. The wick should be small ("not too big, not too tiny") | 7:35–8:02, 13:53–14:20 |
| C3 | The level must be touched. Best case = a dip slightly through the level and back above. Missing the touch is accepted ("missed opportunity") | 7:28–7:42, 13:38–13:45 |
| C4 | Skip a candle that touches the level and reverses very fast with a big wick ("hammer"): the stop would be too wide | 9:48–10:06, 14:20–14:52 |
| C5 | **Break and retest**: a candle CLOSES beyond the level on the 5-minute chart (the breaking candle), then a following candle retests the level and holds (small wick through the level, body on the right side). One retest candle is the minimum; several retest candles are fine. Price must be accepted beyond the level, not back through it | 17:53–19:03, 6:38–6:59 |
| C6 | With several retest candles, the stop goes at the lowest wick (LONG) of the closely grouped candles | 19:19–19:50 |
| C7 | **Bounce** (LONG, off a level below price): wait for 2–3 candles on the 5-minute whose BODIES stay above the level while the WICKS go below it (sellers fade, buyers hold) | 30:05–31:50 |
| C8 | **Rejection** (SHORT, off a level above price): 2–3 candles with bodies below the level and wicks pushing above it; lower high at the level, continuing to a lower low | 34:13–37:47 |
| C9 | Entry as close to the level as possible; better entry = easier 2R. "Good entry or no entry" | 8:10–8:15, 38:03–38:46 |
| C10 | Continuation of the trend (low to high) is the same setups on any timeframe; he lists only three setups: break-and-retest, bounce, rejection | 41:18–42:01 |

## D. Stop, target, management
| # | Rule | Time |
|---|------|------|
| D1 | Stop just beyond (a pixel past) the lowest wick of the retest / bounce candles (LONG), highest wick (SHORT) | 8:15–8:28, 19:35–19:50, 30:38 |
| D2 | If the stop distance is too big (big wick), take a smaller size or skip | 14:34–14:52, 30:45–31:05 |
| D3 | Target = **2R** (1.5R is fine; more than 2R is exceptional). Small steady trades make most of the year's profit, not home runs | 15:11–15:26, 19:50–20:20, 40:17–40:37 |
| D4 | At 2R trim about **half** (50%); the rest runs. Trim can be 20–30% when momentum is strong (many same-colour candles); after a losing first trade he closes 80–100% | 22:43–23:10, 23:17–23:59, 24:27–24:56 |
| D5 | After trimming, move the stop up; keep moving it candle by candle (the candle's open) until the stop is above entry, so even a stop-out is profitable | 15:44–16:29, 24:56–25:34, 32:28–32:41 |
| D6 | Keep a small runner (about 10%) only when there is big space to the next level; do not hold a trade more than about an hour without reason | 38:46–39:22 |
| D7 | If the next level is close to the entry it can overlap the 2R target (fine, but cautious: levels reverse price); room to the next level is a plus | 33:10–34:06 |
| D8 | Hold to target or stop; do not look at the P&L, only the chart; do not close early because of P&L | 1:01:28–1:02:16, 1:44:36 |

## E. Limits and discipline
| # | Rule | Time |
|---|------|------|
| E1 | **Maximum two attempts on the same setup** (a second entry after a stop-out is allowed; a third is a broken rule) | 27:38–28:39 |
| E2 | 2–3 trades a day; 4 or more is overtrading | 35:32–35:50 |
| E3 | After a WINNING trade he stops ("one and done", preserving mode); after a winner he does not re-enter the same level | 1:50:09–1:50:28, 1:58:26 |
| E4 | Accept the stop: never move it further away or cheat a smaller loss | 26:23–27:15, 1:45:06 |
| E5 | Risk per trade is an amount he can accept (e.g. $500–$1,000 of loss); if not comfortable, size down or skip | 26:53–27:15 |
| E6 | Size scales with confidence in the level (5/5 level full; opening-price level less) | 1:12:31 |
| E7 | After a loss, the next trade is more conservative: smaller size and bigger trims | 23:17–23:40 |

## Conflicts and gaps
- **[GAP] pivot definition:** "pivoting point on the hourly" with no bar count. Default: a 3-bar pivot on the hourly body (the
  body-open of the colour-change candle), `pivot_lookback` setting.
- **[GAP] "slightly lower than the level":** no number. Default: wick may pass up to `max_wick_through_pts` (a fraction of the
  stop, set in the config) but the body must close on the right side.
- **[GAP] "retest candle" count and the break distance:** default minimum 1 retest candle within `max_retest_bars` 5-minute bars.
- **[GAP] "two to three trades a day":** default 3 trades a day max (E2) and 2 attempts per setup (E1).
- **[GAP] "within about one hour":** window default 09:35–10:35 ET (after B1, one hour). Configurable; not tuned.
- **Trim at 2R vs. "level to level":** the video does both (levels as targets on the live trade). Default: trim half at 2R.
- **E3 vs E2:** one winner ends the day (E3), up to 3 trades otherwise (E2).
- **Opening-price level:** only the day's own open is available from 1-minute RTH bars; the hourly pivots need prior sessions.

## Not mechanical or option-only (left out on purpose)
Option strike and expiry choice, IV crush and decay, % option stop (5–10%), Bookmap / order-flow confirmation (he calls it a
"confirmation tool, not the core strategy"), relative strength vs the indices for single stocks (kept only as B3 for the
index itself), "bad feeling" judgments (chart looks weird), journaling and star ratings, switching calls to puts
mid-day, tiny "adventurous" size trades, size by position dollars ($10K / $40–50K).

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge (D139),
feed checks, live gates, EOD drawdown on Pro 25K–150K. A signal that hits one of these is skipped with its reason code.
