# External MNQ/NQ and MGC/GC intraday strategies: web research (ALL UNVERIFIED)

Date: 2026-11-10. Web research only, no code run, no numbers reproduced by us. Every figure below is as claimed by the source
(taken from search snippets and one page fetch; I did not read most papers in full). Baseline to beat: NOISE on MNQ, held-out 2024-26,
win 45-52%, PF 1.31-1.38.

Key finding: almost nothing publicly claimed clearly beats our baseline with credible evidence. Claims that do (PF > 2, win > 60%) are
small-sample marketing. Credible independent results cluster at win 35-55% and PF 1.2-1.5 after costs, i.e. about where we already are.

## Table

| # | Name | Market / TF | Core rules | Claimed results | Source | Evidence | Red flags | Testable with our data? |
|---|------|-------------|-----------|-----------------|--------|----------|-----------|-------------------------|
| 1 | Zarattini/Barbon/Aziz "Beat the Market" intraday momentum (noise area) | SPY (not NQ), 1-30 min | Noise-area bands = open +/- avg 14-day move; trade breakouts, exit at close/trailing | Paper reports strong SPY results (Sharpe/return not verified by me); SFI Research Paper 24-97 | https://ideas.repec.org/p/chf/rpseri/rp2497.html | Working paper (SFI), backtest | Same family as our baseline; SPY ETF not NQ; independent replication (row 2) disputes net edge | Already our baseline |
| 2 | Independent replication of Zarattini 5-min ORB on 5 index CFDs | NQ, SPX, Dow, DAX, FTSE; 5 min; 2015-2026 | Paper's first-5-min-candle bracket rule, unchanged | Gross NQ +0.131R, 23.2% hit (matches paper); NET after costs NQ +0.002R, others negative; 2021-26 best net +0.06R (NQ) | https://www.mql5.com/en/blogs/post/776235 | Blog, independent, transparent | CFD spread costs assumed 6-12% of risk; futures with commission-only costs NOT tested | Yes (MNQ 1-min, 5-min ORB). Useful as a cost sanity check and random-direction benchmark method |
| 3 | Zarattini/Aziz/Barbon ORB "Stocks in Play" | US single stocks, 5 min | 5-min opening range break on high relative-volume names, stop 10% ATR, exit at close | >1,600% net 2016-2023, Sharpe 2.81, alpha 36% (top-20 stocks) | https://ideas.repec.org/p/chf/rpseri/rp2498.html | Working paper, backtest | Stocks, not futures; no NQ analogue; small-cap/liquidity/short-borrow assumptions; replications on indices fail net | No (needs single-stock data). Only conceptual: relative-volume filter on MNQ opening |
| 4 | Gao/Han/Li/Zhou "Market Intraday Momentum" | SPY + 10 ETFs; first vs last 30 min | Long last half-hour if first half-hour (incl. overnight) positive, short if negative | ~6.3% annualized gross vs -0.5% hold (1993-2013); effect in 12/16 developed markets in later study | https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414 | Peer-reviewed (JFE 2018) | Tiny OOS R2 (~1.8%); gross of costs; data-mining critique; pre-2013 sample | Yes, trivially (MNQ/MES, 2019-26). One trade/day at ~15:30 ET. Cheap to test; likely small edge |
| 5 | Concretum VWAP Trend Trading | QQQ (and SPY), intraday | Long above VWAP / short below with trailing VWAP stop | QQQ 2018-2023 beat buy-and-hold Sharpe 0.7; strategy Sharpe not retrieved | https://quantifiedstrategies.substack.com/p/systematic-intraday-trend-following | Backtest, author-published | Sharpe not verified; ETF not futures; costs unclear | Yes (VWAP trend on MNQ; note we already have a vwap trend switch, D44) |
| 6 | ORB 15m NQ, second-breakout entry (prop-trading blog) | NQ, 15 min, 6 months | Opening range 15 min, take second breakout | 57% win, avg win 1.8R, avg loss 1R, ~0.43R expectancy | https://www.proptradingvibes.com/blog/opening-range-breakout-strategy | Marketing/blog, 6 months | Tiny sample, author calls it unspectacular, no costs stated | Yes (MNQ 1-min). Cheap; sample too small to trust |
| 7 | NQ ORB 15m, 2020-2022 Substack backtest | NQ, 15 min | Standard 15-min ORB | 451 trades, win 30.4%, PF 1.43; optimizing for win rate >40% lowered Sharpe | https://backtestsnotsignals.substack.com/p/opening-range-breakout-real-edge | Blog backtest, 451 trades | Period short and pre-2023; costs unknown; the TV-vs-Python gap (row 8) shows implementation sensitivity | Yes |
| 8 | NQ 15m ORB TradingView vs Python comparison | NQ, 2023-25 | 15-min ORB | TV: win 46.8%, PF 1.37; Python: win 35.6%, PF 1.30 | https://orb-performance-comparison.pages.dev/ | Blog, self-run | Shows backtest engine variance of ~10 pts win rate; assumptions unknown | Yes. Same band as our baseline; no improvement |
| 9 | FXC NQ ORB V2.4 / "up 400%" ORB claims | NQ, various | ORB variants, some with dynamic risk/regime filter (e.g. Project Kintoun) | Marketing: 64% win, PF 2.26 on 95 trades; 77%/PF 6.4 on a tiny sample (Reddit) | https://de.tradingview.com/script/hD3G5Fcv-FXC-NQ-Opening-Range-Breakout-Strategy-V2-4 ; https://mrjerm.github.io/project_kintoun.html | Marketing / invite-only (closed code) | Invite-only so unreviewable; 95 trades; PF > 2 on small N = classic curve fit | Partly (Kintoun regime-filtered ORB is open on GitHub Pages, testable); invite-only no |
| 10 | GC 15m long-only day-session (paid newsletter) | GC futures, 15 min, since 2002 | Long-only day-session rules (not disclosed in snippet) | 877 trades, +$129k, PF 1.80, win 43.9% | https://algotr.substack.com/p/from-the-lab-a-simple-robust-gold | Paid newsletter, hypothetical | Long-only on a 2002-2026 gold bull market = beta; rules hidden; costs unclear | Partly (MGC.v.0 2019-26 only; gold trended up, so a long bias will look good) |
| 11 | London-session gold breakout (MQL5 vendors) | XAUUSD spot CFD, M15/H1 | Asian range breakout at London open | PF 1.33-1.38, ~49% win, DD 17-19%, 715 trades 2023-25; 2026 OOS PF 1.61 on 157 trades | https://www.mql5.com/en/blogs/post/777540 | Vendor/EA marketing, one broker feed | Fit on 2023-25; spot CFD not GC; EA sale incentive; same author class showed FX London breakout PF 0.99 | Yes (MGC 1-min, 02:00-08:00 ET range). Note: we already tested ORB on MGC and failed; spot CFD spreads differ |
| 12 | Generic gold breakout counterpoint (fractiz Donchian 1h on GC 2020-24) | GC, 1h | Donchian breakout | PF 0.97, -$21.5k, DD 58% | https://anupshindedotcom.pages.dev/breakout-continuation-backtested/ | Blog, backtest | Single rule family | Consistent with our MGC failures; supports "gold breakout has no edge" |
| 13 | ICT Silver Bullet / opening-range fakeout NQ | NQ, 1-5 min | FVG entry in 10-11 or 14-15 ET windows | 56% win over ~1 year (YouTube) | https://ar.tradingview.com/script/SuBXi3p8-ICT-Silver-Bullet-Backtest/ | Influencer/hobbyist, no audit | 1-year windows, discretionary rules, hindsight FVG labeling, no costs | Only if rules are made mechanical; we already have structure/FVG machinery (all failed on MGC) |

Not found: any audited track record, SSRN paper, or peer-reviewed study of a profitable NQ/MNQ or MGC/GC intraday rule set after realistic
futures costs. No credible "Dynamic Momentum on gold futures" paper surfaced; treat any such claim as unlocated.

## Top 3 worth testing on held-out data

1. Gao et al. last-half-hour momentum (row 4) on MNQ/MES. Only peer-reviewed item, one cheap trade per day, structurally different from NOISE
   (late-day, direction from first 30 min + overnight), so possibly diversifying. Expect small gross edge; check net of costs and 2019-26 stability.
   Pick rule on 2019-23, judge 2024-26, per our WIN-RATE RULE.
2. Cost/random-direction benchmark from the replication (row 2) applied to OUR baseline. Not a new strategy but the most valuable test:
   run NOISE vs random-direction brackets with the same stops/exits on MNQ at real futures costs. Tells us how much of PF 1.31-1.38 is
   directional information. Also run the plain 5-min and 15-min ORB on MNQ with commission-only costs (the case the replication did not test).
3. VWAP trend / Kintoun regime-filtered ORB (rows 5, 9) as a filter on top of NOISE, not a standalone: we already have vwap/ema/utbot trend
   switches (D44), so test only whether the regime filter improves held-out win rate without cutting trades below target.
   (Gold: nothing earns a slot. Cheapest honest MGC test would be London/Asian-range breakout, row 11, but it parallels the ORB/trend failures we already have.)

## Plain-language summary

The strongest public work (Zarattini et al.) is the family our baseline is already built from, and an independent replication found its
edge on NQ is about 0.13R gross and roughly zero after realistic costs; our held-out PF of 1.31-1.38 is therefore already at or above the
credible public range. Everything claiming more (win 56-77%, PF 2+) is a short or tiny sample, invite-only code, or a vendor selling something,
with no costs or hindsight-prone discretionary rules. For gold, the evidence is a few vendor backtests of spot XAUUSD at PF ~1.3-1.4 and one
long-only GC newsletter claim that mostly rides gold's bull market, while a plain GC breakout test shows PF 0.97, consistent with our own failures.
Recommendation: do not expect a big upgrade from public sources; test the late-day momentum rule and the random-direction/cost benchmark,
and consider dropping MGC research unless a different idea appears. All numbers above are UNVERIFIED claims.
