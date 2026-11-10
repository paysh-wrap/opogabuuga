# Session 12 — LunqFX confluence engine + order blocks (OB) / SMT (MNQ vs MES)

Candidates: every setup the real engine scored PASS (shadow plan: entry/stop/TP) — `docs/results/tools/research.py MNQ <month> config/rules/lucid_pro_25k.yaml`.
22 sampled months (2021-11..2026-10; the remaining months' dumps were killed mid-run, ~15 min each). Simulation: `lunq_eval.py` (fill at plan entry,
stop first, flat 15:55 ET, 1 micro, $1 fee, 1 tick stop slip, max 3/day, one position). R:R must be 1.75–3.0. Pick on 2021-11..2023-12 (IS), judge on
2024-01..2026-10 (HO). Full grid: `lx_grid.json` (`run_lx.py /tmp/lx`).

| Variant | IS trades | IS win | IS $ | HO trades | HO win | HO $ |
|---|---|---|---|---|---|---|
| Baseline | 508 | 54.7% | -11,555 | 675 | 53.9% | -27,322 |
| (1) OB filter, pick: 5m, body 1.0 ATR, 60 pts | 440 | 65.9% | +4,736 | 603 | 62.9% | -5,724 |
| (1) SMT filter, best (l10 v10) | 299 | 49.5% | -12,052 | 402 | 50.0% | -20,380 |
| (2) OB filter + OB stop anchor (buf 2 / 5) | 440 | 65.9% | +4,736 | 603 | 62.9% | -5,724 |
| anchor alone (all 8) | 508 | 54.7% | ≈ -11,550 | 675 | 53.9% | ≈ -27,310 |

Findings
- OB filter (blocking entries that face an opposing order block) helped every OB setting in-sample and held-out; the pick holds up: +9 pts win rate and
  +$21.6k vs baseline held-out. But LunqFX still loses money held-out (PF 0.88).
- SMT makes everything worse (cuts the winners).
- OB stop anchor changes almost nothing: a tighter OB stop pushes R:R above 3.0 and is refused (never widens, never moves TP).

Wiring: `strategy.lunqfx_structure` (`enabled` false, `anchor_stop` false, `shadow_log` true, `filter` = StructureFilterCfg). Pure
`backend/app/engine/lunq_structure.py`; hook `_lunq_structure` in `backend/app/signals/service.py` runs after the gates on a PASS only (G1–G8 unchanged), stores
`features.lunq_structure` (would_block, anchor_stop, anchor_rr). Tests: `backend/tests/unit/test_lunq_structure.py`.
To try the pick: `filter: {ob_tf_min: 5, ob_body_atr: 1.0, ob_dist_pts: 60, smt_filter: false}`.

Recommendation: keep OFF. Held-out win rate and profit both improve, but the result is still a loss, so it does not make LunqFX tradable.
