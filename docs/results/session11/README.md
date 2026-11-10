# Session 11 (2026-11-10) — results and final report

All studies: MNQ 5 years (Databento MNQ.v.0, 2021-11 → 2026-10), live rules (D57 shrink for NOISE, kill $50, D68 payouts),
pick on 2021–23, judge on 2024–26. Scripts + full tables are next to each report. Use system `python3` (numpy/pandas).

| # | Study | Report | Verdict |
|---|---|---|---|
| 1 | PM fade under D57 stop-shrink | pm_fade_d57_study.md | NOT adopted (D73): −4..−8 pts eval pass 2021–23, no gain 2024–26 |
| 2 | AI tools' published accuracy | ai_tools_published_accuracy.md | none published for index direction |
| 3 | AI-bias sizing | ai_bias_sizing_study.md | version B built for 100K/150K, gated by live record ≥ 60% over ≥ 60 calls (D74) |
| 4 | Win-rate additions (~75 variants) | final_push/winrate.md | ONE passes: NOISE profit lock (+100 pt → stop to entry +10 pt, no re-entry after a locked stop) |
| 5 | Faster evals | final_push/eval_speed.md | reset frozen evals at once; 25K High-risk recover mode; everything else fails |
| 6 | Second market (MES/MYM/M2K) | final_push/second_market.md | none qualifies — stay all-MNQ |
| 7 | Cushion (Kelly) sizing + lock through accounts | final_push/kelly_sizing.md | lock passes on funded; cushion sizing = fewer dead accounts for less income (user choice); 25K worst account |

## Final report (what the final push found)
- Trade stream: mean ≈ $20/trade per micro, sd ≈ $210 → Kelly ≈ 0.43 micro per $1,000 cushion (0.58 with the lock). Live sizes are
  1.7× Kelly on 25K/50K, 1.1× on 100K/150K. ~100 filter/exit variants tested over two sessions: the edge per trade does not move much.
- NOISE profit lock (PROPOSED, needs user approval — changes NOISE parameters, D55): 5y win 50.0% → 53.2%, PF 1.33 → 1.37,
  +$717, max DD same. Through the account engine (dead = frozen/bust, 2021–23 | 2024–26, funded): 25K 66|74 → 63|59 %,
  50K 53|64 → 53|60, 100K 17|63 → 7|36, 150K 15|50 → 14|6; mean income per 2 wk 25K $63|42 → $63|47, 50K $112|80 → $110|102,
  100K $160|119 → $168|154, 150K $220|153 → $238|225. Eval pass within ±3 pts. One of ~30 lock variants; the re-entry sibling failed held-out.
- Eval speed (PROPOSED): (a) reset a frozen eval immediately: 25K cushion < $150, 100K < $300, 150K < $225 (50K none) — same passes,
  4–14% fewer sessions, costs a reset fee each time (prices unknown); (b) 25K High-risk recover mode (fewer micros when 3 don't fit):
  pass 39|32 → 43.5|38 %. Failed: 30-min NOISE checks, 5 entries, small stops when frozen, looser shrink/min-stop, front-loaded size, cushion size on evals.
- Account choice: funded 25K at 1 micro is 70% dead / $53 per 2 wk; 150K at its live table has the best income per dead account.
  Cushion sizing (with the lock): 50K k=0.8 cap 2 → 0%|0% dead, $89|106 (live 53|60 %, $110|102); 100K k=1.0 cap 2 → 0|4 %, $149|132
  (live 7|36 %, $168|154); 150K k=1.0 cap 4 → 0|2 %, $221|202 (live 14|6 %, $238|225).
- Lead not tested cleanly: 150K eval at 3 MNQ micros instead of 4 (seen in a mixed run: pass 66% vs 57%).
- Caveats: simulator fills stops at the stop (no gap slippage); "dead %" is lumpy (overlapping starts); fees not included;
  the agent's dead % (25K 70 / 50K 58 / 100K 38 / 150K 31) differs from session 10's bust yr-1 (57 / 44 / 27.5 / 24.5) — same ranking.
- Verify with Lucid: whether 40% consistency applies to Pro EVALS (yaml has none; if it does, 25K High-risk pass drops to ~30|22 %), reset/eval prices.
