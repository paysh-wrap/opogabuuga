# Paytience: brief on the two main strategies, with final comparison (2026-11-22)

Sources: this repo's own studies (all backtests on cached MNQ/MES 1-minute regular-hours data 2021-10..2026-10 unless noted; nothing here is a promise). Lucid rules are modelled as on your plan cards (EOD trailing drawdown, daily loss limit, 40 % consistency with a 38 % day stop, one position per account, flat by close, never hedge).

## 1. MAIN STRATEGY: NOISE (noise-area momentum), with the fast-pass setups

**What it is.** Noise-area intraday momentum on MNQ (Zarattini/Aziz/Barbon style). The band is the mean absolute move from the open over the previous 14 sessions. It decides on hourly checks 10:00-15:00 ET, enters when price is outside the band, and exits on the band/VWAP. Flat by 16:00. $250 emergency stop per micro, profit lock (+100 pt moves the stop to entry +10), Mondays skipped, at most 3 entries a day.

**Evidence (strong, the only proven edge).**
- 7.5 years (2019-05..2026-11, Databento): 935 trades, 50.1 % win, PF 1.49, +$24.86 per trade per micro, about 2.4 trades a week.
- Last 12 months (held out): 59.5 % win, PF 1.72.
- Beats a random-direction version (random PF about 1.0).
- About 40 tweaks tested in sessions 19-20; only the profit lock and "skip Mondays" survived held-out testing.

**Evaluation odds today (realistic Lucid simulation, rolling starts, 5 years; pass / stuck):**

| Plan | Pass / stuck | Median days to pass |
|---|---|---|
| 25K | 59 / 36 | 74 |
| 50K | 69 / 21 | 92 |
| 100K | 78 / 11 | 152 |
| 150K | 77 / 11 | 159 |

Non-passes are accounts stuck too close to the drawdown floor; none breach outright in this simulation. Published real-world pass rates at other firms are far lower (Topstep 16.8 %, Tradeify 17.2 %), so treat these as upper bounds.

**Fast-pass setups (D156/D157, off by default, evaluation accounts of that exact size only; every Lucid check still shrinks or skips):**

| Plan | Setup | Median days (today to new) | Pass % (today to new) |
|---|---|---|---|
| 150K | NOISE 5 micros @ $100 stop + CANDACE 4; both to 2 micros at cushion <= $1,500 | 159 to 86 | 77 to 74 |
| 100K | NOISE 2 @ $250 (to 1 below $1,000 room) + CANDACE 3 (to 2) | 152 to 127 | 78 to 78 |
| 25K | NOISE 1 @ $75 + CANDACE 2 (CANDACE to 1 below $333) | 74 to 56 | 59 to 62 |
| 50K | no setup beat today's; keep as is | 92 | 69 |

150K also gets 20 % of evaluations passed within 60 days (vs 6 %), and profit rises from $57.9k to $98.7k (5 years, static replay). The 25K/150K search for even better setups (more micros, daily-loss-limit off) was still running at the time of writing.

**Partner strategy.** CANDACE ICT (liquidity sweep, inverted FVG, retrace entry, 09:30-10:00 window). It keeps every sweep alive (D154): 310 trades vs 100 over 5 years, +$1,844 at 1 micro. It lost money in 2021-23 and made money in 2024-26, so it is a small, regime-dependent edge used as the second leg.

**Risks and caveats.**
- Backtests, not promises. News blackouts and intra-trade drawdown touches are only partly modelled.
- Bigger size or tighter stops pass faster but fail more often (the clear trade-off in every study).
- Lucid's Pro evaluation consistency rule is confirmed 40 % by you; third parties claim none, which is unverified.

## 2. SECOND MAIN OPTION: ORDER FLOW, AR Model (D101), with TradingAgents bias

**What it is.** The AR Model order-flow strategy: environment, location, path, confirmation, with the stop beyond the absorption zone. Delta and the footprint are ESTIMATED from 1-minute bars (real tick data needs Databento, whose account is locked). TradingAgents would run a bias at 4 h, 1 h and 30 min before each session (advisory unless its ledger proves at least 70 %).

**Evidence (weak, no edge shown).**
- Session 22 (5 years of MNQ/MES): the shipped config makes 0 trades (no overnight data, location gate fires about once per 150 sessions). With the path filter off, the best usable setup earned PF 1.02 in-sample, then PF 0.69 over 62 held-out trades (-$414), beat only 1 of 30 random-direction runs, and MES lost money.
- Session 19 (7.5 years): every MNQ variant PF 0.86-1.12 in-sample; random sides at the same moments scored the same.
- Evaluation odds (Pro 25K, last 12 months): Order Flow 0 % pass / 38 % bust, against NOISE 55 / 45.
- Not tested on real order-flow data. Pine footprint calls were never compiled in TradingView.
- TradingAgents: needs your AI key; real accuracy unknown (the bias ledger is empty); at realistic 50-56 % accuracy it adds about 0-1 points of win rate and halves trades.

**Verdict.** Not proven. Keep OFF by default, paper-first, labelled UNVERIFIED. It can run on separate accounts beside NOISE (one free account per trade), but it cannot share one account's single position slot (non-negotiable 7).

## 3. Final comparison

| | NOISE (+ CANDACE fast-pass) | Order Flow AR Model |
|---|---|---|
| Proven edge | Yes: 7.5 yr, PF 1.49, held out PF 1.72 | No: PF 0.69 held out, random-like |
| Trades | about 2.4 a week (NOISE) | about 0 at shipped settings |
| Evaluation odds | 59-78 % pass by plan (simulation) | 0 % pass on Pro 25K (last 12 months) |
| Data quality | Real 1-minute bars, 7.5 years | Estimated delta only, no tick data |
| Lucid fit | Sized by Lucid fit; all checks apply | Same checks; needs separate account |
| Status | Main strategy; fast-pass switches queued | Second option; research/paper only |
| Next step to improve | Finish 25K/150K search, build switches | Real tick data (unlock Databento), compile Pine, run on paper |

**Bottom line.** NOISE with the fast-pass setups is the strategy that can pass evaluations and earn. Order Flow stays a labelled, off-by-default second option until it shows an edge on real order-flow data.

## 4. What is still open before the final build
1. Lucid confirmation of the Pro evaluation consistency rule and the daily-loss-limit removal fee (you supplied the plan cards; fee not shown).
2. The 25K/150K search results (more micros, DLL on/off) and the ten-account 5-year study.
3. Your AI key in Connections for the TradingAgents bias runs.
4. Moltbook agent claim (optional); the help-post draft is in docs/results/moltbook/.
