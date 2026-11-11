
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
