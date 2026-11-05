"""Contract sizing (§9). Pure."""

from __future__ import annotations

from decimal import Decimal


def per_contract_risk(stop_ticks: Decimal, tick_value: Decimal, fee_rt: Decimal, slip_ticks: int) -> Decimal:
    return stop_ticks * tick_value + fee_rt + slip_ticks * tick_value


def size_contracts(
    risk_usd: Decimal,
    stop_ticks: Decimal,
    tick_value: Decimal,
    fee_rt: Decimal,
    slip_ticks: int,
    firm_max: int,
    internal_max: int,
    min_qty: int,
) -> int:
    """§9 reference implementation (binding). 0 → Skip("STOP_TOO_WIDE")."""
    per = per_contract_risk(stop_ticks, tick_value, fee_rt, slip_ticks)
    n = min(int(risk_usd // per), firm_max, internal_max)
    return n if n >= min_qty else 0


def profile_for_base(base: Decimal, std_min_risk_base: Decimal) -> str:
    """TIGHT while risk base < $1,500, STD from $1,500 (§6)."""
    return "STD" if base >= std_min_risk_base else "TIGHT"
