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

