
### 25K C40 - 50 configs, 6 ROBUST, 2 qualify (ROBUST: 5y >= 56.6, judge >= 35.6, pick >= 53.9)

| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| **BASE** | 58.6 | 35.9 | 23.0 | 74 | 117 (12 %) | 58.9 | 38.6 | 19,293 | YES | no |
| *top qualifying by median days* |||||||||||
| N1@100+C1 nobrake | 56.8 | 34.6 | 33.1 | 52 | 103 (9 %) | 63.1 | 48.9 | 20,115 | YES | YES |
| N1@75+C2 brake->1/1 | 61.8 | 29.6 | 33.7 | 56 | 95 (9 %) | 62.5 | 54.6 | 19,328 | YES | YES |
| *fastest overall (any)* |||||||||||
| N2@250+C3 brake->1/1 | 24.6 | 74.6 | 24.5 | 18 | 73 (11 %) | 31.8 | 19.0 | 44,850 | no | no |
| N2@250+C3 brake->1/2 | 24.6 | 74.6 | 24.5 | 18 | 66 (11 %) | 32.0 | 18.9 | 44,850 | no | no |
| N2@100+C3 brake->1/1 | 36.3 | 61.5 | 35.5 | 22 | 65 (2 %) | 48.3 | 27.0 | 42,078 | no | no |

VERDICT: best = N1@100+C1 nobrake  cfg {'stop': 100, 'N': 1, 'nc': 1, 'brake': None, 'cbands': []}

### 25K C50 - 50 configs, 6 ROBUST, 1 qualify (ROBUST: 5y >= 58.9, judge >= 37.6, pick >= 56.6)

| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| **BASE** | 60.9 | 34.3 | 26.0 | 69 | 112 (6 %) | 61.6 | 40.6 | 19,293 | YES | no |
| *top qualifying by median days* |||||||||||
| N1@75+C2 brake->1/1 | 64.4 | 29.6 | 39.0 | 52 | 91 (6 %) | 62.5 | 59.1 | 19,328 | YES | YES |
| *fastest overall (any)* |||||||||||
| N2@250+C3 brake->1/1 | 32.3 | 66.9 | 32.1 | 17 | 50 (3 %) | 37.8 | 28.1 | 44,850 | no | no |
| N2@250+C3 brake->1/2 | 31.8 | 67.4 | 31.5 | 17 | 50 (2 %) | 37.8 | 27.1 | 44,850 | no | no |
| N2@150+C3 brake->1/2 | 33.6 | 65.6 | 33.3 | 18 | 53 (8 %) | 36.2 | 31.6 | 41,482 | no | no |

VERDICT: best = N1@75+C2 brake->1/1  cfg {'stop': 75, 'N': 1, 'nc': 2, 'brake': None, 'cbands': [[0.3333333333333333, 1]]}

### 50K C40 - 90 configs, 0 ROBUST, 0 qualify (ROBUST: 5y >= 66.8, judge >= 52.3, pick >= 68.1)

| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| **BASE** | 68.8 | 21.4 | 19.7 | 92 | 133 (13 %) | 73.1 | 55.3 | 38,586 | YES | no |
| *top ROBUST (none qualifies) by median days* |||||||||||
| *fastest overall (any)* |||||||||||
| N3@250+C2 brake->2/1 | 39.5 | 57.7 | 32.2 | 37 | 100 (10 %) | 42.6 | 37.2 | 62,656 | no | no |
| N3@250+C2 brake->1/1 | 40.5 | 56.0 | 33.0 | 38 | 110 (7 %) | 44.1 | 37.7 | 62,656 | no | no |
| N3@100+C3 brake->2/2 | 49.5 | 46.6 | 38.7 | 39 | 92 (11 %) | 56.5 | 42.0 | 60,345 | no | no |

VERDICT: none

### 50K C50 - 90 configs, 2 ROBUST, 0 qualify (ROBUST: 5y >= 68.0, judge >= 54.4, pick >= 68.1)

| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| **BASE** | 70.0 | 20.5 | 20.8 | 88 | 127 (12 %) | 73.1 | 57.4 | 38,586 | YES | no |
| *top ROBUST (none qualifies) by median days* |||||||||||
| N2@100+C1 brake->1/1 | 68.5 | 24.6 | 26.3 | 70 | 117 (7 %) | 69.5 | 57.4 | 38,382 | YES | no |
| N2@100+C0 brake->1/0 | 73.0 | 19.6 | 21.6 | 80 | 129 (7 %) | 70.4 | 55.2 | 35,251 | YES | no |
| *fastest overall (any)* |||||||||||
| N3@250+C3 brake->2/2 | 50.2 | 48.0 | 39.1 | 35 | 75 (2 %) | 49.0 | 49.1 | 64,503 | no | no |
| N3@250+C3 brake->1/1 | 49.3 | 47.3 | 38.9 | 35 | 83 (6 %) | 51.2 | 47.8 | 64,503 | no | no |
| N3@250+C2 brake->2/1 | 42.7 | 54.8 | 35.9 | 35 | 85 (10 %) | 46.1 | 40.0 | 62,656 | no | no |

VERDICT: none

### 100K C40 - 63 configs, 13 ROBUST, 8 qualify (ROBUST: 5y >= 75.7, judge >= 57.4, pick >= 60.1)

| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| **BASE** | 77.7 | 11.3 | 5.8 | 152 | 185 (11 %) | 65.1 | 60.4 | 38,586 | YES | no |
| *top qualifying by median days* |||||||||||
| N2@250+C3 brake->1/2 | 78.0 | 11.3 | 5.2 | 127 | 166 (11 %) | 64.0 | 60.9 | 44,850 | YES | YES |
| N2@250+C3 brake->1/1 | 79.9 | 9.3 | 5.2 | 130 | 169 (11 %) | 64.0 | 64.3 | 44,850 | YES | YES |
| N2@100+C3 brake->1/2 | 79.1 | 10.8 | 3.0 | 131 | 172 (10 %) | 64.5 | 62.8 | 42,078 | YES | YES |
| N2@100+C3 brake->1/1 | 79.1 | 10.8 | 3.0 | 132 | 172 (10 %) | 64.5 | 62.8 | 42,078 | YES | YES |
| N2@150+C2 brake->1/1 | 79.1 | 12.3 | 4.4 | 136 | 182 (9 %) | 61.2 | 65.0 | 39,635 | YES | YES |
| *fastest overall (any)* |||||||||||
| N4@100+C3 brake->2/2 | 53.0 | 42.8 | 27.2 | 60 | 115 (11 %) | 54.5 | 47.7 | 78,612 | no | no |
| N4@100+C2 brake->2/1 | 54.1 | 38.3 | 25.3 | 64 | 120 (11 %) | 54.8 | 48.1 | 76,765 | no | no |
| N4@150+C3 brake->2/2 | 51.0 | 45.0 | 22.9 | 64 | 116 (14 %) | 59.0 | 42.8 | 77,422 | no | no |

VERDICT: best = N2@250+C3 brake->1/2  cfg {'stop': 250, 'N': 2, 'nc': 3, 'brake': [0.3333333333333333, 1], 'cbands': [[0.3333333333333333, 2]]}

### 100K C50 - 63 configs, 13 ROBUST, 8 qualify (ROBUST: 5y >= 76.9, judge >= 59.6, pick >= 60.1)

| config | pass 5y | stuck | <=60d | median d | exp. days w/ resets (cens) | pick pass | judge pass | profit $ | ROBUST | QUALIFIES |
|---|---|---|---|---|---|---|---|---|---|---|
| **BASE** | 78.9 | 11.3 | 5.8 | 147 | 178 (10 %) | 65.1 | 62.6 | 38,586 | YES | no |
| *top qualifying by median days* |||||||||||
| N2@250+C3 brake->1/2 | 78.2 | 11.3 | 5.4 | 126 | 163 (11 %) | 64.0 | 61.3 | 44,850 | YES | YES |
| N2@100+C3 brake->1/2 | 80.2 | 10.8 | 3.5 | 126 | 167 (9 %) | 64.5 | 64.8 | 42,078 | YES | YES |
| N2@250+C3 brake->1/1 | 80.1 | 9.3 | 5.4 | 128 | 165 (11 %) | 64.0 | 64.7 | 44,850 | YES | YES |
| N2@100+C3 brake->1/1 | 80.2 | 10.8 | 3.5 | 129 | 169 (9 %) | 64.5 | 64.8 | 42,078 | YES | YES |
| N2@100+C2 brake->1/1 | 79.1 | 11.7 | 3.1 | 132 | 173 (9 %) | 64.7 | 63.1 | 40,230 | YES | YES |
| *fastest overall (any)* |||||||||||
| N4@250+C3 brake->2/2 | 50.9 | 45.3 | 26.5 | 59 | 113 (12 %) | 59.4 | 42.3 | 84,156 | no | no |
| N4@100+C3 brake->2/2 | 54.6 | 41.5 | 28.0 | 60 | 114 (9 %) | 54.5 | 50.6 | 78,612 | no | no |
| N4@250+C2 brake->2/1 | 50.2 | 45.8 | 25.4 | 60 | 120 (13 %) | 59.2 | 41.3 | 82,309 | no | no |

VERDICT: best = N2@250+C3 brake->1/2  cfg {'stop': 250, 'N': 2, 'nc': 3, 'brake': [0.3333333333333333, 1], 'cbands': [[0.3333333333333333, 2]]}
