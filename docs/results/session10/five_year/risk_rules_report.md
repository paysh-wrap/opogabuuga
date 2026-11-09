# Account-level risk rules vs bust rate (agentE)
Scripts: study.py (own eval/funded sims with rule hooks), report.py, sweep.py. Raw: results.json, tables.md, sweep.txt.
Method: main_strategy_5y.csv, rolling starts every 2 sessions (eval horizon 120, funded 260, payout every 10 sessions, 5 accounts, all income = take-home after split).
H1 = starts 2021-11..2023-12, H2 = 2024-01..2026-10. All $ thresholds are fractions of the plan MLL (25K: 0.25xMLL=$250). Rules apply the same in eval and funded; E* rules are eval-only. Eval DLL is none on 25K, soft on 50K/100K as in the app.
"Pass both halves" = funded bust lower in H1 AND H2, funded income >= 85% of baseline in both halves.
Caveats: overlapping starts (effective sample small), halves differ a lot (H2 is far worse), brake thresholds were tuned post hoc in sweep.txt. Baseline funded bust is high (57% / 52% / 30%).

### pro25k

| rule | eval pass% | eval bust% | e.bust H1/H2 | fund 2wk$ | fund yr med$ | fund bust% | f.bust H1/H2 | f.income H1/H2 vs base | PASS both halves |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 63.4 | 34.4 | 31.4/37.1 | 317 | 4500 | 56.6 | 57.2/55.8 | 100%/100% |  |
| D1 stop after 2 losing trades | 61.6 | 36.3 | 36.4/36.1 | 305 | 4500 | 59.5 | 63.6/54.6 | 94%/100% |  |
| D2 stop after 1 losing trade | 56.3 | 40.6 | 39.9/41.3 | 216 | 2546 | 70.0 | 63.3/77.9 | 60%/80% |  |
| D3 day loss 0.25xMLL | 61.6 | 36.3 | 36.4/36.1 | 306 | 4500 | 58.7 | 61.8/55.0 | 94%/100% |  |
| D4 day loss 0.40xMLL | 61.6 | 36.3 | 36.4/36.1 | 306 | 4500 | 58.7 | 61.8/55.0 | 94%/100% |  |
| W1 week loss 0.5xMLL | 63.2 | 34.6 | 31.8/37.1 | 317 | 4500 | 53.9 | 57.2/50.0 | 99%/102% |  |
| W2 week loss 0.8xMLL | 63.4 | 34.4 | 31.4/37.1 | 319 | 4500 | 55.8 | 57.2/54.2 | 100%/102% |  |
| B1 brake cush<30% cut->1 | 63.4 | 34.4 | 31.4/37.1 | 317 | 4500 | 56.6 | 57.2/55.8 | 100%/100% |  |
| B2 brake cush<50% cut->1 | 63.4 | 34.4 | 31.4/37.1 | 317 | 4500 | 56.6 | 57.2/55.8 | 100%/100% |  |
| B3 brake cush<30% pause 3 | 62.2 | 36.6 | 37.1/36.1 | 278 | 4500 | 59.3 | 64.3/53.3 | 85%/92% |  |
| B4 brake cush<50% pause 5 | 56.0 | 38.4 | 38.9/38.1 | 237 | 0 | 60.8 | 59.0/62.9 | 76%/73% |  |
| P1 profit lock 0.6xMLL cycle->1 | 63.4 | 34.4 | 31.4/37.1 | 317 | 4500 | 56.6 | 57.2/55.8 | 100%/100% |  |
| P2 profit lock 0.3xMLL cycle->1 | 63.4 | 34.4 | 31.4/37.1 | 317 | 4500 | 56.6 | 57.2/55.8 | 100%/100% |  |
| C1 cool-off lose>0.3xMLL | 63.1 | 34.7 | 31.4/37.7 | 316 | 4500 | 57.9 | 57.2/58.8 | 100%/99% |  |
| C2 cool-off lose>0.15xMLL | 56.5 | 39.8 | 42.0/37.7 | 216 | 3166 | 71.9 | 82.0/60.0 | 58%/82% |  |
| E1 eval day profit>=25% tgt stop | 63.4 | 34.4 | 31.4/37.1 | - | - | - | - | - |  |
| E2 eval day profit>=40% tgt stop | 63.4 | 34.4 | 31.4/37.1 | - | - | - | - | - |  |
| E3 eval size down within 30% tgt | 63.4 | 34.4 | 31.4/37.1 | - | - | - | - | - |  |
| E4 eval size down within 15% tgt | 63.4 | 34.4 | 31.4/37.1 | - | - | - | - | - |  |
| X1 D4+B2 | 61.6 | 36.3 | 36.4/36.1 | 306 | 4500 | 58.7 | 61.8/55.0 | 94%/100% |  |
| X2 D3+C1+W2 | 59.9 | 37.9 | 38.2/37.7 | 304 | 4500 | 60.0 | 63.6/55.8 | 92%/101% |  |
| X3 D4+B2+P1 | 61.6 | 36.3 | 36.4/36.1 | 306 | 4500 | 58.7 | 61.8/55.0 | 94%/100% |  |

### pro50k

| rule | eval pass% | eval bust% | e.bust H1/H2 | fund 2wk$ | fund yr med$ | fund bust% | f.bust H1/H2 | f.income H1/H2 vs base | PASS both halves |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 60.4 | 36.6 | 31.4/41.3 | 595 | 9000 | 51.8 | 48.8/55.4 | 100%/100% |  |
| D1 stop after 2 losing trades | 58.5 | 38.4 | 36.7/40.0 | 572 | 9000 | 55.1 | 56.2/53.8 | 93%/100% |  |
| D2 stop after 1 losing trade | 52.8 | 42.2 | 42.0/42.3 | 410 | 4516 | 66.0 | 61.5/71.2 | 61%/82% |  |
| D3 day loss 0.25xMLL | 58.5 | 38.4 | 36.7/40.0 | 573 | 9000 | 53.9 | 54.1/53.8 | 94%/100% |  |
| D4 day loss 0.40xMLL | 58.5 | 38.4 | 36.7/40.0 | 573 | 9000 | 53.9 | 54.1/53.8 | 94%/100% |  |
| W1 week loss 0.5xMLL | 59.9 | 36.6 | 31.8/41.0 | 597 | 9000 | 49.3 | 48.8/50.0 | 99%/102% |  |
| W2 week loss 0.8xMLL | 60.4 | 36.6 | 31.4/41.3 | 599 | 9000 | 51.1 | 48.8/53.8 | 100%/102% |  |
| B1 brake cush<30% cut->1 | 52.4 | 42.0 | 37.8/45.8 | 549 | 8593 | 55.4 | 58.3/52.1 | 90%/96% |  |
| B2 brake cush<50% cut->1 | 57.2 | 29.2 | 20.8/36.8 | 564 | 13070 | 44.2 | 40.3/48.8 | 98%/90% | YES |
| B3 brake cush<30% pause 3 | 60.2 | 37.9 | 37.5/38.4 | 525 | 9000 | 55.1 | 59.4/50.0 | 84%/94% |  |
| B4 brake cush<50% pause 5 | 50.8 | 41.1 | 38.2/43.9 | 460 | 4147 | 55.8 | 54.1/57.9 | 78%/76% |  |
| P1 profit lock 0.6xMLL cycle->1 | 56.7 | 35.2 | 29.3/40.6 | 448 | 9000 | 46.8 | 40.3/54.6 | 74%/77% |  |
| P2 profit lock 0.3xMLL cycle->1 | 53.6 | 29.8 | 21.9/37.1 | 419 | 9453 | 36.5 | 29.7/44.6 | 70%/72% |  |
| C1 cool-off lose>0.3xMLL | 60.2 | 36.8 | 31.4/41.6 | 594 | 9000 | 53.0 | 48.8/57.9 | 100%/100% |  |
| C2 cool-off lose>0.15xMLL | 53.0 | 41.8 | 42.0/41.6 | 414 | 6289 | 67.9 | 77.0/57.1 | 60%/85% |  |
| E1 eval day profit>=25% tgt stop | 60.0 | 36.9 | 31.4/41.9 | - | - | - | - | - |  |
| E2 eval day profit>=40% tgt stop | 60.4 | 36.6 | 31.4/41.3 | - | - | - | - | - |  |
| E3 eval size down within 30% tgt | 57.7 | 35.1 | 31.1/38.7 | - | - | - | - | - | EVAL-ONLY YES |
| E4 eval size down within 15% tgt | 60.7 | 35.6 | 31.4/39.4 | - | - | - | - | - |  |
| X1 D4+B2 | 57.7 | 29.2 | 20.8/36.8 | 562 | 10071 | 44.2 | 41.0/47.9 | 98%/90% | YES |
| X2 D3+C1+W2 | 56.8 | 40.1 | 38.5/41.6 | 573 | 9000 | 54.9 | 55.1/54.6 | 93%/102% |  |
| X3 D4+B2+P1 | 53.5 | 27.8 | 19.1/35.8 | 406 | 8278 | 41.3 | 33.2/50.8 | 67%/70% |  |

### pro100k

| rule | eval pass% | eval bust% | e.bust H1/H2 | fund 2wk$ | fund yr med$ | fund bust% | f.bust H1/H2 | f.income H1/H2 vs base | PASS both halves |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 45.7 | 17.9 | 1.4/32.9 | 686 | 19048 | 29.8 | 12.0/50.8 | 100%/100% |  |
| D1 stop after 2 losing trades | 45.4 | 20.2 | 3.9/35.2 | 675 | 17683 | 30.2 | 13.8/49.6 | 98%/100% |  |
| D2 stop after 1 losing trade | 27.5 | 20.9 | 11.7/29.4 | 483 | 11250 | 37.9 | 25.8/52.1 | 55%/98% |  |
| D3 day loss 0.25xMLL | 45.4 | 18.4 | 1.4/33.9 | 680 | 18205 | 29.3 | 12.0/49.6 | 99%/100% |  |
| D4 day loss 0.40xMLL | 45.7 | 17.9 | 1.4/32.9 | 686 | 19048 | 29.8 | 12.0/50.8 | 100%/100% |  |
| W1 week loss 0.5xMLL | 45.9 | 16.9 | 1.4/31.0 | 692 | 19063 | 28.7 | 12.0/48.3 | 100%/102% |  |
| W2 week loss 0.8xMLL | 45.7 | 17.9 | 1.4/32.9 | 686 | 19048 | 29.8 | 12.0/50.8 | 100%/100% |  |
| B1 brake cush<30% cut->1 | 44.4 | 17.2 | 1.8/31.3 | 643 | 16025 | 26.0 | 11.7/42.9 | 89%/102% | YES |
| B2 brake cush<50% cut->1 | 40.8 | 9.9 | 0.0/19.0 | 610 | 12678 | 19.9 | 0.0/43.3 | 85%/96% | YES |
| B3 brake cush<30% pause 3 | 45.5 | 23.3 | 21.2/25.2 | 615 | 13350 | 34.4 | 31.8/37.5 | 83%/102% |  |
| B4 brake cush<50% pause 5 | 40.1 | 22.6 | 9.9/34.2 | 641 | 16025 | 32.7 | 21.2/46.2 | 87%/105% |  |
| P1 profit lock 0.6xMLL cycle->1 | 28.3 | 16.5 | 1.4/30.3 | 471 | 12960 | 19.3 | 6.7/34.2 | 70%/67% |  |
| P2 profit lock 0.3xMLL cycle->1 | 14.7 | 12.3 | 1.4/22.3 | 376 | 10163 | 18.2 | 6.4/32.1 | 50%/64% |  |
| C1 cool-off lose>0.3xMLL | 45.7 | 17.9 | 1.4/32.9 | 685 | 19048 | 31.0 | 12.0/53.3 | 100%/100% |  |
| C2 cool-off lose>0.15xMLL | 44.7 | 20.9 | 13.8/27.4 | 566 | 11516 | 34.4 | 33.9/35.0 | 69%/107% |  |
| E1 eval day profit>=25% tgt stop | 45.7 | 17.9 | 1.4/32.9 | - | - | - | - | - |  |
| E2 eval day profit>=40% tgt stop | 45.7 | 17.9 | 1.4/32.9 | - | - | - | - | - |  |
| E3 eval size down within 30% tgt | 34.7 | 17.2 | 1.4/31.6 | - | - | - | - | - |  |
| E4 eval size down within 15% tgt | 43.7 | 17.9 | 1.4/32.9 | - | - | - | - | - |  |
| X1 D4+B2 | 40.8 | 9.9 | 0.0/19.0 | 610 | 12678 | 19.9 | 0.0/43.3 | 85%/96% | YES |
| X2 D3+C1+W2 | 45.2 | 18.4 | 1.4/33.9 | 670 | 17471 | 29.6 | 12.0/50.4 | 97%/100% |  |
| X3 D4+B2+P1 | 22.9 | 9.8 | 0.0/18.7 | 405 | 6489 | 14.3 | 0.0/31.2 | 58%/60% |  |
## Brake threshold sweep (post hoc, cut to 1 micro when cushion < y x MLL; 50K/100K only)
    pro50k baseline eval pass 60.4 bust 36.6 (H1 31.4 H2 41.3) | fund 2wk 595 bust 51.8 (H1 48.8 H2 55.4) inc H1 665 H2 511
    pro50k brake0.4 eval pass 50.3 bust 40.8 (H1 34.6 H2 46.5) | fund 2wk 538 bust 52.6 (H1 52.3 H2 52.9) inc H1 577 H2 492
    pro50k brake0.5 eval pass 57.2 bust 29.2 (H1 20.8 H2 36.8) | fund 2wk 564 bust 44.2 (H1 40.3 H2 48.8) inc H1 651 H2 461
    pro50k brake0.6 eval pass 53.8 bust 22.9 (H1 10.2 H2 34.5) | fund 2wk 521 bust 35.8 (H1 22.3 H2 51.7) inc H1 612 H2 414
    pro50k brake0.7 eval pass 52.1 bust 16.2 (H1 1.1 H2 30.0) | fund 2wk 546 bust 27.0 (H1 6.0 H2 51.7) inc H1 654 H2 419
    pro50k brake0.8 eval pass 51.3 bust 13.8 (H1 0.0 H2 26.5) | fund 2wk 493 bust 24.1 (H1 0.0 H2 52.5) inc H1 569 H2 405
    pro100k baseline eval pass 45.7 bust 17.9 (H1 1.4 H2 32.9) | fund 2wk 686 bust 29.8 (H1 12.0 H2 50.8) inc H1 821 H2 527
    pro100k brake0.4 eval pass 42.7 bust 14.5 (H1 0.0 H2 27.7) | fund 2wk 638 bust 22.8 (H1 4.2 H2 44.6) inc H1 726 H2 533
    pro100k brake0.5 eval pass 40.8 bust 9.9 (H1 0.0 H2 19.0) | fund 2wk 610 bust 19.9 (H1 0.0 H2 43.3) inc H1 699 H2 505
    pro100k brake0.6 eval pass 39.3 bust 9.3 (H1 0.0 H2 17.7) | fund 2wk 574 bust 20.1 (H1 0.0 H2 43.8) inc H1 643 H2 492
    pro100k brake0.7 eval pass 31.4 bust 9.9 (H1 0.0 H2 19.0) | fund 2wk 419 bust 22.2 (H1 0.0 H2 48.3) inc H1 533 H2 285
    pro100k brake0.8 eval pass 28.8 bust 4.6 (H1 0.0 H2 8.7) | fund 2wk 428 bust 17.0 (H1 0.0 H2 37.1) inc H1 504 H2 337

## Findings
- Pro 25K (1 micro): the cut-size rules do nothing (already 1 micro); pausing and loss stops all RAISE bust (stops reduce the number of trades but the $250 stop is 25% of MLL; a loss streak still busts). Week stop 0.5xMLL cuts funded bust 56.6->53.9 but H1 unchanged (57.2) so it fails. Nothing passes. The only real lever on 25K is smaller risk per trade (tighter stop / fewer trades), not account rules.
- Pro 50K (2 micros): brake cush<50% cut->1 passes both halves for funded (bust 51.8->44.2; H1 48.8->40.3, H2 55.4->48.8; income 98%/90%). Eval bust also falls 36.6->29.2 (H1 31.4->20.8, H2 41.3->36.8) at -3 pts pass. Higher y (0.7-0.8) cuts H1 bust to ~0-6% but H2 stays ~52% (no help), so the benefit is mostly regime-dependent.
- Pro 100K (2 micros): brake cut at 30% and 50% pass both halves. 50%: funded bust 29.8->19.9 (H1 12.0->0, H2 50.8->43.3), income 85%/96%; eval bust 17.9->9.9 but pass 45.7->40.8. 30%: milder (bust 26.0, income 89%/102%).
- Daily loss stops (N losing trades / $): never lower bust in both halves, cost 5-6% income at best; stop after 1 loss is clearly bad (-40% income, bust up).
- Pause-style brakes and cool-off after a loser: raise bust and cut income (pausing wastes time; busts come from a short cluster of losses, not tiredness).
- Weekly loss stop 0.5xMLL: tiny gain (bust -1 to -3 pts, income ~flat) but fails the both-halves test on 25K/100K (H1 equal); on 50K funded it is lower in both halves (48.8 same in H1 -> not strictly lower) -> fails.
- Profit lock (1 micro after +0.3/0.6xMLL cycle profit): lowers bust (50K 51.8->36.5, 100K 29.8->18.2) but costs 28-50% income: fails the 15% income test.
- Eval-only: stop for day at +25/40% of target: no effect (no effect because days rarely reach that). Size down within 30% of target: 50K bust 36.6->35.1 with H1/H2 both lower but pass -2.7; on 100K pass -11: not worth it. 15%: no gain.
- Combos X1 (D4+B2) equals B2; adding profit lock (X3) cuts bust further but loses 30-40% income.

## Recommendation
- Pro 25K: no account rule helps; keep baseline, optionally week stop 0.5xMLL ($500) as harmless (not proven). Address bust via trade-level risk (stop smaller than $250 / fewer trades) - out of scope here.
- Pro 50K: drawdown brake, cut to 1 micro when cushion (balance - MLL floor) < 50% of MLL ($1,000); optional eval-only size-down within 30% of target is marginal, skip.
- Pro 100K: same brake with y=30% (conservative, income-neutral) or 50% (bust -10 pts funded, ~10% income cost, ~5 pts eval pass cost). Do not use pause, cool-off, daily-stop-after-1 or profit lock.
- Treat the thresholds as indicative: the brake effect is large in H1 and much smaller in H2, and the 5y sample has few independent bust episodes.
