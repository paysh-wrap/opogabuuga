# Session 21 - EOD toggle: realistic account simulator (incl. D57 stop shrink)

Scripts: `sim2.py`, `run2.py`, `report2.py` (new, with shrink); `sim.py`, `run.py`, `report.py` (previous, no shrink). Raw `results.json` (new), `results_noshrink.json`.
Stream: session 20 `streams_BASE.csv` (2021-10-22..2026-10-30, 654 tr), entry price = MNQ open[ek] from days12.pkl. Eras ALL 2021-10-21..2026-10-30, IS ..2025-11-05, J 2025-11-06..2026-10-30. Bootstrap = session-20 protocol (`lib.eval_boot`: 10-day blocks, uniform start, 600 paths x 400 sessions, seed 7). Kill distance/margin per plan YAML.
D57 shrink: allowed = 0.6 x room0; if q x risk > allowed, stop shrinks to per_ticks (min 0.2 % of entry, else skip); trade loses S' if mae >= S' else original pnl; then worst-case check and the mode's kill rule.

## Headline
gmin (stuck test) = D57 min stop at today's level: 0.2 % x mean J-era MNQ entry = $112 per micro, used for every era; an account is STUCK when 0.6 x (balance - floor - kill) < $112, also at the end of an OPEN path. Regular, ALL pass/bust/open: Pro 25K 60/40/0, 50K 66/34/0, 100K 78/18/4, 150K 79/14/7; Daily 25K 54/46/0. J: 25K 40/60, 50K 57/43, 100K 68/30/1, 150K 71/6/23. EOD ON = OFF in every cell; all bust is STUCK.

## Sanity (mode ON, room/kill/shrink off): Pro 25K IS 72/28 (session 20: 72/28), J 68/32 (68/32): exact match.
(Note: my first-run block sampler differed from session 20's and gave 79/21 on IS; adopted session 20's.)

## Tables (with D57 shrink)

**regular table (with D57 shrink)**


EOD toggle OFF (pass / bust %; bust incl. stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 (46) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_flex_100k | 2 | 76 / 20 (20) | 77 / 16 (16) | 67 / 32 (32) |
| lucid_flex_150k | 3 | 78 / 15 (15) | 77 / 14 (14) | 70 / 7 (7) |
| lucid_flex_25k | 1 | 53 / 47 (47) | 54 / 46 (46) | 34 / 66 (66) |
| lucid_flex_50k | 2 | 62 / 38 (38) | 68 / 32 (32) | 49 / 51 (51) |
| lucid_pro_100k | 2 | 78 / 18 (18) | 79 / 15 (15) | 68 / 30 (30) |
| lucid_pro_150k | 3 | 79 / 14 (14) | 79 / 14 (14) | 71 / 6 (6) |
| lucid_pro_25k | 1 | 60 / 40 (40) | 61 / 39 (39) | 40 / 60 (60) |
| lucid_pro_50k | 2 | 66 / 34 (34) | 70 / 30 (30) | 57 / 43 (43) |

EOD toggle ON (pass / bust %; bust incl. stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 (46) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_flex_100k | 2 | 76 / 20 (20) | 77 / 16 (16) | 67 / 32 (32) |
| lucid_flex_150k | 3 | 78 / 15 (15) | 77 / 14 (14) | 70 / 7 (7) |
| lucid_flex_25k | 1 | 53 / 47 (47) | 54 / 46 (46) | 34 / 66 (66) |
| lucid_flex_50k | 2 | 62 / 38 (38) | 68 / 32 (32) | 49 / 51 (51) |
| lucid_pro_100k | 2 | 78 / 18 (18) | 79 / 15 (15) | 68 / 30 (30) |
| lucid_pro_150k | 3 | 79 / 14 (14) | 79 / 14 (14) | 71 / 6 (6) |
| lucid_pro_25k | 1 | 60 / 40 (40) | 61 / 39 (39) | 40 / 60 (60) |
| lucid_pro_50k | 2 | 66 / 34 (34) | 70 / 30 (30) | 57 / 43 (43) |

**suggested table (with D57 shrink)**


EOD toggle OFF (pass / bust %; bust incl. stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 (46) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_flex_100k | 2 | 76 / 20 (20) | 77 / 16 (16) | 67 / 32 (32) |
| lucid_flex_150k | 3 | 78 / 15 (15) | 77 / 14 (14) | 70 / 7 (7) |
| lucid_flex_25k | 1 | 53 / 47 (47) | 54 / 46 (46) | 34 / 66 (66) |
| lucid_flex_50k | 2 | 82 / 13 (13) | 82 / 12 (12) | 78 / 21 (21) |
| lucid_pro_100k | 2 | 78 / 18 (18) | 79 / 15 (15) | 68 / 30 (30) |
| lucid_pro_150k | 3 | 79 / 14 (14) | 79 / 14 (14) | 71 / 6 (6) |
| lucid_pro_25k | 1 | 60 / 40 (40) | 61 / 39 (39) | 40 / 60 (60) |
| lucid_pro_50k | 2 | 85 / 11 (11) | 84 / 10 (10) | 79 / 20 (20) |

EOD toggle ON (pass / bust %; bust incl. stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 (46) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_flex_100k | 2 | 76 / 20 (20) | 77 / 16 (16) | 67 / 32 (32) |
| lucid_flex_150k | 3 | 78 / 15 (15) | 77 / 14 (14) | 70 / 7 (7) |
| lucid_flex_25k | 1 | 53 / 47 (47) | 54 / 46 (46) | 34 / 66 (66) |
| lucid_flex_50k | 2 | 82 / 13 (13) | 82 / 12 (12) | 78 / 21 (21) |
| lucid_pro_100k | 2 | 78 / 18 (18) | 79 / 15 (15) | 68 / 30 (30) |
| lucid_pro_150k | 3 | 79 / 14 (14) | 79 / 14 (14) | 71 / 6 (6) |
| lucid_pro_25k | 1 | 60 / 40 (40) | 61 / 39 (39) | 40 / 60 (60) |
| lucid_pro_50k | 2 | 85 / 11 (11) | 84 / 10 (10) | 79 / 20 (20) |

**high table (with D57 shrink)**


EOD toggle OFF (pass / bust %; bust incl. stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 (46) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_flex_100k | 2 | 68 / 29 (29) | 70 / 24 (24) | 54 / 46 (46) |
| lucid_flex_150k | 3 | 70 / 27 (27) | 74 / 24 (24) | 56 / 13 (13) |
| lucid_flex_25k | 1 | 53 / 47 (47) | 54 / 46 (46) | 34 / 66 (66) |
| lucid_flex_50k | 2 | 62 / 38 (38) | 68 / 32 (32) | 49 / 51 (51) |
| lucid_pro_100k | 2 | 71 / 26 (26) | 72 / 22 (22) | 61 / 38 (38) |
| lucid_pro_150k | 3 | 72 / 25 (25) | 76 / 22 (22) | 60 / 12 (12) |
| lucid_pro_25k | 1 | 60 / 40 (40) | 61 / 39 (39) | 40 / 60 (60) |
| lucid_pro_50k | 2 | 66 / 34 (34) | 70 / 30 (30) | 57 / 43 (43) |

EOD toggle ON (pass / bust %; bust incl. stuck; stuck in brackets)

| plan | c | ALL | IS | J |
|---|---|---|---|---|
| lucid_daily_25k | 1 | 54 / 46 (46) | 53 / 47 (47) | 39 / 61 (61) |
| lucid_flex_100k | 2 | 68 / 29 (29) | 70 / 24 (24) | 54 / 46 (46) |
| lucid_flex_150k | 3 | 70 / 27 (27) | 74 / 24 (24) | 56 / 13 (13) |
| lucid_flex_25k | 1 | 53 / 47 (47) | 54 / 46 (46) | 34 / 66 (66) |
| lucid_flex_50k | 2 | 62 / 38 (38) | 68 / 32 (32) | 49 / 51 (51) |
| lucid_pro_100k | 2 | 71 / 26 (26) | 72 / 22 (22) | 61 / 38 (38) |
| lucid_pro_150k | 3 | 72 / 25 (25) | 76 / 22 (22) | 60 / 12 (12) |
| lucid_pro_25k | 1 | 60 / 40 (40) | 61 / 39 (39) | 40 / 60 (60) |
| lucid_pro_50k | 2 | 66 / 34 (34) | 70 / 30 (30) | 57 / 43 (43) |

## Fade-on rows: not rebuilt with shrink
Kept from the previous run, labelled WITHOUT D57 shrink (2019-05..2026-11 stream); see the section below. In eval_odds.yaml `regular_fade_on` carries those values.

## Caveats
Closed-trade DLL model; MAE is per trade (touch time approximate); news not modelled; J small (118 trades, +-5 pt). STUCK = shrunk stop under 0.2 % of price for every later trade (or balance within kill distance of floor).

# Without D57 shrink (previous run, 2019-05..2026-11 stream)


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
