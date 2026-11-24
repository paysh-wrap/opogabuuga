# Late-day leg gating, round 5 (research only, 2026-11-24; no app code changed, nothing pushed)

## Verdict
No ADOPT CANDIDATE. 0 of 8 gates pass. The UNVERIFIED leg is not gated into something better; even ungated it does not clear the random-direction control on the judge window.

## Build and reproduction
- Stream rebuilt from new_edge scripts (lastmom_day ref bar 239 = 13:29, min move 0.1 x 14-day avg range, enter 15:00 open, 60 pt stop first, flat 15:59, $2/micro RT) on /home/user/days.pkl: pick 465 trades PF 1.50 (WR 53.1 %, $7,756/micro), judge 602 trades PF 1.12 (WR 47.7 %, $3,198). Identical row-for-row to new_edge/scripts/trades_lastmom239.csv.
- NOISE stream: model_qa_scripts base.py, 654 trades, $19,293, equals streams_BASE. CANDACE: pass_faster_c125/streams_candace_base.csv.
- Sim: refine_round3 harness (patched copy harness5.py, adds the leg slot and cushion brake). Reproduces base 50K 66.3 %/61 d and 150K 74.4 %/80 d, and the late_leg_sizes built rows (50K 2 micros brake 69.7 %/51 d, $56,628; 150K 4 micros brake 70.6 %/64 d, $129,449). Sim uses the app-faithful leg (3R target, exit 15:59 bar); the stats table uses the published study leg.

## Pre-registration (chosen before looking at judge)
Gates: G1 skip if NOISE entered before 15:00; G2 skip if NOISE realized P&L before 15:00 < 0 (causal, open trade ignored); G3 NOISE flat at 15:00, NOISE traded today, and trend sign = NOISE last side (strict, so days without a NOISE trade are skipped); G4 |move| >= threshold x 14-day range, grid 0.25/0.5/0.75, pick rule "highest pick PF with pick n >= 150" gave 0.25 (pick PF 1.44, 1.24, 1.29 for the three); G5 skip if prior-day VIX (FRED VIXCLS, previous close, no lookahead) above the pick median 20.34; G6 skip Mondays; G7a entry 14:30, G7b entry 15:30. Total 8 gates (G4 had 3 grid points, so 10 looks). Added reference row G0b = the app's current rule (skip when NOISE position open at 15:00; 26 % of judge signals here: 602 to 462).
ADOPT CANDIDATE rule: PF above ungated on pick AND judge, net $ not below ungated on both, >= 60 judge trades, judge PF above random-direction p95 (2,000 sign-flip draws, same trades, flipped leg re-simulated with its own stop).

## Trade stats (per micro, $2 RT, study leg)
| gate | pick n/WR/PF/net | judge n/WR/PF/net | judge rand p95 (p) | corr NOISE+CANDACE | PF up both | net kept both | ADOPT |
|---|---|---|---|---|---|---|---|
| G0 ungated | 465/53.1%/1.502/$7,756 | 602/47.7%/1.121/$3,198 | 1.18 (0.133) | 0.109 | n | Y | no |
| G0b app rule: skip if NOISE open at entry | 333/51.7%/1.461/$5,248 | 462/47.6%/1.158/$3,222 | 1.238 (0.1325) | -0.005 | n | n | no |
| G1 skip if NOISE traded today (before entry) | 261/52.9%/1.524/$4,582 | 352/46.3%/1.071/$1,078 | 1.165 (0.1685) | -0.011 | n | n | no |
| G2 skip if NOISE realized P&L today < 0 | 368/53.3%/1.574/$6,858 | 504/46.6%/1.137/$3,016 | 1.234 (0.1925) | 0.068 | Y | n | no |
| G3 NOISE flat, traded today, trend side == NOISE last side | 77/44.2%/1.026/$85 | 104/52.9%/1.725/$3,333 | 1.92 (0.1245) | -0.011 | n | n | no |
| G4 abs move >=0.25 x 14d range | 350/53.4%/1.444/$5,211 | 456/46.7%/1.06/$1,254 | 1.221 (0.349) | 0.131 | n | n | no |
| G5 skip if prior-day VIX > pick median 20.34 | 230/52.6%/1.488/$3,064 | 499/46.7%/0.987/$-284 | 1.125 (0.3635) | 0.1 | n | n | no |
| G6 skip Mondays | 383/53.8%/1.528/$6,678 | 493/47.5%/1.117/$2,557 | 1.186 (0.1325) | 0.121 | n | n | no |
| G7a entry 14:30 | 465/47.7%/1.272/$5,642 | 602/43.2%/0.923/$-2,320 | 1.068 (0.477) | 0.175 | n | n | no |
| G7b entry 15:30 | 465/48.8%/1.065/$924 | 602/46.2%/0.991/$-202 | 1.191 (0.549) | 0.088 | n | n | no |
Key readings:
- Ungated judge PF 1.12 is inside the random-direction band (p95 1.18, p = 0.13). Pick PF 1.50 does beat it (p < 0.001). This is the same decay as before, now with the control stated.
- G2 is the only gate with higher PF on both windows (1.57 / 1.14) but it cuts net on both (-$898 pick, -$182 judge) and still fails the control; its PF gain is 8 % fewer losing days removed from a thin edge.
- G0b (what the app already does) lifts judge PF to 1.16 on fewer trades and drops daily correlation with NOISE+CANDACE from 0.11 to -0.005. That is a diversification effect, not an edge gain; pick PF falls 1.50 to 1.46 and pick net falls 32 %.
- G3 flips sign between windows (pick PF 1.03, n = 77; judge PF 1.73, n = 104): classic noise from tiny cells. G5 (VIX) is worst on judge (PF 0.99, net negative): high-VIX days were the profitable ones there. Later entries 14:30 / 15:30 lose in the judge window; 15:00 is not a robust optimum either (pick 1.27 at 14:30, 1.07 at 15:30).
- No gate shows a consistent pick-to-judge improvement. With 8 gates and ~1 effective regime stretch per year, one or two pass-looking cells would be expected by chance; none even did.

## Fast-pass eval effect (rolling starts, sim, leg at built sizes: 50K 2 micros / 150K 4 micros, 1 micro below the cushion brake)
| 50K | pass % ALL/pick/judge | median d ALL | stuck+bust ALL | profit | leg trades |
|---|---|---|---|---|---|
| no leg | 66.3/68.2/56.5 | 61 | 26.2 | $39,080 | 0 |
| G0 | 69.7/73.3/58.2 | 51 | 21.9 | $56,628 | 1067 |
| G0b | 69.4/72.8/59.1 | 53 | 22.4 | $53,969 | 795 |
| G1 | 66.3/73.1/55.7 | 49 | 29.7 | $50,150 | 613 |
| G2 | 68.5/74.6/60.3 | 46 | 27.2 | $54,980 | 872 |
| G3 | 65.7/59.8/61.6 | 55 | 27.7 | $43,450 | 181 |
| G4 | 66.5/73.5/57.3 | 51 | 29.2 | $49,058 | 806 |
| G5 | 67.7/73.3/51.6 | 57.5 | 26.1 | $44,798 | 729 |
| G6 | 65.5/65.6/56.0 | 49 | 27.6 | $53,867 | 876 |
| G7a | 47.8/62.7/36.2 | 47 | 46.9 | $46,953 | 1067 |
| G7b | 57.9/56.3/56.2 | 43 | 36.6 | $45,973 | 1067 |
| 150K | pass % ALL/pick/judge | median d ALL | stuck+bust ALL | profit | leg trades |
|---|---|---|---|---|---|
| no leg | 74.4/72.8/57.3 | 80 | 4.4 | $100,575 | 0 |
| G0 | 70.6/73.3/47.8 | 64 | 14.7 | $129,449 | 1067 |
| G0b | 71.8/73.3/49.9 | 63 | 13.7 | $129,475 | 795 |
| G1 | 72.4/73.5/50.9 | 68 | 4.6 | $122,715 | 613 |
| G2 | 69.6/73.9/46.1 | 64 | 15.8 | $127,189 | 872 |
| G3 | 67.3/72.4/44.8 | 70 | 20.7 | $108,437 | 181 |
| G4 | 68.7/73.3/44.7 | 75.5 | 16.9 | $114,309 | 806 |
| G5 | 67.5/73.3/42.3 | 69 | 18.4 | $105,143 | 729 |
| G6 | 72.8/72.9/51.6 | 66 | 14.4 | $123,927 | 876 |
| G7a | 78.5/72.6/63.8 | 92 | 9.7 | $110,262 | 1067 |
| G7b | 73.6/73.1/53.2 | 66 | 13.0 | $112,917 | 1067 |
- Ungated leg: 50K pass +3.4 pts and 10 days faster (judge +1.7); 150K pass -3.8 pts, 16 days faster, judge -9.5 (matches late_leg_sizes). G0b (app rule) is the same within 1 pt, as the sim already skips the leg while NOISE is open.
- No gate improves both plans on pass % and speed on both windows. Best looking: G1 on 150K (ALL 72.4 %, stuck+bust 4.6 %, judge 50.9 %) but 50K ALL falls to 66.3 %, judge 55.7 %, and profit drops. G6 150K 72.8 % / 66 d vs ungated 70.6 / 64 is a pass gain with 2 days slower and $5.5K less profit; on 50K G6 loses 4 pts pick. G7a 150K shows 78.5 % ALL, 63.8 % judge but median 92 d (28 slower than ungated), profit -$19K, and the leg itself is net negative in judge: that is the leg being a smaller drag, not an edge.
- Judge-window pass differences of a few points are 1-2 regimes; not evidence.

## Limits
- One 5-year dataset; pick and judge each hold few independent regimes. The gate 4 grid and "G3 strict" are interpretation choices fixed here and not tuned afterwards.
- NOISE used for gating is the base (stop 250) stream; the sim uses its own $100-stop NOISE stream, so sim NOISE-busy days differ slightly from the gate flags.
- MES in days.pkl was not used (the leg and NOISE here trade MNQ bars; NOISE's MES bands exist only in the generator).
- Nothing adopted; keep the leg as it is (unverified, optional) until the user decides.

Files: scripts/{lib_ne,research,build_stream,gates,harness5,sims,sim_smoke}.py, scripts/trades_late_rebuilt.csv, scripts/legsets/*.csv, gates_results.json, sim_results.json.
