# Session 18 - Order-flow intraday study for MNQ (BLOCKED, no data)

Status 2026-11-11: **not run. No data could be downloaded.**

## What happened
- `metadata.get_cost` on hist.databento.com (GLBX.MDP3, MNQ.v.0, `trades` and `tbbo`, 2023-01-03..2026-11-07) returned
  **HTTP 403 `auth_account_locked`: "Your account has been locked for security reasons."** This is the Databento account behind the proxy.
  Nothing was downloaded and nothing was spent ($0).
- No local tick, trades, tbbo or MBO data exists in the repo or the container. The repo has only 1-minute OHLCV bars,
  which carry no aggressor side, so footprint, delta, imbalance and sweep signals can't be rebuilt from them.
  Using a proxy such as candle-body "delta" would not test real order flow, so I didn't.
- No numbers are reported, which keeps the rule that nothing is made up.

## Needed to unblock
The user unlocks the Databento account (log in or contact Databento support). Then re-run the cost check. Expected size:
`trades` RTH-only for 2023-2026 MNQ is the cheapest schema with aggressor side. Check the price before downloading and keep it under about $30;
if it costs more, sample days. MBO for iceberg detection is very likely too expensive, so skip it.

## Planned protocol (ready to run once data is available)
- Bars: 1m/5m footprint from `trades`: per-price bid/ask volume, bar delta, cumulative session delta, POC.
- Signals: (1) absorption at session low/high or prior-day H/L; (2) cumulative-delta divergence at a new N-bar or session extreme -> fade;
  (3) 3+ stacked 3:1 imbalances -> follow; (4) POC as magnet/target; (5) sweep bar through 3+ levels with large aggressive volume -> follow.
- Trade: 1 micro, stop 1 tick beyond the defended level, 2R target, flat 16:00 ET, fees and slippage as in session 17
  (next-bar open +/-1 tick, stop checked first).
- Pick on 2023, judge only on 2024-2026. Compare with the NOISE baseline (session 17 preset C HO: 427 trades, 52.2% win,
  $27.19/trade, PF 1.43, max DD $2,028, Pro 25K PASS 33% / BUST 64%) and with random entries using the same exits.
  Use the session-17 `sim.py` for the Pro 25K eval.
- Note: the user's YouTube videos could not be watched. The study uses only general published order-flow concepts.

## Verdict
None yet. No order-flow edge has been measured. Nothing should be built or switched on from this study.

---

# 1-year ESTIMATED order flow (cached MNQ.v.0 1m bars, 2026-11-11)

**Everything here is ESTIMATED order flow, not real order flow.** No tick data (Databento locked, no downloads). Signed volume per 1m bar =
close-location value ((C-L)-(H-C))/(H-L) x V, tick rule when H==L; aggregated to 5m "footprint-lite": bar delta, cumulative session delta,
session volume profile / POC from 1m closes, volume spikes. The teacher videos (Creamer AR Model, Mind Math Money, Jesse Rogers 4h) could
not be watched (YouTube blocked); only general published order-flow concepts and the Jesse Rogers chapter titles (VIDEO_CHAPTERS.md) were used.
**Gamma exposure skipped** (needs options data we don't have).

- Data: 2025-11-06..2026-11-05 only (user rule). PICK = 2025-11-06..2026-07-03 (~8 mo), JUDGE = 2026-07-06..2026-11-05 (~4 mo).
  **1 year is a small sample; the judge window has 9-40 trades per single signal, so every judge number is very noisy.**
- Trade: RTH, entries 09:35-15:30 on next 5m bar open +1 tick, stop 1 tick beyond the defended bar/level, target 1.5R or 2R, flat 16:00, 1 micro,
  $1 fee + 1 tick slip on every exit, max 3 trades/day, 1 position at a time. Eval = session-17 `sim.py` Lucid Pro 25K (boot = block bootstrap
  inside the window, 500 paths). Grid: heavy-delta k in {1,1.5,2} x avg|delta|(20), volume spike m in {1.5,2.5}, R in {1.5,2}; best picked on PICK PF only.
- Random = same timestamps and stop distance, random side (20 seeds). NOISE = session-17 preset C stream, same windows.
- Scripts: `of1y.py` (signals, combos, random) -> `of1y.json`; `of1y_ctx.py` (context filters) -> `of1y_ctx.json`.

## Per signal (params chosen on PICK), JUDGE window
| signal | params | PICK n / win% / PF | JUDGE n | win % | PF | $/trade | net | max DD | boot PASS/BUST % | med days | random $/tr, PF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Absorption | k1.5 2R | 10 / 10 / 0.22 | 4 | 50 | 1.97 | 36.75 | 147 | 92 | 3 / 0 | 183 | 3.2, 0.95 |
| Delta divergence | k1 2R | 453 / 39 / 1.17 | 240 | 30.4 | 0.97 | -1.27 | -306 | 1,417 | 28 / 72 | 27 | -3.5, 0.96 |
| Sweep+vol spike+reclaim | m1.5 2R | 74 / 31 / 0.71 | 34 | 35.3 | 1.01 | 0.91 | 31 | 1,510 | 38 / 61 | 68 | -15.7, 0.78 |
| POC rejection | k1.5 1.5R | 63 / 46 / 1.29 | 34 | 41.2 | 1.41 | 20.56 | 699 | 606 | 63 / 35 | 87 | **17.6, 1.39** |
| Stacked heavy delta | k1 1.5R | 93 / 45 / 1.10 | 40 | 40.0 | 0.75 | -20.29 | -812 | 1,548 | 12 / 87 | 63 | -3.6, 0.92 |
| Best combo (all 5) | k2 2R | 458 / 40 / 1.30 | 241 | 31.5 | 1.00 | -0.10 | -24 | 1,508 | 31 / 69 | 33 | -6.1, 0.86 |
| Best 2-combo (DIV+SWEEP) | k1 2R | 460 / 40 / 1.25 | 243 | 30.5 | 0.97 | -1.14 | -276 | 1,499 | 28 / 72 | 33 | -5.6, 0.88 |
| **NOISE preset C** | shipped | 100 / 57 / 1.44 | 49 | 51.0 | **1.72** | **52.53** | 2,574 | 977 | **67 / 33** | 23 | - |

NOISE full year: 149 trades, 55% win, PF 1.53, $39/trade, net $5,857, max DD $1,096.
POC rejection's judge result is matched by random sides at the same moments (PF 1.39) -> the timing/exit, not the "order flow", earns it.

## Context over signals (premium/discount, volatility regime) - with vs without, JUDGE PF (n)
PD_SESS = longs only below the session-range midpoint so far, shorts only above; PD_PREV = same vs prior session's midpoint;
VOL = skip days whose prior-session range is below the 33rd percentile of the trailing 60 sessions. Params re-picked on PICK per row.
| signal | none | PD_SESS | PD_PREV | VOL | PD_SESS+VOL | PD_PREV+VOL |
|---|---|---|---|---|---|---|
| Absorption | 0.56 (16) | 1.97 (4) | 0.59 (12) | 0.31 (13) | 0.31 (13) | 0.19 (10) |
| Delta divergence | 0.97 (240) | 0.95 (217) | 0.82 (202) | 0.90 (153) | 0.87 (140) | 0.65 (131) |
| Sweep | 1.01 (34) | 0.62 (25) | 0.79 (31) | 1.06 (18) | 0.67 (13) | 0.64 (17) |
| POC rejection | 1.77 (21) | 6.25 (22)* | 1.19 (31) | 1.24 (18) | 6.81 (12)* | 0.98 (19) |
| Stacked delta | 0.75 (40) | 2.07 (9) | 0.52 (15) | 0.48 (26) | 0.41 (6) | 0.18 (9) |
| All 5 | 1.00 (241) | 0.91 (222) | 0.90 (212) | 0.89 (152) | 0.84 (141) | 0.72 (135) |

\* POC + PD_SESS had PICK PF 0.92 / 1.13 (no edge on the picking data) and only 12-22 judge trades -> a lucky 4 months, not evidence.
VOL raised PICK PF for DIV/ALL (1.17->1.38, 1.30->1.37) but **lowered** every one of them on JUDGE -> overfit. PD_PREV hurt nearly everywhere.

## Verdict (plain)
Estimated order flow from 1-minute bars shows **no edge** on held-out data: every signal and combo is about break-even or losing in the judge
months, at or below random sides with the same exits, and far below NOISE (PF 1.72, $52/trade, PASS 67%). The context filters did not fix it
(the only "wins" come from 4-22 trades that also failed on the picking data). This does NOT prove real footprint order flow fails - CLV delta
is a crude stand-in for aggressor volume - only that this proxy is not tradable. 1 year is a small sample.

**Order Flow button parameters:** keep it **OFF / SHADOW-only** (no live or eval trading). If built for shadow logging, use:
signal = POC rejection, heavy delta k = 1.5 x avg|5m delta| (20 bars), target 1.5R, stop 1 tick beyond the bar low/high or POC,
entries 09:35-15:30 ET, flat 16:00, 1 micro, max 3/day, no context filter; label all deltas "estimated". Re-test with real `trades` data
(aggressor side) when Databento is unlocked before anything trades. NOISE stays the main strategy.

## Teacher CZT framework (Jesse Rogers 4h, strategy chapters only; TEACHER_RULES_4H.md) - same 1-year walk-forward, ESTIMATED order flow
Script `czt1y.py` -> `czt1y.json` (108 configs). Uses only the Condition / Zone / Trigger / Management rules (Delta, Absorption, Volume Profile,
Context/Premium-Discount, volatility). Gamma exposure skipped (no options data); LVNs and weekly profile not built.
- **Condition:** prior RTH volume profile from 1m closes (2-pt bins, 70% value area: POC/VAH/VAL). Open above VAH -> longs only, below VAL ->
  shorts only, inside -> reversals at VAL (long) / VAH (short) only. "Flat" day (prior value-area width < 20th pct of last 60) -> no trade.
- **Zone:** prior VAH/VAL/POC, overnight (18:00-09:30) high/low, 100-pt round numbers; touched within 2 ticks and closed back on the right side.
- **Trigger (5m, estimated delta):** ABSORB = heavy opposing delta (> k x avg|delta|) but close in the other half; EXHAUST = push into zone on
  volume < 0.7 avg and |delta| < 0.5 avg, close turning; AGGR = break through a zone in the lean direction with heavy same-side delta and the
  next bar holding beyond it (acceptance).
- **Stop** 1 tick beyond zone/bar (3 ticks off round numbers). **Exits:** fixed 2R vs teacher-style trail (after +1R, stop under the last
  15-min balance, ratchet only, no TP) vs trail capped at 3R; flat 16:00; max 2 attempts/day. Grid k in {1,1.5,2}, condition on/off.

| variant (picked on PICK PF, n>=25) | PICK n / win% / PF | JUDGE n | win % | PF | $/trade | net | max DD | boot PASS/BUST % | med d |
|---|---|---|---|---|---|---|---|---|---|
| Best on PICK: ABSORB, no condition, k1, trail3R | 31 / 35.5 / 1.43 | 16 | 18.8 | **0.51** | -24.47 | -392 | 570 | 0 / 59 | - |
| ABSORB, no condition, k1, trail | 31 / 32 / 1.15 | 16 | 18.8 | 1.14 | 6.91 | 110 | 570 | 47 / 35 | 112 |
| ABSORB+EXHAUST, no cond, k1.5, trail3R | 134 / 24 / 1.03 | 80 | 27.5 | 1.31 | 8.08 | 646 | 525 | 94 / 2* | 116 |
| Full CZT (condition ON, all triggers, k1.5, 2R) | 87 / 25 / 0.60 | 46 | 39.1 | 0.92 | -4.15 | -191 | 1,235 | 8 / 89 | 109 |
| Full CZT, trail | 86 / 20 / 0.59 | 46 | 34.8 | 0.86 | -5.48 | -252 | 1,014 | 0 / 89 | - |
| Full CZT, trail3R | 87 / 22 / 0.69 | 46 | 34.8 | 0.98 | -0.82 | -38 | 872 | 8 / 75 | 156 |
| Same, condition OFF, 2R | 221 / 32 / 0.95 | 110 | 38.2 | 0.96 | -2.27 | -250 | 2,046 | 21 / 79 | 47 |
| AGGR (continuation), cond ON, k2, trail3R | 25 / 32 / 1.06 | 9 | 33.3 | 0.90 | -4.39 | -40 | 384 | 5 / 20 | 176 |
| Generic estimated signals, best combo (above) | 458 / 40 / 1.30 | 241 | 31.5 | 1.00 | -0.10 | -24 | 1,508 | 31 / 69 | 33 |
| **NOISE preset C** | 100 / 57 / 1.44 | 49 | 51.0 | **1.72** | **52.53** | 2,574 | 977 | **67 / 33** | 23 |

\* PICK PF 1.03 (no edge where it was chosen); "PASS 94%" is the bootstrap of a slow, tiny-DD stream over 4 months - not evidence.
- The teacher's **condition filter made things worse** on the picking data (PF 0.95 -> 0.60) and did not help on judge (0.96 -> 0.92);
  with it, absorption fires almost never (1-2 trades) because a bar-level CLV delta rarely shows "heavy opposing delta" at the right zone.
- **Trail vs 2R:** no consistent winner; trail lowers win % (20-35%) and both are about break-even after costs.

## Final verdict (supersedes the one above)
Neither generic estimated order flow nor the teacher's CZT framework, rebuilt from 1-minute bars, shows an edge on the held-out 4 months:
the best picked variant collapses (PF 1.43 -> 0.51) and everything else sits around PF 0.9-1.0, far below NOISE. The likely reason is the data,
not necessarily the method: CZT is read from real footprint/aggressor volume, and CLV delta is a weak stand-in. 1 year (8+4 months) is a small sample.

**Order Flow button:** default **OFF**, SHADOW/paper logging only, never eval/funded, until re-tested on real `trades` data (Databento unlock).
Shadow parameters (teacher CZT as faithfully as bars allow): condition = open vs prior RTH value area (70%, 2-pt bins) with skip if prior
value-area width < 20th pct of 60 days; zones = prior VAH/VAL/POC, overnight high/low, 100-pt rounds (touch within 2 ticks); triggers =
absorption (|est. 5m delta| > 1.5 x avg of 20, close in opposite half) + exhaustion (vol < 0.7 avg, |delta| < 0.5 avg) + aggression with
1-bar acceptance; stop 1 tick beyond zone (3 ticks off round numbers); trail under last 15-min balance after +1R, cap 3R; max 2 attempts/day;
entries 09:35-15:30 ET, flat 16:00, 1 micro; all deltas labelled "estimated". NOISE stays the main strategy.
