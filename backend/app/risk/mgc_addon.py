"""D184 (user 2026-11-25): the MGC add-on (NOISE + CANDACE on micro gold) may hold ONE position on an account that also
holds the main MNQ position. Pure checks only; the controller applies them and every pre-trade check still runs."""

from __future__ import annotations

from collections.abc import Sequence

MGC_MODES = frozenset({"MGC_NOISE", "MGC_CANDACE"})
MNQ_PARTNERS = frozenset({"NOISE", "CANDACE_ICT", "ORDER_FLOW"})  # main strategies (and the D181 leg) the add-on sits beside


def is_mgc_mode(mode: str) -> bool:
    return mode in MGC_MODES


def is_mgc_symbol(symbol: str) -> bool:
    """MGC and its real contracts (MGCZ6 ...)."""
    return symbol.upper().startswith("MGC")


def other_instrument_ok(new_mode: str, new_symbol: str, other: Sequence[tuple[str, str]]) -> bool:
    """`other` = (strategy, symbol) of the account's open legs in the OTHER instrument (MGC legs for an MNQ signal, MNQ
    legs for an MGC signal). Different instruments are the narrow rule-7 exception (D184); anything else stays
    POSITION_OPEN: an MGC signal sits only beside MNQ main legs, an MNQ signal only beside ONE MGC add-on leg."""
    if is_mgc_mode(new_mode):
        return all(s in MNQ_PARTNERS and not is_mgc_symbol(sym) for s, sym in other)
    return new_mode in MNQ_PARTNERS and not is_mgc_symbol(new_symbol) and len(other) == 1
