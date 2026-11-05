# Decisions log (user-approved changes to Master Prompt v9.2)

## D1 — 2026-11-05 — Instruments added
- MGC (Micro Gold, COMEX): tick 0.10, tick_value $1.00, fee_rt VERIFY, enabled: false until §16.6 gate passes.
- MYM (Micro Dow / "US30"): tick 1.0, tick_value $0.50, fee_rt VERIFY, enabled: false until §16.6 gate passes.
- Lucid availability: both listed on Lucid's "Approved Products and Commissions" support article
  (per search results; the article host is blocked in this build session — confirm in your dashboard).
- Fees updated from Lucid's list: MNQ/MES/MYM $0.50/side → fee_rt 1.00; MGC $0.80/side → fee_rt 1.60 (VERIFY).
  The spec's §21 unit cases keep using the $1.50 placeholder as explicit test inputs.
- Correlation: MYM ∈ {YM,MYM} ⊂ EQUITY_INDEX (hedge lock applies with MNQ/MES).
  MGC ∈ {GC,MGC} ⊂ new METALS super-group (own hedge lock; not locked against equity index).
- Max 1 open position per account still applies across all instruments.
- min_stop_ticks / stop_buffer_ticks / slippage become per-instrument (global default + override).
- Bias proxies: YM→DIA, GC→GLD (TradingAgents).

## D2 — 2026-11-05 — Morning window 06:45–11:30 ET (was 09:35–11:30)
- windows: [["06:45","11:30"],["13:30","15:30"]] (still a user setting, editable in Risk UI).
- Schedule moved so everything is ready before 06:45:
  calendar 06:00 → bias 06:10 (10-min timeout) → pre-flight 06:40.
- Pre-09:30 is Globex overnight: thinner liquidity, 08:30 ET news (blackouts still apply).
  Backtest data must include overnight bars; report results per window slice.

## D3 — 2026-11-05 — API Keys page (UI + API)
- Page "API Keys" (under Connections): TradingAgents (repo URL, pinned version/tag, LLM provider + key,
  data vendor key), historical data key (e.g. Databento), broker/relay, notification webhooks.
- Keys write-only: encrypted at rest (OS keychain/Fernet), never returned by the API (last 4 only),
  never logged; "Test" button per key; audit-logged changes.
- TradingAgents key added later by user; until then bias = NO_TRADE + alert (spec §15) — so
  trading stays blocked by G2 unless user enables a documented bias-OFF ablation for PAPER only.

## D4 — 2026-11-05 — Dedicated Automation page
- New UI page "Automation" (not only a panel on Trade): master mode OFF/SEMI/FULL, per-account arm +
  overrides, pre-flight result, attestation, auto-pause reasons + resume rules, kill switch, approval queue,
  live rule-check table per account (DLL left, MLL distance, consistency headroom, hedge lock, news/flat times).
- Built in Phase 5 (controller) + Phase 6 (UI). Every Lucid rule check runs in pure risk code before any
  order; any error blocks new entries (§1.9).

## D5 — 2026-11-05 — Dashboard login
- Admin login created via `make create-admin` (Argon2 hash in DB only; plaintext never stored or committed).
- Username: PayDay (user request, 2026-11-05). Existing installs: `python -m app.cli rename-user admin PayDay`.

## D6 — 2026-11-05 — TradingAgents install
- Pinned tag v0.7.1 (commit 3e44faafa042daf953f6ec2422ae36bb1fd4f50f), Apache-2.0.
- Installed by `make tradingagents` into its own venv (.venv-ta); trading process talks to it via a
  JSON subprocess runner with a hard timeout. REVIEW / unknown rating → NO_TRADE + alert.

## D7 — 2026-11-05 — "1:1 mode" toggle (APPROVED in part; build in Phases 3/4/6)
User request: Risk Management toggle enabling 1:1 reward:risk trades; ONLY in that mode up to 3 losses/day
(normal mode keeps 2); in that mode take 50% profit at 75% of the distance to take-profit.
This overrides the §7 2–3R pillar while ON (user-owned change; the Lab may never toggle or tune it).
Unchanged in this mode: all gates, DLL/MLL pre-trade checks, kill switch, consistency guard, hedge lock,
news/flat times, force_floor after a loss, Evaluation Mode scope.
Answers (user, 2026-11-05): TP exactly 1R. Up to 3 losses/day in this mode. Up to 5 trades/day when on a
3-trade winning streak, never exceeding the 40% consistency rule.
Interpretation (confirm): trades 4 and 5 are allowed only while the CURRENT consecutive-win streak today is >= 3
(W W W → 4th ok; W W W W → 5th ok; W W W L → stop). Config: one_to_one_mode.*
DLL note: per-trade DLL check is never weakened, so on large risk bases (> ~$2,085 at default tiers) a 3rd loss
cannot fit the $600 DLL and the day ends after 2. EVAL (max base $1,437.50): 3 losses = $450.98 incl. margins ✓;
Evaluation Mode: $506.53 ✓; FUNDED at $3,000 cushion: $810.72 ✗ → 3rd trade skipped by the DLL check.
Answers 2 (user, 2026-11-05): stop → breakeven after the 75% partial. One contract: trail the stop into profit,
~25–35% of the way (config: lock 0.30R at the 75% trigger, bounds 0.25–0.35R, ratchet only). A loss on the 4th
trade ends the day. Must pass its own backtest gate (≥100 trades, E ≥ 0.20R net, PF ≥ 1.4, 0 violations) before
paid accounts. Stages: EVAL + FUNDED (LIVE pending). Handles EOD and intraday drawdown accounts.
Still open: Q7 apply the 40% consistency cap on FUNDED too (firm has none there)? LIVE stage allowed?

## D8 — 2026-11-05 — Minimum hold time (Lucid microscalping rule)
- Lucid (FAQ, per search results): flagged if > 50% of profits come from trades held <= 5 s. VERIFY.
- Parameters: behavior.min_hold_seconds 6, firm_microscalp_hold_seconds 5, rapid_trade_warn_pct 20,
  firm_microscalp_pct 50 (config-validated: hold > 5 s, warn < firm limit).
- Enforcement (Phase 4/5): every app-initiated exit waits until held >= 6 s. Never delayed: stop-loss,
  broker TP leg, kill switch, MLL/DLL breach, news flatten, flat times (earlier rules win, per user).
- Metric: % of profit from trades held <= 5 s, per account per payout cycle; warn at 20%.
- Proposal (needs approval): pause NEW entries on an account if that share reaches 35%.

## D9 — 2026-11-05 — Funded drawdown type default = EOD
- User: Lucid account stages are usually EOD drawdown → funded.drawdown_type: eod (VERIFY).
  (A third-party guide said LucidDaily funded is intraday — confirm in your dashboard.)
- Both types stay fully supported: each account has its own drawdown_type (Accounts page) and the MLL
  tracker / guard / 1:1 management follow the account's type. Spec §21 MLL tests for both types are kept.

## D10 — 2026-11-05 — Exclude 09:30–09:35 (opening bell)
- Windows: 06:45–09:30, 09:35–11:30, 13:30–15:30 ET.
- Backtest (Phase 8) reports performance with vs without 09:30–09:35; if excluding it hurts, the Lab raises a
  suggestion for the user (windows are a user setting, never changed automatically).

## D11 — 2026-11-05 — Indicator source access
- Official pages: LunqFX https://www.tradingview.com/script/HGW9NYJZ-ICT-Fractal-Model-HTF-Candles-CISD-C2-Targets-LunqFX/
  (open-source per search results); BigBeluga https://www.tradingview.com/script/mFMTYEYR-Market-Structure-Oscillator-BigBeluga/
- tradingview.com is blocked by this build environment's network policy; user cannot paste source.
- Phase 2 builds Paytience's OWN implementation of the spec's definitions (§5–§6) in Python + Pine (no copied code).
  It is labelled "spec-derived, not yet verified against the original source". Verification: (1) read original
  source once tradingview.com is allowed and align semantics; (2) §5.2 three-way parity over ≥20 sessions —
  mismatch blocks LIVE and Lab promotions (unchanged).

## D12 — 2026-11-05 — Alert id carries the direction (spec §5.3 bug fix)
- §5.3's id = ticker-profile-time-event. Two same-type events in opposite directions on one bar (outside bar
  sweeping both sides, CISD both ways, divergence both ways) would share an id and the second would be dropped as a
  duplicate. Id is now ticker-profile-time-event-DIRECTION (Python + Pine + tests). No trading rule changes.

## D13 — 2026-11-05 — Order route research (decision needed before Phase 5)
- TradersPost lists Lucid Trading as a supported prop firm (automation + copy trading allowed); Lucid permits bots
  (HFT banned). Native Tradovate API keys are generally not issued for prop accounts (third-party reports).
- TradersPost sends orders but (to my knowledge) does not report positions/fills back → kill switch, reconcile and
  stop-modify confirmation would run in CONSERVATIVE MODE (§4) and FULL-AUTO would stay blocked (§1.9).
- Options for read-back: (a) ask Lucid support whether Tradovate API/OAuth can be enabled on your account IDs;
  (b) CrossTrade + NinjaTrader (reads positions/P&L; needs NinjaTrader running on a Windows PC).
