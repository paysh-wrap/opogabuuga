# Session 21 - EOD toggle: realistic account simulator

Scripts: `sim.py`, `run.py`, `report.py`; raw `results.json`; app schema `eval_odds.yaml`. Streams: NOISE R6 (935 tr), fade F0 (non-Monday days without an R6 trade).
Bootstrap: 10-day business-day blocks, 600 paths x up to 400 sessions, seed 7. Kill distance / DLL margin read per plan YAML (Pro 50, Flex+Daily 100/40 as in the files).

## Headline
The two app rules cost a lot, the toggle changes almost nothing. Pro 25K regular goes from 72/28 (closed-trade study) to 50/50 pass/bust; 50K 63/37, 100K 69/23, 150K 71/19 (ALL). Nearly every bust is STUCK, not a kill: the pre-trade room check (q x $250 risk + $40 <= balance - floor - $50) blocks even 1 micro once the cushion is under about $340, and the account can then never recover (balance only moves by trading). Because that check stops entries before a loss can reach the kill line, EOD toggle ON vs OFF differs by 0-1 pt in every cell (kill rarely gets a chance to fire); the toggle matters only if the room check is also relaxed. Fade on in evals is worse than off (Pro 25K 46/54). J (last year) is worse on small accounts (25K 39/61).

## Sanity (mode ON, room check and kill distance off, 400 paths x 500 sessions, session 19 table 2)
- Pro 25K x1 ALL: 73/27 (target 72/28) OK
- Pro 50K x2 ALL: 71/29 (target 70/30) OK
- Pro 50K x1 ALL: 87/8 open 6 (session 19: 90/6) - about 3 pt off, a bit outside the +-2 tolerance (open paths/ pass-check timing differ slightly).

## Tables

**regular, EOD toggle OFF** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 42 / 58 (58) | 43 / 57 (56) | 35 / 65 (64) |
| lucid_flex_100k | 2/b | 66 / 24 (24) | 68 / 21 (21) | 65 / 34 (33) |
| lucid_flex_150k | 3/b | 68 / 20 (20) | 68 / 15 (15) | 72 / 26 (26) |
| lucid_flex_25k | 1 | 42 / 58 (57) | 45 / 54 (54) | 31 / 69 (68) |
| lucid_flex_50k | 2/b | 59 / 40 (40) | 60 / 38 (38) | 47 / 53 (53) |
| lucid_pro_100k | 2/b | 69 / 23 (23) | 69 / 20 (20) | 67 / 32 (32) |
| lucid_pro_150k | 3/b | 71 / 19 (19) | 70 / 14 (14) | 73 / 26 (25) |
| lucid_pro_25k | 1 | 50 / 50 (50) | 53 / 47 (46) | 39 / 61 (60) |
| lucid_pro_50k | 2/b | 63 / 37 (36) | 63 / 36 (36) | 53 / 47 (46) |

**regular, EOD toggle ON** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 42 / 58 (58) | 43 / 57 (57) | 35 / 65 (65) |
| lucid_flex_100k | 2/b | 66 / 24 (24) | 68 / 21 (21) | 65 / 34 (34) |
| lucid_flex_150k | 3/b | 68 / 20 (20) | 68 / 15 (15) | 72 / 26 (26) |
| lucid_flex_25k | 1 | 42 / 58 (58) | 45 / 54 (54) | 31 / 69 (69) |
| lucid_flex_50k | 2/b | 59 / 40 (40) | 60 / 38 (38) | 47 / 53 (53) |
| lucid_pro_100k | 2/b | 69 / 23 (23) | 69 / 20 (20) | 67 / 32 (32) |
| lucid_pro_150k | 3/b | 71 / 19 (19) | 70 / 14 (14) | 73 / 26 (26) |
| lucid_pro_25k | 1 | 50 / 50 (50) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_pro_50k | 2/b | 63 / 37 (37) | 63 / 36 (36) | 53 / 47 (47) |

**suggested, EOD toggle OFF** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 42 / 58 (58) | 43 / 57 (56) | 35 / 65 (64) |
| lucid_flex_100k | 2/b | 66 / 24 (24) | 68 / 21 (21) | 65 / 34 (33) |
| lucid_flex_150k | 3/b | 68 / 20 (20) | 68 / 15 (15) | 72 / 26 (26) |
| lucid_flex_25k | 1 | 42 / 58 (57) | 45 / 54 (54) | 31 / 69 (68) |
| lucid_flex_50k | 1 | 70 / 19 (19) | 71 / 15 (15) | 76 / 22 (22) |
| lucid_pro_100k | 2/b | 69 / 23 (23) | 69 / 20 (20) | 67 / 32 (32) |
| lucid_pro_150k | 3/b | 71 / 19 (19) | 70 / 14 (14) | 73 / 26 (25) |
| lucid_pro_25k | 1 | 50 / 50 (50) | 53 / 47 (46) | 39 / 61 (60) |
| lucid_pro_50k | 1 | 74 / 16 (16) | 74 / 13 (13) | 79 / 20 (20) |

**suggested, EOD toggle ON** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 42 / 58 (58) | 43 / 57 (57) | 35 / 65 (65) |
| lucid_flex_100k | 2/b | 66 / 24 (24) | 68 / 21 (21) | 65 / 34 (34) |
| lucid_flex_150k | 3/b | 68 / 20 (20) | 68 / 15 (15) | 72 / 26 (26) |
| lucid_flex_25k | 1 | 42 / 58 (58) | 45 / 54 (54) | 31 / 69 (69) |
| lucid_flex_50k | 1 | 70 / 19 (19) | 71 / 15 (15) | 76 / 22 (22) |
| lucid_pro_100k | 2/b | 69 / 23 (23) | 69 / 20 (20) | 67 / 32 (32) |
| lucid_pro_150k | 3/b | 71 / 19 (19) | 70 / 14 (14) | 73 / 26 (26) |
| lucid_pro_25k | 1 | 50 / 50 (50) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_pro_50k | 1 | 74 / 16 (16) | 74 / 13 (13) | 79 / 20 (20) |

**high, EOD toggle OFF** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 42 / 58 (58) | 43 / 57 (56) | 35 / 65 (64) |
| lucid_flex_100k | 3/b | 65 / 29 (28) | 63 / 26 (25) | 52 / 47 (46) |
| lucid_flex_150k | 4/b | 68 / 27 (27) | 68 / 22 (22) | 58 / 42 (40) |
| lucid_flex_25k | 1 | 42 / 58 (57) | 45 / 54 (54) | 31 / 69 (68) |
| lucid_flex_50k | 2/b | 59 / 40 (40) | 60 / 38 (38) | 47 / 53 (53) |
| lucid_pro_100k | 3/b | 68 / 26 (26) | 66 / 24 (24) | 58 / 41 (41) |
| lucid_pro_150k | 4/b | 70 / 26 (26) | 70 / 22 (22) | 61 / 39 (39) |
| lucid_pro_25k | 1 | 50 / 50 (50) | 53 / 47 (46) | 39 / 61 (60) |
| lucid_pro_50k | 2/b | 63 / 37 (36) | 63 / 36 (36) | 53 / 47 (46) |

**high, EOD toggle ON** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 42 / 58 (58) | 43 / 57 (57) | 35 / 65 (65) |
| lucid_flex_100k | 3/b | 65 / 29 (29) | 63 / 26 (26) | 52 / 47 (47) |
| lucid_flex_150k | 4/b | 68 / 27 (27) | 68 / 22 (22) | 58 / 42 (42) |
| lucid_flex_25k | 1 | 42 / 58 (58) | 45 / 54 (54) | 31 / 69 (69) |
| lucid_flex_50k | 2/b | 59 / 40 (40) | 60 / 38 (38) | 47 / 53 (53) |
| lucid_pro_100k | 3/b | 68 / 26 (26) | 66 / 24 (24) | 58 / 41 (41) |
| lucid_pro_150k | 4/b | 70 / 26 (26) | 70 / 22 (22) | 61 / 39 (39) |
| lucid_pro_25k | 1 | 50 / 50 (50) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_pro_50k | 2/b | 63 / 37 (37) | 63 / 36 (36) | 53 / 47 (47) |

**regular + fade on in evals, EOD toggle OFF** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 40 / 60 (60) | 36 / 64 (64) | 41 / 59 (59) |
| lucid_flex_100k | 2/b | 66 / 31 (31) | 62 / 34 (34) | 78 / 22 (22) |
| lucid_flex_150k | 3/b | 69 / 27 (27) | 66 / 28 (27) | 84 / 16 (15) |
| lucid_flex_25k | 1 | 40 / 60 (60) | 36 / 63 (63) | 38 / 62 (62) |
| lucid_flex_50k | 2/b | 53 / 46 (46) | 51 / 49 (49) | 56 / 44 (44) |
| lucid_pro_100k | 2/b | 68 / 30 (30) | 64 / 33 (33) | 79 / 21 (21) |
| lucid_pro_150k | 3/b | 71 / 25 (25) | 67 / 27 (26) | 85 / 15 (14) |
| lucid_pro_25k | 1 | 46 / 54 (54) | 44 / 56 (56) | 43 / 57 (56) |
| lucid_pro_50k | 2/b | 56 / 44 (44) | 54 / 46 (46) | 61 / 39 (38) |

**regular + fade on in evals, EOD toggle ON** (pass / bust % ; bust includes stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 40 / 60 (60) | 36 / 64 (64) | 41 / 59 (59) |
| lucid_flex_100k | 2/b | 66 / 31 (31) | 62 / 34 (34) | 78 / 22 (22) |
| lucid_flex_150k | 3/b | 69 / 27 (27) | 66 / 28 (28) | 84 / 16 (16) |
| lucid_flex_25k | 1 | 40 / 60 (60) | 36 / 63 (63) | 38 / 62 (62) |
| lucid_flex_50k | 2/b | 53 / 46 (46) | 51 / 49 (49) | 56 / 44 (44) |
| lucid_pro_100k | 2/b | 68 / 30 (30) | 64 / 33 (33) | 79 / 21 (21) |
| lucid_pro_150k | 3/b | 71 / 25 (25) | 67 / 27 (27) | 85 / 15 (15) |
| lucid_pro_25k | 1 | 46 / 54 (54) | 44 / 56 (56) | 43 / 57 (57) |
| lucid_pro_50k | 2/b | 56 / 44 (44) | 54 / 46 (46) | 61 / 39 (39) |

## Caveats
- DLL is a closed-trade model (loss of the crossing trade capped at -DLL); MAE is per trade, so the touch time inside a trade is approximate and OFF mode assumes the whole MAE can occur before the exit.
- OFF-mode touch: loss = balance - (floor+50), the kill itself counts as bust. News not modelled. J (1 yr, ~121 trades) is small, +-5 pt.
- Fade stream has no `risk` column (assumed $250/micro) and no exit time; it has `mae`, so the MAE check applies to it.
- STUCK = balance-floor-kill distance < risk + margin (no later trade can fit), counted as bust.
- Pass is checked at end of day. Brake cushion = (balance-floor)/MLL before each trade.
