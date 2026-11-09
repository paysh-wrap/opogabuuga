# aibias — TradingAgents + Vibe-Trading as ONE honest daily bias (MGC/GLD, MNQ/QQQ)

## Bottom line
- An LLM daily direction call can only help where direction-of-day changes trade outcomes: **MGC yes** (hindsight
  with-day 39% vs against 14% win), **MNQ no** (35% vs 36%). For MNQ any blocking only removes good trades.
- Even on MGC, blocking pays only at **≥ ~62–65% real accuracy**. Published evidence puts LLM next-day index
  direction near 50–55% (see Evidence). So: advisory by default, gate MGC only after the live ledger PROVES it.
- No backtest of the LLMs is possible or allowed (§15: no re-running on past dates). Everything below is a model of
  the effect at assumed accuracy + a live measurement plan. Not engine-confirmed.

## Simulation (agents/aibias/sim.py, bias_est.py logic, 1y D52/D54 engine stats)
Inputs: MNQ 169 tr (with-day 35% / against 36%), MGC 47 tr (39% / 14%), 85% of trades with the day
(STRATEGY_MAIN), win = +2.0R (≈ PF 1.12 at 36%), loss −1R. ΔR = change vs no bias (MNQ base +9.2R, MGC +2.7R).
| acc | MNQ always-block | MNQ strong-only (35% days) | MGC always-block | MGC strong-only | MGC agree-gate* |
|---|---|---|---|---|---|
| 50% | −4.6R (84 tr) | −1.6R | −1.4R | −0.5R | −0.6R |
| 55% | −4.3R | −1.5R | −0.8R | −0.3R | −0.3R (eff. acc 57%) |
| 60% | −4.1R | −1.4R | −0.3R | −0.1R | +0.0R (eff. 63%) |
| 65% | −3.8R | −1.3R | +0.3R (37% win) | +0.1R | +0.4R (eff. 69%, 39 tr) |
*agree-gate: block only when both tools say the same strong side; error correlation ρ=0.5 assumed (both LLMs read
the same news, so errors are NOT independent; at ρ=0 the effective accuracy would be higher, at ρ=1 no gain);
agreement on ~27% of days. Win-rate uplift is ≤ +2 pts in every row; at ≤ 60% every policy costs money.
Honest read: the bias adds ~+0.4R/yr on MGC at best (65%) and loses at likely accuracy → its value is mostly as
a measured, opt-in filter, never a default block. The current D50/D53 setup (TA strong rating blocks, VT can only
unblock) costs ≈ −1.5R/yr on MNQ and −0.3R on MGC at 55%.

## Design
(a) **Combine** (pure, `app/bias/policy.combine`): TA rating → side (+1/0/−1, strong = BUY/SELL); VT → side +
confidence. P(up) = 0.5 + shrink·(mean tool prob − 0.5), shrink 0.5 (shrinkage to the 50% prior; LLM
confidences are over-confident). `agree_strong` = TA strong AND VT same side AND VT conf ≥ 60.
(b) **Per-market policy**: `instruments.<SYM>.bias_matters` (rules YAML; MGC true, MNQ false). MNQ → always
NEUTRAL (advisory; may feed score only — but score-only with no measured edge is also off by default).
(c) **Calibration ledger**: new table `bias_calls(session_date, symbol, ta_raw, vt_dir, vt_conf, prob_up,
direction, agree_strong, mapped, reason, outcome_up NULL, hit NULL, brier NULL)`. Written at decision time
(before 06:45 ET); scored by a 16:45 ET job using the SAME definition as
bias_est.py: first 1m open vs last close of the app session (no lookahead: scored after close, used from the
next day on). Gate opens only when Wilson 90% lower bound of hit-rate over last 60 directional calls ≥ 0.60
(≈ raw ≥ 68% at n=30, ≥ 64% at n=60) AND Brier < 0.25, with ≥ 30 scored calls. Rolling hit-rate, Brier, n and
Wilson LB per market + per tool (TA alone, VT alone, combined, agree-only) on the Risk/Bias UI; gold "ADVISORY"
badge until GATED. Auto-revert to ADVISORY when the window drops below the bar (no manual re-arm needed: it only
narrows trading).
(d) **Better VT inputs**: add overnight (18:00–06:30 ET) high/low/range and position of price in it, prior RTH
high/low/close, gap vs prior close, ATR(14) daily, today's high-impact calendar events (app calendar, already
fetched 06:00), DXY/US10Y change for GLD. All known before the call; pure builder `bias_context()` from bars.
Timing: run at 06:15 ET (after calendar 06:00 / after the overnight session), not 02:40 — the London+Asia move
is then in the input. Must finish by 06:40 pre-flight; on timeout → advisory NEUTRAL (NOT NO_TRADE: a missing
opinion must not stop trading since its measured value ≈ 0 — needs user OK, it changes §15's failure rule).
(e) **Speed/cost**: TradingAgents config knobs (repo default_config): `selected_analysts` → ["market","news"]
(drop social/fundamentals — ETFs have no meaningful fundamentals), `max_debate_rounds`=1,
`max_risk_discuss_rounds`=1, quick model for analysts, deep model only for the judge; run GLD and QQQ in
parallel (asyncio.gather) with timeout 900 s. VT `--max-iter 6`. Run QQQ only if MNQ ledger tracking is wanted
(it never gates) — otherwise skip it and save half the cost.

## Code changes (patch: agents/aibias/aibias.patch — pure module + tests only, applied in a copy)
- NEW `backend/app/bias/policy.py`: `combine`, `score`, `wilson_lower`, `ledger_stats`, `gate` (in patch).
- `service.run_bias` (pseudo-diff, not in patch):
  `- mapped, note = vt.blend(mapped, outlook)`
  `+ call = policy.combine(raw, outlook and outlook.direction, outlook and outlook.confidence, pol[sym])`
  `+ stats = policy.ledger_stats(ledger.rows(s, sym))  # scored rows only, before today`
  `+ mapped, reason = policy.gate(call, stats, pol[sym]) if not alert else ("NEUTRAL"*, "ADVISORY_ERROR")`
  `+ s.add(BiasCall(...))`  (*needs user decision, see (d))
- NEW `app/bias/ledger.py` (I/O): `record_call`, `score_session(s, sym, sess, open_, close)` called by the
  scheduler after 16:44 flat; migration for `bias_calls`; `GET /api/bias/ledger` → stats per market/tool.
- `ta_runner.py`: read `TRADINGAGENTS_ANALYSTS`, `..._DEBATE_ROUNDS` env → `config[...]` before graph build.
- `vibe_trading.prompt`: accept the richer context dict; `run(..., max_iter=6)`.
- Config: `bias.min_calls 30`, `bias.gate_min_acc 0.60`, `bias.vt_min_conf 60`, `bias.shrink 0.5`,
  `instruments.MGC.bias_matters true`, `MNQ false` — config refuses gate_min_acc < 0.55 and min_calls < 20.

## Tests
- In patch, PASS (17 passed incl. existing test_vibe_trading.py): `tests/unit/test_bias_policy.py` — agreement
  only on strong same-side; MNQ never blocks; warm-up/unproven/Brier ≥ .25 stay advisory; gated only with proof;
  score/Brier/Wilson math.
- To add: ledger scoring uses only completed sessions (no lookahead: a row for today is never in today's stats);
  outcome = session open→close same as bias_est.py; failure path → advisory; property test: gate output ∈
  {NEUTRAL, side of call} (can never flip to the opposite side); `bias_context` uses only bars < run time.
Run: `cd agents/aibias/repo/backend && /home/user/opogabuuga/.venv/bin/python -m pytest -q tests/unit/test_bias_policy.py`

## Evidence (from prior knowledge; web not fetched this run — verify before citing to the user)
- TradingAgents (Xiao et al., arXiv 2412.20138): reports returns/Sharpe on a few US single stocks over ~3 months
  (2024 H1) — tiny sample, no index/futures, no directional hit-rate published; not evidence of > 55% daily accuracy.
- Lopez-Lira & Tang (2023, "Can ChatGPT forecast stock price movements?"): headline sentiment predicts next-day
  single-stock returns, strongest in small caps/negative news, decaying as adoption grows — not index direction.
- Index/ETF next-day direction is close to a coin flip for most published ML/LLM studies (~50–56%).
- Combining: agreement filters raise precision but cut coverage; correlated errors limit the gain; track Brier,
  shrink to the base rate, abstain when unsure, gate on a confidence-bound — all implemented above.

## Open questions for the user
1. OK to stop treating a failed/missing bias as NO_TRADE (→ advisory NEUTRAL)? 2. OK that MNQ bias never gates?
3. Move bias run from 02:40 to 06:15 ET? 4. Run QQQ at all (cost) if it can never gate?
