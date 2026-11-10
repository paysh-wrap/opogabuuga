STREAM
- IS: 565 sessions, 287 with a trade (51%), 148 winning days (avg $170, max $704), 139 losing days (avg $-115); net per session $16.39 per micro.
- HO: 740 sessions, 336 with a trade (45%), 179 winning days (avg $190, max $1580), 157 losing days (avg $-151); net per session $13.86 per micro.

FLOOR
| plan | target | 40% cap (reading A) | min days = ceil(target / cap) | best-case days (3 profitable days needed) |
|---|---|---|---|---|
| Daily25K | $1,250 | $500 | 3 (=2.5, so 3) | 3 |
| Flex25K | $1,250 | $500 | 3 (=2.5, so 3) | 3 |
| Flex50K | $3,000 | $1,200 | 3 (=2.5, so 3) | 3 |
| Flex100K | $6,000 | $2,400 | 3 (=2.5, so 3) | 3 |
| Flex150K | $9,000 | $3,600 | 3 (=2.5, so 3) | 3 |

## Reading A (best day <= 40% of target; binding case)

Columns: pass / bust / still-open(750) in %, sessions to pass p25 / median / p75 (among passers), sessions per successful pass incl. resets. HO = 2024-26, L12 = last 12 months (L12 is ~260 days: noisy).

### Daily25K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1 micro flat, skip day after a losing day | yes | 8/59/33 | 26/43/68 | 3739 | 6/51 | 30 |
| 1 micro flat, day-stop 35% target, skip day after a losing day | yes | 8/59/33 | 26/43/68 | 3739 | 6/51 | 30 |
| 1 micro flat **(baseline)** | yes | 8/55/37 | 25/37/55 | 3997 | 5/58 | 29 |
| 1 micro flat, day-stop 35% target | yes | 8/55/37 | 25/37/55 | 3997 | 5/58 | 29 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 3/60/38 | 19/37/59 | 11509 | 0/64 | 41 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target | yes | 3/60/38 | 19/37/59 | 11533 | 0/64 | 41 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target, day-stop 35% target | yes | 2/60/38 | 18/28/63 | 12979 | 0/63 | 41 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target | yes | 2/60/38 | 18/28/63 | 13007 | 0/63 | 41 |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target, day-stop 35% target | yes | 2/61/37 | 12/24/43 | 14382 | 0/63 | - |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target | yes | 2/61/37 | 12/24/43 | 14383 | 0/63 | - |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 2/61/37 | 18/33/51 | 17085 | 0/64 | - |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target | yes | 2/61/37 | 18/33/51 | 17086 | 0/64 | - |
| 1->2 micros while cushion>=50% MLL | ref | 0/74/26 | 15/24/35 | 43457 | 0/77 | - |

Best with HO bust <= 40%: **none** (every setting busts more).

Best with HO bust <= 35%: **none** (every setting busts more).

### Flex25K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1 micro flat, skip day after a losing day | yes | 8/60/32 | 25/43/68 | 3729 | 5/52 | 30 |
| 1 micro flat, day-stop 35% target, skip day after a losing day | yes | 8/60/32 | 25/43/68 | 3729 | 5/52 | 30 |
| 1 micro flat **(baseline)** | yes | 8/55/37 | 25/38/56 | 3983 | 5/59 | 30 |
| 1 micro flat, day-stop 35% target | yes | 8/55/37 | 25/38/56 | 3983 | 5/59 | 30 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 3/60/37 | 19/38/59 | 11432 | 0/64 | 41 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target | yes | 3/60/37 | 19/38/59 | 11457 | 0/64 | 41 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target, day-stop 35% target | yes | 2/60/37 | 18/35/63 | 12892 | 0/64 | 41 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target | yes | 2/60/38 | 18/35/63 | 12921 | 0/64 | 41 |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target, day-stop 35% target | yes | 2/62/36 | 12/24/43 | 14113 | 0/64 | - |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target | yes | 2/62/36 | 12/24/43 | 14114 | 0/64 | - |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 2/61/37 | 18/33/51 | 16942 | 0/65 | - |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target | yes | 2/61/37 | 18/33/51 | 16943 | 0/65 | - |
| 1->2 micros while cushion>=50% MLL | ref | 0/76/23 | 15/24/35 | 39633 | 0/81 | - |

Best with HO bust <= 40%: **none** (every setting busts more).

Best with HO bust <= 35%: **none** (every setting busts more).

### Flex50K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1 micro flat, skip day after a losing day | yes | 46/28/26 | 140/205/288 | 768 | 38/18 | 132 |
| 1 micro flat, day-stop 35% target, skip day after a losing day | yes | 46/28/26 | 140/205/288 | 768 | 38/18 | 132 |
| 1 micro flat **(baseline)** | yes | 40/23/38 | 107/154/232 | 976 | 34/24 | 124 |
| 1 micro flat, day-stop 35% target | yes | 40/23/38 | 107/154/232 | 976 | 34/24 | 124 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target | yes | 30/26/44 | 89/142/219 | 1384 | 21/29 | 97 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 30/26/44 | 89/142/219 | 1384 | 21/29 | 97 |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target | yes | 23/32/45 | 80/124/189 | 1753 | 19/34 | 89 |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 23/32/45 | 80/124/189 | 1753 | 19/34 | 89 |
| 1->2 micros while cushion>=50% MLL, drop after loss, only while profit<50% target | yes | 19/38/43 | 71/113/159 | 2032 | 17/41 | 69 |
| 1->2 micros while cushion>=50% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 19/38/43 | 71/113/159 | 2032 | 17/41 | 69 |
| 1->2 micros while cushion>=30% MLL, drop after loss, only while profit<50% target | yes | 18/40/42 | 69/103/144 | 2052 | 18/41 | 70 |
| 1->2 micros while cushion>=30% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 18/40/42 | 69/103/144 | 2052 | 18/41 | 70 |
| 1->2 micros while cushion>=50% MLL | ref | 10/48/42 | 42/70/106 | 3653 | 6/54 | 47 |
| 1->3 micros while cushion>=50% MLL | ref | 4/64/32 | 19/33/68 | 6957 | 3/70 | 33 |

Best with HO bust <= 40%: **1 micro flat, skip day after a losing day** - pass 46%, bust 28%, median 205 sessions (p25 140, p75 288), 768 sessions per pass with resets; baseline: 154 median, 976 per pass.

Best with HO bust <= 35%: **1 micro flat, skip day after a losing day** - pass 46%, bust 28%, median 205 sessions (p25 140, p75 288), 768 sessions per pass with resets; baseline: 154 median, 976 per pass.

### Flex100K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1 micro flat **(baseline)** | ref | 87/8/6 | 264/356/479 | 448 | 89/9 | 292 |
| 1 micro flat, day-stop 35% target | ref | 87/8/6 | 264/356/479 | 448 | 89/9 | 292 |
| 1->2 micros while cushion>=50% MLL | yes | 41/28/31 | 110/174/256 | 890 | 36/33 | 138 |
| 1->2 micros while cushion>=50% MLL, day-stop 35% target | yes | 41/28/31 | 110/174/256 | 890 | 36/33 | 138 |
| 1->2 micros while cushion>=30% MLL | yes | 35/35/30 | 99/151/223 | 935 | 30/37 | 110 |
| 1->2 micros while cushion>=30% MLL, day-stop 35% target | yes | 35/35/30 | 99/151/223 | 935 | 30/37 | 110 |
| 1->3 micros while cushion>=30% MLL, only while profit<50% target | yes | 30/42/28 | 117/177/251 | 975 | 23/46 | 128 |
| 1->3 micros while cushion>=30% MLL, only while profit<50% target, day-stop 35% target | yes | 30/42/28 | 117/177/251 | 975 | 23/46 | 128 |
| 1->3 micros while cushion>=70% MLL | yes | 27/34/39 | 87/160/267 | 1540 | 23/40 | 121 |
| 1->3 micros while cushion>=70% MLL, day-stop 35% target | yes | 27/34/39 | 87/160/267 | 1540 | 23/40 | 121 |
| 1->3 micros while cushion>=50% MLL | yes | 19/44/37 | 62/98/171 | 1921 | 13/49 | 84 |
| 1->3 micros while cushion>=50% MLL, day-stop 35% target | yes | 19/44/37 | 62/98/171 | 1921 | 13/49 | 84 |
| 1->3 micros while cushion>=30% MLL | yes | 15/52/32 | 51/78/109 | 1940 | 9/57 | 66 |
| 1->3 micros while cushion>=30% MLL, day-stop 35% target | yes | 15/52/32 | 51/78/109 | 1940 | 9/57 | 66 |
| 1->4 micros while cushion>=50% MLL | ref | 9/56/34 | 42/67/125 | 3483 | 6/63 | 46 |

Best with HO bust <= 40%: **1 micro flat** - pass 87%, bust 8%, median 356 sessions (p25 264, p75 479), 448 sessions per pass with resets; baseline: 356 median, 448 per pass.

Best with HO bust <= 35%: **1 micro flat** - pass 87%, bust 8%, median 356 sessions (p25 264, p75 479), 448 sessions per pass with resets; baseline: 356 median, 448 per pass.

### Flex150K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1->2 micros while cushion>=50% MLL | ref | 87/8/5 | 188/275/417 | 383 | 86/11 | 223 |
| 1 micro flat **(baseline)** | ref | 68/1/31 | 401/505/607 | 851 | 85/1 | 441 |
| 1 micro flat, day-stop 35% target | ref | 68/1/31 | 401/505/607 | 851 | 85/1 | 441 |
| 1->4 micros while cushion>=30% MLL | yes | 30/45/25 | 63/95/151 | 938 | 19/48 | 75 |
| 1->4 micros while cushion>=30% MLL, day-stop 35% target | yes | 30/45/25 | 63/95/151 | 938 | 19/48 | 75 |
| 1->3 micros while cushion>=30% MLL | yes | 37/31/32 | 105/156/237 | 947 | 31/34 | 120 |
| 1->3 micros while cushion>=30% MLL, day-stop 35% target | yes | 37/31/32 | 105/156/237 | 947 | 31/34 | 120 |
| 1->3 micros while cushion>=50% MLL | yes | 44/19/37 | 127/203/328 | 996 | 40/24 | 171 |
| 1->3 micros while cushion>=50% MLL, day-stop 35% target | yes | 44/19/37 | 127/203/328 | 996 | 40/24 | 171 |
| 1->4 micros while cushion>=50% MLL | yes | 37/31/32 | 76/142/266 | 1054 | 24/37 | 113 |
| 1->4 micros while cushion>=50% MLL, day-stop 35% target | yes | 37/31/32 | 76/142/266 | 1054 | 24/37 | 113 |
| 1->5 micros while cushion>=50% MLL | yes | 20/42/38 | 58/111/250 | 2016 | 9/47 | 118 |
| 1->5 micros while cushion>=50% MLL, day-stop 35% target | yes | 20/42/38 | 58/111/250 | 2016 | 9/47 | 118 |
| 1->5 micros while cushion>=30% MLL | yes | 13/56/31 | 42/64/97 | 2211 | 4/59 | 66 |
| 1->5 micros while cushion>=30% MLL, day-stop 35% target | yes | 13/56/31 | 42/64/97 | 2211 | 4/59 | 66 |
| 1->6 micros while cushion>=50% MLL | ref | 10/52/38 | 45/88/172 | 3837 | 6/56 | 46 |

Best with HO bust <= 40%: **1->2 micros while cushion>=50% MLL** - pass 87%, bust 8%, median 275 sessions (p25 188, p75 417), 383 sessions per pass with resets; baseline: 505 median, 851 per pass.

Best with HO bust <= 35%: **1->2 micros while cushion>=50% MLL** - pass 87%, bust 8%, median 275 sessions (p25 188, p75 417), 383 sessions per pass with resets; baseline: 505 median, 851 per pass.


## Reading B (literal 40% of day-start balance; never binds - sensitivity)

Columns: pass / bust / still-open(750) in %, sessions to pass p25 / median / p75 (among passers), sessions per successful pass incl. resets. HO = 2024-26, L12 = last 12 months (L12 is ~260 days: noisy).

### Daily25K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1->2 micros while cushion>=50% MLL | ref | 41/59/0 | 9/14/22 | 48 | 36/64 | 13 |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target | yes | 48/52/0 | 9/18/33 | 55 | 46/54 | 15 |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target, day-stop 35% target | yes | 48/52/0 | 9/18/34 | 55 | 46/54 | 15 |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target | yes | 48/52/0 | 10/21/37 | 59 | 44/56 | 17 |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 48/52/0 | 11/21/37 | 60 | 44/56 | 17 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target | yes | 50/50/0 | 11/22/42 | 63 | 45/55 | 16 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target, day-stop 35% target | yes | 50/50/0 | 12/23/42 | 63 | 45/55 | 16 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target | yes | 49/51/0 | 12/23/44 | 66 | 45/55 | 18 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 49/51/0 | 13/23/44 | 67 | 45/55 | 18 |
| 1->2 micros while cushion>=90% MLL | yes | 45/55/0 | 10/19/37 | 67 | 40/60 | 15 |
| 1->2 micros while cushion>=90% MLL, day-stop 35% target | yes | 45/55/0 | 10/19/37 | 68 | 40/60 | 15 |
| 1 micro flat **(baseline)** | yes | 55/45/0 | 22/37/58 | 81 | 52/48 | 27 |
| 1 micro flat, day-stop 35% target | yes | 55/45/0 | 22/37/58 | 81 | 52/48 | 27 |

Best with HO bust <= 40%: **none** (every setting busts more).

Best with HO bust <= 35%: **none** (every setting busts more).

### Flex25K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1->2 micros while cushion>=50% MLL | ref | 40/60/0 | 9/14/22 | 48 | 36/64 | 12 |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target | yes | 47/53/0 | 9/17/33 | 55 | 45/55 | 15 |
| 1->2 micros while cushion>=70% MLL, only while profit<50% target, day-stop 35% target | yes | 47/53/0 | 9/18/33 | 55 | 45/55 | 15 |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target | yes | 48/52/0 | 10/21/38 | 59 | 44/56 | 17 |
| 1->2 micros while cushion>=70% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 48/52/0 | 11/21/38 | 60 | 44/56 | 17 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target | yes | 50/50/0 | 11/22/42 | 63 | 45/55 | 16 |
| 1->2 micros while cushion>=90% MLL, only while profit<50% target, day-stop 35% target | yes | 50/50/0 | 12/22/42 | 64 | 45/55 | 16 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target | yes | 49/51/0 | 12/23/44 | 66 | 45/55 | 18 |
| 1->2 micros while cushion>=90% MLL, drop after loss, only while profit<50% target, day-stop 35% target | yes | 49/51/0 | 13/23/44 | 67 | 45/55 | 18 |
| 1 micro flat **(baseline)** | yes | 54/46/0 | 22/37/60 | 82 | 51/49 | 27 |
| 1 micro flat, day-stop 35% target | yes | 54/46/0 | 22/37/60 | 82 | 51/49 | 27 |
| 1 micro flat, skip day after a losing day | yes | 50/50/0 | 27/47/79 | 113 | 56/44 | 29 |
| 1 micro flat, day-stop 35% target, skip day after a losing day | yes | 50/50/0 | 27/47/79 | 113 | 56/44 | 29 |

Best with HO bust <= 40%: **none** (every setting busts more).

Best with HO bust <= 35%: **none** (every setting busts more).

### Flex50K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1->3 micros while cushion>=30% MLL, only while profit<50% target, day-stop 35% target | yes | 51/49/0 | 24/42/74 | 85 | 47/53 | 34 |
| 1->3 micros while cushion>=30% MLL, only while profit<50% target | yes | 51/49/0 | 24/42/74 | 85 | 47/53 | 34 |
| 1->3 micros while cushion>=50% MLL | yes | 46/54/0 | 14/25/49 | 93 | 41/59 | 22 |
| 1->3 micros while cushion>=50% MLL, day-stop 35% target | yes | 46/54/0 | 14/25/49 | 93 | 41/59 | 22 |
| 1->3 micros while cushion>=50% MLL, only while profit<50% target | yes | 53/47/0 | 25/45/83 | 106 | 50/50 | 39 |
| 1->3 micros while cushion>=50% MLL, only while profit<50% target, day-stop 35% target | yes | 53/47/0 | 25/45/83 | 106 | 50/50 | 39 |
| 1->2 micros while cushion>=30% MLL | yes | 54/46/0 | 27/48/78 | 107 | 48/52 | 35 |
| 1->2 micros while cushion>=30% MLL, day-stop 35% target | yes | 54/46/0 | 27/48/78 | 107 | 48/52 | 35 |
| 1->2 micros while cushion>=30% MLL, only while profit<50% target | yes | 59/41/0 | 42/71/107 | 120 | 56/44 | 53 |
| 1->2 micros while cushion>=30% MLL, only while profit<50% target, day-stop 35% target | yes | 59/41/0 | 42/71/107 | 120 | 56/44 | 53 |
| 1->2 micros while cushion>=50% MLL | yes | 58/42/0 | 32/55/93 | 123 | 52/48 | 41 |
| 1->2 micros while cushion>=50% MLL, day-stop 35% target | yes | 58/42/0 | 32/55/93 | 123 | 52/48 | 41 |
| 1 micro flat **(baseline)** | ref | 78/22/0 | 96/149/219 | 210 | 76/24 | 116 |
| 1 micro flat, day-stop 35% target | ref | 78/22/0 | 96/149/219 | 210 | 76/24 | 116 |

Best with HO bust <= 40%: **1 micro flat** - pass 78%, bust 22%, median 149 sessions (p25 96, p75 219), 210 sessions per pass with resets; baseline: 149 median, 210 per pass.

Best with HO bust <= 35%: **1 micro flat** - pass 78%, bust 22%, median 149 sessions (p25 96, p75 219), 210 sessions per pass with resets; baseline: 149 median, 210 per pass.

### Flex100K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1->4 micros while cushion>=30% MLL | yes | 41/59/0 | 25/43/69 | 116 | 33/67 | 31 |
| 1->4 micros while cushion>=30% MLL, day-stop 35% target | yes | 41/59/0 | 25/43/69 | 116 | 33/67 | 31 |
| 1->3 micros while cushion>=30% MLL | yes | 50/50/0 | 45/71/108 | 156 | 45/55 | 51 |
| 1->3 micros while cushion>=30% MLL, day-stop 35% target | yes | 50/50/0 | 45/71/108 | 156 | 45/55 | 51 |
| 1->4 micros while cushion>=50% MLL | yes | 48/52/0 | 30/56/105 | 173 | 42/58 | 40 |
| 1->4 micros while cushion>=50% MLL, day-stop 35% target | yes | 48/52/0 | 30/56/105 | 173 | 42/58 | 40 |
| 1->4 micros while cushion>=30% MLL, only while profit<50% target | yes | 49/51/0 | 65/115/189 | 180 | 43/57 | 75 |
| 1->4 micros while cushion>=30% MLL, only while profit<50% target, day-stop 35% target | yes | 49/51/0 | 65/115/189 | 180 | 43/57 | 75 |
| 1->3 micros while cushion>=50% MLL | yes | 58/42/0 | 52/93/164 | 212 | 53/47 | 67 |
| 1->3 micros while cushion>=50% MLL, day-stop 35% target | yes | 58/42/0 | 52/93/164 | 212 | 53/47 | 67 |
| 1->2 micros while cushion>=30% MLL | yes | 66/34/0 | 91/140/207 | 225 | 64/36 | 106 |
| 1->2 micros while cushion>=30% MLL, day-stop 35% target | yes | 66/34/0 | 91/140/207 | 225 | 64/36 | 106 |
| 1->2 micros while cushion>=50% MLL | ref | 72/28/0 | 99/161/245 | 256 | 67/33 | 118 |
| 1 micro flat **(baseline)** | ref | 87/8/6 | 264/356/479 | 448 | 89/9 | 292 |
| 1 micro flat, day-stop 35% target | ref | 87/8/6 | 264/356/479 | 448 | 89/9 | 292 |

Best with HO bust <= 40%: **1->2 micros while cushion>=30% MLL** - pass 66%, bust 34%, median 140 sessions (p25 91, p75 207), 225 sessions per pass with resets; baseline: 356 median, 448 per pass.

Best with HO bust <= 35%: **1->2 micros while cushion>=30% MLL** - pass 66%, bust 34%, median 140 sessions (p25 91, p75 207), 225 sessions per pass with resets; baseline: 356 median, 448 per pass.

### Flex150K

| setting | picked on IS | HO pass/bust/open | HO p25/med/p75 | HO sess per pass | L12 pass/bust | L12 med |
|---|---|---|---|---|---|---|
| 1->6 micros while cushion>=30% MLL | yes | 40/60/0 | 25/43/67 | 137 | 34/66 | 32 |
| 1->6 micros while cushion>=30% MLL, day-stop 35% target | yes | 40/60/0 | 25/43/67 | 137 | 34/66 | 32 |
| 1->5 micros while cushion>=30% MLL | yes | 47/53/0 | 36/60/97 | 171 | 44/56 | 46 |
| 1->5 micros while cushion>=30% MLL, day-stop 35% target | yes | 47/53/0 | 36/60/97 | 171 | 44/56 | 46 |
| 1->4 micros while cushion>=30% MLL | yes | 57/43/0 | 55/88/141 | 198 | 53/47 | 65 |
| 1->4 micros while cushion>=30% MLL, day-stop 35% target | yes | 57/43/0 | 55/88/141 | 198 | 53/47 | 65 |
| 1->3 micros while cushion>=30% MLL | yes | 69/31/0 | 93/147/229 | 242 | 66/34 | 110 |
| 1->3 micros while cushion>=30% MLL, day-stop 35% target | yes | 69/31/0 | 93/147/229 | 242 | 66/34 | 110 |
| 1->6 micros while cushion>=50% MLL | ref | 52/48/0 | 33/65/171 | 276 | 47/53 | 52 |
| 1->5 micros while cushion>=50% MLL | ref | 59/40/1 | 47/98/235 | 313 | 56/44 | 78 |
| 1->3 micros while cushion>=50% MLL | yes | 78/19/3 | 107/184/307 | 327 | 75/24 | 147 |
| 1->3 micros while cushion>=50% MLL, day-stop 35% target | yes | 78/19/3 | 107/184/307 | 327 | 75/24 | 147 |
| 1->4 micros while cushion>=50% MLL | yes | 68/30/2 | 70/138/272 | 328 | 64/36 | 104 |
| 1->4 micros while cushion>=50% MLL, day-stop 35% target | yes | 68/30/2 | 70/138/272 | 328 | 64/36 | 104 |
| 1->2 micros while cushion>=50% MLL | ref | 87/8/5 | 188/275/417 | 383 | 86/11 | 223 |
| 1 micro flat **(baseline)** | ref | 68/1/31 | 401/505/607 | 851 | 85/1 | 441 |
| 1 micro flat, day-stop 35% target | ref | 68/1/31 | 401/505/607 | 851 | 85/1 | 441 |

Best with HO bust <= 40%: **1->3 micros while cushion>=30% MLL** - pass 69%, bust 31%, median 147 sessions (p25 93, p75 229), 242 sessions per pass with resets; baseline: 505 median, 851 per pass.

Best with HO bust <= 35%: **1->3 micros while cushion>=30% MLL** - pass 69%, bust 31%, median 147 sessions (p25 93, p75 229), 242 sessions per pass with resets; baseline: 505 median, 851 per pass.
