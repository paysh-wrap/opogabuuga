"""Household-wide direction lock (§1.8) + one open position per account. Pure."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import RulesConfig


@dataclass(frozen=True)
class OpenPosition:
    account: str
    symbol: str
    profile: str
    direction: str  # LONG | SHORT


def hedge_conflict(
    rules: RulesConfig, symbol: str, direction: str, open_positions: list[OpenPosition]
) -> OpenPosition | None:
    """Any open position in the same super-group (EQUITY_INDEX / METALS) in the opposite direction, on ANY account,
    profile or instrument, blocks the new trade."""
    sg = rules.super_group_of(symbol)
    for p in open_positions:
        if rules.super_group_of(p.symbol) == sg and p.direction != direction:
            return p
    return None


def account_has_position(account: str, open_positions: list[OpenPosition]) -> bool:
    return any(p.account == account for p in open_positions)
