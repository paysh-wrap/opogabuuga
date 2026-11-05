"""risk_base = equity incl. open P&L − current MLL (§9). Never the account size."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def risk_base(equity_incl_open: Decimal, mll: Decimal) -> Decimal:
    return money(equity_incl_open - mll)
