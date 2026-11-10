# Session 13 — gate chain for NOISE + afternoon fade (MNQ): re-tune, MSO / divergence / LunqFX fractal, AI gate

Scope: NOISE + PM fade, MNQ, 1 micro ($250 / 124-pt stop), 5 years 2021-11 → 2026-10. Pick on 2021-11..2023-12 (IS), judge on 2024-01..2026-10 (HO, held-out).
Scripts: `features.py` (real MSO + LunqFX-fractal indicator code, per-minute states, closed bars), `study.py` (hooks + bust sim), `study2.py`, `causal.py`,
`study3.py`, `study4.py`; raw output `*.log`, `grid_*.json`. Baseline = the session-12 trade generators (reproduces 564 / 727 trades). `*.pkl` are not committed.
**Bust rate** = share of rolling-start Lucid Pro 25K eval attempts (EOD trailing $1,000 loss limit locking at +$1,100, target +$1,250, 1 micro,
trade-by-trade breach check, one attempt per start day, overlapping) that breach before hitting the target. It is noisy (overlapping starts, ±5–8 pts between near-identical
variants) — read it as a direction only. It is the plain 1-micro replay, NOT the live app (no D57 shrink, brake or Evaluation-Mode sizing).

## 1. What the gate chain really is for these two strategies
G2 (bias), G3 (model + score), G5, G7, the 100-point score and the 60 floor belong to the LunqFX confluence engine. NOISE / PM_FADE only pass: **G1** (instrument on,
window 03:00–09:30 + 09:35–15:30 ET, calendar loaded, news blackout 15 min before / 1 after), the optional **structure filter** (OB/SMT, D76; MSO divergence added now, OFF),
the **AI ledger** (D72, advisory until proven) and then the **pillar risk checks** (G8: sizing, DLL/MLL, consistency, hedge lock, kill switch). Pillars are untouched.
Windows already cover 10:30–15:30 (NOISE checks) and 13:00–15:29 (fade): nothing to re-tune there. The news blackout and calendar cannot be replayed (no historical calendar in the cache) — not measured.

## 2. (A) vs (B) re-tuned gate knobs  (block % = trades removed vs A)
| variant | IS n / win / profit / bust | HO n / win / profit / bust | verdict |
|---|---|---|---|
| **A current** (hindsight NOISE-day set, as validated in D55) | 564 / 48.6 / $9,363 / 31.5 | 727 / 51.0 / $15,982 / 33.9 | baseline, 1.04 and 1.03 trades/day |
| max 1 NOISE entry/day | 494 / 47.8 / $5,467 / 39.3 | 617 / 51.5 / $11,449 / 22.3 | IS worse |
| max 2 | 557 / 48.1 / $8,213 / 35.9 | 711 / 51.2 / $15,918 / 33.1 | IS worse |
| fade band 1.5 / 2.5 sd | 598 / 49.3 / $8,551 | 783 / 51.5 / $14,222 | profit down both halves |
| drop NOISE 10:30 + 11:30 checks | 449 / 53.0 / $7,584 / 17.0 | 582 / 54.3 / $10,564 / 33.4 | win up, profit −19% / −34% |
| drop any single NOISE hour | 6.5–11% blocked | | none beats A on win AND profit in both halves |
| **fade start earlier (10:00 … 12:00)** | 592–608 / 52.5–59.2 / $13.0–16.0k | 778–815 / 54.5–57.7 / $20–23k | **LOOKS great but is hindsight — see below** |

**Important correction (hindsight).** The validated fade only trades on days when NOISE never trades *all day*. That is unknowable live ("no NOISE trade yet").
`causal.py` re-simulates it causally (fade allowed only if no NOISE signal has fired yet; NOISE signals later still trade unless the fade is open):
| | IS n / win / profit / bust | HO n / win / profit / bust |
|---|---|---|
| A hindsight (D55 numbers) | 564 / 48.6 / $9,363 / 31.5 | 727 / 51.0 / $15,982 / 33.9 |
| **A causal, fade 13:00** (what live can do) | 578 / 47.2 / $6,269 / 48.3 | 740 / 50.0 / $12,270 / 44.5 |
| causal fade from 10:00 | 692 / 61.3 / $9,647 / 28.3 | 936 / 56.6 / $8,009 / 64.6 |
| causal from 11:00 / 12:00 | 644 / 56.2 / $2,650 | 865 / 54.9 / $5,809 |
| causal from 11:30 / 12:30 / 13:30 | 51.7 / 50.2 / 48.8 → $2.9k / $2.7k / $4.8k IS | 835 / 797 / 769 → $14.7k / $9.8k / $9.9k |
So the earlier-fade "gain" is look-ahead; causally every earlier start is worse in at least one half. **B = no change: window 13:00–15:29, band 2 sd, max 3 stay.** Side finding
(open item 4 of the handoff, now quantified): the live-realistic definition costs about **−$3.1k IS / −$3.7k HO (−25%)** and +10 pts bust vs the validated numbers. The app's projections
use the hindsight set, so they are optimistic by roughly that much.

## 3. (C) Structure gates on top of A/B — block rate, win rate, trades/day, profit, bust
Applied to NOISE (N), fade (F) or both (B). Keep rule: IS pick, then HO win AND profit both up.
| gate | block % IS / HO | IS win / profit / bust | HO win / trades/day / profit / bust | keep? |
|---|---|---|---|---|
| MSO structure 1m agree (N) | 5.9 / 6.0 | 49.0 / $8,438 / 33.5 | 50.5 / 0.97 / $14,861 / 41.1 | no |
| MSO structure 1m agree (B) | 38 / 41 | 46.7 / $8,288 / 16.3 | 43.9 / 0.60 / $10,073 / 48.1 | no |
| MSO structure 5m agree (N) | 4.4 / 4.7 | 48.2 / $7,314 / 28.3 | 51.7 / 0.98 / $16,896 / 29.5 | no (IS worse) |
| MSO structure 5m agree (B) | 35 / 36 | 44.8 / $5,596 / 27.0 | 46.4 / 0.66 / $12,123 / 39.4 | no |
| MSO divergence 1m, no opposing div 30 min (N) | 12 / 8 | 50.1 / $10,143 / 14.3 | 51.9 / 0.95 / $10,243 / 42.0 | no (HO profit −36%) |
| MSO divergence 1m 60 min (B) | 31 / 27 | 49.9 / $9,892 / 9.3 | 52.2 / 0.76 / $9,591 / 45.0 | no |
| **MSO divergence 5m, 30 min (N)** | 0.5 / 1.0 | 48.7 / $9,474 / 31.5 | 51.4 / 1.02 / $16,392 / 33.9 | passes the rule on paper but only ~5 trades differ: **noise, left OFF** (flag built) |
| MSO divergence 5m 120 min (B) | 10 / 14 | 48.4 / $7,920 / 23.7 | 51.8 / 0.89 / $17,131 / 31.7 | no (IS worse) |
| LunqFX fractal 15m agrees (N) | 45 / 44 | 52.9 / $3,758 / 26.9 | 55.6 / 0.58 / $7,037 / 26.1 | no (profit −56%) |
| LunqFX fractal 60m agrees (N) | 56 / 55 | 52.4 / $1,227 / 31.7 | 59.2 / 0.46 / $5,414 / 26.6 | no (profit −66%) |
| LunqFX fractal 15m not-opposed (N) | 37 / 35 | 52.8 / $6,432 / 25.9 | 53.2 / 0.67 / $5,920 / 32.7 | no |
Full 51-row table: `study3.log`. Plain verdict: **Big Beluga structure, Big Beluga divergence and LunqFX fractal do NOT make a difference that helps** — the fractal and structure gates raise win rate a few
points only by throwing away 35–55% of the trades and most of the profit; NOISE already trades with the move, and the fade trades against it, so "structure agrees" removes the fade's edge.
Set (C) = nothing kept (set (C) = set (B) = A).

## 4. (D) AI gate (TradingAgents + Vibe-Trading) — ESTIMATE, not real data
No real ledger rows exist (the AI key is not connected, no calls recorded), so accuracy is SIMULATED: each day the call is right with probability p about the session's open→close
direction, a share "cov" of days has a strong both-tools-agree call, and a trade against the call is blocked (4 seeds averaged; strong calls assumed no more accurate than average). Block % is
measured as trades removed vs A. Real tools are published at 50–56% (see session 11), so 55% is the honest expectation.
| accuracy | share of days with a call (≈ block %) | HO block % | IS win / profit / bust | HO win / trades/day / profit / bust |
|---|---|---|---|---|
| A (no AI) | – | 0 | 48.6 / $9,363 / 31.5 | 51.0 / 1.03 / $15,982 / 33.9 |
| 55% | 10% / 25% / 50% / 100% | 4.7 / 11.8 / 24.3 / 47.9 | 48.4 $8.6k · 48.8 $8.2k · 48.9 $7.9k · 49.8 $6.7k | 51.0 $15.3k · 51.3 $16.7k · 50.6 $10.6k · 50.5 $6.5k (bust 39.5 / 29.9 / 40.3 / 44.8) |
| 60% | same | 4.4 / 11.7 / 23.5 / 47.0 | 48.6 $8.9k · 48.8 $8.3k · 49.4 $8.4k · 50.3 $7.8k | 51.0 $15.4k · 51.5 $17.1k · 50.6 $11.9k · 49.6 $6.0k (bust 40.1 / 30.1 / 39.5 / 43.0) |
| 65% | same | 4.2 / 11.4 / 22.8 / 46.5 | 48.7 $9.2k · 49.0 $8.8k · 50.2 $10.1k · 51.2 $9.4k | 51.0 $15.7k · 51.5 $17.1k · 50.8 $12.8k · 50.3 $8.3k (bust 40.0 / 29.8 / 37.0 / 37.8) |
| 70% | same | 4.1 / 10.8 / 23.2 / 45.4 | 48.8 $9.3k · 49.2 $9.1k · 50.0 $10.5k · 52.0 $10.9k | 51.0 $15.7k · 51.5 $17.1k · 50.7 $13.5k · 50.7 $10.6k (bust 40.4 / 29.0 / 36.0 / 33.1) |
| 100% (oracle, upper bound) | | 3.5 / 9.4 / 19.3 / 39.6 | 49.0 · 50.1 · 51.5 · 57.1 ($10.2k · $11.9k · $14.1k · $18.9k) | 51.1 · 51.4 · 51.4 · 52.6 ($16.7k · $18.2k · $18.8k · $22.6k) |
Column groups are the four coverage levels (light block ≈ 5%, ≈ 11%, ≈ 23%, ≈ 46% of trades).

**Reading it plainly.**
- **Light block (≈ 5–12% of trades) at 60 / 65 / 70% accuracy:** held-out win rate +0.0 to +0.5 pt, trades/day 1.03 → 0.91–0.99, profit +$0.1k to +$1.1k, bust a bit lower at the 11% level (≈ 30% vs 34%) — but in-sample the same variant LOSES $0.3k–$1.0k, and at 5% bust is worse. So a light block cuts few trades and nudges win rate up ≈ 0.5 pt, but profit/bust gains are not consistent across both halves: **not proven, small**.
- **Heavy block (≥ 23%)** raises IS win rate up to 52% at 70% but removes 20–45% of trades; held-out profit falls $2.5–5k (−16% to −66%) unless accuracy is ≈ 100%.
- Even a perfect day-direction oracle adds only +0.4 pt win rate at the light level, because NOISE already trades with the day. The AI gate is a small lever for this strategy at any realistic accuracy.
- Thresholds: the 60 / 65 / 70% required accuracy only decides WHEN the gate is allowed to block (needs ≥ 30 scored calls and Wilson lower bound ≥ threshold, so the true accuracy must be a few points above). A lower threshold lets it switch on earlier; at a real 55% tool, switching on at 60% would mostly be luck. Default stays **70%, advisory until proven**; now a config value: `strategy.ai_gate_min_accuracy` (0.55–0.95).

## 5. Final answer table (held-out 2024-26 unless noted)
| set | gates | IS win / $ / bust | HO win / trades per day / $ / bust |
|---|---|---|---|
| A | current (as validated, hindsight fade set) | 48.6 / $9,363 / 31.5 | 51.0 / 1.03 / $15,982 / 33.9 |
| A causal | same, live-realistic fade day rule | 47.2 / $6,269 / 48.3 | 50.0 / 1.02 / $12,270 / 44.5 |
| B | re-tuned config knobs | no variant beat A on both halves (causal check kills the fade-window gain) | = A |
| C | B + MSO structure / MSO divergence / LunqFX fractal | none kept | = B |
| D | C + AI (simulated 55–70%) | light block ≈ same win rate, mixed profit | not proven; stays advisory |

## 6. Built (config flags, nothing enabled that was not proven)
`strategy.ai_gate_min_accuracy` (0.70 default, validated 0.55–0.95; used by the NOISE AI gate and the ledger badge), `strategy.structure_filters.mso_div_filter` (default OFF, needs `enabled`), `/api/strategies`
now returns `gate_chain` (read from config), Strategy page shows it (ON/OFF, plain explanation, AI record). Tests: backend 631 passed (risk/management/phases 100%), frontend 55.
Open: the app's income/pass projections use the hindsight fade-day rule (≈ −25% when causal) — rebuild `main_strategy_5y.csv` with the causal rule and re-run the projections; decide with the user.
