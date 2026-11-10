# Session 12 — order blocks (OB) + SMT (MNQ vs MES): NOISE + afternoon fade

Scope of THIS report: NOISE + PM fade on MNQ (1 micro, $250/124-pt stop, live rules). LunqFX is handled separately (lunq_eval.py, run_lx.py,
lx_grid.json belong to the other agent; lx_grid.json in git is a stale 4-month smoke test, ignore it).

Data: Databento MNQ.v.0 + MES.v.0 1-minute bars 2021-11 -> 2026-10 (not in git; re-download with docs/results/session11/rebuild_main_csv.py and
final_push/dl_second.py mes). Pick on 2021-11..2023-12 (in-sample, IS), judge on 2024-01..2026-10 (held-out, HO).
Code under test = the real indicators (backend/app/indicators/order_block.py, smt.py), closed 1-minute bars (OB also on 5-minute), events at the
confirmation bar. Trade generation = session-11 winrate_study.py (NOISE hourly checks + PM fade), baseline reproduces it. Script: ob_study.py, run_nf.py;
raw grid: nf_grid.json / nf_grid.log.

Roles tested separately:
- FILTER: block an entry when a live opposing OB is within N points ahead (OBF), or a recent SMT divergence points the other way (SMT).
  A vetoed NOISE entry consumes that entry; the fade's "NOISE day" set comes from the UNFILTERED baseline, so a filter never adds a trade.
- ANCHOR: stop moved to the far edge of the nearest same-side live OB (-/+ buffer) only if it is tighter than the fixed 124-pt stop (never wider).

## Baseline (NOISE + fade)
| | trades | win % | PF | profit | max DD |
|---|---|---|---|---|---|
| IS 2021-23 | 564 | 48.58 | 1.30 | $9,363 | $1,538 |
| HO 2024-26 | 727 | 51.03 | 1.34 | $15,982 | $2,591 |

## Results (27 variants, full table in nf_grid.log)
| variant | IS n / win / profit | HO n / win / profit | verdict |
|---|---|---|---|
| OB filter 1m, body 1.5 ATR, 25 pt (best IS pick) | 509 / 49.51 / $9,686 | 681 / 50.66 / $16,274 | win rate DOWN held-out -> FAIL |
| OB filter 5m, body 1.0, 10 pt | 563 / 48.67 / $9,396 | 723 / 51.04 / $16,372 | removes 1 trade IS, 4 HO: +0.01 pt win, noise -> not meaningful |
| OB filter 1m body 1.0, 10-60 pt | 357-512 / 45.1-48.2 | 460-669 / 45.7-50.5 | lower win and/or profit |
| SMT filter (10/20/40 bars, valid 10/30) | 88-467 / 48.0-49.3 / -$348..$5,856 | 144-618 / 50.2-53.1 / $5.5k-$12.3k | blocks 17-84% of trades, profit falls 40-100% IS and 23-65% HO; win rate up HO only |
| OB stop anchor (1m/5m, body 1/1.5, buffer 2/5) | 564-601 / 41.8-48.4 / $7.4k-$9.1k | 728-771 / 44.2-50.8 / $14.7k-$15.8k | win rate and profit both DOWN everywhere |

Only two filter variants passed the IS rule (win AND profit both up): the 1m/25pt one (fails HO on win rate) and 5m/10pt (changes 1 and 4 trades,
so the "improvement" is within noise). No SMT or anchor variant passes IS.

## Verdict
Do NOT enable. Nothing improves held-out win rate AND profit in a meaningful way. OB/SMT filters in this form mostly remove good trades (the NOISE
edge already trades WITH the day; opposing supply/demand and 1-minute SMT carry no extra information). OB stop anchors cut win rate by 1-9 pts and
profit by 2-25% because 1-minute OB edges sit inside normal noise, so the tight stop is hit before the trend works.

## Built (all default OFF)
- indicators/order_block.py, indicators/smt.py (pure, Decimal, closed bars, confirmation-bar events), engine/structure_filter.py.
- config strategy.structure_filters (StructureFilterCfg): enabled=false (no blocking), shadow_log=true (stores what it WOULD have blocked and the OB anchor
  stop in the signal features of NOISE and PM_FADE). smt_filter needs MES 1-minute bars in the feed; skipped when absent. Anchor is never applied live.
- Tests: tests/unit/test_ob_smt.py. Backend 625 passed, risk/management/phases coverage 100%, ruff + mypy clean.
