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

## D55 — Strategy buttons: NOISE (verified) on, LunqFX + Opening-drive as buttons, MGC off, AI advisory ledger (user 2026-11-09)
- User (session 9): "do 1-4 and yes keep old strategy as a button and also … Opening-drive pullback, MNQ as a button
  too"; "add win rates/passing rates next to the buttons"; focus Lucid Pro 25K; "maximum trades … that don't break" it.
- Research: docs/results/2026-11-09_session9_strategy_research.md (7 agents, Databento 2019–2026, pick 2019–2023 /
  judge 2024–2026). Only the noise-area intraday momentum on MNQ passed: hourly checks + 1% emergency stop →
  held-out 440 trades, 45.0% win, +$25.81/trade, PF 1.33; Pro 25K sim 57% pass / 42% bust at 1 micro.
- `strategy:` section (config.StrategyCfg; My Settings keys strategy.lunqfx / strategy.noise / strategy.open_drive,
  versioned + rollback). Pro/Flex plans: noise ON, lunqfx OFF (its setups run in SHADOW, skip reason STRATEGY_OFF),
  open_drive OFF. Legacy Daily file unchanged (LunqFX only).
- NOISE: app/engine/noise.py (pure) + app/signals/strategy_service.py (from TradingView 1-minute heartbeat bars —
  non-negotiable #1 kept). Live engine reproduces the research exactly (parity test + full 2019–2026 replay:
  440 tr / 45.0% / PF 1.33). Warm-up: 10 stored RTH sessions. G1-style gate (window, calendar, news) per entry.
- Pillar changes approved by the user for these strategies only: §7 R:R window (NOISE exits by band/VWAP trail with a
  1% emergency stop + 10% safety TP; OPEN_DRIVE R:R ≈ 0.95), §6 confluence (signals not from LunqFX/MSO), §9 sizing
  (fixed 1 micro: no score tiers, no per-trade $ cap; the worst case at the emergency stop must still fit the DLL left
  and the MLL distance − kill distance — risk/checks.TradeLimits.fixed_contracts, 100% covered). Drawdown Guard and
  half-off defence do not apply to strategy trades. Exits are app-initiated (minimum hold D8 respected, retried).
- OPEN_DRIVE (not verified: in-sample PF 1.00) trades paper (is_sim) accounts only (PAPER_ONLY_STRATEGY).
- MGC disabled in every Pro/Flex plan (every gold strategy failed). MES stays out (it lowered Pro 25K results).
- AI bias (app/bias/ledger.py + policy.py): every daily call scored against the session's real RTH move from stored
  bars; ADVISORY until ≥ 30 scored calls with Wilson lower bound ≥ 70% (NOISE break-even) and Brier < 0.25; only then
  may a strongly-agreed call block the opposite NOISE side (BIAS_PROVEN_AGAINST). LunqFX G2 unchanged.
- UI: Strategy page → strategy buttons with tested win rate, Pro 25K pass/bust, PF, $/trade, trades/week, NOISE
  warm-up progress, AI ledger badge. Numbers are static research facts (app/engine/strategy_catalog.py).

## D56 (user 2026-11-09, session 10): AI-only strategy button — PAPER ONLY, default OFF
- `strategy.ai_bias` (Strategy page). Trades MNQ only when TradingAgents AND Vibe-Trading agree strongly on the day's side
  (bias/policy.combine agree_strong, ≈ 27% of days): entry at the 09:31 bar close, 0.5% broker stop, 10% safety TP,
  flat 16:00, 1 micro (AiBiasCfg). Paper (is_sim) accounts only (PAPER_ONLY_STRATEGY).
- Not back-testable (spec §15: no LLM runs on past dates / hindsight leakage). The card shows "—" for win/PF/$ and a
  hindsight 1-year ceiling by assumed accuracy (docs/results/session10/README.md §3: 100% +$267/tr … 50% +$8/tr).
  Real evidence = the calibration ledger.

## D57 (user 2026-11-09, session 10): drawdown-scaled emergency stop for NOISE / AI_BIAS instead of the $500 pause
- User: "lower risk as account goes into drawdown or whatever it takes to take more trades". Pure risk/checks.pretrade:
  fixed-size NOISE/AI_BIAS skip the pause floor; if the worst case at the plan's stop > strategy.drawdown_shrink (0.6) ×
  room (min(DLL left, equity − MLL − kill distance)), the stop is tightened to fit; tighter than
  strategy.drawdown_min_stop_pct (0.2%) → DRAWDOWN_TOO_DEEP. Kill switch, DLL, MLL, one-position, hedge lock unchanged.
  OPEN_DRIVE and LunqFX keep the pause floor. Set strategy.drawdown_shrink = null to restore the old pause.
- Evidence (README §7): app e2e Jul–Aug 2026 got worse (−$795 vs −$539: tightened stops hit). User reviewed and chose
  to keep it as is (2026-11-09). Also kept: NOISE 1% stop ($250 / $80–120 fixed stops tested on 1 year, §8–9: not
  better for the Pro 25K pass rate).

## D58 (user 2026-11-09, session 10): NOISE fixed $250 emergency stop + afternoon fade = MAIN strategy button
- NOISE emergency stop = fixed $250 per contract (noise_cfg.emergency_stop_usd, 124 pts on MNQ: (250 − $1 fee − 2 ticks
  slippage) / $2); null → the old 1% stop. Parity with the research script tested for both. 5 years: PF 1.36, no losing
  year, worst trade −$250. Grid caveat: NOISE $250 is a narrow peak (±$50 → ≈ 60% pass) — watch it live.
- PM_FADE (engine/pm_fade.py pure, strategy_service.run_pm_fade): 13:01–15:29 ET, close beyond VWAP ± 2.0 × population sd
  of (close − VWAP) today → fade at market, target = VWAP, fixed $250 stop, flat 15:55, 1 per day, only when NOISE has
  no PASS signal today; a too-near target (< 4 ticks) ends the day (TARGET_TOO_CLOSE), like research. PAPER accounts only.
  Live difference to research: research skips days NOISE trades at ANY time; live can only know "no NOISE trade yet"
  (a later NOISE signal is then blocked by the one-position rule while the fade is open).
- Strategy page: MAIN card first ("NOISE + Afternoon fade"), ON switches strategy.pm_fade + strategy.noise; ON in all
  Pro/Flex plans. Research: NOISE $250 + fade $250, 5 years 1 micro: +$25,345, PF 1.33, Pro 25K pass 66% / bust 32%.

## D59 (user 2026-11-09): projected weekly income on the Dashboard
- GET /api/income/projection?plan=&accounts=1–5&micros=1–5&cadence=5|10 (plan whitelisted to config/rules/lucid_*.yaml).
  Pure app/backtest/income_projection.py replays the MAIN strategy's 5-year research trades
  (app/backtest/data/main_strategy_5y.csv, shipped as package data) through the plan's own funded rules (MLL + lock, soft
  DLL, buffer, min request, cycle profit, caps, 40% consistency, max payouts, split; Flex 50% / profitable days / MLL lock).
  Dashboard card "Projected weekly income": per week, per payout, year average / median / middle half, max possible,
  ≥1-payout %, bust %, wait for the 1st payout, with plan / accounts / micros / weekly-or-2-weeks selectors.
  Labelled as a research projection (same trades on all accounts, no open-trade drawdown / news, no eval fees).

## D60 (user 2026-11-09): account growth in the income projection
- income_projection.size_for: base micros, +1 per `grow` $ of cushion above the trailing MLL beyond the first `grow`,
  max 5, shrinks again with the cushion; applied at the start of each session. Eval replay eval_path (plan's eval
  target / MLL / lock / soft DLL / consistency / profitable days). Dashboard card: "Account growth" selector.
  Projection only — the live sizing for NOISE / PM_FADE stays fixed (strategy.*_cfg.contracts) until the user decides.

## D62 (user 2026-11-09): Pro 150K sized at 3 micros for NOISE + afternoon fade
- lucid_pro_150k.yaml strategy.noise_cfg.contracts = 3, pm_fade_cfg.contracts = 3 ($250 stop is per contract → $750
  worst case per trade, 17% of the $4,500 MLL). Other plans stay 1 micro until the user picks their size.

## D62b (user 2026-11-09): Pro 150K = 6 micros, Pro 100K = 4 micros (replaces D62's 3 micros on 150K)
- User's explicit sizing. 5-year research at these sizes: eval 54% pass / 46% bust on both; 5 funded accounts: 150K
  $827 per 2 wk (median year $13,500, bust 54%), 100K $692 (median $9,228, bust 55%); worst trade = 33% of the MLL.
  Research-best alternatives shown to the user: 150K 4 micros + brake (cushion < 50% → 2): $952 / $23,706 / bust 27%;
  150K 3 micros; 100K 2 micros. Change back in config/rules/lucid_pro_{100k,150k}.yaml (strategy.*_cfg.contracts).

## D63 (2026-11-09): automatic size per account (replaces D62/D62b plan-wide micros)
- User: "set the different risk automatically for the different account sizes". Asked which table → no preference →
  research-best table (docs/results/session10/README.md §21–22), in every Pro/Flex plan under strategy.size_table:
  25K → 1 micro · 50K → 2 (cushion < 50% of MLL → 1) · 100K → 2 (< 30% → 1) · 150K → 4 (< 50% → 2).
- Pure app/risk/strategy_sizing.py (100% covered): tier = largest row ≤ the account's own size (Account.starting_balance,
  plan account_size when unknown); brake when cushion (equity − current MLL) < brake_below × the row's MLL. Applied to
  NOISE and PM_FADE in the controller before the pre-trade checks (which still cap at firm/internal max and check the
  worst case vs DLL / MLL room); audited as trade.auto_size. Other strategies keep their fixed contracts.
- Dashboard income card: "Micros each" defaults to "Auto (by account size)" and shows the chosen size + brake.
- Caveat: the app loads ONE plan for all accounts (MLL/DLL/payout rules). Accounts of different sizes are sized
  correctly, but their firm rules come from the loaded plan — select the plan that matches the accounts.

## D64 (user 2026-11-09): Regular / High-risk size profiles, drawdown brake LIVE
- Strategy page: two buttons (versioned My Settings strategy.high_risk). Regular = strategy.size_table: 25K 1 · 50K 2
  (< 50% → 1) · 100K 2 (< 30% → 1) · 150K 3 (< 50% → 2). High risk = strategy.size_table_high: 25K 1 · 50K 2 (< 50% → 1)
  · 100K 3 (< 50% → 1) · 150K 4 (< 50% → 2). Brake in both, applied live by risk/strategy_sizing (D63); audit
  trade.auto_size carries the profile. NOISE trailing exit and $250-per-micro stop unchanged. Dashboard income card:
  "Size profile" selector (active / Regular / High risk). Numbers: docs/results/session10/README.md §24.

## D65 (user 2026-11-09): Lucid Pro payouts — largest allowed, every 2–3 days
- Confirmed from Lucid's help page (user screenshots): no payout window, request any day once eligible; per cycle:
  profit ≥ $250/$500/$750/$1,000, largest day ≤ 40% of the cycle, balance stays ≥ buffer (MLL + $100), min $500.
- payouts.mode "max_eligible" (pure phases/payout_plan): balance − buffer, capped (1st / next), consistency per cycle;
  payouts.frequency "every_n_sessions": daily check at session_check_time (17:05 ET), ≥ min_sessions_between (2)
  sessions after the last processed payout, one open payout at a time. All Pro plans set to this (user: "try to get a
  payout every 2–3 days"). Option payouts.min_pct_of_cap (Payouts page "Wait for ≥ 50% of the cap") — agent study:
  most take-home on 100K / 150K Regular (150K: $1,003 per 2 wk vs $881 every 10 sessions, same bust); 25K / 50K /
  150K High do best with slower requests (every 10 / every 5). Lucid has no API: the app plans + notifies, the user
  requests in Lucid's dashboard; trading blocks while a submitted payout is pending (trade as if already deducted).

## D66 (user 2026-11-09): Evaluation Mode revised for the MAIN strategy (EVAL stage only)
- strategy.size_table_eval (Pro plans; Flex evals not studied → none): used for NOISE / PM_FADE when Evaluation Mode
  is effective for the account (risk/eval_mode.eval_mode_effective: EVAL stage only — non-negotiable 10).
  25K 1 · 50K 2 (< 50% → 1) — unchanged, every faster setting lost value · 100K 2 growing +1 per $1,200 cushion to 4
  (brake < 30% → 1) + day lock-in (stop for the day once today's profit ≥ 33% of the remaining target,
  EVAL_DAY_LOCK) · 150K 4 (brake < 50% → 2). Agent study (eval_speed_report.md): median sessions to pass 100K
  102 → 88, 150K 103 → 84, pass % 65 → 68 / 67 → 68, value per eval 105% / 102%. Original LunqFX keeps 10/12/14% tiers.

## D67 (user 2026-11-09): Pro payouts = maximum allowed, every 2 weeks
- User overrode the 2–3 day setting: lucid_pro_*.yaml payouts.min_sessions_between = 10 (10 trading days after the last
  processed payout), mode max_eligible, min_pct_of_cap null. Payouts page: "Days between payouts" select (10 / 5 / 3 / 2).
  Strategy, sizing, brake, stops, Evaluation Mode and the 40% consistency rule are untouched (payout planning only).
  Study numbers at this cadence (5 funded accts, per 2 wk · bust): 25K $317 · 57%, 50K $564 · 44%, 100K $643 · 26%,
  150K Regular $881 · 24%, 150K High $952 · 27%.

## D68 (user 2026-11-09): payout cadence per Pro size — 25K / 50K every 10 trading days, 100K / 150K every 5
- lucid_pro_100k / 150k payouts.min_sessions_between = 5 (weekly); 25K / 50K stay 10. Study (payout_timing_report.md,
  5 funded accts, per 2 wk · bust): 100K $643 · 26.0% → $702 · 27.5%; 150K Regular $881 · 23.5% → $954 · 24.5%; 150K High
  $952 · 26.8% → $1,064 · 27.9%. 25K / 50K every 5 would add ~9% income but +5–6 pts bust → kept at 10.

## D69 (user 2026-11-09): Pro 25K High-risk evaluation (sprint then protect) + fix of D66 growth
- strategy.size_table_eval_high (Pro plans): 25K evals trade 4 micros per signal and 1 micro once < 50% of the
  $1,250 target remains (taper_below_remaining 0.5 → taper_contracts 1; pure risk/strategy_sizing); 50K/100K/150K rows
  = the D66 eval rows. Used when Evaluation Mode is on (EVAL stage only) AND the High-risk button is on. Funded 25K stays
  1 micro (2 micros funded: bust 64–73%, income −25–35%). Agent study (eval25k_report.md, 593 starts, 120 sessions):
  1 micro 63% pass / 34% bust / median 36 sessions → B2 52% / 48% / 7 sessions; value per eval −17%.
  Best variant (30-min NOISE checks + 5 entries + opening-drive as eval-only extras: 58% / 42%, median 7, value −9%)
  NOT built: needs per-stage signals and opening-drive on EVAL accounts (D55: paper only) — needs user approval.
- BUG FIXED: the D66 controller built SizeTier without grow_per / max_contracts, so 100K eval growth was ignored.
  Test now asserts the growth reaches the sizing (test_eval_growth_row_is_applied_by_the_controller).

## D70 (user 2026-11-09/10): Pro 25K High-risk eval = 3 micros × $150 stop ($450 total), taper to 1 micro (replaces D69's 4 × $250)
- strategy.size_table_eval_high 25K row: contracts 3, stop_usd 150 (new per-row emergency stop, applied by the controller
  before the pre-trade checks), taper to 1 micro once < 50% of the $1,250 target remains. Regular eval stays 1 micro × $250.
- Agent study under the LIVE safety rules (eval25k_total_risk_report.md): 3 × $150 taper: pass 31% / 0% bust / 69%
  frozen, median 8 sessions to pass, 42 to a first pass counting restarts, value per eval $514 — vs 1 micro × $250 55% /
  35 / 59 / $913. Win rate falls with tighter stops (50% → 46% at $150). Total worst case $350–$750 all tie (pass 31–37%);
  $1,000 (4 × $250) is clearly worse. Frozen = the D57 shrink + DRAWDOWN_TOO_DEEP skip after a stop-out (no bust, no trading).
- Open decision for the user: relax the freeze for EVAL accounts (study assumption: 3 × $150 → 49% pass / 51% bust).

## D71 (user 2026-11-10): freeze with $50 left to the loss limit instead of $100 (Pro plans)
- internal.kill_switch_mll_distance = 50 in lucid_pro_{25k,50k,100k,150k}.yaml (others keep 100). It is the margin used by the
  kill switch (flatten + pause when equity − MLL ≤ distance), the pre-trade "NEAR_MLL" check and the room for the
  worst-case check / D57 stop-tightening → fewer frozen accounts, more room per trade, thinner safety margin
  (a slippage gap > $50 could now breach the limit). Measured (kill_distance_report.md): pass +0–4 pts, bust 0%, income +$6–45, win rate unchanged;
  extra risk only under a +$100 stop-out slippage stress (0.5–6% bust). PM_FADE is not tightened by D57 (controller passes shrink only for NOISE/AI_BIAS).

## D72 (user 2026-11-10): AI bias joins the strategy when live evaluation trading starts — record first, then switch on
- User chose "record, then switch on": from the first live EVAL session the daily AI call (TradingAgents + Vibe-Trading) is
  stored and scored in the calibration ledger (bias/ledger.py). It may BLOCK a NOISE entry only once proven
  (≥ 30 scored calls, Wilson lower bound ≥ 70%, Brier < 0.25, both tools agree strongly) — already wired in
  signals/strategy_service.py (ledger.may_block). Until then ADVISORY; no filter, no sizing change.
- Open: (a) the user's TradingAgents/LLM key is not connected — no calls are recorded until it is; (b) PM_FADE is not
  gated by the ledger (a fade trades against the intraday move, so its required accuracy is unknown — needs a study
  before wiring); (c) TradingAgents self-learning loop / OpenBB input still not built.

## D73 (study 2026-11-10, awaiting user): PM_FADE under D57 stop-shrink — measured, NOT adopted
- User: "yes, especially if it helps". Measured (docs/results/session11/pm_fade_d57_study.md): covering PM_FADE lowers eval
  pass in 2021–23 on every plan (−4 to −8 pts on 50K+), no gain in 2024–26, funded income never higher, bust 0% both.
  Fails the held-out rule → controller.py keeps shrink for NOISE/AI_BIAS only; PM_FADE keeps the pause floor + $250 stop.

## D74 (user 2026-11-10): AI-bias SIZING "version B" on 100K/150K — built, gated by the live record
- Study: docs/results/session11/ai_bias_sizing_study.md (70 seeds/cell; bust 0% everywhere). B = agree +1 micro (cap = tier base + 1),
  disagree −1 (min 1), never blocks. Pays on 100K/150K at ≥ ~60% accuracy; loses on 25K at every accuracy; 2024–26 gains are 2–3× smaller.
- Code: strategy.ai_sizing (default on), ai_sizing_min_account 100000, ai_sizing_min_accuracy 0.60, ai_sizing_min_calls 60;
  risk/strategy_sizing.bias_size (pure), bias/ledger.sizing_call (0 until ≥ 60 scored calls with observed hit rate ≥ 60%, Brier < 0.25),
  wired in automation/controller.py after auto_contracts. Audit "trade.auto_size" logs ai_call + contracts_final.
  DLL / D57 / worst-case / firm-max checks still apply after it. 25K and 50K never change. No calls recorded yet (AI key not connected) → no effect today.
- Note: observed hit rate over 60 calls is noisy (a true 55% tool can pass ~25% of the time); the study shows a 55% tool roughly breaks even on 100K, so the downside is small.

## D75 (studies 2026-11-10, AWAITING USER — nothing built): final-push proposals
- P1 NOISE profit lock (+100 pt → stop to entry +10 pt; a locked stop-out ends NOISE for the day). P2 reset frozen evals at once
  (25K < $150, 100K < $300, 150K < $225). P3 25K High-risk recover mode. P4 cushion sizing on funded (fewer dead accounts, less income).
  Rejected: second market MES/MYM/M2K, 30-min NOISE checks, extra entries, looser D57. Numbers: docs/results/session11/README.md.

## D76 (study 2026-11-10): order blocks + SMT (MNQ vs MES) on NOISE / PM_FADE — built, shadow only, NOT enabled
- User asked for OB + SMT as FILTER and as OB STOP ANCHOR. Built pure indicators (order_block.py, smt.py), engine/structure_filter.py and
  strategy.structure_filters (enabled=false, shadow_log=true). Filter can only block; anchor only if tighter than the fixed stop and never applied live.
- Measured on 5y MNQ/MES (pick 2021-23, judge 2024-26; docs/results/session12/README.md): baseline 48.6% / $9,363 IS, 51.0% / $15,982 HO.
  No variant improved held-out win rate and profit meaningfully (best IS pick: HO win 50.7%, +$292 but win rate down); SMT cuts trades 17-84% and profit
  23-100%; OB anchors cut win rate 1-9 pts and profit 2-25%. Stays OFF. LunqFX results are in a separate report by another agent.
- LunqFX (study 2026-11-10, docs/results/session12/LUNQFX.md): engine PASS setups (shadow plans, lucid_pro_25k, 22 sampled months 2021-11..2026-10,
  R:R 1.75-3.0, 1 micro). Baseline IS 54.7% / -$11,555 (508), HO 53.9% / -$27,322 (675). In-sample pick OB filter (5m OB, body 1.0 ATR, block within
  60 pts of an opposing OB): IS 65.9% / +$4,736 (440), HO 62.9% / -$5,724 (603) — win rate and profit both better held-out, but still a loss.
  SMT hurts (HO win 43-50%, all worse). OB stop anchor: no effect (a tighter OB stop almost never keeps R:R <= 3.0). Wired as
  strategy.lunqfx_structure (enabled=false, anchor_stop=false, shadow_log=true; engine/lunq_structure.py, signals/service.py; tests). Recommendation:
  keep OFF — LunqFX stays a SHADOW strategy; the OB filter is the first candidate if LunqFX is ever revisited (needs the full 60-month run).

## D77 (study 2026-11-10): gate chain for NOISE + PM_FADE re-measured — no gate added, AI threshold made a config value
- Gates for these two strategies = G1 + (optional OB/SMT/MSO-divergence structure filter) + AI ledger + pillar risk (G8). G2/G3/G5/G7/score belong to LunqFX. Pillars/risk untouched.
- Measured on 5y MNQ (pick 2021-23, judge 2024-26; docs/results/session13/README.md): window/hour/cooldown/band re-tuning, Big Beluga MSO structure, MSO divergence, LunqFX
  fractal agreement: none improves held-out win rate AND profit (fractal/structure raise win rate only by cutting 35-55% of trades and most profit). All stay OFF.
- Finding: the earlier-fade gain is hindsight (the fade's NOISE-free-day set uses the whole day). Causal rule ("no NOISE signal yet") costs about 25% of profit and +10 pts bust
  vs the validated numbers; the app's projections are optimistic by that much (open: rebuild the stream causally).
- AI gate: ADVISORY by default; threshold now config `strategy.ai_gate_min_accuracy` (default 0.70, range 0.55-0.95). Simulated 55-70% accuracy: a light block (~5-12% of trades)
  moves held-out win rate by at most +0.5 pt with mixed profit/bust; heavy blocks cut trades 20-45% and profit. No real ledger data exists (AI key not connected).
- Built: `strategy.structure_filters.mso_div_filter` (OFF), `/api/strategies.gate_chain`, GateChain UI on the Strategy page.

## D78 (user 2026-11-10, session 13): AI ledger fast-track backfill + live-ledger fixes
- Backfill (Strategy page button, /api/ai-ledger/backfill): TradingAgents + Vibe-Trading run as-of each of the last N (default
  60) MNQ sessions through the existing subprocess runners; stored as proxy `QQQ.BF` / version `BACKFILL:`; shown only as
  "estimate (possible hindsight)"; NEVER counts toward the D55 live proof (all live readers filter on the plain proxy).
  Rate-limited, stops on 3 errors in a row with banner, cancellable, resumable.
- Live ledger: failed proxies retried every 30 min until 09:25 ET; Vibe-Trading failure warns; scoring tolerant to missing edge
  bars; today scored after 16:01 ET; 30-day coverage list; "calls still needed" for the proof. Bias time is 02:40 ET (D34).
- Details: docs/results/session13/AI_LEDGER.md.

## D79 (user 2026-11-10, session 13): permanent webhook URL via the user's free ngrok static domain
- Connections card "ngrok (permanent webhook URL)": authtoken (secret, encrypted, write-only) + static domain (validated *.ngrok-free.app etc.), Test button, status. Links: signup, Domains, Your Authtoken.
- Desktop app (PAYTIENCE_TUNNEL_AUTOSTART): app/tunnel.py downloads pinned ngrok 3.18.4 (sha256-checked) into paytience-data/tools, writes the authtoken to a 0600 ngrok.yml (never on the command line, every output line redacted), runs `ngrok http --url=<domain> 8000`, restarts it if it dies.
- Fallback when ngrok is not set up or keeps failing: pinned cloudflared 2025.9.1 quick tunnel + notification + Connections banner ("temporary link"); ngrok is retried every 5 min. A dead tunnel raises "No public webhook URL" (no silent failure).
- Connections shows https://<domain>/api/webhook/tradingview with "permanent — set once in TradingView" when ngrok is active. Only on Connections (not Dashboard).

D79 addendum (session 13): TradingView connected (webhook secret in indicator + CME real-time data ~$7/mo); user stays PAPER for now. Broker bridge options (not built): CrossTrade Pro ~$49/mo = supported safe option (position read-back required by live gate); Tradovate API add-on ~$30/mo only if Lucid allows (ask); TradersPost cannot read back positions. ngrok path untested against a real account.

## D80 (user 2026-11-10, session 13): UI sync with D72-D79 (no strategy, risk or projection change)
- Strategy page gate chain (/api/strategies.gate_chain) now lists exactly what applies to NOISE + PM fade: G1, pillar risk checks, OB/SMT filter (OFF, shadow-logged), MSO divergence (OFF),
  AI gate (ADVISORY, threshold strategy.ai_gate_min_accuracy editable 55-95%), and G2/G3/G4/G5/G7/fractal marked "LunqFX only". Each row: state + plain reason incl. tested result.
- Toggles added to My Settings allow-list (validated flow): strategy.structure_filters.{enabled,ob_filter,smt_filter,mso_div_filter,shadow_log}, strategy.lunqfx_structure.{enabled,anchor_stop,shadow_log},
  strategy.ai_gate_min_accuracy. Unproven toggles show a gold "unproven" badge + confirm before ON. New Strategy-page card for LunqFX D76 flags.
- Connections: CrossTrade note (needed for automated orders, reads back positions); TradersPost REMOVED from the app entirely (user: registry card, adapter, tests; live_gate broker_reads_back unchanged); ngrok card already existed (D79).
- Dashboard + Today: notice that projections assume the hindsight fade rule (D77, ~25% optimistic) until the causal rebuild is decided. Risk page: stale D52 main-strategy text replaced.

## D81 (user-approved item 14, session 14 2026-11-10): projections rebuilt on the CAUSAL afternoon-fade rule
- `main_strategy_5y.csv` now = NOISE + fade where the fade (13:00-15:29) trades only if no NOISE signal fired yet (live rule); columns d,pnl,strategy,entry_time,causal. Old stream kept as `main_strategy_5y_hindsight.csv`. Test: `tests/unit/test_main_strategy_causal.py`.
- Measured (docs/results/session14/causal_projections.md): 5y profit $25.3k -> $18.5k (-27%), win 50.0 -> 48.8%, fade alone PF 0.99 (-$432); Dashboard funded income -40..-47%, eval pass -8..-21 pts (25K Regular 56 -> 45%).
- Decisions D70 / D71 / D73 / D74 / D75-P3 hold; D75-P2 reset threshold for 100K no longer safe (IS pass -7 pts) - do not use it. Open: the fade has no demonstrated edge as live trades it (separate decision); P1 profit lock and P4 cushion sizing not re-run; paper-day parity test (item 14 step 5) not done.


## D82 (user 2026-11-10, "Yes build abc", session 16): NOISE strategy presets + profit lock
- User approved three presets (Strategy page selector, My Settings key `strategy.preset`, definitions in `config/strategy_presets.yaml`):
  A "Pro 25K classic" (NOISE $250 stop + afternoon fade ON, 1 micro; 63%/36%, Session 10), B "Pro 100K low risk" (NOISE + fade, 3 micros,
  1 micro while cushion < 50% of the loss limit; 63%/22%, Session 10) - both carry the badge "older, likely optimistic (fade measured with
  hindsight ~27% rosy; honest ~57%/42%)" - and C "Pro 150K low risk" (recommended; NOISE + D75-P1 profit lock, fade OFF, 3 micros, 1 micro
  while cushion < $2,250; 77%/18%, held-out 2024-26, Session 15).
- A preset overlays ONLY noise_cfg (stop $, profit lock), strategy.noise / pm_fade and the size tables (size_table, size_table_high) before
  validation. Kill switch, risk checks, DLL/MLL, consistency, Evaluation-Mode tables and every other safety rule are untouched (tested).
  Default = no preset ("custom", the plan file's own values); C is shown as recommended and preselected in the UI but is applied only on click.
  Selecting is a versioned, audited My Settings save; mode stays PAPER (live gates unchanged).
- Profit lock (D75-P1) is new code: `management/profit_lock.py` (pure, Decimal), wired in the order manager: at +100 pt the stop of every open
  leg moves to entry +10 pt (ratchet; stop-modify failure = existing flatten + pause); a locked-stop exit is booked as `PROFIT_LOCK` and sets
  `lock_exit` on the NOISE signal, which stops new NOISE entries that day. Config `noise_cfg.profit_lock_trigger_pts / profit_lock_pts`.
- Known gaps: the preset size row applies to every account regardless of its size (UI warns when the plan size differs); D74 AI sizing (+1 micro,
  proven ledger only) still applies on top. Details + tests: docs/results/session16/presets_build.md.

## D83 (user 2026-11-10, session 16): "AI Duo" strategy button (beside ai_bias, PAPER only, default OFF)
- Side: TradingAgents AND Vibe-Trading must both pick the same side (TA BUY/SELL, VT same side, confidence >= 60). Vibe-Trading only gives an
  opinion (LONG/SHORT/NEUTRAL + confidence), never trades. Any disagreement, failure, NEUTRAL or weak call = no trade with a reason code
  (AI_MISSING, AI_TA_MISSING, AI_VT_MISSING, AI_NEUTRAL, AI_DISAGREE, AI_NOT_STRONG).
- Entry: first 5-minute VWAP pullback close in the AI direction inside the entry window 03:00 (London open) -> 11:30 ET (My Settings
  `strategy.ai_duo_cfg.window_start/window_end`; 09:30-09:35 stays excluded; session VWAP anchored at window_start). Stop = beyond the pullback swing, capped at
  the NOISE dollar stop (config); target 2.0R (config refuses < 1.5R); fixed 1 micro. Markets MNQ and MGC (`strategy.ai_duo_cfg.markets`, AI Duo only; NOISE stays MNQ;
  an AI call is also produced for the MGC proxy GLD while Duo is on). Each market decides once a day: one trade or one SKIP row (direction NONE) with its code,
  plus an `ai_duo.decision` audit entry; `ledger.duo_decisions` / Strategy page list them.
- Hedge lock unchanged (household, EQUITY_INDEX / METALS): NOISE open opposite -> Duo Skip HEDGE_LOCK; Duo open first -> NOISE Skip HEDGE_LOCK; same-bar tie -> NOISE wins
  (it runs first); same direction allowed and flagged `agrees_with_noise`. A stopped-out signal no longer holds the lock. MGC never clashes with NOISE (different group).
- PAPER only: `paper_only` is `Literal[True]` in config and the controller refuses AI_DUO on any non-simulator account (PAPER_ONLY_STRATEGY). Untested strategy (LLM calls
  cannot be back-tested): no historical win rate is claimed. Details: docs/results/session16/ai_duo_build.md.

## D83 addendum (user 2026-11-10): AI Duo is ONE button for MNQ and MGC; per-market windows and accounts
- Windows per market in config (`strategy.ai_duo_cfg.windows`, editable in My Settings): MGC 03:00-11:30 ET (London open), MNQ 08:00-12:00 (user changed 08:30 to 08:00 the same day) ET. 09:30-09:35 stays excluded, news blackout and every gate unchanged.
- Per-market account choice (`strategy.ai_duo_cfg.accounts`, Account ids): MGC and MNQ can run on different accounts; an unassigned market avoids accounts assigned to the other market. Entering an assigned account that is not armed/selected is reported (DUO_ASSIGNED_ACCOUNT_UNAVAILABLE).
- Reward-to-risk: 1:2 preferred (target 2.0R, config), minimum 1:1.5 (config refuses lower); a setup between 1.5R and 2R is allowed and tagged "below preferred 2R" in the ledger/UI; below 1.5R = Skip RR_BELOW_MIN.

## D84 (user 2026-11-10, session 16): TradingAgents MGC research setups = part of the AI Duo button
- `ta_runner.py` gets a `research` command (still ONLY in `.venv-ta`, subprocess JSON, reusing the existing TradingAgents connection/key): gold drivers (USD/DXY, real yields, Fed/CPI calendar, risk sentiment, trend/levels) -> structured setup {side LONG/SHORT/NONE, confidence, entry zone, invalidation, target, valid-until, optional lock_price, reasons}.
- Pure `engine/ta_mgc.py` validates it and builds the plan with the same section 7 builder (stop beyond the invalidation, rr 1.5-3.0 from config, 2R preferred tag, STOP_TOO_WIDE vs the NOISE dollar stop). Vibe-Trading (existing `.venv-vt` connection) must agree on the side: ONE shared agreement function `ai_duo.agree` is used by AI Duo (MNQ/MGC daily call) and by the research setup. Every refusal is a reason code (RESEARCH_NO_TRADE, SETUP_*, AI_*, RR_BELOW_MIN, STOP_TOO_WIDE, SETUP_EXPIRED, NO_ENTRY_IN_ZONE, RESEARCH_FAILED ...).
- Each research report + Vibe opinion + decision is stored in the bias ledger (`BiasDecision` proxy `GLD.RS`, never counted toward the live accuracy proof) and shown on the Strategy page. Job runs 02:45 ET only while AI Duo is on with MGC; no key = "AI key not connected", nothing runs. PAPER only; default OFF. Details: docs/results/session16/ta_mgc_build.md. The runner's LLM step is unverified against the real TradingAgents package (not installable here) and is tested with fakes.

## D85 (user 2026-11-10, session 16): AI Duo on 150K - several positions, $250 cap, aggregate risk, trade management
- OVERRIDES section 1.7 / CLAUDE.md "max 1 open position per account" for AI Duo on accounts of size >= `big_account_size` (150,000) ONLY; every other account size and every other strategy stays at max 1 (tested). Config values: `max_open_positions` 4, `max_qty` 4 (a cap), `max_risk_usd` 250, `big_account_size`. Relayed to the build agent as the user's explicit approval ("Both"); the strategy is PAPER only.
- Safety kept: hedge lock unchanged (household, never opposite in the group); NEW aggregate check in `risk/checks.py`: open-position risk (stop distance x qty + fees + slippage) + new trade + DLL margin must fit the DLL left and the MLL kill buffer, else qty is reduced or Skip AGGREGATE_RISK_EXCEEDS_LIMITS; per-trade cap $250 (qty reduced to what fits; not even 1 micro -> STOP_TOO_WIDE), all account sizes; kill switch flattens ALL positions (tested with two open); every position keeps its own stop bracket; sizing still comes from the normal risk engine (fixed size path + drawdown scale + consistency + worst-case checks), 4 is a cap.
- Trade management for every Duo position, independently (new pure `management/trade_manage.py`, reusing `ratchet`, `runner_stop` and the profit-lock rule): break-even at +1R (entry + fee_cover_ticks), profit lock +100 pt -> entry +50 pt on MNQ (MGC `13 -> 6.5`, marked # VERIFY in config, proportional by price, unconfirmed; NOISE keeps its tested +100 -> +10), or the AI setup's own `lock_price` instead when given; trailing stop 1R behind from +1.5R. Ratchet only, never through the market (capped to the nearest valid tick under/over the current price), the rule that chose the level is logged (`trade.stop_moved` audit). Cushion brake (reused `auto_contracts`): 1 micro while cushion < 50% of the loss limit. Drawdown Guard 2-bracket mode where its own auto rule turns it on. Protective exits never wait.

## D85 addendum (user 2026-11-10, session 16): MGC step trail replaces the guessed 13 -> 6.5 pt lock
- AI Duo on MGC no longer uses the `13 -> 6.5` profit lock (it was an unconfirmed # VERIFY guess, removed). MGC now uses a STEP TRAIL: for every +60 ticks of open (best) profit the stop is raised 20 ticks above the ORIGINAL stop (n steps = n x 20 ticks; 59 ticks = no move, 60 = +20, 120 = +40, 180 = +60). Config `strategy.ai_duo_cfg.step_trail` `{MGC: [60, 20]}` = (step_ticks, raise_ticks): user-set values, no VERIFY. MNQ keeps its `lock_pts` +100 -> +50.
- Ratchet only, tick-rounded (Decimal), never at or through the current price (nearest valid tick behind it, logged `STEP_TRAIL+MARKET_CAP`); protective stop modify, never waits. If the AI setup gives its own lock level (`lock_price`) it is used INSTEAD of the step trail once price has passed that level (until then the step trail holds, so the position is never less protected); still ratchet-only. The rule that chose the level (`BREAKEVEN` / `STEP_TRAIL` / `LOCK_AI` / `TRAIL`) is logged in the `trade.stop_moved` audit entry. $250 max risk per trade with micros is unchanged. Break-even at +1R and the 1.5R/1R trail stay.
- Review fixes (docs/results/session16/review.md): NOISE profit lock capped behind the market; AI lock level only once passed; pending entries count in the aggregate risk; one flatten fill split by quantity across several positions on an account.

## D86 — AI Duo back to 09:36–11:30 ET for MNQ and MGC (user, 2026-11-10)
User: "Go back to best hours". The session 16 window study (docs/results/session16/ai_duo_window) found 03:00 starts lose
the edge (70%-accuracy bound, 2024–26: 09:36–11:30 +$18,993 PF 1.40 vs 03:00–11:30 +$899 PF 1.03). Default
strategy.ai_duo_cfg.windows = MGC 09:36–11:30, MNQ 09:36–11:30 (still editable in settings). Supersedes the D83 addendum hours.

## D87 (user 2026-11-10, "yes implement all"; consistency reading confirmed: best day <= 40% of total profit / of target): "Fast Evaluation" option
- EVAL stage ONLY (non-negotiable 10; pure check `risk/fast_eval.fast_eval_effective`, tests for FUNDED/LIVE), master switch default OFF, PAPER like everything else. Enable = Impact Preview + typed "ENABLE FAST EVALUATION" (same pattern as Evaluation Mode); disable = one click. Risk page card "Paytience · Fast Evaluation".
- Four mechanisms, each with its own config switch + parameters (`fast_eval:` block in config/rules/*.yaml, editable keys `fast_eval.*` in My Settings): (1) cushion size ladder, (2) day-cap harvesting (tighten-only), (3) early-evaluation tier, (4) quality-day filter. Size never rises after a loss; no martingale, no pace escalation.
- Defaults from the study (docs/results/session16/fast_eval/README.md, reading A, held-out, SIMULATED/unproven): Flex 150K ladder 1->2 micros while cushion >= 50% of the loss limit (68%/1% -> 87%/8% pass/bust, median 505 -> 275 sessions); Flex 50K skip the day after a losing day (40%/23% -> 46%/28%, slower 154 -> 205); 100K plain 1 micro; 25K none ("no safe speed-up found - 25K busts 55-60%"). Harvesting and early tier: no measured benefit -> available, OFF. Pro plans: not studied, all OFF.
- Unchanged: kill switch, DLL/MLL, day stops (only tightened), pause floor, hedge/news/flat rules, gates, R:R, consistency cap. Numbers shown in the preview live in config/fast_eval_study.yaml.
- Build notes: docs/results/session16/fast_eval_build.md.

## D88 — Token-based auto-update for the Windows desktop app (user approved, 2026-11-10)
- New optional connection "GitHub (app updates)": read-only fine-grained token (Contents: Read-only on
  paysh-wrap/opogabuuga), encrypted like every key, write-only, never logged or returned. The app works without it.
- The workflow writes desktop/version.json (commit SHA + build time, bundled via the spec) and puts `commit: <sha>`
  in the `desktop-latest` release body. Version shown on Settings → App version.
- Check on start (desktop app + token only) and via "Check for updates". Newer = different commit AND asset built
  after this build. Banner "Update available — Install now?"; nothing installs without the user's click.
- Install: blocked while any position is open, any account is armed or automation is not OFF (reason shown).
  Download via asset API → paytience-data/updates/, verify size + sha256 (GitHub digest), extract to staging, write
  apply-update.bat: waits for Paytience to exit, moves Paytience.exe + _internal to updates/old-<ts>, moves the new
  files in (paytience-data never touched), starts the new app, waits ≤ 120 s for healthy.flag (written by the new
  app on its first healthy start, which also deletes old-*), else restores the backup and starts the old version.
  Every step logged (updates/update.log); any failure = banner + log + notify + old version kept.
- Code: backend/app/updater.py, backend/app/api/updates.py, frontend/src/components/UpdatePanel.tsx,
  tests backend/tests/integration/test_updater.py.

## D89 (user-approved 2026-11-11, session 17): Lucid OFFICIAL payout-consistency rule + N6 fix
- Source: Lucid support "Consistency Percentage" (2026-08-26). LucidPro FUNDED only. It is payout ELIGIBILITY, not a breach: largest single-day profit / account profit since the last payout must be <= limit to REQUEST a payout; the cycle starts again after every processed payout; not applied on LIVE; Pro EVAL, Flex and Daily are unchanged (their yaml has no `funded.payout_consistency`).
- Numbers live only in the Pro rules yaml (`funded.payout_consistency: {pct: 40, legacy_pct: 35, legacy_cutoff: 2025-11-28T15:00:00-05:00}`, generated by scripts/make_plans.py, validated by `PayoutConsistencyCfg`: tz-aware cutoff, legacy not looser than pct).
- Per-account purchased/reset date (`accounts.purchased_at`, migration c5d9e3f7a2b4; Accounts page date field, audited PATCH). Date on or before the cutoff -> 35%; after -> 40%; UNKNOWN -> stricter 35% and a gold VERIFY badge until it is entered.
- Pure `risk/consistency.py`: `payout_consistency` (cycle profit = sum of day profits incl. losing days; "exactly at the limit" counts as eligible = VERIFY; `needed_cycle_profit` rounds UP to a whole dollar so it is never understated; `still_needed`), `payout_limit`, `payout_rule_applies` (FUNDED only), plain-text explanation. Service `payouts/service.py`: cycle = since last processed payout (else stage start), `plan_for` returns CONSISTENCY (no payout proposed) while unmet, and `POST /api/payouts/{id}/status -> submitted` is refused with 409 while unmet. "What is still needed" on Payouts (card, `GET /api/payouts/consistency`), Dashboard (per account) and Accounts.
- N6: for fixed-size strategy trades (NOISE etc.) the pre-entry "TP reward must fit the cap" fit is skipped (the far safety TP is not the exit, so it rejected every entry); instead no entry opens at/after the cap or the day stop, and the watchdog (`Controller._monitor`) flattens the account's strategy trades as soon as today's realised + open profit reaches the consistency day stop (`live_day_stop_hit`, uses the harvest-tightened limit; protective, never waits). No cap was loosened: LunqFX trades keep the TP-reward fit.
- Assumptions (VERIFY with Lucid): equality at the limit is eligible; cycle = closed trades after the last processed payout, grouped by CME session date; the Accounts date picker stores 12:00 ET of the chosen day (a purchase on the cutoff day itself therefore counts as <= cutoff = stricter 35%).

## D90 (user-approved 2026-11-11, session 17): Telegram removed everywhere (Discord stays)
- Removed the Telegram connection (registry entry, tester, tests, UI sample text, README mention). Discord (webhook URL) is unchanged. Migration d6e0f4a8b3c5 deletes any stored Telegram credential from `api_credentials` (tested; Discord rows kept). Historical docs (docs/PHASE0.md Q&A, MASTER_PROMPT_v9.2.md, HANDOFF.md, older results) still mention it as history and were not rewritten. No other code path sent Telegram messages.

## D91 (user-approved 2026-11-11, session 17): BigBeluga MSO removed from the default engine (config switch `indicators.mso.enabled`, default false)
- `indicators.mso.enabled` (rules yaml, `MsoCfg`, default false; all 8 offered Pro/Flex plans say false, `make_plans.py` writes false). Off means: gates G4 (MSO structure), G5 (CHoCH/BoS) and G6 (opposing divergence) are NOT evaluated and do not appear (engine, stored gate chain, Strategy page, gate chain card); the score drops its three MSO components (structure after sweep, oscillator strength, HTF MSO agrees) from BOTH earned and maximum points, so it is renormalised to 100 over the rest (CISD before C2 close, own T2 rate, bias; session-open/SMT unchanged); the D36 "no structure break -> closer target" cap and the MSO divergence veto of the structure filter (D77) and the half-off defence (MSO trend flip + CHoCH) are inert.
- ICT/LunqFX fractal model stays. LunqFX without MSO is UNTESTED -> `signals/service.py` evaluates it as SHADOW only whenever MSO is off, even with the LunqFX button ON (`skip_reason MSO_DISABLED`, never PASS, never an order; execute refuses it; the Strategy page shows "SHADOW ONLY"). NOISE / PM_FADE / AI Duo never used MSO and are unchanged.
- Heartbeats never required an `mso` snapshot (optional field); tested: accepted, and MSO events sent by an old TradingView alert are still accepted but cannot change any outcome while off.
- The legacy `lucid_daily_25k.yaml` (not offered; test baseline) keeps `enabled: true` so the existing MSO regression tests still run unchanged; new tests cover the disabled path. The Pine bridge and the backtest MSO engine are left in place (opt-in path); with MSO off a backtest of LunqFX yields shadow-only signals.

## D92 (user-approved 2026-11-11, session 17): Strategy button "NOISE + AI Duo — split risk 50/50" (default OFF)
- Setting `strategy.noise_ai_split` (default false, versioned My Settings key) + `strategy.noise_ai_split_share` 0.5 (plan file, validated 0 < share <= 0.5). The card turns NOISE and AI Duo on with it (like the MAIN card). It is "in effect" only while the flag AND `strategy.noise` AND `strategy.ai_duo` are on (pure `risk/split_risk.split_active`); NOISE alone stays the main strategy and is unchanged while the button is off.
- Per side (NOISE, AI_DUO): contracts = half, rounded DOWN, minimum 1 micro (`split_contracts`, applied after every other size rule incl. tables, brakes, AI sizing, Fast Eval and the 150K Duo size), and a per-side daily loss budget = half of the account DLL (`split_budget`): realised loss today of THAT strategy (from its plan rows, `state.strategy_day_pnl`; profits never add room) + the risk still open on its positions + the new trade's worst case + the DLL safety margin must fit it, else `SPLIT_BUDGET_EXCEEDED` (new `TradeLimits.side_budget_left`, check "split_budget" in `pretrade`). Tighten-only: every other check (DLL/MLL, kill distance, consistency, day stops, max positions, news, flat) still runs; each use is audited (`trade.split_risk`).
- AI Duo stays PAPER only: `ai_duo_cfg.paper_only` is still `Literal[True]` and the controller refuses AI_DUO on any non-simulator account (`PAPER_ONLY_STRATEGY`) with the split on (tested). Hedge lock unchanged (tested: NOISE long open -> Duo short = HEDGE_LOCK).
- Assumptions (VERIFY with the user): the split is applied to NOISE on every account, also non-paper ones where AI Duo cannot trade (NOISE then simply runs at half size / half DLL budget: conservative); an account without a DLL gets the half size but no budget check; the budget is half of the account's own DLL limit (not of today's remaining DLL). Not measured: the AI half cannot be back-tested, so the card shows no win/pass numbers.
## D93 (user-approved 2026-11-11, session 17): "Mission control" UI look + mandatory-connection highlight and checklist
- Look: docs/results/session17/ui_concepts/mission.html applied app-wide by one stylesheet loaded after index.css
  (frontend/src/mission.css, scoped by the `.mission` class on Layout): mono uppercase gold page labels rendered as
  "PAYTIENCE · <PAGE>", every card a rounded mission tile, pill nav, wider canvas (1500 px), phone bottom dock
  (components/MobileDock.tsx; the full scrolling nav stays). Dashboard hero = components/MissionBento.tsx (cushion gauge
  and day P&L vs DLL for the account closest to its drawdown limit, safety tile linking to Automation, today, balance)
  from /api/dashboard only. Strategy and all other pages get the look through the shared CSS (no page rewrites).
- §18 kept: the concept's grey "muted" text became blueLight; red/green only as the small status dots; P&L keeps ▲/▼ and
  sign. New theme.ts tokens: `mandatory` (#FFC93C, gold family, AA on every surface, tested) and `mission.*` surfaces
  (backgrounds only). No web fonts are downloaded (offline desktop/WebView): font stacks fall back to system fonts.
- Mandatory to trade an EVAL or LIVE account (standout `mandatory` colour + "MANDATORY · EVAL/LIVE" tag on the
  Connections cards; lib/mandatory.ts): broker order route (CrossTrade or Tradovate — Lucid has no API, §1.3), TradingView
  webhook heartbeat (only live signal source, §1.1), webhook secret, public HTTPS URL (ngrok, or own tunnel / Cloudflare
  fallback), economic calendar (§15 "no calendar = no trading"), external-positions attestation (§1.11), clock sync
  (pre-flight < 2 s) and the last pre-flight result (server refuses SEMI/FULL without it). Optional, normal colour:
  Discord/notifications, AI keys (TradingAgents, Vibe-Trading, Alpha Vantage, FRED), Trading-R1, Databento/OpenBB/Fincept,
  Lucid link, GitHub updates.
- "Mandatory connection checklist" (components/MandatoryChecklist.tsx) on Dashboard and Connections, from
  /api/connections, /api/webhook/status and /api/today/plan (last pre-flight, never triggers one). Anything the API does
  not report is "unknown" with the reason. "Ready to trade EVAL/LIVE": NO if any item is missing; NOT CONFIRMED if
  nothing is missing but something is unknown; YES only if all are OK.
- Known gaps (for the user): the server's pre-flight feeds clock_drift_s = 0.0 (not measured), so clock sync always
  shows "unknown" and the line cannot reach YES until drift is measured; pre-flight still requires a daily bias, so in
  practice TradingAgents (classified optional per the user) can still block SEMI/FULL via the pre-flight row; Tradovate
  credentials cannot be tested here (shown "unknown" when only Tradovate is saved).

## D94 (user-approved 2026-11-11, session 17): Trading-R1 as an INFORMATION-ONLY "Research" card
- What: TauricResearch/Trading-R1 (`trading-r1==0.1.1`, PyPI, Apache-2.0 — attribution kept) answers a free-text
  research question; the answer is shown on the Strategy page in the "Research · Trading-R1 (optional)" card with the
  visible label "Information only — never triggers or gates a trade". It has NO effect on any gate, score, bias, size,
  order or automation (app/research/ is not imported by engine/, risk/, management/, phases/, bias/ or signals/).
- Isolation (docs/results/session17/trading_r1/FINDINGS.md): own venv `.venv-tr1` (`make tradingr1`, optional, not in
  `make install`, ~400 MB); never imported in the API process. `app/research/trading_r1.ServeRunner` starts
  `trading-r1 serve` on 127.0.0.1 (free port, random bearer token via TR1_API_TOKEN), POSTs /research
  (mode research, profile anthropic, stream false), then kills the process group. TR1_HOME = `<tr1_root>/data/tr1`
  (desktop: paytience-data/data/tr1 via PAYTIENCE_TR1_ROOT). Child environment built from scratch: only
  ANTHROPIC_API_KEY (by env, never its plaintext credential store) + PATH/proxy basics — no TAURIC key, so sync is
  never configured; daemon, channels and sync subcommands are never called.
- Key: API Keys page provider `tradingr1` (write-only, encrypted like every other key; optional, normal colour).
  Missing venv or key → card says "not configured"; no mock data. Last answer kept in memory only (not persisted).
- Known gaps: ServeRunner itself is untested here (needs the real venv + a key); unit/integration tests use a fake
  runner. Answers are LLM output from a web-browsing agent (prompt-injection risk) and are not backtestable — advisory
  text only. The desktop app does not auto-install .venv-tr1.

## D95 (user-approved 2026-11-11, session 18): Strategy button "Order Flow" — UNVERIFIED, PAPER accounts only (default OFF)
- User: "build no matter what" although the order-flow study is blocked (docs/results/session18/order_flow/RESULTS.md:
  Databento locked, no tick data). **No order-flow backtest exists**; the card shows no numbers and the badge
  "UNVERIFIED · paper only".
- Signal source: TradingView webhook only (non-negotiable #1). `pine/Paytience_OrderFlow.pine` (original code, PERSONAL
  USE ONLY) computes per-bar volume delta from lower-timeframe up/down volume, session cumulative delta and a session
  volume profile (POC / value area) and sends `event: "ORDER_FLOW"` alerts (id `<ticker>-TIGHT-<time_close>-ORDER_FLOW-
  <DIRECTION>`, webhook secret) for ABSORPTION, DELTA_DIVERGENCE, STACKED_IMBALANCE (intrabar proxy), SWEEP, POC_MAGNET
  with entry, defended level, stop and 2:1 target. TradingView delta is an approximation, not true aggressor data.
- Backend: `engine/order_flow.py` (pure, Decimal) rebuilds the plan and never trusts alert prices: stop = defended −
  sign × buffer_ticks (1) tick, rounded away from entry; risk 8–120 ticks; TP = 2R rounded toward entry; rr ≥ rr_min
  (≥ 1.5, config refuses lower). Skip codes OF_UNKNOWN_SIGNAL / OF_BAD_PRICE / OF_LEVEL_WRONG_SIDE / STOP_INVALID /
  STOP_TOO_TIGHT / STOP_TOO_WIDE / RR_BELOW_MIN (audited `order_flow.skip`), gate SKIPs OUTSIDE_WINDOW / NEWS_BLACKOUT /
  CALENDAR_MISSING / HEDGE_LOCK / OF_POSITION_OPEN / OF_DAILY_CAP (3/day). `strategy_service.run_order_flow`, TradePlan
  mode ORDER_FLOW, 1 micro fixed. `OrderFlowCfg` refuses paper_only=false or contracts≠1; the controller refuses any
  non-paper account (PAPER_ONLY_STRATEGY, tested). DLL, consistency, household hedge lock, news/flat times unchanged.
- Settings key `strategy.order_flow` (My Settings, versioned). Known gaps: the Pine script has static tests only (no
  Pine compiler here) — compile it once in TradingView; no performance evidence of any kind.

## D96 (user 2026-11-11, session 18): MGC (micro gold) back ON for the ORDER FLOW strategy only — user override of D55
- User instruction: turn MGC back on for Order Flow only. **Override of D55 ("MGC disabled in every Pro/Flex plan") for
  Order Flow ONLY.** The global switch `instruments.MGC.enabled` stays **false** in every plan, so NOISE, PM fade,
  Opening-drive, AI-only, LunqFX and manual orders keep MGC off exactly as before (AI Duo keeps its own D83 markets list).
- Per-strategy switch: plan file `strategy.order_flow_cfg.instruments` (validated: MNQ and/or MGC, no duplicates, each
  must exist under `instruments:`). Pro/Flex plans: `[MNQ, MGC]`; legacy Daily file unchanged (`[MNQ]`, code default).
  `run_order_flow` passes `enabled = symbol in instruments` to the shared G1 gate (window / calendar / news unchanged).
- Unchanged: default OFF, UNVERIFIED (no order-flow backtest of any kind, MNQ or MGC), PAPER accounts only
  (PAPER_ONLY_STRATEGY), 1 micro fixed, rr ≥ 1.5 (2R target), DLL / consistency / fixed_contracts worst-case checks,
  household hedge lock (MGC = METALS super-group, separate from EQUITY_INDEX) + the signal-level lock vs AI Duo MGC.
  Tick size / tick value / fee come from the MGC instrument config (0.10 / $1.00 / $1.60 VERIFY); the market's own
  `min_stop_ticks` (MGC 16) now tightens the order-flow risk floor (max of the two — tighten-only).
- New: `order_flow_cfg.flat_at` "16:00" — every open order-flow position is flattened at 16:00 ET (reason OF_FLAT_1600,
  runs even with the button off; the global 16:40 / 16:44 flats still apply).
- Pine: `pine/Paytience_OrderFlow.pine` runs on MNQ1! or MGC1! only (runtime.error otherwise); `MGC1!` maps to MGC.
  Any future MGC research must use Databento `MGC.v.0` (volume roll), never `MGC.c.0`.
- UI: the Order Flow card shows "Trades: MNQ + MGC · PAPER accounts only · flat 16:00 ET · 1 micro" (from the plan).
- Known gaps: no backtest; Pine still not compiled here (static tests only); MGC order-flow alerts untested live.

## D97 (user 2026-11-11, session 18): never show/serve a stale Paytience again (old server or old UI)
- Cause of the first bad manual update: an OLD Paytience kept answering :8000 (and/or a cached old index.html), so the new start looked like "the old app". Fixed on five levels:
- 1. Desktop start (`desktop/paytience_app.py`, logic in `backend/app/portguard.py`): before migrate/uvicorn the port is checked. Free -> go. Held by something answering `/api/health` as `app == "paytience"` -> ask it to exit via the local-only `POST /api/system/shutdown` (per-process secret in `paytience-data/run/shutdown.token`, loopback peer AND no proxy/tunnel header, endpoint inert outside the launcher), wait <= 8 s; else terminate exactly that verified PID (`netstat -ano` + `tasklist` + `taskkill /T /F`, no psutil; never our own PID; refused if the listener is not the process that answered); total budget 15 s. Held by anything else, or not freed -> clear message "Port 8000 is held by <name> (PID n); close it and start Paytience again." (console + Windows message box), exit code 2. The guard runs again right before binding (the AI-tool install can take minutes). The browser is only opened when `/api/health` reports OUR pid (an old server answering is not "ready").
- 2. `/api/health` (unauthenticated) now returns `build {commit, built_at}`, `started_at`, `executable` (name, e.g. Paytience.exe). `pid` and the full `executable_path` only for a genuinely local request (never through a tunnel).
- 3. UI: build commit embedded via vite `define` (`__UI_COMMIT__`: `VITE_UI_COMMIT` / `GITHUB_SHA` / `git rev-parse HEAD`, else "dev" = no comparison). Gold sticky banner "You are looking at the OLD interface (UI x, server y) — Reload" (one-click hard reload: unregisters the service worker, clears caches, cache-busting URL) on every page incl. Login; footer on every page "Server: Paytience.exe · build x · started t · UI y". Service-worker cache name bumped to v2 so old shells are purged.
- 4. `index.html` + SPA fallback `Cache-Control: no-store`; `sw.js`/manifest/icons `no-cache`; `/assets/*` (content-hashed) `public, max-age=31536000, immutable`.
- 5. Updater: install writes `updates/expected-commit.txt`; `on_healthy_start(updates_dir, running_commit)` confirms (healthy.flag) only when the running commit matches, else writes `unhealthy.flag` -> the .bat rolls back at once, restores the backup and sets update-failed.txt. The .bat additionally `curl`s `/api/health` after the healthy flag and requires the new commit (skipped, never a false rollback, if curl is missing). Flags are cleared at the start of each update.
- Tests: backend/tests/unit/test_portguard.py, backend/tests/integration/test_build_guard.py, frontend/src/components/BuildGuard.test.tsx. NOT testable here: real Windows behaviour (netstat/tasklist/taskkill output, MessageBox, the .bat with curl/findstr, PyInstaller exe) — reasoned and unit-tested with injected fakes only; try it once on the Windows machine (start Paytience twice; run an update).

## D98 (user-approved 2026-11-11, session 18): "Order Flow" chart page — ORIGINAL footprint-style view, ESTIMATED from bars
- User asked for a DeepCharts-style order-flow chart. Built as an ORIGINAL implementation (no vendor code, branding or look).
- Page `/orderflow` (nav "Order Flow", tab "Paytience · Order Flow"), MNQ and MGC, per CME session (18:00 → 17:00 ET):
  candlesticks + bar-delta histogram, cumulative delta (CVD), footprint grid (canvas; sell × buy per price row per bar, last
  bars that fit the width — phone width shows fewer bars), session volume profile (POC / VAH / VAL 70% / HVN / LVN), prior
  session POC/VAH/VAL, round numbers (MNQ 50, MGC 10 — display settings, not rules), premium/discount shading vs the
  prior value area, and markers for stored ORDER_FLOW webhook alerts (D95 kinds: absorption, exhaustion = delta
  divergence, aggression = stacked imbalance, sweep, POC magnet). Display only — nothing on the page sizes or trades.
- Data: ONLY the 1-minute bars the app already holds (`bars` table, heartbeat/replay bars). No external data, no scraping.
- HONESTY: without tick data the per-price buy/sell split is ESTIMATED (volume spread evenly over the bar's rows; buy share =
  close location in the range; tick rule vs previous close when high = low). Every panel shows the badge
  "ESTIMATED from bars — not true order flow"; responses carry `source: "estimated" | "tick"`. `engine/footprint.py`
  (pure, Decimal) accepts real aggressor-side levels per bar (`BarIn.ticks`) and then marks the bar `source = "tick"`, so a
  real tick feed can be plugged in later without changing the API or UI.
- Code: backend/app/engine/footprint.py, backend/app/api/orderflow.py (`GET /api/orderflow?symbol=&session=`),
  frontend/src/lib/orderflow.ts, components/OrderFlowChart.tsx, pages/OrderFlow.tsx. Tests: tests/unit/test_footprint.py,
  tests/integration/test_orderflow_api.py, frontend/src/pages/OrderFlow.test.tsx.
- Known gaps: canvas drawing and the lightweight-charts rendering are not exercised in jsdom (mocked) — check the page once in a
  browser; no tick feed exists yet; the estimated split cannot show true absorption/imbalance inside a bar.

## D99 (user 2026-11-11, final update): only MANDATORY connections block live start; rule-compliance matrix
- Pre-flight/arming: only mandatory items (broker route, TradingView heartbeat + webhook secret, public URL, calendar, positions
  attestation, clock sync, last pre-flight) can fail it. Optional items (TradingAgents bias, AI keys, Discord, Trading-R1, data vendors,
  update token) are warnings only: bias-dependent strategies skip/shadow, others trade. No mandatory or money/Lucid check loosened.
- Clock drift is now measured by the server (monitor/clocksync.py); it blocks only when the drift is KNOWN > 2 s, otherwise "unknown" + notice.
- New test matrix (tests/integration/test_rule_matrix.py): every strategy x every plan (Pro/Flex/Daily 25K-150K) x EVAL/FUNDED — caps from
  config, worst-case stop within DLL/MLL room, 1 open position, hedge lock, 16:00 flat order, Order Flow/unverified strategies paper-only.
- Finding fixed: ORDER_FLOW was missing from the controller's fixed-size table (would have raised KeyError on the first Order Flow signal) —
  now uses order_flow_cfg.contracts (1 micro).

- D100 (user 2026-11-11): the AR Model (Creamer) order-flow course is the MAIN source of the Order Flow strategy
  (environment → location → path → confirmation; docs/results/session18/order_flow/AR_MODEL_RULES.md). Casper 4h, Mind
  Math Money, ICT, SMC, volume profile etc. are STUDY references only (may refine, never override AR Model rules).
  Safety unchanged: still UNVERIFIED → paper-only, default OFF until proven on real tick data (non-negotiable 5 /
  win-rate rule); NOISE stays the live main strategy until Order Flow beats it on held-out data.

## D101 (session 18, per D100): Order Flow strategy rebuilt around the AR Model — still UNVERIFIED · paper only · default OFF
- Layers (engine/order_flow.check_ar, pure, 100% covered; skip codes audited as `order_flow.skip` with `layer` + the alert's
  layer values; shown on /orderflow): 1 ENVIRONMENT (always on) COMPRESSION → OF_COMPRESSION, env not in `allowed_envs` →
  OF_ENVIRONMENT · 2 LOCATION (switch `location_filter`) fib depth outside fib_min–fib_max (0.705–0.886) or wrong value-area
  side (`value_side` OUTSIDE_VALUE: LONG below VAL / SHORT above VAH) → OF_LOCATION · 3 PATH (switch `path_filter`) unknown →
  OF_PATH_UNKNOWN, a trade WITH the move at/beyond `path_block_zone` (MAX) of the Asia + ATR(20) zones → OF_PATH_EXHAUSTED ·
  4 CONFIRMATION (always on) no/late confirmation candle (`confirm_max_age_min` 3) → OF_NO_CONFIRM; `require_real_delta` →
  OF_DELTA_ESTIMATED. An alert without AR fields (old indicator) → OF_NO_CONFIRM (`required`). Stop now anchored beyond the
  absorption zone (absorption_low/high) — risk bounds / STOP_TOO_WIDE / rr ≥ 1.5 unchanged.
- Config: `strategy.order_flow_cfg.ar` (ArModelCfg) with validators (fib zone inside 0.5–0.886, COMPRESSION not allowed by
  type, path block ≤ MAX, confirm age 1–15, be_after_r 0.25–3); defaults written in all 9 plan files (Daily gets a `strategy:`
  block with only order_flow_cfg.ar). Gates only ever remove trades.
- Study verdict (docs/results/session18/ar_model/RESULTS.md, ESTIMATED 1m delta): the full 4-layer model did NOT beat NOISE;
  location and path did not help on bar data, environment helped a little; only MGC AM environment + confirmation (k = 1.5,
  limit at est. POC, fixed 2R) was a shadow candidate. Hence location/path are separate switches (ON by default = teacher's
  model; real delta may change the verdict). No live parameter set; the button stays default OFF.
- Pine (pine/Paytience_OrderFlow.pine): REAL delta + stacked diagonal imbalances via `request.footprint` when available, else
  estimated lower-timeframe delta, labelled `delta_source` real|est; 5m environment classifier, 15m swing fib + fixed-range
  VAH/VAL with close-beyond-0.886 invalidation, Asia range + ATR(20) zones (study calibration), confirmation candle then
  pullback entry candle; new alert fields env, location_zone, fib, value_side, path_zone, path_side, delta_source,
  confirm_time, absorption_low/high, stacked (old fields unchanged, id still ends -DIRECTION).
- Trail rule (behind the last closed 5m/15m candle, BE after be_after_r R, ratchet only, never through the market):
  `order_flow.trail_stop`, pure + tested, NOT wired — the order manager has no 5m/15m candle feed for order-flow positions
  (clean hook missing); positions keep the broker bracket + 16:00 flat.
- Known gaps: Pine NOT compiled here (static tests only) — the `request.footprint` / `volume_row` method names are from the
  Pine v6 docs as we know them; if TradingView refuses them, set `footprint fp = na` (estimated only). No real-delta test.
- D102 (user 2026-11-11, typed: "Make no strategy stay paper only"): no strategy is FORCED paper-only any more. Order Flow,
  AI Duo, AI bias, Opening-drive and the afternoon fade ship `paper_only: false` (config defaults); the validators that forced
  it (`OrderFlowCfg` paper_only must be true, `AiDuoCfg.paper_only: Literal[True]`) are gone. The controller's
  PAPER_ONLY_STRATEGY check stays as a plan-file OPT-IN (tighten-only). UNCHANGED: default PAPER mode,
  PAYTIENCE_ALLOW_LIVE=true + Settings toggle + typed "I ACCEPT LIVE RISK" + Live-Readiness Checklist, VERIFY badges, every
  risk/DLL/MLL/consistency/hedge/news/flat rule, Order Flow fixed 1 micro (validator), rr floors. UI: "paper only" labels
  removed, UNVERIFIED badges kept. Rule matrix: `test_no_strategy_is_forced_paper_only_per_plan` + opt-in check.
  Supersedes the paper-only parts of D55/D56/D83/D92/D95 and CLAUDE.md's "AI Duo stays paper-only".
- D103 (user 2026-11-11): each desktop build opens under its own browser origin http://paytience-<commit7>.localhost:8000
  (desktop/paytience_app.py ui_url(): paytience-<commit7>-<build time>; after "Install now" the page itself jumps to the new name, frontend uiOrigin()); *.localhost resolves to this PC, so an old build's cached page/service worker can never
  show a blank or stale UI for a new one. Health checks stay on 127.0.0.1. Browser login/cookies are per name → sign in again after an update.
- D104 (user 2026-11-11): TradingAgents + Vibe-Trading auto-install fixed. A venv counts as installed only with its `.paytience-ok`
  marker (written after a successful install) or a working import — a half-built venv (install killed, window closed) is rebuilt,
  not skipped forever. Installs run in a background thread so the dashboard opens at once; retried on EVERY start (needs internet).
- D105 (user 2026-11-11): "Remove LunqFX". The LunqFX fractal confluence strategy is gone from everything the user sees and
  from runtime: Strategy-page button, LunqFX gates panel (G2/G3/G5/G7, fractal agreement, "LunqFX only" badges, structure-filter
  card), the strategy catalog row, the Connections indicator card, `strategy.lunqfx` + `strategy.lunqfx_structure.*` settings
  and the key in all plan yamls. The TradingView webhook acknowledges LunqFX fractal alerts with 200 `{ignored, code
  LUNQFX_REMOVED}` (nothing stored, no banner); `signals.service.process` / the confluence evaluation is no longer called, so
  nothing can trade or shadow-trade LunqFX. Old plan files / stored settings that still carry the keys load fine (ignored by
  StrategyCfg). Deleted: engine/lunq_structure.py + its test. Left DORMANT (pure, unused at runtime; deleting touches
  shared types/tests and risked the risk/phase code): engine/confluence.py, engine/state_machine.py,
  indicators/lunqfx_fractal.py, bigbeluga_mso.py, backtest/parity.py, Cooldown table/API. Risk/phase/management untouched.
  Tests (D105 follow-up): LunqFX-only tests deleted; the safety/infra tests (automation, kill switch, restart recovery,
  watchdog, reliability, every stage, news flatten) now get their tradeable signal from a direct fixture
  (tests/integration/test_signals_flow.py `confirm`: PASS signal + §7 plan from engine/trade_plan) dispatched through
  the real `app.api.webhook.dispatch_updates` (SEMI approval / FULL execute) - same controller/risk/OM path, same
  assertions.
- D106 (user 2026-11-11): "Remove all unnecessary gates and have each strategy have different gates". The generic gates
  panel (GateChain: G1 / RISK / OB / G6 / AI rows "for NOISE + afternoon fade") and the Signals page's fixed G1–G8
  columns are gone. New read-only `GET /api/strategy-gates` (backend/app/api/strategy_gates.py; pure `describe`,
  `lucid_rules`, `evaluate`) lists, per kept strategy (NOISE, Afternoon fade, Opening drive, AI only, AI Duo, Order Flow),
  ONLY the checks its own code in signals/strategy_service.py + engine/* makes, in that order, every number from the live
  config (e.g. NOISE: decision bar, warm-up/roll guard, noise-band breakout, entries/day, window, AI block advisory;
  exits VWAP/band trail, $ stop, flat; Order Flow: AR environment → location → path → confirmation (location/path only
  while their switches are on), stop + R:R plan, window, one position, daily cap). Live status from that strategy's
  latest signal (Order Flow: or its newer audited `order_flow.skip`): earlier gates PASS, the gate owning the skip
  code FAIL, later NOT_REACHED; window/news/hedge/risk codes FAIL the strategy's "Lucid rules" step. Off-by-default
  study filters (D76 OB/SMT) appear only while switched on. Firm/safety checks (news + calendar, DLL/MLL, consistency,
  hedge lock, kill switch, positions per account, flat times, pre-flight) are shown ONCE as "Lucid rules (always on)",
  locked. Display only: no backend gate, risk or safety logic changed. The AI proof-threshold editor moved to the NOISE
  card. Left for the test owner: `/api/strategies` still returns the unused `gate_chain` (tests test_bias_ledger /
  test_mso_disabled read it) — remove together with those asserts.
- D107 (user 2026-11-11): "Remove opening drive". The Opening-drive pullback strategy (OPEN_DRIVE, D55) is removed like
  LunqFX (D105): Strategy-page button/catalog card, `strategy.open_drive` (My Settings key) + `strategy.open_drive_cfg`
  (OpenDriveCfg) and the `open_drive: false` line in the 8 Pro/Flex plan yamls, strategy_service routing
  (`run_open_drive`), the controller's OPEN_DRIVE strategy mode / fixed size / limit entry, the per-strategy gates card
  (api/strategy_gates.py) and UI/docs text. Deleted: engine/open_drive.py + tests/unit/test_open_drive.py and the OPEN_DRIVE
  service test / rule-matrix cell. Old plan files / stored settings with `open_drive` / `open_drive_cfg` load fine (ignored
  by StrategyCfg, like the LunqFX keys). A stored OPEN_DRIVE signal can no longer be executed (NO_PLAN). Safety unchanged:
  the "OD" tag stays in Order Flow's signal-level hedge-lock list (a legacy open position still locks), global flat
  times / watchdog / kill switch / risk untouched. Same change: the D92 split card is labelled "NOISE + AI Duo — 50/50
  risk split" and the per-strategy gates view shows it with both sides (NOISE side, AI Duo side, 50/50 budget
  SPLIT_BUDGET_EXCEEDED, Lucid rules); behaviour unchanged.
- D108 (user 2026-11-11, "implement 1st transcript knowledge too"): the Casper / Jesse Rogers 4h order-flow course
  (docs/results/session18/order_flow/TEACHER_RULES_4H.md) is added as REFINEMENTS of the AR Model Order Flow strategy
  (D100: refine, never override). Plan file `strategy.order_flow_cfg.casper`, each rule its own switch, checked after the
  AR layers (engine/order_flow.check_casper / casper_round_stop, layer CASPER): PRICE_CONFIRMS (entry candle closes away
  from the trapped side, ≥ close_pos_min 0.5–0.9 of its range; ON — tightens) · STACKED (STACKED_IMBALANCE needs
  ≥ min_stacked 3–6 imbalances in a row; ON — tightens) · CVD (sum of delta over the last N bars moves with the trade;
  OFF) · CONDITION (no trade against RTH open vs PRIOR RTH value area 09:30–16:00 ET; OFF) · BUNCHED (no trade when the
  prior value area < min_va_width_atr × daily ATR(20); OFF) · ROUND_STOP (stop 1–3 ticks beyond a nearby round number,
  MNQ 50 / MGC 5, re-checked against max risk and R:R; OFF — it widens the stop). Codes OF_CASPER_<RULE>; an active rule
  whose field the alert lacks skips (no silent pass). Pine sends close_pos, cvd_slope, open_vs_value,
  prior_va_width_atr. Not implemented (not mechanical / no data): gamma, heat map / DOM, trailing behind balances
  (AR trail stays), half-risk feeler trades, "one more attempt" day rule. Still UNVERIFIED, 1 micro, every safety gate
  unchanged; the Order Flow page lists them as an extra layer.
- D109 (user 2026-11-11): TradingAgents as an ADVISOR for Order Flow. Toggle on the Order Flow page = My Settings key
  `strategy.order_flow_cfg.ta_advisor` (default OFF, validated settings flow; also in OrderFlowCfg + all 9 plan yamls with
  `ta_advisor_blocks: false` and `ta_advisor_lead_min: 60`, both plan-file only). When ON (and the Order Flow button is
  on) the EXISTING bias job (bias/service.run_bias, new `only=` proxy filter → ta_runner.py subprocess JSON; never
  imported in the API process) runs once per session at lead_min before the earliest entry-window start of the Order
  Flow markets (ET, scheduler + injected Clock; today 03:00 − 1 h = 02:00 ET; a proxy already decided today is reused,
  not re-run). Advice per market is stored as audit `order_flow.ta_advice` (code OF_TA_ADVICE: side, confidence, time)
  and shown on the Order Flow page with an "advisory" label (bias/of_advisor.py). Semantics: an opposite-side
  ORDER_FLOW signal gets audit `order_flow.ta_disagrees` + a `ta_advice` annotation; it is skipped OF_TA_DISAGREES only
  when `ta_advisor_blocks` is true AND the AI-accuracy ledger is proven (bias/ledger.proven at
  strategy.ai_gate_min_accuracy — advisory until proven). Failure / no key / unknown rating = no advice, never a block
  (warn notice). Also: Order Flow page step-by-step TradingView guide (download /api/pine/orderflow, Pine Editor → Save
  → Add to chart on MNQ1!/MGC1! 1m, Premium/Ultimate for request.footprint else delta_source=est, CME real-time data,
  alert "Any alert() function call", Webhook URL from the Connections tunnel, message {{alert message}}, open-ended
  expiry note, one alert per symbol); the webhook secret is never printed there (Connections page only).
- D110 (user 2026-11-11, "AMT+ Order flow button"; docs/results/session18/order_flow/AMT_PLUS_RULES.md — a prop-firm
  trader who trades Lucid): Strategy-page button "AMT+ Order Flow" = My Settings key `strategy.order_flow_cfg.amt.enabled`
  (default OFF; turning it on also turns `strategy.order_flow` on; `amt.balance_mode` skip|edges also editable). Plan
  file `strategy.order_flow_cfg.amt` (AmtCfg, all 9 yamls): balance_mode skip, level_filter on, levels [ETH_VWAP,
  PRIOR_VAH, PRIOR_VAL, PRIOR_POC, LVN, DELTA_OUTLIER, PRIOR_HIGH, PRIOR_LOW], target_to_level on, target_max_rr 3.0
  (validator 1.5–3.0 and ≥ rr_min: TP ≤ 3R pillar). Top-down, checked BEFORE the AR layers ("order flow LAST"):
  engine/order_flow.check_amt — CONTEXT (alert `context` ACCEPT_ABOVE → longs only, ACCEPT_BELOW → shorts only,
  BALANCE → skip, or with `edges` only LONG at PRIOR_VAL / SHORT at PRIOR_VAH; codes OF_AMT_NO_CONTEXT /
  OF_AMT_COUNTER_CONTEXT / OF_AMT_BALANCE) → LOCATION (`key_level_type` must be an allowed key level, OF_AMT_NO_LEVEL);
  `amt_target` uses the alert's `target_level` (nearest key level beyond entry) as TP when it gives rr_min…target_max_rr,
  else the normal 2R. Pine (Paytience_OrderFlow.pine) now sends prev_rth_vah/val/poc, eth_vwap (anchored 18:00 ET),
  context (acceptance = ≥ accPct 70% of the first accN 30 one-minute closes of each session — Asia 18:00 / London 03:00
  / RTH 09:30 — above / below the prior RTH value area; holds until the next session's read), ctx_session,
  key_level_type (within lvlTicks 8 ticks of the signal bar; LVN = prior RTH rows ≤ 30% of the POC row; DELTA_OUTLIER =
  bars with |delta| ≥ 3× average this Globex day) and target_level. Shown on the Strategy page (card + layer list), the
  Strategy gates list (AMT_CONTEXT / AMT_LOCATION on the Order Flow card) and the Order Flow page ("First layer").
  UNVERIFIED (no real order-flow data; the trader's 43% win / 3.5 avg-win-loss claims are not ours); only removes trades
  or picks a TP inside the R window; 1 micro; every Order Flow and Lucid gate unchanged. Not implemented (no data):
  gamma exposure, Bookmap / heat-map liquidity, weekly TPO, hold-vs-scalp by payout distance.
- D111 (user 2026-11-11, "create final strategy from this or add it as a separate type of order flow trading toggle";
  docs/results/session18/order_flow/ICEBERG_ATR_RULES.md — Scott / Chart Fanatics): a SEPARATE Order Flow TYPE, plan
  file `strategy.order_flow_cfg.zone_atr` (ZoneAtrCfg, 9 yamls; default OFF). Toggles: Order Flow page (on/off +
  POSITION / REVERSION selector) and a Strategy-page card "Order Flow · ATR zones" (also turns Order Flow on); My
  Settings keys zone_atr.enabled / modes / a_plus_only / dead_zone_filter / last_minutes_filter / price_change_confirm /
  tick_filter. The event is an iceberg PROXY (no MBO data): Pine (kind ZONE) marks a footprint absorption / large-volume
  bar (volume ≥ 2.5× average or heavy delta) as the event zone (bar range) and sends zone_signal EVENT / POSITION /
  REVERSION with event_zone_hi/lo, event_kind, event_time, event_size, atr5 (Wilder ATR(14) of the last closed 5m bar),
  rev_level, prior_event_hi/lo, rvol (proxy: 5-bar volume vs ~5 sessions), range5_atr, tick (optional NYSE TICK input).
  engine/zone_atr.py (pure): check_zone codes OF_ZONE_NOT_ENTRY / MODE_OFF / NO_EVENT / EVENT_SMALL (MNQ 150, MGC 150) /
  LAST_MINUTES (last 10 min before 16:00) / DEAD_ZONE (11:15–13:30 ET needs rvol ≥ 1.5) / NOT_PROVEN (POSITION entry ≥
  115% ATR outside the zone) / REV_LEVEL / NO_PRICE_CHANGE (5-min range ≥ 0.70 ATR) / PROGRAM_DAY (|TICK| ≥ 1000 against
  the fade; off without TICK) / NOT_A_PLUS; plan_zone: POSITION stop back through the zone + 115% ATR, TP rr (2R; AMT
  level target when on); REVERSION target = zone edge, stop at the next ATR line (A+: also outside the prior event), TP
  capped at 3R — the rr_min 1.5 floor (D49) stays, so 1-ATR reversions (1R) skip RR_BELOW_MIN and only 2/3-ATR levels
  trade. max_risk_ticks 400 for the wide ATR stop; still 1 micro and every Lucid risk / DLL / MLL check. Trail: a new
  same-direction EVENT ratchets `zone_trail_stop` to its 115%-ATR line (never breakeven), enforced at bar close
  (OF_ZONE_TRAIL exit; the broker stop stays as the protective stop); an opposite EVENT exits (OF_ZONE_OPPOSING_EVENT).
  `exclusive` (default false) makes AR-type alerts skip OF_ZONE_EXCLUSIVE. Strategy gates: ZONE_EVENT / ZONE_TIME /
  ZONE_SETUP on the Order Flow card. UNVERIFIED. Not implemented (no data): real iceberg/stop events (MBO), GEX / hero,
  heat-map liquidity, partial scalps around the runner.

- D112 (user 2026-11-11, "make all strategies take advantage that I have CME real time data"): data plumbing only, no strategy
  logic change. Heartbeat may carry `data_feed` (Pine timenow vs time_close) and price.up_volume/down_volume/delta (absent =
  tolerated; Bridge sends data_feed + real volume, the Order Flow script keeps its own real delta). Backend computes bar-close lag
  vs the injected Clock (`monitor/feed.py: bar_lag_s/data_feed_status`, config `webhook.realtime_max_lag_s` default 90 s);
  DELAYED → controller blocks NEW entries for all strategies (`FEED_DELAYED`) + safety banner + notify; flatten rules unchanged.
  UI: "CME real-time data: OK / DELAYED / unknown" on Connections; Strategy page note. Latest real delta kept on SymbolState.
- D113 (user 2026-11-11): BigBeluga MSO card removed from the Connections page (INDICATORS empty; empty section hidden). Tunnel test now hints "try https://…" when the URL has no scheme.
- D119 (audit 2026-11-11): in-app update root cause — the update .bat inherited the app's cwd (`_internal\backend`), so cmd.exe itself held `_internal` open and every swap failed → restore. Fixes: Popen cwd = updates folder + `cd /d` first line; CREATE_BREAKAWAY_FROM_JOB (fallback without) so killing the app cannot kill the script; new app started with `start "Paytience" /D <app dir>`; rollback also kills ngrok/cloudflared; .bat written in the OEM code page (non-ASCII user paths); uv/pip helpers run with cwd=paytience-data; RestartNotice counts a 5xx as "server gone". Verify on Windows only: breakaway behaviour, OEM path, real swap.
- D115 (user 2026-11-11): per-strategy, per-plan size in every `config/rules/*.yaml` (`strategy.noise_cfg / pm_fade_cfg / ai_bias_cfg / ai_duo_cfg / order_flow_cfg.contracts`, `strategy.max_trade_risk_usd`, size tables). 25K plans = 1 micro for every strategy; NOISE/PM_FADE scale with the plan's drawdown: 50K 2, 100K 3 (high-risk table 4), 150K 5; AI Bias / AI Duo / Order Flow stay at floor(MLL ratio) (2/3/4) because they are UNVERIFIED, plus their own `max_risk_usd` budget (Order Flow + AI Bias: 30% of the MLL; the AI Duo $250 cap unchanged). Order Flow is risk-based: `min(contracts, floor(max_risk_usd / per-contract risk at its own stop))`, 0 → STOP_TOO_WIDE. Every plan has `max_trade_risk_usd` = 50% of the MLL. Never above the plan's firm max, internal max, DLL/MLL worst case, consistency cap, split 50/50 (halves, round down, min 1), hedge lock; `RulesConfig` validators refuse a size < 1 or > firm max micros. Controller: `plan_contracts` (account smaller than the plan → proportionally fewer), `risk_cap` (tightest $ cap), cushion brake for AI Bias / AI Duo / Order Flow. Tests: rule matrix (all plans × stages × strategies) + validators.
- D116 (user 2026-11-11): (a) Qwen "Access to model denied" (HTTP 403) in the Strategy-page backfill / daily AI job. Root cause: TradingAgents ran `qwen3.8-max` / `qwen3.8-flash` (BEST_MODELS) while Vibe-Trading ran a different default (`qwen-plus-latest`) and only the connection test followed `PAYTIENCE_QWEN_BASE_URL`; a workspace key (`sk-ws-…`) not enabled for one of those ids is refused with 403 on exactly that model. Now `connections/registry.py` (`qwen_base_url`, `qwen_model`) is the single source for the connection test, TradingAgents and Vibe-Trading (Connections model fields → `PAYTIENCE_QWEN_QUICK_MODEL` / `PAYTIENCE_QWEN_DEEP_MODEL` → BEST_MODELS; base URL `PAYTIENCE_QWEN_BASE_URL`), and every AI error (backfill job, daily job, notify) names the model(s) that were denied. (b) Lucid rules card showed "Consistency ≤ 4000%": the plan stores 40 (percent) and the card formatted it with `:%`; now "40%". A null DLL reads "none in this plan" (Pro eval, Flex: the amount is a checkout option). (c) The 02:40 / 02:50 / 02:00 ET times are the configured ET values (D34: calendar 02:30, bias 02:40, pre-flight 02:50 before gold's 03:00 window; Order Flow advisor = earliest window start − 60 min); the backend `due()` converts with `to_et`, no conversion bug found — change `schedule.*` in the plan yaml if other times are wanted.
- D121 (2026-11-11, integration): D115 had raised NOISE/PM_FADE size tables (100K 3/4, 150K 5/5). The session-19 refine study
  (docs/results/session19/refine/RESULTS.md) measured 7.5-yr bust 37–46% at those sizes vs ~18% at 100K×2 / 150K×3, so the
  research-verified D63/D64 tables are kept (regular 25K 1 · 50K 2 · 100K 2 · 150K 3; high 1·2·3·4) and the fallback /
  unverified per-plan sizes are capped at the regular table (AI Bias, AI Duo, Order Flow: 100K 2, 150K 3). Hold rule: every
  app-initiated exit waits min_hold_seconds = 7.5 s in all 9 plans (user: ≥ 7 s, also order-block strategies); protective exits never wait.
- D123 (user 2026-11-11): NOISE skips new entries on Mondays (`strategy.noise_cfg.skip_weekdays: [0]` in all 9 plans). Session-19
  refine R6: in-sample PF 1.37→1.44 and held-out win 55.0→59.5 %, PF 1.53→1.72, Pro 25K pass 62→69 %; evidence weak (2024-heavy).
- D122 (user 2026-11-11, "an intelligent dynamic trailing stop loss and cushion level controls on all strategies, make it a
  toggle option"): two new tighten-only controls, per-strategy toggles (NOISE / Afternoon fade / AI only / AI Duo / Order
  Flow), default OFF, UNVERIFIED (no backtest; UI badge). Numbers in every plan yaml (`strategy.dynamic_trail`,
  `strategy.cushion`; DynamicTrailCfg / CushionCfg validators), editable on the Strategy page (My Settings, versioned).
  (1) management/dynamic_trail.py (pure, 100%): from +activate_r (1.0R) the broker stop → breakeven + fee cover, then
  best − max(k × ATR(14) of 5m bars built from the 1m heartbeat bars, distance to the last closed 5m swing low/high ± 1
  tick); k 2.0 until 2R, 1.5 until 3R, 1.0 after, × 0.75 when the ATR is in its lowest 25% of the last 50 values, minus the
  cushion level's k reduction, never below k_floor 0.5; never closer than min_distance_ticks 8 to the market; ratchet only;
  TP untouched; the strategy's own exits (NOISE VWAP/band, flat) stay. Wired in the order manager next to the D85/D82
  moves (OrderManager.bars buffer fed by Controller.on_bar from the webhook heartbeat; protective → no D8 hold; stop-modify
  failure → flatten + pause, §8). Snapshot in trade_state (restart). Order Flow: with its toggle ON, AR-type trades also get
  the D101 `order_flow.trail_stop` (BE after be_after_r, behind the last closed trail_candle_min candle) — the D101 rule
  that was left unwired; zone-type trades keep the already-wired D111 bar-close zone trail. After a restart the bar buffer
  is empty: only breakeven moves until 5m bars build up.
  (2) risk/cushion.py (pure, 100%): cushion = equity incl. open P&L − current MLL, share of the plan's max loss:
  ≥ 75% NORMAL · 50–75% REDUCE (−1 micro, min 1; trail k −0.25) · 25–50% MINIMAL (1 micro, k −0.5, ≤ 1 trade/day →
  CUSHION_MAX_TRADES) · < 25% STOP (CUSHION_STOP, audited `risk.cushion_stop`, blocked for the rest of the session even
  if the cushion recovers; survives a restart). Applied in the controller after the size table / brake / split and before
  pretrade: only ever lowers `fixed`, so the D121 size tables (100K 2 · 150K 3) are unchanged (user 2026-11-11: cushion
  may only reduce size temporarily) and the kill switch, pause floor, DLL, MLL worst case, consistency, hedge lock all still
  run. Dashboard + Accounts show a "CUSHION <level> · x%" chip per account (GET /api/dashboard `cushion`).
  Tests: tests/unit/test_dynamic_trail.py, test_cushion.py, order manager + trade_state cases,
  tests/integration/test_cushion_trail.py (controller, webhook bar feed, dashboard, settings validation);
  frontend TrailCushionCard.test.tsx.
- D124 (user 2026-11-11): Neon Gold style is the default UI (frontend/src/style-switch.ts); ?style=classic shows the previous look.
- D125 (user 2026-11-12 "bust numbers wrong"): Strategy presets Pro 100K / 150K low risk re-based on the session-19 study (7.5 yr, NOISE preset C + Mondays off): 100K = 2 micros (brake 1 under $900, fade OFF), 150K = 3 micros; both pass 83% / bust 15% (held-out last 12 mo 78/22). The old 100K card (3 micros + fade, 63/22) was optimistic.
- D126 (user 2026-11-12): preset pass/bust shown as shares of finished evaluations so they add up to 100 (25K 64/36, 100K 85/15, 150K 85/15; raw had 1–2% still open at the 400-session cap).
- D127 (user 2026-11-12): Strategy-page toggle "NOISE contract size": As configured (default, how it is: Regular/High table) or Suggested = session-19 lowest-bust sizes 25K 1 · 50K 1 · 100K 2 · 150K 3 (strategy.suggested_size + size_table_suggested in the 8 Pro/Flex plans; Daily has no size table). Only NOISE/PM_FADE size; every safety check unchanged.
- D128 (user 2026-11-12, session-20 bug list B3/B4/I6): (B3) the order manager reads the minimum hold, runner trail and early-exit limit LIVE from the RulesHolder (`OrderManager.holder`), so a Risk-page edit of `behavior.min_hold_seconds` applies to the next exit check without a restart. (B4) `behavior.min_hold_seconds` validator floor 6.5 s → 7.0 s (user rule ≥ 7 s; plans stay at 7.5 s). (I6) CONSISTENCY_DAY_STOP, DLL_LIMIT and FEED_LOST are listed in `management/exits.PROTECTIVE` (they already never waited; now the D8 list is complete in one place).
- D129 (user 2026-11-12, B5): household hedge lock also counts orders IN FLIGHT: every trade the order manager tracks (unfilled, working or open, any account) plus persisted trades opened in the last `reliability.hedge_inflight_s` seconds (default 120, 10–900) that are not closed (covers a restart before recovery). CrossTrade polling lag can no longer let an opposite-side signal of another strategy/account through. Tighten-only (`Controller.inflight_positions`; tests/integration/test_hedge_inflight.py).
- D130 (user 2026-11-12, B6): updater rollback hardened. The .bat restore retries Paytience.exe and _internal up to 20 times 1 s apart (like the forward move), checks each part really came back, logs every try, and says "NOT fully restored — copy the backup back by hand" if it gives up. expected-commit.txt is deleted on the .bat :fail/:restore path, on every failed install/launch in the API, and by `on_healthy_start` when it is stale (the .bat already rolled back, or the file is > 15 min old) — so the old app never shows a false "Update check failed" banner. A fresh expected commit is still checked (D97). Windows-only behaviour; verified by script-text tests only.
