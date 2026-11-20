# CANDACE ICT SCALP: "a new sweep no longer throws away the setup in progress" (study only, nothing implemented)

## Plain English

**What was tested.** The engine drops the setup in progress whenever any new pool is swept (candace_ict.py lines 237-243). Three offline variants of that one rule (NY window 09:30-10:00, everything else identical):
- **V1 KEEP_ALL**: every sweep is its own setup, all tracked in parallel.
- **V2 SAME_SIDE**: a new sweep replaces the pending setup only if it is on the same side; the opposite side runs in parallel.
- **V3 PROTECT_FORMED**: a new sweep replaces the pending setup only while it has no valid IFVG yet; once it has one it is kept (new sweeps are ignored until it retraces, times out or fails).

Trade taking: max 1 open position; a signal while a trade is open is skipped (V1: 18 skipped over 5 years); one entry per setup; same-bar ties go to the higher grade, then the earlier sweep (V1: 122 same-bar losers skipped). The baseline engine was reproduced exactly (0 mismatching days of 1,266; 100 trades, IS 53 / J 47), and the new multi-setup code in "engine mode" also matches the engine on all 1,266 days. A no-lookahead replay check (20 days per variant, replay cut at every signal time) found 0 differences.

**Result.**

| | trades IS / J | IS PF | J PF | IS 1-micro $ | J 1-micro $ |
|---|---|---|---|---|---|
| BASE | 53 / 47 | 0.69 | 2.05 | -456 | +1,211 |
| V1 KEEP_ALL | 160 / 150 (3x) | 1.27 | 1.18 | +1,030 | +814 |
| V2 SAME_SIDE | 90 / 79 | 1.00 | 1.28 | -3 | +626 |
| V3 PROTECT_FORMED | 78 / 82 | 0.89 | 1.21 | -224 | +490 |

- **V1 is the only variant that passes the IS filter** (more trades, IS PF 1.27 >= 1.10, IS profit above BASE at 1 micro, 25K fit and 50K fit). **It turns the in-sample period positive** (BASE IS PF 0.69, -$456; V1 +$1,030). V2 and V3 do not (IS PF 1.00 and 0.89); they add trades but fail the PF test.
- **V1 fails the J check, so the verdict is REJECT.** J (2024-01..2026-10): 1-micro +$814 vs BASE +$1,211, 25K fit -$396 vs -$287, 50K fit +$40 vs +$876. Under the binding rule (any profit cut = reject) it cannot be recommended. J PF is still 1.18 and J trades 150 vs 47, so it is not a loser, but the extra trades are weaker (J average $5.4/trade vs $25.8) and BASE's J (47 trades, PF 2.05) looks lucky next to its own IS (PF 0.69).
- V1 with window 10:30 (the only eligible variant, so the only one extended): 408 IS / 390 J trades, IS PF 1.00, IS 1-micro +$36, IS 25K -$580, IS 50K -$1,908. It fails the IS filter against BASE 10:00 and against BASE at 10:30. REJECT, no J pick.
- **Pro 25K vs Pro 50K side by side (V1 vs BASE).** IS 25K fit +$188 vs -$226 (better), IS 50K fit +$762 vs -$994 (better); J 25K fit -$396 vs -$287 (worse), J 50K fit +$40 vs +$876 (worse). So 25K and 50K agree: better in IS, worse in J. No variant passes on 50K but not 25K or the reverse. The 25K plan stays crippled by the grade rule: 116 of V1's 150 J signals size to 0 micros (BASE: 35 of 47); 50K sizes every trade to at least 1.
- Eval pass / bust is 0 / 0 for every row and plan (every start is "still running": even 150 trades in 34 months does not reach the profit target under the 40% consistency rule). So the pass/bust criterion cannot separate anything here; median days to pass is undefined.
- Over all five years V1 would be +$1,844 at 1 micro vs BASE +$755 and 310 vs 100 trades, 6 of 10 chunks positive (BASE also 6 of 10). That is only an observation: the J check, not the 5-year sum, decides, and 2024-26 was seen by earlier sessions.

**Verdict: no variant ACCEPTED. Do not implement.** V1 is worth remembering as the only change that makes IS positive, but it cuts J profit at 1 micro, 25K and 50K.

Caveats: 4 variants tested in total (3 at window 10:00 + V1 at 10:30), on one 5-year sample; 2024-26 was seen by earlier sessions; the IS filter is a screen, not proof. No J row has under 30 trades, so none is "too few to trust" on count, but eval pass/bust is uninformative (0 / 0). Choices that could matter: while a position is open the new variants keep tracking setups and skip signals (BASE instead ignores bars and clears its state); V3 ignored sweeps leave the pool unconsumed; sweeps are detected one per bar (first matching pool) as in the engine.

## If it were to be implemented (not recommended)
V1 in plain words: keep a list of pending setups instead of one; a new sweep adds an entry instead of replacing `sweep, ifvg`; each entry runs the C1 to D3 checks on its own; the first to retrace takes the trade (higher grade first, then earlier sweep) and signals while a position is open are skipped. It would go in `replay_day` in candace_ict.py at lines ~237-243 and the `sweep`/`ifvg` state (lines ~219-220, 252-285).

## Files
- `cks_lib.py` multi-episode mirror (`run_day_v`, policies REPLACE/V1/V2/V3); `cks_stats.py` contracts / days-to-pass extensions of the previous study's sizing and eval sim; `run_cks.py` driver; `tables.md` all tables (A 1-micro, B Lucid-fit, C eval, D Pro 50K/25K block, E 10 chunks, F half-hour win rate, G episode bookkeeping, IS filter, J check).
- Reuses `../candace_trade_more/ctm_lib.py` unchanged.

Full tables follow in `tables.md` (same folder); the key ones are above.
