"""D137 (user 2026-11-13: "All my drawdown will be EOD"): which equity the kill switch / MLL-breach watchdog looks at.

Pure (no I/O). Default (toggle OFF) = balance + open P&L, the safest reading. With `strategy.eod_closed_balance` ON and
an EOD-drawdown account the watchdog looks at the closed balance only (an EOD account's floor moves and is tested at the
end of the session). Intraday-drawdown accounts always use balance + open P&L. VERIFY with Lucid first."""

from __future__ import annotations

from decimal import Decimal


def watched_equity(balance: Decimal, open_pnl: Decimal, drawdown_type: str, closed_only: bool) -> Decimal:
    """Equity the kill switch compares against the MLL."""
    if closed_only and drawdown_type == "eod":
        return balance
    return balance + open_pnl
