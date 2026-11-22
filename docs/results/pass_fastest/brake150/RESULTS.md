# Pro 150K EVALUATION: where to put the brake (research only, 2026-11-22)

User question: "see what happens when you reduce to 4 micros instead of 2, and only do 2 micros if you get down to $1,500 left".
Simulator: `../sim150.py` unchanged on disk, plus two extra size bands added in memory by `brake150.py` (NOISE bands, CANDACE bands).
All Lucid rules on, the same as pass_fastest: EOD MLL + lock, DLL incl. LucidScale, consistency + day stop, kill distance + room check, D57 shrink,
one position at a time, no hedge, flat by close. 1,252 rolling starts over 5 years. C40 = 40 % consistency with a 38 % day stop. C50 = 50 % with a 48 % day stop.
Cushion = equity − MLL floor (max $4,500). "$1,500 left" = cushion < 0.3333 × MLL.

Rows (NOISE @ $100 stop, base NOISE 4 + CANDACE 3 fixed micros, at most 4 micros open since only one position is open at a time):
- REC: NOISE 2 below $2,250 (50 %); CANDACE always 3. This is the pass_fastest recommendation, and it reproduces exactly.
- U1 (the user's idea): no cut until $1,500; below that, NOISE 2 and CANDACE 2.
- U2: below $2,250, NOISE 3 and CANDACE 3; below $1,500, both 2.
- U3: like U1, but only NOISE is cut (CANDACE stays 3).
- BASE (reference for ROBUST): today's NOISE 3 @ $250 + brake 2 below 50 %.

ROBUST = 5-year pass ≥ 70 %, judge pass ≥ BASE judge − 3 and pick pass ≥ BASE pick − 5. Profit = plan-sized static replay. It does not depend on the brake, so it is the same for every row.

**C40** (ROBUST: judge ≥ 56.3, pick ≥ 60.1)

| row | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ | ROBUST |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 77.1 | 10.5 | 5.8 | 159 | 187 (12 %) | 65.1 | 59.3 | 3.8 | 57,879 | YES |
| REC | 79.1 | 9.8 | 9.3 | 111 | 155 (11 %) | 68.7 | 63.7 | 7.5 | 78,612 | YES |
| U1 | 78.8 | 12.2 | 9.3 | 109 | 150 (9 %) | 67.1 | 64.5 | 7.5 | 78,612 | YES |
| **U2** | **80.4** | 10.1 | 9.3 | 112 | 153 (10 %) | 69.5 | 65.4 | 7.5 | 78,612 | YES |
| U3 | 72.6 | 18.5 | 9.3 | 102 | 144 (9 %) | 67.1 | 53.8 | 7.5 | 78,612 | no |

**C50** (ROBUST: judge ≥ 56.7, pick ≥ 60.1)

| row | pass 5y | stuck | <=60d | median d | chain days (cens) | pick pass | judge pass | judge <=60d | profit $ | ROBUST |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 77.3 | 10.5 | 5.8 | 158 | 186 (12 %) | 65.1 | 59.7 | 3.8 | 57,879 | YES |
| REC | 79.9 | 9.8 | 9.7 | 110 | 153 (10 %) | 68.7 | 65.1 | 8.1 | 78,612 | YES |
| U1 | 79.6 | 12.2 | 9.7 | 107 | 146 (8 %) | 67.1 | 66.0 | 8.1 | 78,612 | YES |
| **U2** | **81.3** | 10.1 | 9.7 | 109 | 150 (9 %) | 69.5 | 67.1 | 8.1 | 78,612 | YES |
| U3 | 73.5 | 18.4 | 9.7 | 101 | 143 (8 %) | 67.1 | 55.3 | 8.1 | 78,612 | no |

## Findings
- The brake setting does not change "<=60d" at all (9.3 % C40 / 9.7 % C50 in every row). An account that passes within 60 days almost never drops to a $2,250 cushion.
  The brake only decides the fate of the slow accounts: whether they pass later or get stuck.
- U1 (the user's idea) is about the same as REC. Pass is −0.3 pts and judge +0.8, but stuck is +2.4 pts and pick −1.6. It is slightly quicker for the accounts that do pass
  (median −2 d, chain −5 d, because they trade full size longer). ROBUST: yes.
- U3 (cut only NOISE, CANDACE stays 3 down to $1,500) is not robust. Judge drops to 53.8 / 55.3 and stuck rises to 18.5 %. CANDACE at 3 micros on a thin cushion is what breaks accounts.
- U2 (a step-down: 3/3 below $2,250, then 2/2 below $1,500) is the best on every pass measure: pass +1.3 / +1.4 pts vs REC, judge +1.7 / +2.0, pick +0.8. Stuck is +0.3.

## Recommendation
**U2** (both C40 and C50). Its <=60d ties with REC and U1, it has the highest pass % (80.4 C40 / 81.3 C50), it is ROBUST, and profit is unchanged ($78,612).
If code for a two-step NOISE brake is not wanted: REC (config-only NOISE brake) is the runner-up on pass %. U1 trails REC by 0.3 pts and needs code anyway (the CANDACE brake).

## Config-only vs code
- REC NOISE brake: config-only (`size_table_eval` 150K row `brake_below: 0.5, brake_contracts: 2`, with the D133 cap lifted to 4).
- U1 / U3 NOISE brake: config-only, `brake_below: 0.3333, brake_contracts: 2`. The cut then happens below $1,499.85; `<` is strict, as in risk/strategy_sizing.py.
- U2 NOISE two-step (3 below 0.5, 2 below 0.3333): **needs code**. SizeTierCfg has only one brake_below/brake_contracts pair.
- CANDACE 3 fixed micros (every row): **needs code**, as in pass_fastest. Today CANDACE is sized by its Lucid fit.
- CANDACE brake (U1, U2; 2 micros below $1,500): **needs code**. CANDACE has no brake today.

Files: `brake150.py` (driver), `results.json` (raw numbers).
Run: `cd backend && PYTHONPATH=. /usr/local/bin/python3 ../docs/results/pass_fastest/brake150/brake150.py`.
