# Ten accounts per plan (5 EVAL + 5 FUNDED), Lucid Pro 25K / 50K / 100K / 150K, 2026-11-22 (research only)

## In plain words
- Over the 5-year history all four plans make money with 10 accounts, mostly from funded payouts. Net after fees on TODAY's setup, on-demand payouts: about $53k (25K), $91k (50K), $103k (100K), $118k (150K).
- These 5-year totals are CAPPED: each funded account stops after its 5th payout (it goes "live", not modelled). By the end every account has hit the cap, so the totals show how fast the cap is reached, not an income rate.
- FAST (D157) vs TODAY, with one free account per CANDACE trade:
  - 150K FAST is better: $124.5k vs $118.4k over 5y, median 128 vs 151 days to funded, rolling-12-month median $20.2k vs $17.1k. It pays eval fees again (5 extra buys) and is weaker on the last 12 months ($0.5k vs $1.6k).
  - 25K FAST is WORSE here: 10 vs 20 passes, median 106 vs 39.5 days, $49.9k vs $53.3k. Each CANDACE trade goes to only one of the five eval accounts, so the single-account gain from CANDACE is diluted.
  - 50K FAST = BASE (identical). 100K FAST is about equal (-$1.1k over 5y).
- The last 12 months are poor: a fresh start needs about 100-170 sessions to reach funded and payouts start late. 25K is net negative ($-3.5k TODAY, $-2.9k FAST: 15 funded accounts lost, no payouts). 50K/100K/150K are small positive ($0.5k to $2.3k).
- Rolling 12-month starts (48 windows): median net $11k-$17k (TODAY) per 10 accounts, but 17-23 % of windows are net negative; worst windows $-2.9k to $-4.8k.
- All accounts of one stage take the same trades, so they move in lockstep (passes/resets come in groups of 5). Same-size accounts give no diversification: one bad stretch hits all five.

## Compact table (on-demand payouts ON = main; weekly-Friday variant and full tables in tables.md)
| Plan | Setup | 5y passed | 5y resets/buys | 5y fees | funded alive/lost/5-pay | 5y payouts | 5y NET | median days to funded | last-12m NET | rolling-12m median net |
|--|--|--|--|--|--|--|--|--|--|--|
| 25K | TODAY | 20 | 5/15 | $2,725 | 0/15/10 | $55,998 | **$53,273** | 39.5 | $-3,535 | $10,800 |
| 25K | FAST | 10 | 14/5 | $2,294 | 0/5/10 | $52,239 | **$49,945** | 106 | $-2,887 | $12,106 |
| 50K | TODAY | 5 | 0/0 | $600 | 0/0/10 | $92,061 | **$91,461** | 131 | $2,310 | $16,548 |
| 50K | FAST (=BASE) | 5 | 0/0 | $600 | 0/0/10 | $92,061 | **$91,461** | 131 | $2,310 | $16,548 |
| 100K | TODAY | 5 | 0/0 | $950 | 0/0/10 | $104,197 | **$103,247** | 135 | $1,732 | $14,030 |
| 100K | FAST | 5 | 0/0 | $950 | 0/0/10 | $103,091 | **$102,141** | 135 | $1,732 | $14,030 |
| 150K | TODAY | 5 | 0/0 | $1,275 | 0/0/10 | $119,691 | **$118,416** | 151 | $1,553 | $17,090 |
| 150K | FAST | 5 | 5/0 | $2,550 | 0/0/10 | $127,063 | **$124,513** | 128 | $533 | $20,247 |

Columns: passed = evals passed (each becomes a funded account); resets/buys = eval resets / replacement evals bought for busted funded accounts; funded alive/lost/5-pay = at the end of the run / busted / reached 5 payouts. Last-12m = fresh start on the last 252 sessions (alive/lost counts in tables.md).

TODAY = plan's shipped NOISE row for eval and funded (25K N1@$250; 50K N2 brake->1; 100K N2 brake->1; 150K N3@$250 brake->2), no CANDACE.
FAST = D157 setup on the EVAL accounts only (25K N1@$75+C2; 50K = BASE; 100K N2@$250+C3; 150K N5@$100+C4, brakes as D157); funded accounts keep the TODAY row (fast-pass is EVAL-only).

## How it is simulated (script `ten.py`, tables `report.py` -> `tables.md`, raw `results.json`)
- Account engine = pass_fastest sim150 / brake150 logic (EOD MLL + lock, DLL + LucidScale, 40 % consistency + 38 % day stop in EVAL, kill distance, room check, D57 shrink, plan cap, one position per account), re-stepped day by day so many accounts share one tape. Same MNQ 1-minute days.pkl and NOISE/CANDACE streams, 2021-10-21 to 2026-10-30.
- All accounts take the same NOISE trades (same entries and direction; FAST eval accounts only differ in stop width). Each CANDACE trade goes to ONE free eval account (rotating) and is skipped if an opposite NOISE/CANDACE position is open anywhere (hedge lock).
- EVAL: pass = target + 40 % consistency; stuck/bust = reset fee, restart next session. A pass becomes a fresh FUNDED account the next session (eval pool is not refilled). Funded bust/stuck = account lost, replaced next session by a purchased eval.
- FUNDED: EOD drawdown, no day stop, DLL then LucidScale 60 %. Payout when >= 3 profitable days in the cycle, cycle profit >= yaml minimum, largest day <= 40 % of cycle profit (D89), amount = min(cap, cycle profit, balance - lock trigger), at least $500; trader gets 90 %. On-demand = any session end; weekly = Fridays only. After the 5th payout the account stops.
- Views: 5-year run from day 1; last 252 sessions fresh start; 48 rolling 252-session windows (start every 21 sessions). Median days to funded = sessions from eval chain start to pass, over all passes in the run.

## Assumptions (UNVERIFIED unless noted)
- Fees: 25K eval $116 / reset $81 (user's card, VERIFIED; the $81.20 coupon is not used). 50K/100K/150K: eval fee = reset fee = $120 / $190 / $255 (third-party, UNVERIFIED; the $75 figure was not used because 25K is known). The first 5 evals are paid on day 1; the 5 starting funded accounts are free.
- Funded activation fee $0 (UNVERIFIED). Payout caps first/next from the plan yamls: 25K $1,000/$1,500; 50K $2,000/$2,500; 100K $2,500/$3,000; 150K $3,000/$3,500 (UNVERIFIED). Minimum cycle profit and 3 profitable days also from the yamls (150K min cycle $1,000 = the card's payout profit target).
- 90 % split (yaml), 5 payouts then live (live trading not modelled). Withdrawals reduce the balance; the MLL stays locked.
- On-demand vs weekly differ only by path; neither is shown better.
- One price history (simulation, not a forecast); 5-year totals are capped by the 5-payout stop.
