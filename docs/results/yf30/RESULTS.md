# yf30: 30 days of Yahoo (yfinance / OpenBB) data, late-day momentum + NOISE / CANDACE on MGC (2026-11-23)

**30 days (23 complete sessions, 2026-10-20 to 2026-11-20) is far too small to prove any edge.** Every number below is a
guess about a sample of ~20 days. Nothing here was held out; the MGC settings were picked on the same 30 days they are
reported on.

## Data
- OpenBB is not installed; its yfinance provider is yfinance itself, so `yfinance 1.8.0` was installed in a scratch venv (not the app `.venv`).
  Yahoo gave HTTP 429 on a bare curl; yfinance's own session worked (crumb 429 notice, then data).
- `MGC=F`, `MNQ=F`, `MES=F` (no fallback to GC/NQ needed), **2-minute bars, 24 hours incl. overnight** (1-minute only goes back 7 days). Raw CSVs: `data/*_2m.csv`.
- **Caveat:** these are Yahoo continuous front-month contracts, NOT Databento `MGC.v.0` (volume roll). Roll jumps are possible; the project rule (MGC.c.0 / splices break backtests) applies. Gold fell about 12 % (4165 to 3671) in the window, so the sample is one strong trend.
- The still-forming 2026-11-23 session is dropped. Costs per micro round trip: fee_rt + 2 x 1 tick slippage (MNQ $2.00, MES $3.50, MGC $3.60). No lookahead (entries at the next bar open or the signal bar close, as the engines do).
- "vs random": same entry bar, same exit bar, same stop / target distances, coin-flip direction, 1,000 to 2,000 draws; **p = share of random draws with net $ >= the actual** (small p = better than chance; with ~20 trades nothing below ~0.05 means much).

Scripts: `scripts/pull.py`, `scripts/lib.py`, `scripts/late_day.py`, `scripts/noise_candace.py`; outputs `late_day_results.json`, `noise_candace_results.json`, `noise_candace_log.txt`.
Run: `PYTHONPATH=backend:docs/results/yf30/scripts <yfvenv>/bin/python docs/results/yf30/scripts/<script>.py`.

## (a) Late-day momentum (new_edge rules: sign of 09:30-13:30 trend, enter 15:00, flat 16:00) + overnight predictors
Stops scaled to price (MNQ 60 pt, MES 16 pt, MGC 8 pt). 22 to 24 trades per row. Overnight = prior 16:00 close to 09:30 open (the data new_edge lacked).

| market | variant | n | win % | PF | net $/micro | p vs random |
|---|---|---|---|---|---|---|
| MNQ | A trend 09:30-13:30 (min move filter) | 22 | 36.4 | 1.46 | +696 | 0.18 |
| MNQ | C overnight sign | 22 | 40.9 | 1.73 | +975 | 0.10 |
| MNQ | D trend and overnight agree | 14 | 42.9 | 2.13 | +933 | 0.12 |
| MNQ | first-30-min -> last 30 min | 23 | 30.4 | 0.44 | -1,031 | 0.92 |
| MNQ | overnight + first-30 -> last 30 min | 22 | 36.4 | 1.14 | +169 | 0.38 |
| MES | A trend | 21 | 42.9 | 1.27 | +182 | 0.43 |
| MES | overnight + first-30 -> last 30 min | 22 | 22.7 | 0.34 | -603 | 0.96 |
| MGC | A trend | 23 | 43.5 | 0.84 | -110 | 0.47 |
| MGC | C overnight sign | 23 | 47.8 | 0.79 | -132 | 0.49 |
| MGC | overnight + first-30 -> last 30 min | 23 | 43.5 | 0.50 | -365 | 0.81 |

Correlation of the last-30-min return with first-30-min / overnight / their sum: MNQ -0.01 / 0.05 / 0.03, MES -0.23 / -0.18 / -0.28, MGC 0.21 / -0.08 / -0.03 (n 22 to 23; none significant).
Verdict: MNQ late-day momentum is positive again (PF 1.46) but p = 0.18, consistent with the earlier 5-year PF 1.12 decaying edge; MES and MGC do not confirm it; the overnight + first-30-min predictor does not work here (wrong sign on MES, nothing on MNQ/MGC). Not built.

## (b) NOISE (engine/noise.py) and CANDACE (engine/candace_ict.py), 1 micro, reused unchanged
Adapter notes: both engines were fed **2-minute** bars (NOISE hourly checks 10:00, 11:00, ... exist on the 2-minute grid; k = 0 session close is filled with the first bar only for `Session.complete`). CANDACE's bar-count settings (swing 2, displacement 10, FVG lookback 10, ...) therefore cover twice the time of the live 1-minute feed. NOISE warm-up needs 10 earlier sessions (live default), so only the last ~12 sessions can trade; min-history 5 is also shown.

| market | strategy (setting) | n | win % | PF | net $/micro | shorts | p vs random |
|---|---|---|---|---|---|---|---|
| **MGC** | NOISE $250 stop, no lock, no Monday skip, min hist 10 (**chosen**) | 2 | 100 | inf | +423 | 2 | 0.26 |
| MGC | NOISE same, min hist 5 | 4 | 75 | 9.9 | +453 | 3 | 0.06 |
| MGC | NOISE $100 stop, min hist 10 | 3 | 66.7 | 5.3 | +432 | 3 | 0.25 |
| MGC | NOISE with scaled profit lock (13.5 pt / 1.3 pt), $100 stop | 3 | 66.7 | 3.1 | +208 | 3 | 0.24 |
| **MGC** | CANDACE window 08:20-11:00, stop cap 6 pt, hold 30 min (**chosen**) | 25 | 48.0 | 1.97 | +458 | 8 | 0.063 |
| MGC | CANDACE same, hold 15 min | 25 | 48.0 | 1.76 | +359 | 8 | 0.075 |
| MGC | CANDACE window 09:00-10:00, cap 6 | 8 | 37.5 | 1.59 | +118 | 2 | 0.35 |
| MGC | CANDACE cap 15 pt, 08:20-11:00, hold 30 | 38 | 42.1 | 0.94 | -83 | 18 | 0.36 |
| MNQ | NOISE $250, lock 100/10, Mondays off, min hist 10 | 10 | 50.0 | 2.19 | +972 | 8 | 0.32 |
| MNQ | NOISE $250, no lock, Mondays on, min hist 10 | 14 | 35.7 | 2.15 | +2,075 | 9 | 0.20 |
| MNQ | CANDACE cap 40 pt, 08:20-11:00, hold 30 | 14 | 42.9 | 2.04 | +370 | 5 | 0.16 |
| MNQ | CANDACE cap 40 pt, 09:00-10:00 (live defaults) | 10 | 30.0 | 1.42 | +94 | 3 | 0.39 |

Read plainly: MGC CANDACE is the only row with a meaningful trade count (25) and is positive, but a random direction matches it 6 % of the time at best, it was the best of 8 settings tried on the same data, and widening the stop cap to 15 pt turns it negative (PF 0.94): that is fragility, not an edge. MGC NOISE traded **2 times** (both shorts into the gold sell-off); that is not a result. MNQ looks better than MGC on both engines, still with 10 to 14 trades. Combined MGC at the chosen settings: 27 trades, about +$881 per micro over 23 sessions.

## What was built (D165)
Strategy page button **NOISE + CANDACE · MGC** (`strategy.mgc_noise_candace`, default OFF, gold badge "UNVERIFIED · 30-day yfinance test only", result in the card note). Same engines and plumbing (`run_noise` / `run_candace_ict` with an MGC cfg, plan modes `MGC_NOISE` / `MGC_CANDACE`), numbers in each Pro plan yaml (`mgc_noise_candace_cfg`): NOISE $250 stop (the MNQ-verified value), profit lock and Monday skip off; CANDACE window 08:20-11:00 ET, stop cap 6 pt, hold 30 min, gap tolerance 0.7 pt. Fixed 1 micro; MGC (METALS) is outside the equity hedge lock; rule 7 (one position per account) and every Lucid check still apply and only shrink or skip. MGC bars come from the existing live feed (TradingView heartbeats); NOISE needs 10 stored MGC sessions before it trades. No AI advisor / bias block on it. Treat as paper-only research until far more data confirms it.
