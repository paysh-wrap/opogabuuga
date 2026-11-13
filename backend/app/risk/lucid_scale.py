"""LucidScale DLL (LucidPro, lucidtrading.com plan card 2026-11-13). Pure (no I/O).

Card: "LucidScale DLL (above initial trail): 60% of peak EOD balance". VERIFY interpretation: once the MLL has locked
(= the balance is above the initial trail) the DLL is `scale_pct` % of the peak EOD PROFIT (peak EOD balance - starting
balance); before the lock (and for plans without the field) it is the fixed base DLL."""

from __future__ import annotations

from decimal import Decimal

from app.risk.risk_base import money


def effective_dll(
    base_dll: Decimal | None,
    scale_pct: Decimal | None,
    locked: bool,
    peak_eod_balance: Decimal,
    starting_balance: Decimal,
) -> Decimal | None:
    if scale_pct is None or not locked or base_dll is None:
        return base_dll
    return money(scale_pct / 100 * max(peak_eod_balance - starting_balance, Decimal(0)))
