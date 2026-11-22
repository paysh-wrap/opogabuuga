
### 25K · DLL ON · objective A maximise <=60d

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N1@$75 nb[-] + C2 cb[<333:1] | 61.8 | 29.6 | **33.7** | 56 | 54.6 | 62.5 | 19,328 |
| #1 N1@$75 nb[-] + C2 cb[<500:1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #2 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #3 N1@$75 nb[-] + C2 cb[<500:1] dlock0.7 lock80 | 61.9 | 29.3 | **35.9** | 54 | 55.2 | 61.4 | 19,540 |
| #4 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.7 lock80 | 61.9 | 29.3 | **35.9** | 54 | 55.2 | 61.4 | 19,540 |
| #5 N1@$75 nb[-] + C2 cb[<333:1] lock80 | 61.8 | 29.4 | **35.5** | 55 | 55.0 | 61.4 | 19,540 |

### 25K · DLL ON · objective B maximise 5y pass (more micros)

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N1@$75 nb[-] + C2 cb[<333:1] | 61.8 | 29.6 | **33.7** | 56 | 54.6 | 62.5 | 19,328 |
| #1 N1@$75 nb[-] + C2 cb[<500:1] lock80 | 62.2 | 29.4 | **35.2** | 56 | 55.7 | 61.4 | 19,540 |
| #2 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] lock80 | 62.2 | 29.4 | **35.2** | 56 | 55.7 | 61.4 | 19,540 |
| #3 N1@$75 nb[-] + C2 cb[<500:1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #4 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #5 N1@$75 nb[-] + C2 cb[<500:1] dlock0.7 lock80 | 61.9 | 29.3 | **35.9** | 54 | 55.2 | 61.4 | 19,540 |

Pass-vs-micros curve (25K, DLL ON): best 5y pass per NOISE micros N (any config / best config that is also acceptable)

| N | best pass any | its <=60d | its stuck | its profit | best acceptable pass |
|---|---|---|---|---|---|
| 1 | 63.3 | 23.0 | 28.8 | 15,266 | 62.2 |
| 2 | 42.9 | 37.2 | 54.1 | 40,230 | none |
| 3 | 27.5 | 24.1 | 70.2 | 39,238 | none |
| 4 | 20.0 | 15.0 | 77.4 | 46,776 | none |
| 5 | 14.0 | 10.0 | 83.8 | 61,702 | none |

### 25K · DLL OFF · objective A maximise <=60d

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N1@$75 nb[-] + C2 cb[<333:1] | 61.8 | 29.6 | **33.7** | 56 | 54.6 | 62.5 | 19,328 |
| #1 N1@$75 nb[-] + C2 cb[<500:1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #2 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #3 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.7 lock80 | 61.9 | 29.3 | **35.9** | 54 | 55.2 | 61.4 | 19,540 |
| #4 N1@$75 nb[-] + C2 cb[<500:1] dlock0.7 lock80 | 61.9 | 29.3 | **35.9** | 54 | 55.2 | 61.4 | 19,540 |
| #5 N1@$75 nb[-] + C2 cb[<333:1] lock80 | 61.8 | 29.4 | **35.5** | 55 | 55.0 | 61.4 | 19,540 |

### 25K · DLL OFF · objective B maximise 5y pass (more micros)

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N1@$75 nb[-] + C2 cb[<333:1] | 61.8 | 29.6 | **33.7** | 56 | 54.6 | 62.5 | 19,328 |
| #1 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] lock80 | 62.2 | 29.4 | **35.2** | 56 | 55.7 | 61.4 | 19,540 |
| #2 N1@$75 nb[-] + C2 cb[<500:1] lock80 | 62.2 | 29.4 | **35.2** | 56 | 55.7 | 61.4 | 19,540 |
| #3 N1@$75 nb[-] + C2 cb[<500:1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #4 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.5 lock80 | 61.9 | 29.3 | **36.3** | 54 | 55.2 | 61.4 | 19,540 |
| #5 N1@$75 nb[-] + C2 cb[<500:1] taper[0.25, 1] dlock0.7 lock80 | 61.9 | 29.3 | **35.9** | 54 | 55.2 | 61.4 | 19,540 |

Pass-vs-micros curve (25K, DLL OFF): best 5y pass per NOISE micros N (any config / best config that is also acceptable)

| N | best pass any | its <=60d | its stuck | its profit | best acceptable pass |
|---|---|---|---|---|---|
| 1 | 63.3 | 23.0 | 28.8 | 15,266 | 62.2 |
| 2 | 44.0 | 39.1 | 53.0 | 40,230 | none |
| 3 | 31.3 | 28.6 | 67.9 | 58,498 | none |
| 4 | 20.6 | 19.7 | 78.7 | 66,225 | none |
| 5 | 20.1 | 10.2 | 76.6 | 81,858 | none |

### 150K · DLL ON · objective A maximise <=60d

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N5@$100 nb[<1500:2] + C4 cb[<1500:2] | 74.3 | 17.0 | **20.4** | 86 | 64.5 | 66.7 | 98,728 |
| #1 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.5 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |
| #2 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.7 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |

### 150K · DLL ON · objective B maximise 5y pass (more micros)

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N5@$100 nb[<1500:2] + C4 cb[<1500:2] | 74.3 | 17.0 | **20.4** | 86 | 64.5 | 66.7 | 98,728 |
| #1 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.5 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |
| #2 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.7 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |

Pass-vs-micros curve (150K, DLL ON): best 5y pass per NOISE micros N (any config / best config that is also acceptable)

| N | best pass any | its <=60d | its stuck | its profit | best acceptable pass |
|---|---|---|---|---|---|
| 3 | 89.5 | 2.8 | 0.0 | 62,192 | none |
| 4 | 81.3 | 13.1 | 9.3 | 84,155 | none |
| 5 | 76.0 | 10.8 | 16.0 | 102,422 | 74.7 |
| 6 | 70.3 | 21.6 | 16.3 | 111,452 | none |
| 7 | 67.1 | 29.9 | 22.4 | 131,568 | none |
| 8 | 61.7 | 27.8 | 25.6 | 136,145 | none |
| 10 | 56.0 | 24.7 | 26.9 | 163,715 | none |

### 150K · DLL OFF · objective A maximise <=60d

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N5@$100 nb[<1500:2] + C4 cb[<1500:2] | 74.3 | 17.0 | **20.4** | 86 | 64.5 | 66.7 | 98,728 |
| #1 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.7 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |
| #2 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.5 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |

### 150K · DLL OFF · objective B maximise 5y pass (more micros)

| config | pass 5y | stuck | <=60d | median d | judge | pick | profit $ |
|---|---|---|---|---|---|---|---|
| BASE: N5@$100 nb[<1500:2] + C4 cb[<1500:2] | 74.3 | 17.0 | **20.4** | 86 | 64.5 | 66.7 | 98,728 |
| #1 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.7 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |
| #2 N5@$100 nb[<1500:2] + C4 cb[<1500:2] dlock0.5 | 74.7 | 16.6 | **20.4** | 86 | 65.2 | 66.7 | 98,728 |

Pass-vs-micros curve (150K, DLL OFF): best 5y pass per NOISE micros N (any config / best config that is also acceptable)

| N | best pass any | its <=60d | its stuck | its profit | best acceptable pass |
|---|---|---|---|---|---|
| 3 | 89.5 | 2.8 | 0.0 | 62,192 | none |
| 4 | 81.3 | 13.1 | 9.3 | 84,155 | none |
| 5 | 76.0 | 10.8 | 16.0 | 102,422 | 74.7 |
| 6 | 70.3 | 21.6 | 16.3 | 111,452 | none |
| 7 | 67.1 | 29.9 | 22.4 | 131,568 | none |
| 8 | 61.7 | 27.8 | 25.6 | 136,145 | none |
| 10 | 58.5 | 28.8 | 30.1 | 193,760 | none |