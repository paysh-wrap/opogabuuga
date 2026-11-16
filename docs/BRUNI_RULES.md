# BRUNI STRUCTURE — rule sheet (from ONE transcript only)

Source: Chart Fanatics master class with Gianluca Bruni (a statistical / mechanical trader, ex-discretionary), pasted by the
user on 2026-11-16. Times are the transcript's `h:mm:ss`. Nothing here is copied from any existing Paytience strategy;
only app plumbing is shared.

He is a **statistical** trader: a context (market structure), supply / demand zones ("triple print"), a liquidity filter
("wick gap"), a statistically chosen fixed target, and several RISK models (autocorrelation, Kelly, drawdown shield,
regime flip). He says himself that the risk model matters more than the entry (2:08:25–2:08:43).

**The video never shows his exact entry trigger** ("we will see later on the target, the trigger", 26:25–26:34; it is not
shown). What it does give is the context rules, the zone rule, the filter and the target method. The trigger below is a
flagged **[GAP]** reading of what he does say (an entry at the zone / "inefficiency", stop beyond it, 58:32–58:51), and the
card says so. Every **[GAP]** is a config setting with a documented default, never tuned to make a backtest look better.

## A. Context: peripheral (P) and actual (A) structure
| # | Rule | Time |
|---|------|------|
| A1 | ONE time frame only, 15-minute (he tested 15 and would have to re-test everything for 30 or 5). Never mix time frames | 16:05–16:24, 37:07–37:38 |
| A2 | A BREAKOUT = a candle BODY closes beyond the level, not a wick. A breakout also needs "a certain level" **[GAP]** (number never given; default: body closes beyond by at least `breakout_min_ticks`) | 25:07–25:27, 35:42–35:47 |
| A3 | Only the LAST TWO breakouts count. The latest true breakout = ACTUAL structure (A); the one before = PERIPHERAL structure (P). A third breakout drops the oldest | 13:40–15:53, 31:52–32:11 |
| A4 | When A and P point the same way, go with them; never trade against both | 14:37–14:44, 25:50–26:06 |
| A5 | When A and P disagree: follow A, but only until the DIRECTIONAL POTENTIAL is used up; then follow P | 14:44–14:53, 16:32–17:53 |
| A6 | Directional potential, simple version: a Fibonacci of the structure leg; the 75% level = the discount / premium limit. Short version: follow a bearish A until price reaches the discount (75%) level, then follow the bullish P (long) | 16:58–17:53 |
| A7 | Directional potential, precise version (he tested both; results similar, this one a little better): a volume profile; the VALUE AREA LOW (for a bearish A) / VALUE AREA HIGH (bullish A) is the limit. A wick may take it; a body is not needed for this level | 18:00–20:36, 35:34–35:47 |
| A8 | If price makes two more breakouts without touching that level, it needs not touch it ("follow the strength of the market") | 40:10–40:22 |
| A9 | A zone where price came back, reacted and changed structure "made it work" and becomes B+A (more important); breaking it flips the context from long to short (or the reverse) | 28:08–29:29 |
| A10 | INTERNAL structure: a retracement with no breakout. If price reaches the value-area level and then breaks the internal structure by a body, that break becomes the actual structure (the old A becomes P) | 32:50–38:09 |
| A11 | A break is traded as a BREAKOUT, not guessed as a liquidity sweep (tested: better result) | 30:18–30:41 |
| A12 | No breakout = no trade | 25:27–25:34 |

## B. Zones: "triple print" (42:11–50:51)
| # | Rule | Time |
|---|------|------|
| B1 | A candle is VALID if its BODY is larger than its longest WICK. A candle with a wick longer than its body is not valid | 42:50–44:28 |
| B2 | A demand (long) zone needs THREE valid sell candles in the retracement before the impulse (a supply zone: three valid buy candles). They need not be consecutive; invalid candles in between are fine; more than three: ignore the extras | 44:52–47:37, 49:16–49:41 |
| B3 | Two valid candles is not a zone | 46:40–46:56 |
| B4 | The zone = the latest three valid candles closest to the impulse (before the impulse starts), from the first to the third | 48:07–48:42, 49:01–49:16 |
| B5 | If an impulse has no triple print, go to the next one down; if there is no triple print anywhere in it, it is not a breakout | 49:55–50:51 |
| B6 | Triple (3) was tested against 2 and 4: 2 failed, 4 got worse | 1:06:56–1:07:22 |
| B7 | **[GAP]** the video says the time frame for this is "50-minute"; it conflicts with A1 (15-minute). Default: the same 15-minute chart as A1 (config `zone_tf_minutes`) | 49:49–49:55 |

## C. Wick-gap filter (57:35–1:07:44)
| # | Rule | Time |
|---|------|------|
| C1 | Take the TWO wicks closest to the stop loss (any candles, either colour). Measure the distance between them | 58:12–59:23, 1:04:46–1:05:21 |
| C2 | If the distance is TOO SMALL, the setup tends to stop out: skip it. Close/far is measured by numbers, not feel | 59:23–1:00:29 |
| C3 | He found the threshold by testing 0.1, 0.2, 0.3, 0.4, 0.5, 0.6 pips on 1,000+ trades each: ≤ 0.2 lost, 0.3 break-even, 0.4 first profitable, 0.5 better, 0.6 worse → threshold 0.5 pips for his markets | 1:00:43–1:04:37 |
| C4 | The rule for a new market: sweep the threshold upward until the result stops improving and take the best; do this in-sample only | 1:03:47–1:04:37 |
| C5 | **[GAP]** the pip value for MNQ is not in the video: the threshold is a config number in points, to be found by C4 in-sample, default off until measured | — |

## D. Entry (flagged — not shown in the video)
- **[GAP]** Entry: when A, P and the directional-potential rule (A) agree on a side, a valid triple-print zone exists (B), and
  price returns into that zone, enter toward the context at the zone edge ("as close as possible", "the inefficiency",
  58:32–58:51). Stop beyond the far edge of the zone / the highest or lowest wick. Defaults are config, marked
  `# not from the video`.
- Session: he trades mostly from the Asian session range and the London and New York sessions after it (26:06–26:18) and
  holds "a few hours to one or two days" (1:21:23–1:21:38). Paytience / Lucid are intraday only (flat 16:44 ET), so the BUILT
  window is the **New York session**, flat at the end of the day. The Asian-range schematic is not built (needs overnight
  data and positions held past the close).

## E. Target
| # | Rule | Time |
|---|------|------|
| E1 | Fixed risk : reward per market. The OPTIMAL TARGET is found by testing 1, 1.5, 2, 2.5, 3, 3.5, 4 … on hundreds or thousands of trades and keeping the one with the most total R (look at what you left on the table, and at the win-rate trade-off); he never goes above 1 : 3 for lack of support in the data | 1:40:38–1:44:51 |
| E2 | Usually about 1 : 2; a negative risk : reward was tested and is not optimal for him | 1:44:19–1:45:43 |

## F. Risk models (his heart of the strategy)
| # | Rule | Time |
|---|------|------|
| F1 | Fixed risk size by default. Do not vary the size on a "feel" (A+ setup) unless the math says so (autocorrelation); otherwise you are gambling | 1:53:38–1:55:17 |
| F2 | AUTOCORRELATION of results: win rate after a LOSS (conditional) vs the overall win rate (unconditional). Overall > conditional → POSITIVE (wins and losses come in streaks); lower → NEGATIVE (alternates); about equal → zero. Strength by the gap in points of win rate: 0–2 none, 3–4 weak, 5–6 solid, 7–8 strong, 9–10 extreme (extreme = suspect an error) | 1:55:36–2:01:48 |
| F3 | Positive autocorrelation: after a win raise the risk; after a loss take the next trade smaller or skip it. Negative: the reverse. Zero: fixed risk. Needs a long sample (hundreds to thousands of trades) | 2:02:09–2:05:06 |
| F4 | KELLY: how much to risk per trade; the full Kelly is too aggressive, so risk a FRACTION: a strong signal uses Kelly / 3, weaker Kelly / 4 or / 5. **On a prop firm account use fixed risk instead of Kelly** | 2:07:16–2:11:49 |
| F5 | DRAWDOWN SHIELD (prop firms): instead of one big account use several smaller accounts (his example: 4 x 50K instead of one 200K) risking the same %, and trade ONE account per WEEK. A losing month usually still contains winning weeks, so some accounts earn payouts while others stay safe; if an account is lost, move to the next. Payouts stay smaller and steadier | 2:11:56–2:22:14 |
| F6 | REGIME FLIP: bucket the volatility forecast into calm / middle / high / extreme (he uses GARCH; no formula given **[GAP]**, default realized volatility of the last N 15-minute bars). Measure the win rate of the strategy in EACH bucket in-sample. If a bucket has a very bad win rate (his example: 75% LOSS rate at 1 : 1 in the calm bucket), trade the OPPOSITE side there; he doesn't ask why, he follows the data | 2:29:52–2:36:20 |
| F7 | VARIANCE ACCELERATOR (VAM; autocorrelation by regime + Kelly, e.g. 0.5% to 3%): the championship model, not for prop accounts. NOT built | 2:24:49–2:27:43 |

## G. How he validates (the backtest procedure for this strategy)
| # | Rule | Time |
|---|------|------|
| G1 | A sample of at least 1,000 trades; below that variance can still lie | 53:15–53:51, 1:25:03–1:26:13 |
| G2 | CHUNK optimization: cut the trades into 10 equal chunks and check each chunk's win rate / profit factor; stable across chunks = an edge; a big swing (more than ~20 points of win rate in half of the chunks) = coincidence | 1:12:34–1:17:47 |
| G3 | Include costs: spread, commission, slippage (he haircuts results by about 5%), swap | 1:18:16–1:25:03 |
| G4 | Metrics: EXPECTANCY per dollar risked (0.10–0.30 healthy; 0.40–0.50 strong; above 0.50 amazing), profit factor (and again without the single best trade), Sharpe | 1:31:40–1:40:20 |
| G5 | Monte Carlo reshuffle for the worst-case drawdown and the longest losing streak | 1:26:48–1:30:37 |
| G6 | Bar-replay-style honesty: no look-ahead | 1:11:25–1:11:50 |

## Left out on purpose
Forex-only specifics (pips, spreads, swap, 33 assets, "no good result on metals"), holding 1–2 days (overnight), the Asian
range schematic (needs overnight data), VAM (championship, not prop), the discretionary SMC concepts he left behind, GARCH
as a model (no formula in the video; a flagged proxy is used).

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge (D139), feed
checks, live gates, EOD drawdown on Pro 25K–150K. Variable sizing from F3 can only TIGHTEN the Lucid-fit size (never above
it). A signal that hits one of these is skipped with its reason code.
