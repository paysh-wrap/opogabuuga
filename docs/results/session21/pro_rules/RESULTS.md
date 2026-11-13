# Session 21 - Pro rules (new Lucid rules) realistic account simulator

Scripts: `sim.py` (plans), `sim2.py` (sim), `run2.py`, `report2.py`; raw `results.json`, output `eval_odds.yaml`. Copied from `../eod_toggle/`.
Stream/eras/bootstrap/kill/room check/brake/D57 shrink (0.6, min stop 0.2 %, STUCK when 0.6 x room < $112): unchanged from eod_toggle.

## Changes vs eod_toggle
1. Pro EVAL consistency 40 % (best day <= 40 % of profit at pass check); min profitable days unchanged (1).
2. Pro 25K DLL 600 (50K 1200 / 100K 1800 / 150K 2700). Pro values read from the final YAMLs (asserted in `sim.py`).
3. LucidScale (Pro): once the MLL has locked, DLL = 60 % x (peak EOD balance - start balance), peak keeps rising.
4. App consistency day stop for every plan with an EVAL consistency % (Pro, Flex, Daily): day_stop = (cons - buffer 2 = 38 %) x target ($475 on 25K, 1,140 on 50K, 2,280 on 100K, 3,420 on 150K; buffer from the YAMLs, was 5 = 35 % in the previous run); a trade that would push today above it is capped to today = day_stop and no more trades that day. (40 % entry cap not applied.)
5. Fade-on rows rebuilt with D57 shrink: session-19 `streams_fade_F0.csv` limited to 2021-10-21..2026-10-30 (0 fade trades after removing Mondays and NOISE days), entry = MNQ open[ek], risk $250/micro.

## Headline: regular table, EOD toggle OFF, session-21 eod_toggle (before) -> 35 % day stop (previous run, results_35.json; note: that run's day-stop was 35 %) -> 38 % day stop (this run); pass / bust / open % (median days to pass)

| plan | c | ALL before | ALL 35 % | ALL 38 % | J before | J 35 % | J 38 % |
|---|---|---|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 / 0 (63d) | 51 / 49 / 0 (56d) | 52 / 48 / 0 (54d) | 39 / 61 / 0 (53d) | 34 / 66 / 0 (38d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 2 | 76 / 20 / 5 (168d) | 76 / 20 / 4 (163d) | 76 / 20 / 4 (162d) | 67 / 32 / 1 (126d) | 67 / 32 / 1 (125d) | 67 / 32 / 1 (123d) |
| lucid_flex_150k | 3 | 78 / 15 / 7 (174d) | 77 / 16 / 7 (172d) | 78 / 16 / 7 (169d) | 70 / 7 / 23 (132d) | 70 / 7 / 23 (132d) | 70 / 8 / 23 (128d) |
| lucid_flex_25k | 1 | 53 / 47 / 0 (62d) | 50 / 50 / 0 (54d) | 51 / 49 / 0 (52d) | 34 / 66 / 0 (51d) | 30 / 70 / 0 (36d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 2 | 62 / 38 / 0 (83d) | 60 / 40 / 0 (76d) | 61 / 39 / 0 (74d) | 49 / 51 / 0 (67d) | 47 / 53 / 0 (56d) | 48 / 52 / 0 (55d) |
| lucid_pro_100k | 2 | 78 / 18 / 4 (158d) | 77 / 18 / 4 (164d) | 77 / 18 / 4 (162d) | 68 / 30 / 1 (119d) | 68 / 31 / 1 (125d) | 68 / 31 / 1 (124d) |
| lucid_pro_150k | 3 | 79 / 14 / 7 (166d) | 78 / 14 / 8 (172d) | 78 / 14 / 7 (170d) | 71 / 6 / 23 (126d) | 71 / 6 / 23 (132d) | 71 / 6 / 23 (130d) |
| lucid_pro_25k | 1 | 60 / 40 / 0 (48d) | 56 / 44 / 0 (58d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (32d) | 38 / 62 / 0 (40d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 2 | 66 / 34 / 0 (72d) | 65 / 35 / 0 (78d) | 65 / 34 / 0 (78d) | 57 / 43 / 0 (49d) | 52 / 48 / 0 (56d) | 52 / 48 / 0 (55d) |

**regular** (pass / bust / open %, median days to pass; bust incl. stuck)


EOD toggle OFF

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 / 0 (54d) | 52 / 48 / 0 (53d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 2 | 76 / 20 / 4 (162d) | 78 / 17 / 5 (175d) | 67 / 32 / 1 (123d) |
| lucid_flex_150k | 3 | 78 / 16 / 7 (169d) | 78 / 15 / 7 (176d) | 70 / 8 / 23 (128d) |
| lucid_flex_25k | 1 | 51 / 49 / 0 (52d) | 52 / 48 / 0 (53d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 2 | 61 / 39 / 0 (74d) | 66 / 34 / 0 (79d) | 48 / 52 / 0 (55d) |
| lucid_pro_100k | 2 | 77 / 18 / 4 (162d) | 79 / 16 / 6 (175d) | 68 / 31 / 1 (124d) |
| lucid_pro_150k | 3 | 78 / 14 / 7 (170d) | 79 / 14 / 7 (177d) | 71 / 6 / 23 (130d) |
| lucid_pro_25k | 1 | 57 / 43 / 0 (56d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 2 | 65 / 34 / 0 (78d) | 66 / 33 / 0 (80d) | 52 / 48 / 0 (55d) |

EOD toggle ON

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 / 0 (54d) | 52 / 48 / 0 (53d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 2 | 76 / 20 / 4 (162d) | 78 / 17 / 5 (175d) | 67 / 32 / 1 (123d) |
| lucid_flex_150k | 3 | 78 / 16 / 7 (169d) | 78 / 15 / 7 (176d) | 70 / 8 / 23 (128d) |
| lucid_flex_25k | 1 | 51 / 49 / 0 (52d) | 52 / 48 / 0 (53d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 2 | 61 / 39 / 0 (74d) | 66 / 34 / 0 (79d) | 48 / 52 / 0 (55d) |
| lucid_pro_100k | 2 | 77 / 18 / 4 (162d) | 79 / 16 / 6 (175d) | 68 / 31 / 1 (124d) |
| lucid_pro_150k | 3 | 78 / 14 / 7 (170d) | 79 / 14 / 7 (177d) | 71 / 6 / 23 (130d) |
| lucid_pro_25k | 1 | 57 / 43 / 0 (56d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 2 | 65 / 34 / 0 (78d) | 66 / 33 / 0 (80d) | 52 / 48 / 0 (55d) |
**suggested** (pass / bust / open %, median days to pass; bust incl. stuck)


EOD toggle OFF

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 / 0 (54d) | 52 / 48 / 0 (53d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 2 | 76 / 20 / 4 (162d) | 78 / 17 / 5 (175d) | 67 / 32 / 1 (123d) |
| lucid_flex_150k | 3 | 78 / 16 / 7 (169d) | 78 / 15 / 7 (176d) | 70 / 8 / 23 (128d) |
| lucid_flex_25k | 1 | 51 / 49 / 0 (52d) | 52 / 48 / 0 (53d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 1 | 83 / 13 / 4 (167d) | 83 / 12 / 5 (176d) | 77 / 22 / 1 (130d) |
| lucid_pro_100k | 2 | 77 / 18 / 4 (162d) | 79 / 16 / 6 (175d) | 68 / 31 / 1 (124d) |
| lucid_pro_150k | 3 | 78 / 14 / 7 (170d) | 79 / 14 / 7 (177d) | 71 / 6 / 23 (130d) |
| lucid_pro_25k | 1 | 57 / 43 / 0 (56d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 1 | 84 / 11 / 5 (170d) | 84 / 10 / 6 (177d) | 78 / 20 / 1 (132d) |

EOD toggle ON

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 / 0 (54d) | 52 / 48 / 0 (53d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 2 | 76 / 20 / 4 (162d) | 78 / 17 / 5 (175d) | 67 / 32 / 1 (123d) |
| lucid_flex_150k | 3 | 78 / 16 / 7 (169d) | 78 / 15 / 7 (176d) | 70 / 8 / 23 (128d) |
| lucid_flex_25k | 1 | 51 / 49 / 0 (52d) | 52 / 48 / 0 (53d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 1 | 83 / 13 / 4 (167d) | 83 / 12 / 5 (176d) | 77 / 22 / 1 (130d) |
| lucid_pro_100k | 2 | 77 / 18 / 4 (162d) | 79 / 16 / 6 (175d) | 68 / 31 / 1 (124d) |
| lucid_pro_150k | 3 | 78 / 14 / 7 (170d) | 79 / 14 / 7 (177d) | 71 / 6 / 23 (130d) |
| lucid_pro_25k | 1 | 57 / 43 / 0 (56d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 1 | 84 / 11 / 5 (170d) | 84 / 10 / 6 (177d) | 78 / 20 / 1 (132d) |
**high** (pass / bust / open %, median days to pass; bust incl. stuck)


EOD toggle OFF

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 / 0 (54d) | 52 / 48 / 0 (53d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 3 | 68 / 29 / 3 (109d) | 70 / 24 / 6 (118d) | 53 / 47 / 0 (86d) |
| lucid_flex_150k | 4 | 70 / 27 / 2 (115d) | 74 / 24 / 2 (127d) | 56 / 14 / 31 (89d) |
| lucid_flex_25k | 1 | 51 / 49 / 0 (52d) | 52 / 48 / 0 (53d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 2 | 61 / 39 / 0 (74d) | 66 / 34 / 0 (79d) | 48 / 52 / 0 (55d) |
| lucid_pro_100k | 3 | 70 / 26 / 4 (111d) | 72 / 23 / 5 (119d) | 58 / 41 / 1 (86d) |
| lucid_pro_150k | 4 | 72 / 25 / 3 (116d) | 75 / 23 / 2 (128d) | 59 / 13 / 28 (90d) |
| lucid_pro_25k | 1 | 57 / 43 / 0 (56d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 2 | 65 / 34 / 0 (78d) | 66 / 33 / 0 (80d) | 52 / 48 / 0 (55d) |

EOD toggle ON

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 52 / 48 / 0 (54d) | 52 / 48 / 0 (53d) | 37 / 63 / 0 (38d) |
| lucid_flex_100k | 3 | 68 / 29 / 3 (109d) | 70 / 24 / 6 (118d) | 53 / 47 / 0 (86d) |
| lucid_flex_150k | 4 | 70 / 27 / 2 (115d) | 74 / 24 / 2 (127d) | 56 / 14 / 31 (89d) |
| lucid_flex_25k | 1 | 51 / 49 / 0 (52d) | 52 / 48 / 0 (53d) | 32 / 68 / 0 (35d) |
| lucid_flex_50k | 2 | 61 / 39 / 0 (74d) | 66 / 34 / 0 (79d) | 48 / 52 / 0 (55d) |
| lucid_pro_100k | 3 | 70 / 26 / 4 (111d) | 72 / 23 / 5 (119d) | 58 / 41 / 1 (86d) |
| lucid_pro_150k | 4 | 72 / 25 / 3 (116d) | 75 / 23 / 2 (128d) | 59 / 13 / 28 (90d) |
| lucid_pro_25k | 1 | 57 / 43 / 0 (56d) | 57 / 43 / 0 (56d) | 40 / 60 / 0 (40d) |
| lucid_pro_50k | 2 | 65 / 34 / 0 (78d) | 66 / 33 / 0 (80d) | 52 / 48 / 0 (55d) |
**regular + fade on (D57 shrink)** (pass / bust / open %, median days to pass; bust incl. stuck)


EOD toggle OFF

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 45 / 55 / 0 (35d) | 49 / 51 / 0 (39d) | 46 / 54 / 0 (27d) |
| lucid_flex_100k | 2 | 74 / 25 / 0 (125d) | 74 / 25 / 1 (135d) | 79 / 21 / 0 (92d) |
| lucid_flex_150k | 3 | 76 / 22 / 1 (131d) | 76 / 23 / 1 (138d) | 81 / 6 / 14 (95d) |
| lucid_flex_25k | 1 | 44 / 56 / 0 (33d) | 50 / 50 / 0 (38d) | 42 / 58 / 0 (27d) |
| lucid_flex_50k | 2 | 58 / 42 / 0 (52d) | 58 / 42 / 0 (54d) | 56 / 44 / 0 (38d) |
| lucid_pro_100k | 2 | 75 / 24 / 1 (125d) | 77 / 22 / 1 (138d) | 81 / 19 / 0 (93d) |
| lucid_pro_150k | 3 | 77 / 22 / 1 (132d) | 77 / 22 / 1 (138d) | 82 / 6 / 12 (95d) |
| lucid_pro_25k | 1 | 50 / 50 / 0 (37d) | 53 / 47 / 0 (40d) | 49 / 51 / 0 (28d) |
| lucid_pro_50k | 2 | 61 / 39 / 0 (54d) | 60 / 40 / 0 (57d) | 61 / 39 / 0 (38d) |

EOD toggle ON

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 45 / 55 / 0 (35d) | 49 / 51 / 0 (39d) | 46 / 54 / 0 (27d) |
| lucid_flex_100k | 2 | 74 / 25 / 0 (125d) | 74 / 25 / 1 (135d) | 79 / 21 / 0 (92d) |
| lucid_flex_150k | 3 | 76 / 22 / 1 (131d) | 76 / 23 / 1 (138d) | 81 / 6 / 14 (95d) |
| lucid_flex_25k | 1 | 44 / 56 / 0 (33d) | 50 / 50 / 0 (38d) | 42 / 58 / 0 (27d) |
| lucid_flex_50k | 2 | 58 / 42 / 0 (52d) | 58 / 42 / 0 (54d) | 56 / 44 / 0 (38d) |
| lucid_pro_100k | 2 | 75 / 24 / 1 (125d) | 77 / 22 / 1 (138d) | 81 / 19 / 0 (93d) |
| lucid_pro_150k | 3 | 77 / 22 / 1 (132d) | 77 / 22 / 1 (138d) | 82 / 6 / 12 (95d) |
| lucid_pro_25k | 1 | 50 / 50 / 0 (37d) | 53 / 47 / 0 (40d) | 49 / 51 / 0 (28d) |
| lucid_pro_50k | 2 | 61 / 39 / 0 (54d) | 60 / 40 / 0 (57d) | 61 / 39 / 0 (38d) |

## What changed most and why
- (Numbers in this list are from the 35 % run; see the headline table for 38 %.) Pro 25K: ALL 60/40 -> 56/44, J 40/60 -> 38/62, median days 48 -> 58 (ALL). Pro 50K: J 57/43 -> 52/48. Pro 100K/150K barely move (1-5 pts, days +6): their day-stop level ($2,100 / $3,150) and the 40 % cap almost never bind at 2-3 micros.
- Consistency day stop (all plans with an eval consistency %): caps a winning day at $475 on 25K (1,140 on 50K; previously 437.50 / 1,050). Biggest effect on 25K/50K where one NOISE winner (max $1,672 per micro) is a large part of the $1,250/$2,500 target: wins are truncated, so passes take longer and the bootstrap path gets fewer big days. Flex/Daily 25K lose 3-4 pts pass (53 -> 50 ALL, 34 -> 30 J) and Flex 50K 62 -> 60 (J 49 -> 47). It also removes the consistency-fail path at the pass check (best day <= 38 % target <= 40 % of profit once the target is reached).
- Pro eval consistency 40 %: after the day stop it is nearly never binding; it mainly forces more profitable days.
- Pro 25K DLL 600 (was none): closed-trade DLL, 1 micro, rarely binds (stops are <= $250) so small effect.
- LucidScale: only after the MLL lock (peak EOD >= lock trigger); only matters if a later day loses more than 60 % of peak profit; negligible before the pass.
- Fade-on rows rebuilt with D57 shrink (389 fade trades, non-Monday days without NOISE).
- A first run of this study produced garbage (flex 150K 78 -> 16 pass) because another agent was mid-edit on config/rules (plans read at run time); rerun with unchanged Flex/Daily YAMLs gave the numbers here. YAML md5s used: `yaml_md5.txt`.

## Caveats
Closed-trade DLL/day-stop model (running-trade intraday touch not modelled; capped pnl is an approximation); MAE per trade; news not modelled; J era small (118 trades, about +-5 pts); fade stream uses an assumed $250 risk per micro; LucidScale only simulated in the EVAL window (funded not simulated).
