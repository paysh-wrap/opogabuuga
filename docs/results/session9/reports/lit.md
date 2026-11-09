# lit — literature review: intraday, flat-by-close strategies for MNQ / MGC (2026-11-09)
Web research only, no backtests. Tags: [V] = checked against an abstract or a summary this session.
[M] = from memory of the paper, not re-checked against the PDF this session; check before coding.
News blackouts are not covered anywhere in this report.

## Main finding
No published intraday edge reaches a high win rate and positive expectancy at the same time.
- The credible momentum effects (noise-area breakout, ORB, market intraday momentum) win only 20–45% of trades. They make money because the winners are large.
- Mean-reversion rules with high win rates (RSI(2), gap fades) are daily or overnight effects. Their published edge has decayed, and a fat-tail loss can erase many small wins.
- An independent replication of the 5-min ORB reproduced the gross result on NQ but came out at about 0 R net of costs.

## 1. Noise-area intraday momentum [V]
- **Source:** Zarattini, Aziz & Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", SFI RP 24-97 (2024).
  - https://ideas.repec.org/p/chf/rpseri/rp2497.html
  - https://concretumgroup.com/beat-the-market-an-effective-intraday-momentum-strategy-for-sp500-etf-spy/
- **Tested on:** SPY, 1-min data, 2007 → early 2024.
- **Bands (noise area):**
  - For each minute-of-day t, sigma_t = mean over the last 14 days of |close_t / open_day − 1|.
  - Upper band = max(open, prior close) × (1 + sigma_t). Lower band = min(open, prior close) × (1 − sigma_t).
  - Prior close is used to adjust for the gap.
- **Entry:** check only on 30-min marks (10:00, 10:30, …). Go long if the price is above the upper band, short if below the lower band.
- **Exit:**
  - Trailing stop at the band, or at max(band, VWAP) for longs and the mirror for shorts.
  - Checked at the same 30-min marks.
  - Flat at the close.
- **Sizing:** volatility-targeted, using a 14-day daily-volatility target with a cap on leverage.
- **Reported (net):**
  - About 19.6% a year, Sharpe 1.33, max drawdown about −25%.
  - Costs: commission plus slippage of $0.001/share was modelled.
  - Win rate is about 40–45% [M], with an average win well above the average loss.
- **Out-of-sample:** none. CXO calls the results in-sample.
  - Quantpedia Awards 2025, 4th place.
  - Public TradingView ports exist ("Concretum Bands").
- **Transfer:** should carry over well to MNQ (Nasdaq trends harder than SPY), using RTH 09:30–16:00 only.
  - MGC: unknown. The paper's mechanism is equity-index gamma hedging.
  - It needs a fixed 2R target removed. Exits are trailing or at the close, so this conflicts with the app's rr_max of 2.5.

## 2. Opening-range breakout (5-min ORB) [V]
- **Sources:**
  - Zarattini & Aziz, "Can Day Trading Really Be Profitable?", SSRN 4416622 (2023): https://papers.ssrn.com/abstract=4416622
  - Follow-up: Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy for the U.S. Equity Market" (Stocks in Play), SFI RP 24-98: https://ideas.repec.org/p/chf/rpseri/rp2498.html
- **Tested on:** QQQ and TQQQ, 2016 → Feb 2023, 1,795 trades.
- **Rules:**
  - The direction of the first 5-min candle (09:30–09:35) sets the side. A doji means no trade.
  - Entry: at the open of the 09:35 bar.
  - Stop: the opposite extreme of the first candle.
  - Target: 10R, or exit at the close.
  - Sizing: risk 1% of equity, with a leverage cap of 4×.
- **Reported:**
  - CAGR 33% vs 15% for buy-and-hold, at zero slippage.
  - Win rate about 24%.
  - The Stocks-in-Play version (relative volume over 100%, top 20 names) reports a much higher Sharpe.
- **Independent replication [V]:** MQL5 blog, NQ/SPX/Dow/DAX/FTSE CFDs, 2015–2026, rule applied unchanged. https://www.mql5.com/en/blogs/post/776235
  - Gross: NQ +0.131 R per trade, which reproduces the paper.
  - Net: +0.002 R. Four of five markets were negative.
  - Win rate 20–23%. Costs were 6–12% of risk.
  - In plain terms: the edge is real but smaller than retail-level costs. On MNQ, $1 fee + 2 ticks ≈ $2/RT against a typical stop of about 20–40 pts ($40–80), so costs are about 3–5% of risk. That is lower than the CFD costs in the replication, so MNQ might keep a small edge. This is not verified.
- **Conflicts with the app:** the strategy is defined on the excluded 09:30–09:35 window (D10). Its win rate of about 24% fails the user's win-rate goal.

## 3. VWAP trend trading [M]
- **Source:** Zarattini & Aziz, "Volume Weighted Average Price (VWAP): The Holy Grail for Day Trading Systems", SSRN (2023).
- **Tested on:** QQQ and TQQQ, 2018–2023, 1-min bars.
- **Rules:**
  - Long when a 1-min close is above the session VWAP, short when below.
  - Reverse on each cross. Flat at the close.
- **Reported:** large CAGR and Sharpe of about 2, with a very low win rate (about 17%) and many whipsaws.
- **Costs:** the turnover makes this highly cost-sensitive. Replications on futures that I know of are anecdotal.
- **Transfer:** cost is the killer on MNQ (dozens of round trips a day).
- **Verdict:** use VWAP only as a filter or trailing stop (as in #1), not as a signal. The app already has filters.trend.vwap (D44).

## 4. Market intraday momentum (first half-hour → last half-hour) [V/M]
- **Sources:**
  - Gao, Han, Li & Zhou, JFE 129 (2018) [M]: SPY 1993–2013.
    - Signal: the return from the prior close to 10:00 predicts the 15:30–16:00 return (R² about 1.6%, more on high-volatility and high-volume days and before news).
    - Timing strategy: about 6.7% a year, Sharpe about 1.1.
  - Baltussen, Da, Lammers & Martens, JFE 142 (2021) 377–403 [V]: https://www3.nd.edu/~zda/intramom.pdf
    - 60+ futures (equity, bond, commodity, FX), 1974–2020.
    - Signal: the return from the prior close to 15:30 predicts the last 30 minutes. The effect is strongest when market makers' net gamma exposure is negative, and absent when it is positive.
    - The effect reverts over the next days.
- **Rules:**
  - At 15:30 ET, sign(r[prev close → 15:30]) sets the side.
  - Enter at 15:30 and exit at 16:00 (before 16:40, so it fits Lucid's flat time).
  - No stop or target in the paper.
- **Edge per trade:** a few bps. The win rate is about 52–55% [M].
  - Gold: Baltussen reports commodity futures too, including gold, though the effect is weaker than for equities [M].
- **Decay:** several replications report the SPY effect weakened after 2013, but it is still present in futures with large index option and leveraged-ETF hedging [M].
- **Transfer:** a cheap test on MNQ (1 trade a day). It is hard to wrap in a 1.5–2.5R bracket inside a 30-min window, which conflicts with the app's TradePlan.

## 5. Gold session effects [V]
- **Evidence:**
  - Caminschi & Heaney, J. Futures Markets 34(11) 2014: price reaction of GC futures and GLD around the London PM fix. https://ideas.repec.org/a/wly/jfutmk/v34y2014i11p1003-1039.html
    - Price moves were predictable before the fix announcement, which is evidence of information leakage.
    - The fix moved to the electronic LBMA auction in 2015, so the pre-2015 effect is likely gone.
  - Overnight vs day returns (scinapse 2735606157): gold returns are positive overnight and negative in the day session, a "hat-shaped" pattern. Asian hours rise and the US session falls.
  - The supporting work is mostly student theses (CBS), which are not peer-reviewed.
  - The 2007 IIIS paper by Batten covers COMEX gold volatility patterns only.
- **What is missing:** I found no peer-reviewed, codeable gold intraday strategy with net results. The only usable lead is a "short-bias during the US session" seasonal tilt. It is weak, and it fits poorly with a flat-by-16:40 constraint that starts at 03:00.
- **Caution:** do not build on blog claims about the Asian range or the London-open breakout. None had out-of-sample evidence.

## 6. High-win-rate mean reversion [M]
- **Connors RSI(2):** the signal uses daily bars, the trade lasts about 1–5 days.
  - Rules: buy when the close is above SMA200 and RSI(2) < 10; exit when the close is above SMA5.
  - On SPY 1993–2010s: about 70–75% wins, small average gain, rare large losses.
  - Edge weakened after about 2010 in public replications. It is not intraday, so it is not compatible with flat-by-close.
- **Gap fade on index futures:** fill toward the prior close.
  - Small gaps (under about 0.3%) fill about 60–70% of the time. Large gaps tend to continue.
  - Expectancy after costs is near zero in honest tests. Bulkowski and Quantpedia-type summaries are not peer-reviewed.
- **VWAP-band (±2σ) fades:** no peer-reviewed net-of-cost evidence found. They contradict #1 and #4, which show that intraday extremes tend to continue on trend days.
- **Honest summary:** in this literature a high win rate comes with a negative tail. Required test: expectancy and PF on held-out data, not the win rate.

## 7. Decay, crowding and costs [V/M]
- McLean & Pontiff, J. Finance 71 (2016): anomaly returns are about 26% lower out-of-sample and about 58% lower after publication [M, well established].
- Every strategy above is public, and several have free TradingView ports. Expect less edge than published.
- Nearly every intraday paper above uses ETF costs. For futures, a fixed cost against a small stop is the main way edge is lost (see the ORB replication). Wider stops and fewer trades help.

## 8. ICT / smart-money concepts (liquidity sweep, CISD) [V: absence]
- I found no peer-reviewed or independent out-of-sample study supporting ICT or SMC concepts.
- The evidence is vendor or YouTube material and discretionary hindsight charts.
- Adjacent academic work: stop-hunting and stop-loss cascades exist in FX and futures (Osler 2005, "Stop-loss orders and price cascades") [M]. That does not validate the specific CISD rules.
- The app's own baseline (36% win, PF 1.12 on MNQ, negative on MGC) is consistent with "no edge established".

## 9. Moltbook / "secret society knowledge"
- **What Moltbook is [V]:** a Reddit-style social network for AI agents, launched in 2026. I read search summaries only; I did not register or post.
- **Trading content:** crypto memecoin signals and "pump" chatter. Reporters found scams and manipulation, and the membership numbers are disputed.
- **Verdict:** nothing verifiable and nothing on futures. There is no secret strategy. I found none, and an edge that really works is not something that circulates on social media.
- Sources:
  - https://wonderingaboutai.substack.com/p/moltbook-lurker-bot
  - https://www.datawallet.com/crypto/moltbook-explained

## Ranking for Paytience (credibility × expected edge after costs, MNQ / MGC)
1. **Noise-area momentum (#1) on MNQ, RTH.**
   - Why: strongest evidence and published net results, with a good-sized move per trade.
   - Test: bands from 14 days, 30-min checks, VWAP/band trail, flat at 16:00.
   - Note: win rate about 40%+; a fixed R:R must not be forced on it.
2. **Last-half-hour intraday momentum (#4) on MNQ, and MGC as a secondary.**
   - Why: peer-reviewed, held across 60 futures and 46 years.
   - Caveat: small edge per trade; check MNQ costs (about $2 per round trip against a typical 30-min move of about 20–40 pts).
3. **5-min ORB (#2) on MNQ.**
   - Why: replicated gross. Net is near zero on CFDs; MNQ costs are lower, so it is worth one held-out test.
   - Conflicts: needs the 09:30–09:35 exclusion lifted, and the win rate is about 24%.
4. **Noise-area or ORB with a 1.5–2.5R bracket.**
   - Why: a hybrid that fits the app's TradePlan. Not published, so it is research only and must pass the BRIEF's held-out test.
5. **Gold US-session short tilt or overnight-drift avoidance (#5).**
   - Why: weak evidence. Use it only as a bias filter on MGC (G2), not as a signal.
- **Not recommended as signals:** VWAP-cross (costs), RSI(2) and gap fades (not intraday or decayed), ICT/SMC (no evidence), Moltbook (unverifiable).

## Caveats
- [M] figures must be checked against the PDFs before anyone codes them.
- None of these papers assume prop-firm constraints (DLL, consistency rule).
- There is a conflict with the user's win-rate rule: the best-evidenced edges have win rates below 50%.
