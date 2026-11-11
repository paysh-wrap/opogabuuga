# Two books + Markov study - summary (session 17, 2026-11-11)

Books: covers only -> published rules used. Markov video: not seen -> generic Markov chain method. MNQ 1-minute 2019-05..2026-11, pick on 2019-23, judge on 2024-26 only, $1 fee + 1 tick slippage, flat daily, Pro 25K eval sim. Full tables: RESULTS.md.

| held-out 2024-01..2026-11 | trades | win | $/trade | net $ | max DD $ | eval PASS / BUST | median days | strict PASS / BUST |
|---|---|---|---|---|---|---|---|---|
| NOISE_250 (app default) | 451 | 43.9% | +23.88 | +10,771 | 2,228 | 50.7% / 46.5% | 42 | 29.5% / 56.4% |
| NOISE_250 + lock (preset C) | 427 | 52.2% | +27.19 | +11,609 | 2,028 | 60.3% / 39.4% | 46 | 41.9% / 48.2% |
| **NOISE + lock + RSI(2) momentum guard 90/10 (K6)** | 368 | 52.4% | +32.96 | +12,128 | 1,546 | 65.2% / 30.6% | 47 | 41.6% / 35.7% |
| Connors day bias (IS pick: Double 7's long) | 240 | 39.6% | -13.03 | -3,128 | 6,071 | 30.9% / 67.4% | 45 | 23.8% / 72.0% |
| Connors intraday (IS pick: 5m Double 7's) | 1,253 | 55.9% | -2.62 | -3,287 | 5,404 | 15.9% / 77.3% | 60 | 15.9% / 77.3% |
| Candlestick (IS pick: 15m inside bar @EMA21 3R) | 174 | 35.1% | -20.64 | -3,592 | 5,228 | 6.8% / 54.7% | 93 | 0.0% / 57.2% |
| Markov day bias (IS pick: M1 x gap) | 267 | 42.7% | -2.90 | -774 | 5,084 | 31.4% / 68.6% | 25 | 19.8% / 80.2% |
| Markov NOISE filter (IS pick: not against M2) | 270 | 48.1% | +20.95 | +5,656 | 1,638 | 32.9% / 30.6% | 62 | 20.4% / 44.2% |
| always long 09:31-16:00 (benchmark) | 649 | 43.9% | +10.91 | +7,078 | 5,383 | 29.5% / 70.5% | 12 | 13.9% / 82.7% |

Verdict: every book signal and every Markov use FAILS on held-out data (Markov "bias" = the up-drift only). Only K6 (guard: no NOISE short after RSI(2) > 90, no NOISE long after RSI(2) < 10) beats NOISE; all thresholds 80-95 also beat it and blocked trades lose in both eras, but the evidence is weak (permutation p 0.04 IS / 0.11 HO, HO net gain +$518 with 33 % bootstrap chance <= 0, gain mostly 2026). Recommendation: no app change; SHADOW-test K6 next to NOISE for >= 60 sessions.
