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
