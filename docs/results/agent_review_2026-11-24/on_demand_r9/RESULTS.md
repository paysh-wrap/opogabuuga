# On-demand payouts vs weekly vs every 2 weeks (r9, 2026-11-24)
Status of the RULE: CONFIRMED (Lucid help center, user screenshots 2026-11-24). Status of the NUMBERS: UNVERIFIED research projection (same engine, data and caveats as calculator_r8: Databento MNQ 1-min, NOISE + CANDACE, funded rules, first 250 sessions per account, rolling starts, net of the 10% split, open-trade drawdown only through the stop).

## What is modelled (fsim.py `life(..., od=True)`)
Confirmed: DLL ON; payout requested DURING the session (6:00 PM to 3:45 PM ET) from the profit made THAT session; min $500; cap 1,000-3,000 first / 1,500-3,500 later (by plan); consistency 40% (largest day / cycle profit, today's partial day included); buffer = initial MLL + $100; after the request the account is paused until the end of the trading day; a Hedging Violation blocks it (the app never hedges, so not modelled). The request is made at the first moment the session profit makes the account eligible; amount = min(balance - buffer, plan cap, SESSION profit); the account then stops trading for the rest of that day and the remaining trades of that day are counted as lost (`lost_trades_year`). The "3 profitable days" rule of the weekly model is kept (unconfirmed, VERIFY). An intraday payout does not lower the EOD high that trails the MLL (same floor as the weekly model, conservative).
Compared (study.py, 4 Pro plans x 5 setups = 20 rows: fixed 1/2/3 micros, auto-high, auto-regular):
weekly (request at the close of every 5th session), every 2 weeks, **daily at the close** (request at the end of every session once eligible; Lucid LucidPro has no fixed window, so this is allowed), **on-demand** (confirmed rules above), on-demand WITHOUT the pause (counterfactual, not allowed by Lucid: isolates the pause), and on-demand with the amount NOT limited to session profit (sensitivity: an alternative reading of the rule, UNVERIFIED).

## Results (mean over the 20 rows; table.md has every group)
| mode | net / account / year, all starts | any payout % | bust % | median sessions to 1st payout | payouts / yr |
|---|---|---|---|---|---|
| weekly | $2,397 | 61.4 | 32.4 | 89 | 1.54 |
| every 2 weeks | $2,321 | 60.9 | 32.2 | 92 | 1.43 |
| daily at the close | **$2,452** | 61.9 | 32.5 | **86** | 1.64 |
| **on-demand (confirmed rules)** | **$840** | 45.6 | 28.4 | 98 | 1.05 |
| on-demand, no pause (counterfactual) | $840 | 45.6 | 28.4 | 98 | 1.05 |
| on-demand, amount not session-limited (sensitivity) | $2,466 | 61.9 | 32.8 | 85 | 1.65 |

## Answers
1. **Does on-demand take MORE money out per year (net)? No, much LESS: $840 vs $2,397 weekly (-65%)**, and it pays out at all in only 45.6% of starts vs 61.4% (25K: never, 0 of 5 setups; a single session rarely makes $500). Cause: the request is limited to the profit of that one session, must itself stay within 40% of the cycle, and every request resets the cycle; weekly/daily-close requests take the whole cycle (up to the plan cap). Best mode per row (excluding the counterfactual): daily at the close 11 of 20, weekly 7, every 2 weeks 2, on-demand 0. Only if the amount were NOT limited to session profit (sensitivity, unconfirmed) would on-demand match daily-at-close ($2,466 vs $2,452, +0.6%, within noise).
2. **First payout faster?** No. On the 15 rows where on-demand pays at all: median 98.1 sessions to the first payout vs 97.3 weekly and 94.3 daily at the close (the 98 in the table above is over those 15 rows, the others over all 20). Daily at the close is the fastest allowed mode. Sensitivity reading: 85 over all rows (86 daily close).
3. **Effect of the trading pause: negligible.** On-demand with and without the pause: identical net ($840 vs $840), same busts (28.4%), 1.1 pause days and 0.1 lost trades per account-year (0.3 on 150K). On the sensitivity reading 1.7 pause days / 0.4 lost trades per year, busts 32.8% vs 32.5% (not significant). The lower bust % of confirmed on-demand is NOT an effect of the pause (identical without it); it comes from the small payouts leaving more balance in the account.
4. **Calculator default = "every session at the close" (cadence 1)**, the best of the allowed timings (net +2% vs weekly, first payout 3 sessions sooner); weekly is the best of the three originally listed options; on-demand is labelled "CONFIRMED (Lucid help center)" and stays selectable but is the worst. Caveat: the +2% over weekly is small and inside model noise; the -65% for on-demand is not.

## Files
fsim.py (funded_payout_r6, new args `cad, od, pause`; defaults reproduce r6/r8), calculator_r8/make_calc.py (cadences [5, 10, 1, 0]; regenerates config/income_calc.json, `python3 make_calc.py`, ~3 min), study.py -> study.json, summarize.py -> table.md.
