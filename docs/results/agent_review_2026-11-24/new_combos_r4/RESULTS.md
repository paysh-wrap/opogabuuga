# Round 4 (agent B): entry quality, win rate, new combinations (2026-11-24, research only; no app code changed)
Data: /home/user/days.pkl MNQ (+MES) 1-min RTH. NOISE = built stream ($100 stop, lock 100/10, max 3/day, Mondays skipped, from refine_round3), CANDACE = base stream ($125/micro risk cap), per micro-unit, $2 RT cost in. Pick 2021-10..2023-12, judge 2024-01..2026-10. Thresholds (top-20 % cut-offs) frozen from pick quantiles only: vwap dist 75.8 bp, prior-day range ratio 1.258, move-from-open 0.731 x avg range. Control: for filters, 1,000 random skips of the same fraction (p95 PF / win); for new legs, 200 random-direction runs (p95 judge net). Script run_r4.py, data results_r4.json.
Rule (set before running): ADOPT CANDIDATE only if win AND PF AND net improve on pick AND judge, judge n >= 60, beats random p95, no profit cut. Variants counted: **15** (a1-a5, b1, b2, d1, e1, e2, c1-c4, plus one dropped duplicate b-variant = 15 tries; ~1.5 false wins expected at 10 %).

## NOISE filters / combos (base pick 327 tr 43.4 % PF 1.48 $7,399; judge 413 tr 43.3 % PF 1.50 $10,226)
| variant | pick n/win/PF/net | judge n/win/PF/net | judge ctrl p95 PF/win | verdict |
|---|---|---|---|---|
| a1 skip prior-day range top 20 % | 261/44.4/1.60/6,986 | 312/42.3/1.62/9,685 | 1.69/45.7 | REJECT (net down, win down on judge, inside control) |
| a2 skip VWAP distance top 20 % | 261/42.5/1.35/4,258 | 375/43.7/1.52/9,406 | 1.61/44.6 | REJECT |
| a3 skip first-hour trend disagree | 285/44.9/1.61/7,918 | 386/43.3/1.42/8,130 | 1.58/44.4 | REJECT (pick only) |
| a4 skip move-from-open top 20 % | 261/42.5/1.40/4,888 | 328/44.5/1.68/10,536 | 1.67/45.3 | REJECT (judge only; pick -34 % net) |
| a5 skip MES disagree | 321/43.3/1.48/7,207 | 402/43.8/1.50/9,946 | 1.55/44.0 | REJECT (inert) |
| b1 skip NOISE if CANDACE opposite | 269/43.9/1.39/5,028 | 346/43.4/1.52/9,133 | 1.65/45.1 | REJECT (cuts profit) |
| b2 NOISE only on CANDACE days | 84/39.3/1.52/2,003 | 87/41.4/1.13/526 | 2.28/50.6 | REJECT |
| d1 half size if CANDACE opposite (shrink-only) | 327/43.4/1.44/6,213 | 413/43.3/1.51/9,680 | - | REJECT (cuts profit) |

## CANDACE refinements (base pick 160 tr 40.6 % PF 1.27 $1,030; judge 150 tr 37.3 % PF 1.18 $814)
| e1 skip 09:58-10:05 entries (narrow 10:00-release blackout) | 134/40.3/1.25/846 | 129/37.2/1.14/571 | 1.34/39.8 | REJECT (narrow sweep still cuts ~18-30 %) |
| e2 A/B grades only | 13/61.5/2.29/246 | 11/27.3/0.57/-134 | - | REJECT (n far too small) |

## New third-leg candidates (1 micro, $100 stop, $2 RT)
| leg | pick n/win/PF/net | judge n/win/PF/net | judge random p95 net | corr N / C | per-year | verdict |
|---|---|---|---|---|---|---|
| c1 fade 14:00-15:00 move >0.25 % | 199/35.2/0.62/-4,081 | 144/43.8/1.41/3,058 | 2,352 | -0.09 / -0.01 | 2021-23 negative, 2024-26 positive | REJECT (sign flips pick vs judge) |
| c2 gap fade >0.3 %, 09:35-11:00 | 306/33.3/1.02/444 | 344/28.8/0.97/-730 | 2,120 | -0.02 / -0.02 | mixed | REJECT |
| c3 10:30 break of 09:30-10:00 range, hold to 12:00 | 230/49.1/1.34/3,510 | 275/40.0/1.21/3,126 | 5,035 | +0.18 / -0.03 | 2025-26 flat/negative | REJECT (below random control; correlated with NOISE) |
| c4 MNQ toward MES on divergence at 11:00 | 70/35.7/0.74/-1,066 | 72/22.2/0.49/-2,676 | 3,693 | ~0 | every year negative except 2022 | REJECT |

## Not tested / limits
- (f) late-day leg gating: the late-day leg is not in the verified streams (same gap as rounds 2-3), so not tested.
- last30days fresh-idea pass and FRED/news calendar not run (time); e1 used a fixed time window, not a real release calendar.
- Funded consistency (40 %/35 % best-day rules): no filter here raised win rate without cutting profit, so none can smooth days for free; the cheapest smoothing remains the existing size/brake rules (agent A's area).

## Plain recommendation
0 ADOPT CANDIDATES out of 15. Every filter that lifts win rate or PF on one window loses it on the other or cuts net profit, and all sit inside the random-skip control. Keep NOISE + CANDACE entries as built; do not add a third leg from c1-c4. Only c1 (late-afternoon fade) is worth a watch-list note: positive 2024-26 but negative 2021-23, so it would be a regime bet, not an edge. Nothing adopted without the user.
