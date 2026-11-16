"""Lucid fit sizing shared by the fixed-dollar strategies (D143 JJ F.P.T, D144 GALA PRICE ACTION). PURE.

Plumbing only — no strategy entry rule lives here. Moved out of engine/jj_fpt.py unchanged (D144).
"""

from __future__ import annotations

from decimal import Decimal


def contracts_for(
    risk_usd: Decimal, stop_pts: Decimal, tick: Decimal, tick_value: Decimal, fee_rt: Decimal, slip_ticks: int
) -> int:
    """#28 + #29: same dollars on every trade — contracts = risk $ ÷ (stop $ + fee + slippage both ways), rounded down.
    A 50 pt stop gets about half and a 12.5 pt stop about double the contracts of a 25 pt stop."""
    per = stop_pts / tick * tick_value + fee_rt + 2 * slip_ticks * tick_value
    if per <= 0:
        return 0
    return int(risk_usd // per)


def trade_risk_usd(
    max_loss: Decimal,
    risk_pct: Decimal,
    losses_per_session: int,
    dll_left: Decimal | None,
    dll_use_pct: Decimal,
    mll_room: Decimal,
    plan_cap: Decimal | None,
    day_stop: Decimal | None,
) -> Decimal:
    """D143 Lucid fit (sizing only — never JJ's entry rules): the per-trade $ risk is JJ's #29 share of the drawdown,
    cut so that his worst session (`losses_per_session` losses in a row, #27) fits inside the DLL left today
    (x dll_use_pct), the room above the MLL less the kill-switch distance, and the consistency day stop; the plan's
    per-trade cap applies too. Rounded down to cents; never below 0."""
    n = Decimal(max(losses_per_session, 1))
    parts = [risk_pct * max_loss, max(mll_room, Decimal(0)) / n]
    if dll_left is not None:
        parts.append(max(dll_left, Decimal(0)) * dll_use_pct / n)
    if plan_cap is not None:
        parts.append(plan_cap)
    if day_stop is not None:
        parts.append(max(day_stop, Decimal(0)) / n)
    return min(parts).quantize(Decimal("0.01"), rounding="ROUND_DOWN")
