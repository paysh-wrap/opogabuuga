# Session 9 — strategy research (2026-11-09): "find the highest verified win-rate strategies"

User request: use every resource to find the best *verified* strategies (higher win rate and/or higher R:R), improve
TradingAgents + Vibe-Trading cohesion, implement only after confirmation if old parameters must change. Later in the
session the user narrowed the target to **Lucid Pro 25K accounts** (Flex only if its numbers change the picture).

## Protocol (binding for every result below)
- Data: Databento GLBX.MDP3 `MNQ.v.0` / `MGC.v.0` 1-minute OHLCV, 2019-05-06 → 2026-11-06 (≈ 2.6 M bars each, ≈ $19).
- Pick on **2019-05 → 2023-12**, judge unchanged on **2024-01 → 2026-11** (held-out). PASS = held-out expectancy > 0
  after costs AND PF ≥ 1.15 AND ≥ 100 held-out trades. Shared brief: `session9/BRIEF.md`.
- Costs per round trip, 1 micro: MNQ $1.00 + 1 tick slippage each side; MGC $1.60 + 1 tick each side. Stop-first
  when stop and target share a 1-minute bar. Flat by 16:40 ET (16:00 for RTH strategies), max 3 trades/day.
- News blackouts and open-trade (intraday) drawdown are NOT modeled → prop results are somewhat optimistic.

## Scoreboard (7 agents + independent verification)
| Family | Variants | Verdict | Best honest held-out row |
|---|---|---|---|
| **Noise-area intraday momentum, MNQ** (Zarattini, Aziz & Barbon 2024) | 26 + 12 robustness | **PASS** | hourly checks: 440 tr, **45.0% win, +$25.81/tr, PF 1.33** |
| Noise-area, MGC | 4 | FAIL | PF 0.73–0.95 |
| Opening-range breakout (Zarattini & Aziz 2023 + classic 5/15/30-min), MNQ + MGC | 39 | FAIL | in-sample pick: 419 tr, 44.6%, −$3.58/tr, PF 1.03; every 30-min variant loses in 2026 |
| Last-half-hour momentum (Gao et al. 2018; Baltussen et al. 2021) | 8 | FAIL | 45–49% win, costs eat it, sign flips |
| VWAP trend (1m/5m) | 6 | FAIL | 21–35% win, PF ≤ 1.09 |
| Mean reversion (VWAP-band fade, RSI(2), gap fill, prior-day sweep, opening-drive pullback) | 38 | FAIL | 60–69% win rates exist but need 62–68% to break even → all negative after costs |
| Gold session structure (Asian/London/COMEX ranges, sweeps, VWAP, fix fade, 20-day trend) | 40 | FAIL | all 36 base variants negative in-sample; session sweep-reversal ≈ 31% win |
| Literature + Moltbook | — | — | no published intraday strategy with both high win rate and positive after-cost expectancy; ICT/SMC: no credible independent evidence; Moltbook = crypto/memecoin chatter, nothing verifiable; no "secret" strategy exists |
| Existing app strategy (engine) | — | see "Engine" below | — |

## The only verified winner — MNQ noise-area momentum (reproduce: `tools/noise_area.py`)
Rules (RTH 09:30–16:00 ET): σ_t = mean |close_t / open − 1| for minute t over the previous 14 days; bands =
max(open, prior close)·(1+σ_t) and min(open, prior close)·(1−σ_t); every **60 min** from 10:00: close above the upper
band → long, below the lower → short (fill next bar open); exit when the hourly close crosses back through
max(band, VWAP) (long) / min(band, VWAP) (short); **emergency stop 1.0% of price** on every 1-minute bar; flat 16:00;
max 3 entries/day; roll guard (skip days with |open/prior close − 1| > 1.5%).

| Period (1 micro, net) | trades | win | avg $/tr | PF | max DD $ | worst trade / day |
|---|---|---|---|---|---|---|
| In-sample 2019-05 → 2023-12 | 727 | 44.3% | +15.28 | 1.32 | −1,466 | −335 / −446 |
| **Held-out 2024-01 → 2026-11** | **440** | **45.0%** | **+25.81** | **1.33** | −2,214 | −610 / −774 |
Per year: 2019 PF 0.88 · 2020 1.06 · 2021 1.41 · 2022 1.46 · 2023 1.44 · 2024 1.29 · 2025 1.50 · 2026 1.23.
- Verified twice: the momentum agent's code (paper 30-min version: 625 held-out tr, 40.5%, +$20.40, PF 1.28) and an
  independent re-implementation (581 tr, 40.6%, +$19.47, PF 1.28).
- Robust: all 12 combinations of lookback 7/14/21/28 days × checks every 15/30/60 min are profitable in BOTH periods
  (PF 1.08–1.34). Hourly checks had the best in-sample PF (1.31–1.34 at every lookback) → selected on in-sample data.
- Emergency stop: 0.3–0.5% stops cut winners (held-out PF 1.18); 1.0% keeps the edge (PF 1.33) and caps the worst
  trade at −$610 (was −$839). It exists for broker-side safety, not for performance.
- Pro-25K tweaks chosen a priori (max 1/2 trades a day, stop after the first loss): none beat the base on in-sample
  data (stop-after-first-loss was worse in both periods) → base kept.
- Published-edge decay is expected (McLean & Pontiff: ≈ −58% after publication). The paper appeared in 2024; our
  2025–2026 numbers are genuinely post-publication and still positive.

## Lucid 25K simulation (tools/sim25k.py — real consecutive held-out days, rolling starts, 1 micro)
| Account | eval pass | eval bust | median days to pass | funded: ≥1 payout | avg paid to you | value per eval bought* |
|---|---|---|---|---|---|---|
| **Pro 25K** (eval no DLL; funded DLL $600 soft) | **56.9%** | 42.2% | 38 | 52% | $726 | **≈ $413** |
| Pro 25K, no DLL anywhere | 56.9% | 42.2% | 38 | 53% | $738 | ≈ $420 |
| Flex 25K, no DLL (eval 40% consistency, 3 profitable days) | 38.8% | 47.9% | 66 | 66% | $1,411 | ≈ $548 |
| Flex 25K, DLL $600 on | 38.8% | 51.0% | 66 | 66% | $1,411 | ≈ $548 |
| 2 micros (Pro / Flex) | 49.9% / 35.4% | 50.1% / 58.1% | — | 28% / 50% | — | ≈ $124 / $308 |
| ORB in-sample pick (Pro 25K) | 34.3% | 63.5% | — | 2.5% | $12 | ≈ $4 |
*before the eval fee. The 25K DLL is soft (stops the session, never fails the account — docs/LUCID_RULES.md); at 1 micro
it binds on only 3 of ~720 days for this strategy, so DLL on/off barely matters. The 30-min paper version is fragile
under a DLL: on 2025-04-09 its first trade lost > $600 before a +$3,600 winner — the DLL would have cut the day at −$600.
User decision (2026-11-09): focus on **Pro 25K** unless Flex data changes.

## More trades per day/week? (user: "maximum amount of trades possible that don't break the plan")
| Option (held-out 2024-01 → 2026-11, 1 micro) | trades/week | win | $/tr | PF | Pro 25K pass / bust | verdict |
|---|---|---|---|---|---|---|
| **MNQ RTH, hourly checks (chosen)** | **3.0** | 45.0% | +25.81 | 1.33 | **57% / 42%** | keep |
| MNQ RTH, checks every 30 min | 4.1 | 40.6% | +18.70 | 1.27 | 48% / 49% | worse |
| MNQ RTH, max 5 entries/day | 3.1 | 44.8% | +24.64 | 1.32 | 57% / 42% | no gain (rarely > 3 signals) |
| MES alone (Micro S&P, same rules) | 3.3 | 40.6% | −5.87 | 0.87 | 0% / 71% | FAIL (in-sample PF 1.09) |
| MNQ + MES, one position per account | 4.1 | 41.8% | +11.24 | 1.17 | 29% / 71% | worse → MES stays OFF (user: "add it only if you need to") |
| MNQ London session 03:00–09:30 (hourly / 30-min) | 3.6 / 5.0 | 36.9% / 32.5% | −4.18 / −4.97 | 0.92 / 0.87 | — | FAIL (negative 7 of 8 years) |
Conclusion: ≈ 3 trades/week (≈ 0.6/day) on MNQ RTH is the most the verified edge supports; every way to add trades
found so far lowers the Pro 25K pass rate. (MES data cost ≈ $10; scripts in session9/verify/.)

## TradingAgents + Vibe-Trading (reports/aibias.md + tools/noise_biascheck.py)
- On the noise strategy, **89% of trades already go with the day** (393/440, 49% win, +$20,209); the 47 against-the-day
  trades lost −$8,851 (9% win). A daily call must be **≈ 70% accurate just to break even** as a hard filter
  (55% → $7,069 vs $11,358 without bias; 75% → $12,890). Published LLM next-day accuracy ≈ 50–56%.
- On the current fractal strategy (D52/D53): blocking MNQ costs money at every accuracy; MGC needs ≈ 62–65%.
- Recommended design (needs approval; pure module + 17 passing tests drafted in `session9/agents/aibias/aibias.patch`):
  combined call shrunk toward 50%; a side is blocked only when BOTH tools agree strongly; per-market `bias_matters`;
  a **calibration ledger** scoring every call against the session's open→close, shown on the UI (hit rate, Brier,
  Wilson bound) — the bias stays ADVISORY until ≥ 30 scored calls prove accuracy (≥ 60% for the fractal strategy on
  MGC, ≥ 70% for the noise strategy); Vibe-Trading gets overnight range, prior-day levels, gap, ATR, calendar; runs
  06:15 ET; TradingAgents with 1 debate round, market+news analysts only.

## Engine (existing LunqFX strategy)
See reports/engine.md (appended when the engine agent finishes).

## What implementing the winner would change (needs the user's confirmation — pillar conflicts)
1. §7 TradePlan pillar (R:R 1.5–2.5 fixed TP): the noise strategy has no fixed target (band/VWAP trailing exit + 1%
   emergency stop). Its fixed-2.5R version passes only barely (PF 1.17) and 1.5R/2.0R fail.
2. §6 confluence pillar: signals do not come from the LunqFX fractal/MSO; a new profile "NOISE" would run beside it.
3. Non-negotiable #1: live signals only via TradingView webhooks → needs a Pine indicator (Paytience_Noise.pine)
   computing the bands/VWAP and sending entry/exit alerts, or the app computing them from heartbeat bars.
4. Drawdown Guard 2-bracket mode and the 60–90 score tiers do not apply; risk = 1 micro on Pro 25K.
5. MGC: every separate gold test failed → recommend MGC OFF (or paper only) for Pro 25K.
