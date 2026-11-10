# Pro 25K eval: total worst case per trade ~$450 (micros x stop) under the LIVE D57 rule (MNQ 5y, 2021-11 to 2026-10)

Script: /tmp/claude-0/-home-user-opogabuuga/528f0293-22e9-5e48-80a8-65343eb6ade7/scratchpad/agentP/sweep.py (`sweep.py verify`, `sweep.py run [name filter]`); raw numbers results.json, full table table.md (94 configs, runs in 45 s).
Simulator = live_stop_eval25k.py unchanged except: stop per micro is a config parameter (stop points = (usd-2)/2, tick-rounded), win rate / avg win / avg loss of executed trades are recorded (per trade, all micros, 120-session horizon runs).
Verification: fixed 124-pt stop reproduces trades_main.csv (1,291 trades, $25,345.27, 0/1,111 day mismatches); 4x$250 rows reproduce the previous report exactly (L60 taper 25.1% / chain 55; R40 33.2% / 35; NO 52.4% / 11).
Rule labels: L60 = live (allowed = 0.6 x room, room = equity - floor - $100; stop tightened, skip if stop < 0.2% of price); R40 = allowed = room - $40; NO = no tightening (study assumption, NOT live: those rows bust 34-65%).
"taper50" = full micros until < 50% of the $1,250 target remains, then 1 micro. Eval: $1,250 target, EOD trailing MLL $1,000, lock 26,100 -> floor 25,100, no DLL, >= 1 profitable day, 120 sessions, 593 starts every 2 sessions. Value = pass% x $1,646. STALL = 20 sessions without an executed trade. Chain = sessions to first pass with restarts on BUST/STALL.

## 1. Total worst case ~$450, all variants (taper50 unless noted)
| config | rule | pass | bust | stall | med / p75 | chain med | skip | win rate | avg win / loss | value | era1 pass/chain | era2 pass/chain |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3x$150 taper50 | L60 | 31.2% | 0.0% | 68.8% | 8 / 15 | 42 | 81% | 46.4% | $292 / $-199 | $514 | 35% / 39 | 28% / 44 |
| 3x$150 taper50 | R40 | 36.6% | 0.0% | 63.4% | 8 / 15 | 34 | 77% | 46.5% | $301 / $-210 | $602 | 40% / 35 | 33% / 34 |
| 3x$150 taper50 | NO | 48.7% | 51.3% | 0.0% | 10 / 18 | 16 | 0% | 46.7% | $302 / $-218 | $802 | 54% / 17 | 44% / 16 |
| 3x$150 notaper | L60 | 22.8% | 0.0% | 77.2% | 4 / 6 | 52 | 88% | 44.3% | $428 / $-283 | $375 | 27% / 50 | 19% / 54 |
| 3x$150 notaper | R40 | 30.0% | 0.0% | 70.0% | 5 / 8 | 37 | 84% | 45.3% | $432 / $-293 | $494 | 31% / 41 | 29% / 34 |
| 3x$150 notaper | NO | 41.3% | 58.7% | 0.0% | 6 / 10 | 13 | 0% | 45.9% | $419 / $-301 | $680 | 42% / 14 | 40% / 12 |
| 2x$225 taper50 | L60 | 34.1% | 0.0% | 65.9% | 14 / 21 | 45 | 71% | 47.8% | $228 / $-167 | $561 | 38% / 50 | 30% / 43 |
| 2x$225 taper50 | R40 | 39.8% | 0.0% | 60.2% | 15 / 23 | 40 | 67% | 49.0% | $229 / $-171 | $655 | 41% / 44 | 39% / 37 |
| 2x$225 taper50 | NO | 53.5% | 46.5% | 0.0% | 18 / 27 | 24 | 0% | 49.5% | $230 / $-179 | $880 | 56% / 25 | 51% / 24 |
| 2x$225 notaper | L60 | 29.5% | 0.0% | 70.5% | 9 / 13 | 46 | 77% | 46.8% | $288 / $-205 | $486 | 30% / 51 | 29% / 42 |
| 2x$225 notaper | R40 | 36.1% | 0.0% | 63.9% | 10 / 14 | 39 | 73% | 48.5% | $290 / $-213 | $594 | 35% / 44 | 37% / 34 |
| 2x$225 notaper | NO | 46.4% | 53.6% | 0.0% | 12 / 19 | 20 | 0% | 48.6% | $276 / $-217 | $764 | 47% / 21 | 46% / 19 |
| 4x$112 taper50 | L60 | 24.5% | 0.0% | 75.5% | 4 / 11 | 55 | 88% | 41.9% | $385 / $-231 | $403 | 31% / 42 | 18% / 70 |
| 4x$112 taper50 | R40 | 31.2% | 0.0% | 68.8% | 6 / 13 | 42 | 82% | 42.5% | $369 / $-236 | $514 | 35% / 40 | 27% / 43 |
| 4x$112 taper50 | NO | 46.7% | 53.3% | 0.0% | 8 / 15 | 13 | 0% | 43.4% | $375 / $-240 | $769 | 52% / 12 | 42% / 13 |
| 4x$112 notaper | L60 | 19.9% | 0.0% | 80.1% | 3 / 4 | 69 | 92% | 40.7% | $571 / $-339 | $328 | 27% / 48 | 14% / 108 |
| 4x$112 notaper | R40 | 27.0% | 0.0% | 73.0% | 3 / 5 | 48 | 89% | 41.8% | $559 / $-355 | $444 | 30% / 49 | 24% / 46 |
| 4x$112 notaper | NO | 40.8% | 59.2% | 0.0% | 4 / 8 | 10 | 0% | 42.2% | $581 / $-360 | $672 | 42% / 9 | 39% / 10 |
| 6x$75 taper50 | L60 | 17.2% | 0.0% | 82.8% | 2 / 6 | 93 | 92% | 34.8% | $509 / $-243 | $283 | 20% / 88 | 15% / 106 |
| 6x$75 taper50 | R40 | 23.8% | 0.0% | 76.2% | 2 / 8 | 63 | 89% | 35.2% | $524 / $-244 | $391 | 32% / 43 | 16% / 90 |
| 6x$75 taper50 | NO | 40.3% | 59.7% | 0.0% | 4 / 10 | 10 | 0% | 35.4% | $505 / $-253 | $664 | 47% / 9 | 34% / 12 |
| 6x$75 notaper | L60 | 15.2% | 0.0% | 84.8% | 2 / 2 | 88 | 96% | 34.5% | $858 / $-408 | $250 | 18% / 88 | 13% / 90 |
| 6x$75 notaper | R40 | 20.7% | 0.0% | 79.3% | 2 / 3 | 69 | 93% | 34.8% | $866 / $-403 | $341 | 27% / 48 | 15% / 90 |
| 6x$75 notaper | NO | 37.3% | 62.7% | 0.0% | 3 / 5 | 7 | 0% | 35.2% | $824 / $-409 | $614 | 42% / 7 | 33% / 8 |

## 2. References and other totals (taper50 where q>1, L60 live rule; R40 and NO in the second block)

| config | total | rule | pass | bust | stall | med / p75 | chain med | skip | win rate | avg win / loss | value | era1 pass/chain | era2 pass/chain |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1x$250 notaper | $250 | L60 | 55.5% | 0.0% | 43.7% | 35 / 55 | 59 | 34% | 50.7% | $144 / $-111 | $913 | 65% / 56 | 47% / 66 |
| 1x$350 notaper | $350 | L60 | 49.6% | 0.0% | 50.4% | 30 / 46 | 59 | 41% | 50.6% | $143 / $-112 | $816 | 50% / 60 | 49% / 58 |
| 1x$450 notaper | $450 | L60 | 47.9% | 0.0% | 52.1% | 31 / 47 | 61 | 41% | 50.8% | $143 / $-114 | $788 | 49% / 61 | 47% / 60 |
| 2x$175 taper50 | $350 | L60 | 36.8% | 0.0% | 63.2% | 14 / 21 | 44 | 68% | 48.0% | $225 / $-162 | $605 | 38% / 54 | 35% / 39 |
| 3x$117 taper50 | $351 | L60 | 28.3% | 0.0% | 71.7% | 8 / 15 | 48 | 80% | 43.4% | $297 / $-194 | $466 | 32% / 47 | 25% / 49 |
| 4x$87 taper50 | $348 | L60 | 25.5% | 0.0% | 74.5% | 6 / 14 | 64 | 85% | 39.1% | $363 / $-192 | $419 | 32% / 48 | 19% / 71 |
| 2x$250 taper50 | $500 | L60 | 33.6% | 0.0% | 66.4% | 13 / 20 | 47 | 72% | 47.9% | $225 / $-166 | $553 | 35% / 56 | 32% / 40 |
| 3x$180 taper50 | $540 | L60 | 30.5% | 0.0% | 69.5% | 8 / 15 | 44 | 81% | 47.2% | $284 / $-201 | $503 | 37% / 38 | 25% / 49 |
| 2x$270 taper50 | $540 | L60 | 34.7% | 0.0% | 65.3% | 13 / 19 | 45 | 71% | 48.0% | $227 / $-165 | $572 | 34% / 55 | 35% / 39 |
| 4x$135 taper50 | $540 | L60 | 25.1% | 0.0% | 74.9% | 5 / 11 | 55 | 87% | 43.7% | $373 / $-234 | $414 | 30% / 49 | 20% / 66 |
| 3x$250 taper50 | $750 | L60 | 31.0% | 0.0% | 69.0% | 8 / 15 | 43 | 82% | 47.6% | $291 / $-208 | $511 | 36% / 36 | 26% / 46 |
| 4x$250 taper50 | $1000 | L60 | 25.1% | 0.0% | 74.9% | 4 / 10 | 55 | 88% | 45.4% | $376 / $-250 | $414 | 29% / 52 | 22% / 58 |
| 1x$250 notaper | $250 | R40 | 56.2% | 0.0% | 43.0% | 35 / 55 | 58 | 33% | 50.6% | $142 / $-110 | $925 | 65% / 56 | 48% / 63 |
| 1x$350 notaper | $350 | R40 | 48.9% | 0.0% | 51.1% | 30 / 48 | 62 | 39% | 50.6% | $138 / $-110 | $805 | 48% / 64 | 50% / 60 |
| 1x$450 notaper | $450 | R40 | 50.9% | 0.0% | 49.1% | 33 / 51 | 60 | 38% | 50.9% | $139 / $-111 | $838 | 54% / 59 | 48% / 64 |
| 2x$175 taper50 | $350 | R40 | 40.3% | 0.0% | 59.7% | 15 / 23 | 41 | 65% | 48.4% | $225 / $-166 | $664 | 42% / 44 | 38% / 41 |
| 3x$117 taper50 | $351 | R40 | 31.9% | 0.0% | 68.1% | 9 / 16 | 45 | 77% | 43.5% | $292 / $-192 | $525 | 36% / 47 | 28% / 45 |
| 4x$87 taper50 | $348 | R40 | 31.0% | 0.0% | 69.0% | 7 / 15 | 44 | 80% | 39.6% | $348 / $-190 | $511 | 36% / 41 | 27% / 46 |
| 2x$250 taper50 | $500 | R40 | 38.8% | 0.0% | 61.2% | 14 / 21 | 40 | 68% | 48.8% | $227 / $-170 | $639 | 38% / 48 | 39% / 36 |
| 3x$180 taper50 | $540 | R40 | 36.9% | 0.0% | 63.1% | 8 / 16 | 34 | 76% | 47.7% | $290 / $-210 | $608 | 40% / 34 | 34% / 35 |
| 2x$270 taper50 | $540 | R40 | 39.0% | 0.0% | 61.0% | 14 / 20 | 40 | 68% | 48.8% | $226 / $-170 | $641 | 37% / 47 | 41% / 37 |
| 4x$135 taper50 | $540 | R40 | 30.4% | 0.0% | 69.6% | 6 / 12 | 45 | 84% | 43.8% | $362 / $-241 | $500 | 37% / 32 | 24% / 54 |
| 3x$250 taper50 | $750 | R40 | 37.6% | 0.0% | 62.4% | 8 / 16 | 33 | 77% | 49.2% | $282 / $-212 | $619 | 41% / 34 | 34% / 31 |
| 4x$250 taper50 | $1000 | R40 | 33.2% | 0.0% | 66.8% | 5 / 11 | 35 | 83% | 47.5% | $354 / $-262 | $547 | 38% / 30 | 29% / 41 |
| 1x$250 notaper | $250 | NO | 63.4% | 34.4% | 0.0% | 36 / 56 | 47 | 0% | 50.5% | $142 / $-112 | $1,044 | 66% / 56 | 61% / 40 |
| 1x$350 notaper | $350 | NO | 62.1% | 37.1% | 0.0% | 34 / 51 | 45 | 0% | 50.5% | $143 / $-112 | $1,022 | 65% / 52 | 60% / 38 |
| 1x$450 notaper | $450 | NO | 61.4% | 38.1% | 0.0% | 34 / 52 | 44 | 0% | 50.7% | $143 / $-114 | $1,011 | 64% / 50 | 59% / 41 |
| 2x$175 taper50 | $350 | NO | 54.5% | 45.5% | 0.0% | 17 / 28 | 25 | 0% | 49.1% | $230 / $-171 | $897 | 58% / 25 | 51% / 24 |
| 3x$117 taper50 | $351 | NO | 45.0% | 55.0% | 0.0% | 12 / 21 | 19 | 0% | 44.0% | $307 / $-205 | $741 | 48% / 19 | 42% / 18 |
| 4x$87 taper50 | $348 | NO | 42.7% | 57.3% | 0.0% | 9 / 16 | 14 | 0% | 39.2% | $367 / $-201 | $702 | 47% / 13 | 39% / 16 |
| 2x$250 taper50 | $500 | NO | 51.9% | 48.1% | 0.0% | 17 / 25 | 24 | 0% | 49.4% | $229 / $-177 | $855 | 53% / 25 | 51% / 22 |
| 3x$180 taper50 | $540 | NO | 48.7% | 51.3% | 0.0% | 10 / 18 | 16 | 0% | 48.4% | $299 / $-224 | $802 | 51% / 17 | 47% / 16 |
| 2x$270 taper50 | $540 | NO | 52.8% | 47.2% | 0.0% | 16 / 25 | 24 | 0% | 49.5% | $228 / $-174 | $869 | 50% / 25 | 55% / 22 |
| 4x$135 taper50 | $540 | NO | 45.9% | 54.1% | 0.0% | 7 / 13 | 12 | 0% | 45.2% | $372 / $-253 | $755 | 49% / 12 | 43% / 12 |
| 3x$250 taper50 | $750 | NO | 50.1% | 49.9% | 0.0% | 10 / 17 | 16 | 0% | 49.2% | $296 / $-232 | $825 | 51% / 16 | 50% / 15 |
| 4x$250 taper50 | $1000 | NO | 52.4% | 47.6% | 0.0% | 7 / 14 | 11 | 0% | 49.4% | $364 / $-277 | $863 | 56% / 11 | 49% / 11 |

## 3. Total worst-case $ sweet spot (live rule L60, best taper variant at each total; R40 in brackets)
| total worst case | best config (pass) | pass | med / p75 | chain med | value | R40: pass / chain |
|---|---|---|---|---|---|---|
| $250 | 1 x $250 | 55.5% | 35 / 55 | 59 | $913 | 56.2% / 58 |
| $350 | 2 x $175 taper | 36.8% | 14 / 21 | 44 | $605 | 40.3% / 41 |
| $450 | 2 x $225 taper (3 x $150 taper: 31.2%, 8 / 15, chain 42) | 34.1% | 14 / 21 | 45 | $561 | 39.8% / 40 (3x150: 36.6% / 34) |
| $500 | 2 x $250 taper | 33.6% | 13 / 20 | 47 | $553 | 38.8% / 40 |
| $540 | 2 x $270 taper (3 x $180: 30.5%, 8 / 15, chain 44) | 34.7% | 13 / 19 | 45 | $572 | 39.0% / 40 |
| $750 | 3 x $250 taper | 31.0% | 8 / 15 | 43 | $511 | 37.6% / 33 |
| $1,000 | 4 x $250 taper | 25.1% | 4 / 10 | 55 | $414 | 33.2% / 35 |

## 4. Findings
1. Total worst case barely matters between $350 and $750 under the live rule: pass 31-37% (L60) / 36-40% (R40), chain 42-47 (L60). The differences inside this band (2-4 pass points, 2-5 chain sessions) are within the noise of ~10 independent 120-session windows. Only two things are robust: (a) $1,000 (4 micros) is clearly worse (25% pass, chain 55 at L60); (b) 1 micro (total $250-$450) has a far higher pass rate (48-56%) but is slow (median 30-35, chain 59-61).
2. The $450 total passes the first-trade check (3 x $150 = $448.5 <= $540 allowed, so fresh-account trade 1 is not tightened) but the protection does not hold: after one full stop-out (-$450) the cushion is ~$550, room $450, allowed $270, and 3 micros then need a stop of 44 pts ($88/micro), at or below the 0.2%-of-price floor (40-52 pts at 20-26k) -> DRAWDOWN_TOO_DEEP on most later signals. 69% of 3 x $150 evals STALL at L60 (63% at R40), 0% bust. Same mechanism as for 4 x $250, just one loss later. Skip share 77-81% (mostly idle stalled sessions).
3. Does $450 beat the others? vs $250 (1 micro today): faster (3 x $150 taper: median 8 vs 35 sessions, chain 42 vs 59 at L60; 34 vs 58 at R40) but 24 pts fewer passes (31.2% vs 55.5%, value $514 vs $913). vs $350 / $540 / $500: equal within noise (2 x $175 36.8%, 2 x $270 34.7%, 3 x $180 30.5%; chains 44-47). vs $1,000: better (31-34% vs 25% pass, chain 42-45 vs 55; at R40 36-40% vs 33%). So $450 is "as good as the best multi-micro profile", not better than 1 micro on value/eval, and not distinguishable from $350 or $540.
4. Micros x stop split at the same $450: 2 x $225 (34.1%, med 14, chain 45) ~ 3 x $150 (31.2%, 8, 42) > 4 x $112 (24.5%, chain 55) > 6 x $75 (17.2%, chain 93). More micros with narrower stops is strictly worse: stops of $75-112 are inside the typical NOISE/fade adverse excursion, win rate falls 50% -> 42% (4 x $112) -> 35% (6 x $75), and the narrow trade does not escape the live-rule floor either. (Under NO tightening 6 x $75 still reaches 40.3% / chain 10 - fast but 60% bust - not live.)
5. Taper helps every multi-micro config (+5 to +9 pass pts, e.g. 3 x $150: 22.8% -> 31.2%; 2 x $225 29.5% -> 34.1%). Keep taper50.
6. Win rate vs stop: 1 micro $250-450: 50.5-50.9%; 2 x $225: 47.8-49.5%; 3 x $150: 46.4%; 4 x $112: 42%; 6 x $75: 35% (narrower stops are hit more often before the trail/target). Average win / loss for 3 x $150 taper: +$292 / -$199.
7. Wider single-micro stops do not help: 1 x $350 49.6%, 1 x $450 47.9% (L60) vs 1 x $250 55.5%; a wider stop turns more losers into larger losses, shrinking cushion and causing more stalls.
8. Era split: every live profile is weaker in 2024-26 than 2021-23 (3 x $150: 35% -> 28%; 2 x $225: 38% -> 30%; 1 x $250: 65% -> 47%); exceptions: R40 2 x $270 (37% -> 41%) and 2 x $250 R40 (38% -> 39%). Chain medians 39 -> 44 (3 x $150 L60).
9. R40 (allowed = room - $40) adds 3-8 pass pts to every multi-micro config (3 x $150: 31.2 -> 36.6%, chain 42 -> 34) and does nothing for 1 micro. NO tightening (study assumption) shows pass 41-54% for $450-class configs but with 46-60% bust; it is not what the live code does.

## 5. Verdict
- Best 25K high-risk EVAL profile under the LIVE rule (L60): 3 micros x $150 stop per micro (total $450) with taper to 1 micro when < 50% of the target remains is the fastest (median 8 / p75 15 sessions, restart-chain 42, 31% pass, 0% bust, 69% stall); 2 micros x $175-$225 taper is the same speed class with a slightly better pass rate (34-37%, median 14, chain 44-45). The two are statistically tied; 3 x $150 is the pick for speed, 2 x $175 for pass rate. Fresh-account first trade is untightened for both (448.5 and 2 x 174.5 = 349 <= 540).
- vs the 1-micro baseline (55.5% pass, chain 59, value $913): high-risk 3 x $150 gives 29% shorter chain (42 vs 59, 8 vs 35 median among passers) but 24 pts lower pass probability and 44% lower value per eval ($514). If pass probability per eval / eval fee is the objective, stay at 1 micro; if time-to-funded is, use 3 x $150.
- Total worst case: $450 beats $1,000 (clearly) and equals $350 / $500 / $540 / $750 within noise; it does not beat $250 (1 micro) on pass rate. There is no sweet spot above $350: flat 31-37% pass from $350 to $750. The limiting factor is the live rule's min-stop floor + 0.6 shrink after the first loss, not the initial total.
- Recommendation (exact): 3 micros, stop $150 per micro (74 pts, 296 ticks; per-contract live risk $149.50 incl. fee + 1 tick slip), taper rule: 1 micro as soon as < 50% of the $1,250 target remains (i.e. profit >= $625), leave the live 0.6 rule on (0 busts); if the shrink were raised to room - $40, same profile gives 36.6% pass / chain 34. Fallback for more passes: 2 micros x $175 (stop 86.5 pts) with the same taper.

## 6. Caveats
- Starts overlap; 2-4 pt differences are noise. Stall = 20 idle sessions is a modelling choice (affects chain time only). Day stops, kill-switch flatten, hold rule, firm max contracts and eval fee not modelled. Win-rate/avg figures are over all executed trades in 120-session horizon runs (overlapping starts weight early sessions more). Gap fills beyond the stop are simulated (min(stop, open)) and can exceed the planned worst case; 0% bust in every live row means this never hit the floor.
- The 1-micro rows with wider stops (1 x $350/$450) change the strategy's exit, not just the sizing; they are in the table for completeness.
