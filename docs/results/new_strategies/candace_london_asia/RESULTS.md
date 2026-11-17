# London / Asia / overnight simulation, last 30 days (MNQ, 1-minute) — 2026-11-17

**30 days (21 weekdays) prove nothing.** 1 to 98 trades per row, one regime; read these as "does the code run on overnight bars", not as evidence.
Engines unchanged, default configs, nothing tuned. Script: `run_london_asia.py` (run from `backend/`). Every trade: `trades_all.csv`. Bars: `bars_mnq_1m.csv`. Day coverage: `coverage.csv`.

## Data
- Source: **OpenBB yfinance provider (keyless; no key used, no Databento)**. `openbb` pip-installs here. BUT OpenBB's yfinance 1m path is hard-coded to `period=5d` (only about 5 days) and its 2m+ path gives 58 days. For 30 days of real **1-minute** bars the script therefore calls `yfinance`, the same keyless library OpenBB wraps, in 7-day requests (Yahoo caps 1m at 8 days per request and about 30 days of history). I checked OpenBB's 1m output against yfinance for 09:29-09:31 on 2026-11-12: identical OHLCV.
- Symbol `MNQ=F` (Yahoo continuous front contract; **not volume-rolled**, a roll inside the window is possible). Interval: **1 minute, real bars only, nothing interpolated or filled**.
- Span: 2026-10-19 00:00 to 2026-11-16 22:52 ET, 28,586 bars, no duplicates, strictly increasing. Overnight session included (Globex 18:00-17:00).
- Timestamps: Yahoo gives bar OPEN times; OpenBB returns them as naive ET wall clock, yfinance as tz-aware ET. The script converts to ET-aware, close_time = open + 1 min (what the engines expect). DST ended 2026-11-01 (a Sunday, no bars in the ambiguous hour), no effect.
- Gaps (all real, left as is): Mon-Fri days have 1,004-1,020 bars for 00:00-17:00 (full day = 1,020); minor missing minutes on 10-20, 10-23, 10-30, 11-04. London 02:00-05:00 is complete (180 bars) on 17 of 21 weekdays, 173-179 on the rest. NY 09:00-10:00 complete on all days.
- Not run: Friday evenings (market closed), weekends. **Sunday 18:00 / 20:00 week-open sessions were skipped** (script loops weekdays), which removes the biggest weekly-gap evenings. Fri 11-13 etc. have no 6PM/ASIA by design. Wed 11-04 6PM open bar is missing in the data, so that session was skipped. The first day (10-19) has no prior day, so Candace history is empty there.
- Sizing/costs: $2/pt per micro, $2 round trip per micro, no extra slippage. "Lucid-fit size" = 25K fit risk $158.33 per trade (the BRUNI/CANDACE fit table, equals the D143 JJ min()) via `lucid_fit.contracts_for`; Candace additionally `grade_contracts` (A+ full, B half, C quarter, so C trades often round to 0 contracts = $0). No daily stops, DLL or MLL path simulated; this is a per-trade table, not an eval simulation.
- Trades held after their window run to the engine's own exit (Candace: TP / STOP / max-hold; JJ: TP / STOP until 16:44 ET next day; no unresolved trades remained). JJ 6PM/ASIA are therefore held overnight in this test, which the live app does not do (intraday-only, flat 16:44).

## Which strategies use London / Asia / overnight (rule sheets read)
| Strategy | What the rule sheet says | Engine takes overnight bars as is? | Tested |
|---|---|---|---|
| CANDACE ICT | London 02:00-05:00 (B1), Asia range + midnight price (A5/A6) | London: yes (`london=True`, `replay_day(history, today)` takes any hour). Asia range / midnight price / new-week gap: not built | London + NY tested. Asia range not testable |
| JJ F.P.T | Trades 6 PM (18:00) and Asia (20:00) opens (#5, #12, #19); does NOT trade London | Yes: `jj_fpt.replay` with `SessionInput` 6PM / ASIA (config keeps them OFF) | NY, 6PM, ASIA tested |
| BRUNI | Asian-range schematic, London after it (mentions, "needs overnight data") | No: NY session only; Asian-range schematic not built | Not tested. Needs: Asian high/low range (about 19:00-02:00 ET) + London session bars and a rule for the schematic entry |
| CONTI (ORB / VWAP) | Overnight anomaly only (buy 16:00 close, sell 09:30) | No, and deliberately excluded (breaks Lucid/Paytience flat rules). ORB/VWAP are RTH | Not tested. Needs: nothing built; overnight hold is not allowed |
| IMRE AMT | Full-session (Globex + RTH) and composite profiles (B5) | No: Globex / composite profiles not built | Not tested. Needs: Globex-inclusive volume profile (needs per-bar volume incl. overnight) + composite logic |
| OKALA 8020 | "no overnight" (window 09:30-11:30) | No | Not applicable |
| GALA PA | Overnight gap as one candle (A7); no London/Asia trading | NY only | Not applicable (no overnight session rules) |
| Order Flow AR model (`order_flow.check_ar`) | Asia range + ATR zones as a FILTER | It is a filter, not a signal generator: needs `ArFields` (Asia range zone / path side) supplied by the caller, no standalone trades | Not tested. Needs: an Asia-range builder (19:00-02:00 ET high/low) feeding `ArFields` plus a host strategy to filter; building that glue is an engine change, out of scope |

CANDACE note: the engine's SESSION pool = high/low of today's bars so far. With a 00:00-17:00 `today` it therefore includes the 00:00-02:00 overnight range as a pool, a partial stand-in for the Asia high/low (A5), but the evening 18:00-24:00 Asia accumulation of the previous day is NOT in it (feeding it as history would also contaminate PDH/PDL, so it was left out). Midnight price and new-week gap are not used by the engine.

## Results (1 micro includes $2 round-trip cost; fit = Lucid 25K sized)
| strategy | session | trades | win % | PF | pts | $ (1 micro, $2 RT cost) | $ (Lucid-fit size) | MTM/unresolved |
|---|---|---|---|---|---|---|---|---|
| CANDACE | LONDON | 7 | 29 | 0.87 | -3.2 | -20 | +25 | 0 |
| CANDACE | NY | 1 | 100 | inf | +85.2 | +168 | +0 | 0 |
| JJ_FPT | 6PM | 49 | 31 | 0.71 | -131.5 | -361 | -1785 | 0 |
| JJ_FPT | ASIA | 68 | 44 | 0.93 | +10.5 | -115 | +441 | 0 |
| JJ_FPT | NY | 98 | 38 | 0.85 | -108.5 | -413 | -1425 | 0 |

Rows are one per strategy and session; CSV columns: strategy, session, day, time, dir, kind, entry, stop_pts, exit, pts, usd_1micro, micros_fit, usd_fit. Win % = trades with positive net $ at 1 micro. CANDACE NY is a single trade (+85 pt, grade C so 0 contracts at fit size), meaningless statistically; London 7 trades is no better.

## Limits / honesty
- 30 days, one regime, a continuous (unrolled) contract, free Yahoo data (no volume guarantee: some bars have volume 0, bars at the session start are thin). Do not use any of this to tune or enable anything.
- JJ results are negative at default settings in NY, 6PM and (after costs, 1 micro) ASIA; the fit-size ASIA positive comes from a few large-contract winners on small samples. Do not read as a ranking.
- JJ NY here has no news calendar (no 08:30 pre-news fair price), so it differs from the app's NY session.
- Candace London max hold 30 min is a [GAP] default; NY 15 min.
- To test properly the user would need a longer 1-minute overnight history (for example a Databento/Tradovate/TradingView CSV export; not used here since Databento is locked and no key was given) and, for Asia-range strategies, engine support for an Asia range (an engine change, not done).
