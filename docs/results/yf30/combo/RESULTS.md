# yf30 combo: NOISE + CANDACE + LATE-DAY momentum on MNQ (research only, 2026-11-23)

**30 days (24 complete RTH sessions, 2026-10-20 to 2026-11-20) cannot prove an edge.** Trade counts are 10 / 14 / 22, the settings
were chosen earlier on this same window, and the whole result leans on ONE day (2026-11-05, MNQ fell ~1,200 pt: NOISE short +$1,575, late-day short +$740 per micro).
Yahoo `MNQ=F` is a spliced front month, not Databento; no held-out data.

## Setup
Same data/costs/engines as yf30 (`../scripts`, 2-min bars, $2.00 RT cost per micro). Legs: NOISE $250 stop, lock 100/10, Mondays off, min hist 10;
CANDACE as yf30 MNQ (stop cap 40 pt, window 08:20-11:00, hold 30 min, gap tol 5); LATE-DAY = sign of 09:30-13:30 trend (min-move filter as new_edge), enter 15:00 open, 60 pt stop, flat 15:59 bar close.
Merge: trades ordered by entry bar (tie NOISE, CANDACE, LATE); a trade is skipped if another accepted trade is open (POSITION_OPEN) or the open trade is on the opposite side (HEDGE_LOCK).
- (a) one account: any overlap skips.
- (b) LATE on its own account: LATE only skips for an opposite open NOISE/CANDACE trade (and vice versa); NOISE/CANDACE still share one account.
Approximation: a skipped trade does not change the leg's own later state (e.g. NOISE entry counter). 1 micro unless stated.

## Per leg and combined (net $ per 1 micro)
| set | trades | win % | PF | net $ | max DD $ |
|---|---|---|---|---|---|
| NOISE standalone | 10 | 50.0 | 2.19 | +972 | 567 |
| CANDACE standalone | 14 | 42.9 | 2.04 | +370 | 140 |
| LATE standalone | 22 | 36.4 | 1.46 | +696 | 711 |
| (a) NOISE in combo | 10 | 50.0 | 2.19 | +972 | 567 |
| (a) CANDACE in combo | 14 | 42.9 | 2.04 | +370 | 140 |
| (a) LATE in combo | 19 | 36.8 | 1.16 | +200 | 711 |
| **(a) COMBO one account** | 43 | 41.9 | 1.64 | +1,541 | 612 |
| **(b) COMBO late on separate account** | 46 | 41.3 | 1.76 | +2,037 | 690 |

Skips: (a) LATE 3 x POSITION_OPEN (a NOISE/CANDACE position was still open at 15:00); no HEDGE_LOCK skips in either model. (b) none.
(Maxdd is trade-by-trade equity, not intraday.)

Daily P&L correlation (24 sessions): (a) NOISE-CANDACE -0.04, NOISE-LATE -0.02, CANDACE-LATE +0.27. (b) NOISE-CANDACE -0.04, NOISE-LATE **+0.67** (the 11-05 day: both short), CANDACE-LATE +0.19. Mostly one outlier day, so the 0.67 is not stable.

Random-direction p-value for the combo (same entry/exit bars and stops, coin-flip direction, 2,000 draws; p = share of draws with net >= actual):
(a) +1,541 vs random mean -16, 95th pct +1,939, **p = 0.11**; (b) +2,037 vs mean +289, 95th pct +2,466, **p = 0.09**. Not significant.

## Lucid eval-style sim (one window, EOD drawdown, trail/lock, consistency 40 %, >=3 profitable days, day stop 38 % of target; 50K DLL $1,200 is assumed, not read from the plan file)
Sizes: "1 micro" = every leg 1 micro. D157/D163 sizes: 25K NOISE 1, CANDACE 2 (1 below $333 cushion); 50K NOISE 2 (1 below $667), CANDACE 4 (3 below $1,000), LATE 1. These sizes were tuned for different NOISE/CANDACE settings ($75 stop) and are applied here to the $250 legs as a scale only.

| account / model | (a) one account | (b) late separate |
|---|---|---|
| 25K 1 micro (target $1,250) | profit +$1,541 (123 %), best day 102 % of profit: **target hit, consistency FAIL, not passed** | +$1,297 (104 %), best day 121 %: **not passed** (consistency) |
| 25K D157 N1/C2 | +$1,911 (153 %), best day 82 %: not passed (consistency) | +$1,667 (133 %), 95 %: not passed |
| 50K 1 micro (target $3,000) | +$1,541 (51 %): target not reached | +$1,297 (43 %): not reached |
| 50K D163 N2/C4 | +$3,622 (121 %), best day 87 %: target hit, consistency FAIL | +$3,378 (113 %), 93 %: consistency FAIL |

No account busted (MLL never touched). **Nothing "passed"**: the dollar target was reached on 25K (all sizings) and on 50K at D163 size, but a single day (2026-11-05) is 82-121 % of the profit, far above the 40 % consistency cap; the 38 % day stop did not help because that day was one NOISE trade held to the 16:00 flat. With a different day order or the day stop actually cutting the trade, it might pass; this is one window and one outlier.

## Honest read
Combining reduces nothing dramatic: the legs are nearly uncorrelated (except the single big day), PF 1.64 to 1.76 and p 0.09 to 0.11 are what you would see from a favourable 24 sessions by chance about 1 time in 10. LATE adds little once forced to skip (PF 1.16 in model a). 30 days ~ 22-24 sessions cannot prove an edge; nothing here should change app behavior.

Files: `combo.py` (run: `PYTHONPATH=backend:docs/results/yf30/scripts <yfvenv>/bin/python docs/results/yf30/combo/combo.py`), `results.json` (includes accepted trade lists). Not committed.
