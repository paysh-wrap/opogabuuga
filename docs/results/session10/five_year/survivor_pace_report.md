# Payout pace study (agentL)
Current live sizes (D64 Regular + brake; 150K-High = 4/2), cadence 25K/50K=10, 100K/150K=5 sessions, max-eligible, 90% split, 260-session horizon, starts every 2 sessions, per account (5 accounts take same trades => x5 for household). Data: main_strategy_5y.csv.


# WITH 5-payout cap (as live)


## 25K (523 starts; buffer 26100, min req 500, caps 1000/1500, cadence 10)

**ALL** bust 56.6%
- All: n=523 payouts/yr 1.65 | dist 0/1/2/3/4/5+ % = 42/12/9/17/15/4 | mean paid $1,646
- Survivors: n=227 payouts/yr 3.08 | dist 0/1/2/3/4/5+ % = 1/11/17/33/29/10 | mean paid $3,125 | median sess to 1st payout 80
- After 1st payout: gap sessions median 40.0 mean 45.5; later-payout size to you mean $1,148 median $1,215; checks after 1st: 4682; PAID 12%, below $500 0%, consistency>40% 51%, cycle profit below min 37%
- Gross profit needed before 1st payout $1,600; reached by 62% of starts; median session reached 51 => remaining of 260: 209
- $ per 2 weeks (10 sessions): 1 acct all $63, survivors $120; 5 accts all $317, survivors $601

**H1 2021-11..2023-12** bust 57.2%
- All: n=283 payouts/yr 1.91 | dist 0/1/2/3/4/5+ % = 35/11/13/14/18/8 | mean paid $1,794
- Survivors: n=121 payouts/yr 3.27 | dist 0/1/2/3/4/5+ % = 0/7/23/22/29/18 | mean paid $3,086 | median sess to 1st payout 80
- After 1st payout: gap sessions median 30.0 mean 44.0; later-payout size to you mean $1,070 median $1,132; checks after 1st: 2696; PAID 13%, consistency>40% 40%, cycle profit below min 46%
- Gross profit needed before 1st payout $1,600; reached by 67% of starts; median session reached 56 => remaining of 260: 204
- $ per 2 weeks (10 sessions): 1 acct all $69, survivors $119; 5 accts all $345, survivors $593

**H2 2024-01..2026-10** bust 55.8%
- All: n=240 payouts/yr 1.34 | dist 0/1/2/3/4/5+ % = 49/13/5/20/13/0 | mean paid $1,472
- Survivors: n=106 payouts/yr 2.86 | dist 0/1/2/3/4/5+ % = 2/14/9/45/29/0 | mean paid $3,170 | median sess to 1st payout 70.0
- After 1st payout: gap sessions median 40.0 mean 48.1; later-payout size to you mean $1,286 median $1,350; checks after 1st: 1986; PAID 10%, below $500 0%, consistency>40% 65%, cycle profit below min 25%
- Gross profit needed before 1st payout $1,600; reached by 57% of starts; median session reached 45.5 => remaining of 260: 214.5
- $ per 2 weeks (10 sessions): 1 acct all $57, survivors $122; 5 accts all $283, survivors $610

## 50K (523 starts; buffer 52100, min req 500, caps 2000/2500, cadence 10)

**ALL** bust 44.2%
- All: n=523 payouts/yr 1.70 | dist 0/1/2/3/4/5+ % = 34/15/16/19/12/4 | mean paid $2,933
- Survivors: n=292 payouts/yr 2.77 | dist 0/1/2/3/4/5+ % = 2/13/25/32/21/7 | mean paid $4,865 | median sess to 1st payout 70
- After 1st payout: gap sessions median 30 mean 46.0; later-payout size to you mean $2,039 median $2,250; checks after 1st: 5489; PAID 10%, consistency>40% 47%, cycle profit below min 43%
- Gross profit needed before 1st payout $2,600; reached by 70% of starts; median session reached 47.0 => remaining of 260: 213.0
- $ per 2 weeks (10 sessions): 1 acct all $113, survivors $187; 5 accts all $564, survivors $936

**H1 2021-11..2023-12** bust 40.3%
- All: n=283 payouts/yr 2.06 | dist 0/1/2/3/4/5+ % = 24/15/21/17/16/7 | mean paid $3,386
- Survivors: n=169 payouts/yr 3.03 | dist 0/1/2/3/4/5+ % = 0/8/30/25/26/11 | mean paid $5,105 | median sess to 1st payout 80
- After 1st payout: gap sessions median 30 mean 44.7; later-payout size to you mean $1,994 median $2,202; checks after 1st: 3364; PAID 11%, consistency>40% 35%, cycle profit below min 54%
- Gross profit needed before 1st payout $2,600; reached by 77% of starts; median session reached 51 => remaining of 260: 209
- $ per 2 weeks (10 sessions): 1 acct all $130, survivors $196; 5 accts all $651, survivors $982

**H2 2024-01..2026-10** bust 48.8%
- All: n=240 payouts/yr 1.29 | dist 0/1/2/3/4/5+ % = 46/15/10/21/8/0 | mean paid $2,399
- Survivors: n=123 payouts/yr 2.41 | dist 0/1/2/3/4/5+ % = 4/21/19/41/15/0 | mean paid $4,534 | median sess to 1st payout 70.0
- After 1st payout: gap sessions median 40.0 mean 48.8; later-payout size to you mean $2,130 median $2,250; checks after 1st: 2125; PAID 8%, consistency>40% 65%, cycle profit below min 26%
- Gross profit needed before 1st payout $2,600; reached by 63% of starts; median session reached 40 => remaining of 260: 220
- $ per 2 weeks (10 sessions): 1 acct all $92, survivors $174; 5 accts all $461, survivors $872

## 100K (523 starts; buffer 103100, min req 500, caps 2500/3000, cadence 5)

**ALL** bust 27.5%
- All: n=523 payouts/yr 2.04 | dist 0/1/2/3/4/5+ % = 26/16/18/14/17/9 | mean paid $3,653
- Survivors: n=379 payouts/yr 2.73 | dist 0/1/2/3/4/5+ % = 4/19/23/19/23/12 | mean paid $4,924 | median sess to 1st payout 85
- After 1st payout: gap sessions median 30.0 mean 42.6; later-payout size to you mean $2,219 median $2,343; checks after 1st: 11731; PAID 6%, consistency>40% 39%, cycle profit below min 55%
- Gross profit needed before 1st payout $3,600; reached by 80% of starts; median session reached 69.0 => remaining of 260: 191.0
- $ per 2 weeks (10 sessions): 1 acct all $140, survivors $189; 5 accts all $702, survivors $947

**H1 2021-11..2023-12** bust 14.8%
- All: n=283 payouts/yr 2.43 | dist 0/1/2/3/4/5+ % = 10/20/27/16/13/14 | mean paid $4,049
- Survivors: n=241 payouts/yr 2.73 | dist 0/1/2/3/4/5+ % = 3/19/29/17/16/16 | mean paid $4,587 | median sess to 1st payout 90.0
- After 1st payout: gap sessions median 30 mean 43.2; later-payout size to you mean $2,098 median $2,193; checks after 1st: 7078; PAID 6%, consistency>40% 27%, cycle profit below min 67%
- Gross profit needed before 1st payout $3,600; reached by 90% of starts; median session reached 81.0 => remaining of 260: 179.0
- $ per 2 weeks (10 sessions): 1 acct all $156, survivors $176; 5 accts all $779, survivors $882

**H2 2024-01..2026-10** bust 42.5%
- All: n=240 payouts/yr 1.58 | dist 0/1/2/3/4/5+ % = 45/12/8/12/20/2 | mean paid $3,185
- Survivors: n=138 payouts/yr 2.74 | dist 0/1/2/3/4/5+ % = 7/19/13/22/36/4 | mean paid $5,513 | median sess to 1st payout 70
- After 1st payout: gap sessions median 35 mean 41.6; later-payout size to you mean $2,430 median $2,700; checks after 1st: 4653; PAID 5%, consistency>40% 57%, cycle profit below min 37%
- Gross profit needed before 1st payout $3,600; reached by 68% of starts; median session reached 58.5 => remaining of 260: 201.5
- $ per 2 weeks (10 sessions): 1 acct all $122, survivors $212; 5 accts all $612, survivors $1,060

## 150K (523 starts; buffer 154600, min req 500, caps 3000/3500, cadence 5)

**ALL** bust 24.5%
- All: n=523 payouts/yr 2.13 | dist 0/1/2/3/4/5+ % = 24/14/20/15/17/9 | mean paid $4,963
- Survivors: n=395 payouts/yr 2.78 | dist 0/1/2/3/4/5+ % = 3/16/26/21/23/12 | mean paid $6,531 | median sess to 1st payout 75
- After 1st payout: gap sessions median 30.0 mean 42.6; later-payout size to you mean $2,921 median $3,150; checks after 1st: 12302; PAID 6%, consistency>40% 43%, cycle profit below min 52%
- Gross profit needed before 1st payout $5,100; reached by 80% of starts; median session reached 66 => remaining of 260: 194
- $ per 2 weeks (10 sessions): 1 acct all $191, survivors $251; 5 accts all $954, survivors $1,256

**H1 2021-11..2023-12** bust 8.8%
- All: n=283 payouts/yr 2.59 | dist 0/1/2/3/4/5+ % = 6/17/30/18/13/15 | mean paid $5,770
- Survivors: n=258 payouts/yr 2.80 | dist 0/1/2/3/4/5+ % = 1/15/33/20/14/16 | mean paid $6,290 | median sess to 1st payout 85
- After 1st payout: gap sessions median 30 mean 43.1; later-payout size to you mean $2,863 median $3,150; checks after 1st: 7641; PAID 6%, consistency>40% 30%, cycle profit below min 64%
- Gross profit needed before 1st payout $5,100; reached by 94% of starts; median session reached 77 => remaining of 260: 183
- $ per 2 weeks (10 sessions): 1 acct all $222, survivors $242; 5 accts all $1,110, survivors $1,210

**H2 2024-01..2026-10** bust 42.9%
- All: n=240 payouts/yr 1.58 | dist 0/1/2/3/4/5+ % = 45/11/8/12/22/2 | mean paid $4,011
- Survivors: n=137 payouts/yr 2.75 | dist 0/1/2/3/4/5+ % = 7/18/14/21/38/3 | mean paid $6,984 | median sess to 1st payout 65.0
- After 1st payout: gap sessions median 35 mean 41.6; later-payout size to you mean $3,030 median $3,150; checks after 1st: 4661; PAID 5%, consistency>40% 63%, cycle profit below min 31%
- Gross profit needed before 1st payout $5,100; reached by 63% of starts; median session reached 51.5 => remaining of 260: 208.5
- $ per 2 weeks (10 sessions): 1 acct all $154, survivors $269; 5 accts all $771, survivors $1,343

## 150K-High (523 starts; buffer 154600, min req 500, caps 3000/3500, cadence 5)

**ALL** bust 27.9%
- All: n=523 payouts/yr 2.11 | dist 0/1/2/3/4/5+ % = 24/15/20/14/16/10 | mean paid $5,532
- Survivors: n=377 payouts/yr 2.85 | dist 0/1/2/3/4/5+ % = 1/17/27/20/23/13 | mean paid $7,551 | median sess to 1st payout 70
- After 1st payout: gap sessions median 30.0 mean 41.4; later-payout size to you mean $3,088 median $3,150; checks after 1st: 12399; PAID 6%, consistency>40% 42%, cycle profit below min 52%
- Gross profit needed before 1st payout $5,100; reached by 80% of starts; median session reached 53.0 => remaining of 260: 207.0
- $ per 2 weeks (10 sessions): 1 acct all $213, survivors $290; 5 accts all $1,064, survivors $1,452

**H1 2021-11..2023-12** bust 13.4%
- All: n=283 payouts/yr 2.54 | dist 0/1/2/3/4/5+ % = 9/17/29/16/15/14 | mean paid $6,442
- Survivors: n=245 payouts/yr 2.88 | dist 0/1/2/3/4/5+ % = 0/15/33/18/17/17 | mean paid $7,353 | median sess to 1st payout 75
- After 1st payout: gap sessions median 30.0 mean 41.6; later-payout size to you mean $3,081 median $3,150; checks after 1st: 7791; PAID 6%, consistency>40% 30%, cycle profit below min 64%
- Gross profit needed before 1st payout $5,100; reached by 91% of starts; median session reached 61 => remaining of 260: 199
- $ per 2 weeks (10 sessions): 1 acct all $248, survivors $283; 5 accts all $1,239, survivors $1,414

**H2 2024-01..2026-10** bust 45.0%
- All: n=240 payouts/yr 1.60 | dist 0/1/2/3/4/5+ % = 42/14/10/12/18/4 | mean paid $4,460
- Survivors: n=132 payouts/yr 2.81 | dist 0/1/2/3/4/5+ % = 3/20/15/22/33/7 | mean paid $7,919 | median sess to 1st payout 62.5
- After 1st payout: gap sessions median 25.0 mean 41.0; later-payout size to you mean $3,101 median $3,150; checks after 1st: 4608; PAID 5%, consistency>40% 63%, cycle profit below min 31%
- Gross profit needed before 1st payout $5,100; reached by 68% of starts; median session reached 40 => remaining of 260: 220
- $ per 2 weeks (10 sessions): 1 acct all $172, survivors $305; 5 accts all $858, survivors $1,523

# NO payout cap (real pace)


## 25K (523 starts; buffer 26100, min req 500, caps 1000/1500, cadence 10)

**ALL** bust 57.4%
- All: n=523 payouts/yr 1.65 | dist 0/1/2/3/4/5+ % = 42/12/9/17/15/4 | mean paid $1,646
- Survivors: n=223 payouts/yr 3.04 | dist 0/1/2/3/4/5+ % = 1/11/17/34/30/8 | mean paid $3,100 | median sess to 1st payout 80
- After 1st payout: gap sessions median 40.0 mean 45.5; later-payout size to you mean $1,148 median $1,215; checks after 1st: 4728; PAID 12%, below $500 0%, consistency>40% 51%, cycle profit below min 38%
- Gross profit needed before 1st payout $1,600; reached by 62% of starts; median session reached 51 => remaining of 260: 209
- $ per 2 weeks (10 sessions): 1 acct all $63, survivors $119; 5 accts all $317, survivors $596

**H1 2021-11..2023-12** bust 58.7%
- All: n=283 payouts/yr 1.91 | dist 0/1/2/3/4/5+ % = 35/11/13/14/18/8 | mean paid $1,794
- Survivors: n=117 payouts/yr 3.21 | dist 0/1/2/3/4/5+ % = 0/8/24/23/30/15 | mean paid $3,036 | median sess to 1st payout 80
- After 1st payout: gap sessions median 30.0 mean 44.0; later-payout size to you mean $1,070 median $1,132; checks after 1st: 2742; PAID 13%, consistency>40% 40%, cycle profit below min 47%
- Gross profit needed before 1st payout $1,600; reached by 67% of starts; median session reached 56 => remaining of 260: 204
- $ per 2 weeks (10 sessions): 1 acct all $69, survivors $117; 5 accts all $345, survivors $584

**H2 2024-01..2026-10** bust 55.8%
- All: n=240 payouts/yr 1.34 | dist 0/1/2/3/4/5+ % = 49/13/5/20/13/0 | mean paid $1,472
- Survivors: n=106 payouts/yr 2.86 | dist 0/1/2/3/4/5+ % = 2/14/9/45/29/0 | mean paid $3,170 | median sess to 1st payout 70.0
- After 1st payout: gap sessions median 40.0 mean 48.1; later-payout size to you mean $1,286 median $1,350; checks after 1st: 1986; PAID 10%, below $500 0%, consistency>40% 65%, cycle profit below min 25%
- Gross profit needed before 1st payout $1,600; reached by 57% of starts; median session reached 45.5 => remaining of 260: 214.5
- $ per 2 weeks (10 sessions): 1 acct all $57, survivors $122; 5 accts all $283, survivors $610

## 50K (523 starts; buffer 52100, min req 500, caps 2000/2500, cadence 10)

**ALL** bust 44.2%
- All: n=523 payouts/yr 1.70 | dist 0/1/2/3/4/5+ % = 34/15/16/19/12/4 | mean paid $2,933
- Survivors: n=292 payouts/yr 2.77 | dist 0/1/2/3/4/5+ % = 2/13/25/32/21/7 | mean paid $4,865 | median sess to 1st payout 70
- After 1st payout: gap sessions median 30 mean 46.0; later-payout size to you mean $2,039 median $2,250; checks after 1st: 5555; PAID 10%, consistency>40% 47%, cycle profit below min 44%
- Gross profit needed before 1st payout $2,600; reached by 70% of starts; median session reached 47.0 => remaining of 260: 213.0
- $ per 2 weeks (10 sessions): 1 acct all $113, survivors $187; 5 accts all $564, survivors $936

**H1 2021-11..2023-12** bust 40.3%
- All: n=283 payouts/yr 2.06 | dist 0/1/2/3/4/5+ % = 24/15/21/17/16/7 | mean paid $3,386
- Survivors: n=169 payouts/yr 3.03 | dist 0/1/2/3/4/5+ % = 0/8/30/25/26/11 | mean paid $5,105 | median sess to 1st payout 80
- After 1st payout: gap sessions median 30 mean 44.7; later-payout size to you mean $1,994 median $2,202; checks after 1st: 3430; PAID 11%, consistency>40% 35%, cycle profit below min 54%
- Gross profit needed before 1st payout $2,600; reached by 77% of starts; median session reached 51 => remaining of 260: 209
- $ per 2 weeks (10 sessions): 1 acct all $130, survivors $196; 5 accts all $651, survivors $982

**H2 2024-01..2026-10** bust 48.8%
- All: n=240 payouts/yr 1.29 | dist 0/1/2/3/4/5+ % = 46/15/10/21/8/0 | mean paid $2,399
- Survivors: n=123 payouts/yr 2.41 | dist 0/1/2/3/4/5+ % = 4/21/19/41/15/0 | mean paid $4,534 | median sess to 1st payout 70.0
- After 1st payout: gap sessions median 40.0 mean 48.8; later-payout size to you mean $2,130 median $2,250; checks after 1st: 2125; PAID 8%, consistency>40% 65%, cycle profit below min 26%
- Gross profit needed before 1st payout $2,600; reached by 63% of starts; median session reached 40 => remaining of 260: 220
- $ per 2 weeks (10 sessions): 1 acct all $92, survivors $174; 5 accts all $461, survivors $872

## 100K (523 starts; buffer 103100, min req 500, caps 2500/3000, cadence 5)

**ALL** bust 27.5%
- All: n=523 payouts/yr 2.04 | dist 0/1/2/3/4/5+ % = 26/16/18/14/17/9 | mean paid $3,653
- Survivors: n=379 payouts/yr 2.73 | dist 0/1/2/3/4/5+ % = 4/19/23/19/23/12 | mean paid $4,924 | median sess to 1st payout 85
- After 1st payout: gap sessions median 30.0 mean 42.6; later-payout size to you mean $2,219 median $2,343; checks after 1st: 12016; PAID 6%, consistency>40% 38%, cycle profit below min 56%
- Gross profit needed before 1st payout $3,600; reached by 80% of starts; median session reached 69.0 => remaining of 260: 191.0
- $ per 2 weeks (10 sessions): 1 acct all $140, survivors $189; 5 accts all $702, survivors $947

**H1 2021-11..2023-12** bust 14.8%
- All: n=283 payouts/yr 2.43 | dist 0/1/2/3/4/5+ % = 10/20/27/16/13/14 | mean paid $4,049
- Survivors: n=241 payouts/yr 2.73 | dist 0/1/2/3/4/5+ % = 3/19/29/17/16/16 | mean paid $4,587 | median sess to 1st payout 90.0
- After 1st payout: gap sessions median 30 mean 43.2; later-payout size to you mean $2,098 median $2,193; checks after 1st: 7340; PAID 6%, consistency>40% 26%, cycle profit below min 68%
- Gross profit needed before 1st payout $3,600; reached by 90% of starts; median session reached 81.0 => remaining of 260: 179.0
- $ per 2 weeks (10 sessions): 1 acct all $156, survivors $176; 5 accts all $779, survivors $882

**H2 2024-01..2026-10** bust 42.5%
- All: n=240 payouts/yr 1.58 | dist 0/1/2/3/4/5+ % = 45/12/8/12/20/2 | mean paid $3,185
- Survivors: n=138 payouts/yr 2.74 | dist 0/1/2/3/4/5+ % = 7/19/13/22/36/4 | mean paid $5,513 | median sess to 1st payout 70
- After 1st payout: gap sessions median 35 mean 41.6; later-payout size to you mean $2,430 median $2,700; checks after 1st: 4676; PAID 5%, consistency>40% 57%, cycle profit below min 37%
- Gross profit needed before 1st payout $3,600; reached by 68% of starts; median session reached 58.5 => remaining of 260: 201.5
- $ per 2 weeks (10 sessions): 1 acct all $122, survivors $212; 5 accts all $612, survivors $1,060

## 150K (523 starts; buffer 154600, min req 500, caps 3000/3500, cadence 5)

**ALL** bust 24.5%
- All: n=523 payouts/yr 2.13 | dist 0/1/2/3/4/5+ % = 24/14/20/15/17/9 | mean paid $4,969
- Survivors: n=395 payouts/yr 2.79 | dist 0/1/2/3/4/5+ % = 3/16/26/21/23/12 | mean paid $6,539 | median sess to 1st payout 75
- After 1st payout: gap sessions median 30 mean 42.6; later-payout size to you mean $2,921 median $3,150; checks after 1st: 12622; PAID 6%, consistency>40% 42%, cycle profit below min 53%
- Gross profit needed before 1st payout $5,100; reached by 80% of starts; median session reached 66 => remaining of 260: 194
- $ per 2 weeks (10 sessions): 1 acct all $191, survivors $251; 5 accts all $956, survivors $1,257

**H1 2021-11..2023-12** bust 8.8%
- All: n=283 payouts/yr 2.60 | dist 0/1/2/3/4/5+ % = 6/17/30/18/13/15 | mean paid $5,781
- Survivors: n=258 payouts/yr 2.81 | dist 0/1/2/3/4/5+ % = 1/15/33/20/14/16 | mean paid $6,302 | median sess to 1st payout 85
- After 1st payout: gap sessions median 30.0 mean 43.1; later-payout size to you mean $2,863 median $3,150; checks after 1st: 7941; PAID 6%, consistency>40% 29%, cycle profit below min 65%
- Gross profit needed before 1st payout $5,100; reached by 94% of starts; median session reached 77 => remaining of 260: 183
- $ per 2 weeks (10 sessions): 1 acct all $222, survivors $242; 5 accts all $1,112, survivors $1,212

**H2 2024-01..2026-10** bust 42.9%
- All: n=240 payouts/yr 1.58 | dist 0/1/2/3/4/5+ % = 45/11/8/12/22/2 | mean paid $4,011
- Survivors: n=137 payouts/yr 2.75 | dist 0/1/2/3/4/5+ % = 7/18/14/21/38/3 | mean paid $6,984 | median sess to 1st payout 65.0
- After 1st payout: gap sessions median 35 mean 41.6; later-payout size to you mean $3,030 median $3,150; checks after 1st: 4681; PAID 5%, consistency>40% 63%, cycle profit below min 31%
- Gross profit needed before 1st payout $5,100; reached by 63% of starts; median session reached 51.5 => remaining of 260: 208.5
- $ per 2 weeks (10 sessions): 1 acct all $154, survivors $269; 5 accts all $771, survivors $1,343

## 150K-High (523 starts; buffer 154600, min req 500, caps 3000/3500, cadence 5)

**ALL** bust 27.9%
- All: n=523 payouts/yr 2.11 | dist 0/1/2/3/4/5+ % = 24/15/20/14/16/10 | mean paid $5,532
- Survivors: n=377 payouts/yr 2.85 | dist 0/1/2/3/4/5+ % = 1/17/27/20/23/13 | mean paid $7,551 | median sess to 1st payout 70
- After 1st payout: gap sessions median 30.0 mean 41.4; later-payout size to you mean $3,088 median $3,150; checks after 1st: 12847; PAID 6%, consistency>40% 41%, cycle profit below min 53%
- Gross profit needed before 1st payout $5,100; reached by 80% of starts; median session reached 53.0 => remaining of 260: 207.0
- $ per 2 weeks (10 sessions): 1 acct all $213, survivors $290; 5 accts all $1,064, survivors $1,452

**H1 2021-11..2023-12** bust 13.4%
- All: n=283 payouts/yr 2.54 | dist 0/1/2/3/4/5+ % = 9/17/29/16/15/14 | mean paid $6,442
- Survivors: n=245 payouts/yr 2.88 | dist 0/1/2/3/4/5+ % = 0/15/33/18/17/17 | mean paid $7,353 | median sess to 1st payout 75
- After 1st payout: gap sessions median 30.0 mean 41.6; later-payout size to you mean $3,081 median $3,150; checks after 1st: 8150; PAID 6%, consistency>40% 29%, cycle profit below min 66%
- Gross profit needed before 1st payout $5,100; reached by 91% of starts; median session reached 61 => remaining of 260: 199
- $ per 2 weeks (10 sessions): 1 acct all $248, survivors $283; 5 accts all $1,239, survivors $1,414

**H2 2024-01..2026-10** bust 45.0%
- All: n=240 payouts/yr 1.60 | dist 0/1/2/3/4/5+ % = 42/14/10/12/18/4 | mean paid $4,460
- Survivors: n=132 payouts/yr 2.81 | dist 0/1/2/3/4/5+ % = 3/20/15/22/33/7 | mean paid $7,919 | median sess to 1st payout 62.5
- After 1st payout: gap sessions median 25.0 mean 41.0; later-payout size to you mean $3,101 median $3,150; checks after 1st: 4697; PAID 5%, consistency>40% 63%, cycle profit below min 32%
- Gross profit needed before 1st payout $5,100; reached by 68% of starts; median session reached 40 => remaining of 260: 220
- $ per 2 weeks (10 sessions): 1 acct all $172, survivors $305; 5 accts all $858, survivors $1,523