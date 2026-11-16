# CONTI ORB + CONTI VWAP — rule sheet (from ONE transcript only)

Source: Chart Fanatics episode with Matteo Conti (ex-bank institutional trader), pasted by the user on 2026-11-16.
Times are the transcript's `h:mm:ss`. Nothing here is copied from any existing Paytience strategy; only app plumbing is shared.

He presents a process (idea → rules → backtest → validation → live) and four example ideas. Two are intraday futures
strategies and are built here: **CONTI ORB** (opening range breakout) and **CONTI VWAP**. The other two cannot follow
Paytience / Lucid rules and are left out (see the end).

Rules marked **[GAP]** are not given as a number in the transcript. They are config settings with a documented default,
shown on the card as "not from the video", and must never be tuned to make a backtest look better.

## A. The three boxes every strategy needs (applies to both)
| # | Rule | Time |
|---|------|------|
| A1 | Every strategy has exactly three parts: an ENTRY (why open), an EXIT (take profit and stop loss, plus a time exit if neither hits) and POSITION SIZING | 29:35–30:55 |
| A2 | A time exit closes the position at a fixed time (e.g. 15:30 ET) when neither the take profit nor the stop was hit | 30:31–30:48, 40:14–40:21 |
| A3 | Keep rules simple and fully specific so a machine can run them; complexity means fragility | 4:39–4:54, 1:21:07–1:21:21 |
| A4 | Position sizing = volatility targeting: always put the SAME dollar amount at risk per trade (he uses $10,000 as the example); on a wide-range / high-volatility day use FEWER contracts, on a narrow-range day MORE contracts. Develop with 1 contract; do not trade live with a flat 1 contract | 40:39–42:46, 58:52–59:33 |
| A5 | Validate: split the data 80% in-sample / 20% out-of-sample; fit rules only in-sample; the frozen rules must also work out-of-sample (no overfitting) | 9:11–11:47 |
| A6 | Validate: Monte Carlo on the trades — reshuffle the order, and resample (trades may repeat or be left out) thousands of times; a tight spread of outcomes = a real edge; read the chance of a drawdown larger than a given size | 12:11–18:39 |
| A7 | Automate: the machine watches the data and opens / closes on the rules; the trader monitors performance and risk | 18:53–20:17 |

## B. CONTI ORB — opening range breakout (33:47–50:05)
Why it works (his reasoning): news, earnings and global positioning pile up overnight; many players can only trade after
09:30 ET; their orders collide in the first 30 minutes and reveal a buyer/seller imbalance that carries through the day
(35:21–37:11, 46:17–47:12). The first 30 minutes (09:30–10:00) are the optimal range (48:25).

| # | Rule | Time |
|---|------|------|
| B1 | Range = the HIGH and LOW of 09:30–10:00 ET | 38:44–38:57, 48:25 |
| B2 | ENTRY: go LONG when price CLOSES above the high of the range | 38:44–38:57 |
| B3 | LONG ONLY. A short version (break of the low) exists but works worse, because buyers step in and remove the imbalance; the long-only version also held up in 2022 when the market was falling | 43:10–43:55, 48:40–49:04 |
| B4 | STOP: the low of the range | 39:05–39:14 |
| B5 | TAKE PROFIT: a classic reward-to-risk of 1 : 1 or 1 : 2 (keep it simple) | 39:27–39:56, 49:09–49:19 |
| B6 | TIME EXIT: close at 15:30 ET if neither the stop nor the target was hit | 40:14–40:21 |
| B7 | SIZING: volatility-targeted — same dollar risk per trade, so a wide range (far stop) means fewer contracts | 40:39–42:46 |

Gaps for B: **[GAP]** bar size used for "closes above" (default: the 1-minute bar close); **[GAP]** trades per day (default
1: the first breakout); **[GAP]** last entry time (default 15:00 ET); **[GAP]** which reward-to-risk (the transcript says "either between one or
two"): the config offers `rr` of 1 or 2, default 1 (his own worked example is 1 : 1).

## C. CONTI VWAP — price vs the volume-weighted average price (50:13–59:46)
Why it works: most institutional traders send VWAP execution algos that buy more when volume is high; this amplifies moves
when price crosses VWAP (54:43–55:48). The industry paper tested QQQ on 1-minute bars.

| # | Rule | Time |
|---|------|------|
| C1 | VWAP = the average price of everything traded up to now, weighted by volume, anchored at the OPEN (09:30 ET). He "strongly suggests" the open; using the previous day's VWAP is an optional variation | 51:11–51:40, 57:33–58:03 |
| C2 | 1-minute bars | 53:07–53:25, 56:02 |
| C3 | ENTRY LONG: a 1-minute bar CLOSES above VWAP | 53:15–53:25, 57:04–57:18 |
| C4 | ENTRY SHORT: a 1-minute bar CLOSES below VWAP | 53:40–53:48, 57:04–57:18 |
| C5 | EXIT: the position is closed when price crosses back through VWAP (a long exits when a 1-minute bar closes back below VWAP; a short when it closes back above) — this is the one exit condition | 52:26–52:43, 53:25–53:31, 57:18–57:33 |
| C6 | Instrument: NASDAQ 100 futures (NQ; the app uses MNQ). The same logic is meant to work on any instrument that institutions trade with VWAP algos | 56:17–56:58 |
| C7 | The number of minutes or hours tracked from the open is a parameter to find in the backtest | 58:19–58:36 |
| C8 | SIZING: 1 contract in development; volatility-targeted later | 58:52–59:33 |

Gaps for C (needed to fit Lucid, not in the video): **[GAP] protective stop** — the video has no stop. Lucid / Paytience
require a hard broker stop on every trade, so a config `emergency_stop_pts` is added (default 25 pt); **[GAP] time window**
(default 09:30–15:30 ET, flat at 15:30 like B6); **[GAP] re-entries** (default: after an exit, the next close on the
other side is a new signal; a reversal waits until the old position is confirmed flat, D139).

## Left out on purpose
- **Overnight anomaly** (buy at the 16:00 close, sell at 09:30; 1:21:39–1:28:50): holds a position overnight. Paytience is
  intraday-only and Lucid positions must be flat at 16:44 ET. Not built.
- **Post-earnings announcement drift** (1:00:21–1:21:30): single stocks, earnings data, a 60-day hold. Not futures. Not built.
- The research process (SSRN, LLMs, MultiCharts, 25–400 strategies at once) — not trading rules.

## Lucid / Paytience safety that still applies (never weakened)
News blackout and flat rules, DLL, MLL kill switch, consistency, max 1 open position per account, never hedge (D139), feed
checks, live gates, EOD drawdown on Pro 25K–150K. A signal that hits one of these is skipped with its reason code.

## Implementation notes — CONTI ORB (D146, 2026-11-16)
Engine `backend/app/engine/conti_orb.py` (pure) — `replay_day(today: list[MBar], cfg, tick) -> OrbDay` (this session's
1-minute bars up to now). Hook `strategy_service.run_conti_orb`; key `MNQ-CORB-<day>-<HHMM>`; plan mode `CONTI_ORB`;
`strategy.conti_orb` (default OFF) + `strategy.conti_orb_cfg`. Built: B1–B7 (B5 rr 1 or 2, validator; B6 `CORB_TIME_EXIT`
at 15:30). [GAP] defaults (`# not from the video`): 1-minute close, 1 trade a day, last entry 15:00. A5/A6 are
validation steps for the backtest agent, not runtime rules. Sizing (B7 / A4) = Lucid fit, divisor 1 (one trade a day):
risk = min(25% MLL, DLL left × 0.9, MLL room − kill distance, max_trade_risk_usd, consistency day stop); skip
`CORB_SIZE_BELOW_1`.

| Plan | $/trade (EVAL = FUNDED) | micros @30 pt / 60 pt range |
|------|------|------|
| Pro 25K | 250.00 | 4 / 2 |
| Pro 50K | 500.00 | 8 / 4 |
| Pro 100K | 750.00 | 12 / 6 |
| Pro 150K | 1125.00 | 18 / 9 |

## Implementation notes — CONTI VWAP (D147, 2026-11-16)
Engine `backend/app/engine/conti_vwap.py` (pure) — `replay_day(today: list[MBar], cfg, tick) -> list[VwapSignal]`
(entries + exits so far; `vwap_series(bars)` for the line). Hook `strategy_service.run_conti_vwap`; key
`MNQ-CVWAP-<day>-<HHMM>`; plan mode `CONTI_VWAP`; `strategy.conti_vwap` (default OFF) + `strategy.conti_vwap_cfg`.
Built: C1 (09:30 anchor; the previous-day VWAP variation is not built), C2–C5 (exit `CVWAP_CROSS`), C6 (MNQ).
C7 is a backtest parameter (not a runtime rule); C8 = Lucid fit. [GAP] defaults (`# not from the video`):
emergency_stop_pts 25, far safety target 200 pt (the VWAP cross does the exiting), window to 15:30 (`CVWAP_TIME`),
re-entry only on the other side after an exit, max_losses_per_day 3 (also the sizing divisor). A reversal on the exit
bar is stored as its own signal; the controller skips it while the old position is open (D139, unchanged).
**Left out on purpose:** overnight anomaly and post-earnings drift are NOT built (they break Lucid / Paytience rules).

| Plan | EVAL $/trade | micros @25 pt | FUNDED $/trade | micros @25 pt |
|------|------|------|------|------|
| Pro 25K | 158.33 | 3 | 180.00 | 3 |
| Pro 50K | 360.00 | 6 | 360.00 | 6 |
| Pro 100K | 540.00 | 10 | 540.00 | 10 |
| Pro 150K | 810.00 | 15 | 810.00 | 15 |
