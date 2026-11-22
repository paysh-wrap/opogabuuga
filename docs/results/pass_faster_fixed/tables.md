
### 25K, 5 years (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 58.6 | 0.0 | 35.9 | 5.5 | 74 | 122 | 23.0 | 19293 | 2096 | 2.6 | 1252 |
| NOISE1 | 58.6 | 0.0 | 35.9 | 5.5 | 74 | 122 | 23.0 | 19293 | 2096 | 2.6 | 1252 |
| C125_1 | 49.5 | 0.0 | 45.3 | 5.2 | 48 | 72 | 31.5 | 21501 | 1967 | 3.8 | 1252 |
| A | 49.5 | 0.0 | 45.3 | 5.2 | 48 | 72 | 31.5 | 21501 | 1967 | 3.8 | 1252 |
| B | 49.4 | 0.0 | 45.4 | 5.2 | 48 | 72 | 31.3 | 21252 | 1967 | 3.8 | 1252 |

### 25K, judge 2024-01..2026-10 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 38.6 | 0.0 | 51.6 | 9.8 | 50 | 73 | 23.7 | 10826 | 2096 | 2.5 | 705 |
| NOISE1 | 38.6 | 0.0 | 51.6 | 9.8 | 50 | 73 | 23.7 | 10826 | 2096 | 2.5 | 705 |
| C125_1 | 40.6 | 0.0 | 50.2 | 9.2 | 47 | 71 | 26.1 | 11788 | 1967 | 3.5 | 705 |
| A | 40.6 | 0.0 | 50.2 | 9.2 | 47 | 71 | 26.1 | 11788 | 1967 | 3.5 | 705 |
| B | 40.3 | 0.0 | 50.5 | 9.2 | 47 | 71 | 25.7 | 11538 | 1967 | 3.5 | 705 |

### 25K, pick 2021-10..2023-12 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 58.9 | 0.0 | 15.5 | 25.6 | 74 | 103 | 22.1 | 8468 | 944 | 2.7 | 547 |
| NOISE1 | 58.9 | 0.0 | 15.5 | 25.6 | 74 | 103 | 22.1 | 8468 | 944 | 2.7 | 547 |
| C125_1 | 57.2 | 0.0 | 30.3 | 12.4 | 47 | 69 | 38.6 | 9714 | 980 | 4.0 | 547 |
| A | 57.2 | 0.0 | 30.3 | 12.4 | 47 | 69 | 38.6 | 9714 | 980 | 4.0 | 547 |
| B | 57.2 | 0.0 | 30.3 | 12.4 | 47 | 69 | 38.6 | 9714 | 980 | 4.0 | 547 |

### 25K trades taken / skipped (static fresh-account replay, plan-sized; N = NOISE, C = CANDACE)

| row | window | N sig/taken | C sig/taken | skipped: position open N/C | hedge N/C | no room N/C | C resized | C stop $ over 125 |
|---|---|---|---|---|---|---|---|---|
| A | ALL | 654/638 | 304/303 | 16/1 | 0/0 | 0/0 | 0 | 0 |
| A | JUDGE | 356/349 | 150/150 | 7/0 | 0/0 | 0/0 | 0 | 0 |
| A | PICK | 298/289 | 154/153 | 9/1 | 0/0 | 0/0 | 0 | 0 |
| B | ALL | 654/639 | 304/303 | 0/0 | 15/1 | 0/0 | 0 | 0 |
| B | JUDGE | 356/350 | 150/150 | 0/0 | 6/0 | 0/0 | 0 | 0 |
| B | PICK | 298/289 | 154/153 | 0/0 | 9/1 | 0/0 | 0 | 0 |

### 25K verdict cells (rule: pass % higher OR pass<=60 higher; stuck(+bust) not higher than BASE by > 2 pts; profit not lower than BASE)

| variant | window | pass d | <=60 d | stuck d | bust+stuck d | profit d | cell |
|---|---|---|---|---|---|---|---|
| NOISE1 | JUDGE | +0.0 | +0.0 | +0.0 | +0.0 | +0 | FAIL: speed/pass |
| NOISE1 | ALL | +0.0 | +0.0 | +0.0 | +0.0 | +0 | FAIL: speed/pass |
| C125_1 | JUDGE | +2.0 | +2.4 | -1.4 | -1.4 | +962 | PASS |
| C125_1 | ALL | -9.1 | +8.5 | +9.4 | +9.4 | +2208 | FAIL: stuck |
| A | JUDGE | +2.0 | +2.4 | -1.4 | -1.4 | +962 | PASS |
| A | ALL | -9.1 | +8.5 | +9.4 | +9.4 | +2208 | FAIL: stuck |
| B | JUDGE | +1.7 | +2.0 | -1.1 | -1.1 | +712 | PASS |
| B | ALL | -9.3 | +8.3 | +9.6 | +9.6 | +1958 | FAIL: stuck |

### 50K, 5 years (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 68.8 | 0.0 | 21.4 | 9.7 | 92 | 132 | 19.7 | 38586 | 4193 | 2.6 | 1252 |
| NOISE1 | 76.1 | 0.0 | 12.9 | 10.9 | 148 | 212 | 5.8 | 19293 | 2096 | 2.6 | 1252 |
| A | 80.7 | 0.0 | 9.7 | 9.6 | 121 | 173 | 5.7 | 23348 | 2087 | 3.8 | 1252 |
| B | 80.0 | 0.0 | 10.4 | 9.6 | 121 | 179 | 5.7 | 23099 | 2087 | 3.8 | 1252 |

### 50K, judge 2024-01..2026-10 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 55.3 | 0.0 | 27.4 | 17.3 | 83 | 123 | 19.0 | 21651 | 4193 | 2.5 | 705 |
| NOISE1 | 57.6 | 0.0 | 23.0 | 19.4 | 131 | 170 | 3.8 | 10826 | 2096 | 2.5 | 705 |
| A | 65.7 | 0.0 | 17.3 | 17.0 | 125 | 150 | 2.8 | 12601 | 2087 | 3.5 | 705 |
| B | 64.5 | 0.0 | 18.4 | 17.0 | 126 | 154 | 2.8 | 12352 | 2087 | 3.5 | 705 |

### 50K, pick 2021-10..2023-12 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 73.1 | 0.0 | 0.0 | 26.9 | 86 | 118 | 20.7 | 16935 | 1888 | 2.7 | 547 |
| NOISE1 | 65.1 | 0.0 | 0.0 | 34.9 | 137 | 179 | 8.2 | 8468 | 944 | 2.7 | 547 |
| A | 64.0 | 0.0 | 0.0 | 36.0 | 93 | 113 | 9.3 | 10748 | 1128 | 4.0 | 547 |
| B | 64.0 | 0.0 | 0.0 | 36.0 | 93 | 113 | 9.3 | 10748 | 1128 | 4.0 | 547 |

### 50K trades taken / skipped (static fresh-account replay, plan-sized; N = NOISE, C = CANDACE)

| row | window | N sig/taken | C sig/taken | skipped: position open N/C | hedge N/C | no room N/C | C resized | C stop $ over 125 |
|---|---|---|---|---|---|---|---|---|
| A | ALL | 654/638 | 304/303 | 16/1 | 0/0 | 0/0 | 0 | 0 |
| A | JUDGE | 356/349 | 150/150 | 7/0 | 0/0 | 0/0 | 0 | 0 |
| A | PICK | 298/289 | 154/153 | 9/1 | 0/0 | 0/0 | 0 | 0 |
| B | ALL | 654/639 | 304/303 | 0/0 | 15/1 | 0/0 | 0 | 0 |
| B | JUDGE | 356/350 | 150/150 | 0/0 | 6/0 | 0/0 | 0 | 0 |
| B | PICK | 298/289 | 154/153 | 0/0 | 9/1 | 0/0 | 0 | 0 |

### 50K verdict cells (rule: pass % higher OR pass<=60 higher; stuck(+bust) not higher than BASE by > 2 pts; profit not lower than BASE)

| variant | window | pass d | <=60 d | stuck d | bust+stuck d | profit d | cell |
|---|---|---|---|---|---|---|---|
| NOISE1 | JUDGE | +2.3 | -15.2 | -4.4 | -4.4 | -10826 | FAIL: profit |
| NOISE1 | ALL | +7.3 | -14.0 | -8.5 | -8.5 | -19293 | FAIL: profit |
| A | JUDGE | +10.4 | -16.2 | -10.1 | -10.1 | -9050 | FAIL: profit |
| A | ALL | +11.8 | -14.1 | -11.7 | -11.7 | -15238 | FAIL: profit |
| B | JUDGE | +9.2 | -16.2 | -8.9 | -8.9 | -9300 | FAIL: profit |
| B | ALL | +11.2 | -14.1 | -11.0 | -11.0 | -15487 | FAIL: profit |
