"""Drawdown Guard (§8) [Pillar] — conditional half-close + breakeven + runner, and the D7 1:1 management."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from decimal import Decimal

from app.engine.trade_plan import Direction, TradePlan, round_to_tick


@dataclass(frozen=True)
class GuardCfgView:
    mode: str  # auto | on | off


def guard_active(drawdown_type: str, mll_locked: bool, cfg: GuardCfgView) -> bool:
    """§8 reference: ON only where open-profit peaks move the loss limit (intraday trailing, not yet locked)."""
    if cfg.mode != "auto":
        return cfg.mode == "on"
    return drawdown_type == "intraday" and not mll_locked


def apply_guard(plan: TradePlan, tick: Decimal, fee_cover_ticks: int) -> TradePlan:
    partial = round_to_tick(plan.entry + (plan.take_profit - plan.entry) / 2, tick, toward=plan.entry)
    be = plan.entry + plan.direction.sign * fee_cover_ticks * tick
    return replace(plan, partial_price=partial, breakeven_price=be)


def ratchet(current: Decimal, candidate: Decimal, d: Direction) -> Decimal:
    """Stops only ever tighten."""
    return max(current, candidate) if d is Direction.LONG else min(current, candidate)


def runner_stop(plan: TradePlan, best_price: Decimal, trail_r: Decimal, tick: Decimal) -> Decimal:
    """§8 reference: trail ≤ 2R behind the best price, never looser than breakeven."""
    assert plan.breakeven_price is not None
    cand = round_to_tick(best_price - plan.direction.sign * trail_r * plan.risk_pts, tick, toward=plan.entry)
    return ratchet(plan.breakeven_price, cand, plan.direction)


def split_legs(n: int) -> tuple[int, int]:
    """Leg A (TP at partial) = ceil(n/2); leg B = the rest."""
    a = math.ceil(n / 2)
    return a, n - a


def min_contracts(guard_on: bool, on_min: int, off_min: int) -> int:
    return on_min if guard_on else off_min


@dataclass(frozen=True)
class OneToOneAction:
    """D7 management once price reaches the partial price (75% of the way to TP)."""

    close_qty: int
    new_stop: Decimal


def one_to_one_on_partial(plan: TradePlan, n: int) -> OneToOneAction:
    assert plan.partial_price is not None and plan.breakeven_price is not None and plan.lock_price is not None
    if n >= 2:
        return OneToOneAction(close_qty=split_legs(n)[0], new_stop=plan.breakeven_price)  # 50% (ceil) off, rest at BE
    return OneToOneAction(close_qty=0, new_stop=plan.lock_price)  # single contract: lock +0.30R instead
