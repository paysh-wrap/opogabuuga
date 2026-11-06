# Results K: MNQ Scalp mode on real CME 1-minute data (Databento), 2026-11-06

**Setup:** Pro 25K plan (`config/rules/lucid_pro_25k.yaml`, osc_strength_min 20), `--scalp`, NEUTRAL bias. Each month is a fresh $25K account.
**Data:** `data/futures/mnq_databento_1m.csv`, split into monthly files, covering 2024-01 → 2026-11-05 (35 months, about 750 sessions).
**Periods:**
- Main period (last 12 months): H1 = 2025-11..2026-04 and H2 = 2026-05..2026-11.
- Out-of-sample (OOS) check: 2024 and 2025-01..10. No rule was chosen using this period.

Cells read: trades · trades/day · win % · PF · net $ · max DD $.

**Method:**
- The baseline comes from the app's own engine (`research_scalp.py`, the same as `backtest.py --scalp`).
- Variants come from `tools/scalpsim.py`. It is an offline replica of SimAdapter, the OrderManager, the scalp time stop and the day rules. On 2026-10 it reproduced the engine's 21 trades exactly and the P&L to the cent on 20 of them.
- Across 12 months the replica gives 188 trades and −$527. The engine gives 195 trades and −$638. The gap comes from the engine resizing risk as the balance changes, which the replica does not do.
- Variant plans live in `tools/` and the scratchpad only. No config or code was changed.

**Engine facts found along the way:**
- Every trade was TIGHT. With a risk base of about $1,000 the account is TIGHT-only, so STD signals are never taken.
- A limit order fills on the first bar or not at all.
- Many fills are marketable limits that fill better than the plan entry. The stop and target stay at the plan prices.
- About 60% of trades are 1 contract. Those get the 0.30R lock and never get a runner.
- The 60 s time stop closes about half of all trades at the close of the next bar.

## 1. Baseline (engine)
| period | trades | /day | win | PF | net $ | max DD $ |
|---|---|---|---|---|---|---|
| H1 2025-11..2026-04 | 103 | 0.79 | 50% | 0.80 | −282 | 477 |
| H2 2026-05..2026-11 | 92 | 0.66 | 39% | 0.67 | −356 | 456 |
| OOS 2024 | 241 | 0.90 | 45% | 0.96 | −99 | 611 |
| OOS 2025-01..10 | 192 | 0.86 | 42% | 0.67 | −728 | 813 |

The 22-session Yahoo result (6 trades, 83% win) does not hold up. On 7× more real data, MNQ Scalp has about a 45% win rate, PF 0.7–0.96, and loses money in every half-period.

## 2. Raising the win rate while keeping the trade count (sim)
| variant | H1 | H2 | OOS 2024 | OOS 2025 |
|---|---|---|---|---|
| baseline | 98·0.75·51%·0.90·−126·375 | 90·0.65·40%·0.65·−401·506 | 223·0.84·46%·0.97·−77·603 | 190·0.86·43%·0.74·−594·728 |
| structure break required | 29·0.22·55%·0.43·−291 | 29·0.21·48%·1.10·+31 | 69·0.26·45%·1.50·+286 | 58·0.26·45%·0.58·−254 |
| osc-strength item > 0 | 75·0.58·48%·1.06·+58 | 66·0.47·36%·0.52·−423 | 172·0.64·47%·0.81·−348 | 145·0.65·42%·0.75·−460 |
| C1 ≥ 0.8×ATR | 78·0.60·55%·1.30·+240 | 58·0.42·38%·0.72·−181 | 185·0.69·46%·0.92·−146 | 148·0.67·45%·0.81·−332 |
| stop buffer +1.0×ATR(1m) | 70·0.54·50%·1.00·+3 | 58·0.42·38%·0.57·−234 | — | — |
| entry 0.1R deeper | 92·0.71·49%·1.00·+4 | 79·0.57·38%·0.66·−369 | — | — |
| BE after +0.5R | 97·0.75·49%·0.86·−182 | 90·0.65·39%·0.69·−341 | 223·0.84·42%·0.89·−248 | 189·0.85·39%·0.68·−690 |
| time stop 5 min (max_hold_s 300) | 98·0.75·51%·1.01·+11 | 95·0.68·49%·0.82·−242 | 224·0.84·52%·0.92·−253 | 191·0.86·52%·0.74·−858 |
| skip 07 + 13 ET (picked on 12 m) | 78·0.60·55%·1.15·+132 | 69·0.50·42%·0.87·−93 | 165·0.62·44%·0.82·−342 | 128·0.58·46%·0.79·−328 |
| skip 07 + 13, time stop 5 min | 78·0.60·55%·1.25·+245 | 69·0.50·51%·0.96·−33 | 167·0.63·49%·0.77·−649 | 129·0.58·51%·0.69·−731 |
| skip 07, 5 min, C1 ≥ 0.8×ATR (best on 12 m) | 70·0.54·59%·1.46·+346·236 | 55·0.40·55%·1.15·+90·156 | 166·0.62·51%·0.85·−367 | 127·0.57·54%·0.82·−393 |

Other results:
- Score ≥ 80 leaves about 3 trades per half.
- A smaller or larger target (0.3–1.0R) and turning off the lock both make results worse.
- The full hour table is in `tools/k_out/rep12.txt`.

**Answer:**
- A longer time stop (2–5 min, which is within the 25–300 s bounds) is the one change that raises the win rate everywhere: 40–46% becomes 49–52% at the same trade count. It does not improve PF, because the extra wins are small and the stops are full −1R.
- The best combination on the last 12 months reached 59%/55% win with PF 1.46/1.15, at 0.4–0.54 trades/day. It fails out of sample (PF 0.85/0.82, −$760). Those hour and range filters are overfit.
- No filter tested is profitable in all four periods.

## 3. Asian session (18:00–02:00 ET added; separate engine run on the last 12 months)
| variant | H1 | H2 (to 2026-10) |
|---|---|---|
| engine, normal + Asia | 205·1.58·52%·0.88·−278·584 | 172·1.27·40%·0.57·−886·939 |
| sim, normal hours only | 98·0.75·51%·0.90·−126 | 89·0.66·40%·0.65·−393 |
| sim, Asia only | 95·0.73·48%·0.75·−212 | 96·0.71·35%·0.46·−583 |

Asia doubles the trade count but lowers the win rate (48%/35%) and more than doubles the losses. No Asian hour is positive in both halves. **Leave it out.**

## 4. Holding winners (sim)
| management | H1 | H2 | OOS 2024 | OOS 2025 |
|---|---|---|---|---|
| fixed 0.5R TP on all contracts | 97·48%·0.76·−313 | 90·41%·0.62·−404 | 223·45%·0.84·−349 | 188·41%·0.70·−621 |
| **current**: half at 0.5R, half runner (2R target, 0.5R trail), ≥2 contracts only | 98·51%·0.90·−126 | 90·40%·0.65·−401 | 223·46%·0.97·−77 | 190·43%·0.74·−594 |
| runner trail 1.0R | 98·51%·0.95·−66 | 90·40%·0.71·−335 | 223·46%·1.00·+9 | 190·43%·0.77·−513 |
| runner on 1-contract trades too (3R, 1.0R trail) | 98·44%·0.80·−271 | 90·34%·0.63·−476 | 221·43%·1.07·+153 | 190·39%·0.70·−690 |
| no time stop, fixed 0.5R | 99·51%·0.91·−140 | 92·51%·0.84·−210 | 223·50%·0.81·−627 | 189·50%·0.73·−886 |

**Answer:**
- Holding a runner is better than a fixed take-profit in all four periods, by about $90–270 per half.
- A wider 1.0R trail is the best single management change, but it is still negative.
- Making 1-contract trades all-runner lowers the win rate and is inconsistent.
- Holding winners reduces losses but does not make the mode profitable.

## Recommendation
- **Do not trade MNQ Scalp on the Pro 25K plan as it is now.** Across 35 months the engine loses in every half-period, with PF 0.67–0.96.
- **Do not add the Asian session.**
- **Lowest-risk improvements, if Scalp stays available as a mode:**
  - `max_hold_s` 120–180: win rate 49–51%, trade count unchanged.
  - `trail_r` 1.0: best PF in every period.
  - Both are within the existing bounds. Neither is enough to make the mode profitable.
- **Do not adopt the hour or C1-range filters.** They fail out of sample.
- **Next research step:** the scalp entry is the real problem. Marketable limit fills put the stop very close, and 1-contract trades take full −1R losses.

**Files:**
- Tools: `tools/research_scalp.py`, `tools/scalpsim.py`, `tools/k_report.py`, `tools/k_combos.py`, `tools/k_plan_asia.yaml`
- Raw outputs: `tools/k_out/`
