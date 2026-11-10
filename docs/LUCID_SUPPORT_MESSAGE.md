# Message to send Lucid Trading support (copy + paste)

Hi Lucid team,

I trade LucidDaily 25K accounts (evaluation and funded) and want to confirm a few rules in writing before I use an
automated system:

1. Is fully automated order placement allowed on LucidDaily evaluation AND funded accounts, if the orders are sent
   through CrossTrade (TradingView webhook → Tradovate)?
   Every order would carry a stop-loss and take-profit, hold at least 6 seconds, and never hedge across accounts.
2. Can API access (Tradovate API / OAuth) be enabled on my Lucid-issued Tradovate account IDs so my software can
   read positions, fills and P&L? If not, which supported route lets software read them?
3. Daily Loss Limit ($600): is it measured from the prior day's closing balance, or from the day's highest balance
   (including open profit)? Does the DLL close positions and stop the day (soft breach) or fail the account?
4. On my funded accounts, is the max-loss drawdown end-of-day or intraday-trailing until it locks at $25,100?
5. Microscalping: is the rule "more than 50% of profit from trades held 5 seconds or less", and over which period
   (payout cycle or whole account)?

Thank you!
