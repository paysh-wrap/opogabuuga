# last30days post-build check (2026-11-24)

Caveat: the last30days engine could NOT be run. This session had no shell tool, so there was no Bash, yt-dlp or engine. Everything below comes from WebSearch only. No engine reports were saved to /root/Documents/Last30Days. Re-run the three topics if you want the engine pass. I did not open the two Nov-2026 rebuilds or arXiv 2605.04004. Your context already cites them, and my searches did not surface them.

## Strategy 1: NOISE + CANDACE + late-day momentum (MNQ)
- Nothing new found on post-2024 decay. No 2026 study measures it. This is neither confirming nor contradicting your two rebuild reports. The only decay hint is a community TradingView port that reports weaker results than the paper (informal): https://it.tradingview.com/scripts/scientific
- The paper (Zarattini, Aziz, Barbon) reports 19.6% net annualized, Sharpe 1.33, max drawdown -25% for 2007-2024, on SPY with assumed frictions. This is a ceiling for NQ and is not a forecast. Your plan of PF 1.2-1.4 is consistent with it: https://www.cxoadvisory.com/?p=45565
- The authors say trends can begin before 15:30. That is mild support for a late-day leg in principle, but it does not fix your chance-level result: https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content
- CANDACE and the ICT liquidity-sweep/inverse-FVG topic: I did not search it, so there is no evidence either way. It stays unproven (PF 1.22).
- Independent NQ Noise Area scripts exist, but none is a validated test: https://fr.tradingview.com/scripts/noise/

## Strategy 2: Order Flow AR (delta estimated from 1-minute bars)
- I found no paper that combines OFI, an autoregressive model and OHLCV-estimated delta. That is consistent with your null result (PF 0.69 held out).
- Published OFI work uses quote or BBO data. Example: structural VAR on ES with 1-second BBO data: https://arxiv.org/html/2508.06788v2
- A VAR plus neural network hybrid also uses real order-book OFI: https://www.arxiv.org/pdf/2411.08382
- Regime-dependent OFI memory and forecast power in CSI 300 futures is another reason a fixed AR model can fail out of sample: https://arxiv.org/abs/2505.17388
- The signal needs true signed volume or book data. Estimating delta from 1-minute bars discards the information those papers use.

## Rule and schedule changes affecting the app
- Lucid (third-party sources only; conflicting and unverified against Lucid's official pages). Nov 2: LucidDaily funded accounts may now use EOD drawdown when the evaluation is also EOD, with a 30% or 40% consistency option: https://www.eltraderfinanciado.com/en/news/lucid-trading/luciddaily-eod-drawdown-funded-account-november-2026
- Lucid (October): optional 40% consistency on LucidFlex and LucidDaily evaluations, plus on-demand payouts. Sources disagree on whether funded accounts have a consistency rule: https://propfirmmatch.com/futures/industry-news/lucid-trading-adds-40-consistency-option-and-on-demand-payouts
- CME early-close dates (verify against CME's advisories):
  - Thu Nov 26: equity halt at 12:00 CT, reopens 17:00 CT.
  - Fri Nov 27: ES/NQ close 12:15 CT (13:15 ET).
  - Thu Dec 24: ES/NQ close 12:15 CT per one source, 12:00 CT per another. This is unresolved.
  - Dec 25: closed. Reopens Sun Dec 27 at 18:00 ET.
  - Sources: https://www.quantvps.com/blog/cme-holiday-schedule and https://www.cmegroup.com/tools-information/holiday-calendar/files/2026/2026-christmas-clearing-advisory.pdf

## Recommendations
1. Hard-code the early-close calendar (Nov 26 halt, Nov 27 and Dec 24 early close). Flatten at least 15-30 minutes before the earliest stated time, which means 11:30 CT on Dec 24. Disable the late-day leg on those days. Re-check the CME advisories once they are final, which is about two weeks before each date.
2. Keep sizing and prop-firm planning on PF 1.2-1.4 for NOISE only. Keep CANDACE and the late-day leg off or at minimum size until they have out-of-sample evidence. Retire Order Flow AR on 1-minute estimated delta unless real tick or bid/ask data is available.
3. Make the Lucid consistency %, drawdown type (EOD vs intraday) and payout rules configurable per account type. Confirm them on Lucid's official site before relying on any of them, because the third-party sources conflict.

## Engine run (lead, 2026-11-24, after the build)
last30days engine ran on 3 topics (saved in /root/Documents/Last30Days, suffix v4). Coverage was thin: YouTube blocked by the bot check (not bypassed), Reddit unreachable/throttled, no X. Only GitHub and Hacker News returned items.
- noise area: three more open-source ports of the Zarattini paper (flandyw/botfolio PR 1 "+108% QQQ 10.9y after costs"; shares_alpaca PR 5; a pre-registered QQQ test and a BTCUSDT 5m derivative). Nothing new on decay.
- ICT sweep / iFVG: only two GitHub spec repos; no tested results. Nothing new for CANDACE.
- order flow imbalance AR: GitHub items on keeping stale prior-bar prints out of order-flow delta and research-only Kite order-flow snapshots (both point to needing real tick data). HN hits were off-topic.
Conclusion: no new evidence changes any decision. The early-close dates above are third-party and must be confirmed against CME advisories.
