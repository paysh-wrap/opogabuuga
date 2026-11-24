# On-Demand payouts (Lucid) - research r8, 2026-11-24
Official site lucidtrading.com returned HTTP 403 to WebFetch. Official help center (intercom.help/lucid-trading) was reachable. WebFetch summarises pages, so quotes are as returned; re-verify verbatim.

## Facts
| # | Fact | Status | Source / key sentence |
|---|------|--------|----|
| 1 | LucidPro: no fixed payout window | CONFIRMED (help center) | https://intercom.help/lucid-trading/en/articles/12890092-lucidpro-payouts : "There is no fixed payout window, you may request a payout any day after meeting all eligibility criteria." |
| 2 | Min payout $500; min profit goal between cycles $250/$500/$750/$1,000 (25K/50K/100K/150K), resets | CONFIRMED | same page: "The minimum payout request is $500." |
| 3 | Max payout 1st $1,000-$3,000, 2nd+ $1,500-$3,500 by size | CONFIRMED | same page: "Maximum payout amounts depend on account size and payout cycle" |
| 4 | Consistency 40% (largest day / cycle profit), resets per payout | CONFIRMED | "Your largest single-day profit must be no more than 40% of your total profit during the payout cycle." |
| 5 | Buffer = initial MLL + $100 (26,100 / 52,100 / 103,100 / 154,600); cannot withdraw from buffer | CONFIRMED | "You can not take payout from the buffer balance." |
| 6 | Funds leave account in minutes; paid out within 2 business days; request cannot be edited/cancelled; 90/10 | CONFIRMED | "Payouts will be disbursed to your payment method within 2 business days." |
| 7 | Trading after request risks denial | CONFIRMED | "You should trade as if the payout amount has already been removed from your balance." |
| 8 | Official page has NO "3 profitable days" rule and NO MLL-lock / trading-block rule | CONFIRMED (absence on that page) | app's 3-day (LUCID_RULES "VERIFY") and "submitted blocks trading" are unconfirmed |
| 9 | On-demand = request intraday without waiting for session close; applies to LucidPro, LucidFlex, LucidDaily with DLL ON; Daily allows several requests same day; no-DLL accounts stay on old system; effective Sun Oct 18 (2026) | THIRD-PARTY | https://www.eltraderfinanciado.com/en/news/lucid-trading/lucid-trading-on-demand-payouts-40-dll-october-2026 : "the moment the dashboard marks everything as complete, without waiting for the market to close" |
| 10 | Window 6:00 PM-3:45 PM ET; DLL chosen at purchase, immutable; after intraday request "trading on the account is paused until the end of the trading day"; DLL-on is cheaper; LucidScale DLL = 60% of peak EOD profit after balance closes above buffer | THIRD-PARTY | https://phidiaspropfirm.com/?p=18345 : "On Demand Payouts let a funded LucidPro account withdraw profit made during the session, from 6:00 PM to 3:45 PM ET." |
| 11 | LucidDirect payouts page exists (not read) | UNVERIFIED | https://intercom.help/lucid-trading/en/articles/11404669-how-do-luciddirect-payouts-work |
Not found anywhere: news/volatility-day restrictions, eval-stage applicability (payouts are funded/live only), fees beyond the 10% split, LucidScale/MLL-lock effect of on-demand.

## App conflicts
- Engine pays only Fri 17:05 weekly; Lucid allows any day (fact 1), so engine is stricter, not in conflict. Skim rule "leaves >= 26,100" matches the buffer (fact 5). "3 profitable days" is unconfirmed by official page. Engine's trading block until processed is plausibly right (fact 10) but official only says denial risk.

## App implications
- Payouts page / profit calculator: add "On-demand" mode (requires plan DLL ON): shows eligible now = min(cap, balance - buffer floor, 40% consistency headroom, >= $500 and cycle profit >= goal); net = 90%; blocked-until-EOD flag; compare vs weekly.
- Engine: new on-demand trigger evaluated intraday only after profits booked and flat; recheck floor with open PnL = 0, consistency incl. today's profit (today must not exceed 40% of cycle total), cap by size/payout number, 6:00 PM-3:45 PM ET window; submit then set trading-block until processed/EOD; never allow amount that leaves balance < floor (26,100 for 25K...); no second request while one pending (except Daily plan); dry-run/shadow first; keep weekly sweep as fallback; per-account plan via D168.
- Note: same-day consistency is hard - a single big day is the largest day; requesting on that day often fails the 40% rule.

## Open questions for Lucid support
1. Exact on-demand rules, window, DLL-on only? 2. Is "3 profitable days" real for Pro? 3. Trading pause: until EOD or until processed? 4. Does a payout request lock MLL / affect LucidScale DLL? 5. Consistency counting today's open session profit? 6. Multiple requests per day on Pro/Flex? 7. Any news-day or eval restrictions? 8. Does DLL-off conversion exist?
