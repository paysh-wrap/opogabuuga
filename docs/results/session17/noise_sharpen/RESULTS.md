# Session 17 - NOISE sharpening study (MNQ, Lucid Pro 25K, 1 micro)

Research only. Nothing in the app, config, tests or HANDOFF was touched; nothing committed. Everything here is reproducible from the scripts in this folder
(run order: `build_data.py` -> `baseline_check.py` -> `run_study.py` -> `s2_select.py` -> `s2_randbench.py` -> `s2_lhh.py` -> `s3_paired.py` -> `s3_dow.py` -> `s4_extra.py` -> `report.py`;
`python -I`, own venv with numpy + pandas, no app imports).

## 1. Short answer

1. **The baseline reproduces exactly.** My re-implementation is trade-for-trade identical to the session-9 reference code (`tools/noise_area.py`, 1,167 trades) and to the committed
   session-15 stream (778 trades). Session-9 record: IS 727 tr / 44.3% / +$15.28 / PF 1.32, held-out 440 tr / 45.0% / +$25.81 / PF 1.33. Mine: identical on every number
   (T1). The record in `engine/noise.py` / `NoiseCfg` today is the session-9 rule set with the D58 $250 stop in place of the 1% stop: held-out 451 tr / 43.9% / +$23.88 / PF 1.31;
   with the shipped preset-C lock (100 pt -> entry +10) 427 tr / 52.2% / +$27.19 / PF 1.43. So "matches the session-9 record" = yes for the 1% version; the $250 version is
   a close sibling (PF 1.31 vs 1.33), and preset C is genuinely better in both periods (IS PF 1.38 vs 1.35, HO 1.43 vs 1.31).
2. **The edge is real, not an artefact of the exits.** Random direction with the same timing, exits, lock and costs (200 seeds each): $/trade +$2.5 (plain) / +$4.0 (preset C) held-out,
   PF 1.04 / 1.07, Pro 25K PASS 31% / 33% with BUST 68% / 64%. The real strategy beats 100% of the 200 random seeds on $/trade in the plain version (both eras) and 99.5% (preset C, held-out;
   1 of 200 seeds had a higher $/trade, 2 a higher net profit).
3. **Nothing beats the baseline with statistical confidence on held-out data.** Every paired block-bootstrap 95% interval of the Pro 25K PASS / BUST difference and (except two
   trivial lock tweaks) of the net-profit difference includes zero (T0, T13); the exceptions are two trivial lock tweaks (positive) and the "no entry 11:00" filter (negative). 83 stage-1 rows + 2 combinations + 2 exploratory ones were tried on the same 2.8 held-out years; at 5% per test a
   couple of "hits" are expected by chance. The honest reading of the held-out year-by-year picture is: **preset C is the best supported change** (lock helps in both periods); the day filters and the
   VWAP filter do not add reliably; the IS-selected combinations got WORSE on held-out data (classic over-fit).
4. **Two small, cheap, low-risk candidates could be paper-tested** (they lower max drawdown and bust risk while costing at most ~9% of profit; the Monday filter costs none): a minimum noise-band floor (skip entries when the band is in the narrowest
   20% of the in-sample distribution, sigma < 0.289% of price) and "skip Mondays". Both are weak evidence - see section 4.
5. **Last-half-hour add-on fails** (as in session 9): signs flip between periods (continuation PF 1.08-1.14 in-sample, 0.73-0.92 held-out; reversal the opposite). The IS-picked version lowers
   PASS and raises BUST on both bases.
6. **N10 (skip low-vol tercile) and N12 (skip Friday) hurt**; N11 (skip Monday) is the only one of N10-N12 that does not.

## 2. Method (what was actually run)

- **Data**: Databento GLBX.MDP3 `MNQ.v.0` (volume roll) 1-minute OHLCV, 2019-05-06 .. 2026-11-05 (2,647,687 bars; same download as the other helper, shared read-only; cost ~$10 for the history). RTH 09:30-16:00 ET only.
  Pick period (IS) = 2019-05-06 .. 2023-12-31; judged ONLY on held-out (HO) 2024-01-01 .. 2026-11-06.
- **Strategy** (identical to `engine/noise.py`): sigma_t = mean |close_t / open - 1| over the previous 14 days, bands max(open, prior close)*(1+sigma) / min(...)*(1-sigma), hourly checks 10:00-15:00,
  entry next bar open, exit when the hourly close crosses back through max(band, VWAP) (long) / min(band, VWAP) (short), flat 16:00, max 3 entries/day, roll guard |gap| > 1.5% = no trades,
  $250 emergency stop per micro (124 pt). "preset C" adds the D82 lock: at +100 pt the stop goes to entry +10 pt; a lock exit ends NOISE for the day (session-15 convention).
- **Costs**: $1.00 fee round trip + 1 tick slippage on every entry, exit and stop fill (as sessions 9-15). Stop checked on every 1-minute bar, stop-first in a bar, gaps fill at the open. 1 micro.
- **Pro 25K evaluation simulation** = the session-9 `sim25k.py` rules: balance 25,000, target +1,250 (Pro: may pass in one day, no consistency, no DLL in the eval), MLL 1,000 EOD-trailing floor that locks at 25,100
  once the EOD peak >= 26,100, breach checked after every trade (the "strict" column also kills the account when a trade's worst open loss touches the floor), rolling start every 2nd business day,
  120-session horizon, days without a trade count as sessions. Three estimates are shown for every row: **roll** (the session-9 method), **boot** (block bootstrap of the era's days, 1,000 paths, 10-session blocks, up to 500 sessions),
  **strict**. "days to pass" = median business days (holidays included, as in session 9) of the sessions that passed.
  BUST % = account dead. "open" = neither within 120 sessions (shown because low-trade variants are penalised by the horizon).
- **Selection discipline**: per family the IS-only rule (copied from the unfinished `stage2.py`, written before this run): eligible = IS PF >= base, IS net >= 90% of base, IS max DD <= 105% of base, >= 100 IS trades; pick = best IS edge ratio
  2*mean/sd^2. Pre-registered combination = the top two families by IS ratio (on the preset-C base: "no entry 11:00" + "skip Monday"). Rows marked **IS-pick** are the ones that rule chose; all other rows are shown for completeness only.
  Disclosure: I had looked at the held-out numbers of the stage-1 grid (`quick.py`) before I ran `s2_select.py`; the rule itself was not changed after looking. `s4_extra.py` (section 4) is explicitly post-hoc.
- **Significance**: with ~330 overlapping rolling starts there are really only ~6 independent 120-session windows in 2.8 years, so a single PASS % has a standard error of roughly +-15-20 points. T13 therefore resamples the held-out days
  (paired between variant and base) and gives the 95% interval of the difference. dNet columns give the paired 95% block-bootstrap interval of the net-profit difference over held-out days.
- **Old unfinished scripts in this folder** (`sharpen.py`, `study.py`, `stage2.py`, `lhh.py`, `randbench.py`, `baseline_check.py` old version overwritten): reviewed. `sharpen.gen` logic is correct and reproduces the session-15 stream exactly -> basis of `nz.py`.
  `study.py` variant list and `stage2.py` selection rule re-used. They depended on session-15 `lib`/`account` (which import the app) and on a 150K account harness, so they were rewritten self-contained (`nz.py`, `sim.py`, `s2_*.py`). `sharpen.py/study.py/stage2.py/lhh.py/randbench.py` remain untouched except `baseline_check.py`, which I rewrote (same name) - the old ones were never run and have no results.

## 3. Tables (all held-out unless the column says IS)
Columns: HO = held-out 2024-01..2026-11; roll / boot / strict = Pro 25K eval simulations (see section 2); dNet = paired block-bootstrap 95% interval of net-profit difference vs the row's base; `yrs PF>=base` = calendar years (of 8, 2019 and 2026 partial) in which the variant's profit factor is >= its base's (all trades of the year).

### T0 master table, held-out 2024-01..2026-11 (1 micro; every row also in the detail tables). Base of a [lock] row = BASE [lock] (= preset C); base of a [nolock] row = BASE [nolock] (= app default)
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| session-9 original (1% stop) [nolock] | 440 | 45.0 | 25.8 | 11,358 | 2,214 | 1.33 | 56.9 / 42.2 / 0.8 | 38 | 51.6 / 48.4 (32) | 48.7 / 50.7 | +587 [-2,897, +3,747] | 1.32 (11,106) | 2/8 |
| BASE [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | - | 1.35 (11,816) | 8/8 |
| BASE [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | - | 1.38 (12,110) | 8/8 |
| **IS-pick** N11 skip Monday [lock] | 359 | 54.3 | 33.9 | 12,176 | 2,096 | 1.55 | 67.4 / 29.5 / 3.1 | 53 | 69.4 / 30.6 (44) | 66.0 / 30.9 | +566 [-2,522, +3,909] | 1.44 (11,067) | 6/8 |
| N10 skip low-vol tercile [lock] | 242 | 55.4 | 32.6 | 7,893 | 1,310 | 1.48 | 45.3 / 24.4 / 30.3 | 74 | 60.2 / 39.8 (70) | 43.3 / 26.3 | -3,716 [-9,937, +1,849] | 1.46 (10,025) | 6/8 |
| N12 skip Friday [lock] | 329 | 53.2 | 25.1 | 8,264 | 1,553 | 1.42 | 58.4 / 18.1 / 23.5 | 56 | 63.5 / 36.5 (64) | 52.7 / 28.0 | -3,346 [-9,450, +1,933] | 1.30 (7,539) | 2/8 |
| **IS-pick** VWAP side filter [lock] | 407 | 51.8 | 27.1 | 11,030 | 2,237 | 1.43 | 58.4 / 37.1 / 4.5 | 42 | 60.8 / 39.2 (40) | 57.8 / 42.2 | -579 [-2,278, +1,097] | 1.39 (12,021) | 4/8 |
| **IS-pick** min sigma >= IS p20 (0.29%) [lock] | 380 | 53.7 | 27.8 | 10,549 | 1,527 | 1.46 | 75.9 / 16.7 / 7.4 | 52 | 67.1 / 32.9 (49) | 72.5 / 20.1 | -1,060 [-3,240, +3,592] | 1.42 (11,945) | 7/8 |
| lock 75->+10 | 417 | 56.6 | 28.6 | 11,936 | 1,756 | 1.49 | 61.8 / 30.9 / 7.4 | 45 | 67.3 / 32.7 (43) | 58.4 / 36.3 | +1,166 [-7,374, +6,326] | 1.33 (10,136) | 4/8 |
| lock 200->+10 | 448 | 45.3 | 26.1 | 11,690 | 2,224 | 1.35 | 55.8 / 41.9 / 2.3 | 44 | 50.7 / 49.3 (31) | 48.2 / 51.8 | +919 [+150, +1,861] | 1.37 (12,284) | 8/8 |
| trail-lock +100 give back 100 | 413 | 51.8 | 22.7 | 9,381 | 2,028 | 1.35 | 62.6 / 33.4 / 4.0 | 42 | 60.7 / 39.3 (46) | 58.6 / 39.1 | -1,390 [-9,680, +6,330] | 1.34 (10,794) | 5/8 |
| **IS-pick** no entry 11:00 [lock] | 399 | 52.9 | 20.7 | 8,277 | 2,109 | 1.33 | 47.0 / 51.3 / 1.7 | 53 | 56.1 / 43.9 (44) | 43.6 / 54.7 | -3,332 [-6,804, -384] | 1.44 (12,348) | 4/8 |
| **IS-pick** extra check 15:30 (band entry) [lock] | 450 | 50.9 | 25.2 | 11,356 | 2,260 | 1.40 | 55.2 / 42.5 / 2.3 | 46 | 60.0 / 40.0 (39) | 52.4 / 47.3 | -252 [-1,727, +948] | 1.41 (13,539) | 5/8 |
| COMBO(best-2 IS) = no entry 11:00 + N11 skip Monday | 336 | 54.8 | 25.7 | 8,646 | 2,135 | 1.42 | 55.8 / 36.3 / 7.9 | 61 | 63.0 / 37.0 (54) | 52.4 / 41.9 | -2,964 [-7,342, +1,342] | 1.49 (10,847) | 5/8 |
| COMBO(best-3 IS) = no entry 11:00 + N11 skip Monday + min sigma >= IS p20 (0.29%) | 297 | 56.6 | 21.9 | 6,491 | 1,211 | 1.38 | 52.4 / 25.8 / 21.8 | 63 | 65.0 / 35.0 (73) | 49.0 / 33.4 | -5,118 [-8,586, +995] | 1.54 (10,518) | 5/8 |
| random direction, same exits [nolock] (mean of 200 seeds) | 591 | 43.5 | 2.5 | 1,443 | 5,596 | 1.04 | 31.4 / 67.7 / 0.9 | 32 | - | - | - | - | - |
| random direction, same exits [lock] (mean of 200 seeds) | 563 | 48.6 | 4.0 | 2,235 | 4,498 | 1.07 | 33.2 / 64.2 / 2.6 | 37 | - | - | - | - | - |

### T1 baseline reproduction (1 micro)
| run | era | trades | win % | $/trade | PF | max DD $ | session-9 record |
|---|---|---|---|---|---|---|---|
| session-9 original (1% stop) | IS | 727 | 44.3 | 15.28 | 1.32 | 1,466 | 727 / 44.3% / +15.28 / 1.32 / -1,466 |
| session-9 original (1% stop) | HO | 440 | 45.0 | 25.81 | 1.33 | 2,214 | 440 / 45.0% / +25.81 / 1.33 / -2,214 |
| app default ($250 stop, engine/noise.py + NoiseCfg) | IS | 726 | 44.4 | 16.28 | 1.35 | 1,308 |  |
| app default ($250 stop, engine/noise.py + NoiseCfg) | HO | 451 | 43.9 | 23.88 | 1.31 | 2,228 |  |
| preset C ($250 stop + lock 100->+10) | IS | 722 | 46.3 | 16.77 | 1.38 | 1,308 |  |
| preset C ($250 stop + lock 100->+10) | HO | 427 | 52.2 | 27.19 | 1.43 | 2,028 |  |

Trade-for-trade check vs `tools/noise_area.py` (independent session-9 code, same CSV): identical = **True** (1167 trades).
Trade-for-trade check vs committed session-15 stream `out/streams/N1_MNQ.csv` (lock 100/10, window 2021-11-01..2026-10-27): identical = **True** (778 trades, net $19,519).

### T1b per-year profit factor (all trades of the year, 1 micro)
| stream | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| session-9 original (1% stop) [nolock] | 0.88 | 1.06 | 1.41 | 1.46 | 1.44 | 1.29 | 1.50 | 1.23 |
| BASE [nolock] | 0.89 | 1.09 | 1.45 | 1.51 | 1.42 | 1.35 | 1.37 | 1.24 |
| BASE [lock] | 0.89 | 1.10 | 1.43 | 1.61 | 1.43 | 1.50 | 1.23 | 1.54 |

### T2 N10 / N11 / N12 day filters (held-out)
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | - | 1.35 (11,816) | 8/8 |
| N10 skip low-vol tercile [nolock] | 262 | 43.5 | 27.9 | 7,310 | 2,120 | 1.32 | 37.4 / 46.2 / 16.4 | 60 | 43.0 / 57.0 (54) | 36.0 / 47.9 | -3,460 [-9,799, +2,104] | 1.40 (9,370) | 6/8 |
| **IS-pick** N11 skip Monday [nolock] | 382 | 45.5 | 30.3 | 11,572 | 2,378 | 1.40 | 59.2 / 37.7 / 3.1 | 42 | 56.2 / 43.8 (36) | 56.7 / 40.2 | +801 [-2,276, +4,152] | 1.41 (10,999) | 6/8 |
| N12 skip Friday [nolock] | 349 | 44.4 | 22.2 | 7,742 | 1,810 | 1.30 | 47.3 / 47.0 / 5.7 | 51 | 44.5 / 55.5 (50) | 39.7 / 57.2 | -3,029 [-9,079, +2,170] | 1.28 (7,364) | 1/8 |
| N10+N11 [nolock] | 224 | 46.4 | 36.5 | 8,165 | 2,004 | 1.42 | 51.3 / 35.4 / 13.3 | 68 | 48.2 / 51.8 (56) | 50.7 / 36.0 | -2,606 [-9,315, +3,531] | 1.43 (7,986) | 7/8 |
| N11+N12 (Tue-Thu only) [nolock] | 280 | 46.8 | 30.5 | 8,543 | 1,602 | 1.42 | 42.8 / 53.8 / 3.4 | 50 | 54.1 / 45.9 (60) | 42.8 / 53.8 | -2,228 [-8,956, +4,010] | 1.34 (6,547) | 5/8 |

| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | - | 1.38 (12,110) | 8/8 |
| N10 skip low-vol tercile [lock] | 242 | 55.4 | 32.6 | 7,893 | 1,310 | 1.48 | 45.3 / 24.4 / 30.3 | 74 | 60.2 / 39.8 (70) | 43.3 / 26.3 | -3,716 [-9,937, +1,849] | 1.46 (10,025) | 6/8 |
| **IS-pick** N11 skip Monday [lock] | 359 | 54.3 | 33.9 | 12,176 | 2,096 | 1.55 | 67.4 / 29.5 / 3.1 | 53 | 69.4 / 30.6 (44) | 66.0 / 30.9 | +566 [-2,522, +3,909] | 1.44 (11,067) | 6/8 |
| N12 skip Friday [lock] | 329 | 53.2 | 25.1 | 8,264 | 1,553 | 1.42 | 58.4 / 18.1 / 23.5 | 56 | 63.5 / 36.5 (64) | 52.7 / 28.0 | -3,346 [-9,450, +1,933] | 1.30 (7,539) | 2/8 |
| N10+N11 [lock] | 204 | 58.8 | 41.9 | 8,556 | 1,068 | 1.65 | 57.8 / 13.3 / 28.9 | 70 | 70.1 / 29.9 (77) | 56.9 / 15.6 | -3,052 [-9,654, +3,098] | 1.48 (8,418) | 8/8 |
| N11+N12 (Tue-Thu only) [lock] | 261 | 56.3 | 33.8 | 8,830 | 1,092 | 1.61 | 65.4 / 21.2 / 13.3 | 65 | 77.2 / 22.8 (78) | 65.4 / 21.2 | -2,779 [-9,618, +3,319] | 1.35 (6,496) | 4/8 |

### T3 VWAP entry filter (long only above session VWAP, short only below; slope = VWAP also rising/falling over 60 min)
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | - | 1.35 (11,816) | 8/8 |
| **IS-pick** VWAP side filter [nolock] | 419 | 43.4 | 27.2 | 11,382 | 2,505 | 1.36 | 62.3 / 35.1 / 2.5 | 42 | 52.5 / 47.5 (35) | 52.1 / 47.9 | +611 [-1,653, +2,504] | 1.36 (11,602) | 5/8 |
| VWAP side+slope filter [nolock] | 418 | 43.1 | 25.7 | 10,753 | 2,615 | 1.34 | 62.3 / 36.3 / 1.4 | 42 | 50.9 / 49.1 (34) | 52.1 / 47.9 | -18 [-2,405, +2,013] | 1.35 (11,158) | 4/8 |

| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | - | 1.38 (12,110) | 8/8 |
| **IS-pick** VWAP side filter [lock] | 407 | 51.8 | 27.1 | 11,030 | 2,237 | 1.43 | 58.4 / 37.1 / 4.5 | 42 | 60.8 / 39.2 (40) | 57.8 / 42.2 | -579 [-2,278, +1,097] | 1.39 (12,021) | 4/8 |
| VWAP side+slope filter [lock] | 406 | 51.5 | 25.7 | 10,438 | 2,306 | 1.40 | 58.4 / 37.1 / 4.5 | 42 | 58.5 / 41.5 (40) | 57.8 / 42.2 | -1,172 [-3,071, +670] | 1.38 (11,576) | 2/8 |

### T4 profit-lock variants ($250 stop everywhere; 'lock T->+L' = once +T points in favour the stop moves to entry+L points; a lock exit ends NOISE for the day; trail-lock = stop trails best price minus the give-back; compared with plain BASE [nolock]; the shipped preset C is `lock 100->+10` = BASE [lock])
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | - | 1.35 (11,816) | 8/8 |
| session-9 original (1% stop) [nolock] | 440 | 45.0 | 25.8 | 11,358 | 2,214 | 1.33 | 56.9 / 42.2 / 0.8 | 38 | 51.6 / 48.4 (32) | 48.7 / 50.7 | +587 [-2,897, +3,747] | 1.32 (11,106) | 2/8 |
| lock 50->+0 | 399 | 30.3 | 22.8 | 9,108 | 1,586 | 1.45 | 51.3 / 39.1 / 9.6 | 49 | 61.8 / 38.2 (54) | 47.9 / 43.3 | -1,662 [-11,093, +4,775] | 1.29 (8,400) | 4/8 |
| lock 50->+10 | 394 | 65.0 | 26.9 | 10,606 | 1,404 | 1.53 | 49.9 / 45.0 / 5.1 | 44 | 68.4 / 31.6 (54) | 49.9 / 45.9 | -166 [-9,673, +6,246] | 1.22 (6,419) | 2/8 |
| lock 50->+25 | 392 | 65.1 | 16.5 | 6,480 | 1,491 | 1.33 | 52.7 / 29.2 / 18.1 | 60 | 59.0 / 41.0 (72) | 52.7 / 31.2 | -4,291 [-13,436, +4,399] | 1.19 (5,606) | 2/8 |
| lock 75->+0 | 418 | 37.6 | 26.7 | 11,164 | 1,702 | 1.45 | 58.4 / 28.0 / 13.6 | 44 | 65.6 / 34.4 (43) | 55.5 / 40.8 | +392 [-7,993, +5,596] | 1.32 (10,043) | 4/8 |
| lock 75->+10 | 417 | 56.6 | 28.6 | 11,936 | 1,756 | 1.49 | 61.8 / 30.9 / 7.4 | 45 | 67.3 / 32.7 (43) | 58.4 / 36.3 | +1,166 [-7,374, +6,326] | 1.33 (10,136) | 4/8 |
| lock 75->+25 | 414 | 56.5 | 22.3 | 9,250 | 1,576 | 1.38 | 65.2 / 30.6 / 4.2 | 51 | 62.6 / 37.4 (53) | 64.9 / 31.4 | -1,522 [-9,230, +5,489] | 1.26 (8,022) | 4/8 |
| lock 75->+50 | 406 | 56.7 | 22.3 | 9,054 | 1,396 | 1.38 | 70.8 / 28.9 / 0.3 | 56 | 65.9 / 34.1 (59) | 70.0 / 29.7 | -1,716 [-10,414, +5,841] | 1.27 (8,347) | 4/8 |
| lock 100->+0 | 427 | 40.5 | 26.0 | 11,098 | 2,028 | 1.41 | 59.2 / 33.7 / 7.1 | 47 | 61.5 / 38.5 (40) | 46.5 / 53.5 | +326 [-8,161, +5,314] | 1.38 (12,224) | 5/8 |
| lock 100->+10 | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | +838 [-7,705, +5,854] | 1.38 (12,110) | 6/8 |
| lock 100->+25 | 424 | 52.1 | 22.1 | 9,363 | 2,028 | 1.34 | 59.2 / 39.7 / 1.1 | 51 | 57.1 / 42.9 (42) | 53.8 / 45.9 | -1,408 [-9,274, +5,309] | 1.35 (11,275) | 5/8 |
| lock 100->+50 | 418 | 52.2 | 22.2 | 9,299 | 2,028 | 1.35 | 62.3 / 37.7 / 0.0 | 46 | 60.5 / 39.5 (48) | 58.1 / 41.9 | -1,472 [-9,545, +5,586] | 1.31 (9,808) | 4/8 |
| lock 125->+0 | 436 | 42.2 | 23.8 | 10,397 | 2,028 | 1.35 | 49.0 / 43.3 / 7.6 | 47 | 56.6 / 43.4 (38) | 42.8 / 57.2 | -374 [-8,700, +4,196] | 1.38 (12,462) | 7/8 |
| lock 125->+10 | 436 | 49.8 | 24.6 | 10,718 | 2,028 | 1.37 | 50.7 / 43.3 / 5.9 | 47 | 57.6 / 42.4 (38) | 43.9 / 56.1 | -54 [-8,353, +4,614] | 1.38 (12,362) | 6/8 |
| lock 125->+25 | 433 | 49.7 | 21.5 | 9,323 | 2,028 | 1.32 | 56.1 / 36.8 / 7.1 | 44 | 55.9 / 44.1 (41) | 43.6 / 52.4 | -1,448 [-8,905, +4,715] | 1.37 (12,010) | 6/8 |
| lock 125->+50 | 427 | 49.6 | 19.5 | 8,339 | 2,028 | 1.29 | 53.8 / 40.2 / 5.9 | 52 | 53.3 / 46.7 (43) | 45.3 / 49.6 | -2,432 [-10,069, +4,320] | 1.33 (10,900) | 5/8 |
| lock 150->+0 | 444 | 42.8 | 22.0 | 9,789 | 2,366 | 1.31 | 56.9 / 37.7 / 5.4 | 49 | 55.0 / 45.0 (36) | 50.4 / 49.6 | -982 [-9,587, +3,417] | 1.37 (12,186) | 6/8 |
| lock 150->+10 | 444 | 47.5 | 22.2 | 9,870 | 2,306 | 1.32 | 55.8 / 40.8 / 3.4 | 48 | 55.3 / 44.7 (37) | 50.4 / 49.6 | -902 [-9,616, +3,540] | 1.37 (12,095) | 7/8 |
| lock 150->+25 | 441 | 47.4 | 19.1 | 8,438 | 2,224 | 1.27 | 56.7 / 40.5 / 2.8 | 46 | 53.8 / 46.2 (40) | 52.4 / 44.8 | -2,333 [-9,971, +3,565] | 1.37 (12,265) | 7/8 |
| lock 150->+50 | 436 | 47.5 | 19.3 | 8,414 | 2,224 | 1.27 | 60.6 / 37.1 / 2.3 | 46 | 54.5 / 45.5 (41) | 55.0 / 44.5 | -2,356 [-9,887, +3,901] | 1.35 (11,650) | 5/8 |
| lock 200->+0 | 448 | 43.5 | 25.9 | 11,618 | 2,224 | 1.35 | 55.0 / 42.8 / 2.3 | 44 | 50.4 / 49.6 (31) | 47.6 / 52.4 | +846 [+221, +1,655] | 1.37 (12,224) | 8/8 |
| lock 200->+10 | 448 | 45.3 | 26.1 | 11,690 | 2,224 | 1.35 | 55.8 / 41.9 / 2.3 | 44 | 50.7 / 49.3 (31) | 48.2 / 51.8 | +919 [+150, +1,861] | 1.37 (12,284) | 8/8 |
| lock 200->+25 | 446 | 45.1 | 25.4 | 11,308 | 2,224 | 1.34 | 56.1 / 41.9 / 2.0 | 44 | 50.3 / 49.7 (32) | 48.2 / 51.8 | +536 [-1,082, +1,922] | 1.37 (12,341) | 7/8 |
| **IS-pick** lock 200->+50 | 444 | 45.0 | 26.4 | 11,722 | 2,224 | 1.35 | 56.1 / 41.6 / 2.3 | 44 | 50.5 / 49.5 (31) | 48.2 / 51.8 | +950 [-716, +2,593] | 1.38 (12,521) | 7/8 |
| trail-lock +75 give back 40 | 404 | 56.7 | 11.8 | 4,764 | 2,070 | 1.20 | 42.5 / 30.6 / 26.9 | 63 | 56.8 / 43.2 (82) | 42.5 / 40.8 | -6,007 [-15,423, +2,508] | 1.21 (6,349) | 4/8 |
| trail-lock +75 give back 60 | 404 | 56.7 | 14.8 | 5,967 | 1,700 | 1.25 | 48.2 / 37.7 / 14.2 | 53 | 56.9 / 43.1 (66) | 48.2 / 41.6 | -4,804 [-13,732, +3,328] | 1.22 (6,750) | 3/8 |
| trail-lock +75 give back 100 | 408 | 49.3 | 21.0 | 8,560 | 2,082 | 1.35 | 54.4 / 35.4 / 10.2 | 40 | 60.9 / 39.1 (51) | 53.8 / 36.8 | -2,211 [-10,786, +6,069] | 1.33 (10,238) | 3/8 |
| trail-lock +100 give back 40 | 412 | 51.9 | 13.3 | 5,481 | 2,492 | 1.21 | 43.3 / 41.4 / 15.3 | 58 | 54.9 / 45.1 (63) | 39.7 / 54.4 | -5,290 [-14,486, +2,436] | 1.26 (8,283) | 4/8 |
| trail-lock +100 give back 60 | 412 | 51.9 | 16.4 | 6,764 | 2,028 | 1.25 | 51.8 / 41.6 / 6.5 | 56 | 57.1 / 42.9 (58) | 49.9 / 47.3 | -4,007 [-12,864, +3,541] | 1.27 (8,752) | 4/8 |
| trail-lock +100 give back 100 | 413 | 51.8 | 22.7 | 9,381 | 2,028 | 1.35 | 62.6 / 33.4 / 4.0 | 42 | 60.7 / 39.3 (46) | 58.6 / 39.1 | -1,390 [-9,680, +6,330] | 1.34 (10,794) | 5/8 |
| trail-lock +150 give back 40 | 427 | 47.1 | 18.9 | 8,052 | 2,497 | 1.27 | 63.2 / 33.7 / 3.1 | 53 | 57.2 / 42.8 (48) | 53.3 / 45.6 | -2,718 [-12,079, +4,894] | 1.33 (10,746) | 5/8 |
| trail-lock +150 give back 60 | 427 | 47.1 | 20.4 | 8,714 | 2,496 | 1.29 | 65.4 / 33.7 / 0.8 | 52 | 57.8 / 42.2 (44) | 55.8 / 44.2 | -2,057 [-11,017, +5,723] | 1.32 (10,608) | 6/8 |
| trail-lock +150 give back 100 | 428 | 47.2 | 21.6 | 9,226 | 2,300 | 1.30 | 66.3 / 31.7 / 2.0 | 44 | 56.8 / 43.2 (42) | 56.4 / 42.5 | -1,545 [-10,267, +6,202] | 1.35 (11,437) | 5/8 |

### T5 other filters from the earlier unfinished scripts (applied on the preset-C base)
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | - | 1.38 (12,110) | 8/8 |
| no entry 10:00 [lock] | 369 | 51.5 | 21.7 | 8,026 | 1,985 | 1.35 | 60.6 / 32.6 / 6.8 | 54 | 55.1 / 44.9 (45) | 60.6 / 34.3 | -3,584 [-7,514, +3,389] | 1.39 (9,338) | 3/8 |
| **IS-pick** no entry 11:00 [lock] | 399 | 52.9 | 20.7 | 8,277 | 2,109 | 1.33 | 47.0 / 51.3 / 1.7 | 53 | 56.1 / 43.9 (44) | 43.6 / 54.7 | -3,332 [-6,804, -384] | 1.44 (12,348) | 4/8 |
| no entry 12:00 [lock] | 413 | 53.0 | 29.7 | 12,260 | 2,275 | 1.48 | 63.2 / 36.0 / 0.8 | 43 | 64.2 / 35.8 (41) | 53.3 / 46.7 | +652 [-830, +2,121] | 1.38 (11,878) | 6/8 |
| no entry 13:00 [lock] | 412 | 51.7 | 27.6 | 11,385 | 2,022 | 1.43 | 60.1 / 35.1 / 4.8 | 54 | 60.4 / 39.6 (40) | 54.7 / 40.5 | -224 [-1,822, +1,322] | 1.34 (10,825) | 5/8 |
| no entry 14:00 [lock] | 410 | 52.4 | 28.6 | 11,714 | 2,034 | 1.44 | 58.1 / 41.1 / 0.8 | 42 | 62.4 / 37.6 (40) | 46.5 / 53.5 | +105 [-1,075, +1,274] | 1.36 (11,208) | 4/8 |
| no entry 15:00 [lock] | 386 | 50.8 | 27.2 | 10,518 | 2,058 | 1.41 | 59.2 / 39.4 / 1.4 | 51 | 60.2 / 39.8 (43) | 48.7 / 50.1 | -1,091 [-3,492, +882] | 1.29 (9,043) | 5/8 |
| **IS-pick** no reverse after stop-out [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | +0 [+0, +0] | 1.38 (12,110) | 8/8 |
| no flip after any exit [lock] | 414 | 51.9 | 28.3 | 11,712 | 2,162 | 1.44 | 64.9 / 34.6 / 0.6 | 43 | 62.7 / 37.3 (40) | 59.8 / 40.2 | +102 [-966, +1,306] | 1.38 (11,799) | 6/8 |
| **IS-pick** extra check 15:30 (band entry) [lock] | 450 | 50.9 | 25.2 | 11,356 | 2,260 | 1.40 | 55.2 / 42.5 / 2.3 | 46 | 60.0 / 40.0 (39) | 52.4 / 47.3 | -252 [-1,727, +948] | 1.41 (13,539) | 5/8 |
| min band width >= IS p10 (76 pt) [lock] | 425 | 52.5 | 27.5 | 11,682 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.6 / 38.4 (39) | 51.3 / 48.4 | +72 [+0, +208] | 1.40 (12,208) | 6/8 |
| min sigma >= IS p10 (0.24%) [lock] | 400 | 53.0 | 28.5 | 11,403 | 1,835 | 1.46 | 73.4 / 24.1 / 2.5 | 53 | 63.9 / 36.1 (44) | 70.0 / 27.5 | -206 [-1,880, +2,441] | 1.39 (11,892) | 4/8 |
| min band width >= IS p20 (100 pt) [lock] | 420 | 52.9 | 28.2 | 11,846 | 2,022 | 1.44 | 60.3 / 39.4 / 0.3 | 49 | 62.7 / 37.3 (39) | 51.3 / 48.4 | +237 [-749, +977] | 1.41 (11,930) | 5/8 |
| **IS-pick** min sigma >= IS p20 (0.29%) [lock] | 380 | 53.7 | 27.8 | 10,549 | 1,527 | 1.46 | 75.9 / 16.7 / 7.4 | 52 | 67.1 / 32.9 (49) | 72.5 / 20.1 | -1,060 [-3,240, +3,592] | 1.42 (11,945) | 7/8 |
| min band width >= IS p30 (126 pt) [lock] | 405 | 53.8 | 30.3 | 12,273 | 1,925 | 1.48 | 71.4 / 24.1 / 4.5 | 50 | 65.4 / 34.6 (41) | 51.3 / 48.4 | +664 [-668, +1,849] | 1.39 (10,741) | 4/8 |
| min sigma >= IS p30 (0.33%) [lock] | 357 | 54.3 | 20.7 | 7,400 | 1,574 | 1.35 | 61.8 / 25.8 / 12.5 | 63 | 57.7 / 42.3 (49) | 57.5 / 36.5 | -4,210 [-7,943, +2,279] | 1.39 (10,680) | 3/8 |
| min band width >= IS p40 (149 pt) [lock] | 399 | 53.6 | 30.7 | 12,264 | 1,854 | 1.49 | 72.2 / 24.9 / 2.8 | 55 | 66.2 / 33.8 (42) | 56.4 / 40.8 | +654 [-1,501, +2,656] | 1.41 (10,240) | 5/8 |
| min sigma >= IS p40 (0.39%) [lock] | 310 | 55.5 | 17.2 | 5,340 | 2,084 | 1.27 | 40.2 / 40.2 / 19.5 | 50 | 51.2 / 48.8 (54) | 37.1 / 48.4 | -6,268 [-10,774, +1,428] | 1.40 (10,331) | 4/8 |

### T5b the same on the plain base (no lock)
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | - | 1.35 (11,816) | 8/8 |
| no entry 10:00 [nolock] | 382 | 45.0 | 25.2 | 9,612 | 2,402 | 1.35 | 59.8 / 36.0 / 4.2 | 48 | 49.6 / 50.4 (37) | 56.9 / 38.8 | -1,159 [-5,685, +4,525] | 1.36 (9,268) | 4/8 |
| **IS-pick** no entry 11:00 [nolock] | 420 | 44.5 | 17.7 | 7,438 | 3,099 | 1.23 | 46.5 / 50.4 / 3.1 | 46 | 42.3 / 57.7 (36) | 44.2 / 53.0 | -3,332 [-7,937, +127] | 1.43 (12,708) | 3/8 |
| no entry 12:00 [nolock] | 436 | 44.5 | 25.9 | 11,298 | 2,568 | 1.35 | 53.0 / 46.7 / 0.3 | 41 | 49.9 / 50.1 (34) | 50.4 / 49.3 | +528 [-1,267, +2,244] | 1.36 (11,646) | 6/8 |
| no entry 13:00 [nolock] | 437 | 43.5 | 17.2 | 7,495 | 2,408 | 1.22 | 41.6 / 54.1 / 4.2 | 44 | 43.8 / 56.2 (32) | 40.5 / 58.9 | -3,276 [-9,547, +478] | 1.32 (10,594) | 3/8 |
| no entry 14:00 [nolock] | 430 | 44.2 | 26.6 | 11,451 | 2,616 | 1.35 | 51.6 / 44.5 / 4.0 | 37 | 50.3 / 49.7 (31) | 47.0 / 52.7 | +680 [-892, +2,277] | 1.33 (10,721) | 4/8 |
| no entry 15:00 [nolock] | 404 | 42.1 | 23.7 | 9,592 | 2,121 | 1.30 | 45.3 / 52.4 / 2.3 | 48 | 47.2 / 52.8 (36) | 42.2 / 55.8 | -1,178 [-3,749, +1,182] | 1.27 (8,640) | 4/8 |
| no reverse after stop-out [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | +0 [+0, +0] | 1.35 (11,816) | 8/8 |
| **IS-pick** no flip after any exit [nolock] | 430 | 43.5 | 26.4 | 11,370 | 2,744 | 1.35 | 61.8 / 35.7 / 2.5 | 42 | 51.1 / 48.9 (33) | 55.2 / 44.8 | +600 [-878, +2,147] | 1.35 (11,555) | 6/8 |
| **IS-pick** extra check 15:30 (band entry) [nolock] | 480 | 43.5 | 24.1 | 11,550 | 2,478 | 1.33 | 49.9 / 49.9 / 0.3 | 42 | 48.5 / 51.5 (31) | 47.6 / 52.1 | +779 [-1,243, +2,863] | 1.39 (13,426) | 5/8 |
| min band width >= IS p10 (76 pt) [nolock] | 449 | 44.1 | 24.2 | 10,844 | 2,228 | 1.32 | 50.7 / 42.8 / 6.5 | 42 | 48.4 / 51.6 (31) | 45.9 / 53.8 | +72 [+0, +208] | 1.37 (11,846) | 6/8 |
| min sigma >= IS p10 (0.24%) [nolock] | 423 | 44.9 | 26.6 | 11,272 | 2,228 | 1.36 | 62.3 / 30.9 / 6.8 | 46 | 50.5 / 49.5 (34) | 60.1 / 33.1 | +500 [-1,836, +2,715] | 1.35 (11,357) | 5/8 |
| min band width >= IS p20 (100 pt) [nolock] | 443 | 44.7 | 24.4 | 10,814 | 2,228 | 1.32 | 50.4 / 42.8 / 6.8 | 42 | 48.3 / 51.7 (31) | 45.6 / 53.8 | +42 [-1,300, +981] | 1.37 (11,318) | 6/8 |
| **IS-pick** min sigma >= IS p20 (0.29%) [nolock] | 403 | 44.9 | 25.5 | 10,286 | 2,076 | 1.34 | 68.0 / 27.2 / 4.8 | 52 | 51.7 / 48.3 (37) | 66.0 / 29.2 | -485 [-3,331, +3,341] | 1.38 (11,368) | 6/8 |
| min band width >= IS p30 (126 pt) [nolock] | 430 | 45.3 | 26.4 | 11,338 | 2,228 | 1.35 | 56.4 / 39.4 / 4.2 | 45 | 49.1 / 50.9 (31) | 46.7 / 53.3 | +566 [-1,248, +2,099] | 1.35 (10,278) | 5/8 |
| min sigma >= IS p30 (0.33%) [nolock] | 376 | 46.0 | 21.7 | 8,148 | 2,994 | 1.30 | 52.1 / 41.9 / 5.9 | 56 | 46.4 / 53.6 (39) | 50.4 / 43.6 | -2,624 [-7,023, +2,890] | 1.36 (10,282) | 4/8 |
| min band width >= IS p40 (149 pt) [nolock] | 422 | 45.7 | 28.2 | 11,910 | 2,228 | 1.37 | 59.5 / 39.7 / 0.8 | 46 | 50.6 / 49.4 (34) | 53.5 / 45.6 | +1,138 [-1,018, +3,157] | 1.37 (9,658) | 5/8 |
| min sigma >= IS p40 (0.39%) [nolock] | 326 | 47.9 | 20.5 | 6,687 | 2,985 | 1.27 | 39.4 / 44.8 / 15.9 | 55 | 44.3 / 55.7 (43) | 36.0 / 51.6 | -4,084 [-9,341, +2,224] | 1.36 (9,620) | 4/8 |

### T6 IS-only selection (rule fixed before looking at held-out) and combinations
Selected per family on the plain base: {"N10-12": "N11 skip Monday [nolock]", "vwap": "VWAP side filter [nolock]", "hours": "no entry 11:00 [nolock]", "norev": "no flip after any exit [nolock]", "addon-1530": "extra check 15:30 (band entry) [nolock]", "width": "min sigma >= IS p20 (0.29%) [nolock]", "lock": "lock 200->+50"}

Selected per family on the preset-C base: {"N10-12": "N11 skip Monday [lock]", "vwap": "VWAP side filter [lock]", "hours": "no entry 11:00 [lock]", "norev": "no reverse after stop-out [lock]", "addon-1530": "extra check 15:30 (band entry) [lock]", "width": "min sigma >= IS p20 (0.29%) [lock]"}

IS ranking of filter families on the preset-C base (IS edge ratio): no entry 11:00 (1.70), N11 skip Monday (1.62), min sigma >= IS p20 (0.29%) (1.59), extra check 15:30 (band entry) (1.58), VWAP side filter (1.51)

| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | - | 1.38 (12,110) | 8/8 |
| COMBO(best-2 IS) = no entry 11:00 + N11 skip Monday | 336 | 54.8 | 25.7 | 8,646 | 2,135 | 1.42 | 55.8 / 36.3 / 7.9 | 61 | 63.0 / 37.0 (54) | 52.4 / 41.9 | -2,964 [-7,342, +1,342] | 1.49 (10,847) | 5/8 |
| COMBO(best-3 IS) = no entry 11:00 + N11 skip Monday + min sigma >= IS p20 (0.29%) | 297 | 56.6 | 21.9 | 6,491 | 1,211 | 1.38 | 52.4 / 25.8 / 21.8 | 63 | 65.0 / 35.0 (73) | 49.0 / 33.4 | -5,118 [-8,586, +995] | 1.54 (10,518) | 5/8 |

### T7 random-direction benchmark (200 seeds per base; same timing, exits, costs; direction = coin)
| base | era | metric | random mean | random 5th-95th pct | random best of 200 | real strategy | real beats % of seeds |
|---|---|---|---|---|---|---|---|
| nolock | IS | $/trade | 2.0 | -4.4 .. 8.0 | 11.4 | 16.3 | 100.0 |
| nolock | IS | net $ | 1,938 | -4,249 .. 7,478 | 10,742 | 11,816 | 100.0 |
| nolock | IS | PF | 1.05 | 0.91 .. 1.19 | 1.28 | 1.35 | 100.0 |
| nolock | IS | win % | 45.3 | 42.9 .. 47.6 | 48.9 | 44.4 | 26.5 |
| nolock | IS | trades | 957 | 934 .. 980 | 997 | 726 | 0.0 |
| nolock | IS | Pro 25K roll PASS % | 26.7 | 12.8 .. 42.2 | 51.0 | 40.5 | 92.0 |
| nolock | IS | Pro 25K roll BUST % | 50.8 | 31.1 .. 67.9 | 20.2 (lowest) | 17.7 | 100.0 (seeds with MORE busts) |
| nolock | HO | $/trade | 2.5 | -10.1 .. 15.1 | 18.4 | 23.9 | 100.0 |
| nolock | HO | net $ | 1,443 | -6,044 .. 8,786 | 10,686 | 10,771 | 100.0 |
| nolock | HO | PF | 1.04 | 0.87 .. 1.22 | 1.28 | 1.31 | 100.0 |
| nolock | HO | win % | 43.5 | 40.7 .. 46.3 | 48.8 | 43.9 | 56.0 |
| nolock | HO | trades | 591 | 573 .. 609 | 622 | 451 | 0.0 |
| nolock | HO | Pro 25K roll PASS % | 31.4 | 13.3 .. 49.1 | 59.5 | 50.7 | 96.0 |
| nolock | HO | Pro 25K roll BUST % | 67.7 | 50.6 .. 85.6 | 38.8 (lowest) | 46.5 | 96.5 (seeds with MORE busts) |
| lock | IS | $/trade | 2.3 | -3.6 .. 8.1 | 12.4 | 16.8 | 100.0 |
| lock | IS | net $ | 2,196 | -3,478 .. 7,463 | 11,452 | 12,110 | 100.0 |
| lock | IS | PF | 1.06 | 0.92 .. 1.19 | 1.31 | 1.38 | 100.0 |
| lock | IS | win % | 46.3 | 44.3 .. 48.6 | 49.7 | 46.3 | 49.0 |
| lock | IS | trades | 953 | 929 .. 974 | 982 | 722 | 0.0 |
| lock | IS | Pro 25K roll PASS % | 26.8 | 14.6 .. 41.3 | 51.4 | 41.0 | 94.0 |
| lock | IS | Pro 25K roll BUST % | 50.4 | 29.1 .. 70.1 | 15.0 (lowest) | 14.3 | 100.0 (seeds with MORE busts) |
| lock | HO | $/trade | 4.0 | -7.4 .. 16.2 | 28.4 | 27.2 | 99.5 |
| lock | HO | net $ | 2,235 | -4,238 .. 8,788 | 15,354 | 11,609 | 99.0 |
| lock | HO | PF | 1.07 | 0.89 .. 1.28 | 1.53 | 1.43 | 99.5 |
| lock | HO | win % | 48.6 | 45.4 .. 51.7 | 55.2 | 52.2 | 97.0 |
| lock | HO | trades | 563 | 545 .. 579 | 584 | 427 | 0.0 |
| lock | HO | Pro 25K roll PASS % | 33.2 | 14.1 .. 54.2 | 63.2 | 60.3 | 99.0 |
| lock | HO | Pro 25K roll BUST % | 64.2 | 42.5 .. 83.3 | 22.7 (lowest) | 39.4 | 98.0 (seeds with MORE busts) |

### T8 last-half-hour momentum (15:30 -> 16:00, $250 stop, 1 micro): the six candidate signals alone
| signal / mode | IS trades | IS win % | IS PF | IS net $ | HO trades | HO win % | HO PF | HO net $ |
|---|---|---|---|---|---|---|---|---|
| first-30min return / continuation | 1037 | 47.7 | 0.88 | -3,518 | 649 | 45.6 | 0.92 | -2,216 |
| first-30min return / reversal | 1037 | 48.0 | 0.99 | -236 | 649 | 51.6 | 1.05 | 1,206 |
| open-to-15:29 return / continuation | 1042 | 49.5 | 1.08 | 2,202 | 648 | 44.6 | 0.73 | -7,645 |
| open-to-15:29 return / reversal | 1042 | 46.3 | 0.81 | -5,976 | 648 | 52.6 | 1.31 | 6,640 |
| **IS-pick** prior-close-to-15:29 return / continuation | 1042 | 49.9 | 1.14 | 3,630 | 649 | 45.9 | 0.79 | -5,942 |
| prior-close-to-15:29 return / reversal | 1042 | 45.9 | 0.77 | -7,404 | 649 | 51.3 | 1.22 | 4,932 |

### T9 LHH as an add-on to NOISE (one position at a time; LHH trade dropped if NOISE is still open at 15:30)
| stream | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | corr(day P&L) HO |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOISE alone [nolock] | 451 | 43.9 | 23.9 | 10,771 | 2,228 | 1.31 | 50.7 / 46.5 / 2.8 | 42 | 48.0 / 52.0 (31) | 45.9 / 53.8 | - | 1.35 (11,816) | - |
| **IS-pick** NOISE[nolock] + LHH prior-close-to-15:29 return / continuation | 885 | 46.1 | 11.0 | 9,740 | 4,160 | 1.19 | 46.2 / 53.8 / 0.0 | 33 | 40.8 / 59.2 (24) | 41.4 / 58.6 | -1,031 [-5,531, +4,048] | 1.32 (15,760) | 0.26 |
| NOISE[nolock] + LHH first-30min return / continuation | 885 | 46.1 | 14.3 | 12,649 | 3,170 | 1.26 | 54.7 / 45.3 / 0.0 | 27 | 50.1 / 49.9 (27) | 52.4 / 47.6 | +1,878 [-2,999, +7,688] | 1.18 (9,330) | 0.08 |
| NOISE[nolock] + LHH first-30min return / reversal | 885 | 47.0 | 11.4 | 10,097 | 3,560 | 1.20 | 49.9 / 50.1 / 0.0 | 41 | 43.8 / 56.2 (29) | 49.9 / 50.1 | -674 [-4,945, +3,233] | 1.21 (10,702) | -0.10 |
| NOISE[nolock] + LHH open-to-15:29 return / continuation | 884 | 45.1 | 9.1 | 8,036 | 5,638 | 1.16 | 50.7 / 49.3 / 0.0 | 38 | 37.8 / 62.2 (25) | 50.4 / 49.6 | -2,734 [-7,232, +2,594] | 1.28 (14,332) | 0.27 |
| NOISE[nolock] + LHH open-to-15:29 return / reversal | 884 | 48.0 | 16.6 | 14,714 | 1,754 | 1.31 | 43.1 / 56.9 / 0.0 | 26 | 50.9 / 49.1 (30) | 40.5 / 59.5 | +3,942 [-316, +7,984] | 1.10 (5,684) | -0.28 |
| NOISE[nolock] + LHH prior-close-to-15:29 return / reversal | 885 | 47.0 | 14.7 | 13,006 | 2,776 | 1.27 | 43.6 / 56.4 / 0.0 | 30 | 48.6 / 51.4 (29) | 42.5 / 57.5 | +2,235 [-1,805, +6,606] | 1.08 (4,257) | -0.26 |
| NOISE alone [lock] | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | - | 1.38 (12,110) | - |
| **IS-pick** NOISE[lock] + LHH prior-close-to-15:29 return / continuation | 891 | 49.6 | 9.6 | 8,548 | 3,346 | 1.18 | 45.3 / 54.7 / 0.0 | 29 | 45.1 / 54.9 (27) | 42.8 / 57.2 | -3,062 [-7,802, +1,973] | 1.33 (15,989) | 0.23 |
| NOISE[lock] + LHH first-30min return / continuation | 891 | 49.8 | 13.3 | 11,894 | 2,384 | 1.26 | 55.0 / 45.0 / 0.0 | 28 | 52.0 / 48.0 (28) | 52.7 / 47.3 | +286 [-5,008, +6,185] | 1.18 (9,560) | 0.03 |
| NOISE[lock] + LHH first-30min return / reversal | 891 | 51.0 | 12.5 | 11,166 | 3,526 | 1.25 | 53.0 / 47.0 / 0.0 | 40 | 52.0 / 48.0 (32) | 52.7 / 47.3 | -444 [-5,055, +3,977] | 1.21 (10,739) | -0.02 |
| NOISE[lock] + LHH open-to-15:29 return / continuation | 890 | 48.7 | 7.7 | 6,844 | 4,824 | 1.14 | 49.6 / 50.4 / 0.0 | 35 | 40.0 / 60.0 (27) | 48.4 / 51.6 | -4,765 [-9,525, +527] | 1.30 (14,562) | 0.27 |
| NOISE[lock] + LHH open-to-15:29 return / reversal | 890 | 52.1 | 18.2 | 16,220 | 1,738 | 1.38 | 63.2 / 36.8 / 0.0 | 35 | 64.6 / 35.4 (32) | 59.5 / 40.5 | +4,611 [+130, +8,934] | 1.11 (5,721) | -0.25 |
| NOISE[lock] + LHH prior-close-to-15:29 return / reversal | 891 | 51.2 | 16.3 | 14,512 | 2,444 | 1.33 | 52.7 / 47.3 / 0.0 | 33 | 60.1 / 39.9 (30) | 51.0 / 49.0 | +2,904 [-1,179, +7,618] | 1.08 (4,294) | -0.21 |

### T10 machine check: which variants beat their own base on ALL held-out tests?
(HO $/trade up, roll PASS >= base, roll BUST <= base, boot PASS >= base, boot BUST <= base, and IS PF >= base IS PF.)

24 of 82 variants pass: 

| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs base [95% CI] | IS PF (net) | yrs PF>=base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **IS-pick** N11 skip Monday [nolock] | 382 | 45.5 | 30.3 | 11,572 | 2,378 | 1.40 | 59.2 / 37.7 / 3.1 | 42 | 56.2 / 43.8 (36) | 56.7 / 40.2 | +801 [-2,276, +4,152] | 1.41 (10,999) | 6/8 |
| N10+N11 [nolock] | 224 | 46.4 | 36.5 | 8,165 | 2,004 | 1.42 | 51.3 / 35.4 / 13.3 | 68 | 48.2 / 51.8 (56) | 50.7 / 36.0 | -2,606 [-9,315, +3,531] | 1.43 (7,986) | 7/8 |
| **IS-pick** VWAP side filter [nolock] | 419 | 43.4 | 27.2 | 11,382 | 2,505 | 1.36 | 62.3 / 35.1 / 2.5 | 42 | 52.5 / 47.5 (35) | 52.1 / 47.9 | +611 [-1,653, +2,504] | 1.36 (11,602) | 5/8 |
| no entry 10:00 [nolock] | 382 | 45.0 | 25.2 | 9,612 | 2,402 | 1.35 | 59.8 / 36.0 / 4.2 | 48 | 49.6 / 50.4 (37) | 56.9 / 38.8 | -1,159 [-5,685, +4,525] | 1.36 (9,268) | 4/8 |
| **IS-pick** no flip after any exit [nolock] | 430 | 43.5 | 26.4 | 11,370 | 2,744 | 1.35 | 61.8 / 35.7 / 2.5 | 42 | 51.1 / 48.9 (33) | 55.2 / 44.8 | +600 [-878, +2,147] | 1.35 (11,555) | 6/8 |
| **IS-pick** N11 skip Monday [lock] | 359 | 54.3 | 33.9 | 12,176 | 2,096 | 1.55 | 67.4 / 29.5 / 3.1 | 53 | 69.4 / 30.6 (44) | 66.0 / 30.9 | +566 [-2,522, +3,909] | 1.44 (11,067) | 6/8 |
| no entry 12:00 [lock] | 413 | 53.0 | 29.7 | 12,260 | 2,275 | 1.48 | 63.2 / 36.0 / 0.8 | 43 | 64.2 / 35.8 (41) | 53.3 / 46.7 | +652 [-830, +2,121] | 1.38 (11,878) | 6/8 |
| lock 100->+0 | 427 | 40.5 | 26.0 | 11,098 | 2,028 | 1.41 | 59.2 / 33.7 / 7.1 | 47 | 61.5 / 38.5 (40) | 46.5 / 53.5 | +326 [-8,161, +5,314] | 1.38 (12,224) | 5/8 |
| lock 100->+10 | 427 | 52.2 | 27.2 | 11,609 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.5 / 38.5 (39) | 51.3 / 48.4 | +838 [-7,705, +5,854] | 1.38 (12,110) | 6/8 |
| lock 125->+10 | 436 | 49.8 | 24.6 | 10,718 | 2,028 | 1.37 | 50.7 / 43.3 / 5.9 | 47 | 57.6 / 42.4 (38) | 43.9 / 56.1 | -54 [-8,353, +4,614] | 1.38 (12,362) | 6/8 |
| lock 200->+0 | 448 | 43.5 | 25.9 | 11,618 | 2,224 | 1.35 | 55.0 / 42.8 / 2.3 | 44 | 50.4 / 49.6 (31) | 47.6 / 52.4 | +846 [+221, +1,655] | 1.37 (12,224) | 8/8 |
| lock 200->+10 | 448 | 45.3 | 26.1 | 11,690 | 2,224 | 1.35 | 55.8 / 41.9 / 2.3 | 44 | 50.7 / 49.3 (31) | 48.2 / 51.8 | +919 [+150, +1,861] | 1.37 (12,284) | 8/8 |
| lock 200->+25 | 446 | 45.1 | 25.4 | 11,308 | 2,224 | 1.34 | 56.1 / 41.9 / 2.0 | 44 | 50.3 / 49.7 (32) | 48.2 / 51.8 | +536 [-1,082, +1,922] | 1.37 (12,341) | 7/8 |
| **IS-pick** lock 200->+50 | 444 | 45.0 | 26.4 | 11,722 | 2,224 | 1.35 | 56.1 / 41.6 / 2.3 | 44 | 50.5 / 49.5 (31) | 48.2 / 51.8 | +950 [-716, +2,593] | 1.38 (12,521) | 7/8 |
| min band width >= IS p10 (76 pt) [nolock] | 449 | 44.1 | 24.2 | 10,844 | 2,228 | 1.32 | 50.7 / 42.8 / 6.5 | 42 | 48.4 / 51.6 (31) | 45.9 / 53.8 | +72 [+0, +208] | 1.37 (11,846) | 6/8 |
| **IS-pick** min sigma >= IS p20 (0.29%) [nolock] | 403 | 44.9 | 25.5 | 10,286 | 2,076 | 1.34 | 68.0 / 27.2 / 4.8 | 52 | 51.7 / 48.3 (37) | 66.0 / 29.2 | -485 [-3,331, +3,341] | 1.38 (11,368) | 6/8 |
| min band width >= IS p30 (126 pt) [nolock] | 430 | 45.3 | 26.4 | 11,338 | 2,228 | 1.35 | 56.4 / 39.4 / 4.2 | 45 | 49.1 / 50.9 (31) | 46.7 / 53.3 | +566 [-1,248, +2,099] | 1.35 (10,278) | 5/8 |
| min band width >= IS p40 (149 pt) [nolock] | 422 | 45.7 | 28.2 | 11,910 | 2,228 | 1.37 | 59.5 / 39.7 / 0.8 | 46 | 50.6 / 49.4 (34) | 53.5 / 45.6 | +1,138 [-1,018, +3,157] | 1.37 (9,658) | 5/8 |
| min band width >= IS p10 (76 pt) [lock] | 425 | 52.5 | 27.5 | 11,682 | 2,028 | 1.43 | 60.3 / 39.4 / 0.3 | 46 | 61.6 / 38.4 (39) | 51.3 / 48.4 | +72 [+0, +208] | 1.40 (12,208) | 6/8 |
| min sigma >= IS p10 (0.24%) [lock] | 400 | 53.0 | 28.5 | 11,403 | 1,835 | 1.46 | 73.4 / 24.1 / 2.5 | 53 | 63.9 / 36.1 (44) | 70.0 / 27.5 | -206 [-1,880, +2,441] | 1.39 (11,892) | 4/8 |
| min band width >= IS p20 (100 pt) [lock] | 420 | 52.9 | 28.2 | 11,846 | 2,022 | 1.44 | 60.3 / 39.4 / 0.3 | 49 | 62.7 / 37.3 (39) | 51.3 / 48.4 | +237 [-749, +977] | 1.41 (11,930) | 5/8 |
| **IS-pick** min sigma >= IS p20 (0.29%) [lock] | 380 | 53.7 | 27.8 | 10,549 | 1,527 | 1.46 | 75.9 / 16.7 / 7.4 | 52 | 67.1 / 32.9 (49) | 72.5 / 20.1 | -1,060 [-3,240, +3,592] | 1.42 (11,945) | 7/8 |
| min band width >= IS p30 (126 pt) [lock] | 405 | 53.8 | 30.3 | 12,273 | 1,925 | 1.48 | 71.4 / 24.1 / 4.5 | 50 | 65.4 / 34.6 (41) | 51.3 / 48.4 | +664 [-668, +1,849] | 1.39 (10,741) | 4/8 |
| min band width >= IS p40 (149 pt) [lock] | 399 | 53.6 | 30.7 | 12,264 | 1,854 | 1.49 | 72.2 / 24.9 / 2.8 | 55 | 66.2 / 33.8 (42) | 56.4 / 40.8 | +654 [-1,501, +2,656] | 1.41 (10,240) | 5/8 |


### T13 paired block-bootstrap of the Pro 25K eval outcome difference (variant minus its base, held-out days resampled in 10-session blocks, 400 resamples)
| variant (vs its base) | dPASS % [95% CI] | P(PASS better) | dBUST % [95% CI] | P(BUST lower) |
|---|---|---|---|---|
| N11 skip Monday [lock] | +5.1 [-12.2, +23.8] | 0.70 | -8.1 [-28.6, +8.2] | 0.78 |
| VWAP side filter [lock] | -1.8 [-11.6, +7.1] | 0.34 | +1.1 [-12.5, +12.2] | 0.39 |
| no entry 11:00 [lock] | -7.9 [-25.5, +7.1] | 0.18 | +5.7 [-11.3, +23.2] | 0.26 |
| N10 skip low-vol tercile [lock] | -11.4 [-40.2, +12.5] | 0.18 | -6.5 [-36.0, +21.5] | 0.68 |
| N10+N11 [lock] | -8.2 [-37.7, +17.9] | 0.29 | -14.8 [-42.8, +14.2] | 0.82 |
| min sigma >= IS p10 (0.24%) [lock] | +1.9 [-12.8, +16.2] | 0.60 | -4.6 [-22.7, +9.9] | 0.70 |
| min sigma >= IS p20 (0.29%) [lock] | +5.0 [-11.9, +22.1] | 0.71 | -9.7 [-31.7, +9.1] | 0.83 |
| min sigma >= IS p30 (0.33%) [lock] | -5.0 [-28.9, +17.9] | 0.31 | -3.4 [-28.9, +23.0] | 0.61 |
| min band width >= IS p30 (126 pt) [lock] | +2.3 [-5.4, +12.2] | 0.71 | -3.1 [-15.6, +4.8] | 0.74 |
| min band width >= IS p40 (149 pt) [lock] | +3.0 [-8.8, +17.3] | 0.68 | -4.4 [-21.0, +8.2] | 0.73 |
| no flip after any exit [lock] | +0.5 [-5.7, +8.2] | 0.52 | -0.8 [-12.2, +6.3] | 0.52 |
| extra check 15:30 (band entry) [lock] | -1.0 [-11.1, +7.7] | 0.38 | +1.2 [-10.5, +13.6] | 0.37 |
| N11 skip Monday [nolock] | +5.1 [-8.8, +23.0] | 0.71 | -7.2 [-27.8, +8.0] | 0.80 |
| VWAP side filter [nolock] | +2.0 [-8.8, +14.5] | 0.61 | -3.0 [-18.7, +8.5] | 0.65 |
| no flip after any exit [nolock] | +1.8 [-7.1, +12.5] | 0.61 | -2.3 [-14.5, +7.7] | 0.66 |
| min sigma >= IS p20 (0.29%) [nolock] | +1.9 [-15.6, +19.3] | 0.59 | -4.9 [-23.8, +14.2] | 0.69 |
| extra check 15:30 (band entry) [nolock] | +1.0 [-9.6, +10.8] | 0.61 | -1.0 [-13.9, +12.5] | 0.60 |
| lock 200->+10 | +2.6 [-0.6, +11.1] | 0.86 | -2.9 [-13.0, +0.6] | 0.83 |
| lock 200->+50 | +2.6 [-4.0, +11.9] | 0.75 | -2.9 [-13.9, +4.8] | 0.76 |
| lock 75->+50 | +9.7 [-16.4, +32.9] | 0.81 | -19.6 [-47.6, +5.4] | 0.94 |
| lock 75->+10 | +12.6 [-6.5, +32.0] | 0.91 | -16.7 [-41.1, +4.0] | 0.95 |
| trail-lock +100 give back 100 | +7.5 [-14.7, +31.2] | 0.72 | -10.5 [-34.3, +11.9] | 0.81 |
| lock 100->+10 | +9.2 [-7.7, +26.9] | 0.88 | -11.1 [-31.2, +7.1] | 0.90 |
| session-9 original (1% stop) [nolock] | +2.1 [-12.2, +17.0] | 0.62 | -2.0 [-17.0, +14.2] | 0.61 |
| COMBO(best-2 IS) = no entry 11:00 + N11 skip Monday | -4.0 [-23.8, +18.1] | 0.34 | -2.5 [-26.1, +18.1] | 0.56 |
| COMBO(best-3 IS) = no entry 11:00 + N11 skip Monday + min sigma >= IS p20 (0.29%) | -6.0 [-31.7, +21.5] | 0.33 | -10.8 [-39.1, +16.7] | 0.74 |
| BASE [lock] vs BASE [nolock] | +9.2 [-7.7, +26.9] | 0.88 | -11.1 [-31.2, +7.1] | 0.90 |
| NOISE[nolock] + LHH pick (prior-close-to-15:29 return / continuation) | -5.1 [-24.1, +12.5] | 0.30 | +7.3 [-11.9, +28.9] | 0.21 |
| NOISE[lock] + LHH pick (prior-close-to-15:29 return / continuation) | -12.7 [-32.9, +6.8] | 0.10 | +16.5 [-4.3, +43.1] | 0.06 |

### T11 preset-C trades by weekday and period ($/trade, [n trades], win %)
| period | Mon | Tue | Wed | Thu | Fri | Tue-Fri avg |
|---|---|---|---|---|---|---|
| 2019-05..2021-10 (never used before) | +7.6 [86] 40% | +16.0 [68] 50% | +4.5 [67] 46% | -1.5 [77] 39% | +13.1 [70] 50% | +7.8 [282] |
| 2021-11..2023-12 (session-15 pick) | +6.5 [60] 45% | +10.5 [70] 47% | +16.2 [75] 44% | +49.5 [66] 56% | +44.0 [83] 48% | +30.2 [294] |
| 2024-01..2026-11 (held-out) | -8.3 [68] 41% | +39.1 [90] 59% | +23.0 [86] 58% | +39.2 [85] 52% | +34.1 [98] 49% | +33.9 [359] |

### T12 preset-C trades by band width (sigma at the entry bar; IS 20th percentile = 0.289% of price) ($/trade [n])
| period | sigma < p20 | sigma >= p20 |
|---|---|---|
| 2019-05..2021-10 (never used before) | +0.7 [102] | +10.4 [266] |
| 2021-11..2023-12 (session-15 pick) | +0.0 [43] | +29.8 [311] |
| 2024-01..2026-11 (held-out) | +25.5 [108] | +27.8 [319] |

Welch t of Monday vs Tue-Fri $/trade: 2019-05..2021-10 t=-0.02; 2021-11..2023-12 t=-0.99; 2024-01..2026-11 t=-1.51; 

### T14 exploratory combination (post-hoc, not IS-selected)
| variant | HO trades | win % | $/trade | net $ | max DD $ | PF | roll PASS / BUST / open % | days to pass (med) | boot PASS / BUST % (med d) | strict PASS / BUST % | dNet vs preset C [95% CI] | IS PF (net) | paired eval diff vs preset C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXPLORATORY preset C + skip Monday + min sigma p20 [lock] | 319 | 57.7 | 35.4 | 11,282 | 1,433 | 1.62 | 75.9 / 18.1 / 5.9 | 52 | 74.6 / 25.4 (55) | 74.8 / 19.8 | -326 [-3,046, +5,380] | 1.48 (10,732) | dPASS +10.1 [-11.0,+32.6], dBUST -18.5 [-44.8,+3.1] |
| EXPLORATORY preset C + min sigma p20 + no flip after any exit [lock] | 371 | 53.6 | 29.1 | 10,786 | 1,445 | 1.49 | 82.2 / 8.8 / 9.1 | 50 | 68.7 / 31.3 (50) | 79.0 / 11.9 | -823 [-3,055, +3,833] | 1.41 (11,397) | dPASS +6.3 [-11.0,+25.8], dBUST -11.9 [-35.4,+6.2] |

### T15 the same streams in three non-overlapping periods (trades / $/trade / PF / net $ / max closed-trade DD $)
| stream | 2019-05..2021-10 | 2021-11..2023-12 | 2024-01..2026-11 |
|---|---|---|---|
| preset C (base) | 368 / 7.7 / 1.21 / 2,850 / 1,058 | 354 / 26.2 / 1.50 / 9,260 / 1,109 | 427 / 27.2 / 1.43 / 11,609 / 2,028 |
| preset C + min sigma p20 | 312 / 8.3 / 1.22 / 2,584 / 833 | 330 / 28.4 / 1.56 / 9,361 / 714 | 380 / 27.8 / 1.46 / 10,549 / 1,527 |
| preset C + skip Monday | 282 / 7.8 / 1.21 / 2,198 / 706 | 294 / 30.2 / 1.59 / 8,868 / 917 | 359 / 33.9 / 1.55 / 12,176 / 2,096 |
| EXPL: C + Monday + sigma p20 | 244 / 7.4 / 1.21 / 1,808 / 608 | 278 / 32.1 / 1.65 / 8,925 / 840 | 319 / 35.4 / 1.62 / 11,282 / 1,433 |

## 4. Reading the tables (plain language)

**Baselines.** Plain NOISE ($250 stop): 43.9% win, +$23.9 per trade, 451 trades in 2.8 years, PF 1.31, max drawdown $2,228 (one micro). Pro 25K: roll PASS 50.7% / BUST 46.5%; bootstrap 48% / 52%, median ~42 sessions to pass.
Preset C (lock): win rate 52.2%, +$27.2/trade, PF 1.43, DD $2,028, PASS 60.3% / BUST 39.4% (bootstrap 61.5 / 38.5), median 46 sessions. Preset C vs plain: dPASS +9.2 [-7.7, +26.9], dBUST -11.1 [-31.2, +7.1], P(better) 0.88 / 0.90 - the best-supported
change in the whole study, and consistent in IS (PF 1.38 vs 1.35, win 46.3 vs 44.4%) and PF is better or equal in 6 of 8 calendar years (worse in 2021 and 2025). It cuts win-size, so the win rate rise (44 -> 52%) is partly arithmetic, not new edge.
The Pro 25K itself stays marginal: even the best row busts the eval about 1 time in 3 (the loss limit is only 4 stop-outs at one micro, as session 15 already said).

**N10 / N11 / N12 (T2).** N10 (skip lowest-volatility tercile of the past 500 days) removes ~43% of the trades: PF up (1.48) but net profit -$3.7k, PASS down (45% with 30% of runs still unfinished after 120 sessions), median days to pass 74. N12 (skip Friday): PF unchanged (1.42), net -$3.3k, better than base in only 2 of 8 years.
N11 (skip Monday): +$566 net with 16% fewer trades, win 54.3%, PF 1.55, PASS 67.4 / BUST 29.5 (bootstrap 69.4 / 30.6) - best of the three, paired dPASS +5.1 [-12.2, +23.8], dBUST -8.1 [-28.6, +8.2]. **But** T11 shows Monday is not worse in 2019-05..2021-10
(+$7.6 vs +$7.8 for Tue-Fri, a period nobody had used when N11 was found in session 10); it is worse only in 2021-11..2023 (t = -1.0) and 2024-26 (t = -1.5). So this is a plausible noise artefact, not a confirmed day-of-week effect.

**VWAP filter (T3).** Long only above / short only below session VWAP: nothing. On preset C: net -$579, PASS 58.4 vs 60.3, PF unchanged 1.43, better than base in 4 of 8 years. The slope version is worse. The exit rule already uses VWAP, so the entry filter is nearly redundant.

**Profit-lock variants (T4).** Over 24 fixed (trigger, lock) pairs and 9 trailing locks the shipped 100 -> +10 sits on a broad plateau: neighbours 75 -> +10 (HO PF 1.49, PASS 61.8 / BUST 30.9, but weaker IS: PF 1.33 vs 1.38 so it would not be IS-selected), 125 -> +10, 75 -> +50 (PASS 70.8 / BUST 28.9, but IS PF 1.27 and IS net $8.3k vs $11.8k for plain), all fine; 50-point triggers cut winners
(IS PF 1.19-1.29). A trailing lock (stop trails best price by 40-100 pt after +75..+150) is worse than the fixed lock (PF 1.20-1.35, net -$1.5k..-$6.0k). Locks at +200 pt barely change anything but are the only two variants with a net-profit interval entirely above zero (+$919 [+150, +1,861] for 200 -> +10): too small
to matter (about $1.3 per trading day) and dominated by preset C. Nothing beats 100 -> +10 on both periods. Do not re-tune the lock.

**Other filters (T5).** "No entry at 11:00" is the IS champion (IS PF 1.44, IS ratio 1.70) but held-out PF 1.33 and net -$3.3k with a negative-only interval (-$6.8k..-$0.4k): the clearest over-fit of the study. An extra 15:30 band check adds ~20 trades, no gain (net -$252, PF 1.40 vs 1.43).
No-reverse-after-stop is a no-op (stop-outs never land on a check bar); "no flip after any exit" is tiny. Band-width floors: sigma floors at the IS 10th / 20th percentile improve held-out BUST and drawdown (T0 row: DD $1,527 vs $2,028, roll PASS 75.9 / BUST 16.7, bootstrap 67.1 / 32.9, strict 72.5 / 20.1) at -$1,060 net (6%-9%);
paired dPASS +5.0 [-11.9, +22.1], dBUST -9.7 [-31.7, +9.1]. But (T12) the trades it removes were not worse in the held-out period (+$25.5 vs +$27.8/trade) - they were ~zero only in 2019-2023 - and a harder floor (30th/40th percentile) is mixed to worse. The benefit comes from avoiding a handful of clusters of losses, not a stable signal.

**Lenient machine check (T10).** With the weak rule 'HO $/trade up, PASS >= base, BUST <= base on roll and boot, IS PF >= base' 24 of the variants "beat" their base - this is what chance plus ~80 tries looks like, and it is why T13 (paired intervals) is the table to trust: none of them is distinguishable from zero.

**Pre-registered combinations (T6).** The IS rule combined "no entry 11:00" + "skip Monday" and then + sigma floor: IS looks better (IS PF 1.49 / 1.54) but the gain does not carry over: held-out PF 1.42 / 1.38 (base 1.43), net profit -$3.0k / -$5.1k, roll PASS 55.8 / 52.4 vs 60.3 (the bootstrap PASS is slightly higher, 63 / 65 vs 61.5, with BUST 37 / 35 vs 38.5). No evidence of improvement; do not use.

**Random-direction benchmark (T7).** See section 1.2. The real strategy's trade count is lower (451 vs 591) because wrong-side random trades die quickly and re-enter; the benchmark controls entry timing and exits, not trade count.

**Last-half-hour add-on (T8, T9, T13).** Six signal/mode variants; IS pick = "prior close to 15:29 return / continuation" (IS PF 1.14, net +$3.6k) -> held-out PF 0.79, net -$5.9k. Merged with NOISE it raises max drawdown to $3.3-4.2k and lowers PASS (paired dPASS -5.1 plain / -12.7 preset C, dBUST +7.3 / +16.5). The reversal versions are held-out winners
(open-to-15:29 reversal: PF 1.31, +$6.6k; merged with preset C +$4.6k [+$130, +$8.9k], PASS 63.2 / BUST 36.8) but they lost money in-sample (PF 0.81, -$6.0k) - the sign flipped in 2024; choosing them is hindsight, not allowed by the protocol, and there is no mechanism to bet on.

**Exploratory (T14, T15) - post-hoc, written after the held-out tables were visible.** Preset C + skip Monday + sigma floor: held-out 319 trades, win 57.7%, +$35.4/trade, PF 1.62, DD $1,433, net $11,282 (-$326 vs preset C), PASS 75.9 / BUST 18.1 (bootstrap 74.6 / 25.4); paired dPASS +10.1 [-11.0, +32.6], dBUST -18.5 [-44.8, +3.1].
In the older 2019-05..2021-10 period the stream is flat (PF 1.21 vs 1.21, $ per trade 7.4 vs 7.7): the improvement exists only 2021 onward, and DD is lower in every period.

## 5. Combinations that could work (ranked, plain language)

Criteria for the ranking: held-out PASS up / BUST down on all three estimates, drawdown not worse, IS not worse, profit not materially lower, a simple reason, and no result that relies on one lucky window. "Could work" = worth a paper test only; none is proven.

1. **Keep preset C exactly as built (lock 100 pt -> entry +10).** The only change with support in both periods; do not re-tune it (plateau; neighbours are equivalent or worse in IS).
2. **Preset C + minimum band-width floor** (no new entries when the noise-area sigma at the entry bar is below ~0.29% of price, i.e. the narrowest 20% of in-sample days; threshold fixed on IS only). Held-out: DD -25%, BUST 39 -> 17% (roll) / 38.5 -> 32.9% (boot), PASS +5..+16 points, net -9%. Honest caveat: IS-selected, but the removed trades were not worse held-out and thresholds above p20 degrade. Lowest-risk idea of the study; effect size within noise.
3. **Preset C + skip Mondays.** Held-out PF 1.55, PASS 67 / BUST 30, +$566 net with 16% fewer trades, IS also slightly better (PF 1.44 vs 1.38). Caveat: no Monday weakness in 2019-2021; it was found post hoc in session 10 on 21 tests.
4. **Both together (exploratory, post-hoc):** held-out PF 1.62, DD $1,433, PASS ~75 / BUST ~18-25. Looks best but is the most selected: treat as a hypothesis for a forward paper test, not a result.
5. Everything else - N10, N12, VWAP side/slope filter, no-entry-hour filters, trailing locks, other lock numbers, a 15:30 band check, last-half-hour momentum (any variant), the IS-selected combinations - does **not** beat the baseline on held-out data and is not recommended.

**Does anything beat the baseline on held-out data? No - not with statistical confidence.** Preset C beats plain NOISE directionally (P about 0.9); items 2-4 are directionally better than preset C (P about 0.7-0.85 for fewer busts) but their intervals include zero and the selection history (83+ variants, same held-out years) means some of that is luck.
If you want proof, the forward test is the only clean one (paper, 3-6 months), which Lucid's 25K Pro (4 stop-outs of room) can hardly provide - use the NOISE-sharpening ideas only as low-risk paper hypotheses.

## 6. Doubts about data and method

- **Not a fresh, untouched test set.** Held-out 2024-2026 was already used by sessions 9-16 to confirm NOISE and to choose the lock; this study adds another 80+ looks at it. Treat every held-out improvement as optimistic.
- **Few independent windows**: ~6 non-overlapping 120-session eval windows in the held-out years; PASS % differences below ~15 points are noise (T13).
- **Bar-level fills**: next-bar open +/- 1 tick, no queue/latency; stops by bar high/low (stop-first); an unadjusted `.v.0` volume-roll series (roll jumps removed only through the 1.5% gap guard, and the 1% / $250 stop sizes were never re-checked across rolls); no news blackout modelling; session-9 breach rule counts closed trades only (strict column adds worst open loss).
- **Lock convention**: any exit at or below the locked price after the lock triggered ends NOISE for the day (session-15 code); the app only ends the day on a stop exit labelled PROFIT_LOCK. Small difference, same as the committed stream.
- **Not tested**: other account sizes (50K-150K; the session-15 150K result is untouched), funded stage / payouts / 40% consistency, multi-contract sizing, afternoon fade, MES/MGC, AI bias/AI Duo, any interaction with live fills, 2019 (poor year for the base too: PF 0.89, pre-existing in session 9).
- **N10 definition** copied from session-10 `filters_study.py` (scalar 14-day mean move vs the past 500 days' tercile, requires 60 days of history).
