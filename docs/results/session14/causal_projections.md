# Session 14 - projections rebuilt on the CAUSAL afternoon-fade rule (IMPROVEMENTS item 14, steps 1-4; user-approved)

**Plain summary.** The old stream let the afternoon fade trade only on days NOISE never traded *all day* (unknowable live). The live app (`strategy_service.run_pm_fade`) skips the fade only if a NOISE signal has already fired. Rebuilt with the live rule
(fade 13:00-15:29 allowed only if no NOISE signal fired at a check at or before that minute; a NOISE entry that falls while the fade is open is dropped = one position per account), the 5-year stream loses **27% of its profit**, the
fade turns out to have **no edge at all** (break-even, slightly negative), and every pass / income / bust figure that used the old stream was too rosy. Nothing in the live code changed.

Data: Databento MNQ.v.0 1-minute, 2021-11-01 .. 2026-10-30 (re-downloaded; raw bars are git-ignored). Generator: `docs/results/session11/rebuild_main_csv.py` (now builds both files; the hindsight output reproduces the old CSV to the cent: 1,291 trades, $25,345.32).
Engine studies: the session 10/11 account engines patched with `session14/causal_fade.py` (env `FADE_RULE=causal|hindsight`; hindsight reproduces the old reports exactly, e.g. 25K Regular 55.5/56.0/49.7/56.2 % pass, no-rule 63.4/34.4).
Pick-period / judge-period convention kept: IS = 2021-11..2023-12, HO = 2024-01..2026-10.

## 1. The trade stream (1 micro MNQ, $250 stop, net of costs) - `out/stream_stats.md`
| slice | OLD hindsight: n / win / PF / profit | NEW causal: n / win / PF / profit |
|---|---|---|
| all 5 years | 1291 / 50.0% / 1.33 / $25,345 | 1318 / 48.8% / 1.22 / **$18,539 (-27%)** |
| IS 2021-23 | 564 / 48.6% / 1.30 / $9,363 | 578 / 47.2% / 1.18 / $6,269 |
| HO 2024-26 | 727 / 51.0% / 1.34 / $15,982 | 740 / 50.0% / 1.24 / $12,270 |
| NOISE only | 803 / 44.7% / 1.36 / $18,930 | 769 / 44.5% / 1.37 / $18,972 (unchanged) |
| FADE only | 488 / 58.6% / 1.26 / $6,416 | 549 / 54.8% / **0.99 / -$432** |
| FADE IS / HO | 54.1% / $621 and 61.9% / $5,794 | 51.3% / **-$2,177** and 57.5% / $1,744 |
Profit per month at 1 micro: $422 -> $309. Trades per day unchanged (about 1.0). The numbers match the session-13 `causal.py` figures (IS 578 / 47.2% / $6,269, HO 740 / 50.0% / $12,270).
Why the fade shrinks: the old rule picked only the days NOISE did not trade (quiet, mean-reverting days). Causally the fade also trades the days on which NOISE fires later in the afternoon - trend days, where fading VWAP loses.

## 2. Dashboard income projection (5 accounts, bi-weekly payout, auto size) - `out/projection_compare.md`
| plan / profile | micros | year mean old -> new | year median old -> new | any payout % | first-year bust % |
|---|---|---|---|---|---|
| Pro 25K | 1 | $8,232 -> **$4,409** | $4,500 -> $0 | 58.3 -> 42.6 | 56.6 -> 80.7 |
| Pro 50K | 2 | $14,664 -> $9,034 | $13,070 -> $5,033 | 65.8 -> 56.4 | 44.2 -> 63.7 |
| Pro 100K Regular | 2 | $16,723 -> $9,986 | $16,025 -> $4,618 | 72.8 -> 60.4 | 26.0 -> 39.8 |
| Pro 100K High | 3 | $16,564 -> $8,796 | $11,250 -> $5,507 | 72.7 -> 56.6 | 23.5 -> 48.9 |
| Pro 150K Regular | 3 | $22,918 -> $13,647 | $21,072 -> $7,259 | 74.8 -> 63.3 | 23.5 -> 48.6 |
| Pro 150K High | 4 | $24,760 -> $14,570 | $23,706 -> $7,472 | 74.6 -> 56.0 | 26.8 -> 60.6 |
Income per account per month = year mean / 5 accounts / 12 (for example 150K Regular: $22,918 -> $13,647 per year for 5 accounts = $382 -> $227 per account per month). This replay is the plain per-trade stream (no D57 shrink), so it falls by about the same -40 to -47% as the engine studies below (funded income -40 to -49%, eval pass -8 to -21 pts). `backend/tests/integration/test_income_projection.py` pins were updated to the causal values (4408.91 / 48.6 / 7471.70 / 4173.14).

## 3. Eval-pass and funded-income studies under the live rules (kill_study / pm_fade_d57_study engines) - `out/compare.md`
EVAL pass / bust / frozen % and median sessions (all starts), old -> new:
| plan (kill $50, live) | pass | frozen | median sessions | 2021-23 pass | 2024-26 pass |
|---|---|---|---|---|---|
| 25K Regular 1 x $250 | 56 -> **45** | 43 -> 55 | 35 -> 35 | 65 -> 51 | 48 -> 40 |
| 25K High-risk 3 x $150 taper | 33 -> **28** | 67 -> 72 | 8 -> 7 | 38 -> 30 | 29 -> 26 |
| 25K 2 x $225 taper | 38 -> 30 | 62 -> 70 | 15 -> 13 | 41 -> 32 | 36 -> 28 |
| 50K 2 micros brake | 49 -> 40 | 43 -> 49 | 43 -> 46 | 52 -> 38 | 47 -> 42 |
| 100K (live table, fade as live) | 62 -> 41 | 36 -> 54 | 86 -> 95 | 68 -> 40 | 55 -> 43 |
| 150K (live table, fade as live) | 57 -> 49 | 40 -> 47 | 75 -> 90 | 62 -> 51 | 52 -> 48 |
Bust stays 0% with the live rules (the simulator limitation noted in D71; "frozen" is the real failure and it rises 6-18 pts). With **no** rule at all the 25K Regular bust rate goes 34% -> 48%.
Funded, mean income per 2 weeks (paid to trader) and frozen share, kill $50: 25K x1 $53 -> **$27** (frozen 77 -> 90%); 50K x2 $93 -> $56 (63 -> 75%); 150K x3 $189 -> **$104** (31 -> 54%); 150K x4 High $183 -> $97 (52 -> 67%). Live-controller fade mode ("code"): 100K $141 -> $70, 150K $189 -> $104.

## 4. Which past decisions change
| decision | old conclusion | on the causal stream | verdict |
|---|---|---|---|
| **D70** 25K High-risk 3 x $150 taper vs Regular | HR pass 31% / frozen 69% / median 8 sessions vs Regular 55% / 59% / 35; value per eval $514 vs $913 | HR 27% / 73% / 7 vs Regular 45% / 55% / 34. Ratio HR/Regular pass 0.56 -> 0.60. HR still only buys speed (5x fewer sessions) at a clearly lower pass rate | **holds** (both absolute levels lower; Regular is still the better value per eval) |
| **D71** freeze at $50 instead of $100 | +0-4 pts pass, income +$6-45, bust 0% | +0-2 pts pass (Regular 45 -> 45, HR 27 -> 28, 2x$225 28 -> 30, 50K 40 -> 40); funded income 25K +$2, 150K x3 +$12 ($92 -> $104), bust 0% | **holds**, benefit slightly smaller; the gap-slippage caveat is unchanged |
| **D73** PM_FADE under D57 shrink (not adopted) | covering the fade lowered pass 4-8 pts, no gain 2024-26 | tighten vs code: 25K 45/46, 50K 40/41, 100K 40/41, 150K 40/49 (all starts); no gain 2024-26 | **holds** (still not adopted) |
| **D74** AI-bias sizing "version B" (100K/150K, 60% gate) | pays at >= ~60% accuracy, ~break-even at 55%; loses on 25K | 40 seeds. 100K: +$4 / +$11 / +$29 / +$45 / +$66 per 2 wk at 52 / 55 / 60 / 65 / 70%; 150K: -$5 / +$1 / +$17 / +$40 / +$58; 50K: -$10 / -$6 / +$4 / +$13 / +$23; 25K: -$3 to -$11 at every accuracy. Baseline income halves (100K $126 -> $62, 150K $183 -> $96) | **holds** (break-even about 55% on 100K/150K, about 58-60% on 50K, never on 25K). The 0.60 gate and the 100K+ restriction stay right; the dollar value of the feature is about half of what was shown |
| **D75 P2** reset a frozen eval at once | same pass, 4-14% fewer sessions: 25K < $150, 100K < $300, 150K < $225 | 25K < 15%: same pass (53.4 / 39.0 both), sessions per pass 95 -> 80 and 96 -> 77 (OK). 150K < 5%: same pass, 235 -> 223 (OK). 50K < 5%: no effect. **100K < 10%: IS pass 39.9 -> 32.9 (-7 pts)** | **CHANGES for 100K**: do not use the 100K reset threshold (deep 100K accounts recover causally). 25K / 150K / 50K stay as proposed |
| **D75 P3** 25K High-risk recover mode | pass 38.9% IS and 31.9% OOS -> 43.5% and 38.1% (+4.6 / +6.2) | base 31.4% / 28.4% -> recover 36.7% / 33.2% (+5.3 / +4.8); recover + reset<15% cuts sessions per pass 69 -> 30 (IS) | **holds** |
| D75 P1 NOISE profit lock, P4 cushion/Kelly sizing | passes held-out | **NOT re-run** (not asked; the NOISE stream is unchanged by the causal rule, so P1's NOISE gain stands; P4 income figures are on the old engine and will be about half) | open |
| D55/D58 "fade adds ~$6.4k / 5y" | fade profitable (PF 1.26) | causal fade PF 0.99, -$432 (IS PF 0.85, HO PF 1.09) | **CHANGES**: the afternoon fade has no demonstrated edge as the live app trades it. NOISE alone is $18,972; with the fade $18,539. Worth a separate decision (turn it OFF or re-tune) - nothing changed here |
| D77/D80 notice "about 25% optimistic" | | measured: -27% profit, -45% to -50% funded income | replaced by the causal notice |

## 5. Not done / caveats
- Engine studies approximate two things: a NOISE signal that fires while a (causally allowed) fade is open is dropped using the fade's exit under the nominal 124-pt stop (the account-specific D57 stop could exit earlier); and a risk-skipped NOISE signal still counts as "a NOISE signal fired" (it does in live: the signal is PASS, the controller skips later). Both are small (only the 14:00 / 15:00 checks can overlap).
- D74 re-run used 40 seeds per cell (the original 70); the sign and break-even points are stable, individual cells carry about +-2 pts noise. Hindsight AI table is the committed `session11/out/ai_bias_tables.md`.
- Step 5 of item 14 (replay the last N paper days through `strategy_service` for a trade-by-trade parity check) was not part of this request and is still open.
- Eval-fee, news-blackout and open-trade drawdown are still not modelled (as before).

## Files
`session14/causal_fade.py` (shim), `run_all.sh`, `eval_speed_s14.py`, `compare.py`, `projection_compare.py`, `stream_stats.py`, `out/{hindsight,causal}/*.json|log|txt`, `out/compare.md`, `out/projection_compare.md`, `out/stream_stats.md`.
Re-run: `python3 docs/results/session11/rebuild_main_csv.py`; `bash docs/results/session14/run_all.sh causal|hindsight`; `FADE_RULE=hindsight` reproduces the old reports.
