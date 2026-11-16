"""D145 (user-approved exception): OKALA 8020 ONLY may add to its own open position on the same account. PURE.

Every other strategy keeps "max 1 open position per account" (risk/checks.py one_position). An add is allowed only when
every open trade on the account is OKALA_8020, in the SAME direction (never an opposite order — hedge lock and D139
unchanged), the open position's stop is at break even or better (`require_be`, TP1 taken), fewer than `max_adds` adds
are open, and the remaining per-trade risk cap (cap − worst case still open) buys at least one contract. The caller
still runs every Lucid pre-trade check on the add.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ADD_MODE = "OKALA_8020"  # the single allow-listed plan mode


@dataclass(frozen=True)
class OpenLeg:
    strategy: str
    sign: int  # +1 long, −1 short
    at_breakeven: bool  # its stop is at entry or better
    risk_usd: Decimal  # worst case still open on it


@dataclass(frozen=True)
class AddDecision:
    ok: bool
    reason: str | None
    max_contracts: int = 0
    adds_open: int = 0


def add_allowed(
    mode: str,
    sign: int,
    legs: list[OpenLeg],
    cap_usd: Decimal,
    per_contract_usd: Decimal,
    max_adds: int,
    require_be: bool,
) -> AddDecision:
    """Decide an add to an open position (only reached when the account already holds one)."""
    if mode != ADD_MODE or any(x.strategy != ADD_MODE for x in legs):
        return AddDecision(False, "POSITION_OPEN")
    if any(x.sign != sign for x in legs):
        return AddDecision(False, "OKALA_ADD_OPPOSITE")
    if require_be and not all(x.at_breakeven for x in legs):
        return AddDecision(False, "OKALA_ADD_NOT_AT_BE")
    adds = len(legs) - 1
    if adds >= max_adds:
        return AddDecision(False, "OKALA_MAX_ADDS", adds_open=adds)
    left = cap_usd - sum((x.risk_usd for x in legs), Decimal(0))
    n = int(left // per_contract_usd) if per_contract_usd > 0 and left > 0 else 0
    if n < 1:
        return AddDecision(False, "OKALA_ADD_CAP", adds_open=adds)
    return AddDecision(True, None, n, adds)
