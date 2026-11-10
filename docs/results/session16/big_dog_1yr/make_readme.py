import json, os
H = os.path.dirname(os.path.abspath(__file__)); D = json.load(open(H + "/results.json")); R = D["rows"]
name = lambda p: p.replace("lucid_", "").replace("_", " ").title().replace("K", "K")
order = ["lucid_pro_25k","lucid_pro_50k","lucid_pro_100k","lucid_pro_150k","lucid_flex_25k","lucid_flex_50k","lucid_flex_100k","lucid_flex_150k","lucid_daily_25k"]
L = ["| plan | AI acc | trades | /day | win | PF | net $ | max DD $ | avg $/2wk | eval pass | eval bust | median days to pass | funded bust (1st yr) | funded $/2wk |", "|" + "---|" * 14]
for p in order:
    for x in sorted([r for r in R if r["plan"] == p], key=lambda r: r["acc"]):
        L.append(f"| {name(p)} | {x['acc']*100:.0f}% | {x['n']:.0f} | {x['per_day']:.2f} | {x['win']:.0f}% | {x['pf']:.2f} | {x['net']:+,.0f} | {x['dd']:,.0f} | {x['per2w']:+,.0f} | {x['eval_pass']:.0f}% | {x['eval_bust']:.0f}% | {('%.0f' % x['med_days']) if x['med_days'] else 'n/a'} | {x['funded_bust']:.0f}% | {x['funded_per2w']:+,.0f} |")
def g(p, a): return next(r for r in R if r["plan"] == p and abs(r["acc"] - a) < 1e-9)
txt = f"""# Big Dog Small Trade Aggressive, last 12 months (session 16)

Research only. No backend/frontend code touched. **AI accuracy is SIMULATED (unproven; published LLM next-day accuracy is 50-56%). One year (about 257 sessions) is a SMALL sample. Every number is a bound ("if the AI were X% right"), not a forecast.**

## Verdict (plain language)
- At 50-55% accuracy (the only published range) Big Dog loses money on every plan: 50% = net {g('lucid_pro_25k',.5)['net']:+,.0f} (Pro 25K) to {g('lucid_pro_150k',.5)['net']:+,.0f} (Pro 150K); eval pass only {g('lucid_pro_150k',.5)['eval_pass']:.0f}-{g('lucid_pro_25k',.5)['eval_pass']:.0f}%, eval bust {min(r['eval_bust'] for r in R if r['acc']==.5):.0f}-{max(r['eval_bust'] for r in R if r['acc']==.5):.0f}%.
- It only turns clearly positive at 65-70% simulated accuracy (PF {g('lucid_pro_150k',.65)['pf']:.2f}-{g('lucid_pro_150k',.7)['pf']:.2f}); even at 70% eval pass is only {min(r['eval_pass'] for r in R if r['acc']==.7):.0f}-{max(r['eval_pass'] for r in R if r['acc']==.7):.0f}% (Pro 150K best {g('lucid_pro_150k',.7)['eval_pass']:.0f}%) and funded accounts bust {min(r['funded_bust'] for r in R if r['acc']==.7):.0f}-{max(r['funded_bust'] for r in R if r['acc']==.7):.0f}% in year 1.
- Risk of ruin is the issue, not trade count: about 2 to 3 trades a day with 3 micros per $1,000 of loss limit and 12.5% per-trade risk means 8 full stop-outs reach the loss limit, and the edge per trade is small (PF 1.0-1.2).
- The extras (BE at +1R, trails, locks) cut average winners; at 2R target, a 50% win rate with scratches is roughly break-even after costs, so accuracy above about 65% is needed.
- Verdict: not proven and not safe to rely on; keep it paper/SEMI until the AI ledger shows real accuracy of 65%+ over many sessions, and do not size up on the strength of this one year.

## Method
- Data: Databento `MNQ.v.0` and `MGC.v.0` 1-minute (volume roll), cached CSVs, 2025-11-01 to 2026-10-31 (MNQ and MGC usable days after the same roll/bad-print guard as the AI Duo study). Loader, RTH-anchored VWAP (09:30) and 5-minute bars reused from `../ai_duo_window/ai_duo_window.py`; account engine (`eval_run`, `funded_run`, `plan_rules` reading `config/rules/*.yaml`) reused from `../../session15/lib.py`.
- AI side SIMULATED: correct with probability = accuracy versus the day's real RTH open-to-close direction, independent per market, 27% NEUTRAL days skipped at random. 200 seeds per cell for trade statistics (means).
- Window 09:36-11:30 ET (first 5m bar closing after 09:36, i.e. entry about 09:40; 09:30-09:35 bars excluded). Entry = first 5m bar that pulls back to VWAP and closes in the AI direction; fill at next 1m open + 1 tick; re-entry allowed on later pullbacks after the previous exit (one position per market at a time; MNQ and MGC may overlap; no hedging since they are in different hedge groups).
- Stop = pullback extreme (two 5m bars) +/- 1 tick, widened to at least $10 of risk per micro (assumption); signal skipped if 1 micro does not fit the per-trade budget. Target 2R (limit, needs 1-tick trade-through). Stop moves: BE (entry) at +1R; trail 1R behind best price from +1.5R; MNQ lock +100 pt then stop to entry+50 pt; MGC step trail 20 ticks per 60 ticks gained (my reading of "20 ticks per 60"). Same-bar stop and target counts as stop. Flat at 11:30.
- Costs: 1 tick slippage on entry, stop and flat exits; fee per micro round trip MNQ $1.00, MGC $1.60 (from the rule files).
- Plan sizing: per-trade max loss 12.5% of plan MLL distance (Pro 25K $125); max micros = 3 x MLL/$1,000 (25K 3, 50K 6, 100K 9, 150K 13) reduced to fit the budget; day loss limit 37.5% of MLL ($375 on 25K; also reduces size to fit what remains); max 5 trades a day across both markets; stop after 3 losses; day stop when session profit >= 39% of the plan's eval profit target. Pro / Flex / Daily of the same size share sizing; they differ only in account rules (target, DLL, consistency, minimum profitable days, payout rules) from `config/rules`.
- Account tests: the per-day trade table of each seed is block-bootstrapped (blocks of 10 sessions, 25 paths per seed over {D['na']} seeds = {D['na']*D['npth']:,} paths per cell). Eval runs up to 750 sessions: PASS = target reached with the plan's consistency and profitable-day rules, BUST = EOD loss limit touched (including intraday worst open loss per trade). Funded = first 260 sessions with payout rules of the plan (weekly-style cadence every 10 sessions); funded $/2wk = mean paid to trader per 2 weeks over the year including busted paths.
- `avg $/2wk` in the main columns = trading net divided by (sessions/10), no account rules. `win` counts trades with pnl > 0 (a BE scratch after costs is a loss). `max DD` is trade-by-trade on closed trades.
- Limitations: no 08:30 news flatten; MGC leg shares the MNQ-based AI truth (RTH open-to-close) which is a loose proxy for gold; bootstrap resamples one year of days so tail risk beyond that year is not captured; Flex DLL is not enforced (not stated in the rule file); Daily 25K funded rules as in the YAML (VERIFY items unconfirmed); one-year sample, so differences of a few points between cells are noise.

## Results (mean over seeds; trades and returns are for 12 months, 1 account)

{chr(10).join(L)}

## Files
`big_dog_1yr.py` (simulation), `make_readme.py` (this table), `results.json` (every cell), `cands.pkl` is not committed. Rerun: `python3 big_dog_1yr.py MNQ.csv MGC.csv 200 200 25` then `python3 make_readme.py`.
"""
open(H + "/README.md", "w").write(txt)
