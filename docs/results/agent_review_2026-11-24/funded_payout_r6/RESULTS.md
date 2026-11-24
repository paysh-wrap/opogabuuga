# Funded payout sizing, round 6 (2026-11-24; research only, no app code changed, nothing pushed, nothing adopted)
Sim: fsim.py (reuses harness.py / h4.py fast-pass sim, same streams and pre-trade checks) + run_all.py (pre-registered grid in its header). Data /home/user/days.pkl, rolling start on every day; pick = starts 2021-10..2023-12, judge = 2024-01..2026-10; $2/micro RT in base. Validation: with the eval pass rule my loop reproduces built eval pass exactly (50K 66.3 %, 150K 74.4 %). Full numbers: table6.md, results6.json.

## Funded rules modelled (VERIFY = not confirmed)
Start at account size, EOD MLL + lock, DLL + LucidScale 60 % of peak EOD profit (VERIFY interpretation), kill $50 (kill/stuck counted as lost account), payout cycle: 3 profitable days (VERIFY), cycle profit >= min (VERIFY per plan), largest day <= cap of cycle profit (35 % base, 40 % = cap40 scenario; unknown purchase date => 35 %), amount = min(balance - buffer, first/next cap), net = 90 %, max 5 payouts, payout assumed paid the same evening and trading not blocked while it processes (VERIFY). News (hard breach, VERIFY the 1-min window): no entry from 1 min before to 1 min after, open trade flattened 1 min before; real release calendar of r5 (ISM not included). The $6,000-day live move: yaml says none on Pro (VERIFY); max single day never reached it in any run except as counted in results6.json. Resets/purchase fees not modelled. Payout consistency is never breached by construction (a request is only made when ratio <= cap, asserted in code); the real cost is delay (blocked days column).

## Candidates
a = eval fast-pass sizes (eval day stop 38 % of eval target); b = lowest brake step, no grow (150K also b2 = first step N2/C4); c = regular size_table (NOISE $250 stop, table N, CANDACE floor(MLL/1000)); d30 / d33 = a with funded day stop 30 % / 33 % of the eval target (cycle target proxy, fixed, so not a hard guarantee).

## Expected net payout $ per account, 120 sessions (pick / judge), breach % within 120 d (pick / judge)
| plan | a | b | c | d30 | d33 |
|---|---|---|---|---|---|
| 25K | 927/297, 29/43 | 623/249, 28/42 | 607/490, 36/62 | 860/226, 30/45 | 912/263, 29/44 |
| 50K | 1874/682, 23/36 | 833/225, 2/27 | 1398/929, 9/39 | 1900/487, 23/41 | 1940/563, 23/40 |
| 100K | 1982/1176, 15/20 | 1093/457, 0/13 | 1547/773, 0/22 | 2007/1340, 15/30 | 1982/1266, 15/28 |
| 150K | 2728/1561, 0/0.2 | b 0 (never reaches the buffer), b2 953/333, 0/0 | 1686/1000, 0/19 | 2979/1585, 0/0.2 | 2794/1601, 0/0.2 |
(0 breach on pick = few or no busts in that window; judge 2024-26 is much worse for every plan: regime split again.)
Payouts per account within 120 d (judge): 150K a 0.63, 100K a 0.68, 50K a 0.60 / c 0.66, 25K a 0.50 / c 0.63. Median days to first payout (judge): 150K 55-61, 100K 65, 50K 65-69, 25K 61-84. Max drawdown (payout-adjusted equity) about 1.0x MLL on 25K/50K/100K and 1.1x on 150K for a. DLL hits per account are about 0 in every run. 60-day numbers, DLL, blocked days, half-year spread: table6.md.

## Sensitivity
+$2/micro costs 10-25 % of payout $ for a (150K 1561 -> 1318 judge; 100K 1176 -> 945; 50K 682 -> 626) and raises breach (50K pick 23 -> 32 %). Cap 40 % instead of 35 % adds 10-30 % payout $ (150K a judge 1743, pick 3526), so the unknown purchase date matters: keep 35 % until Lucid's date is known. News rule: 9-10 of about 1,050-1,100 signals blocked and 14-15 cut (about 2 %); payout cost small and mixed (150K judge a 1674 without news vs 1561 with, i.e. about -7 %; pick unchanged within noise; 50K pick actually higher with news). Consistency blocks: 50-80 blocked days per account on 50K-150K plans (a payout was otherwise due but delayed), fewer with d30 (150K 53 vs 64).

## Verdicts
- ADOPT CANDIDATE: none under the preset rule (best on pick AND judge payout $ with no more breach).
- 25K: c wins judge (490 vs 297) but loses pick (607 vs 927) and busts 62 % in judge: split, no adoption. 50K: a wins pick, c wins judge (929 vs 682): split. 100K: d30 beats a on judge (1340 vs 1176) and ties on pick (2007 vs 1982) but judge breach 30 % vs 20 %: fails breach rule.
- 150K: d30 (2979 / 1585) and d33 (2794 / 1601) edge a (2728 / 1561) on both windows with equal breach, and win in the +$2 and cap40 runs too, but the gain is 2-9 % and d30 vs d33 flip between windows, well inside noise. Weak lead only.
- Lowest brake step (b) is safest on busts for 50K/100K but pays 40-70 % less; on 150K it never pays (N1/C1). Regular sizes lose money vs a on pick everywhere and are not safer on judge.
- Honest read: eval fast-pass sizes keep earning on funded accounts in these data (about $1.0-1.6K per 150K account in 120 d judge, $0.7-1.2K on 50K/100K), but the judge window pays roughly half to a third of pick and 20-40 % of 25K/50K/100K accounts are lost within 120 d.

## Recommendation (nothing adopted; user decides)
25K and 50K: funded fast-pass sizes lose 36-43 % of accounts in judge; regular sizes (c) pay more in judge but less in pick: undecided, test with more data. 100K: keep a (breach 20 %); d30 is not worth 10 points more breach. 150K: a with funded day stop 30-33 % of the eval target is the only variant not worse, low-confidence. Do not use the lowest brake step on 150K.
Not run: dynamic day cap tied to cycle profit, late-day leg, multiple accounts, reset/purchase cost, payout processing block, 35 % vs 40 % mix by purchase date.
