# ORB family: MNQ (main) and MGC (secondary). Agent "orb"

**Verdict: FAIL.** The variant chosen in-sample does not pass on held-out data. Two plain ORB variants do pass
the held-out thresholds, but I found them only by looking at held-out results, so they are post-hoc and do not count.
Nothing here beats the benchmark (noise-area momentum: HO 440 trades, 45.0% win, +$25.81/trade, PF 1.33).
MGC ORB loses money at both the 08:20 and the 09:30 open.

Code: `agents/orb/orb.py`. Reproduce:
`cd scratchpad/agents/orb && nice -n 10 /home/user/opogabuuga/.venv/bin/python orb.py mnq` (28 base variants).
The filter and MGC runs pass a JSON variant list as argv[2]; the exact list is the last section below.
Trade lists are in `agents/orb/trades/*.csv`. `agents/orb/best_trades.csv` (d, side, pnl) holds the IS-selected
variant. `posthoc_brk30_eod_trades.csv` holds the post-hoc variant.

## Common mechanics (protocol per BRIEF)
- 1-minute bars in NY time. Opening range (OR) = high/low of the first N minutes after the open (09:30 ET; MGC also 08:20).
- **BRK (classic):** resting buy stop at ORH and sell stop at ORL. A side fills only when price trades through by 1 tick.
  Fill = max(level+1 tick, bar open) + 1 tick slippage. Entries are allowed until 12:00 ET, first trigger only.
  A bar that hits both sides causes the day to be skipped.
  - Stop `opp`: the opposite side of the OR. Stop `half`: the OR midpoint.
  - Target: a limit at k·R, which must trade through by 1 tick and has no slippage. `EOD` means close at the 16:39 bar close (−1 tick); flat by 16:40.
- **ZAR (Zarattini & Aziz 2023, SSRN 4416622):** 5-minute OR. A bullish first candle means long only, a bearish one short only, and a doji means no trade.
  Market entry at the 09:35 open (+1 tick). Stop at the first candle's low/high. Target 10R, otherwise exit at EOD.
  The paper's version is defined on 09:30–09:35 (it trades at 09:35, so this does not break the 09:30–09:35 entry skip).
- Same-bar stop and target: the stop counts first. On the entry bar only the stop is checked. Trades with a stop under 8 ticks (MNQ) or 5 ticks (MGC) are skipped.
- Costs: MNQ $1.00 + 1 tick on entry and on stop/EOD exits; MGC $1.60 + 1 tick. R = entry-to-stop distance, and every R figure is net of costs.
- ATR14 = mean of the prior 14 RTH day ranges. It is set to unknown on roll days (overnight gap > 1.5%), and the trend feature is unknown if a roll falls in the last 21 days.
- Filters (thresholds fixed before running):
  - narrow: OR < 0.2·sqrt(N/5)·ATR14.
  - trend: trade only in the direction of the prior close vs. its 20-day SMA.
  - on: overnight range (18:00–open) ≤ 0.75·ATR14.
  - reverse: after a stop, the opposite side may trigger (max 3 trades a day).
  - atrstop: stop = 0.1·ATR14.
- News blackouts are not modeled. Trades: at most 1 per day (3 with reverse), so the 3-trades/day cap never binds.

**Variants (39, all fixed a priori):**
- MNQ: ZAR × {10R/EOD, 1.5, 2, 2.5R} = 4; BRK × OR {5, 15, 30} × stop {opp, half} × target {1.5, 2, 2.5, EOD} = 24.
- MNQ filters on the IS-best base (BRK30_opp_2.5, highest IS $/trade): narrow, trend, on, reverse, atrstop = 5.
- MGC at 08:20 and 09:30 × {BRK30_opp_2.5, BRK30_opp_EOD, ZAR5_10R} = 6.
- **Selection rule:** highest in-sample $/trade. That picks **B30_2.5+on** (IS $16.90, PF 1.25).

## Main table (IS = 2019-05..2023-12, HO = 2024-01..2026-11; $ per trade = net, 1 micro)
| variant | period | trades | /day | win% | avgW R | avgL R | exp R | $/tr | PF | maxDD R | streak |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **B30_2.5+on (IS-selected)** | IS | 718 | 0.60 | 46.4 | 1.22 | -0.84 | 0.113 | 16.90 | 1.25 | 15.5 | 8 |
| | **HO** | 419 | 0.57 | 44.6 | 1.01 | -0.79 | 0.012 | **-3.58** | **1.03** | 12.7 | 7 |
| BRK30_opp_2.5 (base) | IS | 1151 | 0.96 | 47.1 | 1.12 | -0.86 | 0.073 | 9.46 | 1.16 | 21.7 | 12 |
| | HO | 718 | 0.98 | 46.8 | 1.02 | -0.81 | 0.045 | 9.92 | 1.10 | 26.8 | 10 |
| BRK30_opp_EOD (post-hoc) | IS | 1151 | 0.96 | 46.7 | 1.13 | -0.86 | 0.073 | 9.31 | 1.16 | 20.6 | 12 |
| | HO | 718 | 0.98 | 46.5 | 1.10 | -0.81 | 0.079 | 16.11 | 1.18 | 25.8 | 10 |
| BRK30_opp_1.5 (post-hoc) | IS | 1151 | 0.96 | 48.9 | 1.02 | -0.86 | 0.056 | 7.13 | 1.13 | 21.9 | 12 |
| | HO | 718 | 0.98 | 49.3 | 0.97 | -0.81 | 0.067 | 15.52 | 1.16 | 24.5 | 10 |
| BRK15_opp_2 | IS / HO | 1191 / 735 | 1.0 | 42.1 / 41.8 | 1.43 / 1.43 | -0.94 / -0.91 | .058 / .069 | 5.73 / 11.52 | 1.11 / 1.13 | 18 / 37 | 10 / 9 |
| BRK5_opp_EOD | IS / HO | 1199 / 735 | 1.0 | 28.2 / 30.1 | 2.77 / 2.62 | -1.0 / -.99 | .062 / .095 | 2.79 / 14.02 | 1.09 / 1.14 | 42 / 28 | 20 / 13 |
| ZAR5 10R/EOD (paper) | IS / HO | 1197 / 733 | 1.0 | 23.5 / 25.1 | 3.71 / 3.31 | -1.03 / -1.01 | .086 / .074 | 4.47 / 5.56 | 1.11 / 1.10 | 39 / 40 | 19 / 18 |
| ZAR5 2R | IS / HO | 1197 / 733 | 1.0 | 34.9 / 34.9 | 1.92 / 1.86 | -1.03 / -1.01 | .001 / -.008 | -1.81 / -0.70 | 1.00 / 0.99 | 50 / 40 | 16 / 13 |
| BRK5_half_* (all 4) | HO | 735 | 1.0 | 16–38 | | | -.08..-.01 | -2.9..+1.4 | 0.87–0.99 | | |
| B30_2.5+narrow | IS / HO | 715 / 414 | .6 | 44.2 / 42.3 | | | .069 / .022 | 9.90 / -7.04 | 1.14 / 1.05 | | |
| B30_2.5+trend | IS / HO | 273 / 91 | .2/.1 | 49.5 / 45.1 | | | .054 / .023 | 13.34 / 4.02 | 1.13 / 1.05 | | |
| B30_2.5+reverse | IS / HO | 1417 / 864 | 1.2 | 46.5 / 45.5 | | | .056 / .031 | 7.37 / 6.09 | 1.12 / 1.07 | | |
| B30 atrstop 2.5 | IS / HO | 1039 / 658 | .9 | 26.4 / 24.0 | | | -.138 / -.181 | -3.87 / -10.98 | 0.82 / 0.76 | | |
| MGC@08:20 BRK30_opp_2.5 / EOD / ZAR | HO | ~717 | 1.0 | 37.0 / 34.8 / 12.7 | | | all < 0 | -11.5 / -12.6 / -4.7 | 0.92 / 0.92 / 0.84 | | |
| MGC@09:30 BRK30_opp_2.5 / EOD / ZAR | HO | ~713 | 1.0 | 42.6 / 42.1 / 18.6 | | | all < 0 | -1.0 / -7.4 / -1.9 | 0.97 / 0.90 / 0.92 | | |

All 28 MNQ base rows are printed by the command above.

## Per year
| year | B30_2.5+on: trades / win% / $ / PF | BRK30_opp_EOD (post-hoc): trades / win% / $ / PF |
|---|---|---|
| 2019 | 76 / 47.4 / +721 / 1.46 | 156 / 46.2 / +777 / 1.17 |
| 2020 | 142 / 45.8 / +1654 / 1.16 | 249 / 42.6 / -2884 / 1.01 |
| 2021 | 157 / 45.9 / +1638 / 1.11 | 247 / 49.8 / +2974 / 1.20 |
| 2022 | 164 / 45.7 / +2898 / 1.12 | 248 / 47.2 / +4788 / 1.17 |
| 2023 | 179 / 47.5 / +5224 / 1.47 | 251 / 47.8 / +5062 / 1.26 |
| 2024 | 166 / 41.6 / -457 / 1.02 | 254 / 46.1 / +8515 / 1.44 |
| 2025 | 165 / 48.5 / +1708 / 1.18 | 252 / 47.6 / +4900 / 1.15 |
| 2026 (to Nov) | 88 / 43.2 / -2752 / 0.75 | 212 / 45.8 / -1848 / 0.89 |

## Findings
- **Win rate vs. R:R matches the literature.**
  - EOD/10R versions with tight stops (ZAR5, BRK5_half_EOD) win only 15–25% of the time and depend on rare big winners.
  - Fixed 1.5R targets with the 30-minute OR win 49%. The 30-minute OR is wide, so the target is often not reached by 16:40 and the average win is only about 1.0–1.1R.
- **The published Zarattini ORB replicates only weakly on MNQ** with honest costs and fills: HO PF 1.10, +$5.56/trade.
  The paper's headline numbers used QQQ/TQQQ with leverage sizing and few costs.
- The R:R 1.5–2.5 window subset (BRK*_1.5/2/2.5 and ZAR_1.5/2/2.5) has a best HO PF of 1.16 (BRK30_opp_1.5). It is post-hoc and, because of EOD exits, its realised average win is under 1.5R.
  None of these rows is IS-selected and PF ≥ 1.15. An app config with rr_min 1.5 would still exit at 16:40, so the realised R:R is below the nominal value.
- **2026 is negative for every 30-minute ORB row**, so performance is decaying. The overnight-range filter (the IS winner) overfit.

## Risks and plug-in
- Strong alpha decay in 2026 and one trade a day with all-or-nothing days.
- A 30-minute MNQ OR is often 60–150 points, so the stop is $120–300 per micro. That is a large part of the $1,000 EOD drawdown.
- Plug-in path: a pure engine signal (no TradingView needed) at 10:00 ET, with stop-entry brackets at ORH/ORL, stop on the opposite side, target 1.5–2.5R, and flat at 16:40.
  - It conflicts with the confluence pillars (no C1/C2 sweep, no MSO) and with D49's UT Bot/EMA200 trend agreement. It would need to be a separate profile.
  - **Recommendation: do not adopt.** Benchmark noise-area momentum remains better.

## Exact variant list used for filters and MGC (argv[2])
`B='"kind":"brk","or":30,"stop":"opp","tgt":2.5'`; `orb.py mnq` with filt ∈ narrow/trend/on, reverse:1, atrstop:1 on B.
`orb.py mgc` with B, {brk,30,opp,tgt:null} and {zar,or:5,tgt:10}. MGC opens are 08:20 and 09:30.
