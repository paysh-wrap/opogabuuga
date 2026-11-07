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

## D14 — 2026-11-05 — Heartbeat carries the structure snapshot
- §5.3 heartbeat had price only, so oscillator strength (score item) would go stale between structure events.
  HEARTBEAT now also carries `mso` {trend, osc, htf_trend} (optional field; backward compatible). Bridge + Python.

## D15 — 2026-11-05 — Phase 3 interpretations (confirm or correct)
- Cooldown streak resets when a model reaches T1 (or T2) — "a TP between failures resets the streak" (§21).
  Cooldown is per symbol+profile and lasts the rest of the trigger session + 5 more trading sessions.
- Gate failures are HARD (skip now: bias against/none, C1 too small, cooldown, model failed/traded/C3 closed,
  T1 traded through, instrument disabled) or TRANSIENT (wait for the next bar: window, news, feed, calendar,
  structure, divergence, R:R at this price, score). A waiting model EXPIRES after 6 bars or half of C3.
- Entry price = the close of the bar whose HEARTBEAT has arrived; events for a bar wait for that bar's close.
- "Not halted" (G1) has no separate data source; a halt shows up as a stale feed, which blocks entries.
- Paytience_Bridge_Strategy.pine (§5.5, Strategy Tester) is built after Phase 4, once risk + guard exist.

## D16 — 2026-11-05 — Approvals: 1:1 on LIVE, funded consistency, win-rate filters, self-learning
- 1:1 mode stages: EVAL, FUNDED, LIVE.
- 40% consistency also on FUNDED (user's own limit): cap = 40% × max($1,250, payout-cycle profit so far),
  day stop at 35% of the same reference (interpretation — confirm). Built in Phase 4 (risk/consistency.py).
- Win-rate filters E1–E7 active in 1:1 mode (stricter-only; config one_to_one_mode.filters); E2/E6 need ≥ 30
  recorded samples or the 1:1 trade is skipped (fail-closed). E8 = Lab slice suggestion (Phase 9).
- Self-learning A1–A8 approved. Built now: A4 (regime/time-slice tags on every signal), A5 (disabled instruments
  evaluated in SHADOW, never traded). Scheduled: A1/A2/A8 Phase 8 (backtest), A3/A6/A7 Phase 9 (Lab).
- Fix found while building: bias lookup ignored the proxy ETF (gold would have used the Nasdaq bias); bias is now
  read per instrument proxy (QQQ/SPY/DIA/GLD).

## D17 — 2026-11-05 — Phase 4 interpretations (confirm or correct)
- DLL remaining = DLL + min(0, today's P&L incl. open): profits today do not add room (conservative).
- Worst-case check: contracts × (stop + fees + slippage) + $40 margin ≤ min(DLL remaining, MLL distance − $100 kill
  distance), so the kill switch never has to fire because of a planned stop.
- Funded consistency (D16): cap 40% / day stop 35% of max($1,250, payout-cycle profit so far).
- 1:1 partial on an odd contract count closes ceil(n/2) (same split as the drawdown guard's leg A).
- Effective rules = YAML ⊕ Firm Rules versions ⊕ My Settings versions; if a stored version stops validating, the
  app reports it and must not trade (Phase 5 automation checks `rules.error`).

## D18 — 2026-11-05 — DLL room measured from today's best P&L (safe under every reading)
- Sources disagree whether Lucid's $600 DLL is measured from the prior close (fixed floor) or trails today's high.
  Room = DLL − (today's best P&L incl. open − current P&L). Profits never add room; giving profit back uses room.
  Stricter than or equal to both readings (user: "whatever best protects the account").
- D17 item 2 confirmed by user: worst case must fit both the DLL room and the kill-switch distance.

## D19 — 2026-11-05 — Conflicts to verify with Lucid (docs/LUCID_SUPPORT_MESSAGE.md)
- Tradovate's own help center: prop/evaluation accounts are NOT eligible for Tradovate API keys → the native
  Tradovate route is very likely unavailable; read-back must come via a supported bridge (CrossTrade/NinjaTrader)
  or stay in conservative mode with SEMI-AUTO.
- A third-party guide says every LucidDaily FUNDED account uses intraday drawdown regardless of purchase choice —
  this conflicts with D9 (funded default EOD). Per-account drawdown type handles both; confirm with Lucid.

## D20 — 2026-11-05 — Lucid rules checked on Lucid's own help center (docs/LUCID_RULES.md)
- Funded drawdown is ALWAYS intraday → funded.drawdown_type back to intraday (replaces D9's EOD default).
  Drawdown guard therefore turns ON for funded accounts until the MLL locks at $25,100 (§8, as designed).
- Fees, DLL $600, MLL/lock, contracts, microscalping, news, payouts, live: all match config.
- DLL is fixed per session (does not trail). D18's stricter "from today's best P&L" stays (user: protect the account).
- Automation explicitly permitted.

## D21 — 2026-11-05 — Indicators verified against the original sources
- BigBeluga MSO: ROC/stdev → sigmoid → EMA(10); 5/5 pivots; ChoCh = first break in a direction; divergence on
  oscillator pivots (5/5). LunqFX: one model at a time; HTF candle closes on the next period's first bar; CISD not
  reset by deeper sweeps; failure beyond the sweep even after T1; raw midpoint T1; pre-tick = C2 close beyond T1.
- Python + Pine bridge rewritten to match; LIVE still gated on ≥ 20-session three-way parity.

## D22 — Evaluation Mode one-button toggle (user request, 2026-11-05)
Typed phrase replaced in the UI by one ON/OFF button + a confirm dialog. Backend still requires the phrase (UI sends it
after confirm). Still EVAL-only, capped $140, all other rules unchanged.

## D23 — 1:1 option inside Evaluation Mode (user request, 2026-11-05)
`eval_mode.one_to_one`: when ON, EVAL accounts with Evaluation Mode effective use 1:1 plans (TP 1R, 0.75R partial → BE,
3 losses/day, all D7 rules). Never FUNDED/LIVE via this option. 1:1 backtest gate still applies before LIVE use.

## D24 — Per-account EOD / Intraday trailing toggle (user request, 2026-11-05)
Automation page → each account: "EOD trailing" | "Intraday trailing". Must mirror the account at Lucid (it drives MLL
tracking and the drawdown guard). Any account may use either (user choice); when it differs from the stage default
(EVAL=EOD, FUNDED=intraday per D20) the account shows a ⚠ "confirm in your Lucid dashboard" note. Change refused while a
trade is open.
New accounts default to the stage's drawdown type from the rules file (was always EOD — fixed for FUNDED).

## D25 — Lucid sim → live path (user, 2026-11-05)
EVAL and FUNDED accounts are Lucid SIMULATED accounts (real orders to Lucid's Tradovate sim via CrossTrade);
LIVE = real money after Lucid moves you (≥ 1 processed payout; $6,000 day trigger). Badges: APP PAPER (our simulator),
LUCID SIM, LUCID LIVE $. Payout line counts processed payouts toward live (`funded.payouts_to_live`, VERIFY — user to
confirm the number). Once any account is LIVE, sim accounts are blocked (§10, account_selector). Live rules from config
(start $0, EOD, no DLL, $15k sim-profit cap) — all VERIFY.
D25 update (user-confirmed): 1 processed payout qualifies for live (Lucid risk team decides); 5th payout enters the
live review pool (not required). Config: funded.payouts_to_live 1, funded.payouts_live_review 5.

## D26 — Phase 7: payouts + economic calendar (2026-11-05)
- Payouts: pure `phases/payout_plan.py` (sweep above $28,100 / skim half of week profit when locked; ≥ $500; never
  below $26,100 buffer; ≥ $1 profit since last payout). Weekly Fri 17:05 ET in-process scheduler. Lucid has no API:
  app plans + reminds; user marks "I requested it" (account stops trading) → "Paid" (paper balance debited).
- Calendar: Finnhub's economic calendar is PREMIUM ("Premium Access Required", verified) → using the free
  ForexFactory weekly JSON (nfs.faireconomy.media, format verified: ISO dates with ET offset; impact High/Medium/
  Low/Holiday). USD + High only. Refreshed every 4 h; cached in DB. Covers the current week only: a date outside the
  fetched week = no data = no trading (§15). Feed terms could not be read (Cloudflare) — personal, low-rate use.

## D27 — Phase 8: daily TradingAgents bias job (2026-11-05)
06:10 ET Mon–Fri: TauricResearch/TradingAgents v0.7.1 runs once per enabled instrument's proxy ETF (QQQ for MNQ) in
its isolated venv. Rating → five-tier map. Missing key / failure / timeout / unknown → NO_TRADE + alert (that
instrument doesn't trade). Failures can be retried ("Run now" on Today); a valid bias is never re-run that session.

## D28 — Review fixes (2026-11-05)
- News flatten was missing: now on every heartbeat, open trades are flattened `news_flatten_before_min` (2) /
  firm `news_breach_min_before` (1) before a USD high-impact event; hard-breach stages (FUNDED/LIVE, and EVAL since
  LucidDaily disallows news) stay flat until `news_breach_min_after` (1) after. Tested.
- Simulator fills from on_bar were also left queued (harmless, but could be applied twice): now delivered once.
- EOD MLL update was never scheduled (EOD accounts' MLL would never trail up → app under-estimated risk): now runs
  weekdays at `schedule.eod_update` 16:50 ET (after the 16:44 hard flat) on the settled balance, once per session.

## D29 — Phase 9: backtest + Monte Carlo (2026-11-05)
- Replay uses the live code end to end: 1-min CSV → Python ports of LunqFX fractal + BigBeluga MSO (TIGHT 1m→15m,
  STD 5m→60m) → bridge alerts → real webhook → gates → risk → order manager → simulator (fees, slippage, stop-first),
  in a throwaway app + DB. EOD MLL update per session. ~7 s per day of 1-min data.
- Inputs history can't give are explicit assumptions on the result: bias (recorded TradingAgents decisions only →
  missing days = no trade; or a fixed bias), no historical news calendar.
- Stats: win rate, net, avg R, PF, max DD, best-day share vs 40% consistency. Monte Carlo resamples whole days with
  EOD trailing $1,000 drawdown → eval pass/fail rate + median days.
- Data: CSV upload (Databento GLBX.MDP3 ohlcv-1m or any 1-min OHLC with UTC/epoch time). Databento API pull not
  built (needs your key + verified API format).

## D30 — Focus on LucidPro / LucidFlex; gold (2026-11-05)
- 8 plan rule files from Lucid's help center; plan picker on Risk page (switch only when flat); default Flex 25K.
- Schema: optional eval consistency / DLL, funded news allowed, Flex funded scaling (firm max micros by settled
  profit), payout caps (Pro per payout #, Flex 50% of profit + 5 profitable days), Flex MLL lock on payout request,
  max 5 payouts. Pro 25K–150K per-trade risk capped so two max losses fit the DLL (§11 test).
- Markets buttons (Gold MGC / Nasdaq MNQ / US30 MYM / S&P MES); micro contracts only. Backtest per market with an
  edge breakdown (hour ET, weekday, direction, profile, exit). A gold research agent is gathering MGC specifics.

## D31 — Hold time + half-off defence (user, 2026-11-05)
- Lucid has no minimum-minutes rule; only microscalping (> 50% of profit from trades held ≤ 5 s = flagged). App exits
  wait ≥ 6 s; Dashboard shows each account's % of profit from ≤ 5 s trades (gold at 20%).
- Half-off defence (internal.adverse_half_enabled, default ON; adverse_half_at 0.85–0.95, default 0.90): when every
  confirmation is against the trade (MSO trend flipped AND an MSO CHoCH against since entry) and price has gone 90% of
  the way to the stop, close one of two equal brackets (≈ half), once per trade, after the 6 s hold. Needs ≥ 2
  contracts (trades of 2+ are placed as two identical brackets). The stop on the rest is unchanged.
  Live via CrossTrade: closing a single bracket isn't built yet (API not verified) → reported, nothing sent.
- Note: spec early exits (C3 close / CHoCH against before +1R → full exit) exist in code but were never wired.
  Left unwired pending your choice (full exit vs this half-off rule).

## D32 — Lucid rules: never broken (user, 2026-11-05)
Enforced: flat 16:40/16:44 (Lucid 16:45); EOD/intraday MLL + kill switch; DLL; consistency (plan-specific); max
contracts + Flex scaling; microscalp (≥ 6 s app exits, ≤ 5 s profit share tracked); no hedging (hedge lock, 1
position per account); news per plan; payouts per plan rules. Added now: household limits for real accounts (10 total,
5 funded, 5 live — 11404617) and inactivity warning (Lucid deletes after 30 days with no $1 P&L — 11404632).
Only intraday trading (scalps + day trades, flat before the close); nothing overnight.

## D33 — Cooldown counts only qualified models (user-approved, 2026-11-05)
Gold backtest (Oct 2026, 741 models): 592 skipped by COOLDOWN because failures of models the strategy would never
trade kept re-arming it. Now a MODEL_FAILED counts toward the 3-failure / 5-session cooldown only if that model's
signal passed every gate. T1/T2 hits still reset the streak.
Also fixed: backtests were rate-limited by the live webhook limiter (≈ 90% of replayed alerts dropped).

## D34 — Real futures contracts; morning jobs before gold's London window (user, 2026-11-05)
- Orders name the actual futures contract Lucid/Tradovate trades (MGCZ6, MNQZ6), never the continuous chart symbol
  (MGC1!). app/contracts.py picks the front month from config `instruments.*.contract`: metals roll 2 business days
  before first notice day (GJMQVZ), equity index 8 days before the 3rd-Friday expiry (HMUZ). `override` pins a contract
  (exchange holidays aren't modelled). No contract config → order refused. Dashboard market buttons show the contract.
  TradingView signals still come from MGC1!/MNQ1!.
- Backtests label their data source; spot data (e.g. XAUUSD) is flagged "NOT FUTURES — signal counts only".
  Real MGC/MNQ futures data to be loaded once the app is near finished.
- Calendar 02:30, bias 02:40, pre-flight 02:50 ET (were 06:00/06:10/06:40) so gold's 03:00 window is tradeable live
  (before: no bias until 06:10 → live couldn't trade what the backtest did).
- Approved safety fixes from the review: feed-independent watchdog (flat/news/MLL), 16:44 hard flat enforced with
  retries, flatten exits book real fill P&L, failed emergency flatten stays tracked + retried.
- $50–70k/year analysis dropped for now (user).

## D35 — More signals on MGC/MNQ (user, 2026-11-05)
- R:R minimum 1.75 (was 2.0), all plans. User: "I'll settle with 1.75". Target: MGC 2–4 signals/day, MGC+MNQ 3–5 trades/day.
- New strategy switches (defaults = old behaviour; set per plan once proven on futures data):
  filters.require_mso_agree / require_structure_break (G4/G5 hard vs score-only), filters.t1_through_ok_with_limit,
  score.exclude_unknown (neutral bias / unproven T2 rate leave the max instead of scoring 0), profiles.enabled
  (["STD"] = intraday 5m→1H only).
- Fixed: entry.mode limit_cisd now sends LIMIT brackets (before: market orders → every fill failed the R:R recheck),
  unfilled limits cancel after limit_timeout_bars and don't count as trades. Live partial-leg cancel not supported by
  CrossTrade (account pauses) — VERIFY before live.
- Futures test (Yahoo MGC=F/MNQ=F 1m, 18 sessions, neutral bias): as built 0 trades. Best so far "c4" (1.75R, limit
  CISD, G4/G5 score-only, exclude_unknown, neutral min 60, C1 ≥ 0.4 ATR, T1-through OK with limit, MGC 03:00–15:30,
  MNQ 06:45–15:30, max 5/day): MGC 19 trades (~1/day) 42% win, PF 1.43; MNQ 10 trades, 10% win (TIGHT 1m stops in
  2–8 min). STD-only: ~0.2/day. Half of MGC passes don't fill (limit timeout). Sample far too small → need longer
  futures history before setting any of these live.
- UI modes requested by user: Scalping, Intraday, Low risk, 1:1.

## D36 — Blend for MGC + MNQ, Lucid Pro/Flex (user, 2026-11-05)
- Pro/Flex plans (not the legacy Daily file the test suite uses): rr_min 1.0 (targets 1R–3R), limit_cisd entry, G4/G5
  score-only, T1-through OK with limit, neutral score 60 + exclude_unknown, C1 ≥ 0.4 ATR, MGC enabled 03:00–15:30 ET,
  MNQ 06:45–09:30 + 09:35–15:30, max 5 trades/day; 1:1/scalp max 5 (7 on a win streak); low risk max 7/day.
- Lower risk: if half risk can't buy 1 micro, trade 1 micro when it costs ≤ normal-mode risk (never more).
- Fixed: signal-history cache aged in wall time → backtests never "proved" T1 rates (scalp/1:1 always skipped).
- UI: Trading mode selector (Intraday default / Scalp / 1:1) + Lower risk; Connections: Fincept + OpenBB (info only,
  never touches TradingAgents bias, gates or sizing).
- Futures backtest (Oct 12–Nov 5, 18 sessions, neutral bias, Flex = Pro 25K): normal MGC 40 trades 48% PF 1.28,
  MNQ 19 trades 32% PF 1.41 (~3.3/day). Low risk: MGC 42 (48%, PF 1.48), MNQ 24 (38%, PF 1.58) ≈ 3.7/day.
  Scalp: real T1 hit rate < 55% → its 65% filter blocks almost all (needs a design decision).
- make_plans.py still uses the Daily file as its template: re-running it would drop D36 from Pro/Flex. Don't
  regenerate without porting D36.
- Win rate (D36b): setups without a CHoCH/BoS after the sweep keep trading but target 1R (filters.no_break_rr_cap
  1.0); with a structure break they keep 1R–3R. Futures 18 sessions: MGC 61% win PF 1.73 +$601 MC 95%; MNQ 43% win
  PF 1.73 +$404 MC 92%; ~3.6 trades/day total. One parameter, same effect on both markets, but small sample —
  re-check on longer data.

## D37 — H1 best-hours filter, normal Intraday mode only (user-approved 2026-11-06)
- Instruments get `intraday_windows`; used ONLY when low risk, 1:1 and scalp are all OFF (pure `apply_intraday_windows`).
- MGC 05–07, 09–12, 13–15:30 ET; MNQ 08–09:30, 09:35–10, 11–12, 14–15 ET. Low risk / 1:1 / scalp keep full windows
  so their trade counts are unchanged.
- Sample (Pro 25K, 18 futures sessions, neutral): MGC 61%→71% win, PF 1.73→3.92; MNQ 43%→67%, PF 1.73→4.66;
  ~2 trades/day in Intraday. Hours chosen in-sample (1–6 trades/hour) — confirm on longer data (Databento).

## D38 — Scalp + 1:1 trade again, same signals as normal (user-approved 2026-11-06)
- 1:1 filters E1–E6 off in Pro/Flex plans (min_samples 0 = off; min_score = normal 60); E7 news kept.
- Fix: a stop move that races a same-bar TP/stop fill is not a broker failure (stop no longer WORKING) — real
  modify failures still flatten + pause (§8). This was pausing 1:1 accounts after ~2 trades.
- User: model-fail cooldown does not apply in Scalp mode (`filters.model_fail_cooldown.in_scalp: false`).
- Pro 25K, 18 sessions, neutral: 1:1 MGC 40 tr 65% PF1.56, MNQ 24 tr 50% PF2.06; Scalp MGC 22 tr 50% PF0.66
  (−$86), MNQ 16 tr 56% PF5.75. ~Half of placed limit orders don't fill (all modes).

## D39 — fills/stops use only the finest live price feed (from session 4's "D37" WIP, merged + tested)
- Controller.bar_feed_ok: 5-minute bars are ignored for fills/stops/management while 1-minute bars arrive (within
  3 of their bars); falls back to the slower feed if the finer one goes silent. Half-off defence reads the trade's
  own profile MSO. Test fixed (it checked after the 1-minute feed had gone silent).

## D40 — §17 self-improvement loop (Lab), built 2026-11-06 (user: "strategy must constantly self-improve")
- lab/tunables.py: TUNABLE_PARAMS = only §17.2 keys with bounds; steps ≤ max_param_step_pct (25%) of the range;
  everything else rejected (pillars, firm rules, risk %, Eval Mode, cooldown, lock-in, payouts, windows, R:R).
- lab/challenger.py + lab/cycle.py: weekly (schedule.lab_cycle) and on demand ("Run Lab now"): recorded sessions →
  walk-forward (older 75% train / newest 25% test) → champion vs one-step neighbours → best train candidate that
  keeps WIN RATE and ≥90% of the TRADE COUNT (user rule) → must beat the champion out of sample by
  self_improvement.min_improvement_r with ≥ min_oos_trades → pending Proposal (plain-English explanation).
- Approved proposals apply at the next 18:00 reset as a versioned "lab" settings layer (re-validated); one-click
  rollback; max one per cooldown_days. Nightly session backtest (existing) keeps feeding the Lab page.
- Not built yet: SHADOW run of a challenger before proposal (§17.3), automatic rollback on live rolling-30 E
  (§17.4), Optuna search (one-step neighbours used instead), bootstrap CI guard.
- D40b (same day): SHADOW + AUTO-ROLLBACK built — the loop now closes by itself:
  nightly (every session) → backtest recorded bars + shadow_check (challenger vs champion on sessions recorded
  since it was found; pass needs ≥ shadow_min_sessions 10 and ≥ shadow_min_trades 20, same-or-better win rate,
  ≥90% trades, E ≥ champion; fail after shadow_max_sessions 30) → pending (or auto-approved when
  self_improvement.auto_promote_paper and the app is PAPER) → 18:00 apply → nightly auto_rollback when the live
  rolling-30 net-R E since the change < the champion's out-of-sample E recorded when it was found.
  Still not built: Optuna search, bootstrap CI guard.

## D42 — MNQ off (user, 2026-11-06)
- All Pro/Flex plans: `instruments.MNQ.enabled: false` (every mode: Intraday, Low risk, Scalp, 1:1). MGC only.
- Why: MNQ not profitable after the D39 realistic-fill fix (22 Yahoo sessions) and MNQ Scalp lost in every period of
  35 months of Databento data (Results K). Re-enable from the Risk page market toggle or the plan file once proven.
- Legacy lucid_daily_25k.yaml (test fixture) unchanged.

## D43 — Scalp and 1:1 strategies retired (user, 2026-11-06)
- User: "only keep what was profitable … get rid of scalping strategy and 1:1". After D39 (realistic fills) both lost
  on MGC (1:1 PF 0.61, Scalp PF 0.45) and MNQ Scalp lost in every period of 35 months (Results K).
- Kept: Intraday (best hours, MGC) + the Lower-risk sizing toggle.
- risk/low_risk.retire_short_modes forces one_to_one_mode / scalp_mode / eval_mode.one_to_one OFF in the rules holder,
  whatever a plan file or an older stored setting says. The keys are no longer editable in My Settings; the Risk page
  mode cards, the "How Scalp and 1:1 exit" panel, the Eval-Mode 1:1 checkbox and the Backtest mode picker are gone.
- The dormant engine code (1:1 plan builder, scalp runner) stays for now so old trades/replays still read; it can be
  deleted in a later clean-up.

## D44 — Trend-side filters (built, all OFF until proven) — 2026-11-06
- Research Results L: on MGC setups at a fixed 1.75R target, trading only on the trend side roughly doubled the win
  rate (VWAP, EMA 200 5m, UT Bot 5m). Samples too small (7–15 trades) → built as switches, default OFF.
- indicators/trend.py (pure, Decimal, incremental, closed bars only): session VWAP (resets 18:00 ET), EMA 200 on
  5-minute bars, UT Bot (key 1, ATR 10; QuantNomad's open-source formula) on 5-minute bars. Fed from the heartbeat
  bars TradingView already sends (1m bars are bucketed into 5m) → no Pine/TradingView change.
- Engine gate TREND (only when a switch is on): wrong side → WAIT "TREND_AGAINST"; not warmed up → WAIT "TREND_WARMUP".
  Every signal records features.trend for research. Plans: filters.trend {vwap, ema200_5m, utbot_5m}: false;
  editable in My Settings.

## D45 — Squeeze Momentum switch (built, OFF) — 2026-11-06
- Results N (4 months real MGC, fixed 1.75R): Squeeze Momentum [LazyBear] rising in the trade direction on BOTH 5m
  and 15m: 43% / 54% win, +0.07R / +0.46R (45 trades) vs no filter 26% / 27% (−0.3R). Best of ~1,800 pairs → must be
  confirmed on the 7-year MGC.v.0 data before use.
- indicators/trend.py: _Squeeze (Decimal; momentum = linreg(close − avg(avg(hh20, ll20), sma20), 20, 0)), 15m bucket;
  direction()["squeeze_5m_15m"] = +1/−1 when 5m and 15m agree, 0 = disagree/flat (blocks), None = warming up.
  Switch filters.trend.squeeze_5m_15m (plans: false; My Settings; Risk page checkbox). Unit test vs an independent
  float reference on a random walk + gate test. Full test suite NOT yet re-run after this change (next session).

## D46 — Per-account automation override (master prompt §13 / line 267: "only more restrictive") — 2026-11-06
- Accounts page → Mode: inherit (global) | SEMI (approve each) | OFF (no automation). Never looser than the global mode
  (FULL is not an option; the API refuses it).
- OFF: automation and approvals never place trades on that account. SEMI: never auto-executed; in global FULL the
  other accounts still auto-execute and an approval is queued for the SEMI account(s) only.
- The manual ticket is the user's own explicit order for one account, so the override does not block it (all risk
  checks still apply). Code: automation/controller.py override_allows (unit-tested truth table) + 2 flow tests.

## D47 — Main strategy = trend-aligned 1.75R (user, 2026-11-06: "find the best intraday strategy … 1.75 R:R … still
## save it as the main strategy — TradingAgents (the main component) is not connected yet")
- Search: 7 years of real MGC (Databento MGC.v.0, May 2019 – Oct 2026), 5,768 filled setups, fixed 1.75R target,
  ≤3-filter combinations (indicators, score, C1/ATR, T2 R:R, stop size, structure, hours, side, weekday): picked on
  2019–2023 ONLY, judged on unseen 2024–2026 (docs/results/tools/best175.py, Results P).
- No combination reaches 50% on the unseen years; 70% at 1.75R is not reachable with these setups. Even a PERFECT
  daily bias (hindsight) lifts the chosen strategy only 41% → 49%.
- Previous plan (D36 1R/2–3R mix + D37 best hours) re-measured with the engine on Nov 2024 – Oct 2026: 391 trades,
  43% win, PF 0.87, −$1,201 (the 58% came from 22 sessions and did not hold).
- New main (all Pro/Flex plans): trade_plan rr_min 1.75 / rr_max 1.8 (1.8 so tick rounding never drops a target
  under 1.75R), filters.no_break_rr_cap null (no 1R targets), filters.trend utbot_5m + ema200_5m ON (trade only when
  both agree with the direction), MGC intraday_windows removed (D37 hours hurt on unseen years: 38% → 30%), MGC
  window 03:00–15:30 ET. Unchanged: every gate, score ≥ 60, C1 ≥ 0.4 ATR, risk tiers, Lucid rules, TradingAgents G2.
- Offline at 1.75R: 2019–2023 60 tr 43% −0.01R · 2024–2026 44 tr 39% −0.01R (≈ break-even before bias).
- ENGINE, Nov 2024 – Oct 2026 (not used to choose): 65 tr, 40% win, PF 1.34, +$594, +0.13R/trade (old plan −$1,201).
- Revert: git revert of the D47 commit (or switch the two trend filters off + rr 1.0/3.0 + no_break_rr_cap 1.0).

## D48 — Lock: no plan may aim below 1.75R (user: "why did it take 1R trades when it was supposed to be 1.75–3R")
- Root cause (Results Q): D36 lowered rr_min 1.75 → 1.0 in Pro/Flex 37 minutes after D35; D36b capped no-break
  setups at 1R. 84% of the old plan's trades aimed below 1.75R.
- app/config.py now refuses rr_min < 1.75 at load time; tests/unit/test_plans.py checks every shipped plan.
  Changing this needs an explicit user decision AND a code change — it can't happen through a plan file again.

## D49 — Main strategy = trend-aligned 1.5–2.5R on MGC + MNQ + MES (user 2026-11-06: "it can even be as low as 1.5
## — do 1.5–2.5"; "profit first + test MNQ/MES with the same rules, add a market only if profitable")
- All Pro/Flex plans: trade_plan rr_min 1.5 / rr_max 2.5 (target = min(T2, 2.5R), skip if T2 < 1.5R), no 1R targets,
  UT Bot 5m + EMA200 5m must agree (unchanged from D47). MNQ re-enabled (supersedes D42) and MES enabled (supersedes
  the D1 gate) — both with full windows 06:45–09:30 + 09:35–15:30 ET; D37 best hours removed everywhere. MGC 03:00–15:30.
- Config floor (D48) lowered to 1.5 at the user's request: no plan below 1.5R can load.
- Engine, same rules, NEUTRAL bias, Nov 2024 – Aug 2025 (first 10 months; full 2-year runs → Results R):
  MGC 33 tr 36% +$142 (D47 same months: 24 tr +$83) · MNQ 25 tr 44% +$696 · MES 14 tr 36% +$140 ·
  combined 72 tr 39% PF 1.45 +$978, ≈0.33 trades/day (2–4/day is NOT reachable profitably with these setups).
- TradingAgents (G2): ~85% of these trades already go with the day's direction (trend filters see it intraday); a
  55–60%-accurate daily bias adds ~+1–2 pts win rate but halves the trades and lowers profit. Option for the user
  (not applied): block only on strong ratings (BUY/SELL), map OVERWEIGHT/UNDERWEIGHT to NEUTRAL.
- MNQ + MES share the EQUITY_INDEX hedge lock (never opposite directions household-wide); 1 position per account.

## D50 — MGC + MNQ only, max 3 trades/day, TradingAgents blocks only on strong calls (user 2026-11-06)
- User: "MGC & MNQ", "at least 2 trades a day, maximum three", "Yes apply it" (bias), "only regular Pro and Flex".
- All Pro/Flex plans: MES off again; internal.max_trades_per_day 3 and low_risk_max_trades_per_day 3; bias.rating_map
  BUY → LONG_ONLY, SELL → SHORT_ONLY, OVERWEIGHT/HOLD/UNDERWEIGHT → NEUTRAL (both sides; neutral score ≥ 60).
  Plan picker/API offer only lucid_pro_* / lucid_flex_* (legacy Daily file kept for the test suite only).
- Strategy unchanged from D49 (1.5–2.5R, UT Bot 5m + EMA200 5m). Highest R:R: offline on 7 years MGC the result per
  trade is flat from 1.5R to 3R (1.5–3.0 marginally best, −0.01R offline ≈ +0.1R engine); above 3R too few setups.
- Trades/day reality (engine, Nov 2025 – Feb 2026, max 3/day): EVERY setup = MGC 0.80 + MNQ 0.72 ≈ 1.5/day,
  ≈ break-even (MGC −$215, MNQ +$210); D49-filtered 0.23/day and −$386 in this weak stretch. 2–3 profitable trades/day
  is not available from this setup type. Lucid audit (sub-agent): no rule broken; Flex DLL null and Pro DLL $600 are
  VERIFY — confirm with Lucid.

## D51 — MES eliminated; Lower risk mode 7 trades/day (user 2026-11-06: "Eliminate MES", "for low risk mode do 7")
- MES removed from every Pro/Flex plan (instrument, ES correlation group entry, SMT pair). Legacy Daily file (tests only)
  untouched. Normal mode max 3/day; Lower risk mode = its own limit, 7/day (risk/low_risk.py now uses
  max(normal, low_risk_max_trades_per_day) instead of min(2×normal, cap)).

## D52 — Final: MNQ takes every setup, MGC keeps the D49 trend filter (session 8 end)
- 1-year engine run, Nov 2025 – Oct 2026, Pro 25K rules, rr 1.5–2.5, max 3/day, NEUTRAL bias (data/{mgc1y,mnq1y}):
  MNQ every setup 169 tr 0.64/day 36% PF 1.12 +$562 · MNQ UT+EMA200 28 tr 46% PF 1.49 +$373 · MNQ structure break
  40 tr 45% PF 1.72 +$762 · MGC every setup 215 tr 30% −$870 · MGC UT+EMA200 27 tr 19% −$367 · both, every setup
  384 tr 1.46/day −$308. MGC was positive with D47/D49 on Nov 2024 – Oct 2025.
- New per-market switch instruments.<SYM>.trend_filters (default true). Pro/Flex: MNQ false (every setup), MGC true.
- The user's original spec (MNQ, 9:35–11:30 + 13:30–15:30, hard G4/G5, 2–3R, neutral score 75): 8 months → 9 trades
  (~1/month), 44% win, +$316 — profitable but almost never trades.
- 3+ profitable trades/day per account is not available from this setup type on MGC + MNQ (all setups = 1.46/day).

## D53 — TradingAgents + Vibe-Trading + OpenBB blended into the daily bias (user 2026-11-07)
- Vibe-Trading (HKUDS/Vibe-Trading, MIT, PyPI vibe-trading-ai 0.1.19 pinned) installed in its own venv `.venv-vt`
  (make vibetrading / start.py), run as a subprocess only. Connections card "Vibe-Trading": provider Claude
  (anthropic, LANGCHAIN_TEMPERATURE=1 for current Claude models) / Qwen (DashScope intl) / OpenRouter / OpenAI + key +
  optional model; Save & Test checks install + key. Runtime files in data/vibe-trading.
- Blend (app/bias/vibe_trading.blend, pure + tested): TradingAgents is the backbone (no rating = NO_TRADE). After it
  rates GLD/QQQ, Vibe-Trading gets OpenBB daily context (last, change %, 20-day average, 10 closes) and answers
  LONG/SHORT/NEUTRAL + confidence. If TradingAgents limits the day to one side and Vibe-Trading says the opposite with
  confidence ≥ 60 → NEUTRAL (both sides; intraday rules decide). It never blocks a side, sizes or places trades.
  Stored on the decision (raw "BUY·VT SHORT 85", reasoning + [Blend] note) and shown wherever the bias is shown.
- Why "can only unblock": on the final plan's real trades (last year) a daily direction barely matters for MNQ
  (perfect hindsight: with-the-day 35% vs against 36%); for MGC it matters (39% vs 14%). A wrong daily call that blocks
  a side costs more than a right one gains unless accuracy is very high; a 20-day-trend rule (OpenBB) flipped sign
  between the two years tested → not used as a hard rule.

## D54 — MNQ trades from 03:00 ET (user: "at least 1-2 trades a day", profitable)
1 year engine (Nov 2025–Oct 2026): MNQ 06:45 start 169 tr 0.64/day +$562 · 03:00 start 248 tr 0.94/day 35% PF 1.07
+$492 · 03:00 + 8-bar limit timeout 289 tr 1.09/day +$408 (not applied: global setting, untested on MGC).
With MGC (47 tr, +$215) ≈ 1.1 trades/day combined, profitable. AI-tool estimate (D53 model on these trades):
win rate +0 to +1 pt at 55–65% accuracy; Vibe-Trading blend recovers ~10 trades/$40 vs TradingAgents alone.
