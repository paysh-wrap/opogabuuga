# Agent "momentum" — published intraday-momentum strategies on MNQ / MGC
Data: Databento `.v.0` 1-min, RTH bars 09:30–16:39 ET only, 2019-05 → 2026-11-06. IS = 2019-05→2023-12, HO = 2024-01→2026-11.
Costs per brief (MNQ $1 + 1 tick per market/stop fill; MGC $1.60 + 1 tick; limit TP no slip; stop-first on same-bar tie).
13 rule sets × 2 markets = 26 variants, all fixed before the HO run (code was first run on IS-only data). cap=3 is the
default (≤3 trades/day/market); uncapped in summary.csv. News blackouts NOT modeled. Roll guard: overnight gap > 1.5% →
prev close unknown (bands use the open only; last-half signals using prev close skipped).
R = distance entry→initial stop at entry; for reporting R is floored at 0.1% of price (a handful of trades had a stop
within 1–2 ticks of entry, which made R meaningless). $ figures are unaffected and are the primary metric.
Reproduce: `cd …/scratchpad/agents/momentum && nice -n 10 /home/user/opogabuuga/.venv/bin/python mom.py prep`
(writes summary.csv, per_year.csv; `prep` rebuilds the RTH cache from the CSVs).

## 1. Noise-area breakout — Zarattini, Aziz & Barbon (2024) "Beat the Market" (SPY)
Rules: o = 09:30 open; pc = prior 16:00 close. For minute m, move_m = |close_m/o − 1|; σ_m = mean of move_m over the
prior 14 sessions. UB = max(o,pc)·(1+σ_m), LB = min(o,pc)·(1−σ_m). Decide only at bar closes 10:00, 10:30 … 15:30:
close > UB → long, < LB → short, entry next bar open (market). Initial stop = max(UB,VWAP) long / min(LB,VWAP) short,
tick-rounded 1 tick beyond. Trailing exit: at each 30-min check, close beyond the current max(UB,VWAP)/min(LB,VWAP) →
exit next open (may re-enter/reverse at that check). Else exit 16:00 close. 1 contract (no vol-targeting).
Variant "1m": same but the trailing check runs every 1-min close. RR variants: resting stop at the initial stop + limit
target at k·R (k = 1.5/2.0/2.5), else exit 16:00.

| sym | variant (cap 3) | per | trades | /day | win% | avgW R | avgL R | exp R | $/tr | PF | maxDD R | streak |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | paper 30m trail+EOD | IS | 1078 | 1.47 | 40.4 | 3.14 | −1.70 | +0.253 | +10.97 | 1.24 | 40.7 | 10 |
| MNQ | paper 30m trail+EOD | **HO** | **625** | 1.47 | **40.5** | 3.06 | −1.69 | **+0.236** | **+20.40** | **1.28** | 57.1 | 9 |
| MNQ | 1m trail+EOD | IS | 1392 | 1.90 | 26.5 | 2.38 | −0.84 | +0.018 | +5.13 | 1.18 | 133.2 | 24 |
| MNQ | 1m trail+EOD | HO | 817 | 1.92 | 27.2 | 2.86 | −0.77 | +0.214 | +14.10 | 1.30 | 34.7 | 15 |
| MGC | paper 30m trail+EOD | IS | 913 | 1.46 | 34.7 | 2.13 | −1.31 | −0.119 | −1.40 | 0.93 | 151.5 | 12 |
| MGC | paper 30m trail+EOD | HO | 644 | 1.48 | 32.9 | 2.70 | −1.36 | −0.023 | −2.76 | 0.95 | 76.2 | 18 |
| MGC | 1m trail+EOD | HO | 840 | 1.93 | 21.0 | 2.32 | −0.77 | −0.122 | −10.24 | 0.73 | 111.0 | 26 |

Per year, MNQ paper version (cap 3): 2019 126 tr PF 1.03 $+0.62 · 2020 248 / 1.03 / +1.37 · 2021 219 / 1.36 / +13.74 ·
2022 272 / 1.24 / +15.53 · 2023 213 / 1.52 / +19.58 · **2024 212 / 1.44 / +23.52 · 2025 215 / 1.28 / +21.65 ·
2026 198 / 1.17 / +15.69** (win% 35–48). Positive every year; weak 2019–20 (lower price level → costs larger in R).
Uncapped is nearly identical (HO 630 tr, PF 1.27, $19.89).

### R:R-constrained versions (fixed target, resting stop) — reported separately
| sym | target | per | trades | /day | win% | avgW R | avgL R | exp R | $/tr | PF | maxDD R | streak |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MNQ | 1.5R | IS / HO | 1597 / 946 | 2.2 | 43.9 / 43.0 | 1.12 / 1.08 | −0.81 / −0.80 | +0.034 / +0.007 | +5.17 / +4.31 | 1.17 / 1.08 | 27 / 35 | 13 / 13 |
| MNQ | 2.0R | IS / HO | 1533 / 913 | 2.1 | 38.5 / 38.7 | 1.39 / 1.34 | −0.81 / −0.80 | +0.033 / +0.026 | +4.45 / +6.54 | 1.13 / 1.12 | 29 / 36 | 13 / 14 |
| MNQ | 2.5R | IS / HO | 1484 / 880 | 2.1 | 35.5 / 36.4 | 1.67 / 1.53 | −0.80 / −0.80 | +0.075 / +0.048 | +6.51 / +9.28 | 1.20 / 1.17 | 22 / 28 | 13 / 15 |
| MGC | 1.5/2.0/2.5R | HO | 923/896/870 | 2.1 | 33.8/30.4/27.2 | — | — | −0.15 | −8.5 / −8.7 / −10.7 | 0.78/0.79/0.75 | ~145 | 16–19 |
(avg win < k·R and avg loss > −1R because many trades exit at 16:00 before stop/target.)

**Verdict: MNQ paper version PASS** (HO exp +0.236R, $20.40/trade, PF 1.28, 625 trades). MNQ 1m-trail PASS on HO
(PF 1.30) but IS was marginal (PF 1.18, exp R ≈ 0) — less trustworthy. **MNQ 2.5R fixed target PASS** (PF 1.17,
+$9.28, 880 tr) — barely; 1.5R/2.0R FAIL (PF < 1.15). **MGC: FAIL in every form.**
Risks: avg loss −1.7R in the paper version — the 30-min, close-based trailing check lets losers run well past the initial
stop (needs a hard catastrophic stop for DLL $600 safety; the 1m variant shows the cost of tightening it: win% → 27%).
Win rate only ~40% (fixed target: 36%). Edge concentrated 2021+; MNQ-only; a 2026 PF of 1.17 shows decay risk.

## 2. Market intraday momentum — Gao, Han, Li & Zhou (JFE 2018); Baltussen et al. (JFE 2021)
Rules: trade 15:30 open → 16:00 close (market both ends) in the direction of: (a) prev 16:00 close → 10:00 return;
(b) 09:30→10:00 return; (c) 12th half-hour 15:00→15:30; (d) (a) and (c) agree. 1R = 14-day mean |15:30→16:00| move.
| sym | signal | IS trades / win% / $/tr / PF | HO trades / win% / exp R / $/tr / PF |
|---|---|---|---|
| MNQ | prevclose→10:00 | 1046 / 46.6 / −6.51 / 0.79 | 649 / 48.7 / +0.049 / +3.08 / 1.08 |
| MNQ | first 30 min | 1145 / 47.0 / −3.36 / 0.89 | 710 / 45.2 / −0.084 / −5.47 / 0.87 |
| MNQ | 12th half-hour | 1139 / 48.3 / +2.05 / 1.07 | 706 / 47.3 / −0.029 / −4.06 / 0.91 |
| MNQ | both agree | 545 / 46.4 / −3.34 / 0.89 | 347 / 47.6 / +0.047 / +1.27 / 1.03 |
| MGC | all four | PF 0.57–0.63, −$3.1 to −3.8 | PF 0.70–1.07, −$6.0 to +$1.06 |
**Verdict: FAIL everywhere.** Win rate 45–49% with ~symmetric payoffs; costs ($1.50–2.60 + a tick) eat any edge.
Signs flip between IS and HO — consistent with the effect having decayed in liquid index futures after publication.

## 3. VWAP trend (Zarattini & Aziz VWAP style), 1m and 5m bars, flat 16:39, entries from 09:35
Rules: on a bar close (1m or 5m), long if close > session VWAP and VWAP rose vs the prior bar; short mirror; entry next
open; exit on a close back across VWAP (next open). Stop distance for R = max(|entry−VWAP|, 0.1% price). RR version:
resting stop at that distance, limit TP at 2R.
| sym | variant (cap 3) | HO trades | win% | exp R | $/tr | PF | IS PF |
|---|---|---|---|---|---|---|---|
| MNQ | 1m trail | 2070 | 23.3 | +0.019 | +1.96 | 1.06 | 1.09 |
| MNQ | 5m trail | 1982 | 26.4 | +0.045 | +4.57 | 1.09 | 1.00 |
| MNQ | 1m / 5m 2R | 2112 / 2104 | 35.0 / 35.2 | −0.010 / +0.002 | +1.07 / +0.45 | 1.02 / 1.01 | 0.97 / 1.02 |
| MGC | all four | ~2070 | 21–34 | −0.08 to −0.16 | −3.5 to −7.2 | 0.76–0.91 | 0.81–0.91 |
Uncapped (~6–13 trades/day) is worse (MNQ HO PF 0.97–0.98). **Verdict: FAIL** (low win rate, PF ≤ 1.09, costs dominate).

## How the passing candidate would plug into Paytience
- Signal: MNQ noise-area breakout is self-contained (needs 14-day per-minute σ table, prior close, session VWAP) —
  computable from heartbeat bars server-side; or a TradingView alert at each :00/:30 bar close → webhook.
- Conflicts: it is NOT a C1/C2 sweep model, so G3/G5 (sweep/CHoCH) and the Fractal stop/T2 do not apply; it would be a
  separate profile. Entries 10:00–15:30 overlap D2's 06:45–11:30 window only for 10:00–11:30 (2–4 checks). The
  passing paper version has no fixed TP and losses avg −1.7R → violates the 1.5–2.5R TradePlan pillar; the only
  pillar-compatible form is the 2.5R fixed-target version (PF 1.17, 36% win) — weaker than the app baseline's
  structure-break MNQ (PF 1.72 on 1y) and only marginally above the 1.15 bar. Needs a hard stop for DLL; EOD exit 16:00.
- Win rate is not high in any version (≤ 43%); it does NOT meet a "higher win rate" goal.
