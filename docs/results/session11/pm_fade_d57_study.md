# PM_FADE under the D57 stop-shrink / DRAWDOWN_TOO_DEEP rule? (session 11, 2026-11-10)

No app code edited, nothing committed. Scripts: `pm_fade_d57_study.py` (engine + `verify` / `run`), `pm_fade_tables.py` (tables), `base_sim.py` (rebuilt prep/calendar helpers).
Raw output: `out/results_pm_fade.json`, `out/tables.md`. Data: Databento MNQ.v.0 1-minute bars 2021-10 -> 2026-10 in `backend/app/backtest/data/raw/mnq_5y.csv`
(built by the parallel `rebuild_main_csv.py`; gitignored). Run with the system `python3` (the project `.venv` has no numpy).

## Question and variants
`controller.py:508` passes `shrink_fraction` only for NOISE / AI_BIAS, so PM_FADE keeps the pause floor (risk base < $500 -> RISK_BASE_BELOW_PAUSE) and its $250 stop is never tightened.
- **V0 (current)**: fade untightened, pause floor + plain worst-case check (`kill_study.py` fade_mode "code").
- **V1**: fade covered like NOISE: same `checks.pretrade` arithmetic (worst case <= 0.6 x min(DLL left, equity - MLL - kill); tightened stop < 0.2% of price -> DRAWDOWN_TOO_DEEP skip; scaled -> pause floor bypassed), same VWAP target (fade_mode "tighten").
Everything else identical: NOISE always tightened, kill distance $50 (D71), 5 years MNQ (1,305 sessions, 1,245 with data), per-trade 1-minute re-simulation, 20 idle sessions = frozen, DLL as soft day stop, starts every 2 sessions.

## Sizing (live)
- Eval (Evaluation Mode, D66/D70): 25K Regular 1 x $250; 25K High risk 3 x $150 taper to 1 micro below 50% of target remaining; 50K 2 (brake <50% -> 1); 100K 2 growing +1 per $1,200 cushion to 4, brake <30% -> 1, day lock-in at 33% of remaining target; 150K 4 (brake <50% -> 2). Horizon 120 sessions (25K/50K), 250 (100K/150K). All $250 stops except High risk.
- Funded year 1 (260 sessions, Regular, $250/micro): 25K x1 payout every 10 sessions; 50K x2 (brake) / 10; 100K x2 (brake <30%) / 5; 150K x3 (brake) / 5 (D68). Max-eligible payouts, 40% consistency, 90% split, plan rules from `config/rules/lucid_pro_*.yaml`.
- Income = mean paid per account in year 1 divided by 26 (per 2 weeks; x5 for a five-account household).

## Verification (`pm_fade_d57_study.py verify`) - reproduces the kill-distance report exactly
V1 kill 100: 55.5% pass / 0% bust / 43.7% frozen / median 35 (report 55.5 / 0 / 43.7 / 35). V1 kill 50: 56.0% (56.0). V0 kill 100: 49.7% (49.7). V0 kill 50: 56.2% (56.2). No rule: 63.4% pass / 34.4% bust, win 50.5% (63.4 / 34.4 / 50.5).

## Results (kill $50)
### EVAL (kill $50; pass / bust / frozen / median sessions to pass)

| plan | variant | pass | bust | frozen | med sess | held-out pass 2024-26 / frozen | era1 pass 2021-23 / frozen |
|---|---|---|---|---|---|---|---|
| 25K Regular (1x$250) | V0 current | 56.2% | 0.0% | 43.5% | 34 | 47.1% / 52.9% (bust 0.0%) | 66.1% / 33.2% (bust 0.0%) |
| 25K Regular (1x$250) | V1 tightened | 56.0% | 0.0% | 43.2% | 35 | 48.1% / 51.9% (bust 0.0%) | 64.7% / 33.6% (bust 0.0%) |
| 25K High risk (3x$150 taper) | V0 current | 35.2% | 0.0% | 64.8% | 8 | 31.9% / 68.1% (bust 0.0%) | 38.9% / 61.1% (bust 0.0%) |
| 25K High risk (3x$150 taper) | V1 tightened | 33.1% | 0.0% | 66.9% | 8 | 28.7% / 71.3% (bust 0.0%) | 37.8% / 62.2% (bust 0.0%) |
| 50K | V0 current | 53.0% | 0.0% | 36.8% | 46 | 47.1% / 45.5% (bust 0.0%) | 59.4% / 27.2% (bust 0.0%) |
| 50K | V1 tightened | 49.2% | 0.0% | 43.2% | 43 | 47.1% / 45.5% (bust 0.0%) | 51.6% / 40.6% (bust 0.0%) |
| 100K | V0 current | 61.9% | 0.0% | 35.8% | 86 | 55.1% / 44.9% (bust 0.0%) | 67.8% / 27.9% (bust 0.0%) |
| 100K | V1 tightened | 57.4% | 0.0% | 39.2% | 80 | 55.1% / 44.9% (bust 0.0%) | 59.4% / 34.3% (bust 0.0%) |
| 150K | V0 current | 57.4% | 0.0% | 40.3% | 75 | 51.8% / 48.2% (bust 0.0%) | 62.2% / 33.6% (bust 0.0%) |
| 150K | V1 tightened | 52.8% | 0.0% | 44.9% | 75 | 51.8% / 48.2% (bust 0.0%) | 53.7% / 42.0% (bust 0.0%) |

### FUNDED year 1, per account (260 sessions, D68 cadence)

| plan | variant | bust | mean per 2 wk | mean yr-1 | held-out 2024-26 per 2 wk / bust | era1 2021-23 per 2 wk / bust | frozen |
|---|---|---|---|---|---|---|---|
| 25K x1, pay/10 | V0 current | 0.0% | $53 | $1,380 | $42 / 0.0% | $63 / 0.0% | 70.0% |
| 25K x1, pay/10 | V1 tightened | 0.0% | $53 | $1,377 | $44 / 0.0% | $61 / 0.0% | 76.7% |
| 50K x2 brake<50%->1, pay/10 | V0 current | 0.0% | $97 | $2,534 | $80 / 0.0% | $112 / 0.0% | 57.7% |
| 50K x2 brake<50%->1, pay/10 | V1 tightened | 0.0% | $93 | $2,421 | $80 / 0.0% | $104 / 0.0% | 62.9% |
| 100K x2 brake<30%->1, pay/5 | V0 current | 0.0% | $141 | $3,674 | $119 / 0.0% | $160 / 0.0% | 37.9% |
| 100K x2 brake<30%->1, pay/5 | V1 tightened | 0.0% | $131 | $3,411 | $119 / 0.0% | $142 / 0.0% | 48.9% |
| 150K x3 brake<50%->2, pay/5 | V0 current | 0.0% | $189 | $4,924 | $153 / 0.0% | $220 / 0.0% | 31.4% |
| 150K x3 brake<50%->2, pay/5 | V1 tightened | 0.0% | $189 | $4,924 | $153 / 0.0% | $220 / 0.0% | 31.4% |

### FADE trades (aggregated over all rolling starts; fade signals = signals on days NOISE took no trade)

| run | variant | fade trades | win% | PF | avg win/loss | tightened % of fade trades | tightened trades stopped | fade signals | skipped | of which PAUSE / DEEP / WORST |
|---|---|---|---|---|---|---|---|---|---|---|
| E 25K Regular (1x$250) | V0 | 6,761 | 59.6% | 1.37 | $100 / $-108 | 0.0% | nan | 11,836 | 42.9% | 5,075 / 0 / 0 |
| E 25K High risk (3x$150 taper) | V0 | 1,605 | 57.2% | 1.18 | $198 / $-224 | 0.0% | nan | 7,910 | 79.7% | 6,194 / 0 / 111 |
| E 50K | V0 | 11,045 | 59.1% | 1.27 | $182 / $-208 | 0.0% | nan | 15,520 | 28.8% | 4,475 / 0 / 0 |
| E 100K | V0 | 17,661 | 60.6% | 1.32 | $244 / $-285 | 0.0% | nan | 21,594 | 18.2% | 3,933 / 0 / 0 |
| E 150K | V0 | 16,023 | 60.1% | 1.30 | $341 / $-394 | 0.0% | nan | 20,031 | 20.0% | 3,695 / 0 / 313 |
| F 25K x1, pay/10 | V0 | 23,321 | 59.5% | 1.26 | $101 / $-118 | 0.0% | nan | 79,790 | 70.8% | 56,469 / 0 / 0 |
| F 50K x2 brake<50%->1, pay/10 | V0 | 29,643 | 59.6% | 1.25 | $186 / $-220 | 0.0% | nan | 73,252 | 59.5% | 43,609 / 0 / 0 |
| F 100K x2 brake<30%->1, pay/5 | V0 | 38,890 | 59.7% | 1.25 | $195 / $-230 | 0.0% | nan | 62,330 | 37.6% | 23,440 / 0 / 0 |
| F 150K x3 brake<50%->2, pay/5 | V0 | 41,324 | 59.6% | 1.27 | $290 / $-337 | 0.0% | nan | 60,810 | 32.0% | 19,244 / 0 / 242 |
| E 25K Regular (1x$250) | V1 | 7,831 | 59.0% | 1.29 | $101 / $-112 | 9.3% | 18.8% | 11,893 | 34.2% | 0 / 4,046 / 16 |
| E 25K High risk (3x$150 taper) | V1 | 1,553 | 55.8% | 1.13 | $190 / $-213 | 16.4% | 38.2% | 8,156 | 81.0% | 0 / 6,603 / 0 |
| E 50K | V1 | 11,199 | 59.0% | 1.26 | $177 / $-202 | 3.0% | 46.4% | 15,367 | 27.1% | 0 / 4,159 / 9 |
| E 100K | V1 | 18,072 | 60.6% | 1.33 | $227 / $-262 | 2.9% | 20.9% | 21,375 | 15.5% | 0 / 3,284 / 19 |
| E 150K | V1 | 16,506 | 59.9% | 1.30 | $333 / $-382 | 4.6% | 13.6% | 20,277 | 18.6% | 0 / 3,771 / 0 |
| F 25K x1, pay/10 | V1 | 23,306 | 59.1% | 1.23 | $100 / $-118 | 4.4% | 23.8% | 81,123 | 71.3% | 0 / 53,790 / 4,027 |
| F 50K x2 brake<50%->1, pay/10 | V1 | 28,231 | 59.6% | 1.25 | $181 / $-213 | 2.1% | 38.1% | 76,311 | 63.0% | 0 / 45,264 / 2,816 |
| F 100K x2 brake<30%->1, pay/5 | V1 | 35,650 | 59.7% | 1.26 | $191 / $-224 | 1.1% | 26.0% | 67,080 | 46.9% | 0 / 28,995 / 2,435 |
| F 150K x3 brake<50%->2, pay/5 | V1 | 41,420 | 59.5% | 1.27 | $290 / $-336 | 0.8% | 27.4% | 61,111 | 32.2% | 0 / 19,691 / 0 |

### NOISE side (should be identical V0 vs V1 only when path is the same; differences come from account paths)

| run | variant | NOISE trades | win% | PF | all-trades win% | PF |
|---|---|---|---|---|---|---|
| E 25K Regular (1x$250) | V0 | 13,205 | 45.2% | 1.30 | 50.1% | 1.32 |
| E 25K High risk (3x$150 taper) | V0 | 2,819 | 40.9% | 1.31 | 46.8% | 1.27 |
| E 50K | V0 | 20,054 | 45.4% | 1.27 | 50.3% | 1.27 |
| E 100K | V0 | 31,299 | 45.5% | 1.29 | 50.9% | 1.30 |
| E 150K | V0 | 28,341 | 45.3% | 1.30 | 50.7% | 1.30 |
| F 25K x1, pay/10 | V0 | 41,275 | 45.8% | 1.28 | 50.8% | 1.27 |
| F 50K x2 brake<50%->1, pay/10 | V0 | 50,876 | 45.4% | 1.23 | 50.6% | 1.24 |
| F 100K x2 brake<30%->1, pay/5 | V0 | 65,257 | 45.5% | 1.34 | 50.8% | 1.32 |
| F 150K x3 brake<50%->2, pay/5 | V0 | 67,376 | 45.4% | 1.35 | 50.8% | 1.32 |
| E 25K Regular (1x$250) | V1 | 12,992 | 45.5% | 1.33 | 50.6% | 1.32 |
| E 25K High risk (3x$150 taper) | V1 | 2,683 | 40.7% | 1.30 | 46.2% | 1.24 |
| E 50K | V1 | 18,814 | 45.1% | 1.23 | 50.3% | 1.24 |
| E 100K | V1 | 30,390 | 45.1% | 1.27 | 50.9% | 1.29 |
| E 150K | V1 | 28,110 | 44.9% | 1.26 | 50.5% | 1.28 |
| F 25K x1, pay/10 | V1 | 39,227 | 46.0% | 1.30 | 50.9% | 1.28 |
| F 50K x2 brake<50%->1, pay/10 | V1 | 46,670 | 45.5% | 1.23 | 50.8% | 1.23 |
| F 100K x2 brake<30%->1, pay/5 | V1 | 58,792 | 45.4% | 1.33 | 50.8% | 1.31 |
| F 150K x3 brake<50%->2, pay/5 | V1 | 66,997 | 45.5% | 1.35 | 50.8% | 1.32 |

## Reading the numbers
1. **Busts are 0.0% in both variants on every plan, eval and funded.** The pause floor already protects V0; V1 buys no extra safety in this data (no gap through a stop in 5 years).
2. **Eval, 2021-23 (era 1)**: V1 is worse on every plan with 50K+: pass 59.4 -> 51.6 (50K), 67.8 -> 59.4 (100K), 62.2 -> 53.7 (150K), frozen +6 to +13 pts; 25K Regular -1.4, 25K High risk -1.1.
3. **Eval, 2024-26 (held-out)**: 25K Regular +1.0 pt (47.1 -> 48.1), 25K High risk -3.2 pts (31.9 -> 28.7), 50K / 100K / 150K identical (47.1 / 55.1 / 51.8: accounts rarely sit near the floor in those windows, so the rule never differs). So V1 does NOT help on both halves; the only held-out gain is +1 pt on 25K Regular, inside noise.
4. **Funded year 1**: 25K x1 same overall ($53 per 2 wk; held-out $42 -> $44, era 1 $63 -> $61); 50K $97 -> $93; 100K $141 -> $131; 150K identical. Held-out: +$2 on 25K, 0 elsewhere. V1 never earns more overall.
5. **Fade trade quality**: win rate 59-60% and PF 1.25-1.37 in both; V1 tightens 1-16% of fade trades (16% on 25K High risk) and 14-46% of those end at the tightened stop; tightened fades lower PF slightly (25K Regular 1.37 -> 1.29, High risk 1.18 -> 1.13). V1 skips fades as DRAWDOWN_TOO_DEEP in about the same number as V0 skips as PAUSE (e.g. funded 25K 56,469 PAUSE vs 53,790 DEEP + 4,027 WORST): the freeze is the same, only its label and a few more worst-case skips change.
6. Why: the tightened fade stop is rarely the binding constraint - the account is either comfortably above the pause floor (identical) or so close that both variants stop trading. In the band in between, a tighter stop turns winning mean-reversion trades (they need room to reach VWAP) into stop-outs, exactly the D57 NOISE finding in README section 7.
7. Noise: rolling windows overlap heavily (~10 independent 120-session windows); differences below ~3 pts are not reliable. Era 1 deficits for 50K+ evals (-4 to -8 pts) are larger than that; held-out differences are all within it except High risk (-3.2).

## Verdict
**Do not extend D57 to PM_FADE.** V1 has 0% bust either way, loses 4-8 eval pass points on 50K/100K/150K in 2021-23, is identical in 2024-26 for those, only +1 pt on 25K Regular held-out (-3 pts on 25K High risk), and never raises funded income. Keep `controller.py:508` as is (PM_FADE keeps the pause floor and the $250 stop).
Caveats: one instrument/one strategy path, fade signals only on days NOISE took no trade, stress with stop slippage not rerun here (see kill_distance_report.md section 5 for gap stress).
