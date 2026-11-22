# Final speed search (research only, 2026-11-22)

Same sim as pass70 (sim150.py + brake150 bands, C40 day stop 38 %, DLL ON, EOD MLL, 1 position/account, no hedge).
Built D162 rows reproduced exactly: 150K 76.4 % / 82 d, 100K 71.4 % / 87 d, 50K 66.3 % / 62 d, 25K 61.8 % / 56.5 d.
Rule: floor (70 % 100K/150K, 62 % 25K/50K), judge 2024-26 >= built-3, pick 2021-23 >= built-5, profit >= built, median STRICTLY below built.

New knobs tried (200 configs, single changes + pairs of feasible changes): CANDACE size grow (+1 per $ cushion), day lock 0.4-0.8 and
day lock on CANDACE too, NOISE lock 80-120 pt, brake bands shifted x0.75-1.25 (both / one strategy), size +/-1, weekday skips
(NOISE or CANDACE, each weekday), near-target taper.

| plan | row | pass % | median d | judge | pick | profit |
|---|---|---|---|---|---|---|
| 150K | built N5@$100 + C5, grow, dl 0.7 | 76.4 | 82 | 58.0 | 72.8 | $100.6K |
| 150K | best new: + CANDACE grow +1 per $1,500 cushion, max 6 | 74.4 | 80 | 57.3 | 72.8 | $100.6K* |
| 100K | built N3@$100 + C3, dl 0.5 | 71.4 | 87 | 65.8 | 68.9 | $60.3K |
| 100K | no improvement (every faster row breaks the 70 % floor and judge) | - | - | - | - | - |
| 50K | built N2@$75 + C4 (3 < $1,000), dl 0.5, lock 80 | 66.3 | 62 | 56.5 | 68.2 | $39.1K |
| 50K | best new: CANDACE 5 micros (still 3 < $1,000) | 64.4 | 59 | 56.3 | 65.3 | $40.9K |
| 50K | alt, no pass loss: day lock 0.4 (was 0.5) | 66.3 | 61 | 56.5 | 68.2 | $39.1K* |
| 25K | built N1@$75 + C2 (1 < $333) | 61.8 | 56.5 | 54.6 | 62.5 | $19.3K |
| 25K | no improvement under the strict rules (see note) | - | - | - | - | - |

\* static profit does not model grow / day lock; the 50K C5 row's profit is real (more CANDACE size).

Notes
- 150K: 2 d faster for 2 pts less pass; floor and robustness held. Marginal; needs code (CANDACE grow field).
- 50K: C5 = 3 d faster, -1.9 pts pass, +$1.8K profit; config-only change of the CANDACE size (bands unchanged). Day lock 0.4 = 1 d faster, no pass change, config-only.
- 25K: "skip CANDACE on Tuesday" gives 63.5 % / 52 d (judge 56.6, pick 64.5) but cuts profit (Tuesday CANDACE is +36 pts over 5 years)
  and is a weekday pick from the data itself, so it is NOT adopted. Every other faster 25K row breaks the floor and judge.
- 100K: any extra size (NOISE 4, CANDACE grow, looser brakes) drops pass to 51-62 %.

Files: final.py (sim patch + search; `base|search|combo`; run from backend/ with PYTHONPATH=.), report.py (tables), results.json.
Sim data and parent scripts are read from the main checkout's docs/results/pass_fastest (PF in final.py).
