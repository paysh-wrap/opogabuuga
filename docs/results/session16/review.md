# Session 16 review: D82-D85 (profit lock, AI Duo, trade management, aggregate risk)

Scope: `git diff 18d2bf8..HEAD -- backend frontend config`. Checked against CLAUDE.md.

## Verified OK (no change needed)
- Aggregate risk (`risk/checks.py::_finish`): open risk + this trade + DLL margin must fit min(DLL left, MLL distance - kill buffer);
  qty is reduced to fit or the trade is refused (`AGGREGATE_RISK_EXCEEDS_LIMITS`); runs on every fixed-size path; worst-case check follows.
- Multi-position: `max_open_positions` is 1 unless strategy is AI_DUO AND account size >= `big_account_size` (150K, config).
  `one_position` uses max(open_positions, has_open_position). Every other strategy/account stays at 1.
- AI Duo paper-only: `paper_only: Literal[True]` in config plus `PAPER_ONLY_STRATEGY` in `_execute_one` for non-sim accounts.
- $250 cap and rr floor 1.5 come from config (`max_risk_usd`, `rr_min` validator refuses < 1.5, plan builders use max(cfg, trade_plan.rr_min)).
- Windows MGC 03:00-11:30 / MNQ 08:00-12:00 are config; the instrument/internal windows still apply on top (intersection, safer).
- Kill switch / flatten_all flatten per ACCOUNT at the broker, so all positions go; hedge lock (risk/hedge_lock) untouched, signal-level
  Duo/NOISE lock added on top. Presets only overlay noise/pm_fade/size-table config, no safety code. TA runner is not imported in the API
  process (subprocess adapter only). No secrets in the diff. Stop moves are protective (no 6 s hold); a failed modify flattens + pauses.

## Bugs found and fixed
1. NOISE profit lock (`order_manager._profit_lock`) placed the locked stop without looking at the market: if the bar printed the
   trigger but closed back under entry + lock, the stop would be at/through the price (broker reject -> STOP_MODIFY_FAILED -> flatten +
   never-resuming pause). Now capped one tick behind the bar close (still ratchet-only). Test: `test_noise_profit_lock_is_never_placed_through_the_market`.
2. AI-supplied lock level (`trade_manage.managed_stop`) replaced the config level as soon as the config trigger was hit, even if the AI
   level lay beyond the best price; the market cap then pulled the stop to one tick behind the price and cut the trade early. The AI level
   is now used only once price has passed it; until then the config level holds. Test: `test_an_ai_lock_level_beyond_the_best_price_is_not_used_yet`.
3. Aggregate risk ignored positions whose entry had not filled yet (`controller._open_risk` skipped legs with `entry is None`), so two
   signals in the same minute could together exceed the DLL/MLL room. Pending legs now count at the plan entry. Test: `test_open_risk_counts_an_unfilled_entry...`.
4. Flatten exit fills without a bracket id (CrossTrade) were booked wholly on the first closing trade; with several positions on one
   account the second never got its fill (60 s "unverified" path) and the first got the wrong quantity/fee. The fill is now split by quantity
   across closing trades. Test: `test_flatten_fill_is_shared_between_trades_of_one_account_by_quantity`.

## Notes / residual risks (not changed)
- `on_bar` without a `close` falls back to the bar low as "last" (long-safe, not exact for shorts). The controller always passes the close.
- MGC window instrument limits differ per plan file (the intersection applies).

## Coordinator follow-ups done in the same commit
- Dashboard: "ET ET" fixed (etTime already appends ET); projection grid was 3 columns for label/value pairs (values shifted under the next label), now 2 columns. Test: `DashboardLayout.test.tsx`.
- MGC step trail (D85 addendum): every 60 ticks of profit raise the stop 20 ticks above the original stop (user-set, config `step_trail`); replaces the guessed 13 -> 6.5 lock; AI level replaces it once passed. Tests 0/59/60/120/180 ticks, short side, market cap, AI override.
