# PAYTIENCE — CLAUDE CODE MASTER PROMPT v9.2 (FINAL, COMPLETE)

Source: the user's own text (Part 1, pasted 2026-11-06) and screenshots of §21–§24 (Part 2, email "GRAND FINITO
ADDE U.I", 2026-11-04). §21–§24 were transcribed from images; the screenshots ended inside §24.6, so §24.7+ is
still missing. Approved changes in docs/DECISIONS.md (D1–D39) override the values below where they differ
(e.g. instruments MGC/MNQ, windows, R:R 1.0–3.0 in the Pro/Flex plans, Lucid Pro/Flex plan files).

Indicators (TradingView): 1. "ICT Fractal Model + HTF Candle Projection" [by LunqFX, 3.5K+ stars] ·
2. "Market Structure Oscillator" [by BigBeluga, 1.8K stars] · AI bias: TauricResearch/TradingAgents.

---

Automated confluence trading app for 1–5 Lucid Trading LucidDaily 25K accounts
Purchase profile: EOD drawdown | Daily Loss Limit ON | Consistency 40% | Weekly payouts (on-demand allowed)

## 0. HOW YOU WORK
Role: senior full-stack + trading-systems + quant engineer.
Priorities: firm-rule compliance > capital safety > correctness > fully working UI > readability.
• Build in the phases of §22. After each: run all tests, show results, list open questions, STOP for my approval. Phases 0–6 + backtest gate (§16.9) + clean demo run = required before buying/trading evaluations.
• Ask before guessing on money, rules, credentials, broker APIs or data sources.
• Never weaken a safety check to pass a test. Use Decimal for all prices and money.
• Code references here are binding contracts (names, signatures, behavior).
• Phase 0: write CLAUDE.md with condensed §1, §6–§10, §11C, §13, §14, §17. Re-read it every session.
• Plan mode per phase; small commits; one phase per branch; never commit secrets.

## 1. NON-NEGOTIABLE RULES
1.1 Never automate/scrape the TradingView site/trading panel or the Lucid site. Live signals arrive ONLY via TradingView webhooks. Playwright tests OUR app only.
1.2 Never persist passwords. Prefer broker OAuth or TradersPost. If the Tradovate API needs credentials: one-time modal → memory only → discard; store only the encrypted token (OS keychain preferred); auto-renew.
1.3 Lucid has no public API. Lucid account = Tradovate account ID + rule profile + stage (EVAL/FUNDED/LIVE). The "Lucid" button only opens the Lucid dashboard in a new tab.
1.4 Never disguise automation as manual trading.
1.5 Default PAPER (Tradovate demo). LIVE needs env PAYTIENCE_ALLOW_LIVE=true + Settings toggle + typed "I ACCEPT LIVE RISK" + completed Live-Readiness Checklist (§21).
1.6 Read each TradingView script's license before porting; keep attribution; non-commercial → README "PERSONAL USE ONLY". Never touch protected code.
1.7 Rule numbers live in config (§23) + DB, editable only via the validated Risk UI (§11). "# VERIFY" values show a gold badge until confirmed. Hardcoded rule values = bug (incl. every threshold in §9).
1.8 Never hedge. Household-wide direction lock: no account, profile (TIGHT/STD) or instrument in the EQUITY_INDEX super-group may open opposite to any open position in the household; later signal → Skip("HEDGE_LOCK"). Max 1 open position per account.
1.9 No silent failures: trading-relevant error → block new entries + log + UI banner + notify.
1.10 Self-improvement (§17) may NEVER modify a Pillar (§17.1). Enforced by tests.
1.11 Evaluation Mode (§11C) applies ONLY to stage EVAL; it can never load on FUNDED or LIVE. Enforced in pure risk code + tests.
1.12 Positions at other firms/platforms are invisible to the app: README warns opposite correlated positions elsewhere count as hedging; an "external positions" attestation is required each session before arming.

## 2. TECH STACK
Backend: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 + SQLite (Postgres-ready), Alembic, APScheduler, httpx, websockets, structlog, numpy, pandas, scipy, Optuna.
Workers: arq + Redis (Docker); jobs never block trading; trading has CPU priority.
Frontend: React 18, Vite, TypeScript, Tailwind, TanStack Query, Zustand, React Router, Recharts, TradingView Lightweight Charts; WebSocket with auto-reconnect.
AI bias: TauricResearch/TradingAgents (pinned version) behind an adapter, never modified.
Quality: pytest + hypothesis, vitest + RTL, Playwright, ruff, mypy --strict, eslint, tsc.
Ops: Docker Compose (api, worker, redis, web), Makefile, .env.example, notifications (Discord/Telegram/email). Time: America/New_York, DST-correct, injected Clock.

## 3. FILE TREE
backend/app/: main.py config.py clock.py db.py ws.py models/ schemas/ api/
webhook/(security, parser_bridge, parser_original) indicators/(lunqfx_fractal, bigbeluga_mso, atr, smt)
engine/(state_machine, confluence, scoring, trade_plan, filters)
management/(drawdown_guard, runner, exits)
risk/(risk_base, tiers, sizing, checks, validation, eval_mode, consistency, hedge_lock)
phases/(phase_engine, mll_tracker, transitions)
automation/(controller, preflight, pauses, account_selector, cooldown)
execution/(order_manager, adapters/{base,tradovate,traderspost,sim})
monitor/(pnl_monitor, kill_switch, reconcile, inactivity)
payouts/(payout_engine, plan_tracker)
bias/(tradingagents_adapter) calendar/(econ_calendar)
backtest/(data_store, replay, sim_fills, metrics, monte_carlo)
lab/(tunables, pillars, walk_forward, optimizer, shadow) workers/(jobs, scheduler)
backend/tests/(unit, property, integration, fixtures)
frontend/src/(app, components, pages, lib/{api.ts, ws.ts, theme.ts})
pine/(Paytience_Bridge.pine, Paytience_Bridge_Strategy.pine)
config/rules/lucid_daily_25k.yaml, docker-compose.yml, Makefile, README.md, CLAUDE.md, .env.example

## 4. ARCHITECTURE
Webhook → Market State Store → Confluence Engine (§6) → TradePlan (§7) → Signal (stored with gates/score/features/skip reason even if rejected) → Automation Controller (§13) → Account Selector (§12) →
per account: Phase Engine (§10) → Drawdown Guard (§8) → Risk Engine (§9 + §11C + consistency + hedge lock) → Order Manager → BrokerAdapter → PnL Monitor/MLL Tracker → Kill Switch/Auto-Flatten → Payout Engine (§14) → Audit Log → Notifications → UI WebSocket.
Background: Data Recorder → Backtest (§16) → Lab (§17).
SINGLE SOURCE OF TRUTH: engine/, management/, risk/, phases/ are pure deterministic modules (no I/O). Live, paper, replay, backtest and shadow call the SAME code.

```python
class BrokerAdapter(Protocol):
    capabilities: frozenset[str]  # declare unsupported features
    async def list_accounts(self) -> list[BrokerAccount]: ...
    async def get_positions(self, acct: str) -> list[Position]: ...
    async def get_orders(self, acct: str) -> list[Order]: ...
    async def get_balance(self, acct: str) -> Decimal: ...
    async def place_bracket(self, acct: str, req: BracketRequest) -> BracketAck: ...
    async def modify_stop(self, acct: str, order_id: str, price: Decimal) -> bool: ...
    async def cancel_all(self, acct: str) -> None: ...
    async def flatten(self, acct: str) -> None: ...
    def stream_fills(self) -> AsyncIterator[Fill]: ...
    def stream_pnl(self) -> AsyncIterator[PnlUpdate] | None: ...  # None → CONSERVATIVE MODE
    async def health(self) -> AdapterHealth: ...
```
Adapters: TradovateDirect, TradersPost, Sim (fees, slippage, stop-first on ambiguous bars).
PHASE 0 MUST RESOLVE WITH ME: broker route (incl. Tradovate API access/market-data requirements) + historical data source (+ ES data if SMT enabled).
CONSERVATIVE MODE: open positions assumed at stop; UI banner. Manual trades made outside the app → reconcile.py counts them in risk; a hedge → loud alert.

## 5. TRADINGVIEW LAYER
Paid TradingView plan with webhooks + 2FA (document it).
5.1 Option A (preferred): Paytience_Bridge.pine (v6) ports needed logic of "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]" + "Market Structure Oscillator [BigBeluga]" with attribution; closed bars only; no lookahead. LunqFX "Require C2 to close back inside C1" = ON (pillar). CISD counts only if printed before C2 closes. Bridge also sends HTF ATR(14) and C1 open time. Option B: original scripts + "Any alert() function call" + tested parsers.
5.2 Python reference ports in indicators/. Three-way parity (Python ↔ bridge ↔ originals) ≥20 sessions, incl. T1/T2/fail rates vs the LunqFX built-in track record; mismatch blocks LIVE and Lab promotions. MSO_DIV/MSO_CHOCH/MSO_BOS timestamped at the CONFIRMATION bar (pivot right bars elapsed), never the pivot bar.
5.3 Pine reference:
```pine
//@version=6
indicator("Paytience_Bridge", overlay = true)
secret  = input.string("", "Webhook secret")
profile = input.string("STD", "Profile", options = ["TIGHT", "STD"])

f_send(string evt, string dir, string extra) =>
    if barstate.isconfirmed
        string tail = extra == "" ? "" : "," + extra
        alert('{"v":1,"secret":"' + secret + '","id":"' + syminfo.ticker + "-" + profile + "-" +
              str.tostring(time_close) + "-" + evt + '","symbol":"' + syminfo.ticker + '","profile":"' +
              profile + '","tf":"' + timeframe.period + '","bar_time_ms":' + str.tostring(time_close) +
              ',"event":"' + evt + '","direction":"' + dir + '"' + tail + "}",
              alert.freq_once_per_bar_close)
// Heartbeat: f_send("HEARTBEAT", "NONE", '"price":{"o":' + str.tostring(open, format.mintick) + ',"h":' + str.tostring(high, format.mintick) + ',"l":' + str.tostring(low, format.mintick) + ',"c":' + str.tostring(close, format.mintick) + ',"v":' + str.tostring(volume) + '}')
```
5.4 Payload (Pydantic):
```python
class WebhookPayload(BaseModel):
    v: Literal[1]; secret: SecretStr; id: str; symbol: str
    profile: Literal["TIGHT","STD"]; tf: str; bar_time_ms: int  # bar CLOSE time; tf "60" = 1H
    event: Literal["HEARTBEAT","C1_SWEPT","CISD","MODEL_CONFIRMED","T1_HIT","T2_HIT",
                   "MODEL_FAILED","C3_CLOSED","MSO_CHOCH","MSO_BOS","MSO_DIV"]
    direction: Literal["LONG","SHORT","NONE"]
    price: Ohlcv | None = None
    fractal: FractalFields | None = None  # c1_high,c1_low,c1_time_ms,htf_atr14,t1,t2,invalid,sweep_extreme,
                                          # sweep_time_ms,cisd_level,cisd_before_c2_close,t1_preticked,c3_close_time_ms
    mso: MsoFields | None = None          # trend BULL|BEAR, osc 0–100, div, htf_trend, confirm_time_ms
```
Constant-time secret check (hmac.compare_digest); idempotency on id; reject HEARTBEAT >30 s old, events >90 s (age from bar_time_ms); rate limit; respond 200 within 1 s, process async. HEARTBEAT every closed bar with OHLCV; missing 2× bar interval in session hours → STALE → block.
5.5 Paytience_Bridge_Strategy.pine implements §6–§8 for Strategy Tester (commission, 1 tick slippage).
5.6 README: step-by-step alert setup + test alert.

## 6. CONFLUENCE ENGINE
Roles (none can trigger alone): LunqFX Fractal = WHERE/WHAT (direction, INVALID = stop anchor, T2 = target anchor; C2 sweeps C1 LOW + closes inside → LONG, sweeps C1 HIGH → SHORT). BigBeluga MSO = WHEN/WHETHER (structure turned after sweep, structure side, divergence veto). TradingAgents = WHICH SIDE TODAY. Phase/Guard/Risk = WHETHER this account trades + HOW.
State machine per symbol+profile: IDLE → SWEEP → CONFIRMED → ARMED → ENTERED → MANAGING → RESOLVED(TP|STOP|BE|TRAIL|TIME|STRUCT|MODEL_FAILED|EXPIRED|CANCELLED) → IDLE. Log transitions.
One entry per fractal model (model_key = symbol+profile+c1_time_ms): after any resolution no re-entry on that model.
Model-fail cooldown: [S] model_fail_cooldown.streak (3) consecutive MODEL_FAILED on a symbol+profile → that profile paused for [S] model_fail_cooldown.sessions (5) sessions; banner + notify ([S] = my setting, not Lab-tunable).
Instruments: MNQ core; MES only if its own backtest passes §16.6. Profiles TIGHT = 1m→15m (risk base < $1,500), STD = 5m→1H (risk base ≥ $1,500); both may run (subject to §1.8). Correlation groups {NQ,MNQ},{ES,MES},{YM,MYM},{RTY,M2K} + EQUITY_INDEX super-group.
HARD GATES ([P]=Pillar, [T]=tunable), all must pass at entry-bar close:
G1[P] enabled window; no blackout; no high-impact USD event within [T]no_entry_before_news_min; feed fresh; not halted; profile not in model-fail cooldown.
G2[P] bias ≠ NO_TRADE and not opposite.
G3[P] model CONFIRMED/ARMED, not failed, C3 open, T1 not traded through since confirmation (unless t1_preticked), model not already traded, C1 range ≥ [T]c1_min_range_atr × HTF ATR(14).
G4[P] MSO structure agrees (LONG: trend BULL and osc>50; SHORT: trend BEAR and osc<50). MSO forces osc >50 in bullish / <50 in bearish structure, so G4 = structure agreement; strength is scored separately.
G5[P] MSO_CHOCH or MSO_BOS in direction confirmed at/after sweep_time.
G6[P] no opposing MSO_DIV confirmed within [T]div_lookback_bars.
G7[P] valid TradePlan (§7): reward:risk 1:2 to 1:3; stop ≥ [T]min_stop_ticks.
G8[P] Phase + Guard + Risk + consistency + hedge lock approve ≥ minimum contracts.
SCORE (sizing only), weights [T]: CISD before C2 close 25 | CHoCH after sweep 20 (BoS only 10) | |osc−50| ≥ [T]osc_strength_min 15 | own TP rate ≥ [T]tp_rate_min (0 until 30 samples) 15 | bias aligned 15 | HTF MSO agrees 10 | session-open C1 (C1 opens 09:30 or 13:30 ET) default 0 | SMT (NQ/ES divergence at sweep) default 0. Optional items enabled only after passing §16.6. Weights normalized to 100. Score < [T]min_score(60) → no trade; NEUTRAL bias needs ≥ [T]neutral_min_score(75).
Entry [T]: market at close of first passing bar (default) or limit at CISD with timeout.
Expire after [T]max_wait_bars or half of C3.
Every skip stores a reason code (RR_BELOW_MIN, STOP_TOO_WIDE, STOP_TOO_TIGHT, C1_TOO_SMALL, COOLDOWN, HEDGE_LOCK, CONSISTENCY_CAP, …); skip-rate per reason is reported.

## 7. TRADE PLAN — REWARD:RISK MIN 1:2, MAX 1:3 [P]
```python
@dataclass(frozen=True)
class TradePlan:
    direction: Direction; entry: Decimal; stop: Decimal; take_profit: Decimal
    risk_pts: Decimal; rr: Decimal
    partial_price: Decimal | None = None; breakeven_price: Decimal | None = None

def build_trade_plan(d, entry, invalid, t2, tick, buffer_ticks, min_stop_ticks,
                     rr_min=Decimal(2), rr_max=Decimal(3)) -> TradePlan | Skip:
    s = d.sign
    stop = round_to_tick(invalid - s * buffer_ticks * tick, tick, away_from=entry)
    risk = (entry - stop) * s
    if risk <= 0: return Skip("STOP_INVALID")
    if risk / tick < min_stop_ticks: return Skip("STOP_TOO_TIGHT")
    rr_t2 = (t2 - entry) * s / risk
    if rr_t2 < rr_min: return Skip("RR_BELOW_MIN")
    tp = round_to_tick(entry + s * min(rr_t2, rr_max) * risk, tick, toward=entry)
    rr = (tp - entry) * s / risk
    if rr < rr_min: return Skip("RR_BELOW_MIN_AFTER_ROUNDING")
    return TradePlan(d, entry, stop, tp, risk, rr)
```
After a market fill: rebuild with the fill price; outside 2–3R → flatten ("RR_INVALID_AFTER_FILL"). Reports show gross R and net R after fees + slippage.

## 8. DRAWDOWN GUARD — CONDITIONAL HALF-CLOSE + BREAKEVEN [P]
Used ONLY where open-profit peaks move the loss limit (intraday trailing, not yet locked). EOD-drawdown accounts (this EVAL) → guard OFF in auto mode.
```python
def guard_active(acct, cfg) -> bool:
    if cfg.mode != "auto": return cfg.mode == "on"  # manual override in Risk UI
    return acct.drawdown_type == "intraday" and not acct.mll_locked

def apply_guard(plan, tick, fee_cover_ticks) -> TradePlan:
    partial = round_to_tick(plan.entry + (plan.take_profit - plan.entry) / 2, tick, toward=plan.entry)
    be = plan.entry + plan.direction.sign * fee_cover_ticks * tick
    return replace(plan, partial_price=partial, breakeven_price=be)

def runner_stop(plan, best_price, trail_r, tick) -> Decimal:  # trail_r ∈ [1.0, 2.0], default 2.0
    cand = round_to_tick(best_price - plan.direction.sign * trail_r * plan.risk_pts, tick, toward=plan.entry)
    return ratchet(plan.breakeven_price, cand, plan.direction)  # never looser, only tightens
```
GUARD ON: two brackets sharing the original stop — leg A = ceil(n/2) contracts, TP at partial_price; leg B = rest, TP at take_profit. On leg A fill → move leg B stop to breakeven; then runner_stop trails. If a stop modification fails → flatten remainder + pause account. Minimum 2 contracts. fee_cover_ticks = ceil(round_trip_fee_per_contract / tick_value).
GUARD OFF: one bracket, full size, original stop, TP; minimum 1 contract.
A trade keeps its mode until closed, even if the account locks mid-trade.
Early exits (C3 close; MSO CHoCH against) apply ONLY before price reaches +1R or the partial.
Nightly backtest compares guard ON vs OFF per stage; the Lab may only SUGGEST changing the mode.
Metric: trailing_cost = peak equity during trade − final equity. Guard ON post-partial ≤ 1R.

## 9. RISK ENGINE (100% test coverage)
risk_base = equity incl. open P&L − current MLL (never account size).
cfg = effective_risk_cfg(acct, base_cfg, eval_cfg)  # §11C
```python
def select_risk_pct(score, ctx, cfg) -> Decimal | None:
    pct = cfg.tier(score)  # standard 60–74→0.07, 75–89→0.09, ≥90→0.11; Evaluation Mode 0.10/0.12/0.14
    if pct is None: return None
    if pct == cfg.ceiling and not ctx.ceiling_allowed: pct = cfg.middle
    if ctx.force_floor: pct = cfg.floor
    return pct
```
risk_usd = pct × risk_base, capped at cfg.max_risk_usd when set (standard none; Evaluation Mode $140).
ceiling_allowed = first trade today AND last closed trade not a loss AND not in a streak-floor period AND trades_in_stage ≥ cfg.warmup_trades (standard 20, Evaluation Mode 10)
force_floor = losses_today > 0 OR today_net_r ≥ cfg.day_lockin_r (+2R day lock-in) OR dd_from_peak_base ≥ cfg.dd_floor_pct (20%) OR trades_in_stage < cfg.warmup_trades OR after cfg.streak_floor_losses (4) consecutive losses (until cfg.streak_release_wins (2) wins)
```python
def size_contracts(risk_usd, stop_ticks, tick_value, fee_rt, slip_ticks,
                   firm_max, internal_max, min_qty) -> int:
    per = stop_ticks * tick_value + fee_rt + slip_ticks * tick_value  # per contract
    n = min(int(risk_usd // per), firm_max, internal_max)
    return n if n >= min_qty else 0  # 0 → Skip("STOP_TOO_WIDE")
```
Stop for the day: 2 consecutive losses | risk + dll_safety_margin > DLL remaining | max_trades_per_day | (EVAL) today's profit ≥ consistency day stop (§11C).
Pause account: risk_base < $500 (manual review).
Kill switch: within $100 of MLL or any limit breach → flatten + disarm. With EOD drawdown the MLL is static intraday, but intraday equity touching it is still a breach — distance checked on every P&L update.
Pre-trade checks (logged with values): selected/armed/connected/mode; window/news; cooldown; size; worst case vs min(DLL remaining, MLL distance); internal stop; hedge lock; 1 open position; eval consistency cap; payout pending; external-positions attestation; active risk profile (STANDARD/EVALUATION).
Rapid-trade metric: % of profit from trades held ≤5 s; warn at 20% (firm limit 50%, VERIFY); strategy exits wait 6 s.

## 10. PHASE ENGINE + MLL TRACKER
```python
def update_mll(st, equity, eod: bool = False):
    if st.locked: return
    if st.drawdown_type == "intraday" or (st.drawdown_type == "eod" and eod):
        st.peak = max(st.peak, equity)
        st.mll = st.peak - st.max_loss
        if st.lock_trigger and st.peak >= st.lock_trigger:
            st.mll, st.locked = st.lock_level, True
```
EOD accounts: call update_mll(eod=True) once per session at Lucid's end of day with the settled balance; never trail intraday.
EVAL (EOD drawdown, DLL ON, consistency 40%): target $1,250; largest day ≤ 40% of total profit at pass (≥3 profitable days; day stop per §11C); $1,000 EOD drawdown — MLL starts $24,000, trails EOD peak, locks at $25,100 once EOD peak ≥ $26,100 (VERIFY); $600 DLL; news restricted (flat 1 min before to 1 min after high-impact USD) and blacked out by default. Target + consistency met → auto-disarm, "PASSED – awaiting Lucid" (Evaluation Mode auto-OFF).
FUNDED: intraday trailing until peak ≥ $26,100 → locked at $25,100 (drawdown type VERIFY). While trailing, risk_base ≤ $1,000 (the MLL follows the peak), so the base can only grow after the lock. DLL ON ($600); no consistency rule; news = HARD BREACH (flat 1 min before to 1 min after high-impact USD); $6,000 day → live move; payouts per §14.
LIVE: start $0; $1,000 EOD drawdown; lock trigger/level per config (VERIFY); internal limits apply.
Transitions: sync accounts at 18:00, 16:50 and every 15 min; new IDs → auto-classify + one-click confirm → apply profile; auto_arm_new_accounts (default false; allowed after checklist). Lucid flatten/close detected → never re-enter; any account LIVE → block household sim accounts + alert. Stage change away from EVAL → Evaluation Mode forced OFF + audit + notify.
Inactivity: alert at 21 days without a trade (Lucid deletes inactive accounts after 30 days and breached accounts not reset within 30 days, VERIFY).
Account limits: max 5 funded per household; max total accounts per config (VERIFY).

## 11. EDITABLE RISK MANAGEMENT (UI + API)
A) FIRM RULES: Risk → Firm Rules; typed "UPDATE FIRM RULES" + required note; clears VERIFY badge. Purchase profile (drawdown type, DLL on/off, consistency %) lives here.
B) MY SETTINGS: tiers, floor/ceiling, ceiling conditions, warmup trades, day lock-in R, daily stops, max trades, pause level, DLL margin, kill distance, internal max contracts, cushion target, cap guard, windows, news buffers, flatten times, model-fail cooldown, guard mode (auto/on/off) + runner trail, min stop ticks, payout frequency + skim mode, auto-resume, presets, Evaluation Mode values (§11C).
Validation (server-side; UI mirrors): never looser than firm rules; risk % bounds 1–15% (>11% → red warning + second confirmation); floor ≤ middle ≤ ceiling; times in session; cushion ≥ buffer + min payout; runner trail ≤ 2.0R; consistency day stop < consistency cap; day_lockin_r ≥ 1.0.
DLL test: first loss at ceiling + second loss at floor on the reduced base + 2×margin ≤ DLL, at the maximum risk base possible for the stage (EVAL EOD: $1,000 + day stop = $1,437.50; FUNDED: cushion $3,000), max_risk_usd applied. Defaults: funded 330 + 186.90 + 80 = 596.90 ≤ 600; eval standard 158.13 + 89.56 + 80 = 327.69 ≤ 600; Evaluation Mode 140 + 129.75 + 80 = 349.75 ≤ 600.
Workflow: edit → instant Impact Preview (risk $ per tier at bases 1,000/2,000/3,000, worst day, losses to pause) → WHAT_IF backtest → Save → versioned RiskProfile (author, time, diff, note) → applies to next NEW trade → one-click rollback.
Presets: "Plan Default 7/9/11", "Aggressive Same-Risk" (max 4 trades/day, MNQ+MES, both profiles), "Conservative 5/6/7", "Evaluation Mode 10/12/14" (EVAL only). Per-account overrides (inherit by default).

C) EVALUATION MODE (EVAL-only risk booster; UI button)
Purpose: raise risk per trade on EVAL accounts only so the $1,250 target is reachable in ~15 sessions (3 weeks; 20 max). Nothing else in the strategy changes.
Changes ONLY: tiers 60–74→0.10, 75–89→0.12, ≥90→0.14; floor 0.10; middle 0.12; ceiling 0.14; warmup_trades 10; max_risk_usd $140.
Never changes: gates, score, 2–3R, guard, DLL/MLL checks, daily stops, day lock-in, max trades, kill switch, $500 pause floor, 15% bound, hedge/news/flat-time rules, 1 position, force_floor. No martingale: never raises risk after losses or when behind pace.
Math basis: EVAL risk base ≈ $1,000 at session start when at the EOD peak → $100/$120/$140. $1,250 ÷ $140 ≈ 9R net. A full 3R win ($420) is below the $437.50 day stop, so expect ~1 full win per day and ≥3 winning days. The app shows the MEASURED projection; it never promises a pass date.
Button: header "EVAL MODE" toggle on every page (blue = OFF; gold + badge "EVAL MODE ON" = ON); disabled with tooltip if no EVAL accounts. Also on Risk page and per-account (inherit/on/off) on Accounts page (EVAL accounts only).
Enabling: modal with Impact Preview (risk $ per tier at bases 1,000/750/500, worst day $226, losses to pause 7, P(pass ≤15 / ≤20 sessions) and P(MLL hit) ON vs OFF) + typed "ENABLE EVALUATION MODE" (counts as the second confirmation for >11%). Disabling: one click.
Lifecycle: applies to next NEW trade; open trades keep their risk. Auto-OFF on PASSED, stage change or reclassification.
Consistency guard (EVAL, both profiles): cap = 40% × $1,250 = $500; day stop = (40 − 5)% × $1,250 = $437.50. Stop the day at today's profit ≥ day stop. Pre-trade: if today's profit + planned net reward at TP > cap → reduce contracts to fit (never below min contracts) else Skip("CONSISTENCY_CAP"). If a day still exceeds 40%, the pace card shows the extra total profit needed; trading continues normally.
Pace card (Dashboard + Risk), per EVAL account: profit / $1,250, profitable days (≥3), sessions used/left (target 15, max 20), required $/session, required R/session at current tier, measured E, projected pass date, largest-day headroom vs 40%, status ON PACE / BEHIND / AHEAD (information only — never changes risk).
Implementation: risk/eval_mode.py (pure): def effective_risk_cfg(acct, base_cfg, eval_cfg) -> RiskCfg — returns eval_cfg only if acct.stage == "EVAL" and eval mode is effective for that account; else base_cfg. Same function everywhere. Every toggle audited (user, time, accounts, profile version) + notification + WS event.

## 12. ACCOUNT SELECTOR (1–5)
Stepper 1–5 in header + Accounts page, "Trading N of M". Priority order (drag) or manual checkboxes. An account trades only if selected AND armed AND passing checks. Changing N affects new signals only. Max 5 funded per household. Sequential fan-out, independent checks, same direction only (§1.8); warning "N accounts on one signal = N× correlated exposure".

## 13. AUTOMATION CONTROLLER
Master mode (persisted; header on every page): OFF (signals only; manual ticket works) | SEMI-AUTO ("Approve & Execute" card: gates, score, %, $ risk, contracts, guard ON/OFF, Eval Mode ON/OFF per account, consistency headroom, countdown; buttons Execute All Selected / Execute on… / Skip; click re-runs all checks) | FULL-AUTO (auto-send to selected + armed accounts; notify each order).
Per-account Arm + mode override (only more restrictive). Manual Trade Ticket: symbol, side, market/limit, REQUIRED stop, TP must satisfy 2–3R; size preview; all checks; logged MANUAL.
Default: app starts OFF; only OFF/SEMI-AUTO for the first 5 sessions of each stage, then FULL-AUTO allowed.
Pre-flight (09:25 + on enabling): broker ok, token >2 h, heartbeat fresh, calendar, bias, no unconfirmed VERIFY (LIVE), reconciled, no orphan orders, external-positions attestation, clock drift <2 s. Fail → OFF + banner.
Auto-pause (scope account/global/profile): stale feed, disconnect, 2 order rejects, position mismatch, manual hedge, kill switch, daily stop, payout pending, pause floor, stop-modify failure, model-fail cooldown (profile).
Auto-resume: daily stops reset at 18:00; cooldown ends after its session count; feed/connection pauses resume after 3 healthy heartbeats + pre-flight if enabled (default on PAPER, off LIVE). Kill switch, mismatch, hedge and stop-modify pauses NEVER auto-resume.
Kill switch: flatten + cancel + disarm all + OFF. Flatten per account; FLATTEN ALL (confirm). News flatten 2 min before blackout; auto-flatten 16:40; hard flat 16:44 ET.

## 14. PAYOUT ENGINE + $70K PLAN TRACKER
Buffer $26,100 (Lucid min balance); cushion target $28,100 (risk base $3,000 after lock).
Weekly payouts (default; on-demand allowed by Lucid): every Friday 17:05 after close, per FUNDED account:
• Balance ≥ cushion + $500 → ticket = balance − $28,100 (full sweep).
• Else if MLL locked and skim_mode = half → ticket = 50% of this week's net profit, only if ticket ≥ $500 and balance − ticket ≥ $26,100; the other 50% stays to build the cushion.
• Else → no ticket; profit rolls to next week.
I submit on Lucid manually; marked submitted → account blocked until marked processed (block_trading_while_pending, default true; Friday cadence = weekend-only block). payouts.frequency: weekly (default) | on_demand (daily check).
Cap guard: total sim profit above buffers ≤ $10,000 (live-move cap $15,000).
Tracker: target $70,000 net (floor goal $50,000); 90% split; costs = tools ($1,500 est.) + $190 × evals bought (incl. resets); required E = (target + costs)/(0.9 × N × trades/yr × R_avg); table N = 1..5; measured E per guard mode (rolling-50/all-time); weekly payout history; pace; projection; go/no-go (E ≥ 0.20R to start, ≥ 0.30R target; PF ≥ 1.4; ≥ 150 trades/yr; worst streak keeps base ≥ $500).
Rolling-50 E < 0.20R → cap at floor % (standard and Evaluation Mode) + review banner.

## 15. BIAS, CALENDAR, SCHEDULE (ET)
TradingAgents 07:00 on proxy (NQ→QQQ, ES→SPY); pinned version; check README API; 10-min timeout. Five-tier map: BUY/OVERWEIGHT → LONG_ONLY, HOLD → NEUTRAL, UNDERWEIGHT/SELL → SHORT_ONLY, unknown/failure → NO_TRADE + alert. Store raw rating, reasoning, cost, accuracy. Output is non-deterministic and uses current data: never re-run it for past dates.
Schedule: 18:00 reconcile + reset + apply promotions + cooldown counters | 06:30 calendar → blackouts (no data = no trading) | 07:00 bias | 09:25 pre-flight | windows 09:35–11:30, 13:30–15:30 | 16:40 flatten | 16:44 hard flat | 16:50 sync | EOD MLL update at Lucid session close | 17:00 report + tracker + eval pace + inactivity | Fri 17:05 payouts | 17:15 nightly backtest + shadow | Sat 08:00 Lab cycle. All configurable.

## 16. BACKGROUND BACKTEST ENGINE
16.1 Data: Data Recorder (heartbeats + events), CSV import, optional market-data API (Phase 0). Checks: gaps, duplicates, timezone, rolls (back-adjusted for signals, real contract for P&L).
16.2 Replay through the SAME engines with §5.2 indicators; Sim fills (fees, 1-tick slippage, stop-first). Structure/divergence events used only from confirmation time.
16.3 Simulates Lucid rules per stage (eval target/40% consistency/min days, EOD trailing + lock, intraday trailing/locked MLL, DLL, news, flat times, weekly payouts + skim, cushion), guard ON/OFF and Evaluation Mode ON/OFF, for N = 1..5.
16.4 Outputs: trades, equity, E(R) gross and net, win/BE/TP rates, PF, max DD vs MLL, trailing_cost, days to pass/lock/cushion, weekly payout series, skip-rate by reason, cooldown days, violations (must be 0), breakdown by window/weekday/profile/tier/regime/risk profile.
16.5 Monte Carlo 10,000 block-bootstrap: P(pass), P(pass ≤15 / ≤20 sessions) Eval Mode ON vs OFF, P(MLL hit), P(DLL hit), P(pause), 12-month net by N, P(≥$50k), P(≥$70k).
16.6 Addition gate (MES, extra profile, 4th trade, SMT, session-open score item): own E ≥ 0.25R, ≥100 trades, no drop in blended E.
16.7 Bias in backtests: ONLY live-recorded bias. Periods without it run as an ablation pair (NEUTRAL vs bias filter OFF). Lab reports G2's contribution after ≥60 recorded sessions (suggest only — G2 is a pillar).
16.8 Jobs NIGHTLY/ON_DEMAND/WHAT_IF/SHADOW/PARITY; priority queue; cancel/retry; WS progress; cached by (data hash, config version, git SHA); reproducible.
16.9 Evaluation purchase gate (before buying evals): ≥100 backtest trades, E ≥ 0.20R net, PF ≥ 1.4, 0 violations, Monte Carlo P(pass ≤20 sessions) reported, 2-day demo + 5 SEMI-AUTO sessions clean.

## 17. SELF-IMPROVEMENT ENGINE
17.1 PILLARS (frozen): component roles; fractal definitions (incl. C2 closes back inside C1 = ON); gates G1–G8; 2–3R window; one entry per model; guard logic (when ON: half at 50% of TP, breakeven, trail ≤ 2R); bracket orders; firm rules; hedge lock/news/flat-time rules; consistency guard; model-fail cooldown; day lock-in; all risk % and §9 safety rules (suggest only); Evaluation Mode values and toggle (user only — Lab may report ON vs OFF but never enable, tune or toggle it); payout rules; kill switch; automation safety. Enforced by TUNABLE_PARAMS registry + test rejecting other keys + hash check on pillar modules.
17.2 TUNABLE (bounds): score weights 50–150% each (normalized) | session-open C1 weight 0–10 and SMT weight 0–15 (only after §16.6) | min_score 55–70 | neutral_min_score 70–85 | osc_strength_min 10–30 | tp_rate_min 35–55% | div_lookback 3–12 | c1_min_range_atr 0.4–1.0 | stop_buffer_ticks 2–8 | min_stop_ticks 12–40 | tp_rr_cap 2.0–3.0 | runner_trail_r 1.0–2.0 | max_wait_bars 3–10 | entry_mode | limit_timeout_bars 2–8 | no_entry_before_news_min 10–30 | disable 30-min slices inside my windows only | profile threshold $1,200–$2,000 | bias weight within bounds.
17.3 Weekly: walk-forward 60/20 sessions; Optuna in bounds; objective OOS net E − penalties (violation or <40 trades = disqualify); guards: ≥100 OOS trades, bootstrap 90% CI > 0, ≥ +0.03R, ≤25% range step, multiple-trial adjustment, neighbor stability → CHALLENGER in SHADOW ≥10 sessions/20 trades → proposal (diff, metrics, plain-English) → my approval (auto-promote only PAPER if enabled) → apply at next 18:00; max 1 per 14 days.
17.4 Auto-rollback if live rolling-30 E < champion's OOS lower bound. Never change code, use an LLM to rewrite logic, tune on test windows, or promote mid-session.

## 18. UI / UX (fully functional)
Branding: "Paytience" at top of EVERY page (incl. login/404/error); tab "Paytience · <Page>".
Font colors ONLY blue/gold:
`export const theme = { gold:"#D4AF37", goldLight:"#F2D27A", blue:"#3B82F6", blueLight:"#93C5FD", bg:"#0A1020", card:"#111A33", border:"#1E2A4A" };`
Gold = title/headings/key numbers; blue = links/buttons; light blue = body. WCAG AA test. Red/green only as small badges/icons; P&L uses ▲/▼ + sign.
Header (every page): Paytience | PAPER/LIVE | Automation OFF/SEMI/FULL | EVAL MODE OFF/ON | Accounts [1–5] "Trading N of M" | ET clock | flatten countdown | jobs indicator | status | KILL SWITCH | alerts.
Pages (real endpoints, no mock data, loading/empty/error states, keyboard accessible):
Login | Dashboard (account cards w/ stage, risk base, MLL/DLL distance, MLL locked badge, guard ON/OFF, Eval Mode badge, day lock-in badge, P&L, days since last trade; eval pace card incl. 40% consistency headroom + profitable days; cooldown banner per profile; approval queue; signal; bias (raw five-tier rating); blackouts; next Friday payout estimate; $50k/$70k progress) | Signals (G1–G8 table, score incl. optional items, %, plan prices, C1 range vs ATR, gross/net R, guard mode, risk profile, skip reason, per-account result) | Trade (mode panel, approvals, Manual Ticket, positions, orders, flatten, arm/disarm, pre-flight, external-positions attestation) | Accounts (mapping, stage, drawdown type, DLL, consistency %, profile, arm, override, Eval Mode inherit/on/off, 1–5 selector + priority, Lucid link, inactivity, history) | Risk (My Settings + Impact Preview + What-If + versions; Evaluation Mode panel + pace; day lock-in; model-fail cooldown; Firm Rules incl. purchase profile; gauges; kill log) | Backtest (jobs, results, guard ON/OFF compare, Eval Mode ON/OFF compare, bias ablation, skip reasons, weekly payout simulation, Monte Carlo incl. P(≥$50k)/P(≥$70k), CSV import) | Strategy Lab (champion/challenger, proposals, rollback, insights) | Payouts & Plan (weekly payout tickets: sweep vs skim, submitted/processed, frequency, skim mode, tracker, 12-month projection) | Connections (broker, webhook URL/secret, test alert, heartbeat, calendar, TradingAgents version) | Journal & Logs (search, snapshots, CSV) | Settings (mode, notifications, schedule, auto-resume, weights, checklist, purchase gate status).

## 19. API / WEBSOCKET / DB REFERENCE
REST: POST /api/webhook/tradingview | GET,PUT /api/automation | POST /api/automation/preflight | POST /api/attestation | GET /api/accounts, PATCH /api/accounts/{id}, PUT /api/accounts/selection | GET /api/signals, /api/signals/{id}, POST /api/signals/{id}/execute|skip | POST /api/orders/manual, /api/accounts/{id}/flatten, /api/flatten-all, /api/kill-switch | GET,PUT /api/risk/settings, POST /api/risk/preview, GET /api/risk/versions, POST /api/risk/rollback/{v} | GET,PUT /api/risk/eval-mode, POST /api/risk/eval-mode/preview, PATCH /api/accounts/{id}/eval-mode, GET /api/accounts/{id}/eval-pace | GET /api/cooldowns, POST /api/cooldowns/{profile}/clear (typed confirm) | GET,PUT /api/rules | POST,GET,DELETE /api/backtests[/{id}] | GET /api/gate/purchase | GET /api/lab/proposals, POST .../{id}/approve|reject, POST /api/lab/rollback | GET /api/payouts, GET,PUT /api/payouts/settings, POST /api/payouts/{id}/submitted|processed | GET /api/plan | GET /api/logs, /api/journal | POST /api/auth/login|logout.
WS events: signal.updated, approval.created|expired, order.updated, position.updated, account.updated, risk.alert, risk.eval_mode.changed, risk.day_lockin, cooldown.changed, payout.ready, automation.changed, job.progress, system.status, notification.
Tables: users, accounts (+ eval_mode inherit|on|off, drawdown_type, dll_enabled, consistency_pct, last_trade_at), account_stage_history, rule_profiles(v), risk_profiles(v, kind standard|evaluation), strategy_configs(v, champion/challenger), signals (+ skip_reason, model_key, c1_range_atr), signal_gates, trade_plans, orders, fills, trades (+ risk_profile_kind, gross_r, net_r), daily_account_stats (+ day_profit, day_net_r, consistency_ratio), cooldowns (profile, until_session, streak), bias_decisions (raw_rating, mapped, version), attestations, payouts (+ kind sweep|skim, week), bars, events, backtest_runs, backtest_trades, optimizer_runs, proposals, audit_log(append-only), notifications.

## 20. SECURITY
Webhook secret + HTTPS on port 443 (TradingView webhooks only use ports 80/443; Cloudflare Tunnel guide); optional TradingView source-IP allowlist; localhost binding default; Argon2 dashboard login; CSRF; rate limits; encrypted tokens; no secrets in logs; .env.example only.

## 21. TESTING & DEFINITION OF DONE  (transcribed from screenshots)
Exact unit cases (MNQ tick 0.25 = $0.50; buffer 4 ticks; fee_rt $1.50 placeholder; min_stop_ticks 20):
• Plan: entry 20000, invalid 19981 → stop 19980, risk 20; t2 20070 (3.5R) → TP 20060 (3R); guard ON → partial 20030, BE 20000.75 (3 fee ticks); t2 20050 → TP 20050, partial 20025; t2 20035 (1.75R) → Skip. Stop 4 pts (16 ticks) → Skip("STOP_TOO_TIGHT").
• Runner (trail 2R = 40 pts): best 20055 → stop 20015; best 20035 → stays at BE.
• Sizing: $70 risk, 16-pt stop → per contract 32+1.5+0.5 = 34 → 2 (guard ON ok); 20-pt stop → 42 → 1 → guard ON skip, guard OFF 1.
• Tiers: base 1000 → 70/90/110; base 3000 → 210/270/330.
• Day: loss 330 → base 2670, DLL left 270 → 7% = 186.90, +40 ≤ 270 → second loss → stopped; total 516.90 < 600.
• Streak: one 11% + seven 7% losses from 1000 → ≈535 ≥ 500.
• Day lock-in: today +2.0R net → next trade at floor %; +1.9R → tier unchanged.
• C1 filter: C1 range 30 pts, HTF ATR 60 → 0.5 < 0.6 → Skip("C1_TOO_SMALL"); range 40 → 0.67 → pass.
• Cooldown: 3 consecutive MODEL_FAILED on MNQ-TIGHT → TIGHT paused 5 sessions, STD unaffected; a TP between failures resets the streak.
• Session-open item: weight 0 → score unchanged; C1 opening 09:30 with weight 10 → +10 before normalization (only after §16.6).
• Guard decision: eval EOD → OFF; funded intraday unlocked → ON; funded locked → OFF; live EOD → OFF; mode kept mid-trade.
• MLL EOD eval: start 24,000; intraday equity 25,400 → MLL unchanged; EOD balance 25,400 → MLL 24,400; EOD peak 26,100 → locked 25,100; intraday touch of MLL → breach.
• MLL funded intraday: peak 25,600 → MLL 24,600, risk_base ≤ 1,000; peak 26,100 → locked 25,100; equity 27,100 → base 2,000.
• Eval Mode tiers: base 1000 → 100/120/140; base 1,400 intraday → capped 140.
• Eval Mode day: loss 140 → base 860, DLL left 460 → 10% = 86, +40 ≤ 460 → second loss → stopped; total 226 < 600.
• Eval Mode streak: one 14% + five 10% losses from 1000 → ≈507.82 ≥ 500; sixth → ≈457.04 → pause.
• Eval Mode scope: FUNDED/LIVE with eval_mode=on → standard profile; EVAL→FUNDED → auto-OFF + audit; open trade keeps its risk.
• Consistency 40%: cap $500, day stop $437.50; one 3R win $420 → trading continues; today +$100 + planned $420 → $520 > $500 → reduce contracts or Skip("CONSISTENCY_CAP"); today ≥ $437.50 → day stopped; pass requires ≥3 profitable days.
• Hedge lock: TIGHT LONG open on acct A; STD SHORT (or MES short) for acct B → Skip("HEDGE_LOCK").
• One entry per model: STOP, then same c1_time_ms re-confirms → no entry.
• Bias: OVERWEIGHT → LONG_ONLY; UNDERWEIGHT → SHORT_ONLY; unknown text → NO_TRADE + alert.
• Divergence timing: pivot at bar t, right = 3 → event usable only from bar t+3.
• Webhook: empty extra → valid JSON; 15m/1H HEARTBEAT not stale (age from time_close); response < 1 s.
• Weekly payouts: Fri balance 28,700 → sweep $600; locked, balance 27,400, week profit +$1,100, skim half → $550 (27,400 − 550 ≥ 26,100 ✓); week profit +$800 → $400 < $500 → none; unlocked → none; submitted → blocked until processed.
• Inactivity: 21 days without a trade → alert.
Property tests: risk ≤ min(ceiling × base, max_risk_usd) and ≤ DLL remaining − margin (both profiles); eval profile never selected unless stage == EVAL; no two opposite EQUITY_INDEX positions ever coexist; payout never leaves balance < $26,100; guard ON post-partial trailing_cost ≤ 1R; optimizer never writes non-tunables, eval_mode, cooldown, lock-in or payout keys.
Integration: webhook → orders (Sim + Tradovate demo); backtest vs replay identical decisions (Eval Mode ON and OFF).
Playwright: "Paytience" on every page; all buttons; OFF/SEMI/FULL; EVAL MODE toggle → preview → typed phrase → gold badge → OFF; approvals; manual ticket; selector 1–5; risk edit → preview → save → rollback; cooldown banner + clear; payout ticket (sweep/skim) submit/process; attestation; backtest job; kill switch; contrast.
Live-Readiness Checklist: VERIFY confirmed (incl. purchase profile: EOD, DLL ON, 40%); parity passed; purchase gate §16.9 passed; 2-day demo practice run clean; first 5 sessions per stage in SEMI-AUTO clean; kill switch, auto-pause, stop-modify failure, payout block, hedge lock, cooldown and Eval Mode scope/auto-OFF tested. Done = all green, no TODOs in trading paths, README complete.

## 22. BUILD PHASES (stop after each)
0 Questions, file tree, CLAUDE.md, broker + data decisions | 1 Scaffold, config, DB, audit, Docker | 2 Pine bridge/parsers (+ HTF ATR), Python indicators, parity, webhook | 3 Confluence + filters (C1 range, cooldown, one-per-model) + TradePlan | 4 Guard + Risk (day lock-in) + Phase engines (EOD MLL + lock) + Evaluation Mode + consistency + hedge lock + validation | 5 Automation, selector, execution, adapters, kill switch | 6 Core UI (header incl. EVAL MODE button, Dashboard, Trade, Accounts, Risk, Connections) | 7 Payouts (weekly sweep/skim) + tracker + calendar + bias + scheduler + inactivity | 8 Backtest + workers + Monte Carlo + purchase gate §16.9 → START EVALS | 9 Lab + shadow | 10 Remaining UI pages + E2E | 11 Replay report, README, hardening.

## 23. config/rules/lucid_daily_25k.yaml (as specified; the repo file carries later approved changes)
```yaml
account_size: 25000
purchase: {drawdown_type: eod, dll_enabled: true, consistency_pct: 40}   # VERIFY
max_contracts: {minis: 2, micros: 20}   # VERIFY
eval:
  profit_target: 1250
  consistency_max_day_pct: 40     # VERIFY
  min_profitable_days: 3
  max_loss_limit: 1000            # VERIFY
  drawdown_type: eod
  daily_loss_limit: 600           # VERIFY
  lock_trigger: 26100             # VERIFY
  lock_level: 25100               # VERIFY
  news_allowed_by_firm: false     # VERIFY
  news_breach_min_before: 1
  news_breach_min_after: 1
funded:
  max_loss_limit: 1000
  drawdown_type: intraday         # VERIFY
  lock_trigger: 26100
  lock_level: 25100
  daily_loss_limit: 600           # VERIFY
  consistency_max_day_pct: null
  news_breach_min_before: 1
  news_breach_min_after: 1
  max_daily_profit_live_trigger: 6000
  payout: {split: 0.90, buffer: 26100, min_request: 500, min_cycle_profit: 1}   # VERIFY all
live: {starting_balance: 0, max_loss_limit: 1000, drawdown_type: eod, lock_trigger: 1100, lock_level: 100, sim_payout_cap_on_move: 15000}   # VERIFY all
session: {flat_by: "16:45", reopen: "18:00"}   # VERIFY
behavior:
  min_hold_seconds: 6
  rapid_trade_warn_pct: 20
  firm_microscalp_pct: 50         # VERIFY
  no_hedging: true
  hedge_lock_scope: EQUITY_INDEX
  max_funded_per_household: 5
  max_total_accounts: 10          # VERIFY
  max_open_positions_per_account: 1
  inactivity_alert_days: 21
  firm_inactivity_delete_days: 30 # VERIFY
instruments:
  MNQ: {tick: 0.25, tick_value: 0.50, fee_rt: 1.50, enabled: true}    # VERIFY fees
  MES: {tick: 0.25, tick_value: 1.25, fee_rt: 1.50, enabled: false}
trade_plan: {rr_min: 2.0, rr_max: 3.0, stop_buffer_ticks: 4, min_stop_ticks: 20, slippage_ticks: 1, one_entry_per_model: true}
filters:
  c1_min_range_atr: 0.6           # tunable 0.4–1.0
  htf_atr_period: 14
  model_fail_cooldown: {streak: 3, sessions: 5}   # my setting, not Lab-tunable
score:
  session_open_c1_weight: 0       # tunable 0–10, only after §16.6
  session_open_times: ["09:30", "13:30"]
  smt_weight: 0                   # tunable 0–15, only after §16.6
drawdown_guard: {mode: auto, partial_fraction_of_tp: 0.5, partial_qty: ceil_half, runner_trail_r: 2.0, min_contracts_on: 2, min_contracts_off: 1, early_exits_until_r: 1.0}
internal:
  risk_pct_by_score: {60: 0.07, 75: 0.09, 90: 0.11}
  risk_pct_floor: 0.07
  risk_pct_middle: 0.09
  risk_pct_ceiling: 0.11
  risk_pct_absolute_bounds: [0.01, 0.15]
  max_risk_usd: null
  warmup_trades: 20
  day_lockin_r: 2.0
  dd_floor_pct: 20
  streak_floor_losses: 4
  streak_release_wins: 2
  pause_below_risk_base: 500
  dll_safety_margin: 40
  max_trades_per_day: 3           # Aggressive preset: 4
  max_consecutive_losses_per_day: 2
  internal_max_micros: 10
  kill_switch_mll_distance: 100
  cushion_target_balance: 28100
  cap_guard_total_above_buffer: 10000
  consistency_day_stop_buffer_pct: 5
  auto_flatten: "16:40"
  hard_flat: "16:44"
  windows: [["09:35","11:30"], ["13:30","15:30"]]
  no_entry_before_news_min: 15
  news_flatten_before_min: 2
eval_mode:                        # §11C — EVAL stage ONLY
  default_on: false
  applies_to_stages: [EVAL]
  confirm_phrase: "ENABLE EVALUATION MODE"
  risk_pct_by_score: {60: 0.10, 75: 0.12, 90: 0.14}
  risk_pct_floor: 0.10
  risk_pct_middle: 0.12
  risk_pct_ceiling: 0.14
  max_risk_usd: 140
  warmup_trades: 10
  target_sessions: {target: 15, max: 20}
  auto_off_on_stage_change: true
  pace_escalation: false          # never raise risk to catch up
bias:
  provider: tradingagents
  pinned_version: "SET_IN_PHASE_0"
  proxy: {NQ: QQQ, ES: SPY}
  timeout_min: 10
  rating_map: {BUY: LONG_ONLY, OVERWEIGHT: LONG_ONLY, HOLD: NEUTRAL, UNDERWEIGHT: SHORT_ONLY, SELL: SHORT_ONLY}
  unknown: NO_TRADE
  backtest_source: recorded_only
smt: {enabled: false, pair: [MNQ, MES]}
automation:
  default_mode: "OFF"
  accounts_to_trade: 5
  selection_mode: priority
  semi_auto_sessions_per_stage: 5
  auto_arm_new_accounts: false
  require_external_attestation: true
  auto_resume_after_recovery: {paper: true, live: false}
payouts:
  frequency: weekly               # weekly (Fri) | on_demand
  check_time: "Fri 17:05"
  sweep_above: 28100              # = cushion_target_balance
  skim_mode: half                 # half | off — 50% of week's profit after lock, before cushion is full
  block_trading_while_pending: true
purchase_gate: {min_trades: 100, min_e_net_r: 0.20, min_pf: 1.4, max_violations: 0, demo_days: 2, semi_auto_sessions: 5}
plan:
  annual_target_net: 70000
  annual_floor_net: 50000
  tools_annual: 1500
  eval_cost_per_account: 190
  trades_per_year_assumed: 250
  r_avg_assumed: 255
self_improvement: {enabled: true, auto_promote_paper: false, cooldown_days: 14, min_oos_trades: 100, min_improvement_r: 0.03, max_param_step_pct: 25}
```

## 24. UI ADDITIONS (v9.3)
24.1 Today page (default landing after login): bias + raw rating, today's high-impact events with blackout times, windows, armed/selected accounts, attestation, pre-flight result, cooldowns, eval pace summary; one "Ready to trade" button that runs pre-flight + attestation.
24.2 Trade Replay (Journal + Signals): TradingView Lightweight Chart per trade with C1/C2/C3 boxes, sweep, CISD level, entry/stop/TP/partial/BE/exit markers, MSO events at confirmation time, gate results and score breakdown. Works for live, paper and backtest trades.
24.3 "Why no trade?" panel (Dashboard + Signals): today's setups grouped by skip reason in plain English (e.g. "RR below 2R", "C1 too small", "hedge lock"), with counts vs the 20-session average.
24.4 Mobile/PWA: responsive layout, installable PWA, push notifications (approvals, fills, risk alerts, payouts), one-tap Approve/Skip with countdown, remote KILL SWITCH and FLATTEN ALL (typed or long-press confirm). Same auth + CSRF.
24.5 Rule-proximity meters per account card: MLL distance, DLL used, consistency headroom (EVAL), days since last trade; bands blue (safe) / gold (≥50% used) / red badge (≥80% used).
24.6 Daily P&L calendar heatmap (Payouts & Plan + Accounts): per-account and household; EVAL view marks the largest day and the 40% line; week totals feed the Friday payout estimate.
24.7+ — NOT RECEIVED (screenshots ended here).
