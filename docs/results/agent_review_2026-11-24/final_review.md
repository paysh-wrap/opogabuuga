# Final review: review-fixes-2026-11-24 vs 0a72f1d (read-only, static; tests not run)

Scope: backend/app + frontend/src diff. No blocker found. No safety check is weakened except the NOISE merge gate bypass (M1). Tightened: TP-fit for CANDACE/late-day, paper_only now read, one-choice on load/rollback.

Checked and OK:
- paper_only: every `paper_only` default is False and no config/ yaml sets it, so nothing is blocked by default.
- rth_only: `(09:30, 16:00]` ET uses astimezone(ET), so DST is correct. Sunday/Monday: the 7-day lookback keeps >= 4 RTH sessions, and replay_day slices prior[-1440:] (~3.7 RTH sessions). An empty `today` returns early. No lookahead (bars <= at).
- Late-day / NOISE flat at-or-after: only open signals are touched.
- `_iso` savepoints: the runners wrapped by `_iso` do not call commit (the commits are in run_order_flow, outside `_iso`), and webhook/service.py already uses begin_nested on the same engine.
- Per-runner savepoint failure is not silent: it is logged, broadcast and notified.
- Frontend: the Strategy save and load error states, and the radio card (the partial state re-sets both to ON).
- Count-up settles on the exact target: the final frame sets `target`, and Num snaps when |v-n| < 0.005.

## MEDIUM

M1. backend/app/signals/strategy_service.py:343-366 (NOISE same-direction merge)
- Scenario: at a check, an EXIT and a same-direction ENTER are decided. The merge returns before `_gate` (news, window, calendar, HEDGE_LOCK vs DUO), `structure_check` and `ledger.may_block` run. Before this change a failing gate meant exit and no re-entry (flat). Now the position is held through a news blackout, a closed window or an opposing DUO position.
- The held trade also keeps the OLD 1% stop and TP rather than the re-entry's plan, so it diverges from the backtest. The exit reason is never audited.
- Fix: evaluate `_gate` / `structure_check` / `ledger.may_block` for the ENTER first. Merge only if the gate passes; otherwise emit the EXIT only. Alternatively, on merge, ask the controller to re-issue the plan.

M2. backend/app/automation/controller.py:1312-1318 (`_mark_signal_closed` now closes without an `exit_requested` marker)
- Scenario: SEMI mode (90 s approval) or a late per-account fan-out. Account A's trade is stopped out and its only open trade closes. The signal turns CLOSED while account B's trade is created or approved afterwards. B's trade then sits on a CLOSED signal, so no strategy exit (band/VWAP, 16:00 flat, hold exit) ever targets it. Only the 16:40 flatten covers it.
- Fix: only auto-close when no pending approval or unplaced account is left for that signal (for example, check that Trade count equals the accounts the signal fanned out to), or let strategy exits also match CLOSED signals that still have an open Trade.

M3. backend/app/risk/settings_store.py:311-316 (`enforce_one_choice` inside `effective()`)
- Scenario: a pre-D167 save with 2+ choices ON loads with the later choice silently OFF. The order keeps main NOISE+CANDACE, so a user who enabled Order Flow or OKALA loses it. There is no audit row, banner or log, and it is not persisted, so the Settings version history disagrees with the live config.
- Fix: log and audit once (a settings note such as "D167 normalised") and show a UI notice. Better, persist a new version on first load.

M4. Spec conflict: D160 `order_flow_cfg.ar_side_by_side` (fast_pass.py:120, controller.py:486/697, ar_pre_session.py:34) vs D167
- "AR beside NOISE on a different account" needs NOISE and Order Flow ON together. STRATEGY_CHOICES now forbids that (order_flow vs main_noise_candace), so the option can never be live. The AR toggle in StrategyButtons still shows and saves. If the user switches it on, a 422 or a silent no-op results.
- Fix: ask the lead which decision wins. Either exempt the (order_flow + noise) pair when ar_side_by_side is ON, or hide and disable the toggle and document it in DECISIONS.

M5. backend/app/signals/strategy_service.py:1696-1706 and backend/app/api/webhook.py:129-135 (`_iso`)
- (a) A runner that fails on every bar (a bad config, for example) raises a risk.alert and a notification each minute (alert spam), and `detail` (str(e)[:200]) goes into the notification.
- (b) CLAUDE.md rule 8 says an error should block new entries. Only the failed runner's entries are blocked; the other runners keep entering. A failing NOISE flat or exit leaves the position open until the 16:40 flatten, with only a banner.
- Fix: de-duplicate alerts per (runner, error) per day. On a failed runner, consider forcing exits_only for that symbol.

## LOW

L1. backend/app/signals/strategy_service.py:306-316 (`k < flat_k` early return changed to `>=`)
- Every after-hours heartbeat (about 480 per day on a 24 h store) now runs `load_days` (14 days of bars) before it discovers there is nothing to close.
- Fix: query the OPEN NOISE signals first and return when there are none, then call `load_days`.

L2. frontend/src/lib/useCountUp.ts:11 and components/MissionBento.tsx:15
- A non-finite target (NaN from `Number(undefined)`) stores NaN in `from.current`. The next finite target then animates from NaN and shows "$NaN" for 600 ms. This is a wrong number mid-animation, although the settled value is right.
- Fix: guard `from.current` with `Number.isFinite(start) ? start : target`, and have callers filter NaN.

L3. frontend/src/components/NowRunning.tsx:21
- The error branch is `q.error && !q.data`. A failed refetch keeps showing the stale "Now running" (or the "No strategy" warning) with no stale marker for up to 30 s per retry.
- Fast-pass plans and the late-day option are not listed, so "No strategy is ON" can be shown while a fast-pass plan is ON.
- Fix: when `q.isError && q.data`, show a "status may be stale" suffix. Include the fast-pass toggles, or label the strip "main strategy".

L4. frontend/src/components/StrategyButtons.tsx:158-166
- The turn-off set comes from q.data at click time (up to 30 s stale). The backend 422 catches the error and the save alert shows it, so the effect is only a harmless failed click. A refetch before the PUT would remove it.

## Order Flow
- No Order Flow engine code changed. The changes are `_iso` wrapping (run_order_flow_auction, order_flow_exits), one-choice membership (order_flow is its own choice) and the UI badge (EvidenceBadge replaces hard-coded "UNVERIFIED" text, so confirm `verified` is false for every Order Flow card).
- `run_order_flow_auction` still discards `r.exits` (pre-existing; its exits are broker legs).
- See M4 for the AR side-by-side conflict.
