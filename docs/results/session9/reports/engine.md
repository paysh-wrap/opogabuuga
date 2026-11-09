# engine agent — status: INCOMPLETE (no engine-confirmed results yet)
- Engine speed: 1 month MNQ = 6 min alone; 1 year MNQ 2023 >1h45 and still running with the machine shared (load 4).
  A full 2019–2026 run per market (~7–10 h each) is not feasible in budget.
- Running: agents/engine/run_all.sh (nohup, nice 10) -> MNQ 2023 (in-sample), MNQ 2025-11..2026-11 (held-out),
  then MGC same; each followed by indscreen.py DUMP_ROWS. Plan = lucid_pro_25k.yaml with filters.trend all off
  (agents/engine/plan_all.yaml) so every setup is dumped and trend/structure filters can be screened offline.
- Analysis script ready: agents/engine/analyze.py SYM rows_IS.json rows_OOS.json [named combos e.g. brk trend3 brk+mso]
  (TP=min(T2,2.5R), skip T2<1.5R, score>=60, C1>=0.4ATR; per-feature win/exp/PF IS vs OOS; top combos picked on IS).
- MGC: repo's 7y offline screen (docs/results/ind7y/best175_holdout.txt) shows every IS-picked combo negative on
  2024–2026 held-out (best -0.01R); D52 1y engine -$870 every setup, -$367 with trend filter. Agrees with gold agent:
  recommend MGC OFF (instruments.MGC.enabled: false in lucid_pro_*/lucid_flex_*) pending nothing better.
- MNQ structure-break lead (filters.require_structure_break: true) NOT yet validated in-sample/held-out by me.
- best_trades.csv NOT produced (no completed dump).
