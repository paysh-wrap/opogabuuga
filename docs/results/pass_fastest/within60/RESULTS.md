# Within-60-days pass study, Pro 25K + Pro 150K EVALUATION (research only, 2026-11-22)

## Plain answer
Reproduced first (DLL ON, C40): 25K current pick pass 61.8 %, within-60 33.7 %, median 56 d, judge 54.6; 150K current pick pass 74.3 %, within-60 20.4 %, median 86 d, profit $98,728. Matches the brief.
Grid: 17.8K stage-1 configs (stop $50-150, NOISE micros, CANDACE 0-6, one- and two-step brakes at $1,500/$1,000 (150K) and $500/$333 (25K)) + 4.2K extras (taper, grow, day lock, CANDACE 10:30, lock 80/120) = ~22K runs, each over all 1,252 starts. Rules as the earlier studies (C40, day stop 38 %). DLL OFF = DLL and LucidScale removed, every other rule on.
"Acceptable" = pass >= base, stuck <= base, profit >= base, median <= base, judge >= base-3, pick >= base-5.

**Objective A (more passes within 60 days)**
- 25K: small real gain. Best acceptable: same N1@$75 + CANDACE 2, but CANDACE drops to 1 micro below $500 (not $333), NOISE lock 80 pt, day lock at 50 % of the remaining target: within-60 36.3 % (+2.6), median 54 d, pass 61.9, stuck 29.3, profit $19,540 (+$212), judge 55.2, pick 61.4. Lock 80 alone gives 35.5 % (config-only); the $500 brake step and the day lock add the rest. Same numbers with DLL ON and OFF (the DLL never binds at these sizes).
- 150K: **none** worth taking. Only the day lock (50 % or 70 %) is acceptable: pass 74.7 (+0.4), judge 65.2, but within-60 stays 20.4. Every config with more within-60 passes loses 5-yr pass, stuck or profit (tradeoff table). DLL ON = OFF.

**Objective B (more micros, higher 5-yr pass)**
- 25K: none beyond N1. NOISE 2 micros lifts within-60 (37 %) but 5-yr pass collapses from 62 to 43 %. Best acceptable is still N1 (62.2 %, lock 80 + CANDACE $500 brake: +0.4 pt).
- 150K: none. Pass FALLS with every extra micro: N5 75.8, N6 70.3, N7 67.1, N8 61.7, N10 56 (58.5 DLL OFF). Fewer micros pass more: N4 81.3, N3 89.5 (stuck 0 %, but within-60 2.8 %, profit $62K, median 145 d). More micros only buy speed (N7 + CANDACE 4: within-60 31.4 %, pass 67.0, profit $135K, stuck 22.4) at the cost of pass rate, so they fail the acceptance bar.
- The D159 cap lift therefore does not help B; it matters only if you accept a lower pass rate for faster passes.

Tags: NOISE lock 80 = config-only (check it is a plan-file value). CANDACE fixed micros + CANDACE brake at $500 = needs code. Day lock = config-only (EVAL_DAY_LOCK). 150K day lock = config-only. D133 cap lift = approved config.

## Tradeoff (not accepted, for the decision): 5-yr pass vs within-60 (150K, DLL ON)
| config | pass | stuck | <=60d | profit |
|---|---|---|---|---|
| base N5@$100 + C4, brake 2 below $1,500 | 74.3 | 17.0 | 20.4 | 98,728 |
| N3@$100 + C4, NOISE 2 below $2,250, CANDACE 2 below $1,500 / 1 below $1,000 | 89.5 | 0.0 | 2.8 | 62,192 |
| N4 (best pass) | 81.3 | 9.3 | 13.1 | 84,155 |
| N6 + C4 (best pass) | 68.5 | 20.9 | 26.4 | 116,995 |
| N7 + C4 | 67.0 | 22.4 | 31.4 | 135,262 |
| N8 + C6 | 61.7 | 25.6 | 27.8 | 136,145 |
| N10 + C6 (max <=60d, DLL ON) | 41.0 | 54.0 | 34.5 | 193,760 |

25K max <=60d: N2@$100 + C3 = 40.3 % within 60 d but pass 42.7, stuck 54.7.

Files: lib.py, repro.py, search.py, stage3.py, report.py, results.json, tables.md (top-5 per plan x objective x DLL + pass-vs-micros curves). Brake bands in the tables read `<$cushion:micros`. A and B share one acceptance filter, so their top-5 lists overlap.

# Top-5 tables


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