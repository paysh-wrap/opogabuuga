# AI ledger: fast-track backfill + live ledger audit (D78, session 13)

## 1. Fast-track backfill (estimate only)
- Where: Strategy page, "AI bias record" panel. Pick N (default 60), see the planned tool runs / provider / rough cost,
  press **Start backfill**; progress, error banner and **Cancel** are on the same panel.
- API: `GET /api/ai-ledger`, `GET /api/ai-ledger/backfill/preview?days=N`, `POST /api/ai-ledger/backfill {days}`,
  `POST /api/ai-ledger/backfill/cancel`. In-process background task (app/bias/backfill.py).
- Per past session (last N weekdays, oldest first): TradingAgents through the existing `.venv-ta` runner with the trade
  date = that day, then Vibe-Trading (`.venv-vt`) with a prompt that says "use only information published on or before
  that date". Nothing is imported into the API process; no new secrets (the saved Connections keys, Qwen supported).
- Rate limit: one call at a time, 5 s pause. STOPS after 3 errors in a row (or a missing key) with a UI error + header
  notification. Resumable (days already stored are skipped). A day with no valid TradingAgents rating is not stored.
- Isolation from the live proof: rows are stored under proxy `QQQ.BF` with version `BACKFILL:<ver>`. Every live reader
  (today_bias, live ledger, may_block, sizing_call) filters on `QQQ`, so a backfill row can never reach the D55 70% rule.
  The page shows backfill accuracy only as "estimate (possible hindsight)" and never a PROVEN / may-block verdict.
- Hindsight caveat: TradingAgents cuts its price data at the trade date but its news/LLM memory may still know the outcome;
  Vibe-Trading's tools are live. Treat the estimate as optimistic.
- Scoring limit: a day is scored from the stored 1-minute MNQ bars (09:30-16:00). Days before the app started recording
  bars stay "unscored" (not counted), so the estimate can have fewer scored calls than days run.
- Cost: N days = N TradingAgents runs + N Vibe-Trading runs (120 runs for 60 days). Rough planning guess ~$0.35/day and
  ~2 min/day (shown on the page as a guess; check the Qwen usage page).

## 2. Live ledger audit
- Daily job: scheduled at `schedule.bias` = 02:40 ET (D34 moved it from 06:10; before the open either way), weekdays,
  catch-up any time later if the app was off, one run per session, both tools per MNQ proxy.
- Gaps found and fixed:
  1. A proxy that failed (ERROR/NO_TRADE) was never retried automatically. Now retried every 30 min until 09:25 ET.
  2. A silent Vibe-Trading failure only left a note in the reasoning. Now a warning notification per day.
  3. Scoring needed the exact 09:31 and 16:00 bars; one missing minute left a day unscored forever. Now the first bar in
     09:31-09:35 and the last in 15:56-16:00 are used.
  4. Today's call was scored only the next day. Now scored right after 16:01 ET.
  5. No way to see missing days. New 30-weekday coverage list (no call / TradingAgents only / scored).
  6. New: "calls still needed" until the 70% proof (at the current hit rate, and the best case if every future call hits).
- Scoring is automatic: computed from stored bars whenever the ledger is read (no manual step).
- Not changed: US market holidays still get a call (no bars, so unscored, harmless; ~9 wasted calls a year).
- UI: live record (scored calls, accuracy, Wilson lower bound, calls needed) on the Strategy page.
