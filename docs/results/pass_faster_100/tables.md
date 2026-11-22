
### 25K (NOISE 2 + CANDACE 1), 5 years (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 58.6 | 0.0 | 35.9 | 5.5 | 74 | 122 | 23.0 | 19,293 | 2,096 | 2.6 | 1252 |
| NOISE@$100 alone | 32.9 | 0.0 | 39.6 | 27.5 | 29 | 40 | 30.4 | 35,251 | 3,404 | 3.0 | 1252 |
| A one at a time | 34.0 | 0.0 | 63.2 | 2.8 | 28 | 37 | 33.1 | 38,382 | 3,157 | 4.1 | 1252 |
| B both at once | 34.0 | 0.0 | 63.2 | 2.8 | 28 | 37 | 33.1 | 38,184 | 3,157 | 4.1 | 1252 |

### 25K (NOISE 2 + CANDACE 1), judge 2024-01..2026-10 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 38.6 | 0.0 | 51.6 | 9.8 | 50 | 73 | 23.7 | 10,826 | 2,096 | 2.5 | 705 |
| NOISE@$100 alone | 21.1 | 0.0 | 30.2 | 48.7 | 28 | 37 | 21.1 | 20,453 | 3,404 | 2.9 | 705 |
| A one at a time | 22.8 | 0.0 | 72.2 | 5.0 | 27 | 37 | 22.6 | 22,468 | 3,157 | 3.9 | 705 |
| B both at once | 22.8 | 0.0 | 72.2 | 5.0 | 27 | 37 | 22.6 | 22,268 | 3,157 | 4.0 | 705 |

### 25K (NOISE 2 + CANDACE 1), pick 2021-10..2023-12 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 58.9 | 0.0 | 15.5 | 25.6 | 74 | 103 | 22.1 | 8,468 | 944 | 2.7 | 547 |
| NOISE@$100 alone | 48.1 | 0.0 | 48.8 | 3.1 | 30 | 46 | 42.2 | 14,798 | 2,365 | 3.0 | 547 |
| A one at a time | 48.4 | 0.0 | 48.3 | 3.3 | 28 | 37 | 46.8 | 15,915 | 2,088 | 4.3 | 547 |
| B both at once | 48.4 | 0.0 | 48.3 | 3.3 | 28 | 37 | 46.8 | 15,915 | 2,088 | 4.3 | 547 |

### 25K trades taken / skipped (static fresh-account replay; N = NOISE, C = CANDACE)

| row | window | N sig/taken | C sig/taken | skipped: position open N/C | opposite-dir (hedge) N/C | no room N/C | C resized |
|---|---|---|---|---|---|---|---|
| N100 | ALL | 740/740 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | JUDGE | 413/413 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | PICK | 327/327 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| A | ALL | 740/724 | 304/303 | 16/1 | 0/0 | 0/0 | 0 |
| A | JUDGE | 413/406 | 150/150 | 7/0 | 0/0 | 0/0 | 0 |
| A | PICK | 327/318 | 154/153 | 9/1 | 0/0 | 0/0 | 0 |
| B | ALL | 740/725 | 304/303 | 0/0 | 15/1 | 0/0 | 0 |
| B | JUDGE | 413/407 | 150/150 | 0/0 | 6/0 | 0/0 | 0 |
| B | PICK | 327/318 | 154/153 | 0/0 | 9/1 | 0/0 | 0 |

### 25K verdict cells (pass % higher OR pass<=60 higher; stuck not > BASE+2 pts; profit not lower than BASE)

| variant | window | pass d | <=60 d | stuck d | profit d | cell |
|---|---|---|---|---|---|---|
| N100 | JUDGE | -17.4 | -2.6 | -21.4 | +9,628 | FAIL: pass/speed |
| N100 | ALL | -25.7 | +7.3 | +3.8 | +15,958 | FAIL: stuck |
| A | JUDGE | -15.7 | -1.1 | +20.6 | +11,642 | FAIL: pass/speed, stuck |
| A | ALL | -24.6 | +10.1 | +27.3 | +19,090 | FAIL: stuck |
| B | JUDGE | -15.7 | -1.1 | +20.6 | +11,443 | FAIL: pass/speed, stuck |
| B | ALL | -24.6 | +10.1 | +27.3 | +18,890 | FAIL: stuck |

### 50K (NOISE 2 + CANDACE 1), 5 years (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 68.8 | 0.0 | 21.4 | 9.7 | 92 | 132 | 19.7 | 38,586 | 4,193 | 2.6 | 1252 |
| NOISE@$100 alone | 66.1 | 0.0 | 7.2 | 26.7 | 79 | 142 | 21.2 | 35,251 | 3,404 | 3.0 | 1252 |
| A one at a time | 59.1 | 0.0 | 30.6 | 10.3 | 67 | 107 | 25.5 | 38,382 | 3,157 | 4.1 | 1252 |
| B both at once | 58.6 | 0.0 | 31.1 | 10.3 | 67 | 108 | 25.5 | 38,184 | 3,157 | 4.1 | 1252 |

### 50K (NOISE 2 + CANDACE 1), judge 2024-01..2026-10 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 55.3 | 0.0 | 27.4 | 17.3 | 83 | 123 | 19.0 | 21,651 | 4,193 | 2.5 | 705 |
| NOISE@$100 alone | 48.2 | 0.0 | 4.4 | 47.4 | 67 | 105 | 19.7 | 20,453 | 3,404 | 2.9 | 705 |
| A one at a time | 48.9 | 0.0 | 32.8 | 18.3 | 65 | 95 | 22.4 | 22,468 | 3,157 | 3.9 | 705 |
| B both at once | 48.1 | 0.0 | 33.6 | 18.3 | 64 | 94 | 22.4 | 22,268 | 3,157 | 4.0 | 705 |

### 50K (NOISE 2 + CANDACE 1), pick 2021-10..2023-12 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 73.1 | 0.0 | 0.0 | 26.9 | 86 | 118 | 20.7 | 16,935 | 1,888 | 2.7 | 547 |
| NOISE@$100 alone | 63.6 | 0.0 | 10.8 | 25.6 | 72 | 122 | 23.0 | 14,798 | 2,365 | 3.0 | 547 |
| A one at a time | 62.3 | 0.0 | 18.6 | 19.0 | 63 | 100 | 29.4 | 15,915 | 2,088 | 4.3 | 547 |
| B both at once | 62.3 | 0.0 | 18.6 | 19.0 | 63 | 100 | 29.4 | 15,915 | 2,088 | 4.3 | 547 |

### 50K trades taken / skipped (static fresh-account replay; N = NOISE, C = CANDACE)

| row | window | N sig/taken | C sig/taken | skipped: position open N/C | opposite-dir (hedge) N/C | no room N/C | C resized |
|---|---|---|---|---|---|---|---|
| N100 | ALL | 740/740 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | JUDGE | 413/413 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | PICK | 327/327 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| A | ALL | 740/724 | 304/303 | 16/1 | 0/0 | 0/0 | 0 |
| A | JUDGE | 413/406 | 150/150 | 7/0 | 0/0 | 0/0 | 0 |
| A | PICK | 327/318 | 154/153 | 9/1 | 0/0 | 0/0 | 0 |
| B | ALL | 740/725 | 304/303 | 0/0 | 15/1 | 0/0 | 0 |
| B | JUDGE | 413/407 | 150/150 | 0/0 | 6/0 | 0/0 | 0 |
| B | PICK | 327/318 | 154/153 | 0/0 | 9/1 | 0/0 | 0 |

### 50K verdict cells (pass % higher OR pass<=60 higher; stuck not > BASE+2 pts; profit not lower than BASE)

| variant | window | pass d | <=60 d | stuck d | profit d | cell |
|---|---|---|---|---|---|---|
| N100 | JUDGE | -7.1 | +0.7 | -23.0 | -1,198 | FAIL: profit |
| N100 | ALL | -2.7 | +1.4 | -14.2 | -3,335 | FAIL: profit |
| A | JUDGE | -6.4 | +3.4 | +5.4 | +816 | FAIL: stuck |
| A | ALL | -9.7 | +5.8 | +9.2 | -204 | FAIL: stuck, profit |
| B | JUDGE | -7.2 | +3.4 | +6.2 | +618 | FAIL: stuck |
| B | ALL | -10.2 | +5.8 | +9.7 | -402 | FAIL: stuck, profit |

### 100K (NOISE 4 + CANDACE 2), 5 years (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 77.7 | 0.0 | 11.3 | 10.9 | 152 | 218 | 5.8 | 38,586 | 4,193 | 2.6 | 1252 |
| NOISE@$100 alone | 45.4 | 0.0 | 2.6 | 52.0 | 63 | 83 | 21.2 | 70,502 | 6,808 | 3.0 | 1252 |
| A one at a time | 51.9 | 0.0 | 34.0 | 14.1 | 62 | 92 | 25.5 | 76,765 | 6,314 | 4.1 | 1252 |
| B both at once | 51.4 | 0.0 | 34.5 | 14.1 | 61 | 91 | 25.5 | 76,367 | 6,314 | 4.1 | 1252 |

### 100K (NOISE 4 + CANDACE 2), judge 2024-01..2026-10 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 60.4 | 0.0 | 20.1 | 19.4 | 135 | 188 | 3.8 | 21,651 | 4,193 | 2.5 | 705 |
| NOISE@$100 alone | 34.5 | 0.0 | 0.0 | 65.5 | 56 | 70 | 19.7 | 40,906 | 6,808 | 2.9 | 705 |
| A one at a time | 44.7 | 0.0 | 30.4 | 25.0 | 60 | 90 | 22.4 | 44,935 | 6,314 | 3.9 | 705 |
| B both at once | 43.8 | 0.0 | 31.2 | 25.0 | 59 | 88 | 22.4 | 44,537 | 6,314 | 4.0 | 705 |

### 100K (NOISE 4 + CANDACE 2), pick 2021-10..2023-12 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 65.1 | 0.0 | 0.0 | 34.9 | 137 | 179 | 8.2 | 16,935 | 1,888 | 2.7 | 547 |
| NOISE@$100 alone | 50.1 | 0.0 | 6.0 | 43.9 | 65 | 79 | 23.0 | 29,596 | 4,730 | 3.0 | 547 |
| A one at a time | 56.9 | 0.0 | 19.2 | 23.9 | 60 | 80 | 29.4 | 31,830 | 4,175 | 4.3 | 547 |
| B both at once | 56.9 | 0.0 | 19.2 | 23.9 | 60 | 80 | 29.4 | 31,830 | 4,175 | 4.3 | 547 |

### 100K trades taken / skipped (static fresh-account replay; N = NOISE, C = CANDACE)

| row | window | N sig/taken | C sig/taken | skipped: position open N/C | opposite-dir (hedge) N/C | no room N/C | C resized |
|---|---|---|---|---|---|---|---|
| N100 | ALL | 740/740 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | JUDGE | 413/413 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | PICK | 327/327 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| A | ALL | 740/724 | 304/303 | 16/1 | 0/0 | 0/0 | 0 |
| A | JUDGE | 413/406 | 150/150 | 7/0 | 0/0 | 0/0 | 0 |
| A | PICK | 327/318 | 154/153 | 9/1 | 0/0 | 0/0 | 0 |
| B | ALL | 740/725 | 304/303 | 0/0 | 15/1 | 0/0 | 0 |
| B | JUDGE | 413/407 | 150/150 | 0/0 | 6/0 | 0/0 | 0 |
| B | PICK | 327/318 | 154/153 | 0/0 | 9/1 | 0/0 | 0 |

### 100K verdict cells (pass % higher OR pass<=60 higher; stuck not > BASE+2 pts; profit not lower than BASE)

| variant | window | pass d | <=60 d | stuck d | profit d | cell |
|---|---|---|---|---|---|---|
| N100 | JUDGE | -26.0 | +15.9 | -20.1 | +19,255 | PASS |
| N100 | ALL | -32.3 | +15.4 | -8.7 | +31,916 | PASS |
| A | JUDGE | -15.7 | +18.6 | +10.2 | +23,284 | FAIL: stuck |
| A | ALL | -25.8 | +19.7 | +22.7 | +38,179 | FAIL: stuck |
| B | JUDGE | -16.6 | +18.6 | +11.1 | +22,886 | FAIL: stuck |
| B | ALL | -26.3 | +19.7 | +23.2 | +37,781 | FAIL: stuck |

### 150K (NOISE 4 + CANDACE 2), 5 years (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 77.1 | 0.0 | 10.5 | 12.5 | 159 | 221 | 5.8 | 57,879 | 6,290 | 2.6 | 1252 |
| NOISE@$100 alone | 69.7 | 0.0 | 0.0 | 30.3 | 110 | 169 | 8.0 | 70,502 | 6,808 | 3.0 | 1252 |
| A one at a time | 73.9 | 0.0 | 16.0 | 10.1 | 105 | 163 | 8.9 | 76,765 | 6,314 | 4.1 | 1252 |
| B both at once | 73.5 | 0.0 | 16.4 | 10.1 | 105 | 163 | 8.9 | 76,367 | 6,314 | 4.1 | 1252 |

### 150K (NOISE 4 + CANDACE 2), judge 2024-01..2026-10 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 59.3 | 0.0 | 18.6 | 22.1 | 147 | 201 | 3.8 | 32,476 | 6,290 | 2.5 | 705 |
| NOISE@$100 alone | 46.8 | 0.0 | 0.0 | 53.2 | 90 | 118 | 5.0 | 40,906 | 6,808 | 2.9 | 705 |
| A one at a time | 64.3 | 0.0 | 17.7 | 18.0 | 103 | 144 | 6.7 | 44,935 | 6,314 | 3.9 | 705 |
| B both at once | 63.5 | 0.0 | 18.4 | 18.0 | 104 | 143 | 6.7 | 44,537 | 6,314 | 4.0 | 705 |

### 150K (NOISE 4 + CANDACE 2), pick 2021-10..2023-12 (rolling starts)

| row | pass % | bust % | stuck % | running % | median d | p75 d | pass <=60 d % | plan-sized $ | worst DD $ | trades/wk | n starts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE (shipped) | 65.1 | 0.0 | 0.0 | 34.9 | 138 | 179 | 8.2 | 25,402 | 2,832 | 2.7 | 547 |
| NOISE@$100 alone | 70.2 | 0.0 | 0.0 | 29.8 | 106 | 151 | 11.9 | 29,596 | 4,730 | 3.0 | 547 |
| A one at a time | 69.5 | 0.0 | 0.4 | 30.2 | 96 | 129 | 11.7 | 31,830 | 4,175 | 4.3 | 547 |
| B both at once | 69.5 | 0.0 | 0.4 | 30.2 | 96 | 129 | 11.7 | 31,830 | 4,175 | 4.3 | 547 |

### 150K trades taken / skipped (static fresh-account replay; N = NOISE, C = CANDACE)

| row | window | N sig/taken | C sig/taken | skipped: position open N/C | opposite-dir (hedge) N/C | no room N/C | C resized |
|---|---|---|---|---|---|---|---|
| N100 | ALL | 740/740 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | JUDGE | 413/413 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| N100 | PICK | 327/327 | 0/0 | 0/0 | 0/0 | 0/0 | 0 |
| A | ALL | 740/724 | 304/303 | 16/1 | 0/0 | 0/0 | 0 |
| A | JUDGE | 413/406 | 150/150 | 7/0 | 0/0 | 0/0 | 0 |
| A | PICK | 327/318 | 154/153 | 9/1 | 0/0 | 0/0 | 0 |
| B | ALL | 740/725 | 304/303 | 0/0 | 15/1 | 0/0 | 0 |
| B | JUDGE | 413/407 | 150/150 | 0/0 | 6/0 | 0/0 | 0 |
| B | PICK | 327/318 | 154/153 | 0/0 | 9/1 | 0/0 | 0 |

### 150K verdict cells (pass % higher OR pass<=60 higher; stuck not > BASE+2 pts; profit not lower than BASE)

| variant | window | pass d | <=60 d | stuck d | profit d | cell |
|---|---|---|---|---|---|---|
| N100 | JUDGE | -12.5 | +1.1 | -18.6 | +8,430 | PASS |
| N100 | ALL | -7.3 | +2.2 | -10.5 | +12,623 | PASS |
| A | JUDGE | +5.0 | +2.8 | -0.9 | +12,458 | PASS |
| A | ALL | -3.2 | +3.1 | +5.5 | +18,886 | FAIL: stuck |
| B | JUDGE | +4.3 | +2.8 | -0.1 | +12,060 | PASS |
| B | ALL | -3.6 | +3.1 | +5.9 | +18,488 | FAIL: stuck |

### Verdict summary

| plan | row | judge | 5y |
|---|---|---|---|
| 25K | NOISE@$100 alone | FAIL: pass/speed | FAIL: stuck |
| 25K | A one at a time | FAIL: pass/speed, stuck | FAIL: stuck |
| 25K | B both at once | FAIL: pass/speed, stuck | FAIL: stuck |
| 50K | NOISE@$100 alone | FAIL: profit | FAIL: profit |
| 50K | A one at a time | FAIL: stuck | FAIL: stuck, profit |
| 50K | B both at once | FAIL: stuck | FAIL: stuck, profit |
| 100K | NOISE@$100 alone | PASS | PASS |
| 100K | A one at a time | FAIL: stuck | FAIL: stuck |
| 100K | B both at once | FAIL: stuck | FAIL: stuck |
| 150K | NOISE@$100 alone | PASS | PASS |
| 150K | A one at a time | PASS | FAIL: stuck |
| 150K | B both at once | PASS | FAIL: stuck |

### NOISE stream per micro: $100 stop vs shipped $250 stop (generator-level, no account rules)

| window | stop | trades | win % | PF | net $ per micro |
|---|---|---|---|---|---|
| ALL | $250 | 654 | 51.4 | 1.52 | 19,293 |
| ALL | $100 | 740 | 43.4 | 1.49 | 17,626 |
| PICK | $250 | 298 | 48.0 | 1.55 | 8,468 |
| PICK | $100 | 327 | 43.4 | 1.48 | 7,399 |
| JUDGE | $250 | 356 | 54.2 | 1.49 | 10,826 |
| JUDGE | $100 | 413 | 43.3 | 1.50 | 10,226 |
